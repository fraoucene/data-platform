---
title: "Cartes · Dates Python"
type: cartes
langage: Python
chapitre: Fichiers et formats
cours: Dates
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Dates Python
Python · Dates : parser, calcul, horloge, fuseaux, heure d'été (format spec v4 de revision-pwa).

## 1. date.fromisoformat
- Id : dates-date-fromisoformat
- Sous-thème : parser
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : dates-strptime-format
- Définition : `date.fromisoformat` parse une date ISO `AAAA-MM-JJ` en objet `date`, comparable et triable.
- Contexte : Une `date` ne porte ni heure ni fuseau. Les objets `date` se comparent et se soustraient directement, alors que des chaînes ne se trient correctement qu'en ISO. `isoformat()` fait l'inverse. `weekday()` compte lundi = 0, alors que `getDay()` en JS compte dimanche = 0. Depuis Python 3.11, la forme compacte `20261023` est aussi acceptée.
- Usage : ✅ dates de parution BODACC, paramètres `AAAA-MM-JJ` d'une API · ❌ format français ou exotique : `datetime.strptime` ; date avec heure : `datetime.fromisoformat`.

```python
# Exemple 1 : parser une date ISO
from datetime import date

d = date.fromisoformat("2026-10-23")
d.year, d.month   # → (2026, 10)
d.weekday()       # → 4 : vendredi
d.isoformat()     # → "2026-10-23"
```

```python
# Exemple 2 : comparer et trier
from datetime import date

jours = ["2026-10-23", "2026-10-02"]
ds = [date.fromisoformat(j)
      for j in jours]
min(ds)          # → date(2026, 10, 2)
ds[0] > ds[1]    # → True
```

- Quiz : Que fait `date.fromisoformat("23/10/2026")` ?
- [x] `ValueError`
- [ ] Renvoie `date(2026, 10, 23)`
- [ ] Renvoie `None`
- [ ] `TypeError`
- Réponse : `ValueError` : seul le format ISO est accepté ; une date française se parse avec `strptime("%d/%m/%Y")`.

## 2. strptime : le format
- Id : dates-strptime-format
- Sous-thème : parser
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Voir aussi : dates-date-fromisoformat
- Définition : `datetime.strptime` parse une chaîne selon un format explicite (`%d`, `%m`, `%Y`…), `strftime` formate dans l'autre sens.
- Contexte : Directives courantes : `%d` jour, `%m` mois, `%Y` année sur 4 chiffres, `%y` sur 2, `%H` heure, `%M` minutes. `strptime` renvoie toujours un `datetime` (heure à minuit si absente) : `.date()` pour ne garder que la date. La chaîne doit suivre exactement le format, sinon `ValueError`. Moyen mnémotechnique : p comme parse, f comme format.
- Usage : ✅ dates françaises `JJ/MM/AAAA`, horodatages de logs · ❌ chaîne déjà ISO : `fromisoformat`, plus simple et plus rapide.

```python
# Exemple 1 : parser puis reformater
from datetime import datetime

s = "23/10/2026"
d = datetime.strptime(s, "%d/%m/%Y")
d.month               # → 10
d.strftime("%Y-%m")   # → "2026-10"
```

```python
# Exemple 2 : datetime, pas date
from datetime import date, datetime

d = datetime.strptime("23/10/2026",
                      "%d/%m/%Y")
d.hour    # → 0  (minuit)
d.date()  # → date(2026, 10, 23)
# la chaîne ne suit pas le format
datetime.strptime("2026-10-23",
    "%d/%m/%Y")  # ❌ ValueError
```

- Quiz : Que vaut `datetime.strptime(s, "%d/%M/%Y").month` ?
- [ ] `10`
- [ ] `ValueError`
- [x] `1`
- [ ] `0`
- Réponse : `1` : `%M` signifie minutes ; `10` part dans les minutes et le mois prend sa valeur par défaut, sans erreur.

## 3. timedelta : l'écart
- Id : dates-timedelta-ecart
- Sous-thème : calcul
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : dates-date-fromisoformat
- Définition : soustraire deux dates donne un `timedelta` ; ajouter un `timedelta` à une date la décale de jours, heures, semaines.
- Contexte : Un `timedelta` stocke des jours, secondes et microsecondes : `.days` donne les jours entiers, `.total_seconds()` la durée complète. Il peut être négatif. Pas de calcul en millisecondes comme avec `Date` en JS : on manipule des objets, et le passage d'un mois ou d'une année est géré tout seul.
- Usage : ✅ fenêtre des N derniers jours, délai entre deux annonces · ❌ décaler d'un mois ou d'un an : `date.replace` ou `dateutil.relativedelta`.

```python
# Exemple 1 : écart et décalage
from datetime import date, timedelta

d1 = date(2026, 10, 1)
d2 = date(2026, 10, 23)
(d2 - d1).days        # → 22
d1 + timedelta(weeks=1)
# → date(2026, 10, 8)
```

```python
# Exemple 2 : les 3 derniers jours
from datetime import date, timedelta

fin = date(2026, 11, 1)
[(fin - timedelta(days=i)).day
 for i in range(3)]
# → [1, 31, 30]  (1er nov., 31, 30 oct.)
(fin - date(2026, 11, 3)).days
# → -2  (écart négatif)
```

- Quiz : Avec `d1 = date(2026, 10, 1)`, que fait `d1 + timedelta(months=1)` ?
- [ ] Renvoie `date(2026, 11, 1)`
- [ ] Renvoie `date(2026, 10, 31)`
- [x] `TypeError`
- [ ] `AttributeError`
- Réponse : `TypeError` : `timedelta` n'a pas de mois (durée variable) ; il faut `d1.replace(month=11)` ou `dateutil.relativedelta`.

## 4. comparer : date contre date
- Id : dates-comparer-deux-dates
- Sous-thème : calcul
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Source : data-platform · S1-07
- Définition : Deux `date` se comparent avec `<`, `>=`, `==` dans l'ordre chronologique : `resolve_day` refuse ainsi le jour même (`day >= today`).
- Contexte : Pas besoin de passer par des chaînes : `min`, `max`, `sorted` marchent directement sur des `date`. Comparer une `date` à un `datetime` avec `<` lève en revanche `TypeError`, même si `datetime` hérite de `date` : on ramène d'abord les deux côtés au même type, avec `.date()` sur le `datetime`, dans le bon fuseau.
- Usage : ✅ bornes d'une plage, refus d'une date future, jour le plus récent · ❌ comparer des chaînes de dates non normalisées : parser d'abord.

```python
# Exemple 1 : refuser aujourd'hui
from datetime import date
today = date(2026, 10, 26)
date(2026, 10, 25) >= today  # → False
date(2026, 10, 26) >= today  # → True
max(date(2026, 10, 2), today)
# → date(2026, 10, 26)
```

```python
# Exemple 2 : date contre datetime
from datetime import date, datetime

d = date(2026, 10, 25)
n = datetime(2026, 10, 25, 1)
d == n.date()   # → True
d < n           # ❌ TypeError
```

- Quiz : Que vaut `"2026-10-9" < "2026-10-10"` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : des chaînes se comparent caractère par caractère, et `"9" > "1"` ; seul l'ISO complet (`2026-10-09`) trie juste.

## 5. datetime : naïf ou aware
- Id : dates-naif-ou-aware
- Sous-thème : fuseaux
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Définition : un `datetime` sans `tzinfo` est naïf, avec un fuseau (`ZoneInfo`) il est aware ; les deux ne se comparent pas.
- Contexte : `datetime.now()` et `strptime` renvoient du naïf ; `datetime.now(timezone.utc)` de l'aware. `ZoneInfo` gère l'heure d'été : Paris est à UTC+2 en octobre, UTC+1 en novembre. Règle : stocker en UTC, convertir à l'affichage avec `astimezone`. Un `Date` JS est toujours un instant UTC ; Python laisse le choix, et donc la confusion.
- Usage : ✅ horodatages d'ingestion, comparaisons entre sources (UTC partout) · ❌ simple date de parution sans heure : `date`, qui n'a pas de fuseau.

```python
# Exemple 1 : un fuseau, un décalage
from datetime import datetime
from zoneinfo import ZoneInfo

paris = ZoneInfo("Europe/Paris")
d = datetime(2026, 10, 23, 10,
             tzinfo=paris)
d.utcoffset().seconds // 3600   # → 2
```

```python
# Exemple 2 : convertir en UTC
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

paris = ZoneInfo("Europe/Paris")
# 2 novembre : heure d'hiver
d = datetime(2026, 11, 2, 10,
             tzinfo=paris)
u = d.astimezone(timezone.utc)
u.hour   # → 9
u == d   # → True  (même instant)
```

- Quiz : Avec `d` de l'exemple 1, que fait `d < datetime(2026, 10, 23, 12)` ?
- [ ] `True`
- [x] `TypeError`
- [ ] `False`
- Réponse : `TypeError` : comparer naïf et aware est interdit ; piège en plus, `==` ne lève pas mais renvoie toujours `False`.

## 6. ZoneInfo : un fuseau par son nom
- Id : dates-zoneinfo-nom-iana
- Sous-thème : fuseaux
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : dates-naif-ou-aware
- Source : data-platform · S1-07
- Définition : `ZoneInfo("Europe/Paris")` charge un fuseau IANA avec ses règles d'heure d'été, à passer en `tzinfo` ou à `astimezone`.
- Contexte : Le nom est une clé IANA `Continent/Ville` (`Europe/Paris`, `UTC`) : `"Paris"` n'existe pas et lève `ZoneInfoNotFoundError`, sous-classe de `KeyError`. Le décalage n'est pas stocké : il est calculé pour chaque instant (CEST l'été, CET l'hiver). On crée le fuseau une fois, en constante de module (`PARIS = ZoneInfo("Europe/Paris")`). Équivalent du `timeZone: "Europe/Paris"` d'`Intl`, mais utilisable dans les calculs.
- Usage : ✅ tout calcul en heure civile (jour de parution à Paris) · ❌ un décalage fixe (`+02:00`) pour représenter Paris : faux la moitié de l'année.

```python
# Exemple 1 : le décalage suit la saison
from datetime import datetime
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
datetime(2026, 7, 1, tzinfo=P).tzname()
# → "CEST"
datetime(2026, 12, 1, tzinfo=P).tzname()
# → "CET"
```

```python
# Exemple 2 : un nom inconnu
from zoneinfo import ZoneInfo

ZoneInfo("Europe/Paris").key
# → "Europe/Paris"
ZoneInfo("Paris")  # ❌ ZoneInfoNotFoundError
```

- Quiz : Que vaut `ZoneInfo("Europe/Paris") is ZoneInfo("Europe/Paris")` ?
- [x] `True`
- [ ] `False`
- [ ] `TypeError`
- Réponse : `True` : `ZoneInfo` met ses instances en cache par clé ; deux appels renvoient le même objet, ce qui rend la constante de module peu coûteuse.

## 7. datetime.now : passer le fuseau
- Id : dates-now-avec-fuseau
- Sous-thème : horloge
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Prérequis : dates-naif-ou-aware
- Voir aussi : dates-today-jour-machine
- Source : data-platform · S1-07
- Définition : `datetime.now(tz)` renvoie l'instant courant, aware, dans ce fuseau ; sans argument, l'heure murale de la machine, naïve.
- Contexte : Sur Lambda la machine est en UTC, sur un Mac à Paris : `datetime.now()` change de valeur selon l'hôte, sans le dire (pas de `tzinfo`). `datetime.now(PARIS)` et `datetime.now(timezone.utc)` sont le même instant, affiché différemment. En TS, `new Date()` est toujours un instant absolu ; ici l'instant n'est défini que si on donne le fuseau.
- Usage : ✅ `now(timezone.utc)` pour horodater, `now(PARIS)` pour calculer un jour métier · ❌ `datetime.now()` nu dans du code déployé : naïf, différent selon la machine.

```python
# Exemple 1 : aware ou naïf
from datetime import datetime
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
datetime.now().tzinfo     # → None
datetime.now(P).tzinfo
# → ZoneInfo("Europe/Paris")
```

```python
# Exemple 2 : un instant, deux affichages
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

u = datetime.now(timezone.utc)
p = u.astimezone(ZoneInfo("Europe/Paris"))
u == p                     # → True
(p - u).total_seconds()    # → 0.0
```

- Quiz : Que vaut `datetime.utcnow().tzinfo` ?
- [ ] `timezone.utc`
- [ ] `ZoneInfo("UTC")`
- [x] `None`
- [ ] `AttributeError`
- Réponse : `None` : malgré son nom, `utcnow()` renvoie l'heure UTC en naïf (déprécié depuis 3.12) ; écrire `datetime.now(timezone.utc)`.

## 8. date.today : le jour de la machine
- Id : dates-today-jour-machine
- Sous-thème : horloge
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Voir aussi : dates-now-avec-fuseau
- Source : data-platform · S1-07
- Définition : `date.today()` renvoie la date locale de la machine, sans fuseau : sur Lambda, c'est le jour UTC.
- Contexte : `date.today()` équivaut à `datetime.now().date()` : naïf, il dépend du réglage `TZ` de l'hôte. Pour le jour à Paris quel que soit l'hôte : `datetime.now(PARIS).date()`. Piège typique : le test passe sur le Mac (réglé sur Paris) et la Lambda ingère la mauvaise journée entre minuit et 2 h.
- Usage : ✅ script local jetable, sans enjeu de fuseau · ❌ code déployé : `datetime.now(fuseau).date()`, et horloge injectée pour tester.

```python
# Exemple 1 : le jour à Paris, partout
from datetime import date, datetime
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
jour = datetime.now(P).date()
type(jour) is date     # → True
```

```python
# Exemple 2 : today = now naïf coupé
from datetime import date, datetime

date.today() == datetime.now().date()
# → True  (même horloge machine)
```

- Quiz : Que fait `date.today(ZoneInfo("Europe/Paris"))` ?
- [ ] Renvoie le jour à Paris
- [ ] Renvoie le jour UTC
- [x] `TypeError`
- [ ] Ignore l'argument
- Réponse : `TypeError` (`date.today() takes no arguments`) : `today` n'accepte pas de fuseau ; passer par `datetime.now(P).date()`.

## 9. .date() : le jour dans quel fuseau ?
- Id : dates-date-dans-quel-fuseau
- Sous-thème : fuseaux
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Prérequis : dates-naif-ou-aware
- Voir aussi : dates-journee-bornes-utc
- Source : data-platform · S1-07
- Définition : `dt.date()` garde le jour tel que le `datetime` l'affiche, donc dans son propre fuseau : convertir avant de couper.
- Contexte : Le cœur de `resolve_day`. 2026-10-24 22:30 UTC est déjà le 25 à 00:30 à Paris (CEST, UTC+2). `.date()` ne convertit rien : il lit l'année, le mois et le jour de l'objet. Sur Lambda (UTC), `.date()` direct donne donc la veille du jour parisien entre minuit et 2 h. D'où `now.astimezone(PARIS).date()`.
- Usage : ✅ jour métier (parution BODACC, partition `dt=`) : `astimezone(fuseau_métier).date()` · ❌ `.date()` direct sur un instant UTC quand le métier raisonne en heure de Paris.

```python
# Exemple 1 : même instant, deux jours
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
u = datetime(2026, 10, 24, 22, 30,
             tzinfo=timezone.utc)
u.date()  # → date(2026, 10, 24)
u.astimezone(P).date()
# → date(2026, 10, 25)
```

```python
# Exemple 2 : la veille, selon le fuseau
from datetime import (date, datetime,
                      timedelta, timezone)
from zoneinfo import ZoneInfo

P = ZoneInfo("Europe/Paris")
u = datetime(2026, 10, 24, 22, 30,
             tzinfo=timezone.utc)
u.date() - timedelta(days=1)
# → date(2026, 10, 23)  (faux)
u.astimezone(P).date() - timedelta(1)
# → date(2026, 10, 24)  (veille à Paris)
```

- Quiz : Le 2 novembre à 00:30 heure de Paris, quel jour donne `.date()` sur le même instant en UTC ?
- [ ] Le 2 novembre
- [x] Le 1er novembre
- [ ] Le 3 novembre
- [ ] Le 31 octobre
- Réponse : le 1er novembre : en novembre Paris est à UTC+1 (CET), 00:30 à Paris = 23:30 UTC la veille.

## 10. datetime.fromisoformat : le décalage
- Id : dates-datetime-fromisoformat-decalage
- Sous-thème : parser
- Type : concept
- Niveau : 1
- Profils : débutant, web, data
- Prérequis : dates-date-fromisoformat, dates-naif-ou-aware
- Source : data-platform · S1-07
- Définition : `datetime.fromisoformat` lit un horodatage ISO ; avec un décalage (`+00:00`) le résultat est aware, sans décalage il est naïf.
- Contexte : Les horodatages d'API (`data_processed` du BODACC) arrivent ainsi. Une chaîne sans décalage ne dit pas son fuseau : l'interpréter explicitement (`replace(tzinfo=…)` si on le connaît), jamais deviner. Python 3.11 a élargi le format accepté à presque tout ISO 8601. Dans les tests, `fromisoformat("2026-10-24T22:30:00+00:00")` écrit un instant UTC plus lisiblement qu'un constructeur.
- Usage : ✅ horodatages d'API, instants de test lisibles · ❌ format non ISO (`24/10/2026 22:30`) : `strptime`.

```python
# Exemple 1 : aware si décalage
from datetime import datetime, timezone
a = datetime.fromisoformat(
    "2026-10-24T22:30:00+00:00")
a.tzinfo    # → timezone.utc
n = datetime.fromisoformat(
    "2026-10-24T22:30:00")
n.tzinfo    # → None  (naïf)
```

```python
# Exemple 2 : un décalage non nul
from datetime import datetime, timedelta

d = datetime.fromisoformat(
    "2026-10-25T00:30:00+02:00")
d.utcoffset()  # → timedelta(hours=2)
d.tzname()     # → "UTC+02:00"
```

- Quiz : En Python 3.12, que vaut `datetime.fromisoformat("2026-10-24T22:30Z").tzinfo` ?
- [ ] `None`
- [x] `timezone.utc`
- [ ] `ValueError`
- [ ] `ZoneInfo("UTC")`
- Réponse : `timezone.utc` : depuis 3.11, le suffixe `Z` est accepté et vaut `+00:00` ; avant, `ValueError`.

## 11. astimezone sur un naïf : l'heure de la machine
- Id : dates-astimezone-sur-naif
- Sous-thème : fuseaux
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : dates-naif-ou-aware
- Voir aussi : dates-replace-ou-astimezone
- Source : data-platform · S1-07
- Définition : `astimezone(tz)` sur un `datetime` naïf ne lève pas : Python le suppose à l'heure locale de la machine, puis convertit.
- Contexte : L'erreur évitée dans `resolve_day`. `datetime(2026, 10, 26, 8).astimezone(PARIS)` vaut 08:00 sur un Mac réglé sur Paris, mais 09:00 sur Lambda (UTC) : le même code donne deux résultats selon l'hôte, sans erreur. Seule parade : refuser le naïf à l'entrée (`if now.tzinfo is None: raise ValueError`), ou lui attacher explicitement son fuseau avec `replace(tzinfo=…)`.
- Usage : ✅ garde `tzinfo is None` à l'entrée de toute fonction qui reçoit un instant · ❌ compter sur `astimezone` pour « réparer » un naïf : il devine.

```python
# Exemple 1 : aucune erreur, résultat local
from datetime import datetime
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
n = datetime(2026, 10, 26, 8, 0)
n.astimezone(P).tzinfo
# → ZoneInfo("Europe/Paris")
# Mac à Paris : 08:00 ; Lambda : 09:00
```

```python
# Exemple 2 : refuser le naïf à l'entrée
from datetime import datetime

def exiger_aware(now):
    if now.tzinfo is None:
        raise ValueError("now naïf")
    return now

d = datetime(2026, 10, 26, 8)
exiger_aware(d)   # ❌ ValueError
```

- Quiz : Sur Lambda (UTC), que vaut `datetime(2026, 10, 24, 23).astimezone(P).date()` ?
- [ ] `date(2026, 10, 24)`
- [x] `date(2026, 10, 25)`
- [ ] `ValueError`
- [ ] `TypeError`
- Réponse : `date(2026, 10, 25)` : le naïf est pris pour 23:00 UTC (heure de la machine), soit 01:00 le 25 à Paris ; sur un Mac à Paris, ce serait le 24.

## 12. replace(tzinfo) ou astimezone
- Id : dates-replace-ou-astimezone
- Sous-thème : fuseaux
- Type : comparaison
- Niveau : 2
- Profils : data
- Prérequis : dates-zoneinfo-nom-iana
- Source : data-platform · S1-07
- Définition : `replace(tzinfo=tz)` colle un fuseau sans toucher l'heure affichée ; `astimezone(tz)` convertit le même instant vers ce fuseau.
- Contexte : `replace` change l'instant : 22:30 UTC devenu « 22:30 à Paris » a glissé de deux heures. Il sert à **étiqueter** un naïf dont on connaît le fuseau (un log qu'on sait écrit en heure de Paris). `astimezone` sert à **convertir** un instant déjà aware, pour l'afficher ou en extraire le jour. Confondre les deux décale les données en silence.
- Usage : ✅ `replace` pour attacher son fuseau connu à un naïf · `astimezone` pour convertir un aware · ❌ `replace(tzinfo=…)` sur un aware pour « convertir ».

```python
# Exemple 1 : même affichage, autre instant
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
u = datetime(2026, 10, 24, 22, 30,
             tzinfo=timezone.utc)
u.replace(tzinfo=P).hour   # → 22
u.astimezone(P).hour       # → 0
u.replace(tzinfo=P) == u   # → False
```

- Quiz : `n = datetime(2026, 10, 24, 22, 30)` est connu en heure de Paris. Que vaut `n.replace(tzinfo=P).astimezone(timezone.utc).hour` ?
- [ ] `22`
- [ ] `0`
- [x] `20`
- [ ] `21`
- Réponse : `20` : `replace` déclare 22:30 à Paris (CEST, UTC+2), `astimezone` le convertit en 20:30 UTC.

## 13. now=None : l'horloge lue à l'appel
- Id : dates-now-none-injectable
- Sous-thème : horloge
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : dates-now-avec-fuseau
- Voir aussi : tests-horloge-instants-limites, decorateurs-cache-heure-figee
- Source : data-platform · S1-07
- Définition : `def f(now=None)` puis `now = now or datetime.now(PARIS)` : l'horloge est lue à chaque appel, et un test peut imposer l'instant.
- Contexte : Une valeur par défaut est évaluée **une fois**, à la définition de la fonction (comme un `[]` partagé). `def f(now=datetime.now(PARIS))` figerait l'instant du chargement du module : sur une Lambda dont le conteneur reste chaud des heures, tous les appels verraient la même date. `None` en sentinelle reporte la lecture à l'appel, comme un `const now = new Date()` dans le corps d'une fonction TS.
- Usage : ✅ toute fonction qui dépend de l'heure : `now` injectable, défaut `None` · ❌ `now=datetime.now()` en valeur par défaut, ou horloge lue en dur au fond du code.

```python
# Exemple 1 : l'instant imposé par le test
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
def veille(now=None):
    now = now or datetime.now(P)
    return now.date() - timedelta(1)
lundi = datetime(2026, 10, 26, 8,
                 tzinfo=P)
veille(lundi)  # → date(2026, 10, 25)
```

```python
# Exemple 2 : piège, défaut figé au def
import time
from datetime import datetime, timezone

def stamp(now=datetime.now(timezone.utc)):
    return now

a = stamp()
time.sleep(0.01)
stamp() == a    # → True  (figé)
```

- Quiz : Avec `now = datetime(2026, 1, 1, 0, 0, tzinfo=P)` (minuit pile), que renvoie `now or datetime.now(P)` ?
- [x] `now`
- [ ] L'heure courante : minuit est faux
- [ ] `None`
- [ ] `TypeError`
- Réponse : `now` : un `datetime` est toujours vrai, même à minuit ; seul `time(0)` était faux, avant Python 3.5.

## 14. journée à Paris : ses bornes en UTC
- Id : dates-journee-bornes-utc
- Sous-thème : fuseaux
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : dates-zoneinfo-nom-iana, dates-replace-ou-astimezone
- Source : data-platform · S1-07
- Définition : `datetime.combine(jour, time(), tzinfo=P)` donne minuit de ce jour à Paris ; converti en UTC, il borne une requête par instant.
- Contexte : Une API qui filtre par horodatage UTC (`published_at >= …`) ne connaît pas « le 24 à Paris » : il faut lui donner `[minuit du 24, minuit du 25[` convertis, soit 22:00 UTC la veille en été, 23:00 en hiver. Calculer la fin comme minuit du jour suivant (et non `début + 24 h`) reste juste les jours de changement d'heure, qui ne durent pas 24 h.
- Usage : ✅ requêtes par plage d'instants, filtres Athena sur un horodatage UTC · ❌ filtrer `dt.date() == jour` sur des instants UTC : décalé de 2 h.

```python
# Exemple 1 : minuit à Paris, en UTC
from datetime import (date, datetime,
                      time, timezone)
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
d = datetime.combine(date(2026, 10, 24),
                     time(), tzinfo=P)
d.astimezone(timezone.utc).hour  # → 22
```

```python
# Exemple 2 : [début, fin[ du 24 en UTC
from datetime import (date, datetime,
                      time, timedelta, timezone)
from zoneinfo import ZoneInfo

P, U = ZoneInfo("Europe/Paris"), timezone.utc
def bornes(jour):
    debut = datetime.combine(jour, time(), tzinfo=P)
    fin = datetime.combine(
        jour + timedelta(1), time(), tzinfo=P)
    return debut.astimezone(U), fin.astimezone(U)

a, b = bornes(date(2026, 10, 24))
str(a)  # → "2026-10-23 22:00:00+00:00"
str(b)  # → "2026-10-24 22:00:00+00:00"
```

- Quiz : Combien d'heures dure la journée du 25 octobre 2026 à Paris ?
- [ ] 24
- [x] 25
- [ ] 23
- Réponse : 25 : à 3 h, Paris recule à 2 h (CEST → CET) ; de minuit à minuit il s'écoule 25 h réelles.

## 15. timezone fixe ou ZoneInfo
- Id : dates-timezone-fixe-ou-zoneinfo
- Sous-thème : fuseaux
- Type : comparaison
- Niveau : 2
- Profils : data
- Source : data-platform · S1-07
- Définition : `timezone(timedelta(hours=2))` est un décalage fixe, sans heure d'été ; `ZoneInfo("Europe/Paris")` suit les règles du fuseau toute l'année.
- Contexte : Paris est à UTC+2 l'été (CEST) et UTC+1 l'hiver (CET). Coder `+02:00` en dur donne un résultat juste en octobre et faux d'une heure en novembre, sans erreur. Les décalages lus par `fromisoformat` sont eux aussi des `timezone` fixes : ils décrivent un instant, pas un fuseau. `timezone.utc` reste le bon choix pour UTC, qui n'a pas d'heure d'été.
- Usage : ✅ `timezone.utc` pour UTC, `ZoneInfo` pour tout fuseau civil · ❌ `timezone(timedelta(hours=1))` ou `hours=2` pour « l'heure de Paris ».

```python
# Exemple 1 : +02:00 en novembre
from datetime import (datetime, timedelta,
                      timezone)
from zoneinfo import ZoneInfo
fixe = timezone(timedelta(hours=2))
P = ZoneInfo("Europe/Paris")
d = datetime(2026, 11, 2, 10, tzinfo=fixe)
d.astimezone(P).hour   # → 9  (pas 10)
```

- Quiz : Avec `d = datetime.fromisoformat("2026-10-24T10:00+02:00")`, que vaut `(d + timedelta(days=10)).utcoffset()` ?
- [ ] 1 h : heure d'hiver
- [x] 2 h
- [ ] `None`
- [ ] `ValueError`
- Réponse : 2 h : `fromisoformat` attache un décalage fixe, qui ne suit aucune règle d'heure d'été ; le 3 novembre, Paris est pourtant à UTC+1.

## 16. tzdata : les fuseaux partout
- Id : dates-tzdata-dependance
- Sous-thème : fuseaux
- Type : recette
- Niveau : 2
- Profils : ops
- Source : data-platform · S1-07
- Définition : `zoneinfo` lit la base IANA du système ; le paquet `tzdata` la fournit quand l'hôte n'en a pas (Windows, images minimales).
- Contexte : `ZoneInfo` cherche dans `zoneinfo.TZPATH` (`/usr/share/zoneinfo`…), puis dans le paquet `tzdata` s'il est installé. Sans les deux : `ZoneInfoNotFoundError`, même pour `Europe/Paris`. D'où `tzdata` en dépendance de la Lambda `ingest_bodacc` : le zip embarque la base, le résultat ne dépend plus de l'image. Le paquet suit les mises à jour IANA (règles qui changent) : le tenir à jour.
- Usage : ✅ toute Lambda ou image qui utilise `ZoneInfo` : `tzdata` dans `dependencies` · ❌ supposer que l'hôte de production a la même base que le Mac.

```python
# Exemple 1 : où zoneinfo cherche
import zoneinfo
zoneinfo.TZPATH[0]
# → "/usr/share/zoneinfo"
"Europe/Paris" in (
    zoneinfo.available_timezones())
# → True
```

```bash
# Exemple 2 : la dépendance de la Lambda
uv add --package ingest-bodacc tzdata
# pyproject : "tzdata>=2026.5"
```

- Quiz : Sur une image sans base système ni `tzdata`, que fait `ZoneInfo("UTC")` ?
- [ ] Renvoie UTC : cas spécial intégré
- [x] `ZoneInfoNotFoundError`
- [ ] Renvoie `timezone.utc`
- [ ] Renvoie `None`
- Réponse : `ZoneInfoNotFoundError` : même `UTC` vient de la base IANA ; seul `datetime.timezone.utc` s'en passe.

## 17. soustraire dans un même fuseau : l'heure murale
- Id : dates-soustraction-heure-murale
- Sous-thème : heure d'été
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : dates-timedelta-ecart, dates-zoneinfo-nom-iana
- Source : data-platform · S1-07
- Définition : Deux `datetime` de même `tzinfo` se soustraient en heure murale, changement d'heure ignoré ; passer en UTC pour la durée réelle.
- Contexte : Python ne tient compte des décalages que si les `tzinfo` diffèrent. Le 25 octobre 2026, Paris recule de 3 h à 2 h : de 12:00 le 24 à 12:00 le 25 il s'écoule 25 h, mais la soustraction directe donne `1 day`. L'addition suit la même règle : `+ timedelta(hours=24)` avance l'horloge murale de 24 h. Pour une durée (SLA, latence d'ingestion), convertir les deux en UTC d'abord.
- Usage : ✅ durées réelles : `b.astimezone(U) - a.astimezone(U)` · ❌ durée calculée entre deux instants d'un fuseau à heure d'été.

```python
# Exemple 1 : 24 h affichées, 25 h écoulées
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
P, U = ZoneInfo("Europe/Paris"), timezone.utc
a = datetime(2026, 10, 24, 12, tzinfo=P)
b = datetime(2026, 10, 25, 12, tzinfo=P)
(b - a).total_seconds() / 3600  # → 24.0
reel = b.astimezone(U) - a.astimezone(U)
reel.total_seconds() / 3600     # → 25.0
```

- Quiz : `a` = 24 oct. 12:00 à Paris (`P`), `b` = 25 oct. 11:00 en `timezone.utc`. Que vaut `b - a` ?
- [ ] `1 day, 0:00:00`
- [ ] `23:00:00`
- [x] `1 day, 1:00:00`
- [ ] `TypeError`
- Réponse : `1 day, 1:00:00` : `tzinfo` différents, Python convertit en UTC ; `a` = 10:00 UTC le 24, d'où 25 h.

## 18. fold : 02:30 existe deux fois
- Id : dates-fold-heure-ambigue
- Sous-thème : heure d'été
- Type : concept
- Niveau : 3
- Profils : expert
- Prérequis : dates-zoneinfo-nom-iana
- Voir aussi : dates-heure-inexistante
- Source : data-platform · S1-07
- Définition : Le 25 octobre 2026, 02:30 à Paris existe deux fois ; `fold=0` désigne le premier passage (CEST), `fold=1` le second (CET).
- Contexte : Au recul de 3 h à 2 h, les heures murales 02:00 à 02:59 se répètent. Un horodatage `2026-10-25 02:30` sans décalage est donc ambigu, à une heure près. L'attribut `fold` (PEP 495) lève l'ambiguïté ; il vaut 0 par défaut. C'est une raison de plus pour stocker les instants en UTC ou en ISO avec décalage, jamais en heure locale nue.
- Usage : ✅ relire des logs en heure locale, à convertir en UTC au plus tôt · ❌ stocker de l'heure locale sans décalage : stocker l'UTC.

```python
# Exemple 1 : deux décalages pour 02:30
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
a = datetime(2026, 10, 25, 2, 30, tzinfo=P)
b = a.replace(fold=1)
a.utcoffset().seconds // 3600  # → 2
b.utcoffset().seconds // 3600  # → 1
```

```python
# Exemple 2 : une heure d'écart en UTC
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

P, U = ZoneInfo("Europe/Paris"), timezone.utc
a = datetime(2026, 10, 25, 2, 30, tzinfo=P)
b = a.replace(fold=1)
a.astimezone(U).hour   # → 0
b.astimezone(U).hour   # → 1
```

- Quiz : Avec `a` et `b` de l'exemple 1, que vaut `a == b` ?
- [ ] `False`
- [x] `True`
- [ ] `TypeError`
- Réponse : `True` : même `tzinfo`, la comparaison se fait en heure murale et ignore `fold` ; pourtant une heure les sépare.

## 19. heure inexistante : 02:30 le 29 mars
- Id : dates-heure-inexistante
- Sous-thème : heure d'été
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : dates-zoneinfo-nom-iana
- Voir aussi : dates-fold-heure-ambigue
- Source : data-platform · S1-07
- Définition : Le 29 mars 2026, Paris saute de 02:00 à 03:00 ; `ZoneInfo` accepte pourtant 02:30 sans erreur, avec un décalage choisi par `fold`.
- Contexte : Une heure qui n'existe pas ne lève rien. Avec `fold=0`, `ZoneInfo` applique le décalage d'avant la transition (+01:00) ; un aller-retour par UTC « normalise » en 03:30. Un traitement planifié à 02:30 en heure de Paris ne trouve donc pas son créneau ce jour-là : planifier en UTC, ou hors de la plage 02:00 à 03:00.
- Usage : ✅ valider une heure saisie : aller-retour UTC, comparer · ❌ cron en heure locale entre 02:00 et 03:00 : sauté ou doublé deux fois par an.

```python
# Exemple 1 : 02:30 devient 03:30
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
d = datetime(2026, 3, 29, 2, 30, tzinfo=P)
d.utcoffset().seconds // 3600   # → 1
d.astimezone(timezone.utc).astimezone(P).hour
# → 3
```

- Quiz : Que vaut `datetime(2026, 3, 29, 2, 30, fold=1, tzinfo=P).astimezone(timezone.utc).hour` ?
- [x] `0`
- [ ] `1`
- [ ] `2`
- [ ] `ValueError`
- Réponse : `0` : avec `fold=1`, `ZoneInfo` prend le décalage d'après la transition (+02:00) : 02:30 − 2 h = 00:30 UTC.

## 20. fromisoformat : plus que AAAA-MM-JJ
- Id : dates-fromisoformat-formes-acceptees
- Sous-thème : parser
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : dates-date-fromisoformat
- Source : data-platform · S1-07
- Définition : Depuis Python 3.11, `date.fromisoformat` accepte aussi `20261020` et la semaine ISO `2026-W43-1` : il ne garantit pas un format précis.
- Contexte : `resolve_day` annonce « attendu YYYY-MM-DD » mais laisse passer ces formes, qui désignent bien une date : sans conséquence ici. Un contrat strict (clé de partition, paramètre d'API documenté) doit le vérifier en plus : comparer `d.isoformat() == raw` est le plus simple. Avant 3.11, seul `AAAA-MM-JJ` passait : le comportement dépend de la version de Python.
- Usage : ✅ entrée tolérante (rejeu manuel) · ❌ contrat strict : ajouter le contrôle `isoformat() == raw`.

```python
# Exemple 1 : deux formes acceptées
from datetime import date
date.fromisoformat("2026-W43-1")
# → date(2026, 10, 19)  (lundi, sem. 43)
date.fromisoformat("20261020")
# → date(2026, 10, 20)
```

```python
# Exemple 2 : exiger AAAA-MM-JJ exactement
from datetime import date

def strict(raw):
    d = date.fromisoformat(raw)
    if d.isoformat() != raw:
        raise ValueError(f"{raw!r} : AAAA-MM-JJ")
    return d

strict("2026-10-20")  # → date(2026, 10, 20)
strict("20261020")    # ❌ ValueError
```

- Quiz : En Python 3.12, que fait `date.fromisoformat("2026-10-9")` ?
- [x] `ValueError`
- [ ] Renvoie `date(2026, 10, 9)`
- [ ] Renvoie `date(2026, 10, 1)`
- [ ] Renvoie `None`
- Réponse : `ValueError` : formes élargies ou non, le jour garde 2 chiffres ; `strptime("%Y-%m-%d")`, lui, accepte `9` sans erreur.

## 21. datetime hérite de date
- Id : dates-datetime-herite-de-date
- Sous-thème : calcul
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : dates-date-fromisoformat
- Voir aussi : dates-date-dans-quel-fuseau
- Source : data-platform · S1-07
- Définition : `datetime` est une sous-classe de `date` : `isinstance(dt, date)` est vrai, donc un contrôle par `isinstance` laisse passer un `datetime`.
- Contexte : Une fonction qui attend un jour (`day: date`) accepte un `datetime` sans broncher, puis se comporte mal : `day - timedelta(1)` garde l'heure, `f"dt={day}"` donne `dt=2026-10-24 22:30:00` dans une clé S3. Pour exiger un vrai jour : `type(x) is date`, ou normaliser avec `.date()` (dans le bon fuseau). Les annotations de type ne protègent pas à l'exécution.
- Usage : ✅ `type(x) is date` dans une garde, `.date()` à la frontière · ❌ `isinstance(x, date)` pour « vérifier que c'est un jour ».

```python
# Exemple 1 : le contrôle laisse passer
from datetime import date, datetime
dt = datetime(2026, 10, 24, 22, 30)
isinstance(dt, date)  # → True
type(dt) is date      # → False
f"dt={dt}"
# → "dt=2026-10-24 22:30:00"
```

- Quiz : Que vaut `date(2026, 10, 25) == datetime(2026, 10, 25)` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : `==` entre `date` et `datetime` ne lève pas mais renvoie toujours faux, même à minuit ; comparer `dt.date() == d`.
