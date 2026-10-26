---
title: "Cartes · Step Functions"
type: cartes
langage: AWS
chapitre: Calcul
cours: Step Functions
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Step Functions
AWS · Step Functions : erreurs, choisir, intégrations (format spec v4 de revision-pwa).

## 1. Step Functions : Retry et backoff
- Id : step-functions-retry-backoff
- Sous-thème : erreurs
- Type : concept
- Niveau : 1
- Profils : débutant, data, ops
- Voir aussi : dynamodb-backoff-jitter
- Mots-clés : backoff exponentiel, machine d'états
- Définition : `Retry` relance un état sur les erreurs listées, avec une attente initiale multipliée par `BackoffRate` à chaque nouvel essai.
- Contexte : Sans `Retry`, la première erreur fait échouer l'état puis l'exécution. `MaxAttempts` vaut 3 par défaut (0 = jamais), `IntervalSeconds` 1, `BackoffRate` 2. Une fois les retries épuisés, l'état échoue, sauf si un `Catch` le route ailleurs. L'orchestrateur porte ainsi la logique de reprise, pas le code de la Lambda.
- Usage : ✅ erreurs transitoires (429 BODACC, `Lambda.TooManyRequestsException`) · ❌ erreur de données déterministe : la rejouer ne sert à rien, la router par `Catch`.

```json
# Exemple 1 : 3 retries, backoff x2
"Ingest": {
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "Retry": [{
    "ErrorEquals": ["States.TaskFailed"],
    "IntervalSeconds": 2,
    "BackoffRate": 2,
    "MaxAttempts": 3
  }],
  "Next": "Normalize"
}
```

- Quiz : Avec l'exemple 1, si la Lambda échoue toujours : combien d'appels, et quelles attentes, avant l'échec ?
- [ ] 3 appels, attentes 2 puis 4 s
- [ ] 3 appels, attentes 2, 2 puis 2 s
- [ ] 4 appels, attentes 2, 4 puis 6 s
- [x] 4 appels, attentes 2, 4 puis 8 s
- Réponse : 4 appels, attentes 2, 4 puis 8 s : `MaxAttempts` compte les retries, pas l'appel initial, et chaque attente est multipliée par 2.

## 2. Step Functions : quand orchestrer
- Id : step-functions-quand-orchestrer
- Sous-thème : choisir
- Type : choisir
- Niveau : 1
- Profils : débutant, data
- Voir aussi : step-functions-standard-ou-express, step-functions-mwaa-airflow
- Mots-clés : MWAA, DAG, machine d'états
- Définition : On choisit Step Functions dès qu'un pipeline enchaîne plusieurs étapes AWS : reprises, branches et historique sortent du code, sans serveur.
- Contexte : Le critère : des étapes dépendantes (Lambda, Glue, ECS, EMR), des attentes, des reprises à tracer. La console montre où une exécution a échoué et avec quelle entrée. En Standard, on paie par transition d'état (environ 0,03 $ les 1 000 à Paris), pas au temps écoulé : rien au repos, face à MWAA facturé 24 h/24. Une seule Lambda déclenchée par un événement n'en a pas besoin.
- Usage : ✅ pipeline quotidien ingest → normalize → publish, attente d'un job Spark · ❌ une seule Lambda sans suite : un déclencheur direct suffit ; parc de DAG Airflow existant : MWAA.

```
# Exemple 1 : la décision
Besoin  : chaque jour ingest →
          normalize → publish
→ Choix : Step Functions Standard
Pourquoi: retries, historique,
          0 $ au repos
Écarté  : Lambda qui appelle une
          Lambda (reprise à la main),
          MWAA (facturé 24 h/24)
```

```python
# Exemple 2 : coût d'un mois
transitions = 6        # par exécution
runs = 30
prix = 0.0000297       # $ / transition
round(transitions * runs * prix, 4)
# → 0.0053  ($/mois)
```

- Quiz : Le pipeline doit attendre jusqu'à 2 h le fichier d'un partenaire : comment attendre ?
- [ ] Une Lambda qui boucle avec `sleep`
- [x] Un état `Wait` entre deux vérifications
- [ ] Un workflow Express qui patiente
- [ ] Un `timeout` de 2 h sur la Lambda
- Réponse : un état `Wait` (en Standard) : l'attente ne coûte rien ; une Lambda est tuée à 15 min et facturée pendant le `sleep`, Express est plafonné à 5 min.

## 3. Step Functions : Catch après les retries
- Id : step-functions-catch
- Sous-thème : erreurs
- Type : concept
- Niveau : 2
- Profils : data, ops
- Prérequis : step-functions-retry-backoff
- Mots-clés : machine d'états
- Définition : `Catch` route un état en échec, une fois ses retries épuisés, vers un autre état (alerte, nettoyage) au lieu de faire échouer l'exécution.
- Contexte : Les `Catch` sont lus dans l'ordre : le premier dont `ErrorEquals` correspond gagne, `States.ALL` attrape tout et se place en dernier. L'erreur arrive sous forme d'objet `{"Error": …, "Cause": …}` ; `ResultPath` dit où la ranger dans l'entrée de l'état suivant. Sans `Catch`, l'état en échec fait passer toute l'exécution en `FAILED`.
- Usage : ✅ alerter, marquer la journée en échec, isoler une erreur de données à ne pas rejouer · ❌ `Catch` sans `Retry` sur une erreur transitoire (429) : on abandonne au premier hoquet.

```json
# Exemple 1 : Catch après les retries
"Catch": [{
  "ErrorEquals": ["States.ALL"],
  "ResultPath": "$.erreur",
  "Next": "Alerter"
}]
# → Alerter reçoit l'entrée d'origine
#   et l'erreur dans $.erreur
```

- Quiz : Même `Catch`, mais sans `ResultPath` : que reçoit l'état `Alerter` ?
- [ ] L'entrée d'origine, erreur ajoutée dans `$.erreur`
- [x] Seulement l'objet d'erreur (`Error`, `Cause`)
- [ ] L'entrée d'origine, sans l'erreur
- [ ] Rien : `Next` exige un `ResultPath`
- Réponse : seulement l'objet d'erreur : par défaut `ResultPath` vaut `$`, la sortie d'erreur remplace toute l'entrée ; d'où `"$.erreur"` pour garder la date à rejouer.

## 4. Step Functions : .sync
- Id : step-functions-sync-attendre-job
- Sous-thème : intégrations
- Type : concept
- Niveau : 2
- Profils : data, ops
- Voir aussi : glue-athena-glue-ou-emr
- Mots-clés : EMR, Glue, ECS
- Définition : Le suffixe `.sync` d'une intégration Step Functions attend la fin du job lancé (EMR Serverless, Glue, ECS) avant de passer à l'état suivant.
- Contexte : Trois modes d'intégration : requête-réponse (par défaut, on n'attend que l'acceptation de l'appel), `.sync` (Step Functions sonde le job et échoue si le job échoue), `.waitForTaskToken` (on attend qu'un tiers rappelle `SendTaskSuccess`). `.sync` n'existe qu'en workflow Standard.
- Usage : ✅ enchaîner un job Spark `bodacc-normalize` et l'export qui lit son résultat · ❌ attendre un humain ou un système externe : `.waitForTaskToken`.

```json
# Exemple 1 : attendre le job Spark
"Normalize": {
  "Type": "Task",
  "Resource":
    "arn:aws:states:::emr-serverless:startJobRun.sync",
  "Next": "Publish"
}
# → Publish démarre quand le job
#   est SUCCESS, 12 min plus tard
```

- Quiz : Même état sans `.sync` : quand `Publish` démarre-t-il ?
- [ ] À la fin du job, comme avec `.sync`
- [ ] Jamais : l'état attend un token
- [x] Tout de suite, dès le job accepté
- [ ] Après le timeout par défaut de l'état
- Réponse : tout de suite : l'état réussit dès que `startJobRun` a accepté le job ; `Publish` lit un `processed` pas encore écrit.

## 5. Step Functions : Standard ou Express
- Id : step-functions-standard-ou-express
- Sous-thème : choisir
- Type : comparaison
- Niveau : 2
- Profils : data, ops
- Mots-clés : exactly-once, livraison au moins une fois, machine d'états
- Définition : Un workflow Standard dure jusqu'à un an, exactly-once, historique conservé ; Express dure 5 minutes au plus, at-least-once, à fort débit.
- Contexte : Standard est facturé par transition d'état (environ 0,03 $ les 1 000 à Paris) : idéal pour un pipeline quotidien de quelques états. Express est facturé aux requêtes et à la durée, sans historique dans la console (logs CloudWatch). Le type ne se change pas après création : il faut recréer la machine. `.sync` et `.waitForTaskToken` sont réservés à Standard.
- Usage : ✅ Standard pour le pipeline BODACC quotidien (étapes longues, rejouables) · ❌ Standard pour des milliers d'événements courts par seconde : Express.

```hcl
# Exemple 1 : pipeline quotidien
resource "aws_sfn_state_machine" "d" {
  name     = "daily-pipeline"
  type     = "STANDARD"
  role_arn = aws_iam_role.sfn.arn
  definition = file(
    "${path.module}/steps/daily.json")
}
# ingest 1 min + normalize 12 min
# → 13 min : Express impossible
```

- Quiz : Valider 50 000 événements par seconde, 200 ms chacun : quel type de workflow ?
- [ ] `STANDARD` : exactly-once obligatoire
- [x] `EXPRESS` : court et à haut débit
- [ ] `STANDARD` : seul à appeler Lambda
- [ ] Aucun : Step Functions plafonne à 1 000/s
- Réponse : `EXPRESS` : prévu pour des exécutions courtes à très haut débit, facturé à la durée ; Standard est facturé par transition et limité en débit de démarrage.

## 6. MWAA : quand l'équipe a déjà Airflow
- Id : step-functions-mwaa-airflow
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : data, ops
- Voir aussi : couts-cout-au-repos
- Mots-clés : Airflow, DAG
- Définition : MWAA est Airflow managé : utile pour reprendre des centaines de DAG existants, mais un environnement est facturé à l'heure, même inactif.
- Contexte : Un environnement MWAA (ordonnanceur, workers, serveur web, base) tourne en continu ; on paie aussi les workers ajoutés à la charge. Airflow apporte un écosystème riche d'opérateurs et une équipe peut déjà le maîtriser. MWAA Serverless, facturé à la tâche, réduit ce coût fixe. Pour un premier pipeline de quelques étapes AWS, Step Functions reste plus simple.
- Usage : ✅ migrer un parc de DAG Airflow existant, équipe Airflow · ❌ premier pipeline de 4 étapes AWS : Step Functions, payé à la transition.

```
# Exemple 1 : la décision
Besoin  : 1 pipeline, 4 étapes AWS
→ Choix : Step Functions
Pourquoi: payé à la transition,
          0 $ au repos
Écarté  : MWAA (environnement
          facturé 24 h/24)

Besoin  : migrer 300 DAG Airflow
→ Choix : MWAA
```

- Quiz : Une startup sans Airflow ouvre le plus petit environnement MWAA (micro, Paris) : quel coût fixe mensuel ?
- [ ] Environ 0 $ sans DAG actif
- [ ] Environ 25 $
- [x] Environ 250 $
- [ ] Environ 2 500 $
- Réponse : environ 250 $ (0,35 $/h × 730 h) : l'environnement tourne en continu, quand Step Functions coûterait quelques centimes pour le même pipeline.
