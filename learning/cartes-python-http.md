---
title: "Cartes · HTTP Python (httpx)"
type: cartes
langage: Python
cours: HTTP
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · HTTP Python (httpx)
Python · HTTP : client, réponses, erreurs, streaming, tests, async (format spec v3 de revision-pwa).

## 1. httpx.Client : timeout et en-têtes
- Sous-thème : client
- Niveau : 1
- Définition : `httpx.Client(base_url=…, timeout=…, headers=…)` garde configuration et connexion entre les appels (≈ `axios.create`) ; à fermer avec `with` ou `close()`.
- Contexte : Le timeout par défaut de httpx est de **5 s** pour chaque phase (connexion, lecture, écriture, pool) : trop court pour un export qui streame une journée. `httpx.Timeout(60, connect=5)` sépare une connexion qui doit échouer vite d'une lecture longue. Un `User-Agent` explicite identifie le client auprès d'une API publique partagée. `params={…}` encode la query string.
- Usage : ✅ plusieurs appels vers la même API (connexion réutilisée, config centrale) · ❌ `httpx.get` en boucle : une connexion par appel ; `timeout=None` : un serveur muet bloque jusqu'au timeout de la Lambda.

```python
# Exemple 1 : le défaut, puis le réglage
import httpx
httpx.Client().timeout
# → httpx.Timeout(5.0)
t = httpx.Timeout(60, connect=5)
(t.connect, t.read)  # → (5, 60)
```

```python
# Exemple 2 : en-tête et params, sans réseau
import httpx
vu = {}
def serveur(req):         # faux serveur
    vu["ua"] = req.headers["user-agent"]
    vu["q"] = req.url.params["where"]
    return httpx.Response(200)
t = httpx.MockTransport(serveur)
w = "dateparution=date'2026-10-20'"
with httpx.Client(
        base_url="https://bodacc.test",
        headers={"User-Agent": "dp/0.1"},
        transport=t) as c:
    c.get("/records", params={"where": w})
vu["ua"]      # → "dp/0.1"
vu["q"] == w  # → True  (encodé, décodé)
```

- Quiz : Avec `t = httpx.Timeout(60, connect=5)`, que vaut `t.pool` ?
- [ ] `5`
- [x] `60`
- [ ] `None`
- [ ] `5.0`
- Réponse : `60` : le premier argument s'applique à toutes les phases non précisées (lecture, écriture, pool) ; seule `connect` est à 5.

## 2. Response : statut, texte, json()
- Sous-thème : réponses
- Niveau : 1
- Définition : Une `httpx.Response` expose `status_code`, `headers`, `text` (corps décodé), `content` (octets) et `json()` (corps parsé) ; un 4xx ou 5xx ne lève rien.
- Contexte : Comme `fetch` : un 404 ou un 503 est une réponse normale, pas une exception ; il faut tester le statut ou appeler `raise_for_status()`. `json()` est une **méthode**, `text` et `content` des propriétés. `is_success` (2xx) et `is_error` (4xx, 5xx) évitent les comparaisons à la main. `httpx.get(url)` crée un client jetable pour un seul appel.
- Usage : ✅ lire le statut avant le corps, `json()` sur une réponse JSON d'un seul document · ❌ `r.json()` sans tester le statut : une page d'erreur HTML lève `JSONDecodeError`, loin de la cause.

```python
# Exemple 1 : lire une réponse
import httpx
r = httpx.Response(200,
    json={"total_count": 32373})
r.status_code              # → 200
r.json()["total_count"]    # → 32373
r.is_success               # → True
```

```python
# Exemple 2 : un 503 ne lève pas
import httpx

t = httpx.MockTransport(lambda req:
    httpx.Response(503, text="busy"))
with httpx.Client(transport=t) as c:
    r = c.get("https://bodacc.test")
(r.status_code, r.text)  # → (503, "busy")
r.is_error               # → True
```

- Quiz : Que fait `r.json["total_count"]` (sans parenthèses) ?
- [ ] Renvoie `32373`
- [x] Lève `TypeError`
- [ ] Lève `KeyError`
- [ ] Lève `AttributeError`
- Réponse : `TypeError` ('method' object is not subscriptable) : `json` est une méthode, il faut l'appeler ; `text` et `content`, eux, se lisent sans parenthèses.

## 3. params : construire la query string
- Sous-thème : client
- Niveau : 1
- Définition : `params={…}` encode un dict en query string : espaces et guillemets échappés, liste → clé répétée (≈ `URLSearchParams`).
- Contexte : Ne jamais concaténer la query à la main : un filtre ODSQL comme `dateparution=date'2026-10-23'` contient `=`, `'` et des espaces, que `params` encode correctement. Les valeurs non `str` sont converties (`10` → `"10"`, `True` → `"true"`). Des `params` donnés au `Client` s'ajoutent à ceux de chaque appel. Piège : des `params` passés à l'appel **remplacent** la query déjà écrite dans l'URL.
- Usage : ✅ toujours `params=` pour filtres, pagination, tri · ❌ f-string `f"{url}?where={w}"` : encodage oublié ; mélanger une query dans l'URL et `params=` : la première disparaît.

```python
# Exemple 1 : dict → query encodée
import httpx
q = httpx.Request("GET", "https://b.t/r",
    params={"limit": 10, "where": "a b"})
str(q.url)
# → "https://b.t/r?limit=10&where=a+b"
```

```python
# Exemple 2 : liste → clé répétée
import httpx

q = httpx.Request("GET", "https://b.t/r",
    params={"bulletin": ["A", "B"]})
str(q.url)
# → "https://b.t/r?bulletin=A&bulletin=B"
```

- Quiz : Quelle URL part avec `c.get("https://b.t/r?limit=1", params={"where": "x"})` ?
- [ ] `https://b.t/r?limit=1&where=x`
- [x] `https://b.t/r?where=x`
- [ ] `https://b.t/r?limit=1`
- [ ] `ValueError` : query en double
- Réponse : `https://b.t/r?where=x` : les `params` de l'appel remplacent la query écrite dans l'URL ; tout mettre dans `params`.

## 4. raise_for_status : lever sur 4xx et 5xx
- Sous-thème : erreurs
- Niveau : 1
- Définition : `r.raise_for_status()` lève `httpx.HTTPStatusError` si le statut n'est pas 2xx, et renvoie la réponse sinon, ce qui permet de chaîner.
- Contexte : C'est le `if (!res.ok) throw` de `fetch`, en une ligne. L'exception porte `e.response` et `e.request` : statut, en-têtes (`Retry-After`) et corps restent lisibles pour décider (réessayer un 429, lever sur un 400). Chez httpx, toute réponse hors 2xx lève, redirections 3xx comprises. `raise_for_status` renvoie `r` : `c.get(url).raise_for_status().json()`.
- Usage : ✅ juste après chaque appel dont le corps est utilisé · ❌ statuts qu'on traite différemment (429 réessayé, 404 = absent) : tester `r.status_code` avant.

```python
# Exemple 1 : un 404 lève
import httpx
t = httpx.MockTransport(lambda req:
    httpx.Response(404))
with httpx.Client(transport=t) as c:
    r = c.get("https://bodacc.test/x")
r.raise_for_status()  # ❌ HTTPStatusError
```

```python
# Exemple 2 : lire le statut dans l'erreur
import httpx

t = httpx.MockTransport(lambda req:
    httpx.Response(429))
c = httpx.Client(transport=t)
try:
    c.get("https://b.t").raise_for_status()
except httpx.HTTPStatusError as e:
    code = e.response.status_code
code   # → 429
```

- Quiz : Que fait `raise_for_status()` sur un `301` (redirection non suivie) ?
- [ ] Rien : 3xx n'est pas une erreur
- [x] Lève `HTTPStatusError`
- [ ] Suit la redirection
- [ ] Lève `TooManyRedirects`
- Réponse : Lève `HTTPStatusError` : httpx ne tolère que les 2xx ; une redirection non suivie est signalée comme une erreur.

## 5. json=, data=, content= : le corps envoyé
- Sous-thème : client
- Niveau : 1
- Définition : `json=` sérialise un objet en JSON, `data=` encode un formulaire, `content=` envoie des octets bruts ; chacun pose le bon `Content-Type`.
- Contexte : `json={…}` évite le `JSON.stringify` + en-tête à la main : httpx sérialise et pose `application/json`. `data={…}` donne `application/x-www-form-urlencoded`, comme un formulaire HTML. `content=b"…"` envoie tel quel, sans en-tête de type. La sérialisation passe par `json.dumps` : `date`, `Decimal` ou un modèle pydantic doivent être convertis avant (`model_dump(mode="json")`).
- Usage : ✅ API JSON : `json=` ; formulaire OAuth : `data=` ; fichier ou corps déjà sérialisé : `content=` · ❌ `data=json.dumps(x)` : mauvais `Content-Type`, et `data=` en chaîne est déprécié.

```python
# Exemple 1 : json= sérialise et type
import httpx
q = httpx.Request("POST", "https://b.t",
    json={"siren": "483609327"})
q.headers["content-type"]
# → "application/json"
q.content  # → b'{"siren":"483609327"}'
```

```python
# Exemple 2 : data= : un formulaire
import httpx

q = httpx.Request("POST", "https://b.t",
    data={"siren": "483609327"})
q.content   # → b"siren=483609327"
q.headers["content-type"]
# → "application/x-www-form-urlencoded"
```

- Quiz : Que fait `json={"jour": date(2026, 10, 23)}` ?
- [ ] Envoie `"2026-10-23"`
- [ ] Envoie un timestamp
- [x] Lève `TypeError`
- [ ] Lève `ValueError`
- Réponse : `TypeError` (Object of type date is not JSON serializable) : httpx passe par `json.dumps`, qui ne connaît pas `date` ; envoyer `d.isoformat()`.

## 6. headers : insensibles à la casse
- Sous-thème : réponses
- Niveau : 1
- Définition : `r.headers` est un dict insensible à la casse : `r.headers["content-type"]` et `["Content-Type"]` lisent la même valeur, toujours une `str`.
- Contexte : HTTP ne distingue pas la casse des noms d'en-têtes, et HTTP/2 les envoie en minuscules : ne jamais comparer à la main. Les valeurs sont des chaînes, à convertir (`int(...)` pour `Retry-After` ou `X-RateLimit-Remaining`). Comme pour un dict, `[...]` lève sur un en-tête absent ; `.get(nom, défaut)` est la lecture sûre pour un en-tête optionnel.
- Usage : ✅ `.get()` pour les en-têtes optionnels (`Retry-After`, quotas), conversion explicite en `int` · ❌ `r.headers["Retry-After"]` sans test : `KeyError` sur la réponse qui n'en a pas.

```python
# Exemple 1 : la casse ne compte pas
import httpx
r = httpx.Response(200, headers={
    "X-RateLimit-Remaining": "4999"})
r.headers["x-ratelimit-remaining"]
# → "4999"
r.headers.get("Retry-After")  # → None
```

```python
# Exemple 2 : une valeur str à convertir
import httpx

r = httpx.Response(429,
    headers={"Retry-After": "7"})
s = r.headers.get("retry-after", "1")
int(s)    # → 7
```

- Quiz : Sur une réponse sans cet en-tête, que fait `r.headers["Retry-After"]` ?
- [ ] Renvoie `None`
- [x] Lève `KeyError`
- [ ] Renvoie `""`
- [ ] Renvoie `0`
- Réponse : `KeyError` : comme un dict, `[...]` lève sur une clé absente ; `.get("retry-after")` renvoie `None`.

## 7. client.stream : lire ligne à ligne
- Sous-thème : streaming
- Niveau : 2
- Définition : `with client.stream("GET", url) as r:` puis `r.iter_lines()` lit le corps au fil de l'eau, sans le charger en mémoire (≈ `ReadableStream` lu par morceaux).
- Contexte : `client.get` télécharge tout le corps avant de rendre la main : 59 Mo pour une journée BODACC. `stream` rend la réponse dès les en-têtes ; le corps arrive pendant l'itération, et le `with` ferme la connexion à la sortie. `r.json()` attend un seul document : sur du JSONL, même servi en `application/json`, il lève `JSONDecodeError`.
- Usage : ✅ export JSONL, gros fichier, réponse longue traitée ligne à ligne · ❌ petite réponse JSON : `client.get(...).json()` suffit.

```python
# Exemple 1 : JSONL ligne à ligne
import json, httpx
corps = '{"id": "A1"}\n\n{"id": "A2"}\n'
t = httpx.MockTransport(lambda req:
    httpx.Response(200, text=corps))
c = httpx.Client(transport=t)
with c.stream("GET", "https://b.t") as r:
    ids = [json.loads(l)["id"]
           for l in r.iter_lines() if l]
ids   # → ["A1", "A2"]
```

- Quiz : Dans l'exemple 1, que donne la compréhension sans le `if l` ?
- [ ] `["A1", "A2"]`
- [ ] `["A1", None, "A2"]`
- [x] `JSONDecodeError`
- [ ] `KeyError`
- Réponse : `JSONDecodeError` : `iter_lines()` rend aussi la ligne vide `""`, que `json.loads` refuse ; filtrer avant de décoder.

## 8. exceptions : HTTPStatusError ou TransportError
- Sous-thème : erreurs
- Niveau : 2
- Définition : httpx lève deux familles sous `httpx.HTTPError` : `TransportError` (réseau, timeouts : pas de réponse) et `HTTPStatusError` (réponse reçue, statut d'erreur, via `raise_for_status`).
- Contexte : `TransportError` regroupe `ConnectError`, `ReadError`, `ConnectTimeout`, `ReadTimeout` (ces deux sous `TimeoutException`) : on n'a pas de réponse, on peut réessayer. `HTTPStatusError` n'apparaît que si on appelle `raise_for_status()` ; elle porte la réponse, pour trier 429 et 5xx (réessayer) de 4xx (lever). C'est le tri de `fetch_day` : `except httpx.TransportError` d'un côté, statut testé de l'autre.
- Usage : ✅ attraper la famille dont on traite le cas (`TransportError` pour un retry réseau) · ❌ `except httpx.HTTPError` partout : un 400 permanent serait réessayé comme une coupure.

```python
# Exemple 1 : la hiérarchie
from httpx import (ReadTimeout, ConnectError,
    TransportError, HTTPStatusError, HTTPError)
issubclass(ReadTimeout, TransportError)
# → True
issubclass(ConnectError, TransportError)
# → True
issubclass(HTTPStatusError, TransportError)
# → False
```

```python
# Exemple 2 : trier pour réessayer
import httpx

def a_reessayer(e):
    if isinstance(e, httpx.TransportError):
        return True        # réseau, timeout
    if isinstance(e, httpx.HTTPStatusError):
        s = e.response.status_code
        return s == 429 or s >= 500
    return False

a_reessayer(httpx.ReadTimeout("lent"))
# → True
```

- Quiz : Le serveur répond `503`. Un `except httpx.TransportError:` autour de `c.get(url)` s'exécute-t-il ?
- [ ] Oui : un 503 est une erreur réseau
- [ ] Oui, mais seulement avec `retries`
- [x] Non : aucune exception n'est levée
- [ ] Non : c'est `HTTPStatusError` qui part
- Réponse : Non, rien n'est levé : un 503 est une réponse reçue ; seul `raise_for_status()` lèverait, et ce serait `HTTPStatusError`.

## 9. follow_redirects : désactivé par défaut
- Sous-thème : réponses
- Niveau : 2
- Définition : httpx ne suit pas les redirections par défaut (≠ `fetch`, ≠ `requests`) : un 301 ou 302 est rendu tel quel, sauf avec `follow_redirects=True`.
- Contexte : Venant de `fetch`, on s'attend à recevoir la page finale ; httpx rend la redirection elle-même, avec l'en-tête `Location`, et `raise_for_status()` la traite comme une erreur. L'option se règle sur le client ou par appel. Une fois suivies, les réponses intermédiaires sont dans `r.history` et `r.url` donne l'URL finale. Le nombre de sauts est plafonné (20).
- Usage : ✅ `follow_redirects=True` pour une API qui redirige (http → https, ancien chemin) · ❌ l'activer pour masquer une URL de base fausse : corriger la `base_url`.

```python
# Exemple 1 : la redirection est rendue
import httpx
def srv(req):
    if req.url.path == "/a":
        return httpx.Response(302,
            headers={"Location": "/b"})
    return httpx.Response(200, text="ok")
t = httpx.MockTransport(srv)
c = httpx.Client(transport=t,
    base_url="https://b.t")
c.get("/a").status_code    # → 302
c.get("/a", follow_redirects=True).text
# → "ok"
```

```python
# Exemple 2 : l'historique des sauts
import httpx

def srv(req):
    if req.url.path == "/a":
        return httpx.Response(302,
            headers={"Location": "/b"})
    return httpx.Response(200)

c = httpx.Client(base_url="https://b.t",
    transport=httpx.MockTransport(srv),
    follow_redirects=True)
r = c.get("/a")
(str(r.url), len(r.history))
# → ("https://b.t/b", 1)
```

- Quiz : Avec `follow_redirects=True`, un serveur redirige `/a` vers `/a` sans fin. Que fait `c.get("/a")` ?
- [x] Lève `TooManyRedirects`
- [ ] Lève `RecursionError`
- [ ] Renvoie le dernier `302`
- [ ] Boucle indéfiniment
- Réponse : `TooManyRedirects` : httpx suit au plus 20 redirections (`max_redirects`), puis lève.

## 10. timeout : par appel
- Sous-thème : client
- Niveau : 2
- Définition : `c.get(url, timeout=…)` remplace le timeout du client pour un seul appel ; un dépassement lève une sous-classe de `httpx.TimeoutException`.
- Contexte : Le client porte le réglage par défaut ; un appel exceptionnel (export d'une journée) peut le surcharger sans créer un autre client. Le timeout de lecture n'est pas une durée totale : c'est l'attente maximale **entre deux paquets reçus**. Un flux qui envoie un peu de données régulièrement ne déclenche jamais `ReadTimeout`, même s'il dure dix minutes ; la durée totale se borne ailleurs (timeout de la Lambda).
- Usage : ✅ timeout court par défaut sur le client, plus long sur l'appel lent connu · ❌ croire que `timeout=60` borne la durée totale d'un téléchargement en flux.

```python
# Exemple 1 : surcharger pour un appel
import httpx
c = httpx.Client(timeout=5)
q = c.build_request("GET", "https://b.t",
    timeout=60)
q.extensions["timeout"]["read"]  # → 60
```

```python
# Exemple 2 : attraper le dépassement
import httpx

def lent(req):
    raise httpx.ReadTimeout("lent",
        request=req)

c = httpx.Client(
    transport=httpx.MockTransport(lent))
try:
    c.get("https://b.t", timeout=1)
except httpx.TimeoutException as e:
    nom = type(e).__name__
nom      # → "ReadTimeout"
```

- Quiz : Avec `timeout=60`, un export envoie une ligne toutes les 10 s pendant 5 min. Que se passe-t-il ?
- [ ] `ReadTimeout` au bout de 60 s
- [x] Il se termine sans timeout
- [ ] `ConnectTimeout` au bout de 60 s
- [ ] `PoolTimeout` au bout de 60 s
- Réponse : Il se termine : le timeout de lecture borne l'attente entre deux paquets (ici 10 s), pas la durée totale (doc httpx, « Timeouts »).

## 11. base_url : le chemin est conservé
- Sous-thème : client
- Niveau : 2
- Définition : Avec `httpx.Client(base_url=…)`, un chemin relatif, même commençant par `/`, est ajouté au chemin de la base, pas à la racine du domaine.
- Contexte : httpx ajoute toujours un `/` final à la base, puis colle le chemin : `base_url=".../annonces-commerciales"` + `"/records"` donne `.../annonces-commerciales/records`, ce qu'attend `BodaccClient`. C'est l'inverse de `urljoin` et de `new URL("/records", base)` en JS, où un chemin en `/` repart de la racine. Une URL absolue passée à l'appel ignore la base.
- Usage : ✅ `base_url` = racine de l'API avec son préfixe de version, chemins courts dans les appels · ❌ construire les URL avec `urljoin` en croyant obtenir le même résultat.

```python
# Exemple 1 : la base garde son chemin
import httpx
c = httpx.Client(
    base_url="https://b.t/api/v2.1")
q = c.build_request("GET", "/records")
str(q.url)
# → "https://b.t/api/v2.1/records"
```

```python
# Exemple 2 : une URL absolue l'ignore
import httpx

c = httpx.Client(base_url="https://b.t/api")
q = c.build_request("GET", "https://autre.t/x")
str(q.url)   # → "https://autre.t/x"
```

- Quiz : Que renvoie `urllib.parse.urljoin("https://b.t/api", "/records")` ?
- [ ] `"https://b.t/api/records"`
- [x] `"https://b.t/records"`
- [ ] `"https://b.t/api//records"`
- [ ] `ValueError`
- Réponse : `"https://b.t/records"` : pour `urljoin` (comme `new URL` en JS), un chemin qui commence par `/` repart de la racine ; httpx, lui, le colle à la base.

## 12. MockTransport : un faux serveur
- Sous-thème : tests
- Niveau : 2
- Définition : `httpx.MockTransport(handler)` remplace le réseau d'un client par une fonction : elle reçoit la `Request` et renvoie une `Response`, ou lève.
- Contexte : Le transport est la couche qui envoie vraiment les octets ; le remplacer garde tout le reste du client réel (params, en-têtes, `base_url`, hooks). Le handler voit la requête construite, donc on peut vérifier ce qui part. Lever `httpx.ConnectError(…, request=req)` simule une coupure. Il ne touche que le client qui le reçoit : d'où l'injection d'un `http=` dans `BodaccClient`.
- Usage : ✅ tests unitaires d'un client injectable, exemples sans réseau · ❌ code qui crée son propre client en interne, impossible à injecter : `respx`, qui intercepte globalement.

```python
# Exemple 1 : une fonction = un serveur
import httpx
def serveur(req):
    return httpx.Response(200,
        json={"path": req.url.path})
c = httpx.Client(transport=
    httpx.MockTransport(serveur))
c.get("https://b.t/records").json()
# → {"path": "/records"}
```

```python
# Exemple 2 : simuler une coupure
import httpx

def coupe(req):
    raise httpx.ConnectError("dns",
        request=req)

c = httpx.Client(transport=
    httpx.MockTransport(coupe))
c.get("https://b.t")   # ❌ ConnectError
```

- Quiz : Un test injecte un `MockTransport` dans `c`. Ailleurs, le code appelle `httpx.get(url)`. Où part cet appel ?
- [ ] Vers le `MockTransport` aussi
- [x] Sur le vrai réseau
- [ ] Nulle part : `RuntimeError`
- [ ] Vers le dernier client créé
- Réponse : Sur le vrai réseau : le transport n'appartient qu'au client qui l'a reçu ; `httpx.get` crée un client neuf, avec le transport par défaut.

## 13. respx : router selon la requête
- Sous-thème : tests
- Niveau : 2
- Définition : `respx.get(URL, params=…)` crée une route qui ne répond qu'aux requêtes correspondantes ; `route.calls.last.request` montre ce qui est parti.
- Contexte : Sous `respx.mock`, chaque requête httpx est comparée aux routes dans l'ordre de déclaration : la première qui correspond répond, une requête sans route lève `AllMockedAssertionError`. Le filtre `params=` est une inclusion : la requête doit contenir ces paires, d'autres peuvent s'ajouter. `.respond(…)` est le raccourci de `.mock(return_value=…)`. Le scénario multi-réponses (`side_effect`) est dans le thème Tests.
- Usage : ✅ vérifier le filtre `where`, le `User-Agent` ou la pagination envoyés · ❌ client injectable dans un test simple : `MockTransport`, sans dépendance de plus.

```python
# Exemple 1 : une route par filtre
import httpx, respx
URL = "https://bodacc.test/records"
with respx.mock:
    respx.get(URL, params={"where": "a"}
        ).respond(json={"n": 1})
    respx.get(URL).respond(json={"n": 0})
    r = httpx.get(URL, params={"where": "a"})
r.json()   # → {"n": 1}
```

```python
# Exemple 2 : inspecter la requête partie
import httpx, respx

URL = "https://bodacc.test/records"
with respx.mock:
    route = respx.get(URL).respond(200)
    httpx.get(URL, params={"limit": "1"},
        headers={"User-Agent": "dp/0.1"})
    req = route.calls.last.request
p = req.url.params["limit"]
ua = req.headers["user-agent"]
(p, ua)    # → ("1", "dp/0.1")
```

- Quiz : Route `params={"where": "a"}`, requête `?where=a&limit=1`. La route répond-elle ?
- [x] Oui : les params en plus sont tolérés
- [ ] Non : `AllMockedAssertionError`
- [ ] Non : réponse `404`
- [ ] Oui, si `strict=False`
- Réponse : Oui : le filtre `params` vérifie que ces paires sont présentes, pas qu'elles sont les seules.

## 14. AsyncClient : async with et await
- Sous-thème : async
- Niveau : 2
- Définition : `httpx.AsyncClient` a la même API que `Client`, mais chaque appel est une coroutine à `await`, et il s'ouvre avec `async with`.
- Contexte : Utile quand on veut lancer plusieurs requêtes en même temps dans un seul thread (boucle `asyncio`). Tout se fait dans une `async def`, lancée par `asyncio.run(...)`. Oublier `await` ne lève rien sur le moment : `r` est une coroutine, et `r.status_code` lève `AttributeError` plus loin. Un `with` simple sur un `AsyncClient` lève `TypeError`.
- Usage : ✅ beaucoup d'appels indépendants (une requête par SIREN), framework async (FastAPI) · ❌ un seul appel séquentiel dans une Lambda : `Client` synchrone, plus simple à lire et à tester.

```python
# Exemple 1 : async with, await
import asyncio, httpx
t = httpx.MockTransport(lambda req:
    httpx.Response(200, json={"n": 1}))
async def main():
    async with httpx.AsyncClient(
            transport=t) as c:
        r = await c.get("https://b.t")
    return r.json()
asyncio.run(main())   # → {"n": 1}
```

```python
# Exemple 2 : sans await, une coroutine
import asyncio, httpx

t = httpx.MockTransport(lambda req:
    httpx.Response(200))

async def main():
    async with httpx.AsyncClient(
            transport=t) as c:
        r = c.get("https://b.t")  # oubli
        nom = type(r).__name__
        await r
    return nom

asyncio.run(main())   # → "coroutine"
```

- Quiz : Que fait `with httpx.AsyncClient() as c:` (sans `async`) dans une `async def` ?
- [ ] Fonctionne comme `async with`
- [x] Lève `TypeError`
- [ ] Lève `SyntaxError`
- [ ] Ouvre un client synchrone
- Réponse : `TypeError` (does not support the context manager protocol) : `AsyncClient` n'a que `__aenter__` / `__aexit__`.

## 15. Client fermé : plus d'appel
- Sous-thème : client
- Niveau : 2
- Définition : Après `close()` ou la sortie du `with`, un `httpx.Client` refuse tout appel (`RuntimeError`) : il faut en créer un nouveau.
- Contexte : Fermer libère le pool de connexions ; le client ne se rouvre jamais. D'où deux formes en Lambda : un client par invocation dans un `with`, ou un client global créé à froid et jamais fermé, réutilisé par les invocations suivantes du même conteneur (connexion TLS gardée). `c.is_closed` dit dans quel état il est.
- Usage : ✅ Lambda : client au niveau module, réutilisé à chaud ; script : un `with` autour de tout le travail · ❌ fermer un client partagé dans une fonction qui ne l'a pas créé.

```python
# Exemple 1 : après le with, plus d'appel
import httpx
t = httpx.MockTransport(lambda req:
    httpx.Response(200))
with httpx.Client(transport=t) as c:
    c.get("https://b.t")
c.is_closed            # → True
c.get("https://b.t")   # ❌ RuntimeError
```

```python
# Exemple 2 : un client par conteneur Lambda
import httpx

HTTP = httpx.Client(timeout=60)  # à froid

def handler(event, context):
    return HTTP.is_closed

handler({}, None)   # → False
handler({}, None)   # → False  (le même)
```

- Quiz : Que fait un second `with c:` sur un client déjà fermé ?
- [ ] Rouvre le pool de connexions
- [x] Lève `RuntimeError`
- [ ] Ne fait rien
- [ ] Lève `ValueError`
- Réponse : `RuntimeError` (Cannot reopen a client instance) : un client fermé ne se rouvre pas, ni par `with` ni par un appel.

## 16. stream : le with dans le générateur
- Sous-thème : streaming
- Niveau : 3
- Définition : Dans un générateur qui streame, le `with client.stream(...)` doit être dans le générateur, sinon la réponse est fermée avant la première ligne.
- Contexte : Un `return (gen…)` depuis un `with` quitte le bloc tout de suite : `__exit__` ferme le flux, puis l'appelant itère sur une réponse fermée → `httpx.StreamClosed`. Avec `yield` dans le `with`, la fonction se met en pause **dans** le bloc : la connexion reste ouverte tant que l'appelant itère et se ferme à la fin du flux. Effet secondaire : aucune requête ne part avant le premier `next`.
- Usage : ✅ `fetch_day` : `with c.stream(...) as r:` puis `for l in r.iter_lines(): yield …` · ❌ renvoyer une expression génératrice construite dans le `with` ; ouvrir le flux chez l'appelant pour le passer.

```python
# Exemple 1 : return dans le with = fermé
import httpx
def corps():                  # vrai flux
    yield b'{"id": "A1"}\n'
t = httpx.MockTransport(lambda req:
    httpx.Response(200, content=corps()))
c = httpx.Client(transport=t)
URL = "https://bodacc.test"
def lire():
    with c.stream("GET", URL) as r:
        return (l for l in r.iter_lines())
list(lire())   # ❌ StreamClosed
```

```python
# Exemple 2 : yield dans le with
import httpx, json
appels = []
def serveur(req):
    appels.append(req.url.path)
    return httpx.Response(200,
        text='{"id": "A1"}\n')
t = httpx.MockTransport(serveur)
c = httpx.Client(transport=t)
URL = "https://bodacc.test/e"
def fetch_day():
    with c.stream("GET", URL) as r:
        for l in r.iter_lines():
            yield json.loads(l)
g = fetch_day()
appels       # → []  (aucune requête)
next(g)      # → {"id": "A1"}
appels       # → ["/e"]
```

- Quiz : Où l'appelant de `fetch_day` met-il son `try/except httpx.HTTPError` ?
- [ ] Autour de `g = fetch_day()`
- [x] Autour de la boucle `for a in g:`
- [ ] Nulle part : le `with` l'attrape
- [ ] Dans `__exit__` du client
- Réponse : autour de la boucle : l'appel ne fait rien ; la requête, et donc ses erreurs (429, timeout, coupure), partent pendant l'itération.

## 17. HTTPTransport(retries=) : la connexion seule
- Sous-thème : erreurs
- Niveau : 3
- Définition : `httpx.HTTPTransport(retries=n)` réessaie jusqu'à `n` fois l'**établissement de la connexion** (`ConnectError`, `ConnectTimeout`) ; jamais un statut 429 ou 5xx, ni une lecture coupée.
- Contexte : Ces retries sont sûrs parce qu'aucune requête n'est encore partie. Tout ce qui suit, un 503 reçu, un `ReadTimeout`, un flux coupé, reste à la charge du code : boucle de retry avec backoff et `Retry-After`, comme `fetch_day`. Les tentatives sont espacées d'un petit backoff exponentiel (0,5 s, 1 s…). Le transport se passe au client par `transport=`.
- Usage : ✅ `retries=2` ou `3` contre les coupures DNS ou TCP passagères · ❌ compter dessus pour un 429 de quota ou un 503 : retry applicatif.

```python
# Exemple 1 : le réglage
import httpx
t = httpx.HTTPTransport(retries=3)
c = httpx.Client(transport=t,
    timeout=httpx.Timeout(60, connect=5))
# ConnectError, ConnectTimeout : réessayés
# 429, 503, ReadTimeout : jamais
c.is_closed   # → False
```

```python
# Exemple 2 : un 503 n'est vu qu'une fois
import http.server, threading, httpx
vus = []
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        vus.append(1)
        self.send_response(503)
        self.end_headers()
    def log_message(self, *a):
        pass
s = http.server.HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=s.serve_forever,
                 daemon=True).start()
url = f"http://127.0.0.1:{s.server_port}/"
t = httpx.HTTPTransport(retries=3)
httpx.Client(transport=t).get(url).status_code
# → 503
len(vus)   # → 1
```

- Quiz : Avec `retries=3` et un serveur injoignable, combien de tentatives de connexion au plus ?
- [ ] `3`
- [x] `4`
- [ ] `1`
- [ ] Sans limite
- Réponse : `4` : la tentative initiale plus 3 nouveaux essais ; ensuite `ConnectError` remonte.

## 18. event_hooks : agir sur chaque échange
- Sous-thème : client
- Niveau : 3
- Définition : `event_hooks={"request": [f], "response": [g]}` appelle `f(request)` avant chaque envoi et `g(response)` à chaque réponse reçue, pour tout le client.
- Contexte : Un point unique pour journaliser, mesurer ou lever : `raise_for_status` dans un hook de réponse applique la règle à tous les appels. Le hook de réponse tourne dès les en-têtes, avant la lecture du corps : sur un flux, `r.text` lève `ResponseNotRead` (appeler `r.read()` avant). Sans réponse (coupure réseau), il n'est pas appelé : l'exception remonte directement.
- Usage : ✅ log structuré de chaque appel (méthode, chemin, statut, durée), `raise_for_status` systématique · ❌ logique métier ou retry dans un hook : difficile à suivre, la mettre dans le client.

```python
# Exemple 1 : journaliser chaque échange
import httpx
log = []
def req(r):
    log.append(f"{r.method} {r.url.path}")
def resp(r):
    log.append(r.status_code)
t = httpx.MockTransport(lambda r:
    httpx.Response(429))
c = httpx.Client(transport=t, event_hooks={
    "request": [req], "response": [resp]})
c.get("https://b.t/e")
log    # → ["GET /e", 429]
```

```python
# Exemple 2 : lever pour tous les appels
import httpx

def lever(r):
    r.raise_for_status()

t = httpx.MockTransport(lambda r:
    httpx.Response(503))
c = httpx.Client(transport=t,
    event_hooks={"response": [lever]})
c.get("https://b.t")   # ❌ HTTPStatusError
```

- Quiz : Le transport lève `ConnectError`. Le hook `response` est-il appelé ?
- [ ] Oui, avec `None`
- [x] Non
- [ ] Oui, avec un statut `0`
- [ ] Oui, avec un statut `503`
- Réponse : Non : aucun échange n'a eu lieu, il n'y a pas de réponse à passer ; seul le hook `request` a tourné, puis `ConnectError` remonte.

## 19. stream : read() avant text
- Sous-thème : streaming
- Niveau : 3
- Définition : Dans `client.stream(...)`, le corps n'est pas chargé : `r.text` ou `r.json()` lèvent `ResponseNotRead` tant que `r.read()` n'a pas été appelé.
- Contexte : Le flux sert à lire au fil de l'eau ; httpx refuse donc d'en tout charger en douce. Pour un statut d'erreur, le corps est petit et utile au diagnostic : `r.read()` le charge, puis `r.text` et `r.json()` marchent. C'est ce que fait `_error_for` de `BodaccClient`. Un flux ne se lit qu'une fois : itérer deux fois sans `read()` lève `StreamConsumed`.
- Usage : ✅ dans le `with stream`, `r.read()` avant de lire le corps d'un 4xx ou 5xx · ❌ `r.text` sur un flux de 59 Mo : `iter_lines()`, sinon tout est chargé en mémoire.

```python
# Exemple 1 : le corps n'est pas lu
import httpx
def corps():
    yield b'{"error_code": "X"}'
t = httpx.MockTransport(lambda req:
    httpx.Response(400, content=corps()))
c = httpx.Client(transport=t)
with c.stream("GET", "https://b.t") as r:
    r.text     # ❌ ResponseNotRead
```

```python
# Exemple 2 : read() puis le corps d'erreur
import httpx

def corps():
    yield b'{"error_code": "X"}'

t = httpx.MockTransport(lambda req:
    httpx.Response(400, content=corps()))
c = httpx.Client(transport=t)
with c.stream("GET", "https://b.t") as r:
    if r.is_error:
        r.read()          # charge le corps
        err = r.json()["error_code"]
err    # → "X"
```

- Quiz : Dans le `with stream`, sans `read()`, que fait un second `for l in r.iter_lines():` ?
- [ ] Relit depuis le début
- [ ] Ne fait aucun tour
- [x] Lève `StreamConsumed`
- [ ] Lève `ResponseNotRead`
- Réponse : `StreamConsumed` : les octets ont déjà été consommés par la première boucle ; seul `r.read()` les garde en mémoire pour une relecture.

## 20. asyncio.gather : appels concurrents
- Sous-thème : async
- Niveau : 3
- Définition : `await asyncio.gather(*coros)` lance plusieurs requêtes d'un même `AsyncClient` en même temps et rend leurs résultats dans l'ordre des arguments.
- Contexte : Les requêtes avancent en parallèle pendant les attentes réseau, dans un seul thread : dix appels de 1 s prennent environ 1 s. Un seul client partagé réutilise le pool de connexions. Sans limite, mille coroutines ouvrent mille requêtes : un `asyncio.Semaphore` borne la concurrence pour respecter le quota. Par défaut, la première exception remonte à l'`await` ; `return_exceptions=True` les rend dans la liste.
- Usage : ✅ appels indépendants nombreux (une fiche par SIREN), borné par un `Semaphore` · ❌ pages qui dépendent de la précédente (keyset, curseur) : séquentiel ; une seule requête : `Client` synchrone.

```python
# Exemple 1 : trois jours en parallèle
import asyncio, httpx
def srv(req):
    j = req.url.params["j"]
    return httpx.Response(200, json={"j": j})
t = httpx.MockTransport(srv)
async def main(jours):
    async with httpx.AsyncClient(
            transport=t) as c:
        rs = await asyncio.gather(*(
            c.get("https://b.t", params={"j": j})
            for j in jours))
    return [r.json()["j"] for r in rs]
asyncio.run(main(["22", "23", "24"]))
# → ["22", "23", "24"]
```

```python
# Exemple 2 : borner avec un Semaphore
import asyncio

actifs, pic = [0], [0]

async def appel(sem, i):
    async with sem:
        actifs[0] += 1
        pic[0] = max(pic[0], actifs[0])
        await asyncio.sleep(0.01)
        actifs[0] -= 1
    return i

async def main():
    sem = asyncio.Semaphore(2)
    return await asyncio.gather(
        *(appel(sem, i) for i in range(5)))

asyncio.run(main())   # → [0, 1, 2, 3, 4]
pic[0]                # → 2
```

- Quiz : Un des trois appels lève `ValueError`, sans `return_exceptions`. Que fait `await asyncio.gather(...)` ?
- [ ] Renvoie les deux résultats valides
- [x] Lève `ValueError`
- [ ] Renvoie la liste avec l'exception dedans
- [ ] Rejoue l'appel en échec
- Réponse : Lève `ValueError` : la première exception remonte à l'`await` ; avec `return_exceptions=True`, elle serait placée dans la liste des résultats.
