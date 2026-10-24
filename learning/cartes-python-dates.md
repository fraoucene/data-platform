---
title: "Cartes · Dates Python"
type: cartes
langage: Python
cours: Dates
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Dates Python
Python · Dates : dates, fuseaux (format spec v3 de revision-pwa).

## 1. date.fromisoformat
- Sous-thème : dates
- Niveau : 1
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
- Sous-thème : dates
- Niveau : 1
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
- Sous-thème : dates
- Niveau : 1
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

## 4. datetime : naïf ou aware
- Sous-thème : fuseaux
- Niveau : 3
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
