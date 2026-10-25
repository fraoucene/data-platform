---
title: "Cartes · Ingestion"
type: cartes
langage: Data engineering
cours: Ingestion
created: 2026-10-24
updated: 2026-10-25
---

# Cartes · Ingestion
Data engineering · Ingestion : idempotence, rejeux, fiabilité, flux, planification, schéma (format spec v3 de revision-pwa).

## 1. idempotence : écraser, jamais ajouter
- Sous-thème : idempotence
- Niveau : 1
- Définition : Un job idempotent donne le même résultat qu'il tourne une ou dix fois : clé de sortie déterministe, partition remplacée au lieu d'y ajouter.
- Contexte : Les rejeux sont partout : retry automatique (Lambda asynchrone, SQS livré au moins une fois, Step Functions), rejeu manuel, double déclenchement. Si chaque run ajoute ses lignes, la journée est dupliquée. La règle : un run = une partition `dt=` entièrement réécrite, avec des clés dérivées des entrées (jour, numéro de part), jamais d'un `uuid` ou de l'heure du run : écrire deux fois la même clé écrase l'objet. En base : `MERGE` sur la clé métier.
- Usage : ✅ tout job planifié ou rejouable, backfill, clés `dt=<jour>/part-<n>` · ❌ `uuid4()` ou `now()` dans une clé de sortie, ajout sans clé de dédoublonnage : chaque rejeu duplique.

```python
# Exemple 1 : la clé dérivée des entrées
store = {}

def ecrire(jour, n, data):
    cle = f"bodacc/dt={jour}/part-{n:04d}"
    store[cle] = data   # écrase si présent

ecrire("2026-10-23", 1, "v1")
ecrire("2026-10-23", 1, "v1")  # retry
len(store)  # → 1
```

```python
# Exemple 2 : écraser la partition
partitions = {}

def ecrire(jour, lignes):
    partitions[jour] = lignes  # écrase

for _ in range(2):  # job rejoué
    ecrire("2026-10-23", [1, 2, 3])

len(partitions["2026-10-23"])  # → 3
```

```python
# Exemple 3 : clé aléatoire = doublons
import uuid

s3 = {}
for _ in range(2):  # job rejoué
    k = f"dt=2026-10-23/{uuid.uuid4()}"
    s3[k] = b"annonces du jour"
len(s3)  # → 2  (même jour, 2 objets)
```

- Quiz : Que vaut le `len` de l'exemple 2 si `ecrire` fait `partitions.setdefault(jour, []).extend(lignes)` ?
- [ ] `3`
- [x] `6`
- [ ] `2`
- [ ] `KeyError`
- Réponse : `6` : un ajout n'est pas idempotent, chaque rejeu duplique les lignes du jour.

## 2. batch ou streaming : choisir le rythme
- Sous-thème : flux
- Niveau : 1
- Définition : Le batch traite un lot borné à intervalle fixe (une journée) ; le streaming traite chaque événement dès son arrivée, en continu.
- Contexte : Le choix suit la source et le besoin de fraîcheur, pas la mode. BODACC publie une fois par jour : un batch quotidien suffit. Le streaming coûte plus cher : service toujours allumé (Kinesis), ordre, doublons et état à gérer en continu. Entre les deux, le micro-batch (toutes les 5 min) garde la simplicité du lot. Lire un fichier en flux avec un générateur, c'est du streaming de lecture, pas une architecture streaming.
- Usage : ✅ batch : source publiée par lots, rapports quotidiens ; streaming : alerte en secondes, clics, capteurs · ❌ streaming pour une source quotidienne : coût et complexité sans gain de fraîcheur utile.

```python
# Exemple 1 : le gain d'un flux continu
from datetime import datetime as dt

pub = dt(2026, 10, 22, 6, 17)  # source
cron = dt(2026, 10, 22, 7, 0)  # batch
gain = (cron - pub).seconds // 60
gain  # → 43  (minutes, au mieux)
# donnée lue le lendemain : gain nul
```

```python
# Exemple 2 : micro-batch par fenêtre
from itertools import groupby

evts = [("06:01", "A1"), ("06:03", "A2"),
        ("06:07", "A3")]

def fenetre(e):  # tranche de 5 min
    h, m = e[0].split(":")
    return f"{h}:{int(m) // 5 * 5:02d}"

[(k, len(list(g)))
 for k, g in groupby(evts, fenetre)]
# → [("06:00", 2), ("06:05", 1)]
```

- Quiz : Micro-batch déclenché toutes les 5 minutes : quel retard maximal pour un événement ?
- [ ] 2 min 30 : la moitié de la fenêtre
- [ ] Aucun : il est lu à l'arrivée
- [x] 5 minutes, plus la durée du traitement
- [ ] 10 minutes : deux fenêtres
- Réponse : 5 minutes plus le traitement : un événement arrivé juste après un déclenchement attend la fenêtre suivante entière.

## 3. full ou incrémental : tout relire ou le delta
- Sous-thème : rejeux
- Niveau : 1
- Définition : Un chargement complet relit toute la source à chaque run ; un incrémental ne lit que ce qui est nouveau depuis le dernier run.
- Contexte : Le complet est simple et se corrige seul (il reprend aussi les suppressions), mais son coût croît avec l'historique : 51 millions d'annonces BODACC à 1 835 octets, environ 94 Go par run. L'incrémental lit une journée (59 Mo) mais exige un critère fiable de nouveauté (date de parution, watermark). Règle : complet tant que la source est petite, incrémental dès qu'elle grossit.
- Usage : ✅ complet : référentiel de quelques milliers de lignes (tribunaux) ; incrémental : annonces, logs · ❌ incrémental sur une date peu fiable (date de saisie modifiable) : des lignes passent entre deux runs.

```python
# Exemple 1 : le coût de chaque stratégie
total = 51_155_363      # annonces
jour = 32_373
o = 1_835               # octets / annonce
round(total * o / 1e9)  # → 94  (Go, complet)
round(jour * o / 1e6)   # → 59  (Mo, delta)
```

```python
# Exemple 2 : le delta depuis le watermark
from datetime import date

source = [("A1", date(2026, 10, 21)),
          ("A2", date(2026, 10, 22)),
          ("A3", date(2026, 10, 23))]
wm = date(2026, 10, 21)
[i for i, d in source if d > wm]
# → ["A2", "A3"]
```

- Quiz : La source supprime `A1` après coup : quel mode de chargement le voit ?
- [x] Le complet seulement
- [ ] L'incrémental seulement
- [ ] Les deux
- [ ] Aucun des deux
- Réponse : le complet seulement : il relit tout et constate l'absence ; l'incrémental ne relit que les lignes nouvelles, une suppression n'en produit pas (il faut du CDC).

## 4. pull ou push : qui déclenche
- Sous-thème : planification
- Niveau : 1
- Définition : En pull, le pipeline va chercher la donnée selon un horaire ; en push, la source (ou S3) prévient le pipeline à chaque arrivée.
- Contexte : Une API publique comme BODACC n'envoie rien : on la sonde (pull) sur un cron EventBridge Scheduler. Un partenaire qui dépose un fichier dans S3 déclenche au contraire le traitement par notification (push) : pas d'attente, pas d'appel à vide. Le pull doit gérer « rien de neuf » ; le push doit gérer les notifications en double et surveiller l'absence, car personne ne prévient d'un fichier qui n'arrive pas.
- Usage : ✅ pull : API sans webhook, quota à maîtriser ; push : dépôt S3, webhook, file SQS · ❌ sonder chaque minute une source quotidienne : quota brûlé pour rien.

```python
# Exemple 1 : pull, sonder la source
publies = {"2026-10-22"}   # source

def sonder(jour):
    return jour in publies  # un GET

[sonder(j) for j in
 ("2026-10-22", "2026-10-23")]
# → [True, False]  (rien de neuf)
```

```python
# Exemple 2 : push, la source prévient
traites = []
abonnes = [traites.append]   # Lambda

def deposer(cle):            # PutObject
    for notifier in abonnes:
        notifier(cle)

deposer("in/2026-10-23.csv")
traites  # → ["in/2026-10-23.csv"]
```

- Quiz : En push, le fichier du partenaire n'arrive jamais : que se passe-t-il par défaut ?
- [ ] La Lambda lève une erreur
- [x] Rien : aucun run, aucune alerte
- [ ] S3 renvoie la notification plus tard
- [ ] Le cron de secours relance
- Réponse : rien : sans objet créé, aucun événement ; il faut une alarme sur l'absence (contrôle planifié « fichier du jour présent ? »).

## 5. date logique : le jour traité, pas l'horloge
- Sous-thème : planification
- Niveau : 1
- Définition : Un run planifié traite une date logique (J-1) reçue en paramètre ; il ne la recalcule jamais depuis l'horloge au moment où il tourne.
- Contexte : Le cron de 07:00 UTC du 24 traite la parution du 23. Si le job lit `date.today()`, un rejeu lancé le 26 traite le 25 au lieu du 23, et un backfill devient impossible. Comme dans Airflow (`logical_date`), le déclencheur calcule la date et le job la reçoit (`event["jour"]`). Le job devient une fonction de sa date : rejouable, testable sans figer l'horloge.
- Usage : ✅ tout job quotidien : `jour` dans l'événement, défaut J-1 calculé à l'entrée · ❌ `date.today()` au cœur du traitement : rejeux et backfills faux, tests qui dépendent du jour.

```python
# Exemple 1 : la date vient de l'événement
from datetime import date, timedelta

def handler(event, today):
    j = event.get("jour")
    if j is None:          # run planifié
        return today - timedelta(days=1)
    return date.fromisoformat(j)  # rejeu

auj = date(2026, 10, 26)
handler({}, auj)  # → date(2026, 10, 25)
handler({"jour": "2026-10-23"}, auj)
# → date(2026, 10, 23)
```

- Quiz : Le job calcule `date.today() - timedelta(days=1)`. Le run du 24 échoue, on le relance le 25 : quel jour est traité ?
- [ ] Le 23
- [x] Le 24
- [ ] Le 25
- [ ] Le 22
- Réponse : le 24 : relancé le 25, le job recalcule J-1 = 24 ; le 23, celui qui avait échoué, n'est jamais traité.

## 6. jour clos : refuser aujourd'hui
- Sous-thème : planification
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Une ingestion quotidienne ne traite qu'une journée terminée : le jour même et le futur sont refusés, jamais ingérés à moitié.
- Contexte : La parution du jour peut encore grossir : l'ingérer à 10 h produit une partition partielle, que le manifest (nombre d'annonces, `_SUCCESS`) déclarerait complète, et que personne ne relirait. `resolve_day` refuse donc `day >= today`, avec `today` calculé à Paris. Une erreur explicite vaut mieux qu'un trou silencieux ; une date future, elle, n'a encore rien publié.
- Usage : ✅ tout job « par journée » : borne `day < today` dans le fuseau de la source · ❌ ingérer « ce qu'il y a déjà » du jour en cours et le marquer complet.

```python
# Exemple 1 : seule une journée finie passe
from datetime import date
def jour_clos(day, today):
    if day >= today:
        raise ValueError(f"{day} pas terminé")
    return day
t = date(2026, 10, 26)
jour_clos(date(2026, 10, 25), t)
# → date(2026, 10, 25)
jour_clos(t, t)    # ❌ ValueError
```

- Quiz : Rejeu manuel `{"date": "2026-10-26"}` lancé le 26 à 23:50 heure de Paris : que fait `resolve_day` ?
- [ ] Ingère le 26 : il est presque fini
- [x] `ValueError` : le 26 n'est pas terminé
- [ ] Ingère le 25 à la place
- [ ] Ingère le 26 et le marque partiel
- Réponse : `ValueError` : à Paris on est encore le 26, donc `day >= today` ; il faudra relancer après minuit.

## 7. fail fast : valider l'événement d'abord
- Sous-thème : fiabilité
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Le handler valide ses paramètres (date, format, fuseau) avant tout appel réseau ou écriture, et lève une erreur claire si l'un est faux.
- Contexte : Une date invalide découverte après l'appel à l'API, ou en cours d'écriture, laisse des fichiers partiels et un message obscur (`KeyError`, `TypeError` loin de la cause). Valider tout de suite coûte une milliseconde et rend l'erreur permanente évidente : Step Functions la route en `Catch` au lieu de la réessayer. C'est le rôle de `resolve_day`, première ligne du handler.
- Usage : ✅ toute Lambda déclenchée par un événement : valider puis agir · ❌ valider « au passage », au milieu du traitement.

```python
# Exemple 1 : rien n'est appelé si invalide
from datetime import date
appels = []
def handler(event):
    day = date.fromisoformat(event["date"])
    appels.append(f"fetch {day}")
    appels.append(f"write dt={day}")
handler({"date": "2026-13-01"})  # ❌ ValueError
appels   # → []
```

- Quiz : La date est validée après l'écriture de 3 fichiers sur 5. Elle s'avère invalide : état de la partition ?
- [ ] Vide : l'erreur annule tout
- [x] Partielle : 3 fichiers, sans manifest
- [ ] Complète : les 5 fichiers
- [ ] Supprimée par Lambda
- Réponse : partielle : rien n'annule les écritures déjà faites sur S3 ; valider d'abord évite d'avoir à nettoyer.

## 8. date logique : un objet date, pas une chaîne
- Sous-thème : schéma
- Niveau : 1
- Source : data-platform · S1-07
- Définition : La date reçue en chaîne devient un `date` une fois, à l'entrée ; le job manipule ce `date` et ne reformate qu'à la sortie.
- Contexte : Une chaîne `"2026-10-20"` ne se compare, ne se décale ni ne se valide : un `date` oui (`day - timedelta(1)`, `day >= today`). Convertir à la frontière concentre la validation en un seul endroit (`resolve_day`). Pour la clé S3, `f"dt={day.isoformat()}"` redonne le format canonique, même si l'entrée était `20261020`.
- Usage : ✅ `date` dans tout le code interne, chaîne seulement en entrée et en sortie · ❌ passer la chaîne brute de fonction en fonction et la re-parser à chaque étape.

```python
# Exemple 1 : parser une fois, formater à la fin
from datetime import date, timedelta
day = date.fromisoformat("20261020")
f"dt={day.isoformat()}"  # → "dt=2026-10-20"
day - timedelta(1)   # → date(2026, 10, 19)
```

- Quiz : Avec `day = date(2026, 10, 20)`, que vaut `f"dt={day:%Y/%m/%d}"` ?
- [ ] `"dt=2026-10-20"`
- [x] `"dt=2026/10/20"`
- [ ] `ValueError`
- [ ] `"dt=%Y/%m/%d"`
- Réponse : `"dt=2026/10/20"` : une `date` accepte les codes `strftime` dans une f-string, après `:`.

## 9. ordre des lignes : il fait partie des octets
- Sous-thème : idempotence
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Les mêmes lignes dans un autre ordre donnent un autre fichier, donc un autre hash : l'ordre de lecture fait partie du résultat.
- Contexte : Un hash ne compare pas des ensembles, il compare des octets. Si la source rend les annonces dans un autre ordre au rejeu, le fichier change, son sha256 aussi, et rien ne distingue ce faux changement d'une vraie correction. « Mêmes octets au rejeu » suppose donc un ordre de lecture fixe, en plus d'une sérialisation fixe (clés triées, format compact).
- Usage : ✅ partition comparée par hash, test « deux écritures = mêmes octets » · ❌ consommateur qui ne compare que des ensembles d'id : l'ordre ne compte pas, inutile de le figer.

```python
# Exemple 1 : mêmes lignes, autre ordre
from hashlib import sha256
a = b'{"id":"A1"}\n{"id":"A2"}\n'
b = b'{"id":"A2"}\n{"id":"A1"}\n'
sha256(a).digest() == sha256(b).digest()
# → False
set(a.split()) == set(b.split())
# → True  (même contenu)
```

```python
# Exemple 2 : ordre fixé, mêmes octets
import json

def octets(rows):
    rows = sorted(rows, key=lambda r: r["id"])
    return "".join(json.dumps(r) + "\n"
                   for r in rows).encode()

run1 = [{"id": "A1"}, {"id": "A2"}]
run2 = [{"id": "A2"}, {"id": "A1"}]
octets(run1) == octets(run2)  # → True
```

- Quiz : Le rejeu rend `A1`, `A2`, `A2` au lieu de `A1`, `A2`. Que vaut la comparaison des `set` de l'exemple 1 ?
- [ ] `False`
- [x] `True`
- [ ] `TypeError`
- Réponse : `True` : un `set` écrase les doublons ; seul le hash des octets voit la ligne en trop.

## 10. manifest : un _SUCCESS qui décrit
- Sous-thème : flux
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Un manifest est un petit JSON écrit après les données : il marque la partition complète et décrit le fichier (lignes, empreinte, tailles, format).
- Contexte : Un `_SUCCESS` vide dit seulement « fini ». Le manifest dit aussi quoi : le lecteur sait combien de lignes attendre, peut vérifier l'empreinte, connaît le format et le code qui a écrit, sans ouvrir le fichier. Il reste un marqueur : écrit en dernier, son absence veut dire « partition pas prête ». Équivalent TS : le `package.json` d'un dossier `dist/`, qui décrit ce qui est livré.
- Usage : ✅ partition lue par un autre job (contrôle qualité, chargement aval) · ❌ y recopier les données ou des stats ligne à ligne : il doit rester petit et lisible.

```python
# Exemple 1 : prête si le manifest existe
s3 = {"date=2026-10-20/part-0001.jsonl.gz": b"",
      "date=2026-10-20/_MANIFEST.json":
          {"count": 2, "sha256": "bbdf3f0a"}}

def lire(jour):
    m = s3.get(f"date={jour}/_MANIFEST.json")
    return None if m is None else m["count"]

lire("2026-10-20")   # → 2
lire("2026-10-21")   # → None : pas prête
```

- Quiz : Le lecteur trouve `part-0001.jsonl.gz` sous `date=…/`, mais pas `_MANIFEST.json` : que fait-il ?
- [ ] Il lit le part : le fichier est là
- [x] Il considère la partition non prête
- [ ] Il supprime le part orphelin
- [ ] Il lit le part et recalcule le manifest
- Réponse : il la considère non prête : seul le manifest publie la partition ; un part sans manifest est peut-être en cours d'écriture ou d'un run interrompu.

## 11. manifest : quoi, combien, prouvé comment
- Sous-thème : flux
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Un manifest utile répond à trois questions : quoi (source, date, clé, format), combien (lignes, octets), prouvé comment (sha256, version du code).
- Contexte : Dans `build_manifest` : `source`, `date`, `part`, `format`, `count`, `sha256`, `raw_bytes`, `gz_bytes`, `fetched_at`, `bodacc_client_version`. `raw_bytes` sert au contrôle et au sha256 ; `gz_bytes` à estimer le stockage et le scan. Tout est mesuré par le writer pendant l'écriture : aucune seconde lecture du fichier. La version du client relie chaque partition au code qui l'a produite.
- Usage : ✅ champs mesurés par le writer, sérialisables tels quels (`json.dumps`) · ❌ champs calculés en relisant le fichier, ou objets non JSON (`date`, `Decimal`) : chaînes ISO, nombres.

```python
# Exemple 1 : le manifest du 20 octobre
manifest = {
    "source": "bodacc", "date": "2026-10-20",
    "part": "bodacc/date=2026-10-20/"
            "part-0001.jsonl.gz",
    "format": "jsonl.gz", "count": 2,
    "sha256": "bbdf3f0a", "raw_bytes": 131,
    "gz_bytes": 112,
    "fetched_at": "2026-10-21T05:00:12+00:00",
    "bodacc_client_version": "0.1.0"}
manifest["part"].startswith(
    "bodacc/date=" + manifest["date"])  # → True
round(manifest["gz_bytes"] / manifest["raw_bytes"], 2)
# → 0.85
```

- Quiz : Quel champ retrouve les partitions écrites par une version boguée du client BODACC ?
- [ ] `fetched_at`, la date du déploiement
- [ ] `sha256`
- [x] `bodacc_client_version`
- [ ] `format`
- Réponse : `bodacc_client_version` : `fetched_at` donne l'heure du run, pas le code qui tournait ; la version écrite par le writer (`importlib.metadata.version`) est le lien sûr.

## 12. _MANIFEST : le souligné qui cache
- Sous-thème : flux
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Nommer le manifest `_MANIFEST.json`, comme `_SUCCESS`, le fait ignorer par Athena, Hive et Spark, qui sautent les fichiers commençant par `_` ou `.`.
- Contexte : Ces moteurs lisent tous les objets sous l'emplacement d'une partition. Un `manifest.json` sans souligné serait lu comme une donnée : une ligne de plus, ou une erreur de format dans une table `jsonl.gz`. La convention vient de Hadoop (`_SUCCESS`, `_logs`) : un nom en `_` ou `.` désigne un fichier technique. Notre propre lecteur, lui, le cherche par son nom exact.
- Usage : ✅ tout fichier technique d'une partition : `_MANIFEST.json`, `_SUCCESS` · ❌ `manifest.json`, `README.txt` ou `.csv` d'export à côté des données d'une table.

```python
# Exemple 1 : ce qu'un moteur lit
cles = ["date=2026-10-20/part-0001.jsonl.gz",
        "date=2026-10-20/_MANIFEST.json",
        "date=2026-10-20/manifest.json"]

def lues(cles):
    nom = lambda k: k.rsplit("/", 1)[-1]
    return [k for k in cles
            if not nom(k).startswith(("_", "."))]

len(lues(cles))   # → 2 : manifest.json est lu
```

- Quiz : Lequel de ces fichiers Athena lit-il comme une donnée de la partition ?
- [ ] `_SUCCESS`
- [ ] `.manifest.json`
- [x] `manifest.json`
- [ ] `_MANIFEST.json`
- Réponse : `manifest.json` : sans `_` ni `.` en tête, c'est un objet comme les autres, lu avec les données ; les trois autres sont ignorés.

## 13. backfill : rejouer une plage
- Sous-thème : rejeux
- Niveau : 2
- Définition : Un backfill relance l'ingestion sur une plage de jours passés (trou, bug corrigé), jour par jour, grâce à l'idempotence.
- Contexte : Un bug dans le parsing, une panne de l'API, une nouvelle colonne à remplir : on relance le même job sur chaque jour concerné. C'est sûr uniquement si le job est idempotent (il écrase sa partition). On boucle jour par jour plutôt qu'en un seul appel sur toute la plage : une erreur ne fait rejouer qu'un jour, et chaque jour garde sa partition `dt=`.
- Usage : ✅ combler un trou, recalculer `processed` après un correctif · ❌ job qui ajoute au lieu d'écraser : le backfill duplique les données.

```python
# Exemple 1 : la plage de jours, fin incluse
from datetime import date, timedelta

def jours(debut, fin):
    n = (fin - debut).days + 1
    return [debut + timedelta(i)
            for i in range(n)]

j = jours(date(2026, 10, 20),
          date(2026, 10, 23))
len(j)  # → 4
```

```python
# Exemple 2 : un job par jour
from datetime import date, timedelta

parts = {}
def ingerer(jour):          # idempotent
    parts[f"dt={jour}"] = "ok"

d = date(2026, 10, 30)
while d <= date(2026, 11, 2):
    ingerer(d)
    d += timedelta(days=1)
list(parts)[-1]  # → "dt=2026-11-02"
```

- Quiz : Que vaut `date(2026, 10, 20) + timedelta(hours=23)` ?
- [ ] `date(2026, 10, 21)`
- [x] `date(2026, 10, 20)`
- [ ] `datetime(2026, 10, 20, 23, 0)`
- [ ] `TypeError`
- Réponse : `date(2026, 10, 20)` : une `date` ignore la partie heures d'un `timedelta` ; seuls les jours entiers comptent.

## 14. dédoublonnage : garder la dernière version
- Sous-thème : idempotence
- Niveau : 2
- Définition : On dédoublonne sur une clé métier (id d'annonce) en gardant la dernière version : rejeux et lots qui se recouvrent renvoient la même ligne.
- Contexte : Un dict indexé par la clé métier fait le travail en une passe : chaque nouvelle version écrase l'ancienne, et l'ordre d'insertion de la première apparition est conservé. Le piège est de choisir la mauvaise clé : dans BODACC, `numeroannonce` repart à 1 dans chaque bulletin (A, B, C), donc seule la paire `(bulletin, numero)` est unique.
- Usage : ✅ fusionner des pages ou des runs qui se recouvrent, rejouer une journée · ❌ clé non unique : on perd des annonces en silence ; rectificatif à id propre : l'appliquer à l'annonce visée.

```python
# Exemple 1 : la dernière version gagne
annonces = [
    {"id": "A1", "v": 1},
    {"id": "A2", "v": 1},
    {"id": "A1", "v": 2},  # relu
]
uniques = {a["id"]: a
           for a in annonces}
[a["v"] for a in uniques.values()]
# → [2, 1]
```

```python
# Exemple 2 : la bonne clé est composée
lignes = [
    {"bulletin": "A", "numero": 1},
    {"bulletin": "B", "numero": 1},
]
len({l["numero"]: l
     for l in lignes})  # → 1  (perdue)
len({(l["bulletin"], l["numero"]): l
     for l in lignes})  # → 2
```

- Quiz : Que fait `set(annonces)` pour dédoublonner la liste de l'exemple 1 ?
- [ ] Renvoie 2 annonces
- [ ] Renvoie 3 annonces
- [x] `TypeError`
- Réponse : `TypeError` (unhashable type: 'dict') : un dict est mutable donc non hachable ; passer par une clé.

## 15. watermark : reprendre où on s'est arrêté
- Sous-thème : rejeux
- Niveau : 2
- Définition : Le watermark est le dernier jour traité avec succès ; le run suivant repart du lendemain (≈ un curseur de pagination).
- Contexte : Une Lambda quotidienne qui traite « hier » rate des jours dès qu'un run échoue. Avec un watermark persisté (fichier d'état S3, item DynamoDB), le run suivant traite tous les jours depuis le dernier succès, et rattrape seul les trous. On ne l'avance qu'après l'écriture complète de la partition, jamais avant.
- Usage : ✅ ingestion incrémentale quotidienne, reprise après panne · ❌ watermark avancé avant la fin de l'écriture : un crash laisse un trou que personne ne revoit.

```python
# Exemple 1 : repartir du lendemain
from datetime import date, timedelta

traites = [date(2026, 10, 21),
           date(2026, 10, 22)]
wm = max(traites)
prochain = wm + timedelta(days=1)
prochain  # → date(2026, 10, 23)
```

```python
# Exemple 2 : l'état persisté en JSON
import json
from datetime import date

etat = '{"watermark": "2026-10-22"}'
wm = date.fromisoformat(
    json.loads(etat)["watermark"])
(date(2026, 10, 25) - wm).days
# → 3  (jours à rattraper)
```

- Quiz : Que fait `max(traites)` au tout premier run, quand `traites == []` ?
- [ ] Renvoie `None`
- [x] `ValueError`
- [ ] Renvoie `date.min`
- Réponse : `ValueError` (iterable argument is empty) : prévoir `max(traites, default=date_debut)`.

## 16. retry : backoff exponentiel
- Sous-thème : fiabilité
- Niveau : 2
- Définition : On réessaie un appel en échec avec un délai qui double à chaque essai, plafonné et randomisé (jitter) pour ne pas saturer la source.
- Contexte : Sans délai croissant, un client qui réessaie en boucle aggrave la surcharge qui a causé l'erreur. Le plafond borne l'attente, le jitter évite que plusieurs workers relancent tous au même instant. Si la réponse porte `Retry-After`, on le respecte. On ne réessaie que les erreurs transitoires (quota, 5xx, réseau), et dans `fetch_day` seulement avant la première annonce rendue, sinon on émettrait des doublons.
- Usage : ✅ appels HTTP vers une API à quota (BODACC), S3, DynamoDB ; sur AWS, Step Functions le déclare dans `Retry` · ❌ erreur permanente (requête invalide, 404) : réessayer ne change rien, lever tout de suite.

```python
# Exemple 1 : délai doublé et plafonné
import random

def delai(essai, plafond=30):
    d = min(plafond, 2 ** essai)
    return random.uniform(0, d)  # jitter

[min(30, 2 ** e) for e in range(7)]
# → [1, 2, 4, 8, 16, 30, 30]
0 <= delai(3) <= 8  # → True
```

```python
# Exemple 2 : la boucle, réponses simulées
reponses = iter([503, 503, 200])
attentes = []

def appel(max_essais=5):
    for essai in range(max_essais):
        statut = next(reponses)
        if statut == 200:
            return essai
        attentes.append(2 ** essai)

appel()   # → 2  (réussi au 3e essai)
attentes  # → [1, 2]
```

```python
# Exemple 3 : Retry-After d'abord, sleep injecté
def backoff(essai, retry_after=None):
    if retry_after and retry_after.isdigit():
        return float(retry_after)  # serveur
    return min(2.0 ** essai, 30.0)

attentes = []
sleep = attentes.append   # faux time.sleep
sleep(backoff(0, "7"))    # 429 + en-tête
sleep(backoff(3))         # pas d'en-tête
sleep(backoff(1, "Sat, 24 Oct 2026"))
attentes  # → [7.0, 8.0, 2.0]
```

- Quiz : `429 Too Many Requests` ou `400 Bad Request` : lequel réessayer ?
- [x] Le `429`
- [ ] Le `400`
- [ ] Les deux
- [ ] Aucun des deux
- Réponse : le `429` : quota temporaire qui se libère ; un `400` renverra la même erreur, la requête elle-même est fausse.

## 17. générateurs : un pipeline en flux
- Sous-thème : flux
- Niveau : 2
- Définition : Chaîner des générateurs fait passer les lignes une à une d'étape en étape, mémoire constante quelle que soit la taille du fichier.
- Contexte : Chaque étape (`lire`, `parser`, `filtrer`) consomme un itérable et en produit un autre, sans liste intermédiaire. Rien ne s'exécute tant que la dernière étape n'itère pas : c'est paresseux. `fetch_day` du client BODACC est un générateur : aucune requête n'est faite avant le premier `for`. Un générateur s'épuise : après un parcours complet, il ne rend plus rien.
- Usage : ✅ fichiers JSON Lines de plusieurs dizaines de Mo, flux HTTP en streaming · ❌ données qu'on parcourt plusieurs fois ou qu'on trie : matérialiser en `list`.

```python
# Exemple 1 : deux étapes chaînées
def lire(lignes):
    for l in lignes:
        yield l.strip()

def non_vides(it):
    return (l for l in it if l)

flux = non_vides(
    lire(["A1\n", "\n", "A2\n"]))
list(flux)  # → ["A1", "A2"]
```

```python
# Exemple 2 : compter sans tout charger
import json

def parser(lignes):
    for l in lignes:
        yield json.loads(l)

brut = ['{"t": "A"}', '{"t": "B"}',
        '{"t": "A"}']
sum(1 for a in parser(brut)
    if a["t"] == "A")  # → 2
```

- Quiz : Dans l'exemple 1, que vaut un second `list(flux)` juste après le premier ?
- [ ] `["A1", "A2"]`
- [ ] `["A1", "", "A2"]`
- [x] `[]`
- [ ] `StopIteration`
- Réponse : `[]` : un générateur ne se parcourt qu'une fois ; pour compter puis écrire, recréer le flux.

## 18. _SUCCESS : signaler une partition complète
- Sous-thème : flux
- Niveau : 2
- Définition : Un fichier vide `_SUCCESS` écrit en fin de job signale aux lecteurs que la partition est complète et lisible.
- Contexte : Une partition fait plusieurs fichiers écrits l'un après l'autre : un lecteur qui arrive pendant l'écriture verrait une journée partielle. Le marqueur, écrit à la toute fin, est le signal « fini ». Spark l'écrit par défaut, et un consommateur (Lambda, job aval) attend sa présence avant de lire. Un rejeu commence par le supprimer.
- Usage : ✅ partitions multi-fichiers lues par d'autres jobs · ❌ partition d'un seul objet S3 : son écriture est déjà atomique.

```python
# Exemple 1 : marquer et tester
import os, tempfile

d = tempfile.mkdtemp()
for n in range(2):
    open(f"{d}/part-{n}", "w").close()
open(f"{d}/_SUCCESS", "w").close()

def prete(dossier):
    return "_SUCCESS" in os.listdir(dossier)

prete(d)  # → True
```

```python
# Exemple 2 : le lecteur attend le marqueur
s3 = {"dt=2026-10-23/part-0": b"..."}

def lire(jour):
    if f"dt={jour}/_SUCCESS" not in s3:
        return None  # pas encore prête
    return [k for k in s3 if jour in k]

lire("2026-10-23")  # → None
```

- Quiz : Le job écrit `_SUCCESS` en premier, puis plante sur `part-1` : que lit le consommateur ?
- [ ] Rien : il attend le marqueur
- [x] Une partition incomplète, crue complète
- [ ] Une erreur à la lecture de `part-1`
- Réponse : une partition incomplète qu'il croit complète : le marqueur s'écrit toujours en dernier.

## 19. fraîcheur : planifier après la source
- Sous-thème : planification
- Niveau : 2
- Source : data-platform · S1-05
- Définition : Une ingestion quotidienne se planifie après l'heure réelle de mise à jour de la source, lue dans ses métadonnées, avec une marge, en UTC.
- Contexte : Les métadonnées du dataset BODACC donnent `data_processed` : `2026-10-22T06:17:43+00:00`, soit 08:17 à Paris en octobre, 07:17 en novembre. Un cron en heure de Paris dérive au changement d'heure : on planifie en UTC fixe (`cron(0 7 * * ? *)`). La source ne publie pas tous les jours : J-1 peut légitimement être vide, ce n'est pas une panne.
- Usage : ✅ toute source quotidienne : relever l'heure de mise à jour sur plusieurs jours avant de fixer le cron · ❌ planifier « tôt le matin » à l'intuition, ou alerter sur 0 ligne sans calendrier de publication.

```python
# Exemple 1 : l'heure de la source à Paris
from datetime import datetime
from zoneinfo import ZoneInfo

maj = datetime.fromisoformat(
    "2026-10-22T06:17:43+00:00")
p = maj.astimezone(ZoneInfo("Europe/Paris"))
p.strftime("%H:%M")   # → "08:17"
```

```python
# Exemple 2 : la marge avant le cron UTC
from datetime import datetime, timedelta

maj = datetime.fromisoformat(
    "2026-10-22T06:17:43+00:00")
cron = maj.replace(hour=7, minute=0,
                   second=0)
cron - maj
# → timedelta(seconds=2537)  (≈ 42 min)
cron - maj >= timedelta(minutes=30)
# → True
```

- Quiz : Un cron à 07:00 heure de Paris lit J-1 le 2026-10-23 : quel problème ?
- [ ] Aucun : 07:00 est après 06:17
- [x] 07:00 Paris = 05:00 UTC : trop tôt
- [ ] 07:00 Paris = 08:00 UTC : trop tard
- [ ] Aucun : J-1 est publiée la veille
- Réponse : 07:00 à Paris = 05:00 UTC en octobre, avant la mise à jour de 06:17 UTC : le run lit une journée incomplète ou vide.

## 20. at-least-once : le doublon est normal
- Sous-thème : fiabilité
- Niveau : 2
- Définition : SQS standard, les notifications S3 et la Lambda asynchrone livrent chaque message au moins une fois : un même message peut arriver deux fois.
- Contexte : Garantir « exactement une fois » de bout en bout coûte cher : la plateforme préfère livrer parfois deux fois plutôt que perdre. L'effet « exactement une fois » s'obtient côté consommateur : traitement idempotent (écrasement d'une clé) ou mémoire des ids déjà traités. SQS FIFO dédoublonne, mais seulement sur une fenêtre de 5 minutes ; au-delà, le consommateur reste responsable.
- Usage : ✅ tout consommateur d'événements : supposer le doublon, rendre l'effet idempotent · ❌ compteur incrémenté ou ligne ajoutée à chaque message : un rejeu fausse le total.

```python
# Exemple 1 : un message livré deux fois
msgs = [{"id": "m1", "n": 5},
        {"id": "m1", "n": 5}]  # rejeu
total = 0
for m in msgs:
    total += m["n"]   # non idempotent
total  # → 10  (5 attendu)
```

```python
# Exemple 2 : mémoriser les ids traités
vus, total = set(), 0
for m in [{"id": "m1", "n": 5},
          {"id": "m1", "n": 5}]:
    if m["id"] in vus:
        continue          # déjà traité
    total += m["n"]
    vus.add(m["id"])      # après l'effet
total  # → 5
```

- Quiz : Exemple 2 : on fait `vus.add` avant `total += …`, puis le traitement plante ; au rejeu, que devient `m1` ?
- [ ] Il est traité normalement
- [ ] Il est traité deux fois
- [x] Il est ignoré, jamais traité
- [ ] `KeyError` sur `vus`
- Réponse : ignoré : l'id est marqué vu alors que l'effet n'a pas eu lieu ; on marque toujours après l'effet, ou dans la même transaction.

## 21. ordre : appliquer par version, pas par arrivée
- Sous-thème : fiabilité
- Niveau : 2
- Définition : Les événements peuvent arriver dans le désordre ; on garde celui dont la version (date source, numéro) est la plus haute, pas le dernier reçu.
- Contexte : Retries, parallélisme, plusieurs partitions : un rectificatif peut être traité avant l'annonce qu'il corrige. « Le dernier arrivé gagne » réécrit alors une valeur périmée. On compare donc un champ porté par l'événement (horodatage source, numéro de séquence, LSN en CDC) avant d'écrire. Seules des files ordonnées (SQS FIFO, shard Kinesis) garantissent l'ordre, et seulement par clé, au prix du débit.
- Usage : ✅ upsert d'états (statut d'une entreprise), CDC, consommateurs parallèles · ❌ heure de réception comme version : elle date l'arrivée, pas le fait.

```python
# Exemple 1 : le dernier arrivé gagne
recus = [("483609327", 2, "radiée"),
         ("483609327", 1, "active")]
etat = {}
for siren, v, statut in recus:
    etat[siren] = statut   # naïf
etat["483609327"]  # → "active"  (périmé)
```

```python
# Exemple 2 : la version la plus haute gagne
recus = [("483609327", 2, "radiée"),
         ("483609327", 1, "active")]
etat = {}
for siren, v, statut in recus:
    old = etat.get(siren, (0, None))
    if v > old[0]:
        etat[siren] = (v, statut)
etat["483609327"]  # → (2, "radiée")
```

- Quiz : Exemple 2 : deux événements de même version 2, `radiée` reçu puis `active` : que garde `v > old[0]` ?
- [x] `(2, "radiée")`
- [ ] `(2, "active")`
- [ ] `ValueError`
- Réponse : `(2, "radiée")` : à égalité, le premier reçu reste ; une version doit être unique par clé, ou départagée (numéro de séquence).

## 22. CDC : rejouer les changements d'une base
- Sous-thème : flux
- Niveau : 2
- Définition : Le CDC (Change Data Capture) transmet chaque insert, update et delete d'une base source, dans l'ordre de son journal, au lieu de recopier les tables.
- Contexte : Plutôt que relire 10 millions de lignes chaque nuit, on lit le journal de transactions (binlog MySQL, WAL PostgreSQL) avec DMS ou Debezium. Chaque événement porte une opération (`I`, `U`, `D`), la clé, l'état après, et une position (LSN) qui sert d'ordre et de point de reprise. Contrairement à l'incrémental par date, le CDC voit les suppressions. Il commence par un chargement complet, puis suit les changements depuis sa position.
- Usage : ✅ répliquer une base applicative vers le lake, propager des suppressions · ❌ API publique ou dépôt de fichiers : pas de journal, rester sur un incrémental par date.

```python
# Exemple 1 : appliquer I, U, D dans l'ordre
evts = [(1, "I", "A1", "active"),
        (2, "U", "A1", "radiée"),
        (3, "I", "A2", "active"),
        (4, "D", "A2", None)]
table = {}
for lsn, op, cle, val in evts:
    if op == "D":
        table.pop(cle, None)
    else:
        table[cle] = val
table  # → {"A1": "radiée"}
```

```python
# Exemple 2 : reprendre après le dernier LSN
evts = [(1, "I"), (2, "U"), (3, "D")]
dernier = 2           # LSN persisté
[e for e in evts if e[0] > dernier]
# → [(3, "D")]
```

- Quiz : Exemple 1 : l'événement 4 (`D`) est appliqué avant le 3 (`I`). Que vaut `table` ?
- [ ] `{"A1": "radiée"}`
- [ ] `{}`
- [x] `{"A1": "radiée", "A2": "active"}`
- [ ] `KeyError`
- Réponse : `{"A1": "radiée", "A2": "active"}` : la suppression passe sur une clé absente (`pop` avec défaut), puis l'insertion recrée une ligne supprimée à la source ; d'où l'ordre par LSN.

## 23. évolution de schéma : ajouter, jamais renommer
- Sous-thème : schéma
- Niveau : 2
- Définition : Une source change de schéma avec le temps : un champ ajouté se tolère, un champ renommé ou retypé casse les consommateurs.
- Contexte : Un lecteur tolérant ignore les champs inconnus et met une valeur par défaut aux absents : l'ajout passe sans incident. Un renommage, lui, ressemble à « un champ disparu, un nouveau apparu » : la colonne devient nulle en silence. On compare donc à chaque run les clés reçues aux clés attendues, et on alerte sur toute disparition. BODACC expose son schéma (32 champs typés) dans les métadonnées du dataset.
- Usage : ✅ comparer reçu et attendu à chaque run, alerter sur un champ disparu, tolérer l'ajout · ❌ attendre un `KeyError` en production, ou `.get()` partout sans contrôle : le renommage passe inaperçu.

```python
# Exemple 1 : ce qui a changé
attendu = {"id", "dateparution",
           "familleavis"}
recu = {"id", "date_parution",
        "familleavis", "region_code"}
sorted(attendu - recu)
# → ["dateparution"]   (disparu : alerte)
sorted(recu - attendu)
# → ["date_parution", "region_code"]
```

```python
# Exemple 2 : .get() masque le renommage
a = {"id": "A1",
     "date_parution": "2026-10-20"}
a.get("dateparution")  # → None
# colonne nulle, aucune erreur
```

- Quiz : Exemple 1 : la source garde les mêmes clés mais `familleavis` passe d'une chaîne à une liste. Que vaut `attendu - recu` ?
- [ ] `{"familleavis"}`
- [x] `set()`
- [ ] `TypeError`
- Réponse : `set()` : comparer les noms de clés ne voit pas les types ; contrôler aussi le type de chaque champ (modèle pydantic, schéma déclaré).

## 24. lookback : relire les derniers jours
- Sous-thème : rejeux
- Niveau : 2
- Définition : Une fenêtre de relecture (lookback) refait aussi les N derniers jours à chaque run, pour rattraper les données publiées en retard.
- Contexte : Un watermark strict suppose qu'un jour clos ne change plus. Or une source peut compléter une journée après coup (annonces ajoutées le lendemain, corrections). Relire J-1 à J-3 à chaque run, en écrasant leurs partitions, les rattrape ; l'idempotence rend la relecture sans risque. Le coût est proportionnel à N : on le fixe d'après le retard réellement observé sur la source, pas au hasard.
- Usage : ✅ sources qui complètent des jours passés, données tardives (logs mobiles, événements hors ligne) · ❌ job qui ajoute au lieu d'écraser : chaque relecture duplique.

```python
# Exemple 1 : les jours à relire
from datetime import date, timedelta

def a_relire(jour, n=3):
    return [jour - timedelta(days=i)
            for i in range(n)]

j = a_relire(date(2026, 10, 23))
j[-1]  # → date(2026, 10, 21)
```

```python
# Exemple 2 : une annonce arrivée en retard
source = {"2026-10-21": ["A1", "A9"],
          "2026-10-22": ["A2"]}  # A9 tardive
lake = {"2026-10-21": ["A1"]}    # lu le 22
for j in ("2026-10-21", "2026-10-22"):
    lake[j] = list(source[j])    # écrase
lake["2026-10-21"]  # → ["A1", "A9"]
```

- Quiz : Run quotidien avec un lookback de 3 jours : combien de fois chaque jour est-il ingéré au total ?
- [ ] 1
- [ ] 2
- [x] 3
- [ ] 4
- Réponse : 3 : un jour est lu par son propre run puis par les deux suivants ; le coût d'ingestion est multiplié par N.

## 25. J-1 : dans le fuseau de la source
- Sous-thème : planification
- Niveau : 2
- Source : data-platform · S1-07
- Définition : La veille se calcule dans le fuseau où la source découpe ses journées (Paris pour le BODACC), pas dans celui du serveur (UTC sur Lambda).
- Contexte : Entre minuit et 2 h à Paris (1 h l'hiver), la date UTC est encore celle de la veille : J-1 calculé en UTC vise alors J-2 à Paris, et J-1 n'est pas ingéré par ce run. Invisible avec un cron à 07:00 UTC, le bug apparaît dès qu'on avance le run ou qu'on relance juste après minuit. Calculer en heure de la source supprime la classe de bug, quel que soit l'horaire.
- Usage : ✅ J-1 = `now.astimezone(fuseau_source).date() - 1 jour` · ❌ J-1 calculé dans le fuseau du serveur, ou en UTC « par défaut ».

```python
# Exemple 1 : J-1 à Paris, run à 00:30
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
def veille(now, tz):
    return now.astimezone(tz).date() - timedelta(1)
run = datetime(2026, 10, 25, 0, 30, tzinfo=P)
str(veille(run, P))             # → "2026-10-24"
str(veille(run, timezone.utc))  # → "2026-10-23"
```

- Quiz : Run le 2026-11-03 à 00:30 heure de Paris : quel J-1 donne un calcul en UTC ?
- [ ] Le 2 novembre
- [x] Le 1er novembre
- [ ] Le 3 novembre
- [ ] Le 31 octobre
- Réponse : le 1er novembre : 00:30 à Paris en hiver = 23:30 UTC le 2, donc J-1 UTC = le 1er ; à Paris, J-1 = le 2.

## 26. journée vide : distinguer vide et absente
- Sous-thème : fiabilité
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Une journée sans publication (dimanche) s'écrit en partition vide avec un manifest à 0 : « vide » se distingue de « non traitée ».
- Contexte : Le BODACC ne paraît pas le dimanche : le run du lundi vise une journée à 0 annonce, ce n'est pas une erreur. Si le job n'écrit rien, l'aval ne sait pas si la journée est vide ou si le run a échoué, et un contrôle de complétude alerte à tort. Écrire le manifest (`count: 0`) rend l'absence d'annonces explicite, datée et vérifiable.
- Usage : ✅ toujours écrire le manifest, même à 0 ligne · ❌ lever une erreur sur 0 annonce, ou ne rien écrire.

```python
# Exemple 1 : 0 annonce, manifest écrit
lake = {}
def ecrire(jour, annonces):
    lake[f"dt={jour}/manifest"] = {
        "count": len(annonces)}
ecrire("2026-10-25", [])   # dimanche
lake["dt=2026-10-25/manifest"]
# → {"count": 0}
"dt=2026-10-24/manifest" in lake
# → False  (pas traitée)
```

- Quiz : Le contrôle aval alerte sur « partition absente », et le job n'écrit rien quand il n'y a aucune annonce. Que se passe-t-il ?
- [ ] Rien : 0 annonce est normal
- [x] Une fausse alerte chaque lundi
- [ ] Le job échoue chaque dimanche
- [ ] Le lundi est ingéré deux fois
- Réponse : une fausse alerte chaque lundi : le run du lundi vise dimanche, n'écrit rien, et l'aval prend le vide pour une panne.

## 27. horloge : lue une seule fois par run
- Sous-thème : planification
- Niveau : 2
- Source : data-platform · S1-07
- Définition : L'heure courante se lit une seule fois, à l'entrée du run ; la date logique qui en découle est passée à toutes les étapes.
- Contexte : Deux lectures de l'horloge dans un même run peuvent tomber de part et d'autre de minuit : le préfixe S3 dit le 24, le manifest le 25. Lire l'heure une fois (`resolve_day` au début), puis passer `day` en paramètre rend le run cohérent et testable : un seul instant à injecter. C'est la date logique d'Airflow, appliquée à l'intérieur du job.
- Usage : ✅ `day` calculé en tête du handler, passé partout · ❌ `datetime.now()` ou `date.today()` appelés dans plusieurs fonctions du même run.

```python
# Exemple 1 : deux lectures, deux jours
from datetime import date
horloge = iter([date(2026, 10, 24),
                date(2026, 10, 25)])
lire = lambda: next(horloge)
prefixe = f"dt={lire()}"
manifest = f"dt={lire()}"
prefixe == manifest   # → False
```

- Quiz : Un run démarre à 23:59, dure 3 min et relit `date.today()` pour écrire le manifest : où va le manifest ?
- [ ] Dans la partition du jour de démarrage
- [x] Dans la partition du lendemain
- [ ] Dans les deux partitions
- [ ] Nulle part : erreur
- Réponse : dans celle du lendemain : la seconde lecture tombe après minuit ; données et manifest sont séparés.

## 28. événement : ignorer les clés inconnues
- Sous-thème : schéma
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le handler ne lit que les clés qu'il connaît dans l'événement et ignore les autres : l'appelant peut en ajouter sans casser le job.
- Contexte : Step Functions, EventBridge ou un rejeu manuel envoient des événements de formes différentes (`source`, `execution_id`…). Lire `event.get("date")` et ignorer le reste (lecteur tolérant) découple le job de son déclencheur. À l'inverse, la valeur d'une clé connue se valide strictement : une date fausse lève. Tolérant sur la forme, strict sur le contenu.
- Usage : ✅ `event.get("clé")` pour les options, validation stricte des valeurs · ❌ exiger que l'événement ne contienne que les clés prévues.

```python
# Exemple 1 : la clé en plus est ignorée
from datetime import date
def jour(event):
    return date.fromisoformat(event["date"])
event = {"date": "2026-10-20",
         "source": "step-functions"}
jour(event)   # → date(2026, 10, 20)
```

- Quiz : Un rejeu envoie `{"Date": "2026-10-20"}` (majuscule) à `resolve_day` : que se passe-t-il ?
- [ ] Rejeu du 20 : la casse est ignorée
- [ ] `KeyError`
- [x] J-1 par défaut, sans erreur
- [ ] `ValueError`
- Réponse : J-1 par défaut : `event.get("date")` vaut `None` et la clé `Date` est ignorée ; le rejeu traite silencieusement un autre jour.

## 29. ordre non documenté : le fixer à la source
- Sous-thème : idempotence
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Un ordre de réponse stable mais non documenté est un comportement observé, pas un contrat : on le demande explicitement (`order_by`, `ORDER BY`).
- Contexte : Mesuré sur deux journées, l'export BODACC rendait toujours le même ordre : celui, interne, du serveur. Une réindexation peut le changer sans prévenir, et le rejeu donnerait un autre sha256 pour les mêmes annonces. Demander l'ordre dans la requête (`order_by=id` sur l'export, `ORDER BY id` en SQL) en fait une garantie, protégée par un test qui vérifie le paramètre envoyé.
- Usage : ✅ export ou requête dont le résultat est haché, comparé ou paginé · ❌ compter sur un `SELECT` sans `ORDER BY` : aucun moteur SQL ne garantit son ordre.

```python
# Exemple 1 : l'ordre dans la requête
base = {"where": "dateparution"
                 "=date'2026-10-20'"}
params = {**base, "order_by": "id"}
params["order_by"]   # → "id"
"order_by" in base   # → False
```

```python
# Exemple 2 : un serveur qui réindexe
import random

DATA = ["A3", "A1", "A2"]

def export(order_by=None):
    rows = DATA[:]
    random.shuffle(rows)  # ordre interne
    if order_by:
        return sorted(rows)
    return rows

[export("id") for _ in range(3)]
# → [["A1", "A2", "A3"]] * 3
```

- Quiz : Un `SELECT id FROM annonces` sans `ORDER BY` a rendu 100 fois le même ordre. Que garantit SQL pour la 101e ?
- [ ] L'ordre d'insertion des lignes
- [ ] L'ordre de la clé primaire
- [x] Rien : l'ordre n'est pas défini
- [ ] Le même ordre si la table n'a pas changé
- Réponse : Rien : sans `ORDER BY`, le moteur rend les lignes selon son plan (index, parallélisme, compaction) ; 100 mesures ne font pas un contrat.

## 30. mesure : sur la vraie source, pas la fixture
- Sous-thème : fiabilité
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Une propriété de la source (ordre stable, ids uniques, volume) se mesure sur une vraie journée complète, jamais sur la fixture des tests.
- Contexte : La fixture (25 lignes figées dans le dépôt) est stable par construction : la relire donne forcément le même ordre, elle ne dit rien du serveur. On mesure avec un script jetable hors dépôt, sur une journée passée : deux lectures, comparaison des ids et du hash, doublons, taille, durée. BODACC du 2026-10-20 : 32 373 annonces, 55,6 Mo, ordre stable mais non trié.
- Usage : ✅ avant de bâtir sur une hypothèse (ordre, unicité, volume), après un changement côté source · ❌ conclure d'un test vert sur fixture qu'un comportement du serveur est garanti.

```python
# Exemple 1 : comparer deux lectures
lecture1 = ["A3", "A1", "A2", "A2"]
lecture2 = ["A3", "A1", "A2", "A2"]
lecture1 == lecture2       # → True
len(lecture1) == len(set(lecture1))
# → False  (doublon A2)
```

```python
# Exemple 2 : un rapport de mesure
def mesure(ids1, ids2, attendu):
    return {
        "ordre": ids1 == ids2,
        "doublons": len(ids1) - len(set(ids1)),
        "complet": len(ids1) == attendu,
        "trie": ids1 == sorted(ids1),
    }

m = mesure(["A2", "A1"], ["A2", "A1"], 2)
m["ordre"], m["trie"]   # → (True, False)
```

- Quiz : Que vaut `len(ids) - len(set(ids))` pour `ids = ["A1", "A2", "A2", "A2"]` ?
- [ ] `1`
- [ ] `3`
- [x] `2`
- [ ] `0`
- Réponse : `2` : 4 lignes pour 2 ids distincts ; la mesure compte les lignes en trop, pas les ids en double (il n'y en a qu'un).

## 31. identité : le hash du brut, pas du gzip
- Sous-thème : idempotence
- Niveau : 2
- Source : data-platform · S1-07
- Définition : L'empreinte d'une partition se calcule sur le JSONL non compressé : changer de niveau ou d'outil de compression ne change pas l'identité de la donnée.
- Contexte : Le même contenu compressé au niveau 1, 6 ou 9 donne trois `.gz` différents, donc trois sha256, pour une donnée identique. Hacher les octets bruts au fil de l'écriture (`digest.update(line)` à côté de `gz.write(line)`) donne une identité stable, rangée dans le manifest avec le nombre de lignes et les deux tailles. Le hash du `.gz` reste utile pour vérifier un transfert, pas pour dire « même donnée ».
- Usage : ✅ manifest de partition, détection d'un vrai changement au rejeu · ❌ comparer le sha256 du `.gz` ou l'ETag S3 pour savoir si la donnée a changé.

```python
# Exemple 1 : deux niveaux, deux .gz
import gzip
raw = b'{"id":"A1"}\n' * 100
g1 = gzip.compress(raw, 1, mtime=0)
g9 = gzip.compress(raw, 9, mtime=0)
g1 == g9                       # → False
gzip.decompress(g1) == raw     # → True
```

```python
# Exemple 2 : hacher pendant l'écriture
import gzip, hashlib, io

lignes = [b'{"id":"A1"}\n', b'{"id":"A2"}\n']
digest = hashlib.sha256()
buf = io.BytesIO()
with gzip.GzipFile(fileobj=buf, mode="wb",
                   mtime=0) as gz:
    for ligne in lignes:
        gz.write(ligne)
        digest.update(ligne)  # le brut
brut = gzip.decompress(buf.getvalue())
digest.digest() == hashlib.sha256(brut).digest()
# → True
```

- Quiz : Le manifest garde le sha256 du `.gz`. On passe le niveau de 6 à 9 et on rejoue un jour inchangé : que constate-t-on ?
- [ ] Le même hash qu'avant
- [x] Un autre hash : faux changement
- [ ] Une erreur de décompression
- [ ] Un autre hash : donnée corrompue
- Réponse : Un autre hash : faux changement : les octets compressés dépendent du niveau ; seule l'empreinte du brut est stable.

## 32. test d'idempotence : comparer les octets
- Sous-thème : idempotence
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le test d'idempotence d'un writer écrit deux fois le même contenu, sous deux noms, et compare les octets des fichiers, pas leur contenu décodé.
- Contexte : Comparer le contenu décompressé passe même si l'en-tête gzip contient l'heure ou le nom du fichier : c'est justement le cas piège. Deux noms différents (`tmpa1b2c3`, `part-0001.jsonl.gz`) reproduisent la Lambda, où `tempfile` invente un nom à chaque invocation. Compléter par « ordre des clés sans effet » et « ordre des lignes significatif ».
- Usage : ✅ tout writer de partition rejouable (gzip, Parquet, CSV) · ❌ écrire deux fois au même chemin dans la même seconde : le test passe même avec l'heure et le nom dans l'en-tête.

```python
# Exemple 1 : le contenu ne suffit pas
import gzip
run1 = gzip.compress(b"A1\n", mtime=100)
run2 = gzip.compress(b"A1\n", mtime=200)
gzip.decompress(run1) == gzip.decompress(run2)
# → True  (test trop faible)
run1 == run2   # → False (le vrai test)
```

```python
# Exemple 2 : deux noms, comme en Lambda
import gzip, tempfile
from pathlib import Path

def ecrire(p, filename=None):
    with (p.open("wb") as f,
          gzip.GzipFile(filename, "wb",
                        fileobj=f,
                        mtime=0) as gz):
        gz.write(b"A1\n")
    return p.read_bytes()

d = Path(tempfile.mkdtemp())
ecrire(d / "tmpa1b2c3") == ecrire(d / "p.gz")
# → False  (nom dans l'en-tête)
ecrire(d / "tmpa1", "") == ecrire(d / "p.gz", "")
# → True
```

- Quiz : Exemple 2 sans `filename=""`, mais les deux écritures vont au **même** chemin `p.gz` : que vaut la comparaison ?
- [ ] `False`
- [ ] `ValueError`
- [x] `True`
- Réponse : `True` : même nom, même en-tête ; le test passe alors qu'en Lambda le nom temporaire change à chaque invocation.

## 33. manifest : comparer l'empreinte au rejeu
- Sous-thème : rejeux
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Au rejeu, comparer `count` et sha256 du nouveau fichier à ceux du manifest existant dit si la source a changé, sans relire l'ancien fichier.
- Contexte : Le manifest garde ce que le writer a mesuré : nombre de lignes, sha256 du brut, tailles. Même sha256 : rejeu neutre, rien à propager. sha256 différent alors que l'ordre et la sérialisation sont fixés : la source a vraiment publié autre chose (rectificatif tardif), à journaliser. Sans ordre fixé, un hash différent ne prouve rien.
- Usage : ✅ rejeu, backfill, alerte « journée modifiée après coup » · ❌ comparer seulement `count` : une annonce corrigée garde le même nombre de lignes.

```python
# Exemple 1 : rejeu neutre ou changement
avant = {"count": 3, "sha256": "bbdf3f0a"}
rejeu = {"count": 3, "sha256": "bbdf3f0a"}
rejeu == avant     # → True : neutre
corr = {"count": 3, "sha256": "71c2e9d4"}
corr == avant      # → False : à journaliser
corr["count"] == avant["count"]  # → True
```

```python
# Exemple 2 : une annonce corrigée
import hashlib, json

def stats(rows):
    raw = "".join(json.dumps(r, sort_keys=True)
                  + "\n" for r in rows).encode()
    return len(rows), hashlib.sha256(raw).digest()

v1 = [{"id": "A1", "nature": "Vente"}]
v2 = [{"id": "A1", "nature": "Cession"}]
stats(v1)[0] == stats(v2)[0]   # → True
stats(v1)[1] == stats(v2)[1]   # → False
```

- Quiz : Ordre de lecture non fixé : un rejeu donne un autre sha256 pour le même `count`. Que peut-on conclure ?
- [ ] Une annonce a été corrigée
- [x] Rien de sûr : ordre ou contenu
- [ ] Le fichier est corrompu
- [ ] Rien n'a changé
- Réponse : Rien de sûr : ordre ou contenu : un simple changement d'ordre suffit à changer le hash, il ne distingue plus une correction d'une réindexation.

## 34. S3 : pas de transaction entre deux objets
- Sous-thème : fiabilité
- Niveau : 2
- Source : data-platform · S1-07
- Définition : S3 écrit chaque objet en entier ou pas du tout, mais jamais deux ensemble : publier données et manifest, c'est deux requêtes séparées.
- Contexte : Entre le `PUT` du fichier et celui du manifest, un lecteur peut lister la partition. L'ordre choisit l'état intermédiaire visible : données sans manifest (non publiée, sans danger) plutôt que manifest sans données (publiée, illisible). Il n'y a pas de `rollback` : si le second `PUT` échoue, le premier reste. Équivalent TS : deux `fetch` successifs, pas une transaction de base.
- Usage : ✅ ordre fixe données puis marqueur, et rejeu qui réécrit les deux · ❌ croire qu'un `try/except` annule le premier `PUT` : il faut supprimer ou rejouer.

```python
# Exemple 1 : chaque PUT est entier
s3 = {"part": b"ancien"}
def put(cle, data):
    s3[cle] = data       # tout ou rien
put("part", b"nouveau")
s3["part"]   # → b"nouveau", jamais un mélange
```

```python
# Exemple 2 : l'ordre est le contrat
ordre = []
def publish(put):
    put("part-0001.jsonl.gz")
    put("_MANIFEST.json")      # en dernier
publish(ordre.append)
ordre[-1]   # → "_MANIFEST.json"
```

- Quiz : Le `put_object` du manifest échoue après un `upload_file` réussi : que contient S3 ?
- [ ] Rien : S3 annule le premier envoi
- [x] Le fichier de données seul
- [ ] Le manifest seul
- [ ] Un fichier à moitié écrit
- Réponse : le fichier seul : le premier `PUT` est acquis, aucune transaction ne le défait ; la partition reste non publiée jusqu'au rejeu.

## 35. fetched_at : le seul champ qui change
- Sous-thème : rejeux
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Au rejeu d'une journée inchangée, seul `fetched_at` (l'heure de collecte) change dans le manifest : « même résultat » se juge sur les données.
- Contexte : Le manifest mêle deux natures : des faits sur les données (`count`, `sha256`, tailles), stables, et un fait sur le run (`fetched_at`), qui change à chaque exécution. Exiger un manifest identique octet pour octet obligerait à figer l'heure et perdrait l'info « quand a-t-on collecté ». Le test de rejeu compare le `sha256` ou les octets du part, ou le manifest privé de `fetched_at` ; jamais l'ETag (nouveau à chaque PUT en SSE-KMS), `LastModified` ni `VersionId`.
- Usage : ✅ comparer `sha256` et `count`, ou le manifest sans les champs de run · ❌ `manifest_1 == manifest_2` comme test d'idempotence : faux négatif à chaque run.

```python
# Exemple 1 : comparer sans l'heure
m1 = {"count": 2, "sha256": "bbdf3f0a",
      "fetched_at": "2026-10-21T05:00:12+00:00"}
m2 = {**m1, "fetched_at": "2026-10-22T05:00:09+00:00"}
m1 == m2   # → False
def stable(m):
    return {k: v for k, v in m.items()
            if k != "fetched_at"}
stable(m1) == stable(m2)   # → True : même résultat
```

- Quiz : Rejeu d'une journée inchangée, mais le client BODACC est passé de 0.1.0 à 0.2.0 : quels champs du manifest changent ?
- [ ] `fetched_at` seul
- [x] `fetched_at` et `bodacc_client_version`
- [ ] Tous : nouvelle version, nouveau fichier
- [ ] Aucun
- Réponse : `fetched_at` et `bodacc_client_version` : « seul `fetched_at` change » vaut à code égal ; si le writer n'a pas changé, `sha256` et `count` restent identiques.

## 36. lecteur : partir du manifest
- Sous-thème : flux
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le lecteur d'une partition lit d'abord le manifest, puis le fichier qu'il désigne (`part`), au lieu de lister le préfixe et de tout prendre.
- Contexte : Lister ramasse aussi ce qui ne fait pas partie de la publication : un part d'un run interrompu, un fichier temporaire, un ancien nom. Le manifest est la liste fermée des fichiers valides, comme le journal d'une table Delta ou Iceberg, en plus simple. Il donne aussi `count` et `sha256` pour contrôler ce qu'on vient de lire.
- Usage : ✅ job aval, contrôle qualité, chargement d'une partition par notre code · ❌ `list_objects_v2` puis lire tout ce qui finit par `.gz` : un résidu de run suffit à doubler des lignes.

```python
# Exemple 1 : un résidu traîne
s3 = {
  "date=2026-10-20/part-0001.jsonl.gz": 2,
  "date=2026-10-20/part-0002.jsonl.gz": 2,
  "date=2026-10-20/_MANIFEST.json":
      {"part": "date=2026-10-20/part-0001.jsonl.gz"}}
gz = [k for k in s3 if k.endswith(".gz")]
sum(s3[k] for k in gz)       # → 4 : doublé
m = s3["date=2026-10-20/_MANIFEST.json"]
s3[m["part"]]                # → 2 : le bon
```

- Quiz : Même partition (part-0001 désigné, résidu part-0002) : combien de parts Athena lit-il en interrogeant ce jour ?
- [ ] 1 : le manifest fait foi
- [x] 2 : tous les objets non techniques
- [ ] 3 : les deux parts et le manifest
- [ ] Aucun : partition incohérente
- Réponse : 2 : Athena ignore `_MANIFEST.json` et lit tout le reste du préfixe ; le manifest n'est une règle que pour notre code, d'où le nettoyage des résidus.

## 37. un seul fichier : le manifest sert encore
- Sous-thème : fiabilité
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Avec un seul fichier, l'atomicité de S3 évite déjà la lecture partielle ; le manifest sert alors à décrire, vérifier et préparer plusieurs parts.
- Contexte : Un `PUT`, ou un multipart complété, n'est visible qu'entier : pas de demi-fichier, et un `_SUCCESS` vide n'apporterait rien. Mais le manifest donne `count` et `sha256` sans relire, la version du code, et reste le signal « fini » le jour où la journée est découpée en `part-0001`, `part-0002`. Ajouter ce contrat plus tard obligerait tous les lecteurs à changer.
- Usage : ✅ manifest dès le premier part, même seul · ❌ `_SUCCESS` vide sur une partition d'un seul objet : il ne protège de rien.

```python
# Exemple 1 : le jour où il y a 2 parts
manifest = {"parts": ["part-0001.jsonl.gz",
                      "part-0002.jsonl.gz"]}
present = {"part-0001.jsonl.gz"}

def complete(m, present):
    return set(m["parts"]) <= present

complete(manifest, present)   # → False
```

- Quiz : Un `upload_file` multipart en 3 parts est coupé après la 2ᵉ : que montre `list_objects_v2` sur la clé ?
- [ ] Un objet partiel, 2 parts sur 3
- [x] Rien : l'objet n'existe pas
- [ ] Les 2 parts, comme deux objets
- [ ] Un objet vide de 0 octet
- Réponse : rien : un multipart n'existe qu'après `CompleteMultipartUpload` ; les parts envoyées restent invisibles (et facturées) jusqu'à leur purge.

## 38. rejeu : réparer par les mêmes clés
- Sous-thème : rejeux
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Un run coupé entre fichier et manifest laisse la partition non publiée ; le rejeu réécrit les deux aux mêmes clés et la répare.
- Contexte : Aucun nettoyage spécial n'est nécessaire : le part orphelin est écrasé par le nouveau, le manifest arrive ensuite. Cela ne marche que parce que les clés sont fixes (`part-0001.jsonl.gz`, `_MANIFEST.json`), dérivées du jour seulement. Avec un nom unique par run, chaque échec laisserait un résidu que les moteurs liraient.
- Usage : ✅ clés dérivées des entrées (source, jour, numéro de part), rejeu comme seule procédure de reprise · ❌ `uuid` ou heure dans le nom du part : un résidu par échec.

```python
# Exemple 1 : échec, puis rejeu
s3 = {}
def publish(echec=False):
    s3["date=2026-10-20/part-0001.jsonl.gz"] = 2
    if echec:
        raise ConnectionError("coupure")
    s3["date=2026-10-20/_MANIFEST.json"] = 2
try:
    publish(echec=True)
except ConnectionError:
    pass
publish()
len(s3)   # → 2 : rien en trop
```

- Quiz : Le part s'écrit sous `part-<uuid>.jsonl.gz` ; un run échoue avant le manifest, le rejeu réussit : combien de parts sous le préfixe ?
- [ ] 1 : le rejeu remplace l'ancien
- [x] 2 : l'orphelin reste
- [ ] 0 : S3 purge les orphelins
- [ ] 1 : l'échec n'a rien écrit
- Réponse : 2 : l'uuid change, le premier part n'est jamais écrasé ; notre lecteur l'ignore grâce au manifest, mais Athena le lira.

## 39. lire tout, puis publier : rien de partiel en cas de coupure
- Sous-thème : fiabilité
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le run lit toute la journée vers un fichier local, puis publie : une coupure pendant la lecture ne laisse rien dans le data lake.
- Contexte : Envoyer au fil de l'eau (un objet par lot, un multipart ouvert pendant la lecture) expose une partition à moitié écrite dès que la source coupe. Écrire d'abord dans `/tmp` (512 Mo, un `.gz` de 4,4 Mo pour une journée BODACC) puis publier données et manifest découple les deux risques : la lecture peut échouer sans effet, la publication est courte. L'exception remonte, l'orchestrateur rejoue.
- Usage : ✅ journée qui tient sur le disque local : lecture complète, puis publication · ❌ volume qui dépasse le disque : écrire des parts numérotées et ne publier le manifest qu'à la fin.

```python
# Exemple 1 : la coupure n'atteint pas S3
lake = {}
def flux():
    yield "A202602011"
    raise ConnectionError("coupé")
def run(jour):
    local = list(flux())  # lecture complète
    lake[jour] = local    # puis publication
try:
    run("2026-10-20")
except ConnectionError:
    pass
lake  # → {}
```

```python
# Exemple 2 : publier au fil de l'eau
lake = {}
def flux():
    yield "A202602011"
    raise ConnectionError("coupé")
def run(jour):
    for a in flux():
        lake.setdefault(jour, []).append(a)
try:
    run("2026-10-20")
except ConnectionError:
    pass
lake  # → {"2026-10-20": ["A202602011"]}
```

- Quiz : Exemple 2, puis un rejeu qui réussit avec les deux annonces : que contient `lake["2026-10-20"]` ?
- [ ] `["A202602011", "A202602012"]`
- [x] `["A202602011", "A202602011", "A202602012"]`
- [ ] `["A202602012"]`
- Réponse : la première annonce en double : la publication partielle reste et le rejeu ajoute ; il faudrait en plus écraser la partition.

## 40. rejeu raté : la partition précédente reste valide
- Sous-thème : rejeux
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Un rejeu qui échoue pendant la lecture ne touche ni fichier ni manifest publiés : la partition reste celle du dernier run réussi.
- Contexte : C'est le test « coupure au rejeu » : un premier run publie, la source coupe au second, et l'`ETag` du part est inchangé. Possible parce que rien n'est supprimé ni écrasé avant la fin de la lecture. Supprimer la partition en début de run (« on repart propre ») ferait l'inverse : un rejeu raté efface une journée valide.
- Usage : ✅ écraser aux mêmes clés, en dernier, une fois la nouvelle version prête · ❌ vider le préfixe avant de relire la source.

```python
# Exemple 1 : la version d'avant survit
lake = {"2026-10-20": ("A1", "A2")}
def flux():
    yield "A1"
    raise ConnectionError("coupé")
def rejeu(jour):
    nouveau = tuple(flux())  # lit d'abord
    lake[jour] = nouveau
try:
    rejeu("2026-10-20")
except ConnectionError:
    pass
lake["2026-10-20"]  # → ("A1", "A2")
```

- Quiz : Même rejeu, mais il commence par `del lake[jour]` pour « repartir propre » : que vaut `lake` après la coupure ?
- [ ] `{"2026-10-20": ("A1", "A2")}`
- [ ] `{"2026-10-20": ("A1",)}`
- [x] `{}`
- Réponse : `{}` : la suppression a eu lieu, la réécriture jamais ; une journée valide a disparu à cause d'un rejeu raté.

## 41. rejeu réel : prouver avec les versions S3
- Sous-thème : idempotence
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Sur AWS, l'idempotence d'un rejeu se prouve en téléchargeant les deux versions du fichier et en comparant leurs octets.
- Contexte : Le test unitaire prouve le writer ; le rejeu réel prouve toute la chaîne : ordre renvoyé par l'API, runtime Lambda, upload. Le bucket versionné garde l'ancienne version : `list-object-versions`, deux `get-object --version-id`, puis `cmp` ou `shasum`. ETag, `LastModified` et `VersionId` changent forcément à chaque écriture : ils ne prouvent rien.
- Usage : ✅ critère de validation d'une Lambda d'ingestion, contrôle après un changement de dépendance · ❌ conclure de l'ETag ou du `count` seul : comparer les octets ou le sha256.

```bash
# Exemple 1 : deux versions, mêmes octets
aws s3api list-object-versions \
  --bucket "$B" --prefix "$K" \
  --query 'Versions[].VersionId' \
  --output text
# → f9.dWsBx…  wNaHsrEO…
shasum -a 256 run.gz rejeu.gz
# → a7530862…  run.gz
#   a7530862…  rejeu.gz
```

- Quiz : Le bucket n'est pas versionné. Comment prouver le rejeu ?
- [ ] Comparer l'ETag avant et après
- [x] Hasher l'objet avant le rejeu, puis après
- [ ] Comparer `LastModified`
- [ ] Impossible sans versioning
- Réponse : hasher avant puis après : sans versions, l'ancien contenu disparaît à l'écrasement ; son empreinte doit être prise avant.

## 42. retry en flux : jamais après le premier yield
- Sous-thème : fiabilité
- Niveau : 3
- Source : data-platform · S1-06
- Définition : Sur un flux sans point de reprise, on ne réessaie que l'ouverture ; une coupure après la première ligne rendue doit lever, pas relancer.
- Contexte : Relancer un export après 10 000 annonces émises les rend une seconde fois : doublons silencieux en aval. `fetch_day` garde un drapeau `started` : erreur avant le premier `yield`, backoff puis nouvel essai ; après, `BodaccError`. C'est acceptable parce que l'appelant est idempotent : la Lambda rejoue la journée entière et écrase la même clé S3. Une pagination keyset, elle, réessaie page par page sans doublon.
- Usage : ✅ export streamé, gros téléchargement sans reprise (`Range`) · ❌ pagination par curseur : chaque page se réessaie seule ; appelant qui ajoute au lieu d'écraser : lever ne suffit pas.

```python
# Exemple 1 : relancer après un yield
def flux(essai):         # coupé au 1er
    yield "A1"
    if essai == 0:
        raise ConnectionError
    yield "A2"

def naif():
    for essai in range(2):
        try:
            yield from flux(essai)
            return
        except ConnectionError:
            pass         # on relance tout

list(naif())  # → ["A1", "A1", "A2"]
```

```python
# Exemple 2 : le drapeau started
def flux(essai):
    yield "A1"
    if essai == 0:
        raise ConnectionError
    yield "A2"

def sur():
    for essai in range(2):
        started = False
        try:
            for a in flux(essai):
                started = True
                yield a
            return
        except ConnectionError:
            if started:
                raise RuntimeError("coupé")

list(sur())  # ❌ RuntimeError
```

- Quiz : Exemple 2 : si `flux` levait au 1er essai **avant** `yield "A1"`, que vaudrait `list(sur())` ?
- [x] `["A1", "A2"]`
- [ ] `RuntimeError`
- [ ] `["A1", "A1", "A2"]`
- [ ] `[]`
- Réponse : `["A1", "A2"]` : rien n'a encore été rendu (`started` faux), le nouvel essai est sans risque de doublon.

## 43. empreinte : détecter un changement
- Sous-thème : idempotence
- Niveau : 3
- Définition : Un hash SHA-256 du contenu sérialisé détecte qu'un enregistrement a changé entre deux ingestions, sans comparer champ par champ.
- Contexte : On stocke l'empreinte de chaque annonce avec son id. Au run suivant, même id et même empreinte : rien à réécrire ; empreinte différente : rectificatif à propager. La sérialisation doit être canonique : `sort_keys=True` fixe l'ordre des clés, sinon deux dicts égaux donnent deux chaînes, donc deux hash. Tronquer à quelques caractères suffit pour comparer, pas pour un identifiant global.
- Usage : ✅ ingestion incrémentale, détection de rectificatifs, cache · ❌ comparer des objets avec des `float` ou des dates non normalisés : sérialiser d'abord en types stables.

```python
# Exemple 1 : même contenu, même empreinte
import hashlib, json

def empreinte(doc):
    s = json.dumps(doc, sort_keys=True)
    return hashlib.sha256(
        s.encode()).hexdigest()[:8]

a = {"siren": "483609327", "v": 1}
b = {"v": 1, "siren": "483609327"}
empreinte(a) == empreinte(b)  # → True
```

```python
# Exemple 2 : repérer les annonces modifiées
import hashlib, json

def emp(d):
    s = json.dumps(d, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()

avant = {"A1": emp({"v": 1}),
         "A2": emp({"v": 1})}
apres = {"A1": {"v": 1}, "A2": {"v": 2}}
[i for i, d in apres.items()
 if emp(d) != avant[i]]  # → ["A2"]
```

- Quiz : Dans l'exemple 1, que vaut `empreinte(a) == empreinte(b)` si on retire `sort_keys=True` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : `dumps` suit l'ordre d'insertion du dict ; même contenu, autre chaîne, autre hash.

## 44. annulation : corriger l'annonce visée
- Sous-thème : idempotence
- Niveau : 3
- Source : data-platform · S1-05
- Définition : Une annulation ou un rectificatif est une nouvelle ligne, avec son propre id, qui désigne une ligne antérieure : on l'applique à celle-ci.
- Contexte : Un upsert sur `id` absorbe les rejeux, mais une annulation a un autre `id` : l'insérer seule laisse l'annonce visée intacte, et la table garde un événement qui n'a pas eu lieu (une radiation annulée neuf mois plus tard). BODACC donne la cible dans `parutionavisprecedent` : lettre du bulletin, `numeroParution`, `numeroAnnonce`. Annulation : marquer ou supprimer la cible ; rectificatif : la remplacer.
- Usage : ✅ toute source qui publie des corrections (journaux légaux, CDC, événements compensatoires) · ❌ traiter chaque ligne comme un fait nouveau : la table garde des fantômes.

```python
# Exemple 1 : agir sur la ligne visée
table = {"B20260002157": "radiation"}

def appliquer(t, a):
    if a["typeavis"] == "annulation":
        t.pop(a["vise"], None)  # la cible
    else:
        t[a["id"]] = a["famille"]

appliquer(table, {"id": "B20260201284",
    "typeavis": "annulation",
    "vise": "B20260002157"})
table   # → {}
```

```python
# Exemple 2 : reconstruire l'id visé
import json

p = json.loads(
    '{"nomPublication": "BODACC B",'
    ' "numeroParution": "20260002",'
    ' "numeroAnnonce": "157"}')
(p["nomPublication"][-1]
 + p["numeroParution"]
 + p["numeroAnnonce"])
# → "B20260002157"
```

- Quiz : Avec un upsert naïf sur `id` à la place d'`appliquer`, combien de lignes compte `table` après l'exemple 1 ?
- [ ] 0
- [ ] 1
- [x] 2
- Réponse : 2 : l'annulation `B20260201284` s'ajoute à côté de la radiation `B20260002157`, qui reste en table comme si elle avait eu lieu.

## 45. checkpoint : reprendre au dernier lot écrit
- Sous-thème : rejeux
- Niveau : 3
- Définition : Un job long écrit par lots numérotés et note le dernier lot validé : après un crash, il repart du suivant sans tout refaire.
- Contexte : Un backfill de 300 jours ne tient pas dans une Lambda (15 min). Découpé en lots déterministes (un jour, ou `part-0007` toutes les 10 000 lignes), chaque lot est idempotent ; le checkpoint (S3, DynamoDB) n'avance qu'après l'écriture du lot. C'est le watermark, au grain du lot. Le découpage doit être identique d'un run à l'autre, et la source doit savoir resauter au bon endroit (keyset, `Range`), sinon on relit pour rien.
- Usage : ✅ backfills longs, gros fichiers, boucles Step Functions · ❌ lots de taille variable selon le run : le lot 7 du rejeu n'est plus le lot 7 d'avant.

```python
# Exemple 1 : sauter les lots déjà écrits
from itertools import batched

lignes = [f"A{i}" for i in range(10)]
ecrits, checkpoint = {}, 1  # lots 0 et 1
for n, lot in enumerate(batched(lignes, 4)):
    if n <= checkpoint:
        continue            # déjà écrit
    ecrits[f"part-{n:04d}"] = lot
    checkpoint = n          # après l'écriture
list(ecrits), checkpoint
# → (["part-0002"], 2)
```

- Quiz : Le checkpoint est avancé avant l'écriture, et le job plante pendant le lot 2. Au redémarrage ?
- [ ] Le lot 2 est refait
- [ ] Tout est refait depuis le lot 0
- [ ] Le lot 2 est écrit deux fois
- [x] Le lot 2 est sauté, jamais écrit
- Réponse : le lot 2 est sauté : le checkpoint dit 2 alors que rien n'est écrit ; le trou est silencieux.

## 46. deux fuseaux, deux rôles
- Sous-thème : planification
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Le jour métier (`dt=`) se calcule en heure de la source ; les horodatages techniques (`ingested_at`) s'écrivent en UTC, avec leur décalage.
- Contexte : Le jour de partition suit le découpage de la source (Paris), l'instant d'ingestion reste absolu et comparable entre systèmes. Une annonce du 25 ingérée juste après minuit à Paris a donc un `ingested_at` daté du 24 en UTC, et c'est juste. Mélanger les deux (grouper par `ingested_at[:10]`, ou écrire `ingested_at` naïf) crée des écarts d'une ou deux heures, difficiles à voir.
- Usage : ✅ `dt=` en heure de la source, `ingested_at` en ISO UTC avec `+00:00` · ❌ grouper des volumes métier par la date UTC de l'horodatage technique.

```python
# Exemple 1 : un enregistrement, deux fuseaux
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
now = datetime(2026, 10, 25, 0, 30, tzinfo=P)
rec = {
    "dt": str(now.date()),
    "ingested_at": now.astimezone(
        timezone.utc).isoformat()}
rec["dt"]           # → "2026-10-25"
rec["ingested_at"]  # → "2026-10-24T22:30:00+00:00"
```

- Quiz : Un tableau de bord groupe par `ingested_at[:10]` : dans quel jour compte-t-il une annonce ingérée le 14 juillet à 01:30 à Paris ?
- [ ] Le 14 juillet
- [x] Le 13 juillet
- [ ] Les deux
- [ ] Aucun
- Réponse : le 13 juillet : l'été Paris est à UTC+2, il est 23:30 UTC le 13 ; grouper par `dt` (jour de la source) donne le 14.

## 47. tri : à la source, pas en mémoire
- Sous-thème : flux
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Pour un flux trié sans charger la journée en RAM, on demande le tri à la source (`order_by`) au lieu d'appeler `sorted()` dans la Lambda.
- Contexte : `sorted()` consomme tout le générateur avant de rendre la première ligne : la journée entière (59 Mo de JSON, bien plus en objets Python) passe en mémoire, le streaming est perdu. Côté serveur, le tri coûte du temps (4,5 s au lieu de 1,8 s mesurés sur le BODACC) mais la mémoire reste plate. Si la source ne sait pas trier : morceaux triés sur disque, fusionnés par `heapq.merge`.
- Usage : ✅ export volumineux lu en flux, base qui sait faire `ORDER BY` · ❌ `sorted()` ou `list()` sur le générateur d'une journée dans une Lambda à mémoire réduite.

```python
# Exemple 1 : sorted lit tout d'abord
lus = []
flux = (lus.append(i) or i
        for i in ["A3", "A1", "A2"])
sorted(flux)[0]   # → "A1"
len(lus)          # → 3 : tout est en mémoire
```

```python
# Exemple 2 : tri externe, en flux
import heapq

morceau1 = iter(["A1", "A4"])  # triés
morceau2 = iter(["A2", "A3"])  # à part
fusion = heapq.merge(morceau1, morceau2)
next(fusion)   # → "A1"
list(fusion)   # → ["A2", "A3", "A4"]
```

- Quiz : Sur le générateur d'une journée, quelle mémoire prennent `max(flux)` et `sorted(flux)` ?
- [ ] Les deux chargent tout le flux
- [ ] Les deux restent constantes
- [x] `max` : constante, `sorted` : tout le flux
- [ ] `max` : tout le flux, `sorted` : constante
- Réponse : `max` : constante, `sorted` : tout le flux : `max` ne garde que le plus grand vu, `sorted` doit stocker chaque ligne pour rendre une liste (mesuré : 0,5 Ko contre 12 Mo sur 200 000 ids).

## 48. ordre naturel ou lexical : seule la stabilité compte
- Sous-thème : idempotence
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Un serveur peut trier en ordre naturel (`A9` avant `A10`), Python en ordre lexical : seul compte que l'ordre soit identique à chaque appel.
- Contexte : Avec `order_by=id`, l'export BODACC rend `A202602011`, `A202602012`… en ordre naturel ; `ids == sorted(ids)` vaut donc `False` côté Python. Ce n'est pas un bug : l'idempotence demande un ordre déterministe, pas celui de Python. On vérifie « même ordre sur deux lectures », pas « trié comme `sorted` ». Pour reproduire l'ordre naturel : une clé qui convertit les chiffres en `int`.
- Usage : ✅ comparer deux lectures entre elles, documenter l'ordre obtenu · ❌ contrôle qui exige `ids == sorted(ids)` sur des ids alphanumériques triés par un autre système.

```python
# Exemple 1 : deux ordres possibles
ids = ["A9", "A10", "A11"]  # serveur
ids == sorted(ids)    # → False
sorted(ids)
# → ["A10", "A11", "A9"]  (lexical)
```

```python
# Exemple 2 : une clé d'ordre naturel
import re

def naturel(s):
    return [int(t) if t.isdigit() else t
            for t in re.split(r"(\d+)", s)]

ids = ["A10", "B1", "A9"]
sorted(ids, key=naturel)
# → ["A9", "A10", "B1"]
```

- Quiz : Que vaut `sorted(["A202602012", "A2026020110"])[0]` ?
- [x] `"A2026020110"`
- [ ] `"A202602012"`
- [ ] `TypeError`
- Réponse : `"A2026020110"` : la comparaison se fait caractère par caractère ; au 10e, `"1"` passe avant `"2"`, quelle que soit la longueur.

## 49. tri : départager les ex aequo
- Sous-thème : idempotence
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Trier sur une clé non unique (date) laisse les ex aequo dans l'ordre d'entrée : finir la clé par l'id rend l'ordre déterministe.
- Contexte : `ORDER BY dateparution` seul ne fixe pas l'ordre des annonces d'un même jour : le moteur les rend comme il veut, et le hash varie. En Python, `sorted` est stable : les ex aequo gardent leur ordre d'arrivée, lui-même non garanti. La règle : trier sur une clé unique, ou terminer par une colonne unique (`ORDER BY dateparution, id`). Même règle pour paginer par curseur.
- Usage : ✅ tri d'un résultat haché ou paginé, export ordonné par date · ❌ `ORDER BY` sur une colonne à doublons (date, tribunal, statut) sans colonne unique en dernier.

```python
# Exemple 1 : ex aequo = ordre d'arrivée
r1 = [("10-20", "A2"), ("10-20", "A1")]
r2 = [("10-20", "A1"), ("10-20", "A2")]
date = lambda a: a[0]
sorted(r1, key=date) == sorted(r2, key=date)
# → False
```

```python
# Exemple 2 : finir par l'id
r1 = [("10-20", "A2"), ("10-19", "B1"),
      ("10-20", "A1")]
r2 = r1[::-1]
cle = lambda a: (a[0], a[1])  # date, id
sorted(r1, key=cle) == sorted(r2, key=cle)
# → True
```

- Quiz : `ORDER BY dateparution, tribunal` : l'ordre est-il déterministe si deux annonces ont même date et même tribunal ?
- [ ] Oui : deux colonnes suffisent
- [x] Non : il faut finir par une colonne unique
- [ ] Oui : le moteur départage par clé primaire
- [ ] Non : il faut ajouter `DESC`
- Réponse : Non : il faut finir par une colonne unique : deux lignes égales sur toutes les colonnes triées restent dans un ordre libre ; `…, id` les départage.

## 50. octets reproductibles : les sources de variation
- Sous-thème : idempotence
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Rendre un fichier reproductible octet pour octet, c'est neutraliser chaque source de variation : ordre, sérialisation, en-têtes, réglages de compression.
- Contexte : Inventaire du writer BODACC : ordre des lignes (`order_by=id`), ordre des clés (`sort_keys=True`), espaces (`separators`), échappement (`ensure_ascii=False`), heure et nom dans l'en-tête gzip (`mtime=0`, `filename=""`), niveau de compression en constante. Reste hors du code la version de zlib, qui peut changer les octets compressés : d'où l'empreinte calculée sur le brut.
- Usage : ✅ revue d'un writer rejouable, check-list avant de comparer des hash · ❌ exiger des `.gz` identiques entre machines ou versions de Python : comparer l'empreinte du brut.

```python
# Exemple 1 : quatre réglages, une ligne
import json
opts = dict(ensure_ascii=False, sort_keys=True,
            separators=(",", ":"))
a = {"tribunal": "Créteil", "id": "A1"}
json.dumps(a, **opts)
# → '{"id":"A1","tribunal":"Créteil"}'
```

```python
# Exemple 2 : chaque réglage gzip compte
import gzip, io

def octets(mtime, nom):
    b = io.BytesIO()
    with gzip.GzipFile(nom, "wb", 6, b,
                       mtime) as gz:
        gz.write(b'{"id":"A1"}\n')
    return b.getvalue()

octets(0, "") == octets(0, "")    # → True
octets(1, "") == octets(0, "")    # → False
octets(0, "a") == octets(0, "")   # → False
```

- Quiz : Writer figé (ordre, clés, `mtime=0`, `filename=""`), puis mise à jour de Python en Lambda : quelle empreinte peut changer ?
- [ ] Celle du brut, pas celle du `.gz`
- [ ] Aucune des deux
- [x] Celle du `.gz`, pas celle du brut
- [ ] Les deux
- Réponse : Celle du `.gz`, pas celle du brut : une autre version de zlib peut compresser autrement ; le JSONL brut ne dépend que de `json.dumps`.

## 51. rejeu : l'ancien manifest décrit le nouveau fichier
- Sous-thème : rejeux
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Pendant un rejeu, le fichier est réécrit sous l'ancien manifest : un lecteur peut lire le nouveau fichier avec l'ancien `count` et `sha256`.
- Contexte : « Données puis manifest » protège la première publication, pas le remplacement : entre l'écrasement du part et celui du manifest, les deux ne vont plus ensemble si la source a changé. Parades : le lecteur compare le `sha256` lu au manifest et réessaie en cas d'écart ; ou le rejeu supprime d'abord le manifest ; ou chaque version va sous une nouvelle clé, que le manifest désigne.
- Usage : ✅ vérifier l'empreinte à la lecture quand des rejeux tournent pendant que d'autres lisent · ❌ croire que l'ordre suffit au rejeu : il ne couvre que la première écriture.

```python
# Exemple 1 : la fenêtre du rejeu
import hashlib
sha = lambda b: hashlib.sha256(b).hexdigest()[:8]
s3 = {"part": b'{"id": "A1"}\n',
      "manifest": {"sha256": sha(b'{"id": "A1"}\n')}}
s3["part"] = b'{"id": "A1", "rectif": 1}\n'  # rejeu
lu = s3["part"]       # lecteur, avant le manifest
sha(lu) == s3["manifest"]["sha256"]  # → False
```

- Quiz : Le rejeu supprime d'abord le manifest, puis réécrit le fichier et le manifest : que voit un lecteur pendant ce temps ?
- [ ] L'ancien manifest avec le nouveau fichier
- [x] Une partition non prête
- [ ] L'ancien fichier, toujours cohérent
- [ ] Une erreur 404 sur le part
- Réponse : une partition non prête : sans manifest, le lecteur attend ; on échange une incohérence possible contre une courte indisponibilité.
