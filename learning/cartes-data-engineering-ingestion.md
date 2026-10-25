---
title: "Cartes · Ingestion"
type: cartes
langage: Data engineering
cours: Ingestion
created: 2026-10-24
updated: 2026-10-24
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

## 6. backfill : rejouer une plage
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

## 7. dédoublonnage : garder la dernière version
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

## 8. watermark : reprendre où on s'est arrêté
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

## 9. retry : backoff exponentiel
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

## 10. générateurs : un pipeline en flux
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

## 11. _SUCCESS : signaler une partition complète
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

## 12. fraîcheur : planifier après la source
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

## 13. at-least-once : le doublon est normal
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

## 14. ordre : appliquer par version, pas par arrivée
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

## 15. CDC : rejouer les changements d'une base
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

## 16. évolution de schéma : ajouter, jamais renommer
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

## 17. lookback : relire les derniers jours
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

## 18. retry en flux : jamais après le premier yield
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

## 19. empreinte : détecter un changement
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

## 20. annulation : corriger l'annonce visée
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

## 21. checkpoint : reprendre au dernier lot écrit
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
