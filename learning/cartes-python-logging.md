---
title: "Cartes · Logging Python"
type: cartes
langage: Python
chapitre: Qualité et outillage
cours: Logging
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Logging Python
Python · Logging : loggers, niveaux, handlers, messages, lambda (format spec v3 de revision-pwa).

## 1. logging : WARNING par défaut
- Id : logging-warning-par-defaut
- Sous-thème : niveaux
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : logging-niveaux-entiers
- Voir aussi : logging-basicconfig-une-fois
- Définition : Un logger sans niveau hérite de celui du root, `WARNING` par défaut : `info` et `debug` sont filtrés sans réglage (≈ `console.*` filtrable).
- Contexte : Piège en venant de `console.log` : `log.info(…)` n'écrit rien dans un script non configuré. Les loggers forment un arbre (`bodacc.client` → `bodacc` → root) ; un logger sans niveau prend celui du premier parent réglé. `log.setLevel(logging.INFO)` ou `basicConfig(level=…)` abaisse le seuil. Dans une Lambda, tout ce qui sort sur stdout ou stderr part dans CloudWatch Logs.
- Usage : ✅ régler le niveau au démarrage (`setLevel`, variable `LOG_LEVEL`) · ❌ `print` dans une Lambda : pas de niveau, pas de filtrage.

```python
# Exemple 1 : niveau INFO explicite
import io, logging

buf = io.StringIO()
log = logging.getLogger("ingest8")
log.addHandler(
    logging.StreamHandler(buf))
log.setLevel(logging.INFO)
log.info("début dt=2026-10-23")
buf.getvalue()
# → "début dt=2026-10-23\n"
```

- Quiz : Dans l'exemple 1, sans `log.setLevel(logging.INFO)`, que vaut `buf.getvalue()` ?
- [x] `""`
- [ ] `"début dt=2026-10-23\n"`
- [ ] `"INFO:ingest8:début dt=2026-10-23\n"`
- Réponse : `""` : le logger hérite du niveau du root, `WARNING` par défaut ; `info` est filtré.

## 2. messages : des arguments, pas une f-string
- Id : logging-arguments-pas-fstring
- Sous-thème : messages
- Type : recette
- Niveau : 1
- Profils : débutant, ops, data
- Voir aussi : logging-erreur-format-silencieuse
- Source : data-platform · S1-07
- Définition : `log.info("lu %d annonces", n)` passe les valeurs en arguments : le message n'est formaté que s'il est émis, par le handler.
- Contexte : logging utilise le style `%` (pas `{}`). Une f-string est formatée avant l'appel, même si le niveau filtre la ligne, et chaque ligne devient un texte différent : les outils qui regroupent les messages par modèle ne s'y retrouvent plus. Le record garde le modèle (`msg`) et les valeurs (`args`). Ruff signale la f-string (`G004`).
- Usage : ✅ `%s`, `%d` dans le message, valeurs en arguments · ❌ f-string ou `.format` dans un appel de log ; calcul coûteux en argument : `isEnabledFor`.

```python
# Exemple 1 : formaté à l'émission
import io, logging

buf = io.StringIO()
log = logging.getLogger("ingest8b")
log.addHandler(
    logging.StreamHandler(buf))
log.setLevel(logging.INFO)
log.info("lu %d annonces", 1423)
buf.getvalue()  # → "lu 1423 annonces\n"
```

```python
# Exemple 2 : le modèle reste dans le record
import logging
recs = []
h = logging.Handler()
h.emit = recs.append  # garde les records
log = logging.getLogger("ingest8c")
log.addHandler(h)
log.propagate = False
log.warning("lu %d annonces", 1423)
recs[0].msg           # → 'lu %d annonces'
recs[0].getMessage()  # → 'lu 1423 annonces'
```

- Quiz : `log.warning("taux 100%")`, sans argument : qu'est-ce qui est écrit ?
- [x] `taux 100%`
- [ ] Ligne perdue, `--- Logging error ---`
- [ ] `TypeError` dans l'appelant
- [ ] `taux 100`
- Réponse : `taux 100%` (mesuré) : sans arguments, logging n'applique pas `%` au message ; avec des arguments, il faudrait écrire `%%`.

## 3. getLogger(__name__) : un logger par module
- Id : logging-getlogger-name
- Sous-thème : loggers
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Source : data-platform · S1-07
- Définition : `logging.getLogger(__name__)` renvoie le logger nommé d'après le module (`ingest_bodacc.handler`) ; le même nom rend toujours le même objet.
- Contexte : Le registre des loggers est global au processus : deux `getLogger("ingest_bodacc.handler")` donnent le même objet, configuré une fois, sans le passer en paramètre. `__name__` suit l'arborescence des paquets : le logger se range sous `ingest_bodacc` dans la hiérarchie, et son nom apparaît dans chaque ligne (`%(name)s`).
- Usage : ✅ `logger = logging.getLogger(__name__)` en tête de chaque module · ❌ `logging.info(…)` direct : passe par le root, sans nom de module, et configure le root en douce s'il n'a pas de handler.

```python
# Exemple 1 : même nom, même objet
import logging
a = logging.getLogger("ingest_bodacc.handler")
b = logging.getLogger("ingest_bodacc.handler")
a is b  # → True
a.name  # → "ingest_bodacc.handler"
```

```python
# Exemple 2 : le parent se déduit du nom
import logging
p = logging.getLogger("ingest_bodacc")
h = logging.getLogger("ingest_bodacc.handler")
h.parent is p  # → True
```

- Quiz : Que vaut `logging.getLogger(__name__).name` dans `handler.py` lancé par `python handler.py` ?
- [ ] `"handler"`
- [ ] `"handler.py"`
- [x] `"__main__"`
- [ ] `"root"`
- Réponse : `"__main__"` : un fichier lancé comme script s'appelle `__main__`, pas du nom de son fichier ; importé, il redevient `handler`.

## 4. niveaux : des entiers comparés
- Id : logging-niveaux-entiers
- Sous-thème : niveaux
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Source : data-platform · S1-07
- Définition : Les niveaux sont des entiers (`DEBUG` 10, `INFO` 20, `WARNING` 30, `ERROR` 40, `CRITICAL` 50) ; un message passe s'il atteint le seuil.
- Contexte : `setLevel` accepte l'entier ou le nom en majuscules (`"INFO"`), pratique pour une variable `LOG_LEVEL`. Un logger sans niveau vaut `NOTSET` (0) et prend celui du premier parent qui en a un : `getEffectiveLevel()` donne le seuil réel. `isEnabledFor(niveau)` dit si un message de ce niveau passerait.
- Usage : ✅ `logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))` · ❌ comparer `logger.level` pour savoir ce qui sort : il vaut 0 tant qu'il hérite ; `getEffectiveLevel()`.

```python
# Exemple 1 : seuil et niveau du message
import logging
log = logging.getLogger("dp.niveaux")
log.setLevel("INFO")
log.level  # → 20
log.isEnabledFor(logging.DEBUG)  # → False
log.isEnabledFor(logging.ERROR)  # → True
```

```python
# Exemple 2 : un niveau hérité du parent
import logging
p = logging.getLogger("dp.herite")
p.setLevel(logging.ERROR)
e = logging.getLogger("dp.herite.storage")
e.level  # → 0  (NOTSET)
e.getEffectiveLevel()  # → 40
```

- Quiz : Que fait `log.setLevel("info")` (en minuscules) ?
- [ ] Règle le seuil sur `INFO`
- [x] `ValueError: Unknown level: 'info'`
- [ ] Rien : le seuil reste `WARNING`
- [ ] `TypeError` : un entier est attendu
- Réponse : `ValueError` (mesuré) : seuls les noms en majuscules sont reconnus ; avec une variable d'environnement, `.upper()` avant `setLevel`.

## 5. basicConfig : configurer le root une fois
- Id : logging-basicconfig-une-fois
- Sous-thème : handlers
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : logging-warning-par-defaut
- Source : data-platform · S1-07
- Définition : `logging.basicConfig(level=…, format=…)` pose un handler stderr sur le logger racine, seulement s'il n'en a encore aucun.
- Contexte : Pensé pour un script : un appel au démarrage suffit. Un second appel ne fait rien si le root a déjà un handler, sans erreur ni avertissement ; `force=True` retire les handlers existants et reconfigure. Une bibliothèque ne l'appelle jamais : c'est l'application qui configure. Piège : `logging.info(…)` appelé avant fait lui-même un `basicConfig()` implicite.
- Usage : ✅ script ou CLI : un `basicConfig` en tête de `main()` · ❌ dans un module importé, ou dans une Lambda dont le runtime a déjà posé un handler : sans effet.

```python
# Exemple 1 : le 2e appel est ignoré
import logging
root = logging.getLogger()
sauve = root.handlers[:], root.level
root.handlers = []
logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)
root.level  # → 20  (2e ignoré)
logging.basicConfig(level=logging.DEBUG,
                    force=True)
root.level  # → 10
root.handlers = sauve[0]  # remet l'état
root.setLevel(sauve[1])
```

- Quiz : Dans un script neuf, `logging.info("x")` puis `logging.basicConfig(level=logging.DEBUG)` : que vaut `logging.getLogger().level` ?
- [ ] `10` : `DEBUG`
- [ ] `20` : `INFO`
- [x] `30` : `WARNING`
- [ ] `0` : `NOTSET`
- Réponse : `30` (mesuré) : `logging.info` a déjà fait un `basicConfig()` sans niveau, qui a posé un handler ; le second appel, avec `DEBUG`, est ignoré.

## 6. Formatter : choisir les champs de la ligne
- Id : logging-formatter-champs
- Sous-thème : handlers
- Type : recette
- Niveau : 1
- Profils : ops
- Source : data-platform · S1-07
- Définition : `logging.Formatter("%(levelname)s %(name)s %(message)s")`, posé sur un handler, choisit les champs du record écrits sur chaque ligne.
- Contexte : Un `StreamHandler` sans formatter n'écrit que le message. Champs utiles : `asctime`, `levelname`, `name`, `funcName`, `lineno`, `message` (le texte formaté avec ses arguments). `basicConfig` utilise `logging.BASIC_FORMAT`. Un champ absent du record (`%(siren)s` sans `extra`) ne lève pas dans l'appelant : la ligne est perdue et une trace part sur stderr.
- Usage : ✅ niveau et nom du module dans chaque ligne texte · ❌ `%(champ)s` métier dans le format global : toute ligne sans ce champ est perdue ; le mettre dans le message ou un format JSON.

```python
# Exemple 1 : niveau, module, message
import io, logging
buf = io.StringIO()
h = logging.StreamHandler(buf)
h.setFormatter(logging.Formatter(
    "%(levelname)s %(name)s %(message)s"))
log = logging.getLogger("dp.fmt.handler")
log.propagate = False
log.addHandler(h)
log.warning("lu %d annonces", 2)
buf.getvalue()
# → "WARNING dp.fmt.handler lu 2 annonces\n"
```

```python
# Exemple 2 : le format de basicConfig
import logging
logging.BASIC_FORMAT
# → "%(levelname)s:%(name)s:%(message)s"
```

- Quiz : Format `"%(siren)s %(message)s"` et `log.warning("fin")` sans `extra` : que contient le flux du handler ?
- [ ] `"None fin\n"`
- [ ] `" fin\n"`
- [x] `""` : ligne perdue, trace sur stderr
- [ ] Rien : `KeyError` levé dans l'appelant
- Réponse : `""` (mesuré) : le formatage échoue dans le handler (Formatting field not found in record: 'siren'), qui l'attrape et écrit `--- Logging error ---` sur stderr.

## 7. messages : une erreur de format ne lève pas
- Id : logging-erreur-format-silencieuse
- Sous-thème : messages
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : logging-arguments-pas-fstring
- Source : data-platform · S1-07
- Définition : Un message aux arguments faux (`log.warning("%d", "deux")`) ne lève rien : `logging` écrit `--- Logging error ---` sur stderr et perd la ligne.
- Contexte : Le formatage `msg % args` a lieu dans le handler, au moment d'écrire ; son erreur est attrapée par `Handler.handleError`, qui imprime la trace sur stderr puis continue. Le code appelant ne voit rien et les tests passent. Ruff repère le nombre d'arguments faux (`PLE1205`, `PLE1206`) ; une f-string dans le message plus des arguments est l'erreur classique.
- Usage : ✅ `log.info("lu %d annonces", n)`, un `%` par argument · ❌ f-string **et** arguments : `log.info(f"jour {d}", d)`.

```python
# Exemple 1 : l'appelant ne voit rien
import io, logging
buf = io.StringIO()
log = logging.getLogger("dp.fmterr")
log.addHandler(logging.StreamHandler(buf))
log.propagate = False
log.warning("%d annonces", "deux")
buf.getvalue()  # → ""  (ligne perdue)
# stderr : --- Logging error ---
```

- Quiz : `log.warning(f"jour {jour}", jour)` avec `jour = "2026-10-20"` : que se passe-t-il ?
- [ ] Écrit `jour 2026-10-20`
- [ ] Écrit `jour 2026-10-20 2026-10-20`
- [ ] `TypeError` levé dans l'appelant
- [x] Ligne perdue, `--- Logging error ---` sur stderr
- Réponse : ligne perdue (mesuré) : le message n'a plus de `%s`, `msg % args` lève « not all arguments converted », attrapé par le handler.

## 8. logger.exception : le message et la trace
- Id : logging-exception-trace
- Sous-thème : messages
- Type : recette
- Niveau : 2
- Profils : ops, data
- Prérequis : exceptions-try-except-type
- Voir aussi : exceptions-raise-seul-relancer
- Source : data-platform · S1-07
- Définition : `logger.exception("échec %s", jour)` dans un `except` journalise au niveau `ERROR`, avec la trace complète de l'exception en cours.
- Contexte : Équivaut à `logger.error(…, exc_info=True)`. La trace fait partie du même événement de log (une seule entrée dans CloudWatch). Il ne relance pas : `raise` derrière si l'appelant (Lambda, Step Functions) doit voir l'échec. Hors d'un `except`, aucune exception n'est en cours : la trace écrite vaut `NoneType: None`.
- Usage : ✅ `except Exception: logger.exception(…)` puis `raise`, là où le contexte (jour, SIREN) est connu · ❌ `logger.error(str(e))` : la trace est perdue ; journaliser puis avaler l'erreur.

```python
# Exemple 1 : message, puis trace
import io, logging
buf = io.StringIO()
log = logging.getLogger("dp.exc")
log.addHandler(logging.StreamHandler(buf))
log.propagate = False
try:
    int("A2026")
except ValueError:
    log.exception("jour %s", "2026-10-20")
txt = buf.getvalue()
txt.splitlines()[0]  # → "jour 2026-10-20"
"Traceback" in txt  # → True
```

```python
# Exemple 2 : niveau ERROR, exception jointe
import logging
recs = []
h = logging.Handler()
h.emit = recs.append  # garde les records
log = logging.getLogger("dp.exc2")
log.addHandler(h)
log.propagate = False
try:
    {}["siren"]
except KeyError:
    log.exception("annonce sans siren")
recs[0].levelname  # → "ERROR"
recs[0].exc_info[0].__name__  # → "KeyError"
```

- Quiz : `log.exception("hors except")` appelé alors qu'aucune exception n'est en cours : que se passe-t-il ?
- [ ] `RuntimeError` : pas d'exception active
- [ ] Rien n'est écrit
- [x] Le message, suivi de `NoneType: None`
- [ ] Le message seul, sans trace
- Réponse : le message suivi de `NoneType: None` (mesuré) : `exc_info=True` lit `sys.exc_info()`, vide hors d'un `except`, et le formatter écrit cette « trace » vide.

## 9. propagate : le message remonte aux parents
- Id : logging-propagate-doublons
- Sous-thème : handlers
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : logging-getlogger-name
- Source : data-platform · S1-07
- Définition : Après ses propres handlers, un logger passe le message aux handlers de ses parents jusqu'au root, sauf `propagate = False`.
- Contexte : Le seuil n'est vérifié qu'une fois, sur le logger d'origine : le niveau d'un logger parent ne filtre pas un message propagé, seul celui de ses handlers le fait. D'où les lignes en double : un handler sur `ingest_bodacc` et un sur le root (celui du runtime Lambda) écrivent chacun la ligne. Règle : des handlers sur le root seulement ; les modules font `getLogger` et `setLevel`.
- Usage : ✅ handlers sur le root (ou fournis par le runtime), `setLevel` par module · ❌ `addHandler` dans chaque module : lignes en double dans CloudWatch.

```python
# Exemple 1 : une ligne, écrite deux fois
import io, logging
buf = io.StringIO()
p = logging.getLogger("dp.prop")
e = logging.getLogger("dp.prop.handler")
for lg in (p, e):
    lg.addHandler(logging.StreamHandler(buf))
p.propagate = False  # s'arrête avant root
e.setLevel(logging.INFO)
e.info("fin")
buf.getvalue()  # → "fin\nfin\n"
```

```python
# Exemple 2 : le niveau du parent ne filtre pas
import io, logging
buf = io.StringIO()
p = logging.getLogger("dp.prop2")
p.addHandler(logging.StreamHandler(buf))
p.setLevel(logging.ERROR)
p.propagate = False
e = logging.getLogger("dp.prop2.handler")
e.setLevel(logging.INFO)
e.info("fin")
buf.getvalue()  # → "fin\n"
```

- Quiz : Exemple 1, avec en plus `e.propagate = False` : que vaut `buf.getvalue()` ?
- [ ] `""`
- [x] `"fin\n"`
- [ ] `"fin\nfin\n"`
- Réponse : `"fin\n"` : `e` écrit avec son propre handler, puis ne transmet plus à `p` ; une seule ligne.

## 10. lastResort : sans handler, seulement WARNING
- Id : logging-lastresort
- Sous-thème : handlers
- Type : piège
- Niveau : 2
- Profils : ops, expert
- Prérequis : logging-warning-par-defaut
- Source : data-platform · S1-07
- Définition : Si aucun handler n'existe sur la chaîne d'un logger, `logging.lastResort` écrit sur stderr, mais seulement à partir de `WARNING`.
- Contexte : C'est pourquoi un `logger.warning` s'affiche dans un script sans configuration, alors qu'un `logger.info` disparaît même après `logger.setLevel(INFO)` : il passe le seuil du logger, mais le handler de dernier recours a son propre seuil, `WARNING`, et n'écrit que le texte, sans format. Il faut un vrai handler : `basicConfig`, ou celui que pose le runtime Lambda.
- Usage : ✅ `basicConfig` dans un script, handler du runtime dans une Lambda · ❌ conclure qu'un `setLevel(INFO)` suffit parce que les `warning` s'affichent.

```python
# Exemple 1 : info perdu, warning affiché
import contextlib, io, logging
log = logging.getLogger("dp.last")
log.propagate = False  # aucun handler
log.setLevel(logging.INFO)
err = io.StringIO()
with contextlib.redirect_stderr(err):
    log.info("lu 2")
    log.warning("lent")
err.getvalue()  # → "lent\n"
```

- Quiz : Même exemple, avec `log.addHandler(logging.NullHandler())` avant les appels : que vaut `err.getvalue()` ?
- [ ] `"lent\n"`
- [ ] `"lu 2\nlent\n"`
- [x] `""`
- Réponse : `""` (mesuré) : un `NullHandler` compte comme un handler, donc `lastResort` n'est plus utilisé ; c'est le réglage conseillé aux bibliothèques.

## 11. Lambda : le root est déjà configuré
- Id : logging-lambda-root-configure
- Sous-thème : lambda
- Type : piège
- Niveau : 2
- Profils : ops, data
- Prérequis : logging-basicconfig-une-fois
- Source : data-platform · S1-07
- Définition : Le runtime Python de Lambda pose un handler sur le logger racine, réglé sur `WARNING` : `basicConfig` n'a plus d'effet et `logger.info` reste filtré.
- Contexte : Comportement du runtime (doc AWS, simulé ici). Comme le root a déjà un handler, `logging.basicConfig(level=INFO)` est ignoré sans bruit. Ce qui marche : `logger.setLevel(logging.INFO)` sur le logger du module (le message propage jusqu'au handler du root, dont le niveau ne filtre pas), ou `application_log_level` dans `logging_config` avec le format `JSON`, qui règle le root côté Lambda.
- Usage : ✅ `logger = getLogger(__name__)` puis `logger.setLevel(logging.INFO)` dans le handler Lambda · ❌ `basicConfig(level=INFO)` copié d'un script : rien ne change dans CloudWatch.

```python
# Exemple 1 : simuler le runtime
import io, logging
buf = io.StringIO()
root = logging.getLogger()
sauve = root.handlers[:], root.level
root.handlers = [logging.StreamHandler(buf)]
root.setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("dp.lambda")
log.info("ingestion terminée")
buf.getvalue()  # → ""  (filtré)
log.setLevel(logging.INFO)
log.info("ingestion terminée")
buf.getvalue()  # → "ingestion terminée\n"
root.handlers = sauve[0]  # remet l'état
root.setLevel(sauve[1])
```

- Quiz : Dans la Lambda, `logging.getLogger().setLevel(logging.INFO)` (le root) au lieu du logger du module : effet ?
- [ ] Aucun : le root du runtime est verrouillé
- [ ] Seules les lignes `info` du module apparaissent
- [x] Les `info` du module, mais aussi celles de httpx
- [ ] `ValueError` : le root est géré par Lambda
- Réponse : les `info` de httpx aussi (mesuré : `HTTP Request: GET … "HTTP/1.1 200 OK"`) : les loggers sans niveau héritent du root ; régler son propre logger limite le bruit.

## 12. handler : son propre seuil
- Id : logging-seuil-handler
- Sous-thème : handlers
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : logging-niveaux-entiers
- Source : data-platform · S1-07
- Définition : Un handler a aussi un niveau (`h.setLevel(logging.ERROR)`) : un message doit passer le seuil du logger, puis celui de chaque handler.
- Contexte : Permet d'envoyer tout vers un flux, mais seulement les erreurs vers une alerte. Les deux filtres s'enchaînent : un logger en `DEBUG` avec un handler en `ERROR` n'écrit que les erreurs dans ce handler. Contrairement au niveau d'un logger parent, le niveau d'un handler filtre aussi les messages propagés depuis les enfants.
- Usage : ✅ un handler par destination, chacun son seuil (tout en fichier, erreurs en alerte) · ❌ baisser le seuil du logger pour une destination : toutes les autres reçoivent aussi le bruit.

```python
# Exemple 1 : deux handlers, deux seuils
import io, logging
tout, alertes = io.StringIO(), io.StringIO()
log = logging.getLogger("dp.seuils")
log.propagate = False
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler(tout))
h = logging.StreamHandler(alertes)
h.setLevel(logging.ERROR)
log.addHandler(h)
log.info("lu 2")
log.error("coupé")
tout.getvalue()  # → "lu 2\ncoupé\n"
alertes.getvalue()  # → "coupé\n"
```

- Quiz : Même exemple avec `log.setLevel(logging.CRITICAL)` : que vaut `alertes.getvalue()` ?
- [ ] `"coupé\n"`
- [x] `""`
- [ ] `"lu 2\ncoupé\n"`
- Réponse : `""` : le seuil du logger passe en premier ; `ERROR` (40) est sous `CRITICAL` (50), le message n'atteint aucun handler.

## 13. isEnabledFor : ne pas calculer pour rien
- Id : logging-isenabledfor
- Sous-thème : messages
- Type : recette
- Niveau : 2
- Profils : data, expert
- Prérequis : logging-arguments-pas-fstring
- Source : data-platform · S1-07
- Définition : Les arguments d'un appel de log sont évalués avant l'appel, même filtré : `log.debug("%s", cher())` exécute `cher()` ; `isEnabledFor` évite ce coût.
- Contexte : Le `%s` retarde le formatage, pas l'évaluation des expressions passées : Python évalue tous les arguments avant d'appeler la fonction, comme JS. Un calcul coûteux (`json.dumps` d'une journée) ou destructeur (`sum(1 for _ in flux)` consomme un générateur) se garde derrière `if log.isEnabledFor(logging.DEBUG):`.
- Usage : ✅ calcul coûteux ou générateur derrière `isEnabledFor` · ❌ le garde autour d'un simple `%s` sur une variable : le formatage est déjà paresseux.

```python
# Exemple 1 : calculé même si filtré
import logging
appels = []
def cher():
    appels.append(1)
    return "56 Mo"
log = logging.getLogger("dp.cout")
log.setLevel(logging.INFO)
log.debug("taille %s", cher())
len(appels)  # → 1
```

```python
# Exemple 2 : garder le calcul derrière le seuil
import logging
appels = []
def cher():
    appels.append(1)
    return "56 Mo"
log = logging.getLogger("dp.cout2")
log.setLevel(logging.INFO)
if log.isEnabledFor(logging.DEBUG):
    log.debug("taille %s", cher())
len(appels)  # → 0
```

- Quiz : `log.debug("lignes %d", sum(1 for _ in flux))`, DEBUG filtré, `flux` un générateur de 3 annonces : que donne ensuite `list(flux)` ?
- [ ] Les 3 annonces : le debug est filtré
- [x] `[]`
- [ ] `TypeError` : un générateur n'a pas de longueur
- [ ] La dernière annonce seule
- Réponse : `[]` (mesuré) : `sum(…)` s'exécute avant `debug`, filtré ou non, et épuise le générateur.

## 14. Filter : ajouter un champ à chaque ligne
- Id : logging-filter-request-id
- Sous-thème : handlers
- Type : recette
- Niveau : 3
- Profils : ops, expert
- Prérequis : logging-formatter-champs
- Voir aussi : logging-loggeradapter, AWS/lambda-aws-request-id
- Source : data-platform · S1-07
- Définition : Un `logging.Filter` posé sur un handler voit chaque record : il peut y ajouter un champ (`request_id`) et renvoie vrai pour le laisser passer.
- Contexte : Injecte l'identifiant de l'invocation Lambda dans toutes les lignes sans le passer à chaque appel : le handler le range (variable, `contextvars.ContextVar`), le filtre l'ajoute au record, le format l'écrit (`%(request_id)s`). Un filtre posé sur un logger ne voit pas les messages propagés depuis ses enfants ; sur le handler, si. Une valeur fausse renvoyée (`None`, `False`) supprime la ligne.
- Usage : ✅ champ commun à toutes les lignes (request_id, run_id) · ❌ un champ propre à un seul message : `extra=` sur cet appel.

```python
# Exemple 1 : request_id sur chaque ligne
import io, logging
class AvecId(logging.Filter):
    def filter(self, record):
        record.request_id = "req-123"
        return True
buf = io.StringIO()
h = logging.StreamHandler(buf)
h.addFilter(AvecId())
h.setFormatter(logging.Formatter(
    "%(request_id)s %(message)s"))
log = logging.getLogger("dp.filtre")
log.propagate = False
log.addHandler(h)
log.warning("fin")
buf.getvalue()  # → "req-123 fin\n"
```

- Quiz : Même filtre, mais `filter` oublie son `return True` : que vaut `buf.getvalue()` ?
- [ ] `"req-123 fin\n"`
- [ ] `"None fin\n"`
- [x] `""`
- [ ] `TypeError` à l'appel de `warning`
- Réponse : `""` (mesuré) : la fonction renvoie `None`, valeur fausse, que `logging` lit comme « rejeter le record ».

## 15. dictConfig : il désactive les loggers existants
- Id : logging-dictconfig-desactive
- Sous-thème : handlers
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : logging-getlogger-name
- Source : data-platform · S1-07
- Définition : `logging.config.dictConfig(cfg)` désactive par défaut les loggers déjà créés qu'il ne nomme pas : `disable_existing_loggers` vaut `True`.
- Contexte : Un module importé avant la configuration (son `getLogger(__name__)` tourne à l'import) se tait ensuite, sans erreur : `logger.disabled` passe à `True`. Piège classique quand la config est chargée dans `main()`, après les imports. `"disable_existing_loggers": False` dans le dict l'évite ; les enfants d'un logger nommé dans `loggers` sont gardés, mais remis à `NOTSET` sans handler.
- Usage : ✅ `"disable_existing_loggers": False` dans toute config par dict · ❌ charger la config après les imports avec la valeur par défaut : les logs des modules disparaissent.

```python
# Exemple 1 : le logger importé se tait
import logging, logging.config
log = logging.getLogger("dp.dict.handler")
logging.config.dictConfig({"version": 1})
log.disabled  # → True
logging.config.dictConfig({"version": 1,
    "disable_existing_loggers": False})
log.disabled  # → False
```

- Quiz : `dictConfig({"version": 1, "loggers": {"dp12": {"level": "INFO"}}})` : `dp12.handler`, créé avant, est-il désactivé ?
- [ ] Oui, comme tous les loggers non nommés
- [x] Non : enfant d'un logger nommé, il est gardé
- [ ] Oui, sauf s'il a déjà un handler
- Réponse : non (mesuré) : un descendant d'un logger configuré reste actif, mais son niveau repasse à `NOTSET` et ses handlers sont retirés.

## 16. LoggerAdapter : un contexte fixe
- Id : logging-loggeradapter
- Sous-thème : loggers
- Type : recette
- Niveau : 3
- Profils : ops, expert
- Prérequis : logging-getlogger-name
- Voir aussi : logging-filter-request-id
- Source : data-platform · S1-07
- Définition : `logging.LoggerAdapter(logger, {"request_id": …})` enveloppe un logger et ajoute ces champs à chaque record qu'il émet.
- Contexte : Alternative au `Filter` quand le contexte est connu à un endroit précis (début d'invocation) : on crée l'adapter dans le handler et on le passe aux fonctions. Les champs arrivent comme avec `extra`, le format les lit. Jusqu'à Python 3.12, le dict de l'adapter remplace l'`extra` passé à l'appel ; 3.13 ajoute `merge_extra=True` pour fusionner.
- Usage : ✅ contexte d'une invocation ou d'un lot (`request_id`, jour traité) · ❌ contexte qui doit couvrir les logs des bibliothèques : un `Filter` sur le handler du root.

```python
# Exemple 1 : request_id sans le répéter
import io, logging
buf = io.StringIO()
h = logging.StreamHandler(buf)
h.setFormatter(logging.Formatter(
    "%(request_id)s %(message)s"))
log = logging.getLogger("dp.adapter")
log.propagate = False
log.addHandler(h)
ad = logging.LoggerAdapter(
    log, {"request_id": "req-123"})
ad.warning("lu %d annonces", 2)
buf.getvalue()  # → "req-123 lu 2 annonces\n"
```

- Quiz : Python 3.12, même adapter, `ad.warning("fin", extra={"request_id": "autre"})` : quelle ligne est écrite ?
- [x] `"req-123 fin"`
- [ ] `"autre fin"`
- [ ] `KeyError` : champ en double
- [ ] `"req-123 autre fin"`
- Réponse : `"req-123 fin"` (mesuré en 3.12) : sans `merge_extra`, `process` remplace l'`extra` de l'appel par celui de l'adapter.
