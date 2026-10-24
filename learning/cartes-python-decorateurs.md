---
title: "Cartes · Décorateurs Python"
type: cartes
langage: Python
cours: Décorateurs
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Décorateurs Python
Python · Décorateurs : bases, stdlib, motifs, pièges (format spec v3 de revision-pwa).

## 1. décorateur : une fonction qui en renvoie une autre
- Sous-thème : bases
- Niveau : 1
- Définition : Un décorateur est une fonction qui reçoit une fonction et en renvoie une nouvelle, enrichie (≈ fonction d'ordre supérieur en TS).
- Contexte : En Python, une fonction est un objet comme un autre : on la passe en argument, on la renvoie, on la réaffecte. Le décorateur définit une fonction interne qui appelle l'originale et ajoute un comportement autour (log, mesure, contrôle). Il renvoie la fonction interne **sans l'appeler** : c'est elle qui remplace l'originale, et c'est elle qui tournera à chaque appel.
- Usage : ✅ ajouter le même comportement à plusieurs fonctions (log, retry, chrono) sans toucher à leur code · ❌ comportement propre à une seule fonction : l'écrire directement dedans.

```python
# Exemple 1 : envelopper à la main
def crier(f):
    def nouvelle():
        return f().upper()
    return nouvelle  # sans ()

def saluer():
    return "bonjour"

saluer = crier(saluer)  # remplacée
saluer()       # → "BONJOUR"
```

```python
# Exemple 2 : l'originale reste dispo
def crier(f):
    def nouvelle():
        return f().upper()
    return nouvelle

def saluer():
    return "bonjour"

fort = crier(saluer)  # autre nom
saluer()       # → "bonjour"
fort()         # → "BONJOUR"
```

- Quiz : Si `crier` termine par `return nouvelle()` (avec parenthèses), que fait `saluer()` après `saluer = crier(saluer)` ?
- [ ] Renvoie `"BONJOUR"`
- [ ] Renvoie `"bonjour"`
- [x] Lève `TypeError`
- [ ] Renvoie `None`
- Réponse : `TypeError` ('str' object is not callable) : `crier` a renvoyé le résultat `"BONJOUR"`, une chaîne, et non la fonction.

## 2. @ : un simple raccourci
- Sous-thème : bases
- Niveau : 1
- Définition : `@deco` au-dessus d'un `def f` équivaut à écrire `f = deco(f)` juste après la définition.
- Contexte : Le `@` n'ajoute aucune magie : Python définit la fonction, la passe au décorateur, puis lie le nom `f` à **ce que le décorateur renvoie**. Si le décorateur renvoie autre chose qu'une fonction, `f` devient cette autre chose. Contrairement aux décorateurs TS (expérimentaux, réservés aux classes), ceux de Python s'appliquent aussi aux fonctions libres.
- Usage : ✅ appliquer un décorateur à la définition, lisible en tête de fonction · ❌ besoin de garder aussi la version non décorée : appeler `deco(f)` à la main sous un autre nom.

```python
# Exemple 1 : la même chose avec @
def crier(f):
    def nouvelle():
        return f().upper()
    return nouvelle
@crier   # saluer = crier(saluer)
def saluer():
    return "bonjour"

saluer()       # → "BONJOUR"
```

```python
# Exemple 2 : le nom de l'interne
def crier(f):
    def nouvelle():
        return f().upper()
    return nouvelle

@crier
def saluer():
    return "bonjour"

saluer.__name__  # → "nouvelle"
```

- Quiz : Si `crier` oublie sa ligne `return nouvelle`, que fait l'appel `saluer()` ?
- [ ] Renvoie `"bonjour"`
- [ ] Renvoie `None`
- [ ] Renvoie `"BONJOUR"`
- [x] Lève `TypeError`
- Réponse : `TypeError` ('NoneType' object is not callable) : `@crier` lie `saluer` à ce que renvoie `crier`, ici `None`.

## 3. décorateur : quand il s'exécute
- Sous-thème : bases
- Niveau : 1
- Définition : Le corps du décorateur s'exécute **une fois**, à la définition de la fonction (souvent à l'import du module), pas à chaque appel.
- Contexte : Deux moments à distinguer : le code du décorateur lui-même tourne quand Python lit le `def` ; le code de la fonction interne tourne à chaque appel. Un décorateur qui enregistre la fonction dans un registre (routes Flask, tâches, handlers) agit donc dès l'import, avant tout appel. Un `print` dans le décorateur s'affiche une seule fois.
- Usage : ✅ enregistrer une fonction dans un registre (routes, handlers par type d'annonce) · ❌ travail à refaire à chaque appel : le mettre dans la fonction interne.

```python
# Exemple 1 : il tourne au def
appels = []
def tracer(f):
    appels.append(f.__name__)
    return f   # f telle quelle
@tracer
def charger():
    return "ok"
appels   # → ["charger"]  (sans appel)
```

```python
# Exemple 2 : un registre de handlers
HANDLERS = {}

def handler(f):
    HANDLERS[f.__name__] = f
    return f

@handler
def radiation(a):
    return f"radiée {a}"

HANDLERS["radiation"]("483609327")
# → "radiée 483609327"
```

- Quiz : Avec l'exemple 1, que vaut `len(appels)` après trois appels `charger()` ?
- [ ] `3`
- [x] `1`
- [ ] `4`
- [ ] `0`
- Réponse : `1` : `tracer` n'a tourné qu'à la définition ; les appels exécutent `charger` elle-même, qui n'ajoute rien.

## 4. décorateur générique : *args, **kwargs
- Sous-thème : bases
- Niveau : 1
- Définition : Un décorateur générique définit une fonction interne `(*args, **kwargs)` qui transmet tous les arguments à `f` et renvoie son résultat.
- Contexte : La fonction interne **remplace** l'originale : elle doit donc accepter n'importe quels arguments et les retransmettre tels quels, `*args` pour les positionnels, `**kwargs` pour les nommés (≈ `(...args) => f(...args)` en TS). Elle doit aussi renvoyer le résultat de `f` : oublier ce `return` est le bug classique, la fonction décorée renvoie alors `None`.
- Usage : ✅ tout décorateur réutilisable (chrono, log, retry sur un appel BODACC) · ❌ décorateur lié à une signature précise : l'écrire avec les vrais paramètres pour garder l'autocomplétion.

```python
# Exemple 1 : un chrono générique
import time
def chrono(f):
    def interne(*args, **kwargs):
        t0 = time.perf_counter()
        r = f(*args, **kwargs)
        fin = time.perf_counter()
        interne.duree = fin - t0
        return r   # le résultat
    return interne

@chrono
def somme(a, b=0):
    return a + b

somme(2, b=3)    # → 5
somme.duree > 0  # → True
```

```python
# Exemple 2 : oublier le return
def tracer(f):
    def interne(*args, **kwargs):
        f(*args, **kwargs)  # oubli
    return interne

@tracer
def doubler(x):
    return x * 2

doubler(4)     # → None
```

- Quiz : Si `interne` est écrit `def interne():` (sans `*args, **kwargs`), que fait `somme(2)` ?
- [ ] Renvoie `2`
- [x] Lève `TypeError`
- [ ] Renvoie `None`
- [ ] Lève `NameError`
- Réponse : `TypeError` (takes 0 positional arguments but 1 was given) : c'est `interne` qui reçoit l'appel, et elle n'accepte aucun argument.

## 5. @cache : mémoriser
- Sous-thème : stdlib
- Niveau : 1
- Définition : `functools.cache` mémorise le résultat pour chaque combinaison d'arguments : le second appel identique ne réexécute pas la fonction.
- Contexte : Le cache est un dict dont la clé est faite des arguments : ils doivent donc être hachables (`str`, nombres, tuples). Il n'est jamais vidé et grossit sans limite ; `lru_cache(maxsize=…)` garde seulement les N derniers. Il ne convient qu'aux fonctions pures : même entrée, même sortie, sans effet de bord attendu à chaque appel. `f.cache_clear()` le vide.
- Usage : ✅ lookup stable et coûteux (libellé d'un code tribunal, référentiel) · ❌ résultat qui change dans le temps (appel API du jour) ou arguments non hachables (listes, dicts).

```python
# Exemple 1 : un seul vrai calcul
from functools import cache
appels = []
@cache
def tribunal(code):
    appels.append(code)
    return f"Tribunal {code}"
tribunal("7501"); tribunal("7501")
len(appels)    # → 1  (2e : en cache)
```

```python
# Exemple 2 : inspecter et vider
from functools import cache

@cache
def tribunal(code):
    return f"Tribunal {code}"

tribunal("7501")
tribunal("7501")
tribunal.cache_info().hits  # → 1
tribunal.cache_clear()
tribunal.cache_info().hits  # → 0
```

- Quiz : Que fait `tribunal(["7501"])` (une liste en argument) ?
- [ ] Renvoie `"Tribunal ['7501']"`
- [ ] Renvoie le résultat sans le mettre en cache
- [x] Lève `TypeError`
- [ ] Lève `KeyError`
- Réponse : `TypeError` (unhashable type: 'list') : le cache range les arguments comme clé de dict, ils doivent être hachables.

## 6. décorateur : transformer les arguments
- Sous-thème : bases
- Niveau : 1
- Définition : La fonction interne peut modifier les arguments avant d'appeler `f`, ou son résultat avant de le renvoyer : nettoyage, conversion, valeur par défaut.
- Contexte : `interne` reçoit l'appel en premier : elle voit `args` (tuple) et `kwargs` (dict) bruts et décide de ce que `f` reçoit vraiment. Piège : un argument peut arriver par position **ou** par nom ; lire `args[0]` suppose un appel positionnel. Pour un paramètre précis, le nommer dans la signature de `interne` (`def interne(siren, *a, **kw)`) couvre les deux formes.
- Usage : ✅ normaliser une entrée commune à plusieurs fonctions (SIREN sans espaces, date en `str`) · ❌ conversion propre à une seule fonction : l'écrire dans la fonction ; validation riche : pydantic.

```python
# Exemple 1 : normaliser le SIREN
def normaliser(f):
    def interne(*args, **kw):
        s = args[0].replace(" ", "")
        return f(s, *args[1:], **kw)
    return interne
@normaliser
def cle(siren):
    return f"siren={siren}"
cle("483 609 327")  # → "siren=483609327"
```

```python
# Exemple 2 : transformer le résultat
def en_set(f):
    def interne(*a, **kw):
        return set(f(*a, **kw))
    return interne

@en_set
def sirens():
    return ["483609327", "483609327"]

sirens()   # → {"483609327"}
```

- Quiz : Avec l'exemple 1, que fait l'appel par nom `cle(siren="483 609 327")` ?
- [ ] Renvoie `"siren=483609327"`
- [ ] Renvoie `"siren=483 609 327"`
- [x] Lève `IndexError`
- [ ] Lève `TypeError`
- Réponse : `IndexError` : l'argument nommé arrive dans `kw`, `args` est vide, donc `args[0]` échoue ; nommer `siren` dans la signature de `interne`.

## 7. décorateur : intercepter une erreur
- Sous-thème : bases
- Niveau : 1
- Définition : La fonction interne entoure l'appel de `f` d'un `try/except` pour journaliser, convertir ou relancer ses exceptions.
- Contexte : C'est le décorateur le plus courant après le chrono : `except` attrape ce que `f` lève, puis soit `raise` (relance la même exception, trace intacte), soit `raise MonErreur(...) from e` (convertit en gardant la cause), soit renvoie une valeur de repli. Le piège : un `except` qui ne relance pas avale l'erreur en silence, la fonction décorée renvoie alors `None`.
- Usage : ✅ traduire les erreurs d'une couche (`KeyError` → `BodaccError`), journaliser chaque échec d'une Lambda · ❌ attraper `Exception` sans relancer : l'erreur disparaît des logs et l'appelant continue avec `None`.

```python
# Exemple 1 : convertir l'erreur
class BodaccError(Exception):
    pass
def api(f):
    def interne(*a, **kw):
        try:
            return f(*a, **kw)
        except KeyError as e:
            raise BodaccError(e) from e
    return interne
@api
def resultats(r):
    return r["results"]
resultats({"error_code": "X"})  # ❌ BodaccError
```

```python
# Exemple 2 : journaliser puis relancer
log = []
def tracer(f):
    def interne(*a, **kw):
        try:
            return f(*a, **kw)
        except Exception as e:
            log.append(type(e).__name__)
            raise      # la même, trace intacte
    return interne

@tracer
def div(a, b):
    return a / b

try:
    div(1, 0)
except ZeroDivisionError:
    pass
log    # → ["ZeroDivisionError"]
```

- Quiz : Dans l'exemple 2, sans la ligne `raise`, que fait `div(1, 0)` ?
- [x] Renvoie `None`
- [ ] Lève `ZeroDivisionError`
- [ ] Renvoie `0`
- [ ] Lève `RuntimeError`
- Réponse : Renvoie `None` : l'exception est attrapée et jamais relancée ; `interne` arrive au bout sans `return`.

## 8. @wraps : garder l'identité
- Sous-thème : bases
- Niveau : 2
- Définition : `functools.wraps(f)` recopie sur la fonction interne le nom, la docstring et `__wrapped__` de `f`, pour que logs et outils la reconnaissent.
- Contexte : Sans `@wraps`, la fonction décorée s'appelle `interne` partout : traces d'erreur, logs CloudWatch, `help()`, rapports pytest. `wraps` est lui-même un décorateur, appliqué à la fonction interne. Il ajoute `__wrapped__`, qui pointe vers l'originale : pratique pour tester la fonction sans son décorateur. Réflexe : tout décorateur maison commence par `@wraps(f)`.
- Usage : ✅ systématiquement, dans tout décorateur qui renvoie une fonction interne · ❌ décorateur qui renvoie `f` elle-même (registre) : rien à recopier.

```python
# Exemple 1 : nom et doc conservés
from functools import wraps
def tracer(f):
    @wraps(f)
    def interne(*args, **kwargs):
        return f(*args, **kwargs)
    return interne
@tracer
def doubler(x):
    """Double x."""
    return x * 2

doubler.__name__  # → "doubler"
doubler.__doc__   # → "Double x."
```

```python
# Exemple 2 : retrouver l'originale
from functools import wraps

def crier(f):
    @wraps(f)
    def interne():
        return f().upper()
    return interne

@crier
def saluer():
    return "bonjour"

saluer()              # → "BONJOUR"
saluer.__wrapped__()  # → "bonjour"
```

- Quiz : Même `tracer` mais **sans** `@wraps(f)` : que vaut `doubler.__name__` ?
- [ ] `"doubler"`
- [ ] `"tracer"`
- [x] `"interne"`
- [ ] `AttributeError`
- Réponse : `"interne"` : sans `wraps`, le nom `doubler` pointe sur la fonction interne, avec son propre nom et sans docstring.

## 9. décorateurs empilés : de bas en haut
- Sous-thème : bases
- Niveau : 2
- Définition : Avec plusieurs décorateurs, le plus proche du `def` s'applique en premier : `@a @b def f` équivaut à `f = a(b(f))`.
- Contexte : L'empilement se lit de bas en haut à la définition, mais l'exécution se lit de haut en bas : le décorateur du haut enveloppe tout, son code « avant » tourne en premier et son code « après » en dernier. L'ordre compte dès que les comportements interagissent : un cache placé au-dessus d'un chrono ne mesure que les vrais calculs, placé dessous il mesure aussi les hits.
- Usage : ✅ combiner des comportements indépendants (log + retry, validator + classmethod) · ❌ pile de plus de 3 décorateurs difficile à suivre : un décorateur unique qui fait tout.

```python
# Exemple 1 : l'ordre d'enveloppe
def gras(f):
    return lambda: f"<b>{f()}</b>"
def italique(f):
    return lambda: f"<i>{f()}</i>"
@gras        # appliqué en 2e
@italique    # appliqué en 1er
def titre():
    return "BODACC"
titre()   # → "<b><i>BODACC</i></b>"
```

```python
# Exemple 2 : la même chose sans @
def gras(f):
    return lambda: f"<b>{f()}</b>"

def italique(f):
    return lambda: f"<i>{f()}</i>"

def titre():
    return "BODACC"

t = gras(italique(titre))
t()       # → "<b><i>BODACC</i></b>"
```

- Quiz : Que renvoie `titre()` si on inverse les deux lignes (`@italique` au-dessus de `@gras`) ?
- [ ] `"<b><i>BODACC</i></b>"`
- [x] `"<i><b>BODACC</b></i>"`
- [ ] `"<b>BODACC</b><i>BODACC</i>"`
- [ ] `"<i>BODACC</i>"`
- Réponse : `"<i><b>BODACC</b></i>"` : c'est maintenant `italique(gras(titre))`, le décorateur du haut enveloppe tout.

## 10. @lru_cache(maxsize=…) : borner le cache
- Sous-thème : stdlib
- Niveau : 2
- Définition : `functools.lru_cache(maxsize=n)` mémorise comme `@cache` mais garde seulement les `n` résultats les plus récemment utilisés.
- Contexte : LRU = least recently used : quand le cache est plein, l'entrée la moins récemment lue est évincée, et un nouvel appel avec ces arguments recalcule. `@cache` équivaut à `lru_cache(maxsize=None)` : jamais vidé, il grossit avec chaque argument distinct. Dans une Lambda dont le conteneur vit des heures, un cache sans borne sur des clés variées (un SIREN par appel) devient une fuite mémoire.
- Usage : ✅ clés nombreuses ou imprévisibles (SIREN, URL) dans un processus qui dure · ❌ petit référentiel fixe (codes tribunaux) : `@cache`, plus simple ; données qui changent : pas de cache, ou un TTL.

```python
# Exemple 1 : seuls les 2 derniers restent
from functools import lru_cache
@lru_cache(maxsize=2)
def tribunal(code):
    return f"Tribunal {code}"
for c in ["7501", "6901", "1301"]:
    tribunal(c)
tribunal.cache_info().currsize  # → 2
```

```python
# Exemple 2 : l'évincé est recalculé
from functools import lru_cache

appels = []

@lru_cache(maxsize=2)
def tribunal(code):
    appels.append(code)
    return code

for c in ["7501", "6901", "1301", "7501"]:
    tribunal(c)
appels  # → ["7501", "6901", "1301", "7501"]
```

- Quiz : `@lru_cache` écrit sans parenthèses ni `maxsize` : combien de résultats garde-t-il au plus ?
- [ ] Aucune limite
- [ ] `1`
- [x] `128`
- [ ] `TypeError` à la définition
- Réponse : `128` : depuis Python 3.8, `@lru_cache` sans parenthèses est accepté et prend la valeur par défaut `maxsize=128`.

## 11. décorateur avec état : nonlocal
- Sous-thème : motifs
- Niveau : 2
- Définition : Un décorateur garde un état entre les appels dans un attribut de la fonction interne, ou dans une variable de la fermeture réaffectée avec `nonlocal`.
- Contexte : La fonction interne voit les variables de la fonction englobante (fermeture), mais dès qu'elle **réaffecte** un nom (`n += 1`), Python le considère local à `interne` : lire avant d'écrire lève `UnboundLocalError`. `nonlocal n` dit « c'est le `n` du niveau au-dessus ». Muter un objet (`liste.append`, `interne.appels += 1`) n'en a pas besoin, car le nom n'est pas réaffecté.
- Usage : ✅ compteur d'appels, quota, dernier résultat, horodatage du dernier appel · ❌ état partagé entre threads : ajouter un verrou ; état complexe : décorateur en classe (`__call__`).

```python
# Exemple 1 : un attribut de la fonction
def compter(f):
    def interne(*a, **kw):
        interne.appels += 1
        return f(*a, **kw)
    interne.appels = 0
    return interne
@compter
def ping():
    return "pong"
ping(); ping()
ping.appels   # → 2
```

```python
# Exemple 2 : nonlocal pour un quota
def limiter(maxi):
    def deco(f):
        n = 0
        def interne(*a, **kw):
            nonlocal n   # le n de deco
            n += 1
            if n > maxi:
                raise RuntimeError("quota")
            return f(*a, **kw)
        return interne
    return deco

@limiter(2)
def appel():
    return 200

appel(); appel()
appel()        # ❌ RuntimeError
```

- Quiz : Dans l'exemple 2, sans la ligne `nonlocal n`, que fait le premier `appel()` ?
- [ ] Renvoie `200`
- [x] Lève `UnboundLocalError`
- [ ] Lève `RuntimeError`
- [ ] Renvoie `None`
- Réponse : `UnboundLocalError` : `n += 1` réaffecte `n`, qui devient local à `interne` et n'a pas encore de valeur à lire.

## 12. décorateur sur une méthode : self dans args
- Sous-thème : motifs
- Niveau : 2
- Définition : Sur une méthode, la fonction interne reçoit l'instance comme premier argument positionnel : `self` arrive dans `args[0]`.
- Contexte : Le décorateur s'applique à la fonction brute, au moment du `class` ; l'objet n'existe pas encore. À l'appel `c.get(x)`, Python lie la fonction décorée à `c` et appelle `interne(c, x)`. Un décorateur générique `(*args, **kwargs)` fonctionne donc tel quel. Pour lire l'état de l'objet (client fermé, quota), écrire `def interne(self, *a, **kw)`.
- Usage : ✅ vérifier un état de l'instance avant chaque méthode (client ouvert, authentifié), journaliser avec le nom de la classe · ❌ signature figée sans `self` ni `*args` : la méthode reçoit un argument de trop.

```python
# Exemple 1 : self arrive en args[0]
def tracer(f):
    def interne(*args, **kw):
        print(type(args[0]).__name__)
        return f(*args, **kw)
    return interne
class Client:
    @tracer
    def get(self, siren):
        return siren
Client().get("483609327")  # → "483609327"
# affiché : Client
```

```python
# Exemple 2 : lire l'état de l'instance
def ouvert(f):
    def interne(self, *a, **kw):
        if self.ferme:
            raise RuntimeError("client fermé")
        return f(self, *a, **kw)
    return interne

class Client:
    ferme = False
    @ouvert
    def get(self, siren):
        return siren

c = Client()
c.ferme = True
c.get("483609327")   # ❌ RuntimeError
```

- Quiz : Si `ouvert` définit `def interne(siren):` et appelle `f(siren)`, que fait `Client().get("483609327")` ?
- [ ] Renvoie `"483609327"`
- [ ] Lève `AttributeError`
- [ ] Lève `RuntimeError`
- [x] Lève `TypeError`
- Réponse : `TypeError` (takes 1 positional argument but 2 were given) : `interne` reçoit `self` en plus du SIREN.

## 13. @total_ordering : un décorateur de classe
- Sous-thème : stdlib
- Niveau : 2
- Définition : Un décorateur de classe reçoit la classe et renvoie une classe ; `functools.total_ordering` y ajoute `<=`, `>` et `>=` à partir de `__eq__` et `__lt__`.
- Contexte : Le principe est le même que pour une fonction : `@deco class C` équivaut à `C = deco(C)`. Le décorateur peut modifier la classe (ajouter des méthodes) ou seulement l'enregistrer, puis la renvoie. `@dataclass` est le décorateur de classe le plus courant. Sans `total_ordering`, définir `__lt__` ne donne pas `>=` : Python lève `TypeError`.
- Usage : ✅ objets métier triables et comparables (annonces par numéro) ; registre de classes (une classe par source) · ❌ dataclass : `@dataclass(order=True)` génère déjà toutes les comparaisons.

```python
# Exemple 1 : < et == suffisent
from functools import total_ordering
@total_ordering
class Annonce:
    def __init__(self, num):
        self.num = num
    def __eq__(self, o):
        return self.num == o.num
    def __lt__(self, o):
        return self.num < o.num
Annonce(3) >= Annonce(2)  # → True
```

```python
# Exemple 2 : un registre de classes
SOURCES = {}

def source(cls):
    SOURCES[cls.__name__] = cls
    return cls     # la classe telle quelle

@source
class Bodacc:
    pass

SOURCES["Bodacc"] is Bodacc  # → True
```

- Quiz : Exemple 1 **sans** `@total_ordering` : que fait `Annonce(3) >= Annonce(2)` ?
- [ ] `True`
- [ ] `False`
- [x] `TypeError`
- [ ] `AttributeError`
- Réponse : `TypeError` : `>=` cherche `__ge__`, puis `__le__` de l'autre côté ; aucun des deux n'existe sans `total_ordering`.

## 14. @cache : le résultat est partagé
- Sous-thème : pièges
- Niveau : 2
- Définition : `@cache` renvoie **le même objet** à chaque appel identique : muter un résultat mis en cache modifie le cache pour tous les appelants.
- Contexte : Le cache stocke une référence, pas une copie (comme un `Map` JS de tableaux). Un appelant qui fait `append` sur la liste reçue change ce que recevront les appels suivants, sans erreur. Solutions : renvoyer un type immuable (`tuple`, `frozenset`), ou copier côté appelant. Autre détail de clé : `f("x")` et `f(jour="x")` sont deux entrées distinctes.
- Usage : ✅ fonctions en cache qui renvoient `tuple`, `frozenset`, `str` ou un objet figé (`frozen=True`) · ❌ renvoyer une `list` ou un `dict` depuis une fonction en cache : un appelant finira par le modifier.

```python
# Exemple 1 : la même liste à chaque appel
from functools import cache
@cache
def sirens(jour):
    return ["483609327"]
a = sirens("2026-10-23")
a.append("552100554")   # ⚠️ modifie le cache
sirens("2026-10-23")
# → ["483609327", "552100554"]
```

```python
# Exemple 2 : renvoyer un tuple
from functools import cache

@cache
def sirens(jour):
    return ("483609327",)   # immuable

a = sirens("2026-10-23")
a.append("552100554")  # ❌ AttributeError
```

- Quiz : Combien de fois le corps de `sirens` s'exécute-t-il pour `sirens("2026-10-23")` puis `sirens(jour="2026-10-23")` ?
- [ ] `1`
- [x] `2`
- [ ] `0`
- [ ] `TypeError` au 2e appel
- Réponse : `2` : la clé du cache est faite des arguments tels que passés ; positionnel et nommé donnent deux clés différentes.

## 15. décorateur à arguments : trois niveaux
- Sous-thème : motifs
- Niveau : 3
- Définition : `@deco(n)` demande trois niveaux : `deco(n)` renvoie le vrai décorateur, qui renvoie la fonction interne.
- Contexte : `@repeter(3)` s'évalue en deux temps : d'abord l'appel `repeter(3)`, qui renvoie un décorateur ; puis ce décorateur reçoit la fonction. D'où une fabrique de décorateurs : `repeter(n)` → `deco(f)` → `interne(*a, **kw)`, chaque niveau voyant les variables du précédent par fermeture. C'est la forme de `@retry(tentatives=3)`, `@field_validator("siren")` ou `@pytest.mark.parametrize(...)`.
- Usage : ✅ décorateur configurable (nombre de retries, délai, nom de logger) · ❌ aucun paramètre : décorateur simple à deux niveaux, plus lisible.

```python
# Exemple 1 : répéter n fois
def repeter(n):
    def deco(f):
        def interne(*a, **kw):
            return [f(*a, **kw)
                    for _ in range(n)]
        return interne
    return deco
@repeter(3)
def ping():
    return "pong"
ping()  # → ["pong", "pong", "pong"]
```

```python
# Exemple 2 : un retry configurable
def retry(n):
    def deco(f):
        def interne(*a, **kw):
            for i in range(n):
                try:
                    return f(*a, **kw)
                except ConnectionError:
                    if i == n - 1:
                        raise
        return interne
    return deco
essais = []
@retry(n=3)
def appel():
    essais.append(1)
    raise ConnectionError("429")
appel()        # ❌ ConnectionError
len(essais)    # → 3
```

- Quiz : Avec l'exemple 1, que fait `ping()` si on écrit `@repeter` sans `(3)` ?
- [ ] Renvoie `["pong"]`
- [ ] Renvoie `"pong"`
- [x] Lève `TypeError`
- [ ] Renvoie `[]`
- Réponse : `TypeError` (deco() missing 1 required positional argument) : `repeter(ping)` a renvoyé `deco`, qui attend une fonction.

## 16. @singledispatch : selon le type
- Sous-thème : stdlib
- Niveau : 3
- Définition : `functools.singledispatch` choisit l'implémentation d'après le type du premier argument, chaque variante ajoutée par `@f.register` (≈ surcharges TS, mais à l'exécution).
- Contexte : La fonction de base sert de repli pour les types non enregistrés. `@f.register` lit l'annotation du premier paramètre pour savoir quel type la variante gère ; on nomme souvent les variantes `_`, seul le nom de base sert à l'appel. Le choix suit l'héritage (MRO) : une variante `int` sert aussi à ses sous-classes. Pour les méthodes, c'est `singledispatchmethod`.
- Usage : ✅ même opération sur plusieurs types d'entrée (date en `str`, `date` ou `datetime`) · ❌ deux ou trois cas : un `if isinstance` est plus lisible.

```python
# Exemple 1 : une variante par type
from datetime import date
from functools import singledispatch
@singledispatch
def jour(v):
    raise TypeError(type(v))
@jour.register
def _(v: date):
    return v.isoformat()
jour(date(2026, 10, 23))
# → "2026-10-23"
```

```python
# Exemple 2 : str et repli
from datetime import date
from functools import singledispatch

@singledispatch
def jour(v):
    raise TypeError(type(v))

@jour.register
def _(v: str):
    return v[:10]

jour("2026-10-23T08:00")
# → "2026-10-23"
jour(3.5)      # ❌ TypeError
```

- Quiz : Avec des variantes `@jour.register` pour `int` et pour `str`, laquelle reçoit `jour(True)` ?
- [ ] Aucune : la fonction de base lève `TypeError`
- [x] La variante `int`
- [ ] La variante `str`
- Réponse : La variante `int` : `bool` hérite de `int`, et le dispatch suit l'héritage (MRO), pas le type exact.

## 17. décorateur optionnel : @deco ou @deco(n=…)
- Sous-thème : motifs
- Niveau : 3
- Définition : Un décorateur accepte les deux écritures `@retry` et `@retry(n=5)` en prenant `f=None` en premier paramètre et les options en mots-clés seuls.
- Contexte : `@retry` appelle `retry(f)` ; `@retry(n=5)` appelle `retry(n=5)`, sans fonction, qui doit alors renvoyer le vrai décorateur. Le test `if f is None` choisit entre les deux. Le `*` rend `n` nommé seulement, mais rien n'empêche un appel positionnel : `retry(5)` prend `5` pour la fonction. C'est la forme de `@dataclass` et `@dataclass(frozen=True)`, ou `@pytest.fixture` et `@pytest.fixture(scope=…)`.
- Usage : ✅ décorateur de bibliothèque avec des réglages par défaut raisonnables · ❌ code applicatif : toujours `@retry()` avec parenthèses, un seul chemin à lire.

```python
# Exemple 1 : les deux écritures
def retry(f=None, *, n=3):
    if f is None:         # @retry(n=5)
        return lambda g: retry(g, n=n)
    def interne(*a, **kw):
        return f(*a, **kw)
    interne.n = n
    return interne
@retry
def a(): return 1
@retry(n=5)
def b(): return 2
(a(), a.n, b(), b.n)  # → (1, 3, 2, 5)
```

- Quiz : Avec ce `retry`, que donne `@retry(5)` au-dessus de `def b(): …` ?
- [ ] `b.n` vaut `5`
- [ ] `b.n` vaut `3`
- [x] `TypeError` dès la définition
- [ ] `TypeError` au premier appel
- Réponse : `TypeError` dès la définition : `retry(5)` prend `5` pour `f` et renvoie `interne`, puis `interne(b)` appelle `5(b)`.

## 18. @cache sur une méthode : instances gardées
- Sous-thème : pièges
- Niveau : 3
- Définition : Sur une méthode, `@cache` met `self` dans la clé : le cache, partagé par la classe, garde chaque instance en vie tant qu'il existe.
- Contexte : Le cache vit sur la fonction, donc au niveau de la classe, pas de l'objet. Chaque instance qui appelle la méthode y laisse une entrée qui la référence : elle n'est jamais libérée par le ramasse-miettes, même après `del`. Il faut aussi que l'objet soit hachable. Ruff le signale (règle B019). Alternatives : `@cached_property` (par instance), un dict dans l'instance, ou une fonction de module en cache qui ne prend pas `self`.
- Usage : ✅ fonction de module en cache appelée par la méthode, `@cached_property` pour une valeur par objet · ❌ `@cache` ou `@lru_cache` directement sur une méthode d'objets nombreux (un par annonce).

```python
# Exemple 1 : self est dans la clé
import gc, weakref
from functools import cache
class Ref:
    @cache
    def libelle(self, code):
        return f"T{code}"
r = Ref()
w = weakref.ref(r)
r.libelle("7501")
del r; gc.collect()
w() is None   # → False  (gardée par le cache)
```

```python
# Exemple 2 : un cache rangé dans l'objet
import gc, weakref

class Ref:
    def __init__(self):
        self._cache = {}
    def libelle(self, code):
        if code not in self._cache:
            self._cache[code] = f"T{code}"
        return self._cache[code]

r = Ref()
w = weakref.ref(r)
r.libelle("7501")
del r; gc.collect()
w() is None   # → True  (libérée)
```

- Quiz : Exemple 1 : deux instances distinctes appellent `libelle("7501")`. Que vaut `Ref.libelle.cache_info().currsize` ?
- [ ] `1`
- [x] `2`
- [ ] `0`
- [ ] `TypeError`
- Réponse : `2` : la clé est `(self, "7501")` ; deux objets différents donnent deux entrées, et le calcul n'est pas partagé.

## 19. décorateur en classe : __call__
- Sous-thème : motifs
- Niveau : 3
- Définition : Une classe sert de décorateur : `__init__` reçoit la fonction, `__call__` remplace l'appel ; l'état vit dans les attributs de l'objet.
- Contexte : `@Compter` fait `ping = Compter(ping)` : `ping` devient une **instance**, appelable grâce à `__call__`. Pratique pour un état riche, mais deux pièges : l'objet n'a ni `__name__` ni docstring (`functools.update_wrapper(self, f)` les recopie), et sur une méthode `self` n'est pas transmis, car une instance n'est pas un descripteur comme une fonction : il faudrait implémenter `__get__`.
- Usage : ✅ décorateur avec un état et des méthodes (stats, reset), sur des fonctions libres · ❌ décorateur de méthodes : une fonction décoratrice, qui gère `self` naturellement.

```python
# Exemple 1 : l'état dans l'objet
class Compter:
    def __init__(self, f):
        self.f = f
        self.appels = 0
    def __call__(self, *a, **kw):
        self.appels += 1
        return self.f(*a, **kw)
@Compter
def ping():
    return "pong"
ping(); ping()
ping.appels   # → 2
```

```python
# Exemple 2 : sur une méthode, self se perd
class Compter:
    def __init__(self, f):
        self.f = f
    def __call__(self, *a, **kw):
        return self.f(*a, **kw)

class Client:
    @Compter
    def get(self, siren):
        return siren

Client().get("483609327")  # ❌ TypeError
```

- Quiz : Dans l'exemple 1, que donne `ping.__name__` ?
- [ ] `"ping"`
- [ ] `"Compter"`
- [ ] `"__call__"`
- [x] `AttributeError`
- Réponse : `AttributeError` : `ping` est une instance de `Compter`, qui n'a pas de `__name__` ; `functools.update_wrapper(self, f)` dans `__init__` le recopierait.

## 20. décorateur sur async def : await dedans
- Sous-thème : pièges
- Niveau : 3
- Définition : Pour décorer une `async def`, la fonction interne doit être elle-même `async def` et faire `await f(...)`.
- Contexte : Appeler une fonction async ne l'exécute pas : ça renvoie une coroutine, exécutée plus tard par la boucle. Une interne synchrone reçoit donc la coroutine, pas le résultat : son `try/except` n'attrape rien, son chrono mesure zéro. Avec `async def interne` et `await`, le code autour de l'appel tourne vraiment avant et après. `inspect.iscoroutinefunction(f)` permet de gérer les deux cas.
- Usage : ✅ retry, log ou chrono autour d'appels `httpx.AsyncClient` · ❌ décorateur synchrone générique posé sur une `async def` : il ne voit jamais l'exception ni la durée.

```python
# Exemple 1 : interne async, avec await
import asyncio
def tracer(f):
    async def interne(*a, **kw):
        r = await f(*a, **kw)
        return f"ok:{r}"
    return interne
@tracer
async def fetch(siren):
    await asyncio.sleep(0)
    return siren
asyncio.run(fetch("483609327"))
# → "ok:483609327"
```

```python
# Exemple 2 : interne sync, rien attrapé
import asyncio

def proteger(f):
    def interne(*a, **kw):
        try:
            return f(*a, **kw)  # coroutine
        except ValueError:
            return None
    return interne

@proteger
async def fetch():
    raise ValueError("429")

asyncio.run(fetch())   # ❌ ValueError
```

- Quiz : Exemple 1 avec `r = f(*a, **kw)` (sans `await`) : que renvoie `asyncio.run(fetch("1"))` ?
- [ ] `"ok:1"`
- [x] `"ok:<coroutine object fetch at …>"`
- [ ] `TypeError`
- [ ] `None`
- Réponse : `"ok:<coroutine …>"` : sans `await`, `r` est la coroutine non exécutée, mise telle quelle dans la chaîne (avec un `RuntimeWarning`).
