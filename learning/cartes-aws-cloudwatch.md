---
title: "Cartes · CloudWatch"
type: cartes
langage: AWS
cours: CloudWatch
created: 2026-10-25
updated: 2026-10-25
---

# Cartes · CloudWatch
AWS · CloudWatch : métriques, alarmes, données manquantes, actions, diagnostic (format spec v3 de revision-pwa).

## 1. métriques Lambda : publiées sans code
- Sous-thème : métriques
- Niveau : 1
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
- Sous-thème : métriques
- Niveau : 1
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
- Sous-thème : métriques
- Niveau : 1
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
- Sous-thème : alarmes
- Niveau : 1
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
- Sous-thème : alarmes
- Niveau : 1
- Source : data-platform · S1-08
- Définition : `period` (secondes) découpe la métrique en points : chaque point agrège, avec la statistique choisie, ce qui s'est passé pendant la période.
- Contexte : Lambda publie en résolution standard, à la minute : `period` vaut 60 ou un multiple. Une période courte réagit vite mais découpe une même panne en plusieurs points ; une période longue regroupe une panne et ses retries en un seul point. Le choix dépend du rythme du job, pas d'une valeur « standard ».
- Usage : ✅ 60 s pour un service continu, 900 s pour un job quotidien avec retries · ❌ une période plus courte que la résolution de la métrique : points vides.

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
period              = 900
evaluation_periods  = 1
comparison_operator = "GreaterThanOrEqualToThreshold"
threshold           = 1
```

- Quiz : `period = 60`, erreurs à 06:00:10 et 06:00:50 : combien de points dépassent le seuil 1 ?
- [x] 1, de valeur 2
- [ ] 2, de valeur 1
- [ ] 0 : il faut 60 s d'erreurs
- Réponse : 1, de valeur 2 : les deux erreurs tombent dans la même minute, `Sum` les additionne dans un seul point.

## 6. actions : seulement au changement d'état
- Sous-thème : actions
- Niveau : 1
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

## 7. treat_missing_data : quatre valeurs
- Sous-thème : données manquantes
- Niveau : 2
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

## 8. Errors : un point seulement s'il y a eu invocation
- Sous-thème : données manquantes
- Niveau : 2
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

## 9. période et retries : le nombre de mails
- Sous-thème : alarmes
- Niveau : 2
- Source : data-platform · S1-08
- Définition : Une période plus courte que l'étalement des retries découpe une seule panne en plusieurs passages `ALARM` / `OK`, donc plusieurs paires de mails.
- Contexte : En asynchrone, Lambda réessaie après ~1 min puis ~2 min : trois erreurs étalées sur environ 3 min. Avec `period = 60` et `notBreaching`, chaque minute sans erreur ramène l'alarme à `OK`, puis l'erreur suivante la renvoie en `ALARM`. Une période de 15 min couvre les trois tentatives : une panne, un mail `ALARM`, un mail `OK`.
- Usage : ✅ période ≥ fenêtre des retries pour un job unique · ❌ `period = 60` sur une Lambda asynchrone : jusqu'à six mails pour un seul jour raté.

```python
# Exemple 1 : passages en ALARM
# (minutes, fenêtres alignées : simplifié)
def alarmes(erreurs, period, fin=20):
    pts = [any(t // period == p for t in erreurs)
           for p in range(fin // period + 1)]
    return sum(1 for a, b in
               zip([False] + pts, pts) if b and not a)

essais = [0, 1, 3]   # minutes
alarmes(essais, 1)   # → 2
alarmes(essais, 15)  # → 1
```

- Quiz : Retries plus espacés, erreurs à 0, 2 et 4 min, `period = 60` : combien de passages en `ALARM` ?
- [ ] 1
- [ ] 2
- [x] 3
- [ ] 6
- Réponse : 3 : chaque minute sans erreur (1 et 3) ramène l'alarme à `OK`, chaque erreur la renvoie en `ALARM` ; soit six mails.

## 10. evaluation_periods et datapoints_to_alarm : M sur N
- Sous-thème : alarmes
- Niveau : 2
- Source : data-platform · S1-08
- Définition : `evaluation_periods` (N) fixe combien de points récents on regarde ; `datapoints_to_alarm` (M) combien doivent dépasser pour passer en `ALARM`.
- Contexte : Sans `datapoints_to_alarm`, M vaut N : tous les points évalués doivent dépasser. « 2 sur 3 » tolère un point isolé, utile contre le bruit d'un service continu. Les points en dépassement n'ont pas besoin d'être consécutifs, seulement dans les N derniers. Pour un job quotidien, 1 sur 1 suffit : un seul échec est déjà une journée perdue.
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

## 11. dimension mal écrite : l'alarme muette
- Sous-thème : diagnostic
- Niveau : 2
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

## 12. alarm_description : le runbook dans le mail
- Sous-thème : actions
- Niveau : 2
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
  "Trigger": {"MetricName": "Errors", "Period": 900}}''')
msg["NewStateValue"]          # → 'ALARM'
msg["Trigger"]["Period"]      # → 900
```

- Quiz : Quel champ du message dit si c'est une panne ou un retour à la normale ?
- [ ] `AlarmDescription`
- [x] `NewStateValue`
- [ ] `Trigger.Threshold`
- [ ] `AlarmName`
- Réponse : `NewStateValue` : `ALARM` ou `OK` (avec `OldStateValue`) ; la description est fixe, elle ne change pas d'un message à l'autre.

## 13. describe-alarm-history : qui a changé et quand
- Sous-thème : diagnostic
- Niveau : 2
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

## 14. set-alarm-state : tester le chemin du mail
- Sous-thème : diagnostic
- Niveau : 2
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

## 15. for_each : une alarme par Lambda
- Sous-thème : alarmes
- Niveau : 2
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

## 16. fenêtre glissante : évaluée chaque minute
- Sous-thème : alarmes
- Niveau : 3
- Source : data-platform · S1-08
- Définition : Une alarme est évaluée chaque minute sur les dernières `period × evaluation_periods` secondes : la fenêtre glisse, sans alignement sur l'horloge.
- Contexte : Avec `period = 900`, l'évaluation de 06:05 regarde 05:50 → 06:05, celle de 06:06 regarde 05:51 → 06:06. Une erreur à 06:00 maintient donc `ALARM` jusqu'à ce qu'elle sorte de la fenêtre, environ 15 min plus tard, puis `OK`. Une fenêtre « horloge » (alignée, avec fuseau) existe en option. Au-delà d'un jour de fenêtre totale, l'évaluation n'a lieu qu'une fois par heure.
- Usage : ✅ prévoir le délai du mail `OK` (≈ une période après la dernière erreur) · ❌ attendre un `OK` à la minute où le rejeu réussit.

```python
# Exemple 1 : quand revient OK ?
from datetime import datetime, timedelta

derniere_erreur = datetime(2026, 10, 26, 6, 3)
period = timedelta(seconds=900)
(derniere_erreur + period).strftime("%H:%M")
# → '06:18'  (≈ retour à OK)
```

- Quiz : Fenêtre totale de 2 jours (`period` 86400, 2 périodes) : à quelle fréquence l'alarme est-elle évaluée ?
- [ ] Chaque minute
- [ ] Chaque période, une fois par jour
- [x] Une fois par heure
- Réponse : une fois par heure (doc CloudWatch) : au-delà d'un jour de fenêtre, l'alarme ne prend en compte les données que jusqu'à l'heure pleine.

## 17. Errors : daté du début de l'invocation
- Sous-thème : métriques
- Niveau : 3
- Source : data-platform · S1-08
- Définition : Le point `Errors` d'une invocation porte l'horodatage de son début, pas celui de l'erreur.
- Contexte : Une invocation lancée à 06:00 qui échoue au bout de 4 min 50 (timeout de 300 s) ajoute son 1 à la minute 06:00. Le point arrive donc « dans le passé » : une alarme à période courte peut l'avoir déjà évaluée sans lui, et ne le voir qu'à l'évaluation suivante. Avec une période de 15 min, le décalage est absorbé.
- Usage : ✅ période supérieure à la durée maximale de la fonction · ❌ `period = 60` sur une fonction qui tourne plusieurs minutes : alarme en retard ou point compté hors de la fenêtre attendue.

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

## 18. Duration : sans le démarrage à froid
- Sous-thème : métriques
- Niveau : 3
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

## 19. AsyncEventsDropped : l'événement abandonné
- Sous-thème : métriques
- Niveau : 3
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
