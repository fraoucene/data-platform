---
type: glossaire
langage: Python
updated: 2026-10-26
---

# Glossaire Python

## ABC
- Définition : Abstract Base Class : classe de base (module `abc`) qui déclare des méthodes abstraites que toute sous-classe doit implémenter (≈ classe `abstract` en TS).
- Exemple : `class Source(ABC)` avec `@abstractmethod def lire()` : instancier une source BODACC sans `lire` lève `TypeError`.
- Alias : classe abstraite, Abstract Base Class
- Carte : classes-abstractmethod-contrat

## ABI
- Définition : Application Binary Interface : conventions binaires entre du code compilé et l'interpréteur ; un module compilé pour une version de Python ne charge pas sous une autre.
- Exemple : Le tag `cp312-cp312` d'un wheel de pydantic-core dit : compilé pour l'ABI de CPython 3.12.
- Alias : Application Binary Interface
- Carte : packaging-tags-wheel-plateforme

## AES
- Définition : Advanced Encryption Standard : algorithme de chiffrement symétrique (la même clé chiffre et déchiffre) ; AES-256 utilise une clé de 256 bits.
- Exemple : Une clé de données KMS est une clé AES-256 : elle chiffre le fichier localement, puis on jette sa version en clair.
- Alias : AES-256, Advanced Encryption Standard

## annotation de type
- Définition : Indication de type écrite après un nom (`x: int`, `-> str`), lue par l'éditeur et mypy mais jamais vérifiée par Python à l'exécution.
- Exemple : `def normaliser(sirens: list[str]) -> list[str]` : passer `[1, 2]` ne lève rien, seul mypy le signale.
- Alias : annotations de type, annotation, annotations, type hint
- Carte : listes-annotation-non-controlee

## argparse
- Définition : Module standard qui déclare les options d'un script en ligne de commande, les convertit et génère l'aide et les messages d'erreur (≈ yargs).
- Exemple : `replay.py --from 2026-10-01 --to 2026-10-19` : argparse rend `args.start` et `args.end` déjà en `date`.
- Carte : ligne-de-commande-argparse-options

## *args
- Définition : Paramètre qui ramasse les arguments positionnels en trop dans un tuple ; à l'appel, `f(*l)` déplie une liste en arguments.
- Exemple : `def uv(*args): run(["uv", *args])` accepte n'importe quel nombre d'arguments pour la commande uv.
- Alias : args
- Carte : decorateurs-args-kwargs

## argument nommé
- Définition : Argument passé avec le nom du paramètre (`f(jour="2026-10-20")`), indépendant de sa position ; un paramètre après `*` doit l'être.
- Exemple : `PartStats(count=3, sha256=h)` se lit sans connaître l'ordre des champs.
- Alias : arguments nommés, keyword argument
- Carte : classes-dataclass-kw-only

## argument positionnel
- Définition : Argument passé par sa place dans l'appel (`f(1, 2)`) ; pour argparse, une valeur lue par sa position, sans `--option`.
- Exemple : `PartStats(3, "ab", 120, 40)` est positionnel : inverser deux tailles ne lève aucune erreur.
- Alias : arguments positionnels, positionnel
- Carte : ligne-de-commande-positionnel-vs-option

## ASCII
- Définition : Jeu de 128 caractères de base (lettres sans accent, chiffres, ponctuation), chacun codé sur un octet ; ses textes sont identiques en UTF-8.
- Exemple : `json.dumps("é")` écrit `"é"`, pur ASCII, tant qu'on ne passe pas `ensure_ascii=False`.
- Carte : json-ensure-ascii-accents

## assert
- Définition : Instruction qui lève `AssertionError` si la condition est fausse ; pytest l'utilise comme seul outil de vérification des tests.
- Exemple : `assert stats == PartStats(count=3, ...)` : en échec, pytest affiche le champ qui diffère.
- Carte : tests-assert-introspection

## async with
- Définition : Forme asynchrone de `with` : elle attend (`await`) l'ouverture et la fermeture d'une ressource, dans une fonction `async def`.
- Exemple : `async with httpx.AsyncClient() as c:` ouvre puis ferme proprement un client HTTP asynchrone.
- Carte : context-managers-async-with

## asynchrone
- Définition : Style de code où une fonction `async def` se met en pause sur une attente (réseau, disque) pour laisser tourner d'autres tâches dans le même thread.
- Exemple : Dix requêtes HTTP asynchrones d'une seconde chacune prennent environ une seconde au total.
- Alias : async, async def
- Carte : http-asyncclient-await

## asyncio
- Définition : Module standard qui fait tourner les coroutines (`async def`) : boucle d'événements, `asyncio.run`, `gather`, verrous et files asynchrones.
- Exemple : `asyncio.run(main())` lance le programme asynchrone ; `asyncio.gather` attend plusieurs requêtes à la fois.
- Carte : http-asyncio-gather

## atomique
- Définition : Se dit d'une opération qui a lieu en entier ou pas du tout : aucun lecteur ne voit un état à moitié fait.
- Exemple : Écrire `etat.tmp` puis `os.replace` vers `etat.json` : un lecteur voit l'ancien fichier ou le nouveau, jamais un fichier tronqué.
- Alias : écriture atomique, atomicité
- Carte : context-managers-ecriture-atomique

## attribut
- Définition : Valeur rattachée à un objet et lue avec un point (`obj.nom`) ; les clés d'un dict, elles, se lisent avec `d["nom"]`.
- Exemple : `annonce.siren` lit un attribut ; sur un dict JSON brut, `d.siren` lève `AttributeError`.
- Alias : attributs
- Carte : dictionnaires-pas-acces-par-point

## await
- Définition : Mot-clé qui attend le résultat d'une coroutine ; sans lui, on récupère la coroutine elle-même, pas son résultat.
- Exemple : `r = await c.get(url)` ; oublier `await` donne une coroutine, et `r.status_code` lève `AttributeError`.
- Carte : http-asyncclient-await

## backend de build
- Définition : Outil déclaré dans `[build-system]` de `pyproject.toml` qui fabrique le wheel et le sdist d'un paquet (`uv_build`, setuptools, hatchling).
- Exemple : `uv init --lib` écrit `build-backend = "uv_build"` : `dp-common` devient installable et importable.
- Alias : build-system, build backend
- Carte : packaging-build-system-virtuel

## base64
- Définition : Encodage qui écrit des octets quelconques avec 64 caractères imprimables, 4 caractères pour 3 octets ; transporte du binaire dans du texte.
- Exemple : S3 attend `ChecksumSHA256` en base64 des 32 octets du sha256 : 44 caractères, pas les 64 de l'hexadécimal.
- Carte : hachage-base64-ou-hex-s3

## BaseException
- Définition : Classe racine de toutes les exceptions ; `KeyboardInterrupt` et `SystemExit` en héritent directement, hors d'`Exception`, pour qu'un `except Exception` les laisse passer.
- Exemple : Un Ctrl+C traverse `except Exception:` et arrête bien le script.
- Carte : exceptions-except-exception-limites

## boucle d'événements
- Définition : Moteur d'asyncio qui reprend tour à tour les coroutines prêtes et les met en pause pendant leurs attentes (≈ event loop de Node).
- Exemple : Appeler une `async def` ne fait que créer une coroutine ; c'est la boucle, lancée par `asyncio.run`, qui l'exécute.
- Alias : event loop
- Carte : decorateurs-async-await

## bytecode
- Définition : Code intermédiaire que Python produit en compilant un fichier `.py` avant de l'exécuter, rangé en `.pyc` dans `__pycache__`.
- Exemple : Sans `.pyc` dans le zip, la Lambda compile les modules à chaque démarrage à froid : quelques millisecondes de plus.
- Alias : .pyc
- Carte : archives-zip-reproductible-recette

## bytes
- Définition : Type Python d'une suite d'octets (`b"A1"`), distinct du texte `str` ; on passe de l'un à l'autre par `encode` et `decode`.
- Exemple : `gzip.compress` et `hashlib.sha256` exigent des `bytes` : `"A1".encode("utf-8")` d'abord.
- Alias : octets, bytes-like, bytearray
- Carte : compression-bytes-pas-str

## BytesIO
- Définition : `io.BytesIO` : objet fichier binaire en mémoire, sans disque ; on y écrit et on relit des octets comme dans un vrai fichier.
- Exemple : Un test compresse vers `io.BytesIO()` puis lit `buf.getvalue()` pour vérifier les octets du gzip.
- Alias : io.BytesIO, StringIO
- Carte : compression-gzipfile-en-flux

## @cache
- Définition : Décorateur `functools.cache` qui mémorise le résultat d'une fonction pour chaque combinaison d'arguments : un appel identique ne refait pas le calcul.
- Exemple : `@cache def s3_client(): return boto3.client("s3")` crée le client au premier appel puis le réutilise.
- Alias : functools.cache, lru_cache
- Carte : decorateurs-cache-memoriser

## @cached_property
- Définition : Décorateur `functools.cached_property` : l'attribut est calculé au premier accès puis stocké dans l'objet, sans recalcul ensuite.
- Exemple : Un index des SIREN d'un lot d'annonces, coûteux, calculé une seule fois par objet `Lot`.
- Alias : cached_property
- Carte : classes-cached-property

## camelCase
- Définition : Style de nommage qui colle les mots en mettant une majuscule à chacun sauf le premier (`dateParution`), courant en JavaScript et dans les API JSON.
- Exemple : Un modèle Pydantic lit la clé `dateParution` de l'API dans le champ Python `date_parution` grâce à un alias.
- Carte : validation-alias

## caplog
- Définition : Fixture pytest qui capture les logs émis pendant un test : `caplog.records` (enregistrements) et `caplog.text` (texte).
- Exemple : Vérifier qu'un rejet d'annonce est journalisé avec son SIREN : filtrer `caplog.records` par nom de logger.
- Carte : tests-caplog

## capsys
- Définition : Fixture pytest qui capture ce que le code écrit sur la sortie standard et la sortie d'erreur pendant un test.
- Exemple : `capsys.readouterr().err` contient le message d'usage d'argparse après une option manquante.
- Carte : ligne-de-commande-main-argv-teste

## CEST
- Définition : Central European Summer Time : heure d'été de Paris, UTC+2, de fin mars à fin octobre ; l'hiver, c'est CET, UTC+1.
- Exemple : 22:30 UTC le 24 octobre est déjà 00:30 le 25 à Paris, en CEST.
- Alias : CET
- Carte : dates-date-dans-quel-fuseau

## ClassVar
- Définition : Annotation `ClassVar[T]` qui déclare un attribut partagé par la classe, et non un champ de chaque instance, par exemple dans une dataclass.
- Exemple : `NIVEAU: ClassVar[int] = 6` dans une dataclass reste une constante, absente de `__init__`.
- Carte : classes-dataclass-sans-annotation

## clé de tri
- Définition : Fonction passée à `key=` de `sorted`, `min`, `max` : elle reçoit un élément et renvoie la valeur à comparer, sans comparateur `(a, b)`.
- Exemple : `sorted(annonces, key=lambda a: (a["date"], a["siren"]))` trie par date puis par SIREN.
- Alias : key
- Carte : fonctions-sorted-key-lambda

## coercition
- Définition : Conversion automatique d'une valeur vers le type annoté pendant la validation, par exemple la chaîne `"10000"` en entier.
- Exemple : Pydantic en mode lax convertit `"2026-10-20"` en `date` ; le mode strict refuse.
- Alias : mode lax
- Carte : validation-coercion-lax

## collision
- Définition : Deux contenus différents qui donnent la même empreinte ; rare avec SHA-256 entier, probable avec une empreinte tronquée.
- Exemple : Identifier 100 000 annonces par 8 caractères hexadécimaux de leur sha256 : une collision est quasi certaine.
- Alias : collisions
- Carte : hachage-troncature-collision

## compréhension
- Définition : Expression qui construit une liste, un dict ou un set en une ligne : `[f(x) for x in seq if cond]` (≈ `filter` + `map`).
- Exemple : `[s.replace(" ", "") for s in sirens if s]` nettoie une liste de SIREN en une ligne.
- Alias : compréhensions, compréhension de liste
- Carte : listes-comprehensions

## conftest.py
- Définition : Fichier de pytest dont les fixtures sont visibles, sans import, par tous les tests de son dossier et des sous-dossiers.
- Exemple : `packages/bodacc-client/tests/conftest.py` partage la fixture `export_rows` entre les fichiers de test du membre.
- Alias : conftest
- Carte : tests-conftest-portee

## context manager
- Définition : Objet utilisable dans un bloc `with` : il ouvre une ressource à l'entrée et la libère toujours à la sortie, même sur exception.
- Exemple : `with open(p) as f:` ferme le fichier à la fin du bloc ; `httpx.Client` et `TemporaryDirectory` font de même.
- Alias : gestionnaire de contexte, gestionnaire, with, bloc with, context managers
- Carte : context-managers-with-try-finally

## ContextVar
- Définition : `contextvars.ContextVar` : variable dont la valeur est propre au contexte d'exécution courant (thread, tâche asynchrone), sans la passer en paramètre.
- Exemple : Ranger l'identifiant de l'invocation au début du handler, puis l'ajouter à chaque ligne de log par un filtre.
- Alias : contextvars
- Carte : logging-filter-request-id

## copie superficielle
- Définition : Copie du conteneur seulement : la nouvelle liste ou le nouveau dict partage les mêmes éléments que l'original.
- Exemple : `b = dict(a)` puis `b["tags"].append("y")` modifie aussi `a["tags"]` ; `copy.deepcopy` évite ce partage.
- Alias : shallow copy, copie profonde
- Carte : collections-copie-superficielle-profonde

## coroutine
- Définition : Objet renvoyé par l'appel d'une fonction `async def` : un calcul suspendable, exécuté seulement quand on l'attend avec `await` (≈ Promise paresseuse).
- Exemple : `fetch("1")` sans `await` ne lance aucune requête : on obtient une coroutine.
- Alias : coroutines
- Carte : decorateurs-async-await

## Counter
- Définition : `collections.Counter` : dict qui compte les occurrences de chaque élément, avec `most_common(n)` pour le classement.
- Exemple : `Counter(a["ville"] for a in annonces).most_common(3)` donne les trois villes les plus fréquentes.
- Carte : dictionnaires-counter-compter

## couverture de code
- Définition : Mesure des lignes, et avec `--cov-branch` des chemins (`if`, boucles), exécutés par les tests ; révèle le code jamais testé.
- Exemple : `pytest --cov --cov-branch` a montré la sortie de boucle de `fetch_day` jamais prise par les tests.
- Alias : coverage, couverture
- Carte : tests-couverture-branches

## CPython
- Définition : Implémentation de référence de Python, écrite en C, celle qu'on installe d'habitude et que Lambda exécute.
- Exemple : Sous CPython, un objet sans référence est détruit aussitôt ; d'autres implémentations ne le garantissent pas.
- Carte : generateurs-close-finally

## CRC32
- Définition : Somme de contrôle de 32 bits calculée sur des octets ; détecte une corruption accidentelle, sans sécurité contre une falsification.
- Exemple : Un gzip finit par le CRC32 de son contenu, écrit à la fermeture : sans `close()`, le fichier est illisible.
- Alias : CRC
- Carte : compression-fin-crc-fermeture

## dataclass
- Définition : Classe décorée par `@dataclass` : Python génère `__init__`, `__repr__` et `__eq__` à partir des champs annotés, sans vérifier leurs types.
- Exemple : `@dataclass(frozen=True) class PartStats: count: int; sha256: str` : un résultat nommé, comparable d'un bloc.
- Alias : dataclasses, @dataclass
- Carte : classes-dataclass-generee

## datetime aware
- Définition : `datetime` qui porte un fuseau (`tzinfo`) : il désigne un instant précis, comparable entre machines et fuseaux.
- Exemple : `datetime.now(timezone.utc)` est aware ; on le convertit ensuite à l'heure de Paris pour trouver le jour.
- Alias : aware
- Carte : dates-naif-ou-aware

## datetime naïf
- Définition : `datetime` sans fuseau (`tzinfo` à `None`) : une heure murale dont l'instant réel dépend de la machine qui la lit.
- Exemple : `datetime.now()` sur Lambda (UTC) et sur un Mac à Paris donne deux heures différentes, sans le dire.
- Alias : naïf, naive, heure naïve
- Carte : dates-naif-ou-aware

## déballage
- Définition : Affectation de chaque élément d'une séquence à une variable : `a, b = t` (≈ déstructuration `const [a, b] = t`).
- Exemple : `for jour, n in compteurs.items():` déballe chaque paire ; `[record] = liste` exige exactement un élément.
- Alias : dépaquetage, déstructuration, unpacking
- Carte : collections-tuple-deballer

## Decimal
- Définition : Type `decimal.Decimal` qui représente un nombre décimal exactement, en base 10, sans les erreurs d'arrondi binaire du `float`.
- Exemple : `Decimal("0.1") + Decimal("0.2") == Decimal("0.3")` est vrai ; avec des `float`, faux.
- Carte : texte-nombres-decimal-montants

## décorateur
- Définition : Fonction qui reçoit une fonction (ou une classe) et en renvoie une version enrichie ; `@deco` au-dessus d'un `def` équivaut à `f = deco(f)`.
- Exemple : `@retry` réessaie un appel BODACC, `@cache` mémorise un résultat, `@dataclass` génère des méthodes.
- Alias : décorateurs, decorator
- Carte : decorateurs-fonction-qui-renvoie

## defaultdict
- Définition : `collections.defaultdict` : dict qui crée automatiquement la valeur d'une clé absente en appelant une fabrique (`list`, `int`).
- Exemple : `par_ville = defaultdict(list)` puis `par_ville[v].append(a)` groupe les annonces sans tester la clé.
- Carte : dictionnaires-defaultdict-grouper

## deflate
- Définition : Algorithme de compression sans perte qui remplace les répétitions par des renvois ; utilisé par gzip, zip et zlib.
- Exemple : Une journée BODACC de 55,6 Mo de JSON tombe à 4,4 Mo : beaucoup de répétitions à remplacer.
- Carte : compression-gzip-ou-zlib

## dependency group
- Définition : Groupe nommé de dépendances de développement, déclaré dans `[dependency-groups]` du `pyproject.toml` (PEP 735) et jamais publié avec le paquet.
- Exemple : `uv add --dev pytest` range pytest dans le groupe `dev` : `uv sync` l'installe, la roue publiée ne le contient pas.
- Alias : dependency groups, dependency-groups, groupe de dépendances
- Carte : DevOps/uv-dev-dependency-groups

## deque
- Définition : `collections.deque` : file à deux bouts où ajouter ou retirer en tête comme en queue se fait en temps constant.
- Exemple : `deque(maxlen=100)` garde les 100 dernières lignes d'un log, les plus anciennes sortent seules.
- Carte : listes-deque-file

## descripteur
- Définition : Objet de classe qui contrôle l'accès à un attribut via `__get__` et `__set__` ; les fonctions, `property` et `cached_property` en sont.
- Exemple : Une fonction est un descripteur : lue sur une instance, elle devient une méthode liée qui reçoit `self`.
- Alias : descripteurs, descriptor
- Carte : decorateurs-classe-call

## __dict__
- Définition : Dictionnaire interne d'un objet Python qui range ses attributs, nom → valeur ; `vars(obj)` le renvoie.
- Exemple : Après `a.sirens = []`, `a.__dict__` vaut `{"sirens": []}` ; `cached_property` y range sa valeur calculée.
- Carte : classes-cached-property

## docstring
- Définition : Chaîne placée en première ligne d'une fonction, classe ou module, qui la documente ; `help()` et les éditeurs l'affichent.
- Exemple : `def resolve_day(...): """Jour à ingérer, à l'heure de Paris."""` ; `functools.wraps` la recopie sur la fonction décorée.
- Carte : decorateurs-wraps-identite

## drapeau
- Définition : Option de ligne de commande sans valeur, vraie si présente et fausse sinon (`--dry-run`) ; argparse l'obtient avec `action="store_true"`.
- Exemple : `replay.py --dry-run` affiche les jours à rejouer sans appeler la Lambda.
- Alias : flag, store_true
- Carte : ligne-de-commande-store-true

## duck typing
- Définition : Principe de Python : un objet convient s'il a les méthodes attendues, quel que soit son type ou son héritage (≈ typage structurel de TS, mais à l'exécution).
- Exemple : Un faux client S3 avec seulement `upload_file` et `put_object` remplace le vrai boto3 dans un test.
- Carte : tests-faux-qui-enregistre-ordre

## EAFP
- Définition : « Easier to Ask Forgiveness than Permission » : style Python qui tente l'opération puis capture l'exception, plutôt que tout tester avant.
- Exemple : `try: d["siren"] except KeyError:` plutôt que `if "siren" in d:` avant chaque lecture.
- Carte : dictionnaires-keyerror-capturer

## échappement
- Définition : Écriture d'un caractère spécial sous une forme sûre : `\n` pour un retour à la ligne, `é` pour « é » dans du JSON.
- Exemple : `json.dumps("a\nb")` écrit `"a\\nb"` : le document reste sur une seule ligne du JSONL.
- Alias : échapper, échappé, échappés
- Carte : json-jsonl-saut-de-ligne

## empreinte
- Définition : Résumé de taille fixe calculé à partir d'un contenu par une fonction de hachage ; un octet changé donne une autre empreinte.
- Exemple : Le manifest d'une partition porte l'empreinte sha256 du JSONL : la même au rejeu prouve les mêmes octets.
- Alias : empreintes, digest, hachage
- Carte : hachage-sha256-empreinte

## en flux
- Définition : Traiter des données morceau par morceau à mesure qu'elles arrivent, sans tout charger en mémoire (≈ stream).
- Exemple : Lire une journée BODACC de 59 Mo ligne à ligne avec `iter_lines()` : la mémoire reste à quelques Mo.
- Alias : flux, streaming
- Carte : http-stream-iter-lines

## en-tête gzip
- Définition : Dix premiers octets d'un fichier gzip : signature `\x1f\x8b`, méthode, horodatage `mtime`, système et, en option, nom du fichier.
- Exemple : Un nom de fichier temporaire écrit dans l'en-tête gzip change les octets d'une même partition à chaque invocation.
- Carte : compression-filename-vide

## encodage
- Définition : Règle qui traduit le texte en octets et inversement (UTF-8, Latin-1) ; le même texte donne d'autres octets selon l'encodage.
- Exemple : `open(p, encoding="utf-8")` évite que « Créteil » soit lu avec l'encodage par défaut de la machine.
- Alias : encoding, encodages
- Carte : hachage-bytes-pas-str

## ensure_ascii
- Définition : Option de `json.dumps`, vraie par défaut, qui échappe tout caractère non ASCII en `\uXXXX` ; `False` écrit les accents tels quels.
- Exemple : `json.dumps("é", ensure_ascii=False)` écrit 1 caractère mais 2 octets UTF-8.
- Carte : json-ensure-ascii-accents

## espace de noms
- Définition : Dictionnaire qui associe des noms à des objets : variables d'un module, d'une fonction, ou dict passé à `exec`.
- Exemple : `check_cards.py` exécute chaque carte dans un espace de noms neuf, pour qu'aucune variable ne fuite d'une carte à l'autre.
- Carte : execution-dynamique-eval-vs-exec

## évaluation paresseuse
- Définition : Calcul retardé jusqu'au moment où la valeur est demandée ; générateurs, `map`, `filter` et `range` fonctionnent ainsi.
- Exemple : `range(10**9)` ne coûte rien ; `list(range(10**9))` créerait un milliard d'entiers.
- Alias : paresseux, paresseuse, paresse, lazy
- Carte : generateurs-paresse-memoire

## exception
- Définition : Objet d'erreur levé par `raise` qui interrompt le code et remonte jusqu'au premier `except` de son type (≈ `throw` / `catch`).
- Exemple : `date.fromisoformat("hier")` lève `ValueError`, capturée par `except ValueError` dans `resolve_day`.
- Alias : exceptions
- Carte : exceptions-raise-lever

## exception chaînée
- Définition : Exception levée en gardant l'originale comme cause (`raise B from a` → `__cause__`, ou implicitement `__context__`) ; la trace montre les deux.
- Exemple : `resolve_day` lève « date invalide 'hier' » `from exc` : la cause technique reste lisible dans CloudWatch.
- Alias : chaînage, raise from, __cause__, __context__
- Carte : exceptions-raise-from-cause

## ExitStack
- Définition : `contextlib.ExitStack` : pile de context managers ouverte dynamiquement, tous refermés en ordre inverse à la sortie du `with`.
- Exemple : Ouvrir un fichier de sortie par jour d'une plage, en nombre variable, et tous les fermer même sur erreur.
- Carte : context-managers-exitstack-variable

## expression
- Définition : Code qui produit une valeur (`len(s)`, `a if c else b`), à la différence d'une instruction qui agit (`x = 1`, `import`).
- Exemple : Une lambda ne contient qu'une expression ; `eval` calcule une expression, `exec` exécute des instructions.
- Alias : expressions
- Carte : execution-dynamique-eval-vs-exec

## expression conditionnelle
- Définition : Expression `x if cond else y` qui choisit entre deux valeurs (≈ ternaire `cond ? x : y`, dans un autre ordre).
- Exemple : `lambda a: "radiation" if a["famille"] == "R" else "autre"` dans une clé de regroupement.
- Alias : ternaire, condition ternaire
- Carte : fonctions-lambda-ternaire

## expression génératrice
- Définition : Expression `(f(x) for x in seq)` qui crée un générateur en une ligne, sans construire de liste.
- Exemple : `sum(a["capital"] for a in annonces)` additionne sans liste intermédiaire.
- Alias : expressions génératrices, generator expression
- Carte : generateurs-expression-syntaxe

## f-string
- Définition : Chaîne préfixée par `f` dont les `{expressions}` sont évaluées et insérées (≈ template literal `` `${x}` ``) ; `{x!r}` insère le `repr`.
- Exemple : `f"date invalide {raw!r}"` affiche `date invalide 'hier'`, guillemets compris.
- Alias : f-strings, chaîne formatée
- Carte : exceptions-message-repr

## fabrique
- Définition : Fonction (ou classe) appelée pour créer un objet neuf à la demande ; `defaultdict(list)` appelle la fabrique `list` à chaque clé absente.
- Exemple : `repeter(3)` est une fabrique de décorateurs : elle renvoie le décorateur configuré.
- Alias : factory, fabriques
- Carte : fonctions-defaultdict-fabrique

## fail fast
- Définition : Principe qui fait échouer un traitement au plus tôt, dès qu'une entrée est invalide, avant tout effet coûteux ou partiel.
- Exemple : Le handler refuse une date invalide avant tout appel à l'API BODACC : `call_count == 0` le prouve.
- Alias : échouer tôt
- Carte : tests-respx-aucun-appel

## fermeture
- Définition : Fonction qui garde l'accès aux variables de la fonction où elle a été définie, même après la fin de celle-ci (≈ closure JS).
- Exemple : `def repeter(n): def deco(f): ...` : `deco` voit `n` par fermeture ; `nonlocal` permet de le réaffecter.
- Alias : closure, closures, fermetures
- Carte : fonctions-closure-capture-tardive

## FIPS
- Définition : Federal Information Processing Standards : normes américaines de cryptographie ; en mode FIPS, les algorithmes jugés faibles comme MD5 sont refusés.
- Exemple : Sur une machine FIPS, `hashlib.md5()` lève, sauf `usedforsecurity=False` pour une simple somme de contrôle.
- Carte : hachage-md5-sha1-integrite

## fixture pytest
- Définition : Fonction marquée `@pytest.fixture` qui prépare une donnée ou une ressource ; pytest l'injecte dans chaque test qui a un paramètre du même nom.
- Exemple : `def test_ecrit(tmp_path, s3):` reçoit un dossier temporaire et un faux client S3 moto.
- Alias : fixture, fixtures, fixtures pytest
- Carte : tests-fixture-injection-par-nom

## float
- Définition : Nombre à virgule flottante binaire (IEEE 754) : rapide mais approché, `0.1 + 0.2` vaut `0.30000000000000004`.
- Exemple : Un montant lu en `float` dérive à force de sommes ; `Decimal` le garde exact.
- Alias : flottant, flottants, nombre flottant
- Carte : json-float-forme-courte

## fonction d'ordre supérieur
- Définition : Fonction qui reçoit une fonction en argument ou en renvoie une ; décorateurs, `map` et `sorted(key=…)` en sont.
- Exemple : `crier(saluer)` reçoit `saluer` et renvoie une nouvelle fonction qui l'appelle.
- Alias : higher-order function
- Carte : decorateurs-fonction-qui-renvoie

## fonction lambda
- Définition : Petite fonction anonyme `lambda x: expr` réduite à une seule expression, renvoyée implicitement (≈ arrow function `(x) => expr`).
- Exemple : `sorted(annonces, key=lambda a: a["date"])` ; à ne pas confondre avec le service AWS Lambda.
- Alias : lambda Python, lambdas Python, expression lambda
- Carte : fonctions-lambda-une-expression

## fonction pure
- Définition : Fonction dont le résultat ne dépend que de ses arguments, sans effet de bord : même entrée, même sortie.
- Exemple : `days(start, end)` est pure, donc testable sans AWS et mémorisable par `@cache`.
- Alias : fonctions pures
- Carte : decorateurs-cache-memoriser

## frozenset
- Définition : Version figée d'un `set` : non modifiable, donc hashable, utilisable comme clé de dict ou élément d'un autre set.
- Exemple : `frozenset({"A1", "A2"})` comme champ d'une dataclass figée qu'on range dans un set.
- Carte : collections-hashable

## fuite mémoire
- Définition : Mémoire qui grossit sans jamais être libérée parce que des objets restent référencés alors qu'ils ne servent plus.
- Exemple : Un `@cache` sans borne sur un SIREN par appel, dans une Lambda chaude des heures, finit par saturer la mémoire.
- Alias : fuites mémoire, memory leak
- Carte : decorateurs-lru-cache-maxsize

## functools.partial
- Définition : Fonction qui fige certains arguments d'une autre et renvoie une nouvelle fonction qui attend le reste.
- Exemple : `partial(lire_jour, tribunal="7501")` donne une fonction qui ne demande plus que le jour.
- Alias : partial
- Carte : fonctions-closure-figer-valeur

## functools.wraps
- Définition : Décorateur à poser sur la fonction interne d'un décorateur : il recopie le nom, la docstring et `__wrapped__` de la fonction d'origine.
- Exemple : Sans `@wraps(f)`, les logs CloudWatch nomment la fonction décorée `interne` au lieu de `fetch_day`.
- Alias : wraps, @wraps, __wrapped__
- Carte : decorateurs-wraps-identite

## fuseau horaire
- Définition : Région qui suit une même heure légale et ses règles d'heure d'été (`Europe/Paris`) ; Python le représente par un `tzinfo`.
- Exemple : Le jour de parution BODACC se calcule dans le fuseau `Europe/Paris`, pas en UTC.
- Alias : fuseau, fuseaux, tzinfo, timezone
- Carte : dates-zoneinfo-nom-iana

## générateur
- Définition : Itérateur produit par une fonction qui contient `yield` : il calcule ses valeurs une à une, à la demande, et ne se parcourt qu'une fois (≈ `function*`).
- Exemple : `fetch_day` est un générateur : il rend les annonces ligne par ligne pendant le téléchargement.
- Alias : générateurs, fonction génératrice, generator
- Carte : generateurs-yield-a-la-demande

## graphlib
- Définition : Module standard dont `TopologicalSorter` range des tâches dépendantes dans un ordre où chacune passe après ses prérequis.
- Exemple : `TopologicalSorter({"publier": {"ecrire"}}).static_order()` rend `ecrire` puis `publier`.
- Alias : TopologicalSorter

## gzip
- Définition : Format de compression d'un seul fichier (deflate + en-tête + CRC32), extension `.gz` ; aussi le module Python qui le lit et l'écrit.
- Exemple : Chaque partition est écrite en `part-0001.jsonl.gz` par `gzip.GzipFile`, avec `mtime=0` pour des octets reproductibles.
- Alias : .gz, GzipFile
- Carte : compression-gzip-open-modes

## handler de log
- Définition : Objet `logging.Handler` qui écrit les messages d'un logger vers une destination (flux, fichier, CloudWatch), avec son propre niveau et format.
- Exemple : Le runtime Lambda pose un handler sur le logger racine : les modules n'en ajoutent pas, sinon chaque ligne sort en double.
- Alias : StreamHandler
- Carte : logging-propagate-doublons

## hash
- Définition : Entier calculé par `hash(obj)` qui range un objet dans un dict ou un set ; pour les chaînes, il change à chaque lancement de Python.
- Exemple : `hash("A1")` diffère d'un run à l'autre : jamais le stocker ; utiliser `hashlib.sha256` pour une empreinte stable.
- Alias : hash(), __hash__
- Carte : hachage-hash-builtin-instable

## hashable
- Définition : Objet dont le `hash` ne change jamais (chaîne, nombre, tuple, frozenset), seul admis comme clé de dict ou élément de set.
- Exemple : Une liste n'est pas hashable : `{["A1"]}` lève `TypeError: unhashable type: 'list'`.
- Alias : hachable, hachables, hashables
- Carte : collections-hashable

## heapq
- Définition : Module standard de tas binaire : `heapq.nlargest(n, …)` et `nsmallest` donnent les n premiers sans trier toute la liste.
- Exemple : `heapq.nlargest(10, annonces, key=lambda a: a["capital"])` : les dix plus gros capitaux d'une journée.
- Carte : collections-sorted-plusieurs-cles

## heure d'été
- Définition : Décalage d'une heure appliqué une partie de l'année : Paris passe de UTC+1 à UTC+2 fin mars, et revient fin octobre.
- Exemple : Le 25 octobre 2026 dure 25 heures à Paris : 02:00 à 02:59 s'y répètent.
- Alias : changement d'heure, DST
- Carte : dates-fold-heure-ambigue

## heure murale
- Définition : Heure affichée par une horloge locale (date, heure, minute), sans tenir compte des changements d'heure entre deux instants.
- Exemple : De 12:00 le 24 octobre à 12:00 le 25 à Paris : 1 jour en heure murale, mais 25 heures réelles.
- Alias : heure locale
- Carte : dates-soustraction-heure-murale

## hexadécimal
- Définition : Écriture d'un nombre ou d'octets en base 16 (chiffres 0-9 et lettres a-f), deux caractères par octet.
- Exemple : `hexdigest()` écrit les 32 octets d'un sha256 en 64 caractères hexadécimaux, ceux du manifest.
- Alias : hex, hexdigest
- Carte : hachage-hexdigest-ou-digest

## HMAC
- Définition : Hash-based Message Authentication Code : empreinte calculée avec une clé secrète ; seul qui a la clé peut la reproduire ou la vérifier.
- Exemple : Vérifier la signature d'un webhook : recalculer son HMAC-SHA256 puis comparer avec `hmac.compare_digest`.
- Alias : HMAC-SHA256
- Carte : hachage-compare-digest-temps-constant

## httpx
- Définition : Bibliothèque Python de client HTTP, synchrone et asynchrone, avec timeouts, flux et transports remplaçables (≈ axios).
- Exemple : `BodaccClient` utilise un `httpx.Client` pour télécharger l'export BODACC du jour en flux.
- Carte : http-client-timeout-defaut

## IANA
- Définition : Organisme qui maintient la base mondiale des fuseaux horaires (noms `Continent/Ville` et règles d'heure d'été), lue par `zoneinfo`.
- Exemple : `ZoneInfo("Europe/Paris")` charge la règle IANA ; le paquet `tzdata` l'embarque dans le zip de la Lambda.
- Alias : base IANA, tz database
- Carte : dates-zoneinfo-nom-iana

## identité
- Définition : Fait que deux noms désignent le même objet en mémoire, testé par `is` ; `==` compare seulement les valeurs.
- Exemple : `[1] == [1]` est vrai, `[1] is [1]` faux : deux listes égales mais distinctes.
- Alias : is
- Carte : collections-alias-pas-de-copie

## IEEE 754
- Définition : Norme de représentation des nombres flottants en binaire, suivie par Python et JavaScript ; beaucoup de décimales n'y sont qu'approchées.
- Exemple : `0.1 + 0.2 == 0.3` est faux dans les deux langages, à cause d'IEEE 754.
- Carte : tests-approx-flottants

## immuable
- Définition : Objet qu'on ne peut plus modifier après création (`str`, `tuple`, `frozenset`, dataclass figée) ; pour le changer, on en crée un nouveau.
- Exemple : Une fonction en cache renvoie un `tuple` immuable : aucun appelant ne peut altérer le résultat partagé.
- Alias : immuables, immutable, non modifiable
- Carte : classes-frozen-en-surface

## import Python
- Définition : Instruction qui charge un module et exécute son code une première fois, puis le garde en cache pour les imports suivants.
- Exemple : Un décorateur s'exécute à l'import du module ; importer boto3 dans `main()` seulement accélère `--help`.
- Alias : imports, importer, importé
- Carte : ligne-de-commande-import-differe

## IndexError
- Définition : Exception levée quand on lit une liste ou un tuple à un index qui n'existe pas (pas de `undefined` comme en JS).
- Exemple : `["a", "b"][5]` lève `IndexError` ; la tranche `l[5:]` rend simplement `[]`.
- Carte : listes-index-negatif

## injection de commande
- Définition : Faille où une donnée insérée dans une commande shell est interprétée comme une commande supplémentaire.
- Exemple : `run(f"echo {nom}", shell=True)` avec `nom = "x; rm f"` exécute aussi `rm f` ; une liste sans shell l'évite.
- Carte : sous-processus-shell-true-injection

## injection de dépendance
- Définition : Passer à une fonction ou un objet ses dépendances (client, horloge) en paramètre, au lieu qu'il les crée lui-même ; un test y met un faux.
- Exemple : `BodaccClient(http=..., sleep=delais.append)` : en test, pas de réseau ni d'attente réelle.
- Alias : injection de dépendances, injectable, injecté
- Carte : tests-injection-dependance

## installation éditable
- Définition : Installation d'un paquet qui pointe vers ses sources au lieu de les copier : une modification du code est visible sans réinstaller.
- Exemple : `uv sync` installe `dp-common` en éditable : un `.pth` ajoute `packages/dp-common/src` au `sys.path`.
- Alias : éditable, mode éditable
- Carte : packaging-installation-editable

## instruction
- Définition : Ligne de code qui agit sans produire de valeur (`x = 1`, `import os`, `def`, `return`), à la différence d'une expression.
- Exemple : `print` est une expression, mais `x = 1` est une instruction : interdite dans une lambda.
- Alias : instructions
- Carte : execution-dynamique-eval-vs-exec

## interpréteur
- Définition : Programme qui exécute le code Python (`python3`, `.venv/bin/python`) ; `sys.executable` donne le chemin de celui en cours.
- Exemple : `[sys.executable, "-m", "pytest"]` relance pytest avec le même interpréteur, donc les mêmes dépendances.
- Alias : interpréteur Python
- Carte : sous-processus-sys-executable

## isinstance
- Définition : Fonction qui teste si un objet est d'un type ou d'une de ses sous-classes : `isinstance(x, str)`.
- Exemple : `isinstance(raw, str)` avant `fromisoformat` ; mais un `datetime` passe `isinstance(x, date)`.
- Carte : dates-datetime-herite-de-date

## ISO 8601
- Définition : Norme d'écriture des dates et heures, du plus grand au plus petit (`2026-10-20T22:30:00+00:00`), triable comme du texte.
- Exemple : `date.fromisoformat("2026-10-20")` lit une date ISO ; les partitions sont nommées `date=2026-10-20`.
- Alias : ISO, date ISO, dates ISO
- Carte : dates-date-fromisoformat

## itérable
- Définition : Objet qu'on peut parcourir avec `for` (liste, dict, chaîne, fichier, générateur) : `iter()` en tire un itérateur.
- Exemple : `Counter`, `sum`, `set` et `list.extend` acceptent n'importe quel itérable, pas seulement une liste.
- Alias : itérables
- Carte : generateurs-iterable-ou-iterateur

## itérateur
- Définition : Objet qui rend ses valeurs une à une par `next()` et s'épuise : on ne le parcourt qu'une fois (générateur, `map`, `zip`, `groupby`).
- Exemple : Après `list(zip(a, b))`, le même `zip` rend une liste vide.
- Alias : itérateurs
- Carte : generateurs-iterable-ou-iterateur

## itertools
- Définition : Module standard d'outils sur les itérables : `islice`, `batched`, `groupby`, `chain`, `count`, souvent paresseux.
- Exemple : `itertools.batched(annonces, 500)` découpe un flux en lots de 500 pour un envoi groupé.
- Carte : generateurs-batched-lots

## kebab-case
- Définition : Style de nommage en minuscules avec des tirets entre les mots (`dry-run`), courant pour les options de ligne de commande.
- Exemple : L'option `--dry-run` devient `args.dry_run` côté Python, en snake_case.
- Carte : ligne-de-commande-tiret-souligne

## KeyError
- Définition : Exception levée quand on lit avec `d[k]` une clé absente d'un dict ; `d.get(k)` renvoie `None` à la place.
- Exemple : `os.environ["RAW_BUCKET"]` lève `KeyError` si la variable n'est pas définie.
- Carte : dictionnaires-lire-sans-planter

## **kwargs
- Définition : Paramètre qui ramasse les arguments nommés en trop dans un dict ; à l'appel, `f(**d)` déplie un dict en arguments nommés.
- Exemple : Un décorateur générique `def interne(*args, **kwargs): return f(*args, **kwargs)` transmet tout sans connaître la signature.
- Alias : kwargs
- Carte : decorateurs-args-kwargs

## littéral
- Définition : Valeur écrite telle quelle dans le code : `42`, `"A1"`, `[1, 2]`, `{"a": 1}`, `None`.
- Exemple : `ast.literal_eval("['483609327']")` relit un littéral Python sans exécuter de code.
- Alias : littéraux
- Carte : execution-dynamique-literal-eval

## logger
- Définition : Objet `logging.Logger` nommé par lequel un module émet ses messages ; les loggers forment un arbre selon leurs noms pointés.
- Exemple : `logger = logging.getLogger(__name__)` dans `ingest_bodacc/handler.py` donne le logger `ingest_bodacc.handler`.
- Alias : loggers, getLogger
- Carte : logging-getlogger-name

## logger racine
- Définition : Logger au sommet de l'arbre (`logging.getLogger()`), parent de tous ; c'est sur lui qu'on pose en général les handlers.
- Exemple : `logging.basicConfig` configure le logger racine ; dans Lambda, le runtime l'a déjà fait.
- Alias : logger root, root logger
- Carte : logging-basicconfig-une-fois

## LRU
- Définition : Least Recently Used : politique de cache plein qui évince l'entrée lue le moins récemment pour faire de la place.
- Exemple : `@lru_cache(maxsize=1024)` garde les 1 024 SIREN les plus récemment demandés.
- Alias : least recently used
- Carte : decorateurs-lru-cache-maxsize

## MAC
- Définition : Message Authentication Code : empreinte calculée avec une clé secrète, qui prouve qu'un message vient de qui détient la clé et n'a pas été modifié.
- Exemple : `blake2b(data, key=secret)` produit un MAC ; HMAC est la construction la plus répandue.
- Carte : hachage-blake2b-taille-cle

## MagicMock
- Définition : Faux objet de `unittest.mock` qui accepte n'importe quel attribut ou appel et enregistre tout ; pratique mais trop permissif.
- Exemple : `s3 = MagicMock()` accepte `s3.put_objet(...)`, faute de frappe comprise : le test passe à tort.
- Alias : unittest.mock
- Carte : tests-faux-client-signature

## manylinux
- Définition : Tag de wheel compilé pour Linux qui garantit une compatibilité avec la plupart des distributions (`manylinux2014_x86_64`).
- Exemple : Le zip de la Lambda installe pydantic-core en wheel manylinux, pas celui du Mac.
- Carte : packaging-tags-wheel-plateforme

## marqueur pytest
- Définition : Étiquette `@pytest.mark.<nom>` posée sur un test pour le sélectionner, l'exclure ou changer son traitement (`skip`, `xfail`).
- Exemple : `@pytest.mark.integration` et `-m 'not integration'` dans `addopts` : les tests réseau ne tournent qu'à la demande.
- Alias : marqueur, marqueurs, pytest.mark
- Carte : tests-marqueur-exclure-integration

## MD5
- Définition : Fonction de hachage ancienne qui produit une empreinte de 128 bits ; cassée pour la sécurité, encore utilisée pour vérifier l'intégrité.
- Exemple : L'ETag d'un objet S3 envoyé d'un bloc, sans SSE-KMS, est le MD5 de son contenu.
- Carte : hachage-md5-sha1-integrite

## membre gzip
- Définition : Bloc complet d'un fichier gzip (en-tête, données, CRC32, taille) ; plusieurs membres collés forment encore un gzip valide.
- Exemple : `cat a.gz b.gz > ab.gz` donne un gzip à deux membres, décompressé en contenus mis bout à bout.
- Alias : membres, plusieurs membres
- Carte : compression-plusieurs-membres

## métaclasse
- Définition : Classe d'une classe : elle contrôle comment une classe est créée ; `ABCMeta` est celle des classes abstraites.
- Exemple : Hériter d'`ABC` donne la métaclasse `ABCMeta`, qui refuse d'instancier une classe aux méthodes abstraites manquantes.
- Alias : métaclasses, metaclass
- Carte : classes-abstractmethod-contrat

## métadonnées de paquet
- Définition : Fiche d'un paquet installé (nom, version, dépendances, fichiers) rangée dans son dossier `.dist-info`, lue par `importlib.metadata`.
- Exemple : `importlib.metadata.version("bodacc-client")` lit la version dans `METADATA`, pas dans `pyproject.toml`.
- Alias : dist-info, .dist-info, METADATA
- Carte : packaging-dist-info

## méthode spéciale
- Définition : Méthode au nom entouré de doubles tirets bas (`__init__`, `__eq__`, `__enter__`) que Python appelle lui-même pour un opérateur ou un protocole.
- Exemple : `with` appelle `__enter__` et `__exit__` ; `==` appelle `__eq__`, que `@dataclass` génère.
- Alias : méthodes spéciales, dunder, méthode magique
- Carte : context-managers-enter-exit-classe

## mock
- Définition : Faux objet ou service qui remplace une dépendance réelle (réseau, AWS) pendant un test, pour contrôler ses réponses.
- Exemple : moto mocke S3 en mémoire et respx mocke l'API BODACC : le test du handler tourne sans réseau.
- Alias : mocks, mocké, mocker, simulacre
- Carte : tests-moto-mock-aws

## module
- Définition : Fichier `.py` importable ; ses fonctions, classes et variables forment un espace de noms (`dp_common.io`).
- Exemple : `@staticmethod` est rarement utile : une simple fonction de module fait souvent mieux.
- Alias : modules
- Carte : packaging-nom-distribution-vs-module

## monkeypatch
- Définition : Fixture pytest qui remplace le temps d'un test une variable d'environnement ou un attribut, puis restaure tout automatiquement.
- Exemple : `monkeypatch.setenv("RAW_BUCKET", "dp-raw")` puis `monkeypatch.delenv("AWS_PROFILE", raising=False)`.
- Carte : tests-monkeypatch

## mot réservé
- Définition : Mot du langage interdit comme nom de variable ou d'attribut (`from`, `class`, `import`, `def`, `lambda`).
- Exemple : L'option `--from` donnerait `args.from`, erreur de syntaxe : d'où `dest="start"`.
- Alias : mots réservés, mot-clé réservé
- Carte : ligne-de-commande-dest-mot-reserve

## moto
- Définition : Bibliothèque Python de test qui simule les services AWS en mémoire et intercepte les appels boto3, sans compte ni réseau.
- Exemple : `with mock_aws():` crée un bucket `dp-raw` factice où le test écrit puis relit une partition.
- Alias : mock_aws
- Carte : tests-moto-mock-aws

## MRO
- Définition : Method Resolution Order : ordre dans lequel Python cherche une méthode parmi une classe et ses parents (`Classe.__mro__`).
- Exemple : `ValueError.__mro__` montre `ValueError`, `Exception`, `BaseException`, `object`.
- Alias : Method Resolution Order, __mro__
- Carte : exceptions-hierarchie-sous-classes

## mtime
- Définition : Date de dernière modification d'un fichier, en secondes depuis 1970 ; gzip l'écrit dans son en-tête, zip la recopie sur ses entrées.
- Exemple : `gzip.GzipFile(..., mtime=0)` fixe cet horodatage : deux compressions du même contenu donnent les mêmes octets.
- Alias : date de modification
- Carte : compression-mtime-zero

## mypy
- Définition : Vérificateur de types statique pour Python : il lit les annotations et signale les incohérences, sans exécuter le code.
- Exemple : mypy signale `normaliser([1, 2])` sur une fonction annotée `list[str]`, ce que Python laisse passer.
- Alias : pyright, vérificateur de types
- Carte : dictionnaires-typeddict-json

## name mangling
- Définition : Renommage automatique par Python d'un attribut `__nom` en `_Classe__nom`, pour qu'une sous-classe ne l'écrase pas par accident.
- Exemple : `self.__cle` dans `Client` est stocké sous `_Client__cle` : `c.__cle` lève `AttributeError`.
- Carte : classes-prive-par-convention

## __name__
- Définition : Variable que Python donne à chaque module : son nom d'import (`ingest_bodacc.handler`), ou `"__main__"` quand le fichier est lancé comme script.
- Exemple : `logging.getLogger(__name__)` nomme le logger d'après le module ; `if __name__ == "__main__":` ne s'exécute qu'en lançant le script.
- Carte : ligne-de-commande-garde-main

## NamedTuple
- Définition : `typing.NamedTuple` : tuple dont les éléments ont aussi un nom ; on lit `p.count` ou `p[0]`, et il se déballe.
- Exemple : `class Part(NamedTuple): count: int; sha256: str` puis `count, sha = part`.
- Carte : classes-dataclass-plutot-que-tuple

## Namespace
- Définition : Objet renvoyé par `argparse.parse_args` : chaque option y devient un attribut (`args.dry_run`), pas une clé.
- Exemple : `vars(args)` convertit le Namespace en dict, pour un log ou un test.
- Carte : ligne-de-commande-argparse-options

## NaN
- Définition : Not a Number : valeur flottante spéciale résultat d'un calcul indéfini ; JSON n'a pas d'équivalent, et `NaN` n'y est pas valide.
- Exemple : `json.dumps(float("nan"))` écrit `NaN`, que `JSON.parse` et Athena refusent ; `allow_nan=False` bloque.
- Alias : Not a Number, Infinity
- Carte : json-nan-allow-nan

## niveau de log
- Définition : Gravité d'un message (`DEBUG` 10, `INFO` 20, `WARNING` 30, `ERROR` 40, `CRITICAL` 50) ; un logger ou un handler filtre sous son seuil.
- Exemple : Sans réglage, un logger hérite de `WARNING` : `log.info` n'écrit rien.
- Alias : niveaux de log, log level
- Carte : logging-niveaux-entiers

## normalisation Unicode
- Définition : Conversion d'un texte vers une forme unique (NFC, NFD) quand un même caractère accentué peut s'écrire de deux façons.
- Exemple : « é » d'un PDF (e + accent combinant) et « é » saisi diffèrent pour `==` jusqu'à `unicodedata.normalize("NFC", s)`.
- Alias : NFC, NFD
- Carte : texte-nombres-unicode-nfc

## objet fichier
- Définition : Objet renvoyé par `open` (ou `BytesIO`) avec `read`, `write`, `seek` et `close` ; de nombreuses API l'acceptent à la place d'un chemin.
- Exemple : `GzipFile(fileobj=f)` et `s3.upload_fileobj(f, …)` prennent un objet fichier déjà ouvert.
- Alias : fileobj, objets fichiers, file object
- Carte : context-managers-gzipfile-fileobj

## OpenSSL
- Définition : Bibliothèque de cryptographie du système, utilisée par Python pour une partie de `hashlib` et pour les connexions sécurisées.
- Exemple : `hashlib.algorithms_available` dépend de l'OpenSSL installé ; `algorithms_guaranteed`, non.
- Carte : hachage-new-par-nom

## ordre d'insertion
- Définition : Ordre dans lequel les clés ont été ajoutées à un dict, conservé par Python depuis 3.7 et repris par `json.dumps`.
- Exemple : Réaffecter une clé ne la déplace pas ; `sort_keys=True` impose un ordre stable pour hacher un JSON.
- Carte : dictionnaires-ordre-insertion

## os.environ
- Définition : Dictionnaire des variables d'environnement du processus : `os.environ["X"]` lève `KeyError` si `X` manque, `.get("X")` rend `None`.
- Exemple : Le handler lit `os.environ["RAW_BUCKET"]`, que Terraform pose dans la configuration de la Lambda.
- Carte : AWS/lambda-environ-echouer-tot

## pandas
- Définition : Bibliothèque Python d'analyse de tableaux de données en mémoire (DataFrame) : filtres, regroupements, statistiques.
- Exemple : Pour des moyennes par tribunal sur des millions de lignes, pandas ou DuckDB remplacent le module `statistics`.
- Alias : DataFrame
- Carte : collections-statistics-moyenne-mediane

## paquet
- Définition : Dossier de modules Python importable comme un tout (avec `__init__.py`) ; aussi, la distribution installable qui le contient.
- Exemple : `bodacc_client` est un paquet : `from bodacc_client import Annonce` passe par son `__init__.py`.
- Alias : paquets, package, packages
- Carte : packaging-init-facade

## parametrize
- Définition : Marqueur `@pytest.mark.parametrize` qui lance un même test une fois par jeu de valeurs, chaque cas compté à part.
- Exemple : `@pytest.mark.parametrize("raw", ["hier", "2026-13-01"])` vérifie deux dates invalides en un seul test.
- Alias : pytest.mark.parametrize, paramétré
- Carte : tests-parametrize

## PascalCase
- Définition : Écriture d'un nom composé où chaque mot commence par une majuscule, sans séparateur : `PutObject`, `ContentType`.
- Exemple : boto3 reprend les noms de l'API AWS en PascalCase (`Bucket=`, `Key=`) ; les classes Python aussi : `class Annonce`.
- Carte : AWS/s3-boto3-arguments-nommes

## pathlib
- Définition : Module standard dont la classe `Path` manipule les chemins comme des objets ; l'opérateur `/` les assemble.
- Exemple : `tmp_path / "date=2026-10-20" / "part-0001.jsonl.gz"` construit un chemin sans gérer les séparateurs.
- Carte : fichiers-formats-path-assembler-chemin

## PEP
- Définition : Python Enhancement Proposal : document numéroté qui décrit une évolution ou une convention de Python (PEP 8 : style ; PEP 621 : `pyproject.toml`).
- Exemple : PEP 479 a changé une `StopIteration` échappée d'un générateur en `RuntimeError`.
- Alias : PEPs, Python Enhancement Proposal
- Carte : generateurs-stopiteration-runtimeerror

## PEP 440
- Définition : Norme des numéros de version Python et de leurs comparaisons : segments numériques, pré-versions `a`, `b`, `rc`, spécificateurs `>=`, `~=`.
- Exemple : Selon PEP 440, `0.10.0` est plus récent que `0.9.0`, alors que la comparaison de chaînes dit l'inverse.
- Carte : packaging-ordre-pep440

## point de code
- Définition : Numéro unique qu'Unicode donne à chaque caractère (`U+00E9` pour « é ») ; Python trie les chaînes selon ces numéros.
- Exemple : `sorted(["é", "z", "a"])` donne `["a", "z", "é"]` : « é » a un point de code plus grand que « z ».
- Alias : points de code, code point
- Carte : json-sort-keys-points-de-code

## portée
- Définition : Zone du code où un nom est visible ; en Python, seuls fonctions, classes, modules et compréhensions en créent une, pas les blocs `if`, `for` ou `with`.
- Exemple : Après `with open(p) as f:`, `f` existe encore, mais le fichier est fermé.
- Alias : scope
- Carte : context-managers-pas-de-portee

## portée de fixture
- Définition : Durée de vie d'une fixture pytest (`function`, `module`, `session`) : combien de tests partagent la même valeur.
- Exemple : Un mock moto en `scope="session"` démarre une fois pour toute la suite, mais son état est partagé.
- Alias : scope de fixture
- Carte : tests-fixture-scope

## pré-version
- Définition : Version publiée avant la finale pour essai : alpha (`a1`), bêta (`b1`) ou release candidate (`rc1`), classée avant la finale.
- Exemple : `1.0.0rc1 < 1.0.0` selon PEP 440 ; uv ne choisit une pré-version que si on la demande.
- Alias : pré-versions, alpha, bêta, release candidate
- Carte : packaging-ordre-pep440

## @property
- Définition : Décorateur qui expose une méthode comme un attribut lu sans parenthèses, recalculé à chaque lecture (≈ getter `get` en TS).
- Exemple : `annonce.nb_sirens` renvoie `len(self.sirens)` sans qu'on écrive `annonce.nb_sirens()`.
- Alias : property, propriété, propriétés
- Carte : classes-property-getter

## Protocol
- Définition : `typing.Protocol` : déclare les méthodes attendues d'un objet pour le typage, sans héritage (≈ `interface` TS, vérifié par mypy).
- Exemple : `class S3Like(Protocol): def put_object(self, **kw): ...` accepte le vrai client comme un faux.
- Carte : classes-abstractmethod-contrat

## __pycache__
- Définition : Dossier où Python range le bytecode compilé (`.pyc`) des modules importés, pour démarrer plus vite la fois suivante.
- Exemple : Le zip d'une Lambda ne doit pas contenir de `__pycache__` : fichiers générés qui changent les octets d'un build à l'autre.
- Carte : archives-zip-reproductible-recette

## Pydantic
- Définition : Bibliothèque de validation : un modèle `BaseModel` déclare ses champs par annotations, convertit et vérifie les données à l'exécution (≈ zod).
- Exemple : `Annonce.model_validate_json(ligne)` valide chaque ligne JSONL de l'export BODACC.
- Alias : BaseModel
- Carte : validation-champ-requis-optionnel

## PyPI
- Définition : Python Package Index : dépôt public des paquets Python, d'où uv et pip téléchargent les dépendances (≈ registre npm).
- Exemple : `uv add httpx` télécharge httpx depuis PyPI et l'écrit dans `pyproject.toml`.
- Alias : Python Package Index
- Carte : packaging-nom-distribution-vs-module

## pyproject.toml
- Définition : Fichier de configuration d'un projet Python : nom, version, dépendances (`[project]`), backend de build et réglages d'outils (≈ `package.json`).
- Exemple : `lambdas/ingest_bodacc/pyproject.toml` déclare `httpx` et `tzdata` comme dépendances de la Lambda.
- Alias : pyproject
- Carte : packaging-table-project

## pytest
- Définition : Outil de test Python le plus courant : il découvre les fonctions `test_*`, vérifie avec `assert` et fournit les fixtures (≈ Jest).
- Exemple : `make check` lance `pytest` sur tous les membres du monorepo, sans réseau ni AWS.
- Carte : tests-decouverte-nommage

## ramasse-miettes
- Définition : Mécanisme qui libère automatiquement la mémoire des objets devenus inaccessibles (≈ garbage collector de JS).
- Exemple : Un fichier ouvert sans `with` n'est fermé que lorsque le ramasse-miettes détruit l'objet : moment non garanti.
- Alias : garbage collector, GC
- Carte : context-managers-with-open-ferme

## record de log
- Définition : Objet `LogRecord` créé à chaque appel de log : message, arguments, niveau, nom du logger, heure, et champs ajoutés.
- Exemple : Un `logging.Filter` ajoute `record.request_id` ; le format l'écrit avec `%(request_id)s`.
- Alias : LogRecord, record, records
- Carte : logging-formatter-champs

## récursion
- Définition : Fonction qui s'appelle elle-même sur une partie plus petite du problème ; aussi, traitement qui descend dans des structures imbriquées.
- Exemple : `fib(n)` appelle `fib(n - 1)` ; `copy.deepcopy` et `dataclasses.asdict` descendent récursivement dans les sous-objets.
- Alias : récursif, récursive, récursivement
- Carte : decorateurs-cache-recursion

## référence
- Définition : Lien d'une variable vers un objet : affecter ou passer en argument copie la référence, pas l'objet, qui reste partagé.
- Exemple : `b = a` puis `b.append(1)` modifie aussi `a` : les deux noms désignent la même liste.
- Alias : références
- Carte : collections-alias-pas-de-copie

## regex
- Définition : Expression régulière : motif de recherche dans du texte (`^\d{9}$` pour neuf chiffres) ; module `re` en Python.
- Exemple : `pytest.raises(ValueError, match="date invalide")` applique `re.search` au message de l'exception.
- Alias : expression régulière, expressions régulières
- Carte : tests-match-casse-ancres

## répertoire central
- Définition : Table des entrées d'une archive zip, écrite à la fin du fichier à sa fermeture ; elle permet de lire une entrée sans parcourir les autres.
- Exemple : Un zip écrit sans `close()` n'a pas de répertoire central : `BadZipFile` à l'ouverture.
- Alias : central directory
- Carte : archives-zipfile-lire

## REPL
- Définition : Read-Eval-Print Loop : console interactive de Python (`python` sans fichier) qui exécute chaque ligne tapée et affiche le résultat.
- Exemple : `exit()` est fait pour le REPL ; dans un script, `sys.exit(main())`.
- Alias : console Python
- Carte : ligne-de-commande-code-de-sortie

## repr
- Définition : Représentation d'un objet pour le développeur (`repr(x)`), souvent réécrivable en code : guillemets visibles pour une chaîne, ce n'est pas du JSON.
- Exemple : `repr("")` vaut `"''"`, lisible dans un message d'erreur, là où `str("")` n'affiche rien.
- Alias : __repr__, !r
- Carte : exceptions-message-repr

## requirements.txt
- Définition : Fichier texte qui liste des dépendances Python, une par ligne, souvent avec leur version exacte ; format historique de pip.
- Exemple : `uv export` écrit un `requirements.txt` figé que le build de la Lambda installe dans le dossier à zipper.
- Alias : requirements
- Carte : packaging-plage-lib-vs-lock

## résolution de dépendances
- Définition : Calcul par l'outil de paquets d'un jeu de versions qui satisfait toutes les contraintes du projet et de ses dépendances.
- Exemple : uv résout pour toute la plage `requires-python` : une dépendance exigeant Python 3.13 échoue si le projet promet 3.12.
- Alias : résolution, résoudre
- Carte : packaging-requires-python-resolution

## respx
- Définition : Bibliothèque de test qui intercepte les requêtes httpx et renvoie des réponses déclarées par route (≈ msw).
- Exemple : `respx.get(URL).mock(side_effect=[r429, r200])` teste le retry du client BODACC sans réseau.
- Carte : tests-respx-side-effect

## rglob
- Définition : Méthode `Path.rglob(motif)` qui liste récursivement les fichiers d'un dossier et de ses sous-dossiers, dans un ordre non garanti.
- Exemple : `sorted(src.rglob("*"))` donne un ordre stable pour construire un zip reproductible.
- Carte : archives-ordre-des-entrees

## scalaire
- Définition : Valeur simple, non composée : nombre, chaîne, booléen ou `null` en JSON, par opposition à un objet ou un tableau.
- Exemple : `json.loads("42")` renvoie un scalaire, `42`, pas un dict : vérifier le type avant `r["clé"]`.
- Alias : scalaires
- Carte : json-racine-scalaire

## sdist
- Définition : Source distribution : archive `.tar.gz` des sources d'un paquet Python, à reconstruire en wheel au moment de l'installer.
- Exemple : `uv build` produit un sdist et un wheel ; une Lambda n'installe que des wheels.
- Alias : source distribution
- Carte : packaging-wheel-vs-sdist

## seek
- Définition : Méthode `f.seek(n)` qui déplace la position de lecture ou d'écriture dans un objet fichier ; `seek(0)` revient au début.
- Exemple : Après `t.write(b"A1")`, `t.seek(0)` est nécessaire avant `t.read()`, sinon on lit à la fin.
- Carte : compression-seek-sequentiel

## sémaphore
- Définition : Compteur qui limite le nombre de tâches pouvant entrer en même temps dans une section (`asyncio.Semaphore(10)`).
- Exemple : Borner à dix les requêtes simultanées vers une API pour respecter son quota.
- Carte : http-asyncio-gather

## sentinelle
- Définition : Valeur spéciale, souvent `None`, qui signifie « non fourni » et déclenche un comportement par défaut.
- Exemple : `def f(now=None): now = now or datetime.now(PARIS)` lit l'horloge à chaque appel.
- Alias : valeur sentinelle
- Carte : dates-now-none-injectable

## sérialisation
- Définition : Conversion d'un objet en texte ou en octets pour l'écrire ou l'envoyer (JSON, par exemple) ; la désérialisation fait l'inverse.
- Exemple : `json.dumps` ne sait pas sérialiser une `date` : `default=` ou `model_dump_json` s'en chargent.
- Alias : sérialiser, sérialisé, sérialisable, désérialisation
- Carte : json-default-dates

## set
- Définition : Collection sans doublons ni ordre (`{1, 2}`), au test d'appartenance très rapide ; ses éléments doivent être hashables (≈ `Set` en TS).
- Exemple : `sirens_hier - sirens_aujourdhui` donne les SIREN disparus entre deux journées.
- Alias : sets, ensemble
- Carte : collections-set-unicite

## sha256
- Définition : SHA-256 : fonction de hachage qui résume n'importe quels octets en 32 octets (64 caractères hexadécimaux) ; un octet changé change tout.
- Exemple : Le `_MANIFEST.json` d'une partition porte le sha256 du JSONL non compressé, preuve d'un rejeu identique.
- Alias : SHA-256, hashlib
- Carte : hachage-sha256-empreinte

## signature de fonction
- Définition : Liste des paramètres d'une fonction (noms, défauts, types, `*args`) ; `inspect.signature(f)` la renvoie.
- Exemple : Un faux client reprend la signature exacte de `upload_file(filename, bucket, key, ExtraArgs=None)` de boto3.
- Alias : signatures, signature Python
- Carte : decorateurs-wrapped-sans-cache

## singleton
- Définition : Objet dont il n'existe qu'une instance, partagée par tout le programme.
- Exemple : `@cache def s3_client()` crée le client S3 au premier appel et rend toujours le même ensuite.
- Alias : singletons
- Carte : decorateurs-cache-singleton

## site-packages
- Définition : Dossier d'un environnement Python où sont installés les paquets tiers ; Python y cherche les imports.
- Exemple : `.venv/lib/python3.12/site-packages/httpx/` contient le code de httpx installé par uv.
- Carte : packaging-installation-editable

## snake_case
- Définition : Style de nommage en minuscules avec des soulignés (`date_parution`), convention Python pour variables et fonctions.
- Exemple : L'option `--dry-run` devient l'attribut `args.dry_run` ; la clé d'API `dateParution` devient `date_parution`.
- Carte : ligne-de-commande-tiret-souligne

## sous-processus
- Définition : Programme lancé par un script Python (`subprocess.run`), qui tourne dans son propre processus avec ses sorties et son code de retour.
- Exemple : Le script de build lance `uv export` puis `uv pip install` en sous-processus.
- Alias : subprocess, processus enfant
- Carte : sous-processus-run-lancer

## src layout
- Définition : Organisation d'un paquet où le code vit dans `src/<paquet>/` et non à la racine, pour que les tests importent la version installée.
- Exemple : `packages/bodacc-client/src/bodacc_client/` n'est importable qu'une fois le paquet installé par `uv sync`.
- Alias : disposition src
- Carte : packaging-src-layout

## st_mode
- Définition : Champ renvoyé par `os.stat` qui code le type d'un fichier (fichier, dossier, lien) et ses droits Unix.
- Exemple : `oct(os.stat(p).st_mode)[-3:]` vaut `"600"` pour un fichier créé par `mkstemp`.
- Carte : archives-external-attr-type-fichier

## stdlib
- Définition : Bibliothèque standard de Python : les modules livrés avec le langage (`json`, `gzip`, `datetime`, `pathlib`), sans rien installer.
- Exemple : `statistics` est dans la stdlib : moyenne et médiane sans dépendance externe.
- Alias : bibliothèque standard, standard library
- Carte : collections-statistics-moyenne-mediane

## StopIteration
- Définition : Exception que lève `next()` quand un itérateur est épuisé ; une boucle `for` l'attrape seule et s'arrête.
- Exemple : `next(g, None)` renvoie `None` au lieu de lever `StopIteration` sur un générateur vide.
- Carte : generateurs-next-stopiteration

## surrogate
- Définition : Moitié d'une paire de codes UTF-16 qui note un caractère hors du plan de base (emoji) ; isolé, il n'est pas un caractère valide.
- Exemple : `"\ud800"` passe `json.dumps(ensure_ascii=False)` mais lève `UnicodeEncodeError` à l'`encode("utf-8")`.
- Alias : surrogates, surrogate isolé
- Carte : json-surrogate-isole

## sys.argv
- Définition : Liste des arguments de la ligne de commande : `sys.argv[0]` est le script, la suite les options (≈ `process.argv`).
- Exemple : `parse_args(None)` lit `sys.argv[1:]` ; un test passe sa propre liste à `main(argv)`.
- Alias : argv
- Carte : ligne-de-commande-parse-args-none

## sys.path
- Définition : Liste des dossiers où Python cherche les modules à l'import, dossier courant ou du script en tête.
- Exemple : En src layout, `src/` n'est pas sur `sys.path` : on teste le paquet installé, pas le dossier.
- Carte : packaging-src-layout

## SystemExit
- Définition : Exception levée par `sys.exit(code)` ; non attrapée, elle termine le programme avec ce code de sortie.
- Exemple : `pytest.raises(SystemExit)` puis `exc.value.code == 2` vérifie une erreur d'usage d'argparse.
- Alias : sys.exit
- Carte : ligne-de-commande-code-de-sortie

## tâche concurrente
- Définition : Travail qui progresse en même temps que d'autres, en alternance (asyncio) ou en parallèle (threads, processus).
- Exemple : `asyncio.TaskGroup` lance plusieurs requêtes concurrentes et regroupe leurs erreurs dans un `ExceptionGroup`.
- Alias : tâches concurrentes
- Carte : exceptions-exceptiongroup-except-etoile

## tampon
- Définition : Zone mémoire où des données s'accumulent avant d'être écrites ou lues en bloc ; vidée par `flush()` ou à la fermeture.
- Exemple : Dans le bloc `with`, la taille d'un fichier gzip peut valoir 0 : les données sont encore dans le tampon.
- Alias : tampons, buffer, mémoire tampon
- Carte : context-managers-taille-apres-bloc

## tarfile
- Définition : Module standard qui lit et écrit les archives `.tar` (souvent `.tar.gz`), lues de façon séquentielle, contrairement au zip.
- Exemple : `tarfile.extractall(dest, filter="data")` refuse les chemins `../` d'une archive hostile.
- Alias : tar, .tar.gz
- Carte : archives-extractall-zip-slip

## tempfile
- Définition : Module standard qui crée fichiers et dossiers temporaires au nom unique (`TemporaryDirectory`, `NamedTemporaryFile`), supprimés à la sortie du `with`.
- Exemple : La Lambda écrit la partition dans un `TemporaryDirectory()` sous `/tmp`, puis l'envoie à S3.
- Alias : fichier temporaire, fichiers temporaires, TemporaryDirectory
- Carte : fichiers-temporaires-temporarydirectory-jetable

## temps constant
- Définition : Coût qui ne dépend pas de la taille des données, noté O(1) ; aussi, comparaison qui prend toujours le même temps.
- Exemple : `x in mon_set` répond en temps constant, même sur 100 000 SIREN.
- Alias : O(1)
- Carte : collections-set-unicite

## temps linéaire
- Définition : Coût proportionnel à la taille des données, noté O(n) : deux fois plus d'éléments, deux fois plus de temps.
- Exemple : `x in ma_liste` parcourt la liste : temps linéaire, lent si on le répète en boucle.
- Alias : O(n)
- Carte : listes-in-index-count

## test d'intégration
- Définition : Test qui fait parler le code à de vrais services (réseau, API, compte AWS de dev), plus lent et moins isolé qu'un test unitaire.
- Exemple : `make test-integration` lance les tests marqués `integration` contre la vraie API BODACC.
- Alias : tests d'intégration
- Carte : tests-marqueur-exclure-integration

## thread
- Définition : Fil d'exécution d'un processus ; plusieurs threads partagent la même mémoire et peuvent tourner en même temps.
- Exemple : Deux threads qui ratent le même `@cache` en même temps exécutent tous deux la fonction.
- Alias : threads, ThreadPoolExecutor
- Carte : decorateurs-cache-threads

## timedelta
- Définition : Durée en Python (`datetime.timedelta`) : différence entre deux dates, ou décalage à ajouter, en jours, secondes, microsecondes.
- Exemple : `day + timedelta(days=1)` passe au jour suivant ; `(end - start).days + 1` compte les jours d'une plage.
- Carte : dates-timedelta-ecart

## timestamp Unix
- Définition : Nombre de secondes écoulées depuis le 1er janvier 1970 à minuit UTC ; manière universelle de noter un instant.
- Exemple : L'en-tête gzip stocke un timestamp Unix ; `mtime=0` signifie « pas d'horodatage ».
- Alias : horodatage Unix, epoch
- Carte : compression-mtime-zero

## TOCTOU
- Définition : Time Of Check to Time Of Use : faille où l'état vérifié change avant d'être utilisé, par exemple un nom de fichier libre pris entre-temps.
- Exemple : `tempfile.mktemp()` donne un nom libre qu'un autre processus peut créer avant vous ; `mkstemp` crée le fichier aussitôt.
- Alias : race condition, condition de course
- Carte : fichiers-temporaires-mktemp-obsolete

## trace d'erreur
- Définition : Pile des appels affichée quand une exception remonte, de l'appel le plus externe à la ligne qui a levé (≈ stack trace).
- Exemple : `logger.exception(…)` écrit la trace complète dans CloudWatch ; `str(exc)` seul la perd.
- Alias : traceback, trace, stack trace, traces d'erreur
- Carte : logging-exception-trace

## tranche
- Définition : Sous-partie d'une séquence `l[début:fin:pas]`, fin exclue ; elle renvoie une copie et ne lève jamais `IndexError` (≈ `slice`).
- Exemple : `sirens[:3]` prend les trois premiers, `l[::-1]` inverse, `l[:]` copie.
- Alias : tranches, slice
- Carte : listes-tranches-bornes-pas

## transport HTTP
- Définition : Couche de httpx qui envoie réellement les octets sur le réseau ; on peut la remplacer pour simuler un serveur ou régler les retries.
- Exemple : `httpx.Client(transport=httpx.MockTransport(handler))` répond sans réseau dans un test.
- Alias : transport, MockTransport, HTTPTransport
- Carte : http-mocktransport

## tri stable
- Définition : Tri qui garde l'ordre d'origine des éléments égaux ; celui de Python l'est, ce qui permet de trier en plusieurs passes.
- Exemple : Trier par SIREN, puis par date : à date égale, les annonces restent classées par SIREN.
- Carte : listes-sorted-key

## try/finally
- Définition : Bloc dont la partie `finally` s'exécute toujours, erreur ou non, même après un `return` : la base du nettoyage.
- Exemple : `with` équivaut à un `try/finally` qui ferme la ressource dans le `finally`.
- Alias : finally, try
- Carte : exceptions-else-finally

## tuple
- Définition : Séquence ordonnée non modifiable (`(1, 2)`), créée par la virgule ; hashable si ses éléments le sont (≈ `readonly [a, b]`).
- Exemple : `return count, sha` renvoie un tuple ; `(jour, tribunal)` sert de clé composée dans un dict.
- Alias : tuples
- Carte : collections-tuple-fige

## Unicode
- Définition : Norme qui donne un numéro unique (point de code) à chaque caractère de toutes les écritures ; UTF-8 en est l'encodage le plus courant.
- Exemple : « é » est U+00E9 ; Python 3 manipule tout texte (`str`) en Unicode.
- Carte : texte-nombres-unicode-nfc

## UTC
- Définition : Temps universel coordonné : heure de référence mondiale, sans heure d'été ; les autres fuseaux s'expriment en décalage (UTC+2).
- Exemple : Lambda tourne en UTC : 22:30 UTC le 24 octobre est déjà le 25 à Paris.
- Alias : timezone.utc
- Carte : dates-naif-ou-aware

## UTF-8
- Définition : Encodage Unicode le plus répandu : 1 octet pour l'ASCII, 2 à 4 pour les autres caractères (2 pour « é »).
- Exemple : `"Créteil".encode("utf-8")` fait 8 octets pour 7 caractères.
- Alias : utf8
- Carte : json-len-caracteres-octets

## UUID
- Définition : Universally Unique Identifier : identifiant de 128 bits, écrit en 36 caractères hexadécimaux et tirets, quasi certain d'être unique sans coordination.
- Exemple : `uuid.uuid4()` génère un identifiant aléatoire ; `json.dumps` ne sait pas l'écrire sans `default=str`.
- Alias : uuid4, GUID
- Carte : json-default-dates

## valeur fausse
- Définition : Valeur traitée comme fausse dans un `if` : `None`, `False`, `0`, `""`, `[]`, `{}` ; toute autre est vraie (≈ falsy).
- Exemple : `d.get("nb") or 5` remplace aussi un vrai `0` par 5 : tester `is None` pour un nombre.
- Alias : valeurs fausses, falsy, faux en booléen
- Carte : dictionnaires-get-ou-or

## valeur par défaut
- Définition : Valeur d'un paramètre quand l'appel ne le fournit pas ; en Python, elle est évaluée une seule fois, à la définition de la fonction.
- Exemple : `def f(acc=[])` partage la même liste entre tous les appels ; écrire `acc=None` puis créer la liste.
- Alias : valeurs par défaut, défaut mutable
- Carte : validation-defaut-mutable

## ValidationError
- Définition : Exception de Pydantic qui regroupe toutes les erreurs d'une validation, chacune avec son chemin (`loc`), son type et son message.
- Exemple : `e.errors()` liste `("personnes", 0, "siren")` : le SIREN de la première personne est invalide.
- Carte : validation-validationerror-erreurs

## venv
- Définition : Environnement virtuel : dossier (`.venv`) avec son propre interpréteur Python et ses paquets, isolé des autres projets (≈ `node_modules` plus la version de Node).
- Exemple : `uv sync` crée `.venv` à la racine du monorepo ; `uv run pytest` exécute pytest avec ce Python-là.
- Alias : .venv, environnement virtuel, virtualenv
- Carte : packaging-python-m

## vue
- Définition : Objet renvoyé par `d.keys()`, `d.values()`, `d.items()` : il reflète le dict en direct, sans copie.
- Exemple : `a.keys() - b.keys()` donne les champs présents dans une annonce et absents de l'autre.
- Alias : vues
- Carte : dictionnaires-vues-ensemblistes

## warning
- Définition : Avertissement émis par le module `warnings` (`UserWarning`, `DeprecationWarning`) : affiché sans interrompre le programme.
- Exemple : Écrire deux fois `a.py` dans un zip émet un `UserWarning` ; `simplefilter("error")` le change en exception.
- Alias : warnings, UserWarning, avertissement
- Carte : archives-doublon-meme-nom

## wheel
- Définition : Paquet Python prêt à installer (`.whl`, un zip) : on le décompresse dans site-packages sans étape de build.
- Exemple : Le zip de la Lambda est fait de wheels Linux aarch64, jamais du `.venv` du Mac.
- Alias : wheels, .whl, roue, roues
- Carte : packaging-wheel-vs-sdist

## yield
- Définition : Mot-clé qui rend une valeur depuis un générateur et le met en pause jusqu'à la demande suivante.
- Exemple : `for ligne in r.iter_lines(): yield json.loads(ligne)` rend les annonces une à une.
- Alias : yield from
- Carte : generateurs-yield-a-la-demande

## zip
- Définition : Format d'archive qui regroupe plusieurs fichiers, chacun compressé à part, avec une table des entrées en fin de fichier ; module `zipfile`.
- Exemple : Le code d'une Lambda est livré en `.zip` publié dans le bucket d'artefacts sous son hash.
- Alias : .zip, zipfile, archive zip
- Carte : archives-zipfile-ecrire

## ZIP64
- Définition : Extension du format zip pour les archives ou entrées de plus de 4 Gio, ou de plus de 65 535 fichiers.
- Exemple : `zf.open(info, "w", force_zip64=True)` pour écrire en flux une entrée qui peut dépasser 2 Gio.
- Alias : force_zip64
- Carte : archives-open-ecrire-en-flux

## ZipInfo
- Définition : Objet `zipfile.ZipInfo` qui décrit une entrée d'archive : nom, date, droits, compression ; passé à `writestr` pour fixer ces valeurs.
- Exemple : `ZipInfo("handler.py", date_time=(1980, 1, 1, 0, 0, 0))` rend l'entrée indépendante de l'horloge.
- Carte : archives-zipinfo-date-fixe

## ZoneInfo
- Définition : Classe `zoneinfo.ZoneInfo` qui charge un fuseau IANA par son nom, avec ses règles d'heure d'été.
- Exemple : `PARIS = ZoneInfo("Europe/Paris")` en constante de module, puis `now.astimezone(PARIS).date()`.
- Carte : dates-zoneinfo-nom-iana
