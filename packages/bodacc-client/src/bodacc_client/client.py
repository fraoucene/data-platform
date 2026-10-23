"""Client HTTP de l'API BODACC (OpenDataSoft Explore v2.1, dataset `annonces-commerciales`)."""

import json
import time
from collections.abc import Callable, Iterator
from datetime import date
from types import TracebackType
from typing import Any

import httpx

from bodacc_client.models import Annonce

EXPORT_PATH = "/exports/jsonl"
RECORDS_PATH = "/records"
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})
BULLETINS = ("A", "B", "C")  # `numeroannonce` repart à 1 dans chaque bulletin
MAX_PAGE_SIZE = 100  # plafond de `limit` sur /records

DEFAULT_BASE_URL = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales"
DEFAULT_USER_AGENT = "data-platform-bodacc-client/0.1"
DEFAULT_TIMEOUT = 60.0  # secondes de lecture : l'export d'une journée prend ~5 s, le défaut httpx (5 s) est trop court
CONNECT_TIMEOUT = 5.0
BASE_DELAY = 1.0
MAX_DELAY = 30.0


class BodaccError(Exception):
    """Échec d'un appel à l'API BODACC."""

    def __init__(self, message: str, status_code: int | None = None, url: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class BodaccRateLimitError(BodaccError):
    """Quota dépassé (HTTP 429) même après toutes les tentatives."""


class _RetryableResponse(Exception):
    """Interne : statut transitoire (429, 5xx) reçu avant toute annonce ; porte l'erreur et `Retry-After`."""

    def __init__(self, error: BodaccError, retry_after: str | None) -> None:
        super().__init__(str(error))
        self.error = error
        self.retry_after = retry_after


class BodaccClient:
    """Client de l'API BODACC, à utiliser comme context manager.

    >>> with BodaccClient() as client:
    ...     ...

    `http` et `sleep` sont injectables pour tester sans réseau ni attente réelle.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 5,
        base_delay: float = BASE_DELAY,
        max_delay: float = MAX_DELAY,
    ) -> None:
        if max_attempts < 1:
            # Avec 0, la boucle de tentatives ne tournerait pas : journée vide, sans requête ni erreur.
            raise ValueError(f"max_attempts doit valoir au moins 1, reçu {max_attempts}")
        self._owns_http = http is None
        self._http = http or httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout, connect=CONNECT_TIMEOUT),
            headers={"User-Agent": user_agent},
        )
        self._sleep = sleep
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay

    def close(self) -> None:
        """Ferme la connexion HTTP, seulement si ce client l'a créée."""
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "BodaccClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    @staticmethod
    def _day_params(day: date) -> dict[str, str]:
        """Filtre ODSQL d'une journée de parution. Le littéral `date'…'` est obligatoire (champ de type date)."""
        return {"where": f"dateparution=date'{day.isoformat()}'"}

    def _backoff(self, attempt: int, retry_after: str | None) -> float:
        """Délai avant la tentative suivante : `Retry-After` s'il est en secondes, sinon exponentiel plafonné.

        `attempt` commence à 0 : 1 s, 2 s, 4 s, 8 s… avec les valeurs par défaut.
        """
        if retry_after and retry_after.strip().isdigit():
            return float(retry_after.strip())
        return min(self._base_delay * 2**attempt, self._max_delay)

    @staticmethod
    def _error_for(response: httpx.Response) -> BodaccError:
        """Construit l'exception adaptée au statut, avec un extrait du corps pour le diagnostic."""
        response.read()
        message = f"HTTP {response.status_code} sur {response.request.url} : {response.text[:200]}"
        error_class = BodaccRateLimitError if response.status_code == 429 else BodaccError
        return error_class(message, status_code=response.status_code, url=str(response.request.url))

    def fetch_day(self, day: date) -> Iterator[dict[str, Any]]:
        """Toutes les annonces d'une journée de parution, une par une, en streaming.

        Générateur : aucune requête n'est faite tant que l'appelant n'itère pas.
        Lit l'export JSONL ligne par ligne, sans charger la journée (~59 Mo) en mémoire.

        Retries : 429, 502, 503, 504, timeouts et erreurs réseau sont réessayés jusqu'à
        `max_attempts`, mais seulement AVANT la première annonce rendue. Après, une coupure
        lève `BodaccError` : réessayer redonnerait des annonces déjà émises (doublons).
        L'appelant (la Lambda) rejoue alors la journée entière.
        """
        params = self._day_params(day)
        for attempt in range(self._max_attempts):  # pragma: no branch (la dernière tentative rend ou lève)
            started = False
            try:
                for row in self._stream_export(params):
                    started = True
                    yield row
                return
            except _RetryableResponse as retryable:
                self._wait_or_raise(attempt, retryable.error, retryable.retry_after)
            except httpx.TransportError as exc:  # inclut les timeouts
                if started:
                    raise BodaccError(f"Flux interrompu après le début de la lecture : {exc!r}") from exc
                self._wait_or_raise(attempt, self._network_error(exc), None)

    def count_day(self, day: date) -> int:
        """Nombre d'annonces d'une journée selon l'API (`total_count` de `/records`, exact).

        Sert de référence pour vérifier qu'une lecture complète n'a rien perdu.
        """
        params = {**self._day_params(day), "limit": "1"}
        return int(self._get_with_retry(RECORDS_PATH, params).json()["total_count"])

    def fetch_day_paged(self, day: date, page_size: int = MAX_PAGE_SIZE) -> Iterator[dict[str, Any]]:
        """Plan B de `fetch_day` : même résultat, par pages keyset sur `/records`.

        Pour chaque bulletin (A, B, C) : `numeroannonce > N` trié par `numeroannonce`, puis N avance
        au dernier reçu. Pas de plafond d'offset (10 000), et chaque page se réessaie sans doublon.
        325 appels pour une journée de ~32 000 annonces, contre 1 pour l'export.
        """
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValueError(f"page_size doit être entre 1 et {MAX_PAGE_SIZE}, reçu {page_size}")
        day_filter = self._day_params(day)["where"]
        for bulletin in BULLETINS:
            last_numero = 0
            while True:
                params = {
                    "where": f"{day_filter} and publicationavis='{bulletin}' and numeroannonce > {last_numero}",
                    "order_by": "numeroannonce",
                    "limit": str(page_size),
                }
                results = self._get_with_retry(RECORDS_PATH, params).json()["results"]
                yield from results
                if len(results) < page_size:
                    break
                last_numero = results[-1]["numeroannonce"]

    def _stream_export(self, params: dict[str, str]) -> Iterator[dict[str, Any]]:
        """Une tentative : ouvre l'export, classe le statut, puis rend les lignes décodées."""
        with self._http.stream("GET", EXPORT_PATH, params=params) as response:
            self._check_status(response)
            # Le serveur annonce `application/json` mais le corps est du JSONL : jamais `response.json()`.
            for line in response.iter_lines():
                if line.strip():
                    yield json.loads(line)

    def _get_with_retry(self, path: str, params: dict[str, str]) -> httpx.Response:
        """GET complet (non streamé) avec la même politique de retry que `fetch_day`."""
        for attempt in range(self._max_attempts):
            try:
                response = self._http.get(path, params=params)
                self._check_status(response)
                return response
            except _RetryableResponse as retryable:
                self._wait_or_raise(attempt, retryable.error, retryable.retry_after)
            except httpx.TransportError as exc:
                self._wait_or_raise(attempt, self._network_error(exc), None)
        raise AssertionError("inatteignable : _wait_or_raise lève à la dernière tentative")  # pragma: no cover

    def _check_status(self, response: httpx.Response) -> None:
        """Statut transitoire → `_RetryableResponse` ; autre erreur (400, 404…) → `BodaccError`, sans retry."""
        if response.status_code in RETRYABLE_STATUS:
            raise _RetryableResponse(self._error_for(response), response.headers.get("retry-after"))
        if response.is_error:
            raise self._error_for(response)

    def _wait_or_raise(self, attempt: int, error: BodaccError, retry_after: str | None) -> None:
        """Dernière tentative : lève `error`. Sinon : attend le délai de backoff."""
        if attempt == self._max_attempts - 1:
            raise error
        self._sleep(self._backoff(attempt, retry_after))

    def _network_error(self, exc: httpx.TransportError) -> BodaccError:
        error = BodaccError(f"Échec réseau après {self._max_attempts} tentatives : {exc!r}")
        error.__cause__ = exc
        return error

    def iter_annonces(self, day: date) -> Iterator[Annonce]:
        """Comme `fetch_day`, mais chaque annonce est validée et décodée en `Annonce`."""
        for row in self.fetch_day(day):
            yield Annonce.model_validate(row)
