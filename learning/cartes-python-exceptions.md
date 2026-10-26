---
title: "Cartes · Exceptions Python"
type: cartes
langage: Python
chapitre: Bases du langage
cours: Exceptions
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Exceptions Python
Python · Exceptions : lever, capturer, chaîner, types (format spec v3 de revision-pwa).

## 1. raise : lever une exception
- Id : exceptions-raise-lever
- Sous-thème : lever
- Type : concept
- Niveau : 1
- Profils : débutant
- Mots-clés : exception, runtime Lambda, CloudWatch
- Source : data-platform · S1-07
- Définition : `raise ValueError("message")` interrompt la fonction et remonte jusqu'au premier `except` qui la capture (≈ `throw new Error()`).
- Contexte : On lève une **instance** d'une classe qui hérite de `BaseException` ; `raise ValueError` (la classe seule) l'instancie sans message. Sans `except` sur le chemin, l'exception remonte jusqu'au runtime : sur Lambda, l'invocation échoue et l'erreur part dans CloudWatch avec sa trace. Une erreur levée tôt et avec un message clair vaut mieux qu'un résultat faux qui continue sa route.
- Usage : ✅ entrée invalide, état impossible (date future, `now` naïf) · ❌ cas normal attendu (journée vide, 0 annonce) : renvoyer une valeur, pas lever.

```python
# Exemple 1 : refuser une date non terminée
from datetime import date
def verifier(day, today):
    if day >= today:
        raise ValueError(f"{day} non terminé")
    return day
t = date(2026, 10, 26)
verifier(t, t)    # ❌ ValueError
```

```python
# Exemple 2 : le cas valide passe
from datetime import date

def verifier(day, today):
    if day >= today:
        raise ValueError(f"{day} non terminé")
    return day

verifier(date(2026, 10, 25),
         date(2026, 10, 26))
# → date(2026, 10, 25)
```

- Quiz : Que fait `raise "date invalide"` ?
- [ ] Lève une `Exception` avec ce message
- [x] `TypeError`
- [ ] `SyntaxError`
- [ ] Lève une `ValueError`
- Réponse : `TypeError` (`exceptions must derive from BaseException`) : contrairement à `throw` en JS, on ne lève pas une chaîne.

## 2. try / except : capturer un type
- Id : exceptions-try-except-type
- Sous-thème : capturer
- Type : concept
- Niveau : 1
- Profils : débutant
- Prérequis : exceptions-raise-lever
- Mots-clés : exception, handler Lambda
- Source : data-platform · S1-07
- Définition : `try:` exécute le bloc ; `except ValueError as exc:` capture seulement ce type (et ses sous-classes) et donne l'objet dans `exc`.
- Contexte : Contrairement au `catch (e)` de TS qui attrape tout, chaque `except` filtre par type : une autre exception traverse et remonte. On capture le type le plus précis possible, au plus près de la ligne qui lève : un `try` d'une ligne autour de `date.fromisoformat(raw)`, pas autour de toute la fonction. Plusieurs `except` peuvent se suivre.
- Usage : ✅ traduire ou contourner une erreur prévue (date illisible, clé absente) · ❌ `try` géant autour de tout le handler : on ne sait plus quelle ligne a échoué.

```python
# Exemple 1 : capturer la date invalide
from datetime import date
def lire(raw):
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None
lire("hier")        # → None
lire("2026-10-20")  # → date(2026, 10, 20)
```

- Quiz : Que vaut `log` après ce code ? `try: d = date.fromisoformat("hier"); log.append("lu")` puis `except ValueError: log.append("ko")`
- [ ] `["lu", "ko"]`
- [x] `["ko"]`
- [ ] `["lu"]`
- [ ] `[]`
- Réponse : `["ko"]` : le `try` s'arrête à la ligne qui lève ; ce qui la suit dans le bloc ne s'exécute pas.

## 3. TypeError ou ValueError : le bon type
- Id : exceptions-typeerror-ou-valueerror
- Sous-thème : types
- Type : comparaison
- Niveau : 1
- Profils : débutant, data
- Mots-clés : stdlib, isinstance
- Source : data-platform · S1-07
- Définition : `TypeError` = argument du mauvais type (`int(None)`) ; `ValueError` = bon type mais valeur refusée (`int("abc")`, `"2026-13-01"`).
- Contexte : La stdlib suit cette règle : `date.fromisoformat(20261020)` lève `TypeError`, `date.fromisoformat("hier")` lève `ValueError`. Un `except ValueError` ne voit donc pas l'entier. `resolve_day` ramène tout à `ValueError` (« entrée invalide ») en testant `isinstance(raw, str)` d'abord : l'appelant n'a qu'un type à gérer. Le type levé fait partie du contrat de la fonction : le choisir et le documenter.
- Usage : ✅ `ValueError` pour une donnée mal formée, `TypeError` pour un appel mal écrit · ❌ `Exception("…")` générique : impossible à capturer précisément.

```python
# Exemple 1 : la stdlib distingue les deux
int("abc")    # ❌ ValueError
int(None)     # ❌ TypeError
```

```python
# Exemple 2 : un seul type pour l'appelant
from datetime import date

def lire(raw):
    if not isinstance(raw, str):
        raise ValueError(f"chaîne attendue, reçu {raw!r}")
    return date.fromisoformat(raw)

lire(20261020)    # ❌ ValueError
date.fromisoformat(20261020)  # ❌ TypeError
```

- Quiz : Que lève `date(2026, 13, 1)` ?
- [ ] `TypeError`
- [x] `ValueError`
- [ ] `OverflowError`
- [ ] `IndexError`
- Réponse : `ValueError` (`month must be in 1..12`) : l'entier a le bon type, c'est sa valeur qui est hors limites.

## 4. message : la valeur avec !r
- Id : exceptions-message-repr
- Sous-thème : lever
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : repr, f-string, CloudWatch
- Source : data-platform · S1-07
- Définition : Dans un message d'erreur, `f"{raw!r}"` affiche la valeur par `repr` : guillemets visibles, chaîne vide lisible, type devinable.
- Contexte : `f"date invalide {raw}"` donne `date invalide ` pour une chaîne vide, et ne distingue pas `"20261020"` de `20261020`. Avec `!r` : `date invalide ''`, et `'20261020'` contre `20261020`. Un bon message dit ce qui a été reçu et ce qui était attendu : `date invalide 'hier', attendu YYYY-MM-DD`. Il finit dans les logs CloudWatch : c'est lui qu'on lit en premier pendant un incident.
- Usage : ✅ toute valeur reçue citée dans un message d'erreur ou un log · ❌ message sans la valeur (« date invalide ») : impossible à diagnostiquer.

```python
# Exemple 1 : vide et nombre visibles
raw = ""
f"date invalide {raw}"
# → "date invalide "
f"date invalide {raw!r}"
# → "date invalide ''"
f"reçu {20261020!r}"  # → "reçu 20261020"
```

```python
# Exemple 2 : reçu et attendu
def msg(raw):
    return (f"date invalide {raw!r},"
            " attendu YYYY-MM-DD")

msg("hier")
# → "date invalide 'hier', attendu YYYY-MM-DD"
```

- Quiz : Avec `d = date(2026, 10, 24)`, que vaut `f"{d!r}"` ?
- [ ] `"2026-10-24"`
- [ ] `"'2026-10-24'"`
- [x] `"datetime.date(2026, 10, 24)"`
- [ ] `"date(2026, 10, 24)"`
- Réponse : `"datetime.date(2026, 10, 24)"` : `repr` d'une date montre son constructeur qualifié ; sans `!r`, `str` donne `2026-10-24`.

## 5. except (A, B) : plusieurs types
- Id : exceptions-except-plusieurs-types
- Sous-thème : capturer
- Type : concept
- Niveau : 1
- Profils : débutant
- Prérequis : exceptions-try-except-type
- Voir aussi : tests-raises-plusieurs-types
- Mots-clés : tuple, PEP
- Source : data-platform · S1-07
- Définition : `except (ValueError, TypeError) as exc:` capture l'un ou l'autre type avec le même traitement : un tuple, entre parenthèses.
- Contexte : Jusqu'à Python 3.13, les parenthèses sont obligatoires. Depuis 3.14 (PEP 758), `except ValueError, TypeError:` est permis, mais seulement sans `as` : avec `as exc`, les parenthèses restent obligatoires. `type(exc).__name__` dit lequel a été levé. Si les traitements diffèrent, deux `except` séparés valent mieux qu'un `isinstance` dans le bloc.
- Usage : ✅ même réaction à plusieurs erreurs d'entrée (texte illisible ou type faux) · ❌ tuple fourre-tout de cinq types : signe qu'il faut un `except` plus haut, ou une exception métier.

```python
# Exemple 1 : deux types, un traitement
from datetime import date
def lire(raw):
    try:
        return date.fromisoformat(raw)
    except (ValueError, TypeError) as exc:
        return type(exc).__name__
lire("hier")     # → "ValueError"
lire(20261020)   # → "TypeError"
```

- Quiz : En Python 3.14, que fait `except ValueError, TypeError as exc:` ?
- [ ] Capture les deux, `exc` vaut l'erreur levée
- [ ] Capture `ValueError`, `exc` ne vise que `TypeError`
- [x] `SyntaxError` à la compilation
- [ ] Capture seulement `TypeError`
- Réponse : `SyntaxError` (multiple exception types must be parenthesized when using 'as') : PEP 758 n'autorise l'écriture sans parenthèses que sans `as`.

## 6. str(exc) et args : lire l'erreur
- Id : exceptions-str-et-args
- Sous-thème : types
- Type : concept
- Niveau : 1
- Profils : débutant
- Prérequis : exceptions-try-except-type
- Voir aussi : tests-keyerror-guillemets
- Mots-clés : exception, logs structurés
- Source : data-platform · S1-07
- Définition : `str(exc)` donne le message d'une exception ; `exc.args` le tuple des arguments passés à son constructeur.
- Contexte : `ValueError("date invalide")` : `str` vaut le message, `args` vaut `("date invalide",)`. Avec plusieurs arguments, `str` affiche le tuple entier ; sans argument, une chaîne vide. Pour transporter des champs (SIREN, jour) jusqu'aux logs structurés, une sous-classe avec des attributs vaut mieux qu'un message à re-parser.
- Usage : ✅ `str(exc)` pour journaliser, `exc.args[0]` pour la valeur brute · ❌ extraire une donnée du message par regex : porter un attribut.

```python
# Exemple 1 : message et args
e = ValueError("date invalide")
str(e)    # → "date invalide"
e.args    # → ("date invalide",)
str(ValueError())  # → ""
```

```python
# Exemple 2 : plusieurs arguments
e = ValueError("date invalide", "hier")
str(e)
# → "('date invalide', 'hier')"
e.args[1]   # → "hier"
```

- Quiz : Avec `exc = ValueError("date invalide")`, que fait `exc.message` ?
- [ ] Renvoie `"date invalide"`
- [x] `AttributeError`
- [ ] Renvoie `None`
- [ ] Renvoie `""`
- Réponse : `AttributeError` : pas de `.message` comme en JS (`err.message`) ; le message se lit avec `str(exc)`.

## 7. raise … from exc : garder la cause
- Id : exceptions-raise-from-cause
- Sous-thème : chaîner
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : exceptions-try-except-type
- Voir aussi : exceptions-context-implicite, tests-raises-cause
- Mots-clés : exception chaînée, trace d'erreur
- Source : data-platform · S1-07
- Définition : `raise ValueError(msg) from exc` lève une nouvelle erreur en gardant l'originale dans `__cause__` (≈ `new Error(msg, { cause })`).
- Contexte : `resolve_day` traduit `Invalid isoformat string: 'hier'` en `date invalide 'hier', attendu YYYY-MM-DD` : message métier pour l'appelant, cause technique conservée. La trace affiche les deux, reliées par « The above exception was the direct cause of the following exception ». Le type peut rester le même (`ValueError` vers `ValueError`) : on enrichit le message sans changer le contrat.
- Usage : ✅ traduire une erreur de bas niveau en erreur métier, à une frontière (parsing, client HTTP) · ❌ relancer sans `from` dans un `except` : trace trompeuse.

```python
# Exemple 1 : message métier, cause gardée
from datetime import date
def lire(raw):
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(
            f"date invalide {raw!r}") from exc
lire("hier")   # ❌ ValueError
```

```python
# Exemple 2 : la cause reste lisible
from datetime import date

try:
    try:
        date.fromisoformat("2026-13-01")
    except ValueError as exc:
        raise ValueError("date invalide") from exc
except ValueError as e:
    cause = str(e.__cause__)
cause   # → "month must be in 1..12"
```

- Quiz : Que fait `raise ValueError("date invalide") from 42` ?
- [ ] Lève `ValueError` avec `__cause__ = 42`
- [ ] Lève `ValueError`, `42` ignoré
- [x] `TypeError`
- [ ] `SyntaxError`
- Réponse : `TypeError` (`exception causes must derive from BaseException`) : la cause doit être une exception, ou `None`.

## 8. raise dans except : __context__ implicite
- Id : exceptions-context-implicite
- Sous-thème : chaîner
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : exceptions-try-except-type
- Voir aussi : exceptions-raise-from-cause
- Mots-clés : exception chaînée, trace d'erreur, Ruff
- Source : data-platform · S1-07
- Définition : Une exception levée dans un `except` sans `from` garde l'originale dans `__context__` : la trace présente les deux comme un incident en cascade.
- Contexte : La trace dit alors « During handling of the above exception, another exception occurred », ce qui laisse croire à un bug dans le gestionnaire lui-même. `from exc` dit « c'est voulu, voici la cause » (`__cause__`) ; `from None` masque l'original. Ruff signale l'oubli (règle `B904`, `raise` sans `from` dans un `except`). Dans tous les cas, l'original reste accessible pour le débogage.
- Usage : ✅ toujours `from exc` (ou `from None`) quand on relève dans un `except` · ❌ laisser le chaînage implicite pour une traduction volontaire.

```python
# Exemple 1 : contexte, pas cause
try:
    try:
        int("hier")
    except ValueError:
        raise TypeError("jour illisible")
except TypeError as e:
    ctx = type(e.__context__).__name__
    cause = e.__cause__
ctx      # → "ValueError"
cause    # → None
```

- Quiz : Avec `raise ValueError("date") from exc` dans l'`except`, que vaut `e.__context__ is e.__cause__` ?
- [x] `True`
- [ ] `False`
- [ ] `AttributeError`
- Réponse : `True` : `from exc` remplit `__cause__`, et Python remplit aussi `__context__` avec l'exception en cours, la même.

## 9. raise seul : relancer telle quelle
- Id : exceptions-raise-seul-relancer
- Sous-thème : lever
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : exceptions-try-except-type
- Voir aussi : logging-exception-trace
- Mots-clés : trace d'erreur, Step Functions, logger
- Source : data-platform · S1-07
- Définition : Dans un `except`, `raise` sans argument relance l'exception en cours, avec sa trace d'origine, après un log ou un nettoyage.
- Contexte : Motif courant : `except Exception: logger.exception("échec %s", jour)` puis `raise`. L'appelant (Lambda, Step Functions) voit l'erreur réelle et peut réessayer ou alerter. Avaler l'exception sans relancer transforme un échec en succès silencieux : le run serait marqué réussi, la journée manquante. `raise exc` marche aussi mais ajoute la ligne courante à la trace.
- Usage : ✅ journaliser avec contexte puis laisser l'erreur remonter · ❌ `except Exception: log(…)` sans `raise` : l'échec disparaît.

```python
# Exemple 1 : journaliser, puis relancer
log = []
def ingerer(jour):
    try:
        int(jour)
    except ValueError:
        log.append(f"échec {jour}")
        raise
ingerer("hier")   # ❌ ValueError
log               # → ["échec hier"]
```

- Quiz : Que fait `raise` seul, hors de tout `except` ?
- [ ] Rien : aucune exception en cours
- [ ] `SyntaxError`
- [x] `RuntimeError`
- [ ] Lève `Exception`
- Réponse : `RuntimeError` (`No active exception to reraise`) : `raise` seul n'a de sens que pendant le traitement d'une exception.

## 10. try : else et finally
- Id : exceptions-else-finally
- Sous-thème : capturer
- Type : concept
- Niveau : 2
- Profils : débutant
- Prérequis : exceptions-try-except-type
- Voir aussi : context-managers-with-try-finally
- Mots-clés : try/finally, context manager
- Source : data-platform · S1-07
- Définition : `else` s'exécute si le `try` n'a rien levé ; `finally` s'exécute toujours, erreur ou non, même après un `return`.
- Contexte : `else` sort du `try` le code qui ne doit pas être protégé : seul `fromisoformat` est sous `try`, la suite (`if day >= today`) va dans `else`, pour qu'une erreur de cette suite ne soit pas capturée par mégarde. `finally` sert à libérer une ressource ou écrire une métrique de fin ; pour un fichier ou une connexion, préférer `with`.
- Usage : ✅ `else` pour garder le `try` minimal, `finally` pour un nettoyage inconditionnel · ❌ `return` dans `finally` : il écrase le résultat et avale l'erreur.

```python
# Exemple 1 : sans erreur
log = []
try:
    n = int("20261020")
except ValueError:
    log.append("except")
else:
    log.append("else")
finally:
    log.append("finally")
log   # → ["else", "finally"]
```

```python
# Exemple 2 : avec erreur
log = []
try:
    n = int("hier")
except ValueError:
    log.append("except")
else:
    log.append("else")
finally:
    log.append("finally")
log   # → ["except", "finally"]
```

- Quiz : Que renvoie `f()` si `f` fait `try: return "try"` puis `finally: return "finally"` ?
- [ ] `"try"`
- [x] `"finally"`
- [ ] `None`
- [ ] `SyntaxError`
- Réponse : `"finally"` : le `return` du `finally` remplace celui du `try` ; il avalerait même une exception (avertissement depuis 3.14).

## 11. hiérarchie : except attrape les sous-classes
- Id : exceptions-hierarchie-sous-classes
- Sous-thème : types
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : exceptions-try-except-type
- Voir aussi : exceptions-exception-metier, json-decodeerror-position
- Mots-clés : MRO, JSON
- Source : data-platform · S1-07
- Définition : `except ValueError` capture aussi ses sous-classes, comme `json.JSONDecodeError` ou `UnicodeDecodeError` : la hiérarchie compte plus que le nom.
- Contexte : Un `except ValueError` autour d'un parse JSON puis d'une date attrape les deux erreurs sans les distinguer. `type(exc).__mro__` montre la chaîne d'héritage. Pour traiter un cas précis à part, son `except` passe en premier, le plus général ensuite. En TS, `instanceof` suit la même logique, mais rien ne filtre automatiquement dans `catch`.
- Usage : ✅ capturer une famille (`ValueError`, `OSError`) quand le traitement est commun · ❌ `except ValueError` large sur plusieurs étapes : on ne sait plus laquelle a échoué.

```python
# Exemple 1 : JSONDecodeError est un ValueError
import json
try:
    json.loads('{"date": ')
except ValueError as exc:
    nom = type(exc).__name__
nom   # → "JSONDecodeError"
```

```python
# Exemple 2 : la chaîne d'héritage
import json
[c.__name__ for c in
 json.JSONDecodeError.__mro__[:3]]
# → ["JSONDecodeError", "ValueError", "Exception"]
```

- Quiz : Que vaut `issubclass(ZoneInfoNotFoundError, ValueError)` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : `ZoneInfoNotFoundError` hérite de `KeyError` (une clé de fuseau inconnue) ; un `except ValueError` ne la voit pas.

## 12. exception métier : sous-classer ValueError
- Id : exceptions-exception-metier
- Sous-thème : types
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : exceptions-hierarchie-sous-classes
- Mots-clés : logs structurés, Step Functions
- Source : data-platform · S1-07
- Définition : `class DateInvalide(ValueError): pass` crée un type d'erreur métier, capturable par son nom ou par `ValueError`.
- Contexte : Hériter du bon type standard garde la compatibilité : le code existant qui capture `ValueError` continue de marcher, le nouveau peut viser `DateInvalide`. Une sous-classe peut porter des champs (`self.raw`) pour les logs structurés. Une exception par décision que l'appelant prend différemment (rejouer, ignorer, alerter), pas une par message.
- Usage : ✅ erreur que l'appelant doit distinguer (Step Functions qui route `DateInvalide` vers une alerte) · ❌ une classe par message d'erreur : hiérarchie inutile.

```python
# Exemple 1 : un type, un champ
class DateInvalide(ValueError):
    def __init__(self, raw):
        super().__init__(f"date invalide {raw!r}")
        self.raw = raw
try:
    raise DateInvalide("hier")
except ValueError as e:
    r = (type(e).__name__, e.raw)
r   # → ("DateInvalide", "hier")
```

- Quiz : Avec `class DateInvalide(Exception)`, un `except ValueError:` existant la capture-t-il ?
- [ ] Oui : toute erreur de date est un `ValueError`
- [x] Non : elle n'hérite pas de `ValueError`
- [ ] Oui, si le message contient « invalide »
- [ ] Non, et la classe lève `TypeError`
- Réponse : non : `except` filtre par héritage ; hériter de `Exception` casse les appelants qui capturaient `ValueError`.

## 13. except Exception : pas tout
- Id : exceptions-except-exception-limites
- Sous-thème : capturer
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : exceptions-hierarchie-sous-classes
- Voir aussi : tests-raises-trop-large
- Mots-clés : BaseException, handler Lambda
- Source : data-platform · S1-07
- Définition : `except Exception` capture presque tout, sauf `KeyboardInterrupt`, `SystemExit` et `GeneratorExit`, qui héritent directement de `BaseException`.
- Contexte : C'est voulu : un Ctrl+C ou une sortie demandée doivent pouvoir arrêter le programme. Un `except:` nu (ou `except BaseException`) les avale aussi : le script ne s'arrête plus. En TS, `catch` attrape tout ce qui est lancé. Règle : `except Exception` seulement à la frontière (handler Lambda, boucle d'un lot), avec log puis relance ou rejet, jamais au milieu du code.
- Usage : ✅ filet de sécurité à la frontière, avec log et relance · ❌ `except:` nu, ou `except Exception: pass` au milieu du traitement.

```python
# Exemple 1 : ce qu'Exception ne couvre pas
issubclass(ValueError, Exception)
# → True
issubclass(KeyboardInterrupt, Exception)
# → False
issubclass(SystemExit, BaseException)
# → True
```

- Quiz : Que fait `try: sys.exit(1)` suivi de `except Exception: print("ko")` ?
- [ ] Affiche `ko` et continue
- [x] Quitte sans afficher `ko`
- [ ] Affiche `ko` puis quitte
- [ ] `RuntimeError`
- Réponse : quitte sans afficher : `sys.exit` lève `SystemExit`, qui n'hérite pas d'`Exception` et traverse l'`except`.

## 14. from None : la cause masquée, pas effacée
- Id : exceptions-from-none-masque
- Sous-thème : chaîner
- Type : concept
- Niveau : 3
- Profils : expert
- Prérequis : exceptions-raise-from-cause
- Mots-clés : exception chaînée, trace d'erreur
- Source : data-platform · S1-07
- Définition : `raise … from None` met `__suppress_context__` à vrai : la trace n'affiche plus l'exception d'origine, qui reste pourtant dans `__context__`.
- Contexte : Utile quand l'erreur d'origine n'apporte rien au lecteur (`KeyError: 'siren'` traduite en « A1 sans siren »). Rien n'est perdu pour le débogage : `e.__context__` garde la `KeyError`. À l'inverse, pour `fromisoformat`, la cause (`month must be in 1..12`) est utile : `from exc`, comme dans `resolve_day`.
- Usage : ✅ erreur d'origine sans valeur pour le lecteur (clé absente, conversion triviale) · ❌ masquer une cause qui explique l'échec : `from exc`.

```python
# Exemple 1 : masquée mais présente
try:
    try:
        {}["siren"]
    except KeyError:
        raise ValueError("A1 sans siren") from None
except ValueError as e:
    r = (e.__cause__, e.__suppress_context__,
         type(e.__context__).__name__)
r   # → (None, True, "KeyError")
```

- Quiz : Que fait `raise ValueError("a") from None`, hors de tout `except` ?
- [ ] `SyntaxError`
- [ ] `RuntimeError` : rien à masquer
- [x] Lève `ValueError` normalement
- [ ] `TypeError`
- Réponse : lève `ValueError` normalement : `from None` est permis partout ; il n'y a simplement aucun contexte à masquer.

## 15. as exc : effacée après le bloc
- Id : exceptions-as-exc-effacee
- Sous-thème : capturer
- Type : piège
- Niveau : 3
- Profils : expert
- Mots-clés : portée, trace d'erreur
- Source : data-platform · S1-07
- Définition : La variable de `except E as exc:` est supprimée à la fin du bloc : la lire ensuite lève `NameError`.
- Contexte : Python fait un `del exc` implicite pour casser le cycle exception, trace, cadre, variable, qui garderait toute la pile en mémoire. En TS, `e` est simplement hors de portée après le `catch` ; ici le nom est réellement effacé de la fonction. Pour garder l'erreur : l'affecter à une autre variable dans le bloc (`err = exc`).
- Usage : ✅ copier l'exception dans une autre variable pour la traiter après · ❌ lire `exc` après le bloc `except`.

```python
# Exemple 1 : garder l'erreur
err = None
try:
    int("hier")
except ValueError as exc:
    err = exc
type(err).__name__   # → "ValueError"
exc                  # ❌ NameError
```

- Quiz : `exc = "rien"` avant le `try`, puis `except ValueError as exc:` capture une erreur. Que donne `exc` après le bloc ?
- [ ] `"rien"`
- [ ] L'exception capturée
- [x] `NameError`
- [ ] `None`
- Réponse : `NameError` : le `del exc` de fin de bloc efface le nom, même s'il existait avant ; l'ancienne valeur est perdue aussi.

## 16. add_note : du contexte sans changer le type
- Id : exceptions-add-note
- Sous-thème : lever
- Type : recette
- Niveau : 3
- Profils : data, expert
- Mots-clés : trace d'erreur, logger
- Source : data-platform · S1-07
- Définition : `exc.add_note("annonce A1")` (Python 3.11+) attache une ligne de contexte, affichée sous la trace, sans changer le type ni le message.
- Contexte : Alternative légère à `raise … from` quand on veut seulement dire où l'erreur est survenue (jour, SIREN, fichier) puis relancer avec `raise`. Les notes vivent dans `exc.__notes__`, une liste, et s'empilent à chaque niveau qui en ajoute. `str(exc)` ne les inclut pas : un log qui n'écrit que `str(exc)` les perd, `logger.exception` (trace complète) les affiche.
- Usage : ✅ ajouter le jour ou le SIREN en cours dans une boucle, puis `raise` · ❌ changer le type ou le message : `raise NouvelleErreur(…) from exc`.

```python
# Exemple 1 : note ajoutée, puis relance
try:
    try:
        int("hier")
    except ValueError as exc:
        exc.add_note("jour 2026-10-24")
        raise
except ValueError as e:
    notes = e.__notes__
notes   # → ["jour 2026-10-24"]
```

- Quiz : Que fait `ValueError("x").__notes__` sur une exception sans note ?
- [ ] Renvoie `[]`
- [ ] Renvoie `None`
- [x] `AttributeError`
- Réponse : `AttributeError` : `__notes__` n'est créé qu'au premier `add_note` ; lire avec `getattr(e, "__notes__", [])`.

## 17. ExceptionGroup : except* trie le lot
- Id : exceptions-exceptiongroup-except-etoile
- Sous-thème : types
- Type : concept
- Niveau : 3
- Profils : expert
- Prérequis : exceptions-hierarchie-sous-classes
- Voir aussi : http-asyncio-gather
- Mots-clés : asyncio, tâche concurrente
- Source : data-platform · S1-07
- Définition : `ExceptionGroup("lot", [e1, e2])` lève plusieurs erreurs à la fois ; `except* ValueError` traite celles de ce type, les autres continuent.
- Contexte : Python 3.11+. Utile pour valider un lot d'annonces en entier et rendre toutes les erreurs d'un coup, ou pour des tâches parallèles (`asyncio.TaskGroup` lève un groupe). Chaque `except*` reçoit un sous-groupe (`g.exceptions`) ; plusieurs `except*` peuvent s'exécuter pour un même groupe, contrairement à `except`.
- Usage : ✅ rapport de validation complet d'un lot, erreurs de tâches concurrentes · ❌ une seule erreur : `raise` simple, plus lisible.

```python
# Exemple 1 : deux types, deux traitements
vus = []
errs = [ValueError("A1"), TypeError("A2")]
try:
    raise ExceptionGroup("lot", errs)
except* ValueError as g:
    vus.append(len(g.exceptions))
except* TypeError as g:
    vus.append("type")
vus   # → [1, "type"]
```

- Quiz : `ExceptionGroup("lot", [ValueError("A1")])` est levé : un `except ValueError:` le capture-t-il ?
- [ ] Oui : le groupe ne contient que des `ValueError`
- [x] Non : un `ExceptionGroup` n'est pas un `ValueError`
- [ ] Oui, après dépaquetage automatique
- [ ] Non, et Python lève `TypeError`
- Réponse : non : `except` compare le type du groupe lui-même ; pour viser son contenu, il faut `except*`.
