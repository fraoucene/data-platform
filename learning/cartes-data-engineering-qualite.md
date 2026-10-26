---
title: "Cartes · Qualité et observabilité"
type: cartes
langage: Data engineering
chapitre: Fiabiliser
cours: Qualité et observabilité
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Qualité et observabilité
Data engineering · Qualité et observabilité : contrôles, logs, rejets (format spec v3 de revision-pwa).

## 1. quarantaine : isoler les lignes invalides
- Id : qualite-quarantaine-lignes-invalides
- Sous-thème : rejets
- Type : recette
- Niveau : 2
- Profils : data
- Voir aussi : qualite-seuil-de-rejet
- Mots-clés : pydantic, DLQ
- Définition : Une ligne invalide part en quarantaine (rejets, avec l'erreur) au lieu de faire planter tout le lot (≈ dead letter queue).
- Contexte : Sur ~32 000 annonces par jour, quelques-unes ont toujours un champ manquant ou mal formé. Lever sur la première bloquerait la journée entière. On capture `ValidationError` ligne par ligne, on garde la ligne brute et le type d'erreur dans un fichier `rejets/dt=…`, et le lot continue. Les rejets se relisent ensuite pour corriger le modèle.
- Usage : ✅ validation ligne à ligne d'un gros lot hétérogène · ❌ attraper `Exception` en entier : un bug du code passerait pour une ligne invalide.

```python
# Exemple 1 : trier les valides et les rejets
from pydantic import (BaseModel,
                      ValidationError)

class Ligne(BaseModel):
    siren: str

ok, rejets = [], []
for b in [{"siren": "483609327"},
          {"nom": "sans siren"}]:
    try:
        ok.append(Ligne(**b))
    except ValidationError as e:
        rejets.append((b, e))
len(ok), len(rejets)  # → (1, 1)
```

```python
# Exemple 2 : garder le type d'erreur
from pydantic import (BaseModel,
                      ValidationError)

class Ligne(BaseModel):
    siren: str

try:
    Ligne(nom="sans siren")
except ValidationError as e:
    err = e.errors()[0]
err["type"], err["loc"]
# → ("missing", ("siren",))
```

- Quiz : `{"siren": 483609327}` (un `int`) va dans `ok` ou dans `rejets` ?
- [ ] `ok`, avec `siren == "483609327"`
- [x] `rejets`
- [ ] `ok`, avec `siren == 483609327`
- Réponse : `rejets` : pydantic v2 ne convertit pas un `int` en `str` (erreur `string_type`).

## 2. seuil de rejet : échouer à temps
- Id : qualite-seuil-de-rejet
- Sous-thème : rejets
- Type : concept
- Niveau : 2
- Profils : data, ops
- Prérequis : qualite-quarantaine-lignes-invalides
- Mots-clés : quarantaine, CloudWatch, watermark
- Définition : Au-delà d'un taux de rejet fixé, le job échoue : trop de lignes invalides signale un changement de format de la source.
- Contexte : La quarantaine évite qu'une ligne bloque le lot, mais elle peut masquer une panne : si l'API renomme un champ, 100 % des lignes partent en rejet et le job « réussit » avec une partition vide. Le seuil (quelques %) transforme ce silence en échec visible : alarme CloudWatch, pas de watermark avancé. On raisonne en taux, pas en nombre absolu, car le volume varie selon le jour.
- Usage : ✅ tout pipeline avec quarantaine · ❌ seuil à 0 % sur une source réelle : le job échouerait chaque jour pour une annonce mal formée.

```python
# Exemple 1 : taux de rejet contrôlé
def verifier(lus, rejets, seuil=0.05):
    taux = rejets / lus
    if taux > seuil:
        raise RuntimeError(f"{taux:.0%}")
    return taux

verifier(1000, 12)  # → 0.012
verifier(1000, 80)  # ❌ RuntimeError
```

- Quiz : Que fait `verifier(0, 0)` un samedi sans annonce ?
- [ ] Renvoie `0.0`
- [ ] `RuntimeError`
- [x] `ZeroDivisionError`
- [ ] Renvoie `None`
- Réponse : `ZeroDivisionError` : tester `lus == 0` avant ; une journée vide n'est pas un échec.

## 3. réconciliation : lus = écrits + rejetés
- Id : qualite-reconciliation-lus-ecrits-rejetes
- Sous-thème : contrôles
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : qualite-quarantaine-lignes-invalides
- Voir aussi : ingestion-rejeu-rapprocher-trois-comptes
- Mots-clés : générateur, watermark, log structuré
- Définition : En fin de run, on vérifie lus = écrits + rejetés ; un écart signale des lignes perdues en silence.
- Contexte : Un filtre trop large, une exception avalée, un générateur épuisé deux fois : des lignes peuvent disparaître sans erreur. Compter à chaque étape et comparer en fin de run attrape ces pertes. On peut aussi comparer `lus` au total annoncé par la source (`count_day` du client BODACC, via `total_count`). Le bilan est loggé en JSON pour être suivi dans le temps.
- Usage : ✅ fin de chaque run, avant d'avancer le watermark · ❌ ce contrôle écrit avec `assert` (voir le quiz) : lever une vraie exception, comme l'exemple.

```python
# Exemple 1 : le bilan qui se vérifie
def bilan(lus, ecrits, rejetes):
    perdues = lus - ecrits - rejetes
    if perdues:
        raise RuntimeError(
            f"{perdues} perdues")
    return {"lus": lus, "ok": ecrits}

bilan(100, 97, 3)
# → {"lus": 100, "ok": 97}
bilan(100, 95, 3)  # ❌ RuntimeError
```

- Quiz : Le contrôle écrit `assert lus == ecrits + rejetes`, que fait `bilan(100, 95, 3)` lancé avec `python -O` ?
- [ ] `AssertionError`
- [x] Renvoie `{"lus": 100, "ok": 95}`
- [ ] `RuntimeError`
- [ ] Renvoie `None`
- Réponse : il renvoie le dict : `-O` supprime les `assert` ; un contrôle de prod lève une vraie exception (`if … raise`).

## 4. contrat de données : vérifié des deux côtés
- Id : qualite-contrat-de-donnees
- Sous-thème : contrôles
- Type : concept
- Niveau : 2
- Profils : data
- Voir aussi : ingestion-evolution-de-schema
- Mots-clés : Lambda, Makefile
- Source : revision-pwa · pwa-revision
- Définition : Un contrat de données fixe le format qu'un producteur livre ; un même code le vérifie avant publication puis à la réception.
- Contexte : Écrit seul, dans une spec, le contrat dérive : chaque producteur l'interprète. Ses règles mesurables (champ manquant, longueur, ordre) vivent donc dans un code unique, lancé par le producteur (`make cards-validate`) et par le consommateur (Lambda `catalog-build`). Les erreurs sortent au format `fichier:carte:champ`, lisibles par un humain comme par un agent. Un fichier en erreur est écarté entier, les autres passent.
- Usage : ✅ toute frontière entre deux dépôts ou deux équipes (fichiers, événements, API) · ❌ contrat implicite (« copie un fichier existant ») : chaque producteur invente sa variante.

```python
# Exemple 1 : une règle, une erreur lisible
def verifier(fichier, cartes):
    erreurs = []
    for n, c in enumerate(cartes, 1):
        if "Réponse" not in c:
            erreurs.append(
                f"{fichier}:{n}:Réponse manquant")
    return erreurs

cartes = [{"Réponse": "oui"}, {}]
verifier("cartes-ko.md", cartes)
# → ['cartes-ko.md:2:Réponse manquant']
```

- Quiz : Le producteur lance `make cards-validate` avant chaque publication : la Lambda doit-elle revalider ?
- [ ] Non : valider deux fois n'apporte rien
- [ ] Non : S3 refuse un fichier invalide
- [x] Oui : rien n'oblige un dépôt S3 à passer par la validation
- Réponse : oui : un `aws s3 cp` à la main ou un autre producteur contourne le contrôle local ; le consommateur ne publie que ce qu'il a lui-même vérifié (fichier `test/cartes-ko.md` écarté à l'étape 10).

## 5. logs JSON : des champs filtrables
- Id : qualite-logs-json-filtrables
- Sous-thème : logs
- Type : recette
- Niveau : 2
- Profils : data, ops
- Mots-clés : Logs Insights, run
- Définition : Un formatter JSON écrit un objet par événement, avec des champs (`run_id`, compteurs) filtrables dans CloudWatch Logs Insights.
- Contexte : Un log texte se lit à l'œil mais se requête mal. En JSON, Logs Insights découvre les champs : `filter run = "r42" | stats sum(lus)`. On passe les champs par `extra={…}` : ils deviennent des attributs du `LogRecord`, que le formatter lit. Les noms réservés du record (`message`, `asctime`, `msg`, `args`…) ne peuvent pas être utilisés dans `extra`.
- Usage : ✅ Lambdas et jobs en prod, corrélation par `run_id` · ❌ script local lu dans un terminal : un format texte reste plus lisible.

```python
# Exemple 1 : un formatter JSON
import json, logging

class Json(logging.Formatter):
    def format(self, r):
        return json.dumps({
            "msg": r.getMessage(),
            "run": r.run_id})

r = logging.makeLogRecord(
    {"msg": "fin", "run_id": "r42"})
Json().format(r)
# → '{"msg": "fin", "run": "r42"}'
```

```python
# Exemple 2 : les champs passés par extra
import io, json, logging

class Json(logging.Formatter):
    def format(self, r):
        return json.dumps({"lus": r.lus})

buf = io.StringIO()
h = logging.StreamHandler(buf)
h.setFormatter(Json())
log = logging.getLogger("ingest19")
log.addHandler(h)
log.warning("bilan", extra={"lus": 1423})
buf.getvalue()  # → '{"lus": 1423}\n'
```

- Quiz : Que fait `log.warning("fin", extra={"message": "x"})` ?
- [ ] Écrit `x` à la place de `fin`
- [ ] Écrit `fin`, `extra` est ignoré
- [ ] Ajoute un second champ `message`
- [x] `KeyError`
- Réponse : `KeyError` (Attempt to overwrite 'message' in LogRecord) : `extra` ne peut pas réutiliser un attribut réservé du record.
