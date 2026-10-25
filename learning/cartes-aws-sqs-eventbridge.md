---
title: "Cartes · SQS et EventBridge"
type: cartes
langage: AWS
cours: SQS et EventBridge
created: 2026-10-24
updated: 2026-10-25
---

# Cartes · SQS et EventBridge
AWS · SQS et EventBridge : choisir, eventbridge, sqs (format spec v3 de revision-pwa).

## 1. EventBridge Scheduler : le cron
- Sous-thème : eventbridge
- Niveau : 1
- Définition : EventBridge Scheduler déclenche une cible (Lambda, Step Functions) selon une expression `cron` à six champs, dans un fuseau horaire choisi.
- Contexte : Les six champs sont minute, heure, jour du mois, mois, jour de semaine, année. Sans `schedule_expression_timezone`, l'heure est UTC : 6 h devient 7 h ou 8 h à Paris selon la saison. `flexible_time_window` peut étaler le départ pour lisser la charge. Scheduler gère retries et DLQ de la cible, sans Lambda intermédiaire.
- Usage : ✅ ingestion quotidienne, rapport hebdomadaire, tâche ponctuelle (`at(…)`) · ❌ réagir à un fait (fichier déposé) : notification S3 ou règle EventBridge sur événement.

```hcl
# Exemple 1 : tous les jours à 6 h Paris
resource "aws_scheduler_schedule" "j" {
  name = "bodacc-daily"
  schedule_expression = "cron(0 6 * * ? *)"
  schedule_expression_timezone = "Europe/Paris"
  flexible_time_window { mode = "OFF" }
}
```

```bash
# Exemple 2 : autres expressions
# cron(0 6 ? * MON-FRI *) → jours ouvrés
# rate(1 day)  → toutes les 24 h
#   depuis la création, sans heure fixe
# at(2026-10-31T06:00:00) → une fois
```

- Quiz : L'expression `cron(0 6 * * * *)` est-elle acceptée ?
- [ ] Oui : tous les jours à 6 h
- [ ] Oui : toutes les heures à partir de 6 h
- [x] Non : un des deux champs jour doit valoir `?`
- [ ] Non : un cron AWS n'a que 5 champs
- Réponse : non : jour du mois et jour de semaine ne peuvent pas valoir `*` tous les deux ; l'un des deux doit être `?`.

## 2. SQS : quand découpler
- Sous-thème : choisir
- Niveau : 1
- Définition : SQS est une file entre un producteur et un consommateur : elle absorbe les pics, retente les échecs et isole les messages cassés en DLQ.
- Contexte : Le producteur dépose et repart ; le consommateur lit à son rythme. Avec Lambda, `maximum_concurrency` sur le mapping borne le nombre de lecteurs, donc le débit vers une API limitée. Une file standard livre au moins une fois, sans ordre garanti ; une file FIFO garde l'ordre et déduplique, à débit plus faible. Un message n'est lu que par un consommateur.
- Usage : ✅ lisser des appels vers une API limitée (BODACC, 429), file de jours à rejouer · ❌ diffuser un même événement à plusieurs services : SNS ou EventBridge en amont.

```
# Exemple 1 : la décision
Besoin  : 32 000 annonces à enrichir
          via une API limitée à 10 rps
→ Choix : SQS + Lambda consommatrice
          (concurrence max = 10)
Pourquoi: lissage du débit, retries,
          DLQ pour les cas cassés
Écarté  : appel direct (429 en masse)
```

```hcl
# Exemple 2 : borner les lecteurs
resource "aws_lambda_event_source_mapping" "m" {
  event_source_arn = aws_sqs_queue.enrich.arn
  function_name    = "bodacc-enrich"
  scaling_config {
    maximum_concurrency = 10
  }
}
```

- Quiz : Trois services (indexation, alertes, export) doivent chacun recevoir chaque annonce : une seule file SQS suffit-elle ?
- [x] Non : il faut un fan-out, une file par service
- [ ] Oui : chaque service lit toute la file
- [ ] Oui, avec une file FIFO
- [ ] Oui, avec trois DLQ
- Réponse : non : un message SQS est consommé par un seul lecteur ; il faut un fan-out (SNS ou EventBridge vers une file par consommateur).

## 3. event_pattern : le filtre EventBridge
- Sous-thème : eventbridge
- Niveau : 1
- Définition : `event_pattern` décrit les événements qui déclenchent la règle : une liste vaut OU entre valeurs, des clés différentes valent ET.
- Contexte : CodeCommit publie un événement « Repository State Change » par référence modifiée : `referenceCreated`, `referenceUpdated` ou `referenceDeleted`, avec le nom et le type (branche ou tag). Le motif ne garde que la création et la mise à jour de la branche `main` ; la suppression et les tags sont ignorés. Un champ absent de l'événement ne matche jamais.
- Usage : ✅ déclencher sur une branche, un type de référence, un dépôt précis · ❌ filtrer sur les fichiers modifiés : l'événement ne les contient pas, le tester dans le build.

```hcl
# Exemple 1 : main, création ou mise à jour
detail = {
  event = ["referenceCreated",
  "referenceUpdated"]
  referenceType = ["branch"]
  referenceName = ["main"]
}
# liste = OU · clés = ET
```

```text
# Exemple 2 : ce qui déclenche
push sur main         → oui
création de main      → oui
push sur feat/x       → non (nom)
tag nommé main        → non (type)
suppression de main   → non (event)
```

- Quiz : Un seul `git push` envoie 3 nouveaux commits sur `main` : combien de builds partent ?
- [x] `1`
- [ ] `3`
- [ ] `0`
- [ ] `2`
- Réponse : `1` : l'événement porte sur la référence, pas sur les commits ; `main` passe une fois à son nouveau commit, un seul `referenceUpdated`.

## 4. SQS : standard ou FIFO
- Sous-thème : sqs
- Niveau : 1
- Définition : Une file standard livre au moins une fois, sans ordre garanti ; une file FIFO garde l'ordre par groupe et déduplique sur 5 minutes.
- Contexte : En FIFO, `MessageGroupId` est obligatoire : l'ordre vaut à l'intérieur d'un groupe (un SIREN), les groupes se traitent en parallèle. La déduplication repose sur `MessageDeduplicationId` ou, avec `content_based_deduplication`, sur le SHA-256 du corps. Débit FIFO : 300 appels/s par action hors mode haut débit (3 000 messages/s en lots de 10), contre un débit quasi illimité en standard.
- Usage : ✅ FIFO quand l'ordre par entité compte (événements successifs d'un même SIREN) · ❌ FIFO par réflexe : standard et traitement idempotent, plus simple et sans plafond.

```hcl
# Exemple 1 : file FIFO dédupliquée
resource "aws_sqs_queue" "annonces" {
  name       = "bodacc-annonces.fifo"
  fifo_queue = true
  # même corps en 5 min → ignoré
  content_based_deduplication = true
}
```

```bash
# Exemple 2 : un groupe par SIREN
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"siren":"483609327"}' \
  --message-group-id 483609327
# ordre garanti pour ce SIREN seulement
```

- Quiz : `fifo_queue = true` avec `name = "bodacc-annonces"` : que donne `terraform plan` ?
- [ ] Une file FIFO nommée `bodacc-annonces`
- [ ] Une file standard : `fifo_queue` est ignoré
- [x] Une erreur : `invalid queue name`
- [ ] Une file nommée `bodacc-annonces.fifo`
- Réponse : une erreur (mesuré) : le nom d'une file FIFO doit finir par `.fifo` ; le provider le vérifie dès le plan.

## 5. SQS : 1 Mio, 14 jours
- Sous-thème : sqs
- Niveau : 1
- Définition : Un message SQS pèse au plus 1 Mio et reste au plus 14 jours en file (4 par défaut), puis il est supprimé sans bruit.
- Contexte : `message_retention_seconds` va de 60 à 1 209 600 s. Avec le défaut, un consommateur en panne pendant un long week-end suffit à perdre des messages. Au-delà de 1 Mio, on dépose le contenu dans S3 et on envoie sa clé dans le message (motif « claim check ») : le message reste petit, le fichier garde sa propre durée de vie.
- Usage : ✅ envoyer une référence S3 (bucket, clé) plutôt que l'annonce ou le fichier brut · ❌ SQS comme stockage : au-delà de quelques jours, S3.

```hcl
# Exemple 1 : rétention au maximum
resource "aws_sqs_queue" "jours" {
  name = "bodacc-jours"
  message_retention_seconds = 1209600 # 14 j
}
```

```python
# Exemple 2 : envoyer la clé, pas le fichier
import json
msg = {"bucket": "data-platform-dev-raw",
       "key": "bodacc/dt=2026-10-23/p0.json"}
corps = json.dumps(msg)
len(corps.encode()) < 1024 * 1024  # → True
```

- Quiz : On envoie le JSON brut d'une journée BODACC (50 Mo) en un seul message : que se passe-t-il ?
- [x] Refusé : 1 Mio maximum
- [ ] Accepté, découpé en morceaux par SQS
- [ ] Accepté, stocké dans S3 par SQS
- [ ] Accepté en FIFO seulement
- Réponse : refusé : SQS rejette tout message de plus de 1 Mio ; la bibliothèque « extended client » fait le dépôt S3, SQS ne le fait pas seul.

## 6. événement : source, detail-type, detail
- Sous-thème : eventbridge
- Niveau : 1
- Définition : Un événement EventBridge est un JSON à enveloppe fixe : `source` (émetteur), `detail-type` (nature du fait), `detail` (contenu libre), plus `time`, `account`, `region`.
- Contexte : Les règles filtrent sur ces champs ; `source` et `detail-type` suffisent souvent. Un événement maison prend une `source` à soi (`data-platform.bodacc`). `detail` est un objet JSON ; l'événement entier pèse au plus 256 Ko. Dans `put-events`, `Detail` se passe comme une chaîne JSON, pas comme un objet.
- Usage : ✅ un `detail-type` par fait métier (`AnnoncePubliee`, `JourIngere`) · ❌ un seul type générique avec un champ `action` : les règles deviennent illisibles.

```json
# Exemple 1 : un événement maison
{"source": "data-platform.bodacc",
 "detail-type": "JourIngere",
 "time": "2026-10-24T06:02:11Z",
 "account": "<account_id>",
 "region": "eu-west-3",
 "detail": {"jour": "2026-10-23",
            "annonces": 31874}}
```

- Quiz : Une application envoie `put-events` avec `Source = "aws.s3"` : que se passe-t-il ?
- [ ] Accepté : la source est libre
- [ ] Accepté, mais rangé dans le bus `default`
- [x] Refusé : le préfixe `aws.` est réservé aux services AWS
- [ ] Accepté, et S3 reçoit l'événement
- Réponse : refusé (`NotAuthorizedForSourceException`) : seuls les services AWS publient en `aws.*`, ce qui empêche d'imiter leurs événements.

## 7. bus personnalisé : put-events
- Sous-thème : eventbridge
- Niveau : 1
- Définition : Un bus personnalisé reçoit les événements métier de l'application, envoyés par `put-events`, à part du bus `default` où arrivent ceux des services AWS.
- Contexte : Une règle appartient à un bus (`event_bus_name`) : une règle du bus `default` ne voit jamais un événement du bus `data-platform`. L'émetteur a besoin de `events:PutEvents` sur l'ARN du bus. `put-events` accepte 10 entrées par appel. Sans `event_bus_name`, une règle Terraform va sur `default`.
- Usage : ✅ un bus `data-platform` pour les faits du pipeline (jour ingéré, annonce publiée) · ❌ événements métier sur `default` : mélangés à ceux d'AWS, droits plus larges.

```hcl
# Exemple 1 : bus et règle rattachée
resource "aws_cloudwatch_event_bus" "dp" {
  name = "data-platform"
}
resource "aws_cloudwatch_event_rule" "jour" {
  name           = "jour-ingere"
  event_bus_name = aws_cloudwatch_event_bus.dp.name
  event_pattern  = jsonencode({
    "detail-type" = ["JourIngere"] })
}
```

```bash
# Exemple 2 : publier sur le bus
aws events put-events --entries \
  '[{"EventBusName": "data-platform",
     "Source": "data-platform.bodacc",
     "DetailType": "JourIngere",
     "Detail": "{\"jour\":\"2026-10-23\"}"}]'
# → {"FailedEntryCount": 0, "Entries": […]}
```

- Quiz : Sur 10 entrées, une est refusée : que renvoie `put-events` ?
- [ ] Une exception, rien n'est publié
- [x] Un succès avec `FailedEntryCount: 1`, les 9 autres publiées
- [ ] Une exception, les 9 autres publiées
- [ ] Un succès, l'entrée refusée est retentée seule
- Réponse : un succès avec `FailedEntryCount: 1` : l'appel ne lève rien ; il faut lire `Entries` et renvoyer soi-même les entrées en `ErrorCode`.

## 8. SQS : DLQ et maxReceiveCount
- Sous-thème : sqs
- Niveau : 2
- Définition : Une redrive policy déplace un message vers une DLQ après `maxReceiveCount` réceptions sans suppression, pour l'isoler et l'analyser.
- Contexte : Chaque lecture incrémente `ApproximateReceiveCount` ; le message n'est supprimé que si le consommateur le confirme (Lambda le fait pour un lot réussi). Un message toxique (JSON cassé) bloquerait sinon des ressources sans fin. La DLQ doit être du même type (standard ou FIFO) et sa rétention plus longue que celle de la file source. `start-message-move-task` rejoue la DLQ vers la source après correction.
- Usage : ✅ toute file consommée par Lambda, avec alarme sur la profondeur de la DLQ · ❌ DLQ sans alarme : les échecs s'y accumulent sans que personne ne le voie.

```hcl
# Exemple 1 : 5 réceptions puis DLQ
resource "aws_sqs_queue" "jours" {
  name = "bodacc-jours"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })
}
# 5 échecs (ex. 429 BODACC) → DLQ
```

```bash
# Exemple 2 : rejouer la DLQ
aws sqs start-message-move-task \
  --source-arn arn:aws:sqs:eu-west-3:\
123456789012:bodacc-jours-dlq
# → messages renvoyés vers bodacc-jours
```

- Quiz : Avec `maxReceiveCount = 1`, que devient un jour tombé sur un `429` passager ?
- [ ] Réessayé 1 fois, puis DLQ
- [x] En DLQ au premier échec, sans retry
- [ ] Réessayé jusqu'à la rétention de la file
- [ ] Supprimé sans passer par la DLQ
- Réponse : en DLQ au premier échec : une seule réception autorisée, donc aucun retry ; garder plusieurs réceptions pour absorber les erreurs transitoires.

## 9. EventBridge : règle ou Scheduler
- Sous-thème : eventbridge
- Niveau : 2
- Définition : EventBridge route des événements vers des cibles selon des règles sur leur contenu, et planifie des tâches (Scheduler, ≈ cron managé).
- Contexte : Une règle filtre sur n'importe quel champ (`source`, `detail.type`, préfixe, plage numérique) et envoie à jusqu'à 5 cibles : c'est le fan-out sans code. Les événements des services AWS (S3, Glue, Step Functions) y arrivent nativement. Scheduler est un service à part : il déclenche à une heure, pas sur un fait, avec fuseau horaire et retries.
- Usage : ✅ alertes métier sur certaines annonces, réagir à la fin d'un job Glue, cron du pipeline · ❌ file de travail à lisser et rejouer : SQS.

```json
# Exemple 1 : ne router que les procol TC
{"source": ["data-platform.bodacc"],
 "detail-type": ["AnnoncePubliee"],
 "detail": {
   "type": ["procol"],
   "tribunal": [{"prefix": "TC "}]
 }}
# → seules les procol des TC
#   déclenchent la Lambda d'alerte
```

- Quiz : Lancer l'ingestion BODACC chaque jour à 6 h : règle sur événement ou EventBridge Scheduler ?
- [ ] Règle sur l'événement `AnnoncePubliee`
- [x] Scheduler, avec une expression `cron`
- [ ] Règle sur les événements S3 de `raw`
- [ ] SQS avec un délai de 24 h
- Réponse : Scheduler : il n'y a pas d'événement source, juste une heure ; il gère aussi le fuseau horaire et les retries de la cible.

## 10. flux continu : Firehose ou Kinesis
- Sous-thème : choisir
- Niveau : 2
- Définition : Data Firehose pose un flux dans S3 par lots, sans code ; Kinesis Data Streams garde le flux pour plusieurs lecteurs, qui peuvent le relire.
- Contexte : Firehose bufferise (taille ou durée), convertit en Parquet, puis écrit : rien à dimensionner, payé au Go ingéré, mais une fois livré, le flux n'est plus relisible. Kinesis Data Streams conserve les enregistrements 24 h par défaut, jusqu'à 365 jours : chaque consommateur lit à sa position et peut revenir en arrière. Les deux se combinent : Streams en entrée, Firehose vers S3.
- Usage : ✅ Firehose pour archiver des événements dans le lake · ❌ Firehose quand plusieurs consommateurs temps réel ou un rejeu sont nécessaires : Kinesis Data Streams.

```
# Exemple 1 : la décision
Besoin  : clics de l'app → S3
          pour analyse le lendemain
→ Choix : Data Firehose → S3
          (lots, Parquet)
Pourquoi: zéro code, zéro shard,
          payé au Go ingéré
Écarté  : Kinesis Data Streams
          (capacité, consommateurs)
```

- Quiz : Deux équipes doivent lire le même flux en temps réel et pouvoir rejouer les dernières 24 h : quel service ?
- [ ] Data Firehose, avec deux destinations
- [x] Kinesis Data Streams
- [ ] SQS, avec rétention de 24 h
- [ ] S3 avec notifications
- Réponse : Kinesis Data Streams : rétention rejouable (24 h par défaut, jusqu'à 365 jours) et plusieurs consommateurs ; Firehose livre puis oublie, SQS ne donne chaque message qu'à un lecteur.

## 11. jsonencode : le motif en HCL
- Sous-thème : eventbridge
- Niveau : 2
- Définition : `jsonencode` convertit un objet HCL en chaîne JSON : le motif s'écrit en HCL lisible plutôt qu'en JSON échappé dans une chaîne.
- Contexte : `event_pattern` attend une chaîne JSON. `jsonencode` produit du JSON compact aux clés triées par ordre alphabétique (vérifié dans `terraform console`), donc stable d'un `plan` à l'autre. Une clé avec un tiret comme `detail-type` doit être entre guillemets en HCL, sinon elle est lue comme une soustraction. `resources` limite la règle à un ARN de dépôt.
- Usage : ✅ tout attribut qui attend du JSON (motif, politique de file, `definition` d'une machine d'états) · ❌ politique IAM : `aws_iam_policy_document`, qui valide les champs.

```hcl
# Exemple 1 : objet HCL → chaîne JSON
event_pattern = jsonencode({
  source = ["aws.codecommit"]
  "detail-type" = [
  "CodeCommit Repository State Change"]
  resources = [
    data.aws_codecommit_repository.this.arn
  ]
})
# → "{\"detail-type\":[…],
#     \"resources\":[…],
#     \"source\":[\"aws.codecommit\"]}"
```

- Quiz : On retire `resources` du motif : quels dépôts déclenchent ce build ?
- [ ] Aucun : le motif devient invalide
- [ ] Seulement `revision-pwa`, déduit du projet
- [ ] Tous les dépôts git du compte, GitHub compris
- [x] Tous les dépôts CodeCommit du compte et de la région
- Réponse : tous les dépôts CodeCommit du compte et de la région : seul l'ARN dans `resources` désigne `revision-pwa`.

## 12. rôle EventBridge : StartBuild seulement
- Sous-thème : eventbridge
- Niveau : 2
- Définition : Pour lancer CodeBuild, EventBridge endosse son propre rôle, qui n'a qu'un droit : `codebuild:StartBuild` sur ce projet.
- Contexte : EventBridge n'agit jamais avec les droits de celui qui a créé la règle : il lui faut un rôle dont la trust policy accepte `events.amazonaws.com`. Ce rôle (`revision-pwa-dev-events-deploy`) ne voit ni S3 ni CloudFront : il démarre le build, et c'est le rôle de CodeBuild qui déploie. Deux rôles, deux services, deux jeux de droits disjoints.
- Usage : ✅ un rôle dédié par cible EventBridge, limité à l'ARN de la cible · ❌ `codebuild:*` ou `resources = ["*"]` : la règle pourrait lancer ou modifier n'importe quel projet.

```hcl
# Exemple 1 : un seul droit
data "aws_iam_policy_document" "events" {
  statement {
    actions = ["codebuild:StartBuild"]
    resources = [
      aws_codebuild_project.deploy.arn
    ]
  }
}
# trust : events.amazonaws.com
```

- Quiz : Pourquoi ne pas réutiliser le rôle `deploy` de CodeBuild comme rôle de la cible EventBridge ?
- [ ] Un rôle IAM ne peut avoir qu'une politique
- [x] Sa trust policy n'accepte que `codebuild.amazonaws.com`
- [ ] EventBridge exige un rôle nommé `events-*`
- [ ] Les deux rôles doivent être dans deux régions
- Réponse : sa trust policy n'accepte que CodeBuild, et il porte des droits S3 inutiles à EventBridge : un rôle par service, un droit chacun.

## 13. event_target : relier règle et projet
- Sous-thème : eventbridge
- Niveau : 2
- Définition : `aws_cloudwatch_event_target` branche la règle sur le projet CodeBuild et indique le rôle qu'EventBridge endosse pour le lancer.
- Contexte : Une règle sans cible ne fait rien : elle matche les événements et les jette. La cible porte l'ARN du projet et le rôle. Les ressources gardent le préfixe `cloudwatch_event` pour des raisons historiques : EventBridge s'appelait CloudWatch Events. Une règle accepte jusqu'à cinq cibles, chacune avec son rôle.
- Usage : ✅ une cible par action déclenchée (build, Lambda, notification) · ❌ une Lambda intermédiaire qui appelle `StartBuild` : la cible CodeBuild native suffit.

```hcl
# Exemple 1 : règle → projet, via un rôle
resource "aws_cloudwatch_event_target" "deploy" {
  rule     = aws_cloudwatch_event_rule.push_main.name
  arn      = aws_codebuild_project.deploy.arn
  role_arn = aws_iam_role.events.arn
}
```

- Quiz : On oublie `role_arn` sur cette cible CodeBuild : que se passe-t-il ?
- [ ] EventBridge prend le rôle de service du projet
- [x] La cible est refusée : CodeBuild exige un rôle
- [ ] Le build part avec les droits de l'auteur de la règle
- [ ] Le build part, mais sans logs
- Réponse : la cible est refusée : pour une cible CodeBuild, EventBridge a besoin d'un rôle autorisé à `StartBuild` ; il n'emprunte aucun autre rôle.

## 14. long polling : attendre 20 s
- Sous-thème : sqs
- Niveau : 2
- Définition : Le long polling fait attendre `ReceiveMessage` jusqu'à 20 s qu'un message arrive, au lieu de répondre vide aussitôt : moins d'appels facturés.
- Contexte : Le défaut est le short polling (`receive_wait_time_seconds = 0`) : chaque appel répond tout de suite, souvent vide, et chaque appel se paie, même vide. Le mapping Lambda fait déjà du long polling : le réglage compte pour un consommateur maison (script, conteneur). Côté client, `WaitTimeSeconds` d'un appel prime sur le réglage de la file.
- Usage : ✅ `receive_wait_time_seconds = 20` sur toute file lue par un consommateur maison · ❌ boucle `while True` en short polling : appels vides facturés à la chaîne.

```hcl
# Exemple 1 : long polling par défaut
resource "aws_sqs_queue" "jours" {
  name = "bodacc-jours"
  receive_wait_time_seconds = 20 # max
}
```

```python
# Exemple 2 : appels par jour, file vide
jour = 24 * 3600
short = jour / 0.1  # un appel / 100 ms
long_ = jour / 20   # un appel / 20 s
int(short), int(long_)  # → (864000, 4320)
```

- Quiz : Short polling, la file contient 3 messages, `ReceiveMessage` en renvoie 0 : la file est-elle vide ?
- [ ] Oui : SQS renvoie tout message disponible
- [ ] Oui : les 3 messages sont expirés
- [ ] Non : ils sont forcément en vol chez un autre lecteur
- [x] Pas forcément : seule une partie des serveurs a été interrogée
- Réponse : pas forcément : en short polling, SQS n'interroge qu'un échantillon de ses serveurs ; le long polling les interroge tous.

## 15. mapping SQS : lot et fenêtre
- Sous-thème : sqs
- Niveau : 2
- Définition : `batch_size` fixe le nombre maximal de messages par invocation ; `maximum_batching_window_in_seconds` attend jusqu'à N secondes pour remplir le lot.
- Contexte : Avec une file standard, `batch_size` va jusqu'à 10 000. Un lot plus gros réduit le nombre d'invocations, mais un échec rejoue tout le lot sans `ReportBatchItemFailures`. La charge utile d'une invocation reste limitée à 6 Mo : le lot s'arrête avant. La fenêtre ajoute de la latence : jusqu'à N secondes avant traitement.
- Usage : ✅ messages petits et nombreux (SIREN à enrichir) : lots de 100, fenêtre de 30 s · ❌ gros lots sans réponse partielle : un message cassé rejoue tous les autres.

```hcl
# Exemple 1 : 100 SIREN par appel, 30 s max
resource "aws_lambda_event_source_mapping" "m" {
  event_source_arn = aws_sqs_queue.jours.arn
  function_name    = aws_lambda_function.i.arn
  batch_size       = 100
  maximum_batching_window_in_seconds = 30
}
# lot plein OU 30 s écoulées → invocation
```

- Quiz : Même mapping sans `maximum_batching_window_in_seconds` : que donne l'`apply` ?
- [ ] Des lots de 100, envoyés aussitôt
- [ ] Des lots de 10 : SQS plafonne la lecture
- [x] Refusé : au-delà de 10, la fenêtre est obligatoire
- [ ] Une fenêtre de 30 s par défaut
- Réponse : refusé par l'API (le `plan` passe, mesuré) : un `batch_size` au-delà de 10 exige une fenêtre d'au moins 1 s (doc AWS).

## 16. politique de file : qui peut écrire
- Sous-thème : sqs
- Niveau : 2
- Définition : `aws_sqs_queue_policy` autorise un service (EventBridge, SNS, S3) à déposer dans la file ; pour une cible SQS, EventBridge n'endosse pas de rôle.
- Contexte : C'est une politique de ressource, comme `aws_lambda_permission` : le principal est `events.amazonaws.com`, borné par `aws:SourceArn` à la règle. Sans elle, rien ne casse à l'`apply` : la règle matche, puis chaque livraison échoue et l'événement est retenté puis perdu. Une file chiffrée par une clé KMS du client demande aussi `kms:GenerateDataKey` au service dans la politique de clé.
- Usage : ✅ une déclaration par émetteur, bornée par `aws:SourceArn` · ❌ `Principal: "*"` sans condition : n'importe qui peut remplir la file.

```hcl
# Exemple 1 : seule cette règle écrit
data "aws_iam_policy_document" "q" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.jours.arn]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.procol.arn]
    }
  }
}
```

- Quiz : La politique manque : où voit-on que les événements ne sont pas livrés ?
- [ ] Une erreur à l'`apply` de la cible
- [x] La métrique `FailedInvocations` de la règle
- [ ] Des messages dans la DLQ de la file
- [ ] Une erreur dans les logs du consommateur
- Réponse : `FailedInvocations` : la règle a matché mais la livraison est refusée ; la file ne reçoit rien, sa DLQ et son consommateur non plus.

## 17. cible : retries et DLQ
- Sous-thème : eventbridge
- Niveau : 2
- Définition : Si la livraison à une cible échoue, EventBridge réessaie 24 h et 185 fois au plus par défaut, puis jette l'événement, sauf DLQ.
- Contexte : `retry_policy` réduit la fenêtre (`maximum_event_age_in_seconds`, `maximum_retry_attempts`). `dead_letter_config` garde l'événement non livré dans une file SQS, avec la raison en attributs (`ERROR_CODE`, `ERROR_MESSAGE`). Ces retries couvrent la livraison (cible absente, droits, limitation), pas l'échec du code de la cible.
- Usage : ✅ DLQ sur chaque cible, avec alarme ; fenêtre courte pour un événement qui périme vite · ❌ défaut de 24 h pour une alerte : livrée trop tard pour servir.

```hcl
# Exemple 1 : 1 h max, puis DLQ
resource "aws_cloudwatch_event_target" "q" {
  rule = aws_cloudwatch_event_rule.procol.name
  arn  = aws_sqs_queue.jours.arn
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 10
  }
  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }
}
```

- Quiz : La cible est une Lambda ; elle est bien appelée, mais son code lève une exception : l'événement va-t-il dans la DLQ de la cible ?
- [ ] Oui, après 185 essais
- [ ] Oui, immédiatement
- [x] Non : la livraison a réussi, Lambda gère ses propres retries
- [ ] Non : une cible Lambda n'accepte pas de DLQ
- Réponse : non : EventBridge a livré (appel asynchrone accepté) ; l'échec du code relève des 2 retries et de la destination `on_failure` de la Lambda.

## 18. schedule group : default si rien
- Sous-thème : eventbridge
- Niveau : 2
- Source : data-platform · S1-08
- Définition : Toute planification Scheduler appartient à un groupe ; sans `group_name`, c'est le groupe `default`, qui existe dans chaque compte et région.
- Contexte : Le groupe porte les tags et sert de frontière d'accès : c'est son ARN que voit `aws:SourceArn` dans la confiance du rôle d'exécution. Un groupe par environnement ou par équipe permet de borner les rôles et de tout supprimer d'un coup. Le nom d'une planification n'est unique que dans son groupe : `get-schedule` cherche dans `default` si `--group-name` manque.
- Usage : ✅ `default` pour un projet seul par compte ; un groupe dédié quand plusieurs projets partagent le compte · ❌ croire `aws:SourceArn` porté par la planification elle-même.

```bash
# Exemple 1 : le groupe toujours là
aws scheduler list-schedule-groups \
  --query 'ScheduleGroups[].Name'
# → ["default"]  (compte sans planification)
```

- Quiz : Planification créée dans le groupe `data-platform-dev` ; `aws scheduler get-schedule --name <nom>` sans `--group-name` : résultat ?
- [ ] La planification : le nom est unique dans le compte
- [x] `ResourceNotFoundException`
- [ ] Toutes les planifications de ce nom
- Réponse : `ResourceNotFoundException` : sans `--group-name`, la recherche se fait dans `default`, où ce nom n'existe pas.

## 19. SQS : visibility timeout
- Sous-thème : sqs
- Niveau : 3
- Définition : Le visibility timeout cache un message lu aux autres consommateurs ; s'il n'est pas supprimé à temps, il redevient visible et sera relu.
- Contexte : SQS ne sait pas qu'un consommateur travaille : il attend la suppression. Si le traitement dure plus que le visibility timeout, un second consommateur reçoit le même message, d'où des doublons. Avec Lambda, AWS conseille 6 fois le timeout de la fonction, pour laisser la place aux retries du poller sur throttling. La valeur va de 0 s à 12 h.
- Usage : ✅ visibility timeout ≥ 6 × timeout Lambda, traitement idempotent quand même · ❌ visibility par défaut (30 s) devant une Lambda de plusieurs minutes.

```hcl
# Exemple 1 : file réglée sur la Lambda
resource "aws_sqs_queue" "jours" {
  name = "bodacc-jours"
  visibility_timeout_seconds = 1800
}
resource "aws_lambda_event_source_mapping" "m" {
  event_source_arn = aws_sqs_queue.jours.arn
  function_name    = "bodacc-ingest"
  batch_size       = 1
}
# timeout Lambda 300 s → 6 × 300
```

```python
# Exemple 2 : trop lent = relu
visibility = 30          # s
duree = 45               # traitement
relu = duree > visibility
relu  # → True : traité deux fois
```

- Quiz : File laissée à `30` s, Lambda à `timeout = 300` : que fait l'`apply` du mapping ?
- [ ] Il passe, SQS s'adapte au timeout
- [ ] Il passe, mais avec un avertissement
- [ ] Il passe et ramène la Lambda à 30 s
- [x] Il échoue : visibility < timeout Lambda
- Réponse : il échoue avec `InvalidParameterValueException` : le visibility timeout de la file doit être au moins égal au timeout de la fonction.

## 20. SQS : échec partiel d'un lot
- Sous-thème : sqs
- Niveau : 3
- Définition : Avec `ReportBatchItemFailures`, le handler renvoie les `messageId` en échec ; seuls ceux-là reviennent dans la file, les autres sont supprimés.
- Contexte : Par défaut, un lot SQS réussit ou échoue en entier : une exception remet tous les messages dans la file, y compris ceux déjà traités, qui le seront deux fois. La réponse partielle évite ce rejeu. Une exception levée reste un échec du lot entier ; une liste vide signifie « tout a réussi ».
- Usage : ✅ `batch_size` > 1 avec traitement message par message · ❌ `batch_size = 1` : rien à gagner ; réponse partielle sans le réglage sur le mapping.

```python
# Exemple 1 : signaler le message raté
def handler(event, context):
    ko = []
    for r in event["Records"]:
        if r["body"] == "2026-10-31":
            ko.append({"itemIdentifier":
                       r["messageId"]})
    return {"batchItemFailures": ko}

ev = {"Records": [
  {"messageId": "a", "body": "2026-10-23"},
  {"messageId": "b", "body": "2026-10-31"}]}
handler(ev, None)
# → {"batchItemFailures": [{"itemIdentifier": "b"}]}
```

```hcl
# Exemple 2 : activer sur le mapping
resource "aws_lambda_event_source_mapping" "m" {
  event_source_arn = aws_sqs_queue.jours.arn
  function_name    = "bodacc-ingest"
  batch_size       = 10
  function_response_types = [
    "ReportBatchItemFailures"]
}
```

- Quiz : Même handler, mais le mapping n'a pas `function_response_types` : que devient le message `b` ?
- [x] Supprimé comme réussi
- [ ] Remis seul dans la file
- [ ] Envoyé directement en DLQ
- [ ] Le lot entier revient dans la file
- Réponse : supprimé comme réussi : sans ce réglage, la valeur renvoyée est ignorée ; une invocation sans exception vaut succès de tout le lot.

## 21. input_transformer : remodeler l'événement
- Sous-thème : eventbridge
- Niveau : 3
- Définition : `input_transformer` extrait des champs de l'événement (`input_paths`) et les place dans un gabarit (`input_template`) : la cible reçoit ce JSON au lieu de l'événement.
- Contexte : Jusqu'à 100 variables, en JSONPath simple (`$.detail.siren`). Une chaîne reçoit ses guillemets automatiquement, un objet ou un tableau s'insère tel quel ; `<aws.events.event.json>` insère l'événement entier. Utile quand la cible attend un format fixe (Step Functions, API tierce, `sourceVersion` de CodeBuild) : pas de Lambda de traduction.
- Usage : ✅ adapter l'événement au contrat de la cible · ❌ condition ou calcul : une Lambda ou EventBridge Pipes.

```hcl
# Exemple 1 : ne garder que siren et jour
input_transformer {
  input_paths = {
    siren = "$.detail.siren"
    jour  = "$.detail.jour"
  }
  input_template = <<-T
    {"siren": <siren>, "jour": <jour>}
  T
}
# → {"siren": "483609327",
#    "jour": "2026-10-23"}
```

- Quiz : L'événement n'a pas de `detail.jour` : que devient `<jour>` dans la sortie ?
- [ ] `null`
- [ ] Une chaîne vide `""`
- [ ] La livraison échoue et part en DLQ
- [x] La variable n'est pas créée et disparaît de la sortie
- Réponse : elle disparaît : un chemin absent ne crée pas de variable et rien n'est validé (doc AWS) ; vérifier le JSON produit avant de s'y fier.

## 22. archive et replay : rejouer des événements
- Sous-thème : eventbridge
- Niveau : 3
- Définition : Une archive garde les événements d'un bus (tous ou filtrés) N jours ; un replay les renvoie sur ce bus pour une plage de dates.
- Contexte : Après un bug d'un consommateur, on corrige puis on rejoue la journée d'événements, vers toutes les règles ou certaines seulement. Les événements rejoués portent un champ `replay-name`, ce qui permet de les exclure d'une règle (alertes déjà envoyées). Le replay n'est ni instantané ni ordonné : les consommateurs doivent être idempotents. L'archive se paie au Go.
- Usage : ✅ rejouer les `AnnoncePubliee` d'une journée vers une règle corrigée · ❌ archive comme source de vérité : la zone raw du lake reste la référence.

```hcl
# Exemple 1 : 30 jours d'événements
resource "aws_cloudwatch_event_archive" "a" {
  name             = "bodacc-30j"
  event_source_arn = aws_cloudwatch_event_bus.dp.arn
  retention_days   = 30
}
```

```bash
# Exemple 2 : rejouer le 23 octobre
aws events start-replay \
  --replay-name bodacc-2026-10-23 \
  --event-source-arn "$ARCHIVE_ARN" \
  --event-start-time 2026-10-23T00:00:00Z \
  --event-end-time 2026-10-24T00:00:00Z \
  --destination "Arn=$BUS_ARN"
```

- Quiz : Que veut dire `retention_days = 0` sur une archive ?
- [ ] Rien n'est archivé
- [x] Les événements sont gardés sans limite
- [ ] Un jour, la plus petite valeur
- [ ] Le défaut de 30 jours
- Réponse : sans limite : `0` signifie une rétention indéfinie (doc AWS) ; fixer une durée pour borner le coût de stockage.

## 23. motifs : anything-but, numeric, exists
- Sous-thème : eventbridge
- Niveau : 3
- Définition : Les opérateurs de motif filtrent au-delà de l'égalité : `anything-but` (tout sauf), `numeric` (comparaisons), `exists` (présence d'un champ), `prefix`.
- Contexte : Mesuré avec `aws events test-event-pattern` : `"capital": "150000"` (chaîne) ne matche pas `numeric`, seul un nombre JSON passe ; `exists: true` accepte un champ à `null`. Le matching est sensible à la casse : `"tc paris"` ne matche pas `"TC Paris"` (`equals-ignore-case` existe). Si l'événement contient un tableau, il matche dès qu'un élément matche.
- Usage : ✅ tester chaque motif avec `test-event-pattern` avant de déployer · ❌ filtrer dans le code de la Lambda : invocations payées pour rien.

```json
# Exemple 1 : procol de 100 k€ et plus
{"source": ["data-platform.bodacc"],
 "detail": {
   "type": [{"anything-but": ["radiation"]}],
   "capital": [{"numeric": [">=", 100000]}],
   "siren": [{"exists": true}]}}
```

```text
# Exemple 2 : test-event-pattern (mesuré)
procol, 150000, siren     → true
radiation, 150000, siren  → false
procol, "150000", siren   → false
procol, 150000, sans siren → false
```

- Quiz : Même motif, événement `{"capital": 150000, "siren": "483609327"}`, sans champ `type` : matche-t-il ?
- [ ] Oui : un champ absent n'est pas `radiation`
- [x] Non : `anything-but` exige que le champ existe
- [ ] Oui : `anything-but` ignore les champs absents
- [ ] Erreur : motif invalide sans le champ
- Réponse : non (mesuré) : comme toute condition sur une valeur, `anything-but` ne matche qu'un champ présent.
