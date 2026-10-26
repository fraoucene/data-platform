---
title: "Cartes · CloudWatch"
type: cartes
langage: AWS
chapitre: Exploitation
cours: CloudWatch
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · CloudWatch
AWS · CloudWatch : métriques, alarmes, actions, graphes, données manquantes, diagnostic (format spec v4 de revision-pwa).

## 1. métriques Lambda : publiées sans code
- Id : cloudwatch-metriques-lambda
- Sous-thème : métriques
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : cloudwatch-errors-vs-throttles
- Mots-clés : métrique, dimension, throttling, EMF
- Source : data-platform · S1-08
- Définition : Lambda publie seule dans l'espace `AWS/Lambda` les métriques `Invocations`, `Errors`, `Duration`, `Throttles`, par fonction, sans une ligne de code.
- Contexte : Rien à installer ni à appeler : chaque invocation alimente ces séries, à la minute. Elles portent la dimension `FunctionName`, et une seconde série `FunctionName` + `Resource` (version ou alias). C'est la base d'une alarme d'exploitation ; une métrique métier (annonces ingérées) demanderait au contraire `PutMetricData` ou un log au format EMF.
- Usage : ✅ alarme d'échec, de throttling ou de durée sur une Lambda · ❌ compter des objets métier (annonces, SIREN) : métrique personnalisée ou manifest.

```bash
# Exemple 1 : ce qui existe déjà
aws cloudwatch list-metrics \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=$F \
  --query 'Metrics[].MetricName'
# → Throttles Errors Duration
#   Invocations ConcurrentExecutions …
#   (mesuré, chaque nom deux fois :
#    FunctionName, et + Resource)
```

- Quiz : Le handler attrape l'exception et renvoie `{"ok": False}`. Que compte `Errors` pour cette invocation ?
- [ ] 1 : le résultat dit échec
- [x] 0 : aucune exception n'est sortie
- [ ] Rien : la métrique n'est pas publiée
- Réponse : 0 : `Errors` ne compte que les exceptions sorties du handler et les erreurs du runtime (timeout) ; un retour normal est un succès.

## 2. Errors : exceptions et timeouts, pas les throttles
- Id : cloudwatch-errors-vs-throttles
- Sous-thème : métriques
- Type : comparaison
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : lambda-laisser-echouer
- Mots-clés : concurrence, throttling, runtime, timeout
- Source : data-platform · S1-08
- Définition : `Errors` compte les invocations terminées par une erreur de fonction : exception du code, ou erreur du runtime comme un timeout.
- Contexte : Une requête refusée faute de concurrence (`TooManyRequestsException`) ne compte ni dans `Invocations` ni dans `Errors`, seulement dans `Throttles` (doc Lambda). Une alarme sur `Errors` seule ne voit donc pas une fonction bridée. Le taux d'échec se calcule `Errors / Invocations`, et `Invocations` égale le nombre de requêtes facturées.
- Usage : ✅ `Errors` pour « le code a échoué », `Throttles` en plus pour « on n'a pas pu l'exécuter » · ❌ supposer qu'`Errors` couvre tous les échecs d'appel.

```bash
# Exemple 1 : une heure de rejeu, 0 erreur
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors --period 900 \
  --dimensions Name=FunctionName,Value=$F \
  --statistics Sum \
  --start-time 2026-10-25T12:00:00Z \
  --end-time 2026-10-26T00:00:00Z
# → 17:30  0.0   (19 invocations)
#   17:45  0.0   (5 invocations)
```

- Quiz : Réserve de concurrence à 0, Scheduler appelle la fonction : quelle métrique augmente ?
- [ ] `Errors`
- [ ] `Invocations` et `Errors`
- [x] `Throttles`
- [ ] Aucune
- Réponse : `Throttles` : la requête est refusée avant toute exécution ; elle ne compte ni comme invocation ni comme erreur.

## 3. Sum ou Average : compter ou mesurer un taux
- Id : cloudwatch-sum-ou-average
- Sous-thème : métriques
- Type : comparaison
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : métrique, statistique
- Source : data-platform · S1-08
- Définition : Chaque invocation envoie `Errors` = 0 ou 1 ; `Sum` sur une période donne le nombre d'échecs, `Average` le taux d'échec.
- Contexte : La statistique choisie change le sens du seuil. `Sum >= 1` : au moins un échec dans la période, ce qu'on veut pour un job quotidien. `Average > 0.05` : plus de 5 % d'échecs, utile pour une API très sollicitée où un échec isolé est normal. `Maximum` sur `Errors` vaut toujours 0 ou 1 : peu informatif.
- Usage : ✅ `Sum` pour un traitement rare et critique, `Average` pour un flux volumineux · ❌ `Average` sur un job quotidien : une invocation ratée sur trois = 0,33, seuil difficile à lire.

```python
# Exemple 1 : même série, deux lectures
errors = [0, 1, 0]   # essai + 2 retries
sum(errors)          # → 1
round(sum(errors) / len(errors), 2)
# → 0.33  (Average)
```

- Quiz : Sur 15 min, 3 invocations, toutes en échec. Que vaut `Average` de `Errors` ?
- [ ] `3`
- [x] `1.0`
- [ ] `0.33`
- [ ] `100`
- Réponse : `1.0` : la moyenne de trois 1 ; `Average` est une proportion entre 0 et 1, pas un pourcentage.

## 4. alarme : trois états
- Id : cloudwatch-alarme-trois-etats
- Sous-thème : alarmes
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : cloudwatch-treat-missing-data
- Mots-clés : métrique, abonnement SNS
- Source : data-platform · S1-08
- Définition : Une alarme est toujours `OK`, `ALARM` ou `INSUFFICIENT_DATA` ; elle part en `INSUFFICIENT_DATA` à sa création, faute de données évaluées.
- Contexte : `OK` : la métrique respecte le seuil. `ALARM` : elle le franchit. `INSUFFICIENT_DATA` : l'alarme vient de démarrer, ou pas assez de points pour décider. Juste après `make up`, l'historique montre le premier passage (mesuré : `INSUFFICIENT_DATA` → `OK`). Un état ne dit rien de la livraison du mail : c'est l'abonnement SNS qui décide.
- Usage : ✅ lire l'état avant de conclure « tout va bien » · ❌ prendre `INSUFFICIENT_DATA` pour une panne : c'est souvent une métrique qui n'a simplement pas de point.

```bash
# Exemple 1 : état et raison
aws cloudwatch describe-alarms \
  --alarm-names "$A" \
  --query 'MetricAlarms[0].[StateValue,
    StateReason]'
# → OK
#   Threshold Crossed: 1 datapoint
#   [0.0 (25/10/26 16:57:00)] was not
#   greater than or equal to … (1.0).
```

- Quiz : Alarme créée il y a 30 s sur une métrique qui n'a jamais eu de point : dans quel état ?
- [ ] `OK`
- [ ] `ALARM`
- [x] `INSUFFICIENT_DATA`
- Réponse : `INSUFFICIENT_DATA` : toute alarme démarre dans cet état, jusqu'à sa première évaluation avec des données ou une règle de données manquantes.

## 5. period : la taille d'un point
- Id : cloudwatch-period
- Sous-thème : alarmes
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Prérequis : cloudwatch-sum-ou-average
- Mots-clés : métrique, statistique
- Source : data-platform · S1-08
- Définition : `period` (secondes) découpe la métrique en points : chaque point agrège, avec la statistique choisie, ce qui s'est passé pendant la période.
- Contexte : Lambda publie en résolution standard, à la minute : `period` vaut 60 ou un multiple. Une période courte réagit vite mais découpe une même panne en plusieurs points ; une période longue regroupe une panne et ses retries en un seul point. Le choix dépend du rythme du job, pas d'une valeur « standard ».
- Usage : ✅ 60 s, avec `evaluation_periods` pour la durée regardée (15 × 60 s), même pour un job quotidien · ❌ une seule longue période (900 s) sur une métrique rare : l'alarme peut rester bloquée en `ALARM` (mesuré en S1-08).

```python
# Exemple 1 : 3 erreurs, deux découpages
erreurs = [0, 1, 3]   # minutes après 06:00
par_minute = {m // 1 for m in erreurs}
len(par_minute)       # → 3 points à 1
par_15min = {m // 15 for m in erreurs}
len(par_15min)        # → 1 point (Sum 3)
```

```hcl
# Exemple 2 : l'alarme de data-platform
statistic           = "Sum"
period              = 60
evaluation_periods  = 15   # 15 min regardées
datapoints_to_alarm = 1    # une minute en erreur suffit
comparison_operator = "GreaterThanOrEqualToThreshold"
threshold           = 1
```

- Quiz : `period = 60`, erreurs à 06:00:10 et 06:00:50 : combien de points dépassent le seuil 1 ?
- [x] 1, de valeur 2
- [ ] 2, de valeur 1
- [ ] 0 : il faut 60 s d'erreurs
- Réponse : 1, de valeur 2 : les deux erreurs tombent dans la même minute, `Sum` les additionne dans un seul point.

## 6. actions : seulement au changement d'état
- Id : cloudwatch-actions-changement-etat
- Sous-thème : actions
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : sns-topic-fan-out
- Mots-clés : topic SNS, alarme composite
- Source : data-platform · S1-08
- Définition : `alarm_actions` part quand l'alarme passe en `ALARM`, `ok_actions` quand elle revient à `OK` ; rester dans un état ne renvoie rien.
- Contexte : Une alarme évaluée chaque minute ne spamme pas : l'action suit la transition, pas l'évaluation. `ok_actions` donne le mail de retour à la normale, utile pour savoir qu'un rejeu a suffi. `insufficient_data_actions` existe aussi, rarement utile pour un job quotidien. Une action est en général un topic SNS ; le même topic peut servir à toutes les alarmes.
- Usage : ✅ `alarm_actions` + `ok_actions` vers le topic d'alertes · ❌ compter sur un rappel tant que la panne dure : il n'y en a pas, prévoir une revue ou une alarme composite.

```hcl
# Exemple 1 : un mail en panne, un au retour
alarm_actions = [aws_sns_topic.alerts.arn]
ok_actions    = [aws_sns_topic.alerts.arn]
```

- Quiz : L'alarme reste en `ALARM` pendant 3 h. Combien de mails `ALARM` reçus ?
- [ ] 180, un par minute
- [ ] 12, un par période de 15 min
- [x] 1
- [ ] 3, un par heure
- Réponse : 1 : l'action n'est exécutée qu'au passage `OK` → `ALARM`, pas à chaque évaluation.

## 7. get-metric-widget-image : un graphe sans console
- Id : cloudwatch-widget-image
- Sous-thème : graphes
- Type : recette
- Niveau : 1
- Profils : ops
- Voir aussi : cloudwatch-start-iso-8601
- Mots-clés : base64, tableau de bord CloudWatch
- Source : data-platform · S1-09
- Définition : `aws cloudwatch get-metric-widget-image` rend en PNG un graphe décrit en JSON, le même format qu'un widget de tableau de bord.
- Contexte : Une capture de la console montre le numéro de compte et ne se refait pas à l'identique. La définition JSON se commite à côté du PNG : on relance la commande et on obtient le graphe du jour. Lecture seule : aucun tableau de bord n'est créé. La réponse est du JSON dont le champ `MetricWidgetImage` contient le PNG en base64.
- Usage : ✅ livrable, rapport, preuve d'exploitation dans le dépôt · ❌ suivi en direct : un tableau de bord CloudWatch (`aws_cloudwatch_dashboard`).

```bash
# Exemple 1 : définition commitée → PNG
aws cloudwatch get-metric-widget-image \
  --metric-widget file://invocations.json \
  --query MetricWidgetImage \
  --output text | base64 --decode \
  > invocations.png
file invocations.png
# → PNG image data, 1000 x 400
```

```json
# Exemple 2 : invocations.json
{"metrics": [["AWS/Lambda", "Invocations",
  "FunctionName",
  "data-platform-dev-ingest-bodacc"]],
 "start": "-PT24H", "width": 1000}
```

- Quiz : Sans `width` ni `height` dans le JSON, quelle taille fait le PNG ?
- [ ] 1000 × 400
- [x] 600 × 400
- [ ] 800 × 600
- [ ] Erreur : taille obligatoire
- Réponse : 600 × 400 (mesuré dans l'en-tête du PNG) : taille par défaut d'un widget ; `width` et `height` la changent.

## 8. start : une durée ISO 8601
- Id : cloudwatch-start-iso-8601
- Sous-thème : graphes
- Type : concept
- Niveau : 1
- Profils : ops
- Mots-clés : ISO 8601
- Source : data-platform · S1-09
- Définition : `"start": "-PT24H"` fait commencer le graphe 24 heures avant maintenant : une durée ISO 8601 précédée d'un signe moins.
- Contexte : `P` ouvre la durée, `T` sépare les jours des heures : `-P7D` (7 jours), `-PT3H` (3 heures), `-PT15M` (15 minutes). `M` avant `T` voudrait dire mois, après `T` minutes. Une date absolue (`2026-10-25T00:00:00Z`) fige le graphe ; une durée relative le garde à jour à chaque regénération.
- Usage : ✅ graphe « dernières 24 h » regénéré par script · ❌ rapport sur une période précise et passée : `start` et `end` absolus.

```json
# Exemple 1 : trois fenêtres glissantes
{"start": "-PT24H"}
{"start": "-P7D"}
{"start": "-PT15M"}
```

- Quiz : Que couvre `"start": "-P1M"` ?
- [ ] 1 minute
- [x] 1 mois
- [ ] 1 heure
- Réponse : 1 mois : sans `T`, `M` désigne des mois ; 1 minute s'écrit `-PT1M`.

## 9. treat_missing_data : quatre valeurs
- Id : cloudwatch-treat-missing-data
- Sous-thème : données manquantes
- Type : concept
- Niveau : 2
- Profils : ops
- Mots-clés : métrique
- Source : data-platform · S1-08
- Définition : `treat_missing_data` dit comment lire une période sans point : `missing` (défaut), `notBreaching`, `breaching` ou `ignore`.
- Contexte : `notBreaching` : l'absence vaut « dans le seuil ». `breaching` : elle vaut « hors seuil ». `ignore` : l'alarme garde son état. `missing` : si toute la plage évaluée est vide, l'alarme passe en `INSUFFICIENT_DATA`. Le bon choix dépend de ce que signifie l'absence : une métrique qui n'existe que sur événement (`Errors` d'un job) ou un flux continu qui ne devrait jamais s'arrêter.
- Usage : ✅ `notBreaching` pour une métrique d'erreurs intermittente, `breaching` pour un battement de cœur attendu · ❌ laisser le défaut `missing` sur un job quotidien : `INSUFFICIENT_DATA` presque toute la journée.

```python
# Exemple 1 : plage entièrement vide
etat = {"missing": "INSUFFICIENT_DATA",
        "notBreaching": "OK",
        "breaching": "ALARM",
        "ignore": "état précédent"}
etat["notBreaching"]   # → 'OK'
etat["missing"]
# → 'INSUFFICIENT_DATA'  (le défaut)
```

- Quiz : Alarme `Errors` d'un job quotidien avec `treat_missing_data = "breaching"` : quel état la plupart du temps ?
- [ ] `OK`
- [x] `ALARM`
- [ ] `INSUFFICIENT_DATA`
- Réponse : `ALARM` : hors de l'invocation quotidienne, il n'y a aucun point, et chaque absence compte comme un dépassement.

## 10. Errors : un point seulement s'il y a eu invocation
- Id : cloudwatch-errors-sans-invocation
- Sous-thème : données manquantes
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : cloudwatch-treat-missing-data
- Mots-clés : métrique, EventBridge Scheduler, manifest
- Source : data-platform · S1-08
- Définition : Lambda publie `Errors` = 0 sur les périodes où la fonction a tourné ; sans invocation, aucun point, pas même un zéro.
- Contexte : Mesuré : `get-metric-statistics` renvoie 0.0 pour les tranches de 15 min avec invocations, et rien pour les autres. Pour une alarme, l'absence de point est donc l'état normal d'un job planifié, 23 h 59 sur 24 : d'où `notBreaching`. Revers : la même alarme ne voit pas un job qui n'a jamais démarré (schedule désactivée), puisqu'il n'y a ni point ni erreur.
- Usage : ✅ `Errors` + `notBreaching` pour « le job a échoué » · ❌ s'en servir pour « le job n'a pas tourné » : alarme sur `Invocations` avec `breaching`, ou contrôle des manifests.

```bash
# Exemple 1 : seules les tranches actives
aws cloudwatch get-metric-statistics \
  --metric-name Invocations --period 900 \
  --namespace AWS/Lambda --statistics Sum \
  --dimensions Name=FunctionName,Value=$F \
  --start-time 2026-10-25T12:00:00Z \
  --end-time 2026-10-26T00:00:00Z
# → 14:00 1   14:30 1
#   17:30 19  17:45 5
#   (aucun point entre 14:45 et 17:30)
```

- Quiz : La schedule est passée en `DISABLED` par erreur. Que fait l'alarme `Errors` avec `notBreaching` ?
- [ ] Passe en `ALARM` le lendemain
- [ ] Passe en `INSUFFICIENT_DATA`
- [x] Reste `OK` : aucune erreur, aucun point
- Réponse : reste `OK` : sans invocation, pas de point, et l'absence est lue comme normale ; il faut une alarme sur `Invocations` pour voir un job qui ne tourne plus.

## 11. période et retries : le nombre de mails
- Id : cloudwatch-retries-un-seul-mail
- Sous-thème : alarmes
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : cloudwatch-period, cloudwatch-actions-changement-etat
- Voir aussi : lambda-async-deux-retries
- Mots-clés : invocation asynchrone, retry
- Source : data-platform · S1-08
- Définition : Pour qu'une panne et ses retries donnent un seul mail, la durée regardée (`period × evaluation_periods`) doit couvrir l'étalement des retries.
- Contexte : En asynchrone, Lambda réessaie après ~1 min puis ~2 min : trois erreurs étalées sur environ 3 min. Si l'alarme ne regardait qu'une minute, une minute sans erreur pourrait la ramener à `OK` entre deux tentatives. Couvrir 15 min suffit ; mais avec une seule période de 900 s, l'alarme est restée bloquée en `ALARM` (dernier vrai point réévalué). La forme qui marche : 15 périodes de 60 s, 1 sur 15.
- Usage : ✅ `period = 60`, `evaluation_periods = 15`, `datapoints_to_alarm = 1` pour une Lambda asynchrone · ❌ regarder une seule minute (`evaluation_periods = 1`) : une panne peut être découpée en plusieurs paires de mails.

```python
# Exemple 1 : passages en ALARM
# (minutes, fenêtres alignées : simplifié)
def alarmes(erreurs, n, fin=40):
    # ALARM à la minute t si une erreur
    # tombe dans les n dernières minutes
    pts = [any(t - n < e <= t for e in erreurs)
           for t in range(fin)]
    return sum(1 for a, b in
               zip([False] + pts, pts) if b and not a)

essais = [0, 1, 3]   # minutes
alarmes(essais, 1)   # → 2  (n = 1 minute)
alarmes(essais, 15)  # → 1  (1 sur 15)
alarmes([0, 2, 4], 15)
# → 1
```

- Quiz : Erreurs à 0, 2 et 4 min, alarme « 1 sur 15 » de 60 s : combien de passages en `ALARM` (modèle de l'exemple) ?
- [x] 1
- [ ] 2
- [ ] 3
- [ ] 6
- Réponse : 1 : les trois erreurs tombent dans les 15 minutes regardées ; l'alarme reste en `ALARM` jusqu'à la minute 18 (4 + 15 − 1), puis revient à `OK`.

## 12. evaluation_periods et datapoints_to_alarm : M sur N
- Id : cloudwatch-m-sur-n
- Sous-thème : alarmes
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : cloudwatch-period
- Mots-clés : métrique
- Source : data-platform · S1-08
- Définition : `evaluation_periods` (N) fixe combien de points récents on regarde ; `datapoints_to_alarm` (M) combien doivent dépasser pour passer en `ALARM`.
- Contexte : Sans `datapoints_to_alarm`, M vaut N : tous les points évalués doivent dépasser. « 2 sur 3 » tolère un point isolé, utile contre le bruit d'un service continu. Les points en dépassement n'ont pas besoin d'être consécutifs, seulement dans les N derniers. Pour un job quotidien : 1 sur 15 avec des périodes de 60 s (un seul échec est déjà une journée perdue, et 15 périodes courtes laissent l'alarme redescendre).
- Usage : ✅ M sur N pour une latence ou un taux d'erreur bruité · ❌ 3 sur 3 avec `period = 900` sur un job quotidien : il faudrait 45 min d'erreurs continues, l'alarme ne part jamais.

```python
# Exemple 1 : 2 sur 3
def etat(points, m, n, seuil=1):
    derniers = points[-n:]
    hors = sum(1 for p in derniers if p >= seuil)
    return "ALARM" if hors >= m else "OK"

etat([0, 1, 0, 1], m=2, n=3)   # → 'ALARM'
etat([0, 1, 0, 0], m=2, n=3)   # → 'OK'
```

- Quiz : `evaluation_periods = 3` sans `datapoints_to_alarm`, points `[1, 0, 1]` : quel état ?
- [ ] `ALARM` : 2 points sur 3
- [x] `OK` : il en faut 3 sur 3
- [ ] `INSUFFICIENT_DATA`
- Réponse : `OK` : sans `datapoints_to_alarm`, M = N = 3 ; le point à 0 suffit à ne pas déclencher.

## 13. dimension mal écrite : l'alarme muette
- Id : cloudwatch-dimension-mal-ecrite
- Sous-thème : diagnostic
- Type : piège
- Niveau : 2
- Profils : ops
- Voir aussi : cloudwatch-treat-missing-data
- Mots-clés : dimension, output, terraform plan
- Source : data-platform · S1-08
- Définition : Une alarme dont la dimension ne correspond à aucune série surveille une métrique vide : avec `notBreaching`, elle reste `OK` pour toujours.
- Contexte : CloudWatch ne valide ni le nom de métrique ni la valeur de dimension : `FunctionName = "ingest-bodaccc"` est accepté sans erreur, au `plan` comme à l'`apply`. Avec `missing`, on verrait `INSUFFICIENT_DATA` ; avec `notBreaching`, tout paraît sain. D'où la dimension lue dans l'output du module (`module.lambda[k].function_name`), jamais tapée, et un vrai test de l'alarme.
- Usage : ✅ dimension issue d'une référence Terraform, test de bout en bout (étape 7) · ❌ nom de fonction écrit à la main dans `dimensions`.

```hcl
# Exemple 1 : la valeur vient du module
dimensions = {
  FunctionName = module.lambda[each.key].function_name
}
# ❌ FunctionName = "data-platform-dev-ingest-bodaccc"
#   accepté, ne surveille rien
```

- Quiz : Alarme `notBreaching` sur une fonction au nom mal tapé ; la vraie fonction échoue. Quel état ?
- [ ] `ALARM`
- [x] `OK`
- [ ] `INSUFFICIENT_DATA`
- [ ] Erreur à la création de l'alarme
- Réponse : `OK` : la série surveillée n'a aucun point, lu comme « dans le seuil » ; les erreurs vont dans une autre série.

## 14. alarm_description : le runbook dans le mail
- Id : cloudwatch-alarm-description-runbook
- Sous-thème : actions
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : cloudwatch-actions-changement-etat
- Mots-clés : topic SNS, runbook
- Source : data-platform · S1-08
- Définition : `alarm_description` est recopiée telle quelle dans le message envoyé au topic : y écrire quoi regarder et quoi lancer.
- Contexte : Le message SNS d'une alarme est un JSON qui porte `AlarmName`, `AlarmDescription`, `NewStateValue`, `NewStateReason` et le `Trigger` (métrique, seuil, période). Celui qui reçoit le mail à 7 h n'a pas le code sous les yeux : la description lui donne la commande de logs et le rattrapage (`make replay`). Limite : 1 024 caractères.
- Usage : ✅ commande de diagnostic + commande de reprise, interpolées par Terraform · ❌ description vide ou qui répète le nom de l'alarme.

```python
# Exemple 1 : le message reçu (extrait)
import json
msg = json.loads('''{
  "AlarmName": "dp-dev-ingest-bodacc-errors",
  "NewStateValue": "ALARM",
  "AlarmDescription": "lire aws logs tail …, puis make replay",
  "Trigger": {"MetricName": "Errors", "Period": 60}}''')
msg["NewStateValue"]          # → 'ALARM'
msg["Trigger"]["Period"]      # → 60
```

- Quiz : Quel champ du message dit si c'est une panne ou un retour à la normale ?
- [ ] `AlarmDescription`
- [x] `NewStateValue`
- [ ] `Trigger.Threshold`
- [ ] `AlarmName`
- Réponse : `NewStateValue` : `ALARM` ou `OK` (avec `OldStateValue`) ; la description est fixe, elle ne change pas d'un message à l'autre.

## 15. describe-alarm-history : qui a changé et quand
- Id : cloudwatch-historique-alarme
- Sous-thème : diagnostic
- Type : recette
- Niveau : 2
- Profils : ops
- Voir aussi : cloudwatch-state-reason
- Mots-clés : topic SNS, terraform apply
- Source : data-platform · S1-08
- Définition : `describe-alarm-history` liste les événements d'une alarme : changements d'état, exécutions d'actions, modifications de configuration.
- Contexte : `--history-item-type StateUpdate` montre les passages `OK` ↔ `ALARM` avec leur date ; `Action` montre si la publication SNS a réussi ou échoué ; `ConfigurationUpdate` trace les `apply`. C'est la première commande quand un mail n'est pas arrivé : l'alarme a-t-elle changé d'état, l'action est-elle partie ? L'historique est gardé 30 jours.
- Usage : ✅ « ai-je été prévenu, et quand ? », preuve d'un test d'alarme · ❌ chercher la cause de l'erreur : elle est dans les logs de la Lambda.

```bash
# Exemple 1 : le premier passage
aws cloudwatch describe-alarm-history \
  --alarm-name "$A" \
  --history-item-type StateUpdate \
  --query 'AlarmHistoryItems[].[Timestamp,
    HistorySummary]' --output text
# → 2026-10-25T18:12:11 Alarm updated
#   from INSUFFICIENT_DATA to OK
```

- Quiz : L'alarme est passée en `ALARM` mais aucun mail n'est arrivé. Quel type d'historique regarder d'abord ?
- [ ] `StateUpdate`
- [x] `Action`
- [ ] `ConfigurationUpdate`
- Réponse : `Action` : il dit si la publication vers le topic a réussi ; si oui, chercher du côté de l'abonnement (non confirmé, spams).

## 16. set-alarm-state : tester le chemin du mail
- Id : cloudwatch-set-alarm-state
- Sous-thème : diagnostic
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : cloudwatch-actions-changement-etat
- Mots-clés : abonnement SNS, dimension, handler
- Source : data-platform · S1-08
- Définition : `aws cloudwatch set-alarm-state` force un état pour déclencher ses actions ; l'évaluation suivante remet l'état réel.
- Contexte : Il teste le seul chemin alarme → SNS → mail, pas la métrique : une dimension fausse passerait ce test. L'état forcé ne dure que jusqu'à la prochaine évaluation (environ une minute) : on reçoit donc souvent `ALARM` puis `OK`. Pour prouver toute la chaîne, provoquer une vraie erreur du handler, puis compléter par ce test si le mail n'arrive pas.
- Usage : ✅ vérifier un abonnement ou une politique de topic, démonstration · ❌ seule preuve qu'une alarme marche : elle ne regarde jamais la métrique.

```bash
# Exemple 1 : forcer, puis observer
aws cloudwatch set-alarm-state \
  --alarm-name "$A" \
  --state-value ALARM \
  --state-reason "test du mail"
# → mail ALARM, puis à l'évaluation
#   suivante (sans erreur) : mail OK
```

- Quiz : Ce test réussit (mail reçu). Qu'est-ce qu'il ne prouve pas ?
- [ ] Que l'abonnement est confirmé
- [ ] Que le topic accepte CloudWatch
- [x] Que l'alarme regarde la bonne série
- Réponse : la bonne série : l'état est forcé sans lire la métrique ; une dimension mal écrite ne se voit qu'avec une vraie erreur.

## 17. for_each : une alarme par Lambda
- Id : cloudwatch-alarme-par-lambda
- Sous-thème : alarmes
- Type : recette
- Niveau : 2
- Profils : ops
- Voir aussi : Terraform/langage-hcl-for-each-map-de-config
- Mots-clés : for_each, module Terraform
- Source : data-platform · S1-08
- Définition : `aws_cloudwatch_metric_alarm` avec `for_each = local.lambdas` crée une alarme par fonction, au même endroit que leur déclaration.
- Contexte : Ajouter une Lambda à `local.lambdas` lui donne fonction, rôle, logs, retries (module) et alarme, sans rien oublier. Le nom suit la clé (`${local.prefix}-<clé>-errors`), la dimension vient de l'output du module. Une alarme coûte environ 0,10 $ par mois en résolution standard : négligeable face au coût d'une journée perdue sans le savoir.
- Usage : ✅ alarme générée pour toute ressource d'une famille (Lambdas, files, jobs) · ❌ alarmes écrites une par une : la prochaine Lambda en aura une à moitié ou pas du tout.

```hcl
# Exemple 1 : une par entrée
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each   = local.lambdas
  alarm_name = "${local.prefix}-${each.key}-errors"
  dimensions = {
    FunctionName = module.lambda[each.key].function_name
  }
}
```

- Quiz : On ajoute `normalize = {…}` à `local.lambdas`. Que montre `make plan` pour les alarmes ?
- [ ] Rien : il faut ajouter une ressource
- [x] Une alarme `…-normalize-errors` à créer
- [ ] L'alarme existante remplacée
- Réponse : une alarme à créer : `for_each` ajoute une instance par nouvelle clé, sans toucher à celle d'`ingest-bodacc`.

## 18. Errors = 0 : une invocation réussie débloque l'alarme
- Id : cloudwatch-invocation-debloque-alarme
- Sous-thème : données manquantes
- Type : piège
- Niveau : 2
- Profils : ops, expert
- Prérequis : cloudwatch-errors-sans-invocation
- Voir aussi : cloudwatch-alarme-bloquee-alarm
- Mots-clés : rejeu, métrique
- Source : data-platform · S1-08
- Définition : Une invocation réussie publie un point `Errors = 0` ; devenu le point le plus récent, il ramène l'alarme à `OK`.
- Contexte : `Errors` n'a de points que pendant les minutes où la fonction a tourné : 0 si tout va bien, ≥ 1 sinon. Sans invocation, il n'y a rien. Mesuré : alarme bloquée en `ALARM` depuis 18:17 sur l'erreur, un `make replay` réussi vers 18:40, retour `OK` à 18:41:11 avec la raison « 1 datapoint [0.0] was not greater than or equal to the threshold ». Le temps seul ne l'avait pas fait.
- Usage : ✅ comprendre pourquoi le rejeu « répare » aussi l'alarme · ❌ s'en servir comme réglage : une alarme doit redescendre seule (périodes courtes, 1 sur 15).

```python
# Exemple 1 : le point le plus récent décide
points = [1, None, None, 0]  # erreur, rien, rien, succès
vrais = [p for p in points if p is not None]
vrais[-1]                     # → 0
"ALARM" if vrais[-1] >= 1 else "OK"
# → 'OK'
```

- Quiz : Même alarme bloquée, mais le rejeu échoue lui aussi : que publie-t-il ?
- [ ] Rien : un échec ne publie pas de point
- [x] Un point `Errors = 1`
- [ ] Un point `Errors = 0` et un point `Throttles = 1`
- Réponse : `Errors = 1` : une invocation en erreur compte dans `Errors` ; l'alarme reste en `ALARM`, sans nouveau mail (pas de changement d'état).

## 19. StateReason : lire pourquoi l'alarme a changé
- Id : cloudwatch-state-reason
- Sous-thème : diagnostic
- Type : recette
- Niveau : 2
- Profils : ops
- Mots-clés : métrique, UTC
- Source : data-platform · S1-08
- Définition : `StateReason` (dans le mail et `describe-alarms`) dit sur quels points l'alarme a décidé : valeur, date du point, ou points manquants.
- Contexte : Mesuré : `Threshold Crossed: 1 datapoint [1.0 (17:02:00)]` lors d'une erreur à 17:16 UTC, la date est le début de la période qui contient l'erreur, pas l'heure de l'erreur. `1 datapoint [0.0 …]` : un vrai point sain a ramené `OK`. `no datapoints were received for 15 periods and 15 missing datapoints were treated as [NonBreaching]` : retour `OK` par absence de données.
- Usage : ✅ distinguer un retour `OK` par succès d'un retour par silence, dater une panne · ❌ lire la date du point comme l'heure exacte de l'erreur.

```bash
# Exemple 1 : la raison du dernier changement
aws cloudwatch describe-alarms \
  --alarm-names data-platform-dev-ingest-bodacc-errors \
  --query 'MetricAlarms[0].StateReason' \
  --output text --profile data-platform
# → Threshold Crossed: no datapoints were
#   received for 15 periods and 15 missing
#   datapoints were treated as [NonBreaching].
```

- Quiz : Période de 900 s, point annoncé `[1.0 (06:00:00)]` : quand l'erreur a-t-elle eu lieu ?
- [ ] À 06:00:00 exactement
- [x] Entre 06:00 et 06:15
- [ ] Entre 05:45 et 06:00
- [ ] Au moment du mail
- Réponse : entre 06:00 et 06:15 : un point est daté du début de sa période ; l'erreur est quelque part dans les 15 minutes qui suivent.

## 20. tester une alarme : une vraie erreur sans effet de bord
- Id : cloudwatch-tester-alarme-vraie-erreur
- Sous-thème : diagnostic
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : cloudwatch-set-alarm-state
- Mots-clés : handler, invocation synchrone, partition
- Source : data-platform · S1-08
- Définition : Tester une alarme de bout en bout : provoquer une vraie erreur du handler, qui échoue avant toute écriture, sans casser source ni droits.
- Contexte : Ici, une date future (`{"date": "2099-01-01"}`) : `resolve_day` lève `ValueError` à la première ligne, rien n'est lu ni écrit dans S3, et `Errors` compte l'échec comme une vraie panne. En synchrone (`aws lambda invoke`), pas de retry : une erreur, un mail. `set-alarm-state` ne teste que le chemin SNS → mail, pas la métrique ni la dimension. Après le test, ne pas réinvoquer avant le retour à `OK`.
- Usage : ✅ entrée invalide refusée par la validation de l'event · ❌ couper le réseau, retirer un droit IAM, ou tester sur un jour réel : effets de bord et partition partielle possible.

```python
# Exemple 1 : refusée avant tout appel
from datetime import date

def resolve_day(event, today=date(2026, 10, 25)):
    day = date.fromisoformat(event["date"])
    if day >= today:
        raise ValueError(f"{day} n'est pas terminée")
    return day

resolve_day({"date": "2099-01-01"})  # ❌ ValueError
```

- Quiz : Même test, mais invoqué avec `--invocation-type Event` : combien d'erreurs dans `Errors` ?
- [ ] 1
- [ ] 2
- [x] 3
- [ ] 185
- Réponse : 3 : en asynchrone, l'essai et ses 2 nouvelles tentatives (`async_retry`) échouent chacun ; les 185 de Scheduler ne concernent que la livraison.

## 21. widget : "." recopie la ligne du dessus
- Id : cloudwatch-widget-point-recopie
- Sous-thème : graphes
- Type : concept
- Niveau : 2
- Profils : ops
- Mots-clés : espace de noms CloudWatch, dimension, métrique
- Source : data-platform · S1-09
- Définition : Dans `metrics` d'un widget, `"."` reprend la valeur à la même position dans la ligne précédente : espace de noms, nom de dimension, valeur.
- Contexte : Deux séries de la même fonction ne diffèrent que par le nom de métrique : `[".", "Errors", ".", "."]` évite de répéter `AWS/Lambda`, `FunctionName` et le nom de la fonction. Le dernier élément d'une ligne peut être un objet d'options (`label`, `color`, `stat`), propre à cette série.
- Usage : ✅ plusieurs métriques d'une même ressource sur un graphe · ❌ ressources différentes : écrire chaque ligne en entier, sinon le `"."` recopie la mauvaise valeur.

```json
# Exemple 1 : invocations et erreurs
"metrics": [
  ["AWS/Lambda", "Invocations",
   "FunctionName", "data-platform-dev-ingest-bodacc",
   {"label": "Invocations"}],
  [".", "Errors", ".", ".",
   {"label": "Errors", "color": "#d62728"}]
]
```

- Quiz : Dans l'exemple, que vaut le 3e élément de la ligne `Errors` une fois résolu ?
- [ ] `"AWS/Lambda"`
- [x] `"FunctionName"`
- [ ] `"data-platform-dev-ingest-bodacc"`
- [ ] `"."`
- Réponse : `"FunctionName"` : chaque `"."` recopie l'élément à la même position de la ligne au-dessus.

## 22. widget : l'axe en UTC par défaut
- Id : cloudwatch-widget-utc
- Sous-thème : graphes
- Type : piège
- Niveau : 2
- Profils : ops
- Mots-clés : UTC, rejeu
- Source : data-platform · S1-09
- Définition : Un graphe rendu par `get-metric-widget-image` affiche ses heures en UTC, sauf si le JSON précise `"timezone": "+0100"`.
- Contexte : Mesuré : le rejeu lancé vers 17:30 à Paris apparaissait en pic à 16:30 ; avec `"timezone": "+0100"`, l'axe et le pic se recalent. Le fuseau est un décalage fixe, pas `Europe/Paris` : il ne suit pas l'heure d'été, `+0200` en été. La console, elle, affiche souvent l'heure locale du navigateur : les deux ne coïncident pas.
- Usage : ✅ graphe destiné à un lecteur qui raisonne en heure de Paris · ❌ comparer avec des logs ou des dates UTC (`fetched_at`) : garder l'UTC.

```json
# Exemple 1 : axe à l'heure de Paris (hiver)
{"timezone": "+0100",
 "start": "-PT24H",
 "metrics": [["AWS/Lambda", "Invocations",
   "FunctionName", "data-platform-dev-ingest-bodacc"]]}
# sans timezone : pic à 16:30 ; avec : 17:30
```

- Quiz : En juillet, quelle valeur de `timezone` met l'axe à l'heure de Paris ?
- [ ] `"+0100"`
- [x] `"+0200"`
- [ ] `"Europe/Paris"`
- Réponse : `"+0200"` : l'heure d'été de Paris est UTC+2 ; `"Europe/Paris"` est refusé (mesuré : `ValidationError`, le champ attend un décalage `+HHMM`).

## 23. fenêtre glissante : évaluée chaque minute
- Id : cloudwatch-fenetre-glissante
- Sous-thème : alarmes
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Prérequis : cloudwatch-m-sur-n
- Mots-clés : métrique, latence
- Source : data-platform · S1-08
- Définition : Une alarme est évaluée chaque minute sur les dernières `period × evaluation_periods` secondes : la fenêtre glisse, sans alignement sur l'horloge.
- Contexte : Avec 15 périodes de 60 s, l'évaluation de 06:05 regarde 05:50 → 06:05, celle de 06:06 regarde 05:51 → 06:06. Une erreur à 06:00 maintient `ALARM` jusqu'à sa sortie des 15 minutes, puis `OK` (mesuré : 21 min après la dernière erreur, latence comprise). Piège : CloudWatch lit une plage plus large ; avec une seule période de 900 s, la sortie de fenêtre n'a pas suffi. Option : fenêtre « horloge ». Au-delà d'un jour, évaluation horaire.
- Usage : ✅ prévoir le délai du mail `OK` (≈ 15 min + quelques minutes de latence après la dernière erreur) · ❌ compter sur la sortie de fenêtre avec `evaluation_periods = 1` : voir « dernier vrai point réévalué ».

```python
# Exemple 1 : quand revient OK ?
from datetime import datetime, timedelta

derniere_erreur = datetime(2026, 10, 26, 6, 3)
fenetre = timedelta(seconds=60) * 15
(derniere_erreur + fenetre).strftime("%H:%M")
# → '06:18'  (+ latence : OK vers 06:20)
```

- Quiz : Fenêtre totale de 2 jours (`period` 86400, 2 périodes) : à quelle fréquence l'alarme est-elle évaluée ?
- [ ] Chaque minute
- [ ] Chaque période, une fois par jour
- [x] Une fois par heure
- Réponse : une fois par heure (doc CloudWatch) : au-delà d'un jour de fenêtre, l'alarme ne prend en compte les données que jusqu'à l'heure pleine.

## 24. Errors : daté du début de l'invocation
- Id : cloudwatch-errors-date-debut
- Sous-thème : métriques
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : cloudwatch-period
- Mots-clés : invocation, timeout
- Source : data-platform · S1-08
- Définition : Le point `Errors` d'une invocation porte l'horodatage de son début, pas celui de l'erreur.
- Contexte : Une invocation lancée à 06:00 qui échoue au bout de 4 min 50 (timeout de 300 s) ajoute son 1 à la minute 06:00. Le point arrive donc « dans le passé » : une alarme à période courte peut l'avoir déjà évaluée sans lui, et ne le voir qu'à l'évaluation suivante. Une fenêtre regardée de 15 min (60 s × 15) absorbe ce décalage.
- Usage : ✅ fenêtre regardée (`period × evaluation_periods`) plus longue que la durée maximale de la fonction · ❌ fenêtre d'une minute (60 s × 1) sur une fonction qui tourne plusieurs minutes : point compté hors de la fenêtre attendue.

```python
# Exemple 1 : où tombe le point
from datetime import datetime, timedelta

debut = datetime(2026, 10, 26, 6, 0, 5)
erreur = debut + timedelta(seconds=290)
erreur.strftime("%H:%M")              # → '06:04'
debut.replace(second=0).strftime("%H:%M")
# → '06:00'  (minute du point Errors)
```

- Quiz : Fonction de 5 min qui échoue à la fin, `period = 60` : dans quelle minute le point `Errors` apparaît-il ?
- [x] La minute du début
- [ ] La minute de l'erreur
- [ ] Les deux, à 0,5 chacune
- Réponse : la minute du début : la doc Lambda précise que l'horodatage reflète l'invocation, pas le moment de l'erreur.

## 25. Duration : sans le démarrage à froid
- Id : cloudwatch-duration-sans-init
- Sous-thème : métriques
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Voir aussi : lambda-ligne-report, lambda-cold-start-init
- Mots-clés : handler, démarrage à froid, percentile, ligne REPORT
- Source : data-platform · S1-08
- Définition : La métrique `Duration` mesure le temps du handler seul ; le démarrage à froid (`Init Duration`) n'y figure pas.
- Contexte : Une alarme « trop lent » sur `Duration` ignore donc l'init, qui peut pourtant être facturée : mesuré en S1-07, `Billed Duration` 5 520 ms pour `Duration` 4 563 ms et `Init Duration` 956 ms. Pour suivre le vrai coût ou le temps vu par l'appelant, lire les lignes `REPORT`. `Duration` accepte les percentiles (`p95`), plus parlants que `Average`.
- Usage : ✅ `Duration` `p95` ou `Maximum` pour approcher le timeout · ❌ calculer la facture depuis `Duration` : `Billed Duration` des lignes `REPORT`.

```python
# Exemple 1 : REPORT de S1-07 (mesuré)
duration, init, billed = 4563.27, 956.27, 5520
round(duration + init)   # → 5520 (≈ billed)
duration < billed        # → True
```

- Quiz : Alarme `Duration Maximum > 280000` (timeout 300 s). Une invocation à froid : 2 s d'init, 279 s de handler. L'alarme part-elle ?
- [ ] Oui : 281 s au total
- [x] Non : `Duration` vaut 279 s
- [ ] Oui, mais seulement à froid
- Réponse : non : `Duration` exclut l'init ; seul le temps du handler (279 s) est comparé au seuil.

## 26. AsyncEventsDropped : l'événement abandonné
- Id : cloudwatch-async-events-dropped
- Sous-thème : métriques
- Type : concept
- Niveau : 3
- Profils : data, ops, expert
- Prérequis : lambda-async-deux-retries
- Voir aussi : lambda-destinations-ou-dlq
- Mots-clés : invocation asynchrone, DLQ, concurrence réservée, throttling
- Source : data-platform · S1-08
- Définition : `AsyncEventsDropped` compte les événements asynchrones abandonnés sans exécution réussie : retries épuisés, âge maximal dépassé, ou concurrence réservée à 0.
- Contexte : `Errors` dit « une tentative a échoué » ; `AsyncEventsDropped` dit « l'événement est perdu », après les retries (2 tentatives, 1 h ici). Pour un job quotidien, c'est la vraie journée manquante. Avec une destination `OnFailure` ou une DLQ, l'événement y part avant d'être abandonné. `AsyncEventAge` qui grimpe signale des retries ou du throttling en cours.
- Usage : ✅ alarme « journée perdue » en complément d'`Errors`, file d'attente qui grossit (`AsyncEventAge`) · ❌ s'en servir pour un appel synchrone (`make replay`) : il n'y a pas d'événement en file.

```python
# Exemple 1 : trois tentatives, un abandon
tentatives = ["échec", "échec", "échec"]
errors = sum(t == "échec" for t in tentatives)
dropped = int(all(t == "échec"
                  for t in tentatives))
(errors, dropped)   # → (3, 1)
```

- Quiz : Le 2e retry réussit après deux échecs. Que valent `Errors` et `AsyncEventsDropped` ?
- [ ] 2 et 1
- [x] 2 et 0
- [ ] 0 et 0
- [ ] 3 et 1
- Réponse : 2 et 0 : deux tentatives ont échoué, mais l'événement a fini par réussir, il n'est pas abandonné.

## 27. plage d'évaluation : plus large que evaluation_periods
- Id : cloudwatch-plage-evaluation
- Sous-thème : données manquantes
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Prérequis : cloudwatch-m-sur-n
- Mots-clés : métrique
- Source : data-platform · S1-08
- Définition : À chaque évaluation, CloudWatch lit plus de points que `evaluation_periods` (la plage d'évaluation), pour combler les trous avec de vrais points plus anciens.
- Contexte : Doc *alarms-and-missing-data* : s'il y a assez de vrais points dans la plage (au moins `evaluation_periods`), l'alarme décide sur les plus récents d'entre eux et `treat_missing_data` est ignoré. Sinon seulement, les trous sont complétés (`notBreaching` → dans le seuil). La taille exacte de la plage dépend de la période et n'est pas réglable. Vaut pour la fenêtre glissante (par défaut), pas pour la fenêtre « horloge ».
- Usage : ✅ `evaluation_periods` grand (15) sur une métrique rare : peu de vrais points, les trous jouent · ❌ `evaluation_periods = 1` : un seul vrai point ancien suffit, `notBreaching` n'entre jamais en jeu.

```python
# Exemple 1 : la règle, simplifiée
def etat(points, n, plage, seuil=1):
    vus = points[-plage:]
    vrais = [p for p in vus if p is not None]
    if len(vrais) >= n:
        evalues = vrais[-n:]   # derniers VRAIS
    else:                      # trous = notBreaching
        evalues = [p or 0 for p in vus[-n:]]
    return "ALARM" if any(p >= seuil for p in evalues) else "OK"

etat([1, None, None], n=1, plage=3)       # → 'ALARM'
etat([1] + [None] * 15, n=15, plage=20)   # → 'OK'
```

- Quiz : Modèle de l'exemple, `n=15`, points `[1] + [None] * 10` : quel état ?
- [x] `ALARM`
- [ ] `OK`
- [ ] `INSUFFICIENT_DATA`
- Réponse : `ALARM` : un seul vrai point, donc trous complétés, mais l'erreur est encore dans les 15 derniers points.

## 28. dernier vrai point réévalué : l'alarme bloquée en ALARM
- Id : cloudwatch-alarme-bloquee-alarm
- Sous-thème : données manquantes
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : cloudwatch-plage-evaluation, cloudwatch-treat-missing-data
- Mots-clés : métrique
- Source : data-platform · S1-08
- Définition : Sur une métrique qui ne publie plus, une alarme à une seule période peut réévaluer indéfiniment son dernier vrai point, et rester en `ALARM`.
- Contexte : Mesuré en S1-08 : `period = 900`, `evaluation_periods = 1`, `notBreaching` ; erreur à 18:16, `ALARM` à 18:17, toujours `ALARM` à 18:40 alors que l'erreur était sortie de la période. Le seul vrai point de la plage, l'erreur, suffisait (1 ≥ 1). Doc : « might repeatedly re-evaluate the last set of data points… use shorter periods ». Correctif mesuré : 60 s × 15, 1 sur 15 → `OK` seul en 20 min.
- Usage : ✅ métrique d'erreurs rare : périodes de 60 s, `evaluation_periods` 15, `datapoints_to_alarm` 1 · ❌ une seule longue période avec `notBreaching` en croyant que « pas de point = OK ».

```hcl
# Exemple 1 : avant / après (data-platform)
# avant : bloquée en ALARM
period             = 900
evaluation_periods = 1
# après : OK seule 15 min après l'erreur
period              = 60
evaluation_periods  = 15
datapoints_to_alarm = 1
treat_missing_data  = "notBreaching"
```

- Quiz : Ancien réglage (900 s × 1), panne à 06:00, aucune invocation jusqu'au lendemain 06:00 : quel risque ?
- [ ] Aucun : `OK` à 06:15
- [x] Rester en `ALARM` longtemps : pas de mail à la panne suivante
- [ ] Un mail `ALARM` toutes les 15 min
- [ ] `INSUFFICIENT_DATA` toute la nuit
- Réponse : rester en `ALARM` longtemps (mesuré : 23 min et plus, sans fin observée) : les actions ne partent qu'au changement d'état, une nouvelle panne pendant ce temps ne déclencherait aucun mail.
