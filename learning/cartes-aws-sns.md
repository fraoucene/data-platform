---
title: "Cartes · SNS"
type: cartes
langage: AWS
chapitre: Messages et événements
cours: SNS
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · SNS
AWS · SNS : topics, email, abonnements, politique, choisir (format spec v4 de revision-pwa).

## 1. topic : un message, plusieurs abonnés
- Id : sns-topic-fan-out
- Sous-thème : topics
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : sns-vers-sqs-fan-out
- Source : data-platform · S1-08
- Définition : Un topic SNS pousse chaque message publié à tous ses abonnés : email, file SQS, Lambda, HTTPS (≈ un `EventEmitter` entre services).
- Contexte : L'émetteur (une alarme CloudWatch, un budget, ton code) ne connaît que l'ARN du topic, jamais les destinataires : on ajoute un abonné sans toucher à l'émetteur. SNS pousse, il ne stocke pas : un message publié sans abonné est perdu, et un abonné indisponible au-delà des retries ne le reçoit jamais. Pour garder les messages, abonner une file SQS.
- Usage : ✅ diffuser une alerte ou un événement à plusieurs consommateurs (fan-out) · ❌ garder des messages à relire plus tard : SQS (ou SNS → SQS).

```hcl
# Exemple 1 : topic + abonné
resource "aws_sns_topic" "alerts" {
  name = "${local.prefix}-alerts"
}

resource "aws_sns_topic_subscription" "mail" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
```

- Quiz : On publie dans un topic qui n'a encore aucun abonné, puis on abonne une file. La file reçoit-elle le message ?
- [ ] Oui, SNS le garde 4 jours
- [x] Non, il est perdu
- [ ] Oui, à la confirmation de l'abonnement
- Réponse : non : SNS ne stocke pas les messages, il les pousse aux abonnés présents au moment de la publication.

## 2. abonnement email : PendingConfirmation
- Id : sns-email-pending-confirmation
- Sous-thème : email
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Source : data-platform · S1-08
- Définition : Un abonnement email reste `PendingConfirmation` tant que le lien du mail de confirmation n'est pas cliqué ; d'ici là, rien n'est livré.
- Contexte : Terraform crée l'abonnement, mais ne peut pas le confirmer : seul le destinataire le peut, ce qui empêche d'abonner l'adresse de quelqu'un d'autre. Tant que le lien n'est pas cliqué, l'alarme passe bien en `ALARM` et publie, mais le mail ne part pas. Mesuré après `make up` : `PendingConfirmation`, puis un ARN complet une fois le lien cliqué.
- Usage : ✅ vérifier la confirmation juste après le premier `apply` · ❌ conclure qu'une alerte marche parce que l'alarme existe.

```bash
# Exemple 1 : avant et après le clic
aws sns list-subscriptions-by-topic \
  --topic-arn "$T" \
  --query 'Subscriptions[].SubscriptionArn' \
  --output text
# avant → PendingConfirmation
# après → arn:aws:sns:eu-west-3:<account_id>:
#         data-platform-dev-alerts:<id>
```

- Quiz : Abonnement email non confirmé, l'alarme passe en `ALARM`. Que se passe-t-il ?
- [ ] Le mail part quand même
- [ ] SNS le garde jusqu'à la confirmation
- [x] Rien n'est livré à l'adresse
- [ ] L'alarme reste `OK`
- Réponse : rien n'est livré : l'alarme change d'état et publie, mais SNS ne livre qu'aux abonnements confirmés, et ne garde rien pour plus tard.

## 3. protocoles : qui doit confirmer
- Id : sns-protocoles-confirmation
- Sous-thème : abonnements
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Source : data-platform · S1-08
- Définition : SNS livre en `email`, `email-json`, `sqs`, `lambda`, `http`/`https`, `sms`, `firehose` ; email et HTTP(S) exigent une confirmation par le destinataire.
- Contexte : Une file SQS ou une Lambda du même compte, abonnées par Terraform, sont confirmées d'office : leur propriétaire est celui qui crée l'abonnement. Une adresse email ou une URL doivent prouver qu'elles acceptent les messages (lien cliqué, ou `SubscribeURL` appelée par le serveur). `email-json` livre le JSON brut au lieu d'un texte mis en forme.
- Usage : ✅ email pour un humain, SQS ou Lambda pour un traitement automatique · ❌ SMS pour des alertes fréquentes : coût par message, et quotas.

```hcl
# Exemple 1 : même topic, deux abonnés
resource "aws_sns_topic_subscription" "file" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.alertes.arn
}
# confirmé d'office (même compte)
# l'abonnement email : clic requis
```

- Quiz : Lequel de ces abonnements, créé par Terraform dans le même compte, reste en attente de confirmation ?
- [ ] `sqs`
- [ ] `lambda`
- [x] `https`
- Réponse : `https` : le serveur doit appeler la `SubscribeURL` reçue pour confirmer ; SQS et Lambda du même compte sont confirmés d'office.

## 4. topic par environnement
- Id : sns-topic-par-environnement
- Sous-thème : topics
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Source : data-platform · S1-08
- Définition : Un topic d'alertes porte le préfixe d'environnement (`data-platform-dev-alerts`) : les alertes de dev et de prod ne se mélangent pas.
- Contexte : Le topic du budget (`data-platform-budget-alerts`) est global au compte : un budget porte sur la facture entière. Les alertes d'exploitation, elles, dépendent de l'environnement : en prod, on voudra d'autres destinataires (astreinte, canal d'équipe), voire un autre compte. Le nom vient de `local.prefix`, comme les buckets et les fonctions.
- Usage : ✅ `${local.prefix}-alerts` pour tout ce qui suit un environnement · ❌ un seul topic « alerts » partagé : un mail de dev réveille l'astreinte de prod.

```hcl
# Exemple 1 : un nom par environnement
locals {
  prefix = "data-platform-${var.environment}"
}
resource "aws_sns_topic" "alerts" {
  name = "${local.prefix}-alerts"
}
# dev  → data-platform-dev-alerts
# prod → data-platform-prod-alerts
```

- Quiz : Dev et prod sont dans le même compte et partagent `alerts`. Que reçoit l'astreinte de prod quand une Lambda de dev échoue ?
- [ ] Rien : les alarmes filtrent par environnement
- [x] Le mail d'alerte de dev
- [ ] Un mail marqué « dev »
- Réponse : le mail d'alerte de dev : tous les abonnés d'un topic reçoivent tous ses messages ; seul un topic par environnement les sépare.

## 5. publish : envoyer un message de test
- Id : sns-publish-test
- Sous-thème : topics
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : cloudwatch-set-alarm-state
- Source : data-platform · S1-08
- Définition : `aws sns publish --topic-arn … --message …` envoie un message à tous les abonnés confirmés du topic et renvoie son `MessageId`.
- Contexte : C'est le test le plus court du maillon SNS → mail, sans passer par une alarme. Il prouve que l'abonnement est confirmé et que le mail n'arrive pas en spam ; il ne prouve rien de la politique du topic pour CloudWatch, puisque c'est ton identité qui publie, pas le service. `--subject` donne l'objet du mail (100 caractères au plus).
- Usage : ✅ vérifier un nouvel abonnement email, un filtre de boîte mail · ❌ tester une alarme : `set-alarm-state`, ou une vraie erreur du handler.

```bash
# Exemple 1 : un message de test
aws sns publish --topic-arn "$T" \
  --subject "test data-platform" \
  --message "chemin SNS -> mail OK ?"
# → {"MessageId": "…"}
#   mail reçu par chaque abonné confirmé
```

- Quiz : Ce `publish` arrive bien par mail. Que reste-t-il à prouver pour les alarmes ?
- [ ] Rien, la chaîne est complète
- [x] Que CloudWatch a le droit de publier
- [ ] Que l'abonnement est confirmé
- Réponse : le droit de CloudWatch : ton `publish` passe par ton identité IAM ; celui de l'alarme passe par la politique du topic.

## 6. 48 h pour confirmer
- Id : sns-confirmation-48h
- Sous-thème : email
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : sns-email-pending-confirmation
- Source : data-platform · S1-08
- Définition : SNS supprime un abonnement non confirmé au bout de 48 heures ; il faut alors le recréer pour recevoir un nouveau mail de confirmation.
- Contexte : Un mail de confirmation parti en spam et oublié deux jours : l'abonnement disparaît côté AWS, mais Terraform le croit toujours là jusqu'au prochain `plan`, qui le recrée. Exception : un abonnement suspendu pour dépassement de débit reste 30 jours en `PendingConfirmation` avant suppression (doc SNS).
- Usage : ✅ cliquer le lien juste après l'`apply`, vérifier `SubscriptionsConfirmed` · ❌ remettre à plus tard : après 48 h, il faut un nouvel `apply`.

```python
# Exemple 1 : jusqu'à quand cliquer ?
from datetime import datetime, timedelta

apply = datetime(2026, 10, 25, 18, 10)
(apply + timedelta(hours=48)).strftime(
    "%d/%m %H:%M")
# → '27/10 18:10'
```

- Quiz : Abonnement email jamais confirmé, 3 jours après l'`apply`. Que fait `make plan` ?
- [ ] `No changes`
- [x] Propose de recréer l'abonnement
- [ ] Erreur : abonnement introuvable
- Réponse : propose de le recréer : SNS l'a supprimé après 48 h, Terraform constate l'absence au rafraîchissement et le replanifie.

## 7. politique de topic : un service qui publie en son nom
- Id : sns-politique-de-topic
- Sous-thème : politique
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : iam-politique-de-ressource
- Source : data-platform · S1-08
- Définition : `aws_sns_topic_policy` est la politique côté ressource du topic : elle autorise un service (`cloudwatch.amazonaws.com`, `budgets.amazonaws.com`) à y publier.
- Contexte : CloudWatch publie en son propre nom, sans endosser de rôle : c'est la « liste d'invités » posée sur le topic, comme `aws_lambda_permission` sur une Lambda. `aws:SourceAccount` limite l'accès aux alarmes du compte (confused deputy). Attention : cette ressource **remplace** la politique par défaut, elle ne s'y ajoute pas (mesuré : un seul `Statement`).
- Usage : ✅ une instruction par service émetteur, bornée par `aws:SourceAccount` · ❌ `Principal = "*"` sans condition : n'importe qui pourrait publier dans tes alertes.

```json
# Exemple 1 : politique mesurée
{"Statement": [{
  "Sid": "AllowCloudWatchAlarms",
  "Effect": "Allow",
  "Principal": {"Service": "cloudwatch.amazonaws.com"},
  "Action": "sns:Publish",
  "Condition": {"StringEquals": {
    "aws:SourceAccount": "<account_id>"}}}]}
```

- Quiz : Après cette politique, un utilisateur IAM du compte avec `sns:Publish` dans sa propre politique peut-il publier ?
- [x] Oui : même compte, son identité suffit
- [ ] Non : seul CloudWatch est listé
- [ ] Seulement avec `aws:SourceAccount`
- Réponse : oui : dans un même compte, l'identité ou la ressource suffit ; la politique du topic ajoute un appelant, elle ne retire pas les droits IAM du compte.

## 8. aws:SourceArn : n'autoriser que ses alarmes
- Id : sns-source-arn-alarmes
- Sous-thème : politique
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : sns-politique-de-topic
- Source : data-platform · S1-08
- Définition : Pour CloudWatch, `aws:SourceArn` vaut l'ARN de l'alarme émettrice ; `ArnLike` avec `…:alarm:*` restreint aux alarmes du compte et de la région.
- Contexte : `aws:SourceAccount` dit « une alarme de ce compte » ; `aws:SourceArn` peut dire « ces alarmes-là » (`…:alarm:data-platform-dev-*`). La doc CloudWatch recommande les deux contre le confused deputy. Si un nom d'alarme contient des caractères non ASCII, garder `aws:SourceAccount` seul (doc).
- Usage : ✅ `ArnLike` sur un préfixe d'alarmes quand plusieurs équipes partagent un compte · ❌ un `StringEquals` sur `alarm:*` : le joker n'est interprété qu'avec `ArnLike`.

```json
# Exemple 1 : compte + préfixe d'alarmes
"Condition": {
  "ArnLike": {"aws:SourceArn":
    "arn:aws:cloudwatch:eu-west-3:<account_id>:alarm:data-platform-dev-*"},
  "StringEquals": {
    "aws:SourceAccount": "<account_id>"}
}
```

- Quiz : Avec la condition de l'exemple, l'alarme `data-platform-prod-ingest-bodacc-errors` du même compte peut-elle publier ?
- [ ] Oui : même compte
- [x] Non : hors du préfixe `dev`
- [ ] Oui : `ArnLike` ignore le nom
- Réponse : non : les deux conditions doivent être vraies, et l'ARN de l'alarme de prod ne correspond pas au motif `…:alarm:data-platform-dev-*`.

## 9. SNS ne garde rien : SNS → SQS
- Id : sns-vers-sqs-fan-out
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : data, ops
- Voir aussi : sns-sqs-ou-eventbridge
- Source : data-platform · S1-08
- Définition : Pour qu'aucun message ne se perde, on abonne une file SQS au topic : SNS diffuse, SQS conserve jusqu'à 14 jours.
- Contexte : Un consommateur lent ou en panne ne lit pas un message poussé par SNS ; une file le garde jusqu'à ce qu'il le traite et le supprime. C'est le motif « fan-out » : un topic, plusieurs files, chacune à son rythme. La file doit autoriser le topic à y écrire (`aws_sqs_queue_policy`, principal `sns.amazonaws.com`, `aws:SourceArn` = le topic).
- Usage : ✅ plusieurs traitements indépendants d'un même événement, consommateur qui peut être arrêté · ❌ une file pour un mail d'alerte : l'humain n'a pas besoin de relecture différée.

```hcl
# Exemple 1 : la file abonnée au topic
resource "aws_sns_topic_subscription" "q" {
  topic_arn            = aws_sns_topic.events.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.events.arn
  raw_message_delivery = true
}
```

- Quiz : Sans `raw_message_delivery`, que contient le corps du message dans la file ?
- [ ] Le message publié, tel quel
- [x] Une enveloppe JSON SNS qui contient le message
- [ ] Le message encodé en base64
- Réponse : une enveloppe JSON (`Type`, `MessageId`, `TopicArn`, `Message`…) : le message d'origine est dans le champ `Message`, à relire avec un second `json.loads`.

## 10. SNS, SQS ou EventBridge : choisir
- Id : sns-sqs-ou-eventbridge
- Sous-thème : choisir
- Type : comparaison
- Niveau : 2
- Profils : data, web, ops
- Voir aussi : sqs-eventbridge-quand-sqs
- Source : data-platform · S1-08
- Définition : SNS pousse un message à des abonnés, SQS garde des messages pour un consommateur, EventBridge route des événements selon leur contenu.
- Contexte : SNS : diffusion immédiate, abonnés humains (email) ou machines, sans stockage. SQS : tampon, reprise, débit lissé, un consommateur par message. EventBridge : règles sur le contenu (`source`, `detail-type`), nombreuses cibles AWS, archive et rejeu. Les alarmes CloudWatch publient vers SNS ; elles émettent aussi des événements EventBridge de changement d'état.
- Usage : ✅ SNS pour un mail d'alerte, SQS pour un travail à faire, EventBridge pour router des événements métier · ❌ SNS pour un travail qui doit survivre à une panne du consommateur.

```python
# Exemple 1 : la question à se poser
def choisir(besoin):
    return {"diffuser à des abonnés": "SNS",
            "garder jusqu'au traitement": "SQS",
            "router selon le contenu": "EventBridge"}[besoin]

choisir("garder jusqu'au traitement")
# → 'SQS'
```

- Quiz : Un mail d'alerte à deux personnes quand une alarme passe en `ALARM` : quel service ?
- [x] SNS
- [ ] SQS
- [ ] EventBridge seul
- Réponse : SNS : c'est la cible native des actions d'alarme, et l'abonnement email livre directement aux deux adresses.

## 11. email : standard seulement, texte non personnalisable
- Id : sns-email-non-personnalisable
- Sous-thème : email
- Type : piège
- Niveau : 2
- Profils : ops
- Voir aussi : sqs-eventbridge-input-transformer
- Source : data-platform · S1-08
- Définition : Un abonnement email n'existe que sur un topic standard, pas FIFO, et SNS ne permet pas de personnaliser le corps du mail.
- Contexte : La doc SNS le dit : l'email sert aux alertes système internes, pas au marketing. Le mail d'une alarme reprend le message de CloudWatch, mis en forme par SNS ; pour un format propre (Slack, Teams), passer par une Lambda abonnée ou AWS Chatbot. Le contenu utile se règle donc à la source : nom d'alarme parlant, `alarm_description` qui donne la marche à suivre.
- Usage : ✅ email pour quelques destinataires techniques · ❌ email sur un topic FIFO, ou pour un message mis en page : Lambda abonnée, Chatbot.

```hcl
# Exemple 1 : le contenu se règle ici
alarm_name        = "${local.prefix}-${each.key}-errors"
alarm_description = "… : lire `aws logs tail …`, puis `make replay`."
```

- Quiz : On veut un mail avec un tableau HTML des journées en échec. Que faire ?
- [ ] Un modèle HTML dans l'abonnement email
- [x] Une Lambda abonnée qui envoie le mail (SES)
- [ ] `email-json` avec un champ `html`
- Réponse : une Lambda abonnée qui met en forme et envoie (par exemple via SES) : l'abonnement email SNS n'accepte aucune personnalisation.

## 12. get-topic-attributes : confirmés ou en attente
- Id : sns-get-topic-attributes
- Sous-thème : topics
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : sns-email-pending-confirmation
- Source : data-platform · S1-08
- Définition : `get-topic-attributes` donne, entre autres, `SubscriptionsConfirmed`, `SubscriptionsPending`, la politique (`Policy`) et la clé KMS du topic.
- Contexte : Une seule commande pour l'état d'un topic : combien d'abonnés reçoivent vraiment, combien attendent un clic, qui peut publier, chiffré ou non. Mesuré sur `data-platform-dev-alerts` : 1 confirmé, 0 en attente, une politique à une instruction, pas de clé KMS. Les compteurs se mettent à jour avec un léger délai après une confirmation.
- Usage : ✅ contrôle après `apply`, audit des topics d'un compte · ❌ lire l'état d'un abonnement précis : `get-subscription-attributes`.

```bash
# Exemple 1 : l'état du topic d'alertes
aws sns get-topic-attributes \
  --topic-arn "$T" \
  --query 'Attributes.{ok:SubscriptionsConfirmed,
    attente:SubscriptionsPending,
    kms:KmsMasterKeyId}'
# → {"ok": "1", "attente": "0",
#    "kms": null}
```

- Quiz : `SubscriptionsConfirmed` vaut `"1"`. Dans quel type la CLI le renvoie-t-elle en JSON ?
- [ ] Un nombre, `1`
- [x] Une chaîne, `"1"`
- [ ] Un booléen, `true`
- Réponse : une chaîne : tous les attributs SNS sont des chaînes (mesuré : `"1"`, `"0"`), à convertir avant de comparer.

## 13. ConfirmationWasAuthenticated : le lien de désabonnement
- Id : sns-desabonnement-non-authentifie
- Sous-thème : email
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : sns-email-pending-confirmation
- Source : data-platform · S1-08
- Définition : `ConfirmationWasAuthenticated = false` (cas du clic dans le mail) : le lien « unsubscribe » de chaque message désabonne sans authentification.
- Contexte : Mesuré sur l'abonnement d'alertes : `PendingConfirmation` à `false`, `ConfirmationWasAuthenticated` à `false`. Quiconque reçoit le mail (liste de diffusion, transfert) peut donc couper l'alerte pour tout le monde d'un clic. AWS documente une parade : confirmer l'abonnement par un appel authentifié (`ConfirmSubscription` avec `AuthenticateOnUnsubscribe`), qui exige alors des droits IAM pour se désabonner.
- Usage : ✅ confirmation authentifiée pour une liste de diffusion ou une astreinte partagée · ❌ abonner une liste d'équipe avec un simple clic : un membre peut tout couper.

```bash
# Exemple 1 : l'état de l'abonnement
aws sns get-subscription-attributes \
  --subscription-arn "$S" \
  --query 'Attributes.{p:PendingConfirmation,
    auth:ConfirmationWasAuthenticated}'
# → {"p": "false", "auth": "false"}
```

- Quiz : Le mail d'alerte est envoyé à une liste d'équipe confirmée par clic. Un membre clique « unsubscribe ». Résultat ?
- [ ] Seul ce membre est retiré
- [x] Plus personne ne reçoit les alertes
- [ ] Refusé : il faut des droits IAM
- Réponse : plus personne : l'abonné est l'adresse de la liste ; non authentifié, le désabonnement passe d'un clic et coupe l'unique abonnement.

## 14. email : 10 messages par seconde, puis suspension
- Id : sns-email-suspension-debit
- Sous-thème : email
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Source : data-platform · S1-08
- Définition : Au-delà de 10 messages par seconde, SNS suspend un abonnement email en `PendingConfirmation` ; sans reconfirmation, il disparaît après 30 jours.
- Contexte : Une rafale d'alarmes (cent fonctions qui échouent en même temps) peut ainsi couper l'abonnement au pire moment, et silencieusement. Une adresse qui rebondit (bounce) est en plus mise en liste de suppression pendant 7 jours. Pour les alertes à fort volume, passer par une Lambda ou un outil d'astreinte qui regroupe ; garder l'email pour peu de messages.
- Usage : ✅ email pour des alertes rares et regroupées (une alarme par job) · ❌ email comme sortie d'un flux d'événements : SQS, Lambda ou outil d'astreinte.

```python
# Exemple 1 : la rafale qui suspend
alarmes_simultanees = 40
limite_par_seconde = 10
alarmes_simultanees > limite_par_seconde
# → True : abonnement suspendu
```

- Quiz : Abonnement suspendu par une rafale, personne ne reconfirme : quand disparaît-il ?
- [ ] Après 48 heures, comme un abonnement neuf
- [ ] Après 7 jours
- [x] Après 30 jours
- [ ] Jamais : il reste en attente
- Réponse : après 30 jours (doc SNS) : un abonnement suspendu pour dépassement de débit reste `PendingConfirmation` 30 jours ; les 48 h ne valent que pour un abonnement jamais confirmé.

## 15. budget et alarme : deux émetteurs, deux politiques
- Id : sns-politique-un-seul-document
- Sous-thème : politique
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : sns-politique-de-topic, sns-source-arn-alarmes
- Source : data-platform · S1-08
- Définition : Chaque service qui publie dans un topic a besoin de sa propre instruction dans la politique : `budgets.amazonaws.com` pour le budget, `cloudwatch.amazonaws.com` pour les alarmes.
- Contexte : Dans data-platform, chaque topic n'a qu'un émetteur et sa politique ne nomme que lui. Réutiliser le topic du budget pour les alarmes, sans ajouter l'instruction CloudWatch, ferait échouer la publication des alarmes en silence côté mail : l'historique `Action` de l'alarme le montrerait. Comme `aws_sns_topic_policy` remplace tout, une seule ressource doit porter toutes les instructions du topic.
- Usage : ✅ un `aws_iam_policy_document` par topic, une instruction par émetteur · ❌ deux `aws_sns_topic_policy` sur le même topic : la dernière appliquée écrase l'autre.

```hcl
# Exemple 1 : deux émetteurs, une politique
data "aws_iam_policy_document" "t" {
  statement {
    sid = "Budgets"
    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }
    actions = ["sns:Publish"]
  }
  statement {
    sid = "CloudWatch"
    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
    actions = ["sns:Publish"]
  }
}
```

- Quiz : Deux ressources `aws_sns_topic_policy` visent le même topic. Quelle politique est en place après l'`apply` ?
- [ ] La fusion des deux
- [x] Celle appliquée en dernier
- [ ] Aucune : Terraform refuse
- Réponse : celle appliquée en dernier : chaque ressource remplace la politique entière ; l'ordre dépend du graphe, et le `plan` suivant voit une dérive.
