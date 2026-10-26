---
type: glossaire
langage: AWS
updated: 2026-10-26
---

# Glossaire AWS

## abonnement SNS
- Définition : Inscription d'une destination (adresse e-mail, file SQS, Lambda, URL) à un topic SNS : elle recevra chaque message publié ; e-mail et HTTP doivent d'abord confirmer.
- Exemple : L'adresse d'alerte de data-platform est abonnée au topic `alerts` : tant que le lien de confirmation n'est pas cliqué, l'abonnement reste `PendingConfirmation`.
- Alias : abonnements SNS, abonnement, abonné
- Carte : sns-email-pending-confirmation

## Access Analyzer
- Définition : Outil d'IAM qui relit une politique avant de la poser (fautes, droits trop larges) et signale les ressources ouvertes à d'autres comptes.
- Exemple : `aws accessanalyzer validate-policy` sur le JSON d'une politique signale un `s3:ListBucket` posé sur `bucket/*`, le mauvais type de ressource.
- Alias : IAM Access Analyzer
- Carte : iam-access-analyzer

## ACL
- Définition : Access Control List : ancien mécanisme de droits posé objet par objet dans S3, désactivé par défaut depuis 2023 au profit des politiques.
- Exemple : Les buckets de data-platform sont en `BucketOwnerEnforced` : une requête qui pose une ACL est refusée, seules les politiques décident.
- Alias : ACLs, Access Control List
- Carte : s3-acl-desactivees

## ACM
- Définition : AWS Certificate Manager : service qui fournit et renouvelle gratuitement les certificats HTTPS utilisés par CloudFront ou un load balancer.
- Exemple : Pour servir l'app de révision sur un domaine perso, il faudrait un certificat ACM créé dans `us-east-1`, la seule région que lit CloudFront.
- Alias : AWS Certificate Manager, certificat ACM
- Carte : cloudfront-certificat-par-defaut

## action IAM
- Définition : Opération AWS nommée dans une politique sous la forme `service:Opération` (`s3:GetObject`, `dynamodb:Query`) ; c'est ce que la politique autorise ou refuse.
- Exemple : La Lambda d'ingestion a l'action `s3:PutObject` sur `bodacc/*`, mais pas `s3:DeleteObject` : elle peut écrire, pas supprimer.
- Alias : actions IAM
- Carte : iam-statement-structure

## ACU
- Définition : Aurora Capacity Unit : unité de capacité d'Aurora Serverless v2 (environ 2 Go de mémoire et le processeur associé), facturée à l'heure.
- Exemple : Avec un minimum à 0 ACU, une base Aurora Serverless v2 se met en pause sans connexion et ne facture plus que son stockage.
- Alias : ACUs, Aurora Capacity Unit
- Carte : dynamodb-aurora-pause

## alarme CloudWatch
- Définition : Règle qui surveille une métrique et passe en `ALARM` quand elle franchit un seuil, puis déclenche une action (souvent un message SNS).
- Exemple : Chaque Lambda de data-platform a une alarme sur `Errors` : une erreur dans les 15 dernières minutes envoie un mail via le topic `alerts`.
- Alias : alarme, alarmes, alarmes CloudWatch
- Carte : cloudwatch-alarme-trois-etats

## alarme composite
- Définition : Alarme CloudWatch dont l'état se calcule à partir d'autres alarmes (ET, OU), pour n'alerter qu'une fois quand plusieurs signaux vont ensemble.
- Exemple : Une alarme composite pourrait n'envoyer de mail que si l'alarme `Errors` ET l'alarme sur les manifests manquants sont en `ALARM`.
- Alias : alarmes composites
- Carte : cloudwatch-actions-changement-etat

## alias de Lambda
- Définition : Nom stable (`live`, `prod`) qui pointe vers une version publiée d'une fonction Lambda ; les appelants visent l'alias, on change la version derrière.
- Exemple : Revenir en arrière consiste à repointer l'alias `live` de la version 4 vers la version 3, sans redéployer de code.
- Alias : alias Lambda
- Carte : lambda-versions-alias

## alias KMS
- Définition : Nom lisible (`alias/data-platform-dev`) qui pointe vers une clé KMS : les humains l'utilisent, alors que l'identifiant réel de la clé change à chaque recréation.
- Exemple : `aws kms describe-key --key-id alias/data-platform-dev` retrouve la clé du projet sans connaître son identifiant.
- Alias : alias de clé KMS
- Carte : kms-alias-ou-arn

## Amazon Linux
- Définition : Distribution Linux maintenue par AWS, système d'exploitation des runtimes Lambda récents (Amazon Linux 2023 pour `python3.12`).
- Exemple : Les roues Python du zip doivent être compilées pour Linux (glibc 2.34 sur Amazon Linux 2023), pas pour le macOS du poste.
- Alias : Amazon Linux 2023
- Carte : lambda-manylinux-glibc

## amr
- Définition : Champ d'un jeton Cognito qui dit comment l'utilisateur s'est authentifié : connecté (`authenticated`) ou invité, puis par quel fournisseur.
- Exemple : La confiance du rôle de l'app de révision exige que `amr` contienne `authenticated` : un visiteur invité ne peut pas l'endosser.
- Carte : cognito-amr-liste

## API Gateway
- Définition : Service qui expose des API HTTP ou REST publiques et transmet chaque requête à un backend, souvent une Lambda (≈ routes d'API Next.js).
- Exemple : Une API « fiche entreprise par SIREN » passerait par API Gateway, qui appelle une Lambda lisant DynamoDB.
- Alias : Amazon API Gateway
- Carte : cognito-ou-api-gateway

## ARN
- Définition : Amazon Resource Name : identifiant unique d'une ressource AWS, de la forme `arn:aws:service:région:compte:ressource` ; les politiques IAM l'utilisent pour viser une ressource.
- Exemple : `arn:aws:s3:::<bucket>/bodacc/*` désigne tous les objets sous `bodacc/` du bucket raw.
- Alias : ARNs, Amazon Resource Name
- Carte : iam-statement-structure

## Athena
- Définition : Service qui exécute du SQL directement sur des fichiers stockés dans S3, sans serveur, facturé aux octets lus.
- Exemple : Une requête Athena compte les annonces BODACC du jour en lisant le préfixe de la partition dans le bucket processed.
- Alias : Amazon Athena
- Carte : glue-athena-cout-au-scanne

## attribut DynamoDB
- Définition : Champ nommé d'un item DynamoDB (`vues`, `ok`) ; hors clés, chaque item porte les siens, sans schéma commun.
- Exemple : L'item de progression d'une carte porte `ok` et `vues`, celui d'un appareil d'autres attributs : la table n'impose rien.
- Alias : attributs DynamoDB
- Carte : dynamodb-item-sans-schema

## Aurora
- Définition : Base de données relationnelle managée d'AWS, compatible PostgreSQL et MySQL ; la variante Serverless v2 ajuste sa capacité à la charge.
- Exemple : Pour relier annonces, entreprises et dirigeants par des jointures SQL, Aurora conviendrait mieux que DynamoDB.
- Alias : Amazon Aurora, Aurora Serverless, Aurora Serverless v2
- Carte : dynamodb-jointures-aurora

## auto scaling
- Définition : Ajustement automatique d'une capacité selon la charge ; pour DynamoDB provisionné, Application Auto Scaling monte ou baisse lectures et écritures réservées.
- Exemple : Une table provisionnée à 10 écritures/s avec auto scaling peut monter à 40 pendant l'ingestion, puis redescendre la nuit.
- Alias : Application Auto Scaling, autoscaling
- Carte : dynamodb-auto-scaling

## AWS Budgets
- Définition : Service qui suit la dépense du compte et envoie une alerte (par SNS ou e-mail) quand un montant prévu ou réel dépasse un seuil.
- Exemple : Le budget de data-platform alerte via le topic `budget-alerts` quand la facture du mois approche 35 $.
- Alias : budget AWS, budgets AWS
- Carte : sns-politique-un-seul-document

## AWS Chatbot
- Définition : Service AWS qui relaie des notifications (alarmes, événements) vers Slack ou Microsoft Teams, mises en forme pour la lecture humaine.
- Exemple : Abonné au topic d'alertes, AWS Chatbot posterait chaque alarme de data-platform dans un canal Slack d'équipe.
- Carte : sns-email-non-personnalisable

## AWS Organizations
- Définition : Service qui regroupe plusieurs comptes AWS sous une organisation, avec facture commune et règles (SCP) imposées aux comptes membres.
- Exemple : En entreprise, dev et prod de data-platform vivraient dans deux comptes d'une même organisation, bornés par des SCP.
- Alias : Organizations, organisation AWS
- Carte : iam-scp-plafond-compte

## BatchWriteItem
- Définition : Opération DynamoDB qui écrit ou supprime jusqu'à 25 items en un appel, sans transaction : une partie peut revenir non traitée.
- Exemple : La synchronisation de l'app de révision envoie son outbox par lots de 25 réponses avec `BatchWriteItem`.
- Alias : batch_writer, BatchWrite
- Carte : dynamodb-batchwriteitem-25

## blocage d'accès public
- Définition : Réglage S3 qui refuse toute politique ou ACL rendant un bucket ou ses objets publics, quel que soit le reste de la configuration.
- Exemple : Tous les buckets de data-platform ont le blocage d'accès public actif : CloudFront lit le bucket du site par OAC, sans l'ouvrir.
- Alias : Block Public Access, blocage de l'accès public
- Carte : s3-politique-https

## boto3
- Définition : Kit de développement (SDK) officiel d'AWS pour Python : il fournit des clients (`boto3.client("s3")`) pour appeler chaque service.
- Exemple : La Lambda d'ingestion écrit ses fichiers dans S3 avec `boto3.client("s3").put_object(...)`.
- Alias : boto3.client, boto3.resource
- Carte : s3-boto3-arguments-nommes

## botocore
- Définition : Bibliothèque bas niveau sur laquelle repose boto3 : signature des requêtes, réessais, modèles JSON décrivant chaque API AWS.
- Exemple : Les 10 réessais par défaut de DynamoDB sont écrits dans `botocore/data/_retry.json`, lus par tout client boto3.
- Carte : dynamodb-reessais-botocore

## bucket
- Définition : Conteneur de stockage S3 au nom unique dans le monde, qui contient des objets identifiés par leur clé.
- Exemple : data-platform a un bucket par zone : `raw` pour les annonces brutes, `processed` pour les données nettoyées, `artifacts` pour les zips de Lambda.
- Alias : buckets, bucket S3, buckets S3
- Carte : s3-cle-sans-dossier

## bucket key
- Définition : Option S3 qui dérive une clé de bucket depuis la clé KMS, pour appeler KMS bien moins souvent qu'une fois par objet : facture et quota baissent.
- Exemple : Les buckets `raw` et `processed` ont `bucket_key_enabled = true` : écrire mille petits fichiers ne coûte presque aucun appel KMS.
- Alias : S3 Bucket Key, clé de bucket
- Carte : kms-bucket-key

## buildspec
- Définition : Fichier YAML versionné avec le code (`buildspec.yml`) qui décrit les phases et commandes d'un build CodeBuild (≈ `.gitlab-ci.yml`).
- Exemple : Le buildspec de revision-pwa installe pnpm, lance les tests puis `make deploy` dans la phase `build`.
- Alias : buildspec.yml
- Carte : codebuild-buildspec-phases

## bus EventBridge
- Définition : Canal qui reçoit des événements et les passe aux règles qui lui sont attachées ; le bus `default` reçoit ceux des services AWS.
- Exemple : Un bus `data-platform` recevrait les événements métier comme « jour ingéré », séparés de ceux d'AWS.
- Alias : bus d'événements, bus personnalisé, event bus
- Carte : sqs-eventbridge-bus-personnalise

## catalogue Glue
- Définition : Glue Data Catalog : registre des tables (schéma, format, emplacement S3, partitions) qu'utilisent Athena, Glue et EMR ; il ne contient aucune donnée.
- Exemple : La table `annonces` du catalogue Glue dit à Athena que les fichiers Parquet sont sous `processed/annonces/`.
- Alias : Glue Data Catalog, catalogue de données Glue
- Carte : glue-athena-table-metadonnees

## CDK
- Définition : Cloud Development Kit : outil d'AWS qui décrit l'infrastructure en TypeScript ou Python, puis la déploie via CloudFormation.
- Exemple : Une équipe TypeScript décrirait ses buckets et Lambdas en CDK ; data-platform a choisi Terraform.
- Alias : AWS CDK, Cloud Development Kit

## chiffrement d'enveloppe
- Définition : Méthode où une clé de données chiffre le fichier localement, puis la clé KMS chiffre seulement cette clé de données, stockée avec le fichier.
- Exemple : S3 en SSE-KMS fait du chiffrement d'enveloppe : un seul appel KMS par objet, quelle que soit sa taille.
- Alias : envelope encryption
- Carte : kms-chiffrement-enveloppe

## classe de stockage
- Définition : Niveau de prix d'un objet S3 ou d'une table DynamoDB : moins cher au stockage, plus cher ou plus lent à la lecture pour les classes froides.
- Exemple : Les annonces brutes de plus d'un an iraient en Standard-IA ou Glacier, rarement relues.
- Alias : classes de stockage, classe S3, classe de table
- Carte : s3-classe-de-stockage

## clé d'accès
- Définition : Identifiant permanent d'un utilisateur IAM (`AKIA…`) avec son secret, utilisé pour signer les appels AWS ; à éviter au profit de rôles temporaires.
- Exemple : data-platform n'en stocke aucune : la CI et les Lambdas utilisent des rôles, le poste une session SSO.
- Alias : clés d'accès, access key, AccessKeyId
- Carte : iam-utilisateur-ou-role

## clé de données
- Définition : Clé de chiffrement générée par KMS (`GenerateDataKey`) pour chiffrer un fichier localement ; elle est stockée chiffrée par la clé KMS à côté des données.
- Exemple : Chaque objet SSE-KMS de `raw` a sa clé de données chiffrée ; la lire demande `kms:Decrypt`.
- Alias : clés de données, data key
- Carte : kms-chiffrement-enveloppe

## clé de partition DynamoDB
- Définition : Attribut de la clé d'une table DynamoDB (`pk`) qui décide dans quelle partition un item est rangé ; toute `Query` donne sa valeur exacte.
- Exemple : Dans la table de progression, la clé de partition est l'identity id de l'utilisateur : chacun lit seulement ses lignes.
- Alias : clés de partition DynamoDB, partition key, pk
- Carte : dynamodb-cle-partition-et-tri

## clé de tri DynamoDB
- Définition : Seconde partie, facultative, de la clé d'une table DynamoDB (`sk`) : elle ordonne les items d'une même partition et permet de lire une plage.
- Exemple : `sk = R#2026-10-25#iam-oidc` range les réponses d'un utilisateur par date, lisibles avec `begins_with`.
- Alias : clés de tri DynamoDB, sort key, sk
- Carte : dynamodb-cle-partition-et-tri

## clé KMS client
- Définition : Clé KMS créée et gérée par le client (`aws_kms_key`) : on écrit sa politique, on peut la désactiver ; elle coûte 1 $ par mois.
- Exemple : La clé `data-platform-dev` chiffre les buckets raw et processed ; la désactiver couperait d'un coup toute lecture.
- Alias : clé client, clés client, clé gérée par le client, customer managed key
- Carte : kms-cle-aws-ou-client

## clé S3
- Définition : Nom complet d'un objet dans un bucket S3, chemin compris (`bodacc/date=2026-10-20/part-0001.jsonl.gz`) ; S3 n'a pas de vrais dossiers.
- Exemple : Rejouer une journée réécrit les mêmes clés S3, ce qui rend l'ingestion idempotente.
- Alias : clés S3, clé d'objet
- Carte : s3-cle-sans-dossier

## CLI AWS
- Définition : Outil en ligne de commande `aws` qui appelle les API AWS depuis un terminal ou un script (`aws s3 ls`, `aws lambda invoke`).
- Exemple : `aws logs tail /aws/lambda/<nom> --follow` affiche en direct les logs d'une Lambda de data-platform.
- Alias : AWS CLI
- Carte : s3-cli-s3-ou-s3api

## client boto3
- Définition : Objet Python créé par `boto3.client("<service>")` qui expose une méthode par opération de l'API du service (`put_object`, `query`).
- Exemple : La Lambda d'ingestion crée son client S3 une fois par environnement d'exécution, puis le réutilise à chaque invocation.
- Alias : client S3, client SDK, clients boto3
- Carte : lambda-client-boto3-cache

## ClientError
- Définition : Exception de botocore levée quand une API AWS répond une erreur ; son code (`AccessDenied`, `NoSuchKey`) est dans `e.response["Error"]["Code"]`.
- Exemple : Tester l'existence d'un manifest : attraper `ClientError` sur `head_object` et vérifier que le code vaut `"404"`.
- Carte : s3-nosuchkey-ou-404

## CloudFront
- Définition : Réseau de diffusion (CDN) d'AWS : il sert des fichiers en HTTPS depuis des serveurs proches des utilisateurs, avec un cache (≈ CDN de Vercel).
- Exemple : L'app de révision et son catalogue sont servis par une distribution CloudFront devant deux buckets S3 privés.
- Alias : Amazon CloudFront
- Carte : cloudfront-distribution-cdn

## CloudFront Functions
- Définition : Petites fonctions JavaScript exécutées par CloudFront sur chaque requête ou réponse, au plus près de l'utilisateur, pour réécrire une URL ou poser un en-tête.
- Exemple : Une CloudFront Function réécrirait `/cours/python` en `/index.html` pour une SPA à routes profondes.
- Alias : CloudFront Function, fonction CloudFront, fonctions CloudFront
- Carte : cloudfront-functions-viewer-request

## CloudTrail
- Définition : Journal d'audit d'AWS : il enregistre les appels d'API du compte (qui, quoi, quand, d'où), pour enquêter ou prouver un accès.
- Exemple : Chaque `kms:Decrypt` sur la clé du projet apparaît dans CloudTrail avec le rôle qui l'a demandé.
- Alias : AWS CloudTrail
- Carte : kms-alias-ou-arn

## CloudWatch
- Définition : Service de supervision d'AWS : métriques, alarmes, tableaux de bord et, avec CloudWatch Logs, journaux des applications.
- Exemple : CloudWatch reçoit les métriques `Errors` des Lambdas de data-platform et leurs logs, et déclenche les alarmes.
- Alias : Amazon CloudWatch
- Carte : cloudwatch-metriques-lambda

## CloudWatch Logs
- Définition : Partie de CloudWatch qui stocke les journaux texte des services, rangés en groupes de logs et en flux.
- Exemple : Tout `print` d'une Lambda part dans CloudWatch Logs, groupe `/aws/lambda/<nom>`, gardé 14 jours.
- Alias : logs CloudWatch
- Carte : lambda-logs-flux-par-environnement

## CodeBuild
- Définition : Service de build managé : il lance un conteneur, exécute les commandes d'un buildspec et facture à la minute (≈ un runner GitLab CI).
- Exemple : À chaque push sur main, CodeBuild construit et déploie l'app de révision.
- Alias : AWS CodeBuild
- Carte : codebuild-buildspec-phases

## CodeCommit
- Définition : Service d'AWS qui héberge des dépôts Git privés, comme GitHub ou GitLab, avec des droits gérés par IAM.
- Exemple : Le dépôt revision-pwa vit sur CodeCommit ; un push sur main déclenche une règle EventBridge qui lance le build.
- Alias : AWS CodeCommit
- Carte : codebuild-source-clone-leger

## CodePipeline
- Définition : Service qui enchaîne des étapes de livraison (source, build, test, déploiement) et se passe des artefacts d'une étape à l'autre.
- Exemple : Pour construire chaque commit et passer le résultat à une étape de déploiement séparée, CodePipeline remplacerait la règle EventBridge.
- Alias : AWS CodePipeline
- Carte : codebuild-no-artifacts

## Cognito
- Définition : Service d'authentification d'AWS : comptes et connexion (user pool), et échange d'un jeton contre des clés AWS temporaires (identity pool).
- Exemple : L'app de révision connecte l'utilisateur avec Cognito, puis appelle DynamoDB avec les clés reçues de l'identity pool.
- Alias : Amazon Cognito
- Carte : cognito-user-ou-identity-pool

## comportement de cache
- Définition : Règle d'une distribution CloudFront qui, pour un motif de chemin (`/content/*`), choisit l'origine, la politique de cache et les règles HTTPS.
- Exemple : Le comportement `/content/*` envoie les requêtes du catalogue au bucket `content`, le comportement par défaut au bucket du site.
- Alias : comportements de cache, cache behavior
- Carte : cloudfront-ordered-cache-behavior

## compte AWS
- Définition : Espace isolé chez AWS, identifié par un numéro à 12 chiffres, qui contient des ressources, des identités IAM et sa propre facture.
- Exemple : data-platform tourne dans le compte de dev de l'auteur ; ses ressources se distinguent des autres projets par le préfixe `data-platform-`.
- Alias : comptes AWS
- Carte : iam-politique-de-ressource

## compte root
- Définition : Identité créée avec le compte AWS (l'e-mail d'inscription), qui a tous les droits ; on la protège par MFA et on ne s'en sert jamais au quotidien.
- Exemple : Sur le compte de data-platform, le root ne sert qu'à l'administration rare ; le travail passe par un utilisateur Identity Center.
- Alias : utilisateur root, root du compte
- Carte : iam-utilisateur-ou-role

## concurrence
- Définition : Nombre d'exécutions d'une fonction Lambda en cours au même instant ; le compte en a 1 000 par région par défaut, partagées entre fonctions.
- Exemple : Dix journées BODACC rejouées ensemble donnent dix exécutions concurrentes, chacune dans son environnement.
- Alias : concurrence Lambda, exécutions concurrentes
- Carte : lambda-concurrence-reservee

## concurrence provisionnée
- Définition : Réglage Lambda qui garde N environnements déjà initialisés en permanence, pour supprimer le démarrage à froid ; facturé même sans trafic.
- Exemple : Une API synchrone sensible à la latence en profiterait ; le pipeline quotidien de data-platform, non.
- Alias : provisioned concurrency
- Carte : lambda-concurrence-provisionnee

## concurrence réservée
- Définition : Réglage Lambda qui fixe le nombre maximal d'exécutions simultanées d'une fonction, pris sur le quota du compte ; gratuit.
- Exemple : `catalog-build` a une concurrence réservée de 1 : deux reconstructions du catalogue ne tournent jamais en même temps.
- Alias : reserved concurrency, reserved_concurrent_executions
- Carte : lambda-concurrence-reservee

## condition IAM
- Définition : Bloc `Condition` d'une politique qui ne laisse s'appliquer le statement que si un test sur la requête est vrai (préfixe, compte d'origine, identité).
- Exemple : La condition `dynamodb:LeadingKeys` = identity id limite chaque utilisateur de l'app à sa propre partition.
- Alias : conditions IAM, bloc Condition, clé de condition
- Carte : iam-condition-s3-prefix

## confused deputy
- Définition : Faille où un service ou un tiers de confiance est amené à agir pour un autre client que le bon ; on la ferme par `aws:SourceAccount` ou `ExternalId`.
- Exemple : Le rôle de EventBridge Scheduler n'accepte que les planifications du compte de data-platform, grâce à `aws:SourceAccount`.
- Alias : tiers confus, problème du tiers confus
- Carte : iam-sourceaccount-service

## context Lambda
- Définition : Second argument du handler Lambda : objet qui donne l'identifiant de l'invocation, le nom de la fonction et le temps restant avant le timeout.
- Exemple : `context.aws_request_id` est ajouté à chaque ligne de log de l'ingestion pour la relier à sa ligne REPORT.
- Alias : context, objet context
- Carte : lambda-handler-event-context

## couche Lambda
- Définition : Archive zip montée dans `/opt` d'une fonction Lambda, pour partager des dépendances entre plusieurs fonctions ; versionnée à part du code.
- Exemple : Une couche contenant pydantic et httpx servirait à toutes les Lambdas Python de data-platform au lieu de les embarquer dans chaque zip.
- Alias : couches Lambda, layer, layers
- Carte : lambda-couches-opt

## crawler
- Définition : Robot Glue qui parcourt des fichiers S3, devine leur schéma et leurs partitions, et met à jour le catalogue Glue ; facturé au temps de calcul.
- Exemple : Un crawler planifié sur `processed/annonces/` découvrirait chaque jour la nouvelle partition, mais pour plus cher qu'un `ADD PARTITION`.
- Alias : crawler Glue, crawlers
- Carte : glue-athena-crawler-ou-projection

## cycle de vie
- Définition : Règles S3 (lifecycle) qui suppriment ou déplacent automatiquement des objets vers une classe moins chère après un nombre de jours.
- Exemple : Une règle de cycle de vie supprime les anciennes versions des objets de `raw` 30 jours après leur remplacement.
- Alias : lifecycle S3, règle lifecycle, règle de cycle de vie, règles de cycle de vie
- Carte : s3-lifecycle-expiration

## DAX
- Définition : DynamoDB Accelerator : cache en mémoire placé devant DynamoDB, compatible avec son API, qui répond en microsecondes ; facturé par nœud à l'heure.
- Exemple : Pour quelques centaines de lectures par jour, DAX est inutile : une table DynamoDB seule répond déjà en millisecondes.
- Alias : DynamoDB Accelerator
- Carte : dynamodb-dax-cache

## delete marker
- Définition : Marqueur que S3 pose à la place d'un objet supprimé dans un bucket versionné : l'objet semble absent, mais ses versions restent récupérables.
- Exemple : Un `aws s3 rm` sur `raw`, versionné, pose un delete marker ; l'ancienne version de la partition reste facturée et restaurable.
- Alias : delete markers, marqueur de suppression
- Carte : s3-versioning-suppression

## DeleteItem
- Définition : Opération DynamoDB qui supprime un item par sa clé complète ; elle réussit aussi si l'item n'existe pas.
- Exemple : Retirer un appareil de l'app de révision supprime ses lignes de compteurs une par une avec `DeleteItem`.
- Alias : delete_item
- Carte : dynamodb-deleteitem-idempotent

## démarrage à froid
- Définition : Création d'un nouvel environnement Lambda (chargement du code, imports, init) avant la première invocation qu'il sert ; il ajoute de la latence.
- Exemple : Une ligne REPORT avec `Init Duration` 300 ms signale un démarrage à froid de `catalog-build`.
- Alias : cold start, démarrages à froid
- Carte : lambda-cold-start-init

## Deny explicite
- Définition : Statement `Effect: Deny` qui correspond à la requête : il refuse l'accès quoi que disent tous les `Allow`, administrateur compris.
- Exemple : Un Deny explicite sur `s3:*` quand `aws:SecureTransport = false` interdit toute requête en HTTP clair sur les buckets de données.
- Alias : Deny, refus explicite
- Carte : iam-deny-explicite-gagne

## destination d'échec
- Définition : Cible (file SQS, topic SNS, bus EventBridge) où Lambda envoie un événement asynchrone abandonné, avec l'erreur, pour pouvoir le rejouer.
- Exemple : Une destination `on_failure` vers SQS garderait l'événement S3 qui a échoué trois fois, au lieu de le perdre.
- Alias : destination on_failure, destinations Lambda
- Carte : lambda-destinations-ou-dlq

## dimension
- Définition : Paire nom-valeur qui distingue les séries d'une métrique CloudWatch : `FunctionName = ingest-bodacc` isole les erreurs d'une seule fonction.
- Exemple : L'alarme d'erreurs de l'ingestion lit sa dimension `FunctionName` dans l'output du module, jamais tapée à la main.
- Alias : dimensions
- Carte : cloudwatch-dimension-mal-ecrite

## distribution
- Définition : Configuration CloudFront qui sert un domaine : ses origines, ses comportements de cache, son certificat HTTPS.
- Exemple : Une seule distribution sert l'app de révision et son catalogue sur le même domaine `dxxxx.cloudfront.net`.
- Alias : distribution CloudFront, distributions
- Carte : cloudfront-distribution-cdn

## DLQ
- Définition : Dead-letter queue : file où l'on met de côté les messages ou événements qui ont échoué trop de fois, pour les analyser et les rejouer.
- Exemple : Une DLQ derrière la file des jours à rejouer garde un jour qui échoue en boucle, sans bloquer les autres.
- Alias : dead-letter queue, file de lettres mortes, DLQs
- Carte : sqs-eventbridge-dlq-max-receive

## DPU
- Définition : Data Processing Unit : unité de calcul de Glue (4 vCPU, 16 Go), facturée à l'heure, à la seconde près.
- Exemple : Un job Glue de 10 minutes sur 2 DPU coûte environ 2 × 1/6 × 0,44 $ à Paris.
- Alias : DPUs, Data Processing Unit
- Carte : glue-athena-glue-ou-emr

## DynamoDB
- Définition : Base de données NoSQL serverless d'AWS : chaque item se lit par sa clé en quelques millisecondes, facturée à la requête (≈ une `Map` géante managée).
- Exemple : L'app de révision stocke la progression de chaque utilisateur dans une table DynamoDB, une partition par identity id.
- Alias : Amazon DynamoDB, table DynamoDB
- Carte : dynamodb-quand-choisir

## DynamoDB Streams
- Définition : Flux qui publie chaque modification d'item d'une table DynamoDB, gardée 24 h, lisible par une Lambda pour réagir au changement.
- Exemple : Un flux sur la table des procédures déclencherait une Lambda d'alerte quand le statut d'une procédure change.
- Alias : flux DynamoDB, stream DynamoDB, Streams
- Carte : dynamodb-streams-vues

## EBS
- Définition : Elastic Block Store : disque réseau attaché à une machine virtuelle EC2, facturé à la taille, qu'il serve ou non.
- Exemple : Un volume EBS chiffré pose un grant sur la clé KMS pour pouvoir déchiffrer au nom de l'instance.
- Alias : Elastic Block Store, volume EBS
- Carte : kms-grant

## ECR
- Définition : Elastic Container Registry : registre privé d'images Docker d'AWS, d'où Lambda, ECS ou CodeBuild tirent leurs images.
- Exemple : Une Lambda PySpark en image conteneur serait poussée dans ECR, puis référencée par `image_uri`.
- Alias : Elastic Container Registry, registre ECR
- Carte : lambda-zip-couche-ou-image

## ECS
- Définition : Elastic Container Service : service qui lance et supervise des conteneurs Docker, sur des serveurs EC2 ou en serverless avec Fargate.
- Exemple : Step Functions peut lancer une tâche ECS pour un traitement trop long pour Lambda et attendre sa fin.
- Alias : Elastic Container Service, tâche ECS
- Carte : lambda-fargate-conteneur-long

## EFS
- Définition : Elastic File System : système de fichiers réseau partagé (lecture, écriture, verrous) montable par plusieurs serveurs, conteneurs ou Lambdas.
- Exemple : Si plusieurs tâches devaient partager des fichiers avec `seek` et verrous, EFS conviendrait, S3 non.
- Alias : Elastic File System
- Carte : s3-data-lake-choisir

## ElastiCache
- Définition : Service de cache en mémoire managé (Redis, Valkey, Memcached), qui répond en microsecondes ; il a un coût même sans requête.
- Exemple : Pour 200 appels par jour, un cluster ElastiCache coûterait plus que la table DynamoDB qu'il protège.
- Alias : Amazon ElastiCache
- Carte : dynamodb-cache-elasticache

## élévation de privilège
- Définition : Faille où une identité obtient plus de droits qu'on ne lui en a donné, par exemple en confiant un rôle administrateur à un service qu'elle crée.
- Exemple : `iam:PassRole` borné au seul rôle de la Lambda empêche de créer une fonction avec un rôle administrateur.
- Alias : escalade de privilèges
- Carte : iam-passrole

## EMF
- Définition : Embedded Metric Format : format de ligne de log JSON que CloudWatch transforme seul en métrique, sans appel `PutMetricData`.
- Exemple : Une ligne EMF écrite par l'ingestion pourrait publier le nombre d'annonces du jour comme métrique.
- Alias : Embedded Metric Format
- Carte : cloudwatch-metriques-lambda

## EMR
- Définition : Service d'AWS qui exécute Spark ou Hadoop sur des clusters, ou en mode Serverless facturé au vCPU et à la mémoire.
- Exemple : Un job Spark de normalisation BODACC sur de gros volumes pourrait tourner sur EMR Serverless, lancé par Step Functions.
- Alias : EMR Serverless, Amazon EMR
- Carte : glue-athena-glue-ou-emr

## endpoint VPC
- Définition : Point d'accès privé qui laisse un VPC joindre un service AWS sans passer par Internet ; le type Gateway (S3, DynamoDB) est gratuit.
- Exemple : Une Lambda en VPC qui lit S3 par un endpoint Gateway évite une NAT Gateway à 36 $ par mois.
- Alias : endpoints VPC, VPC endpoint, endpoint Gateway
- Carte : couts-nat-gateway-endpoint

## environnement d'exécution
- Définition : Micro-machine isolée où Lambda charge le code ; gardée « chaude » un moment, elle sert plusieurs invocations successives et garde `/tmp` et le code de module.
- Exemple : Le client S3 de l'ingestion est créé une fois par environnement d'exécution, puis réutilisé tant qu'il reste chaud.
- Alias : environnements d'exécution, conteneur chaud, environnement chaud
- Carte : lambda-tmp-ephemere

## espace de noms CloudWatch
- Définition : Préfixe qui regroupe les métriques CloudWatch d'un service (`AWS/Lambda`, `AWS/DynamoDB`) ou d'une application.
- Exemple : Les métriques `Errors` et `Duration` des fonctions de data-platform sont dans l'espace de noms `AWS/Lambda`.
- Alias : namespace CloudWatch
- Carte : cloudwatch-widget-point-recopie

## event source mapping
- Définition : Lecteur géré par Lambda qui interroge une file SQS ou un flux (Kinesis, DynamoDB Streams) et invoque la fonction par lots.
- Exemple : Une file de jours à rejouer serait consommée par un event source mapping qui invoque l'ingestion avec quelques messages à la fois.
- Alias : event source mappings
- Carte : lambda-event-source-mapping

## EventBridge
- Définition : Service d'événements d'AWS : il route des événements vers des cibles selon des règles sur leur contenu, et planifie des tâches (Scheduler).
- Exemple : Un push sur main du dépôt revision-pwa produit un événement que EventBridge transmet à CodeBuild.
- Alias : Amazon EventBridge, CloudWatch Events
- Carte : sqs-eventbridge-regle-ou-scheduler

## EventBridge Pipes
- Définition : Service EventBridge qui relie une source (file, flux) à une cible avec filtrage et transformation, sans Lambda intermédiaire.
- Exemple : Un pipe pourrait lire une file SQS d'annonces, filtrer et reformater chaque message, puis lancer Step Functions.
- Carte : sqs-eventbridge-input-transformer

## EventBridge Scheduler
- Définition : Service qui déclenche une cible AWS (Lambda, Step Functions) à heure fixe (`cron`), à intervalle (`rate`) ou une seule fois (`at`).
- Exemple : L'ingestion BODACC est lancée chaque matin à 6 h, heure de Paris, par une planification EventBridge Scheduler.
- Alias : Scheduler, planification Scheduler
- Carte : sqs-eventbridge-scheduler-cron

## expression DynamoDB
- Définition : Petit texte qui décrit, côté serveur, une condition ou une modification d'item (`SET vues = vues + :un`), avec des jetons `:v` et `#n`.
- Exemple : `ConditionExpression="attribute_not_exists(pk)"` n'écrit une annonce que si elle n'existe pas déjà.
- Alias : expressions DynamoDB, UpdateExpression, ConditionExpression, KeyConditionExpression
- Carte : dynamodb-updateexpression-clauses

## Fargate
- Définition : Mode serverless d'ECS : il exécute un conteneur sans serveur à gérer ni limite de durée, facturé au vCPU et à la mémoire réservés.
- Exemple : Une reprise d'historique BODACC de plusieurs heures, trop longue pour Lambda, tournerait dans une tâche Fargate.
- Alias : ECS Fargate, AWS Fargate
- Carte : lambda-fargate-conteneur-long

## file FIFO
- Définition : File SQS qui garde l'ordre des messages d'un même groupe et supprime les doublons pendant 5 minutes, à débit limité.
- Exemple : Des événements successifs d'un même SIREN passeraient par une file FIFO avec le SIREN comme groupe.
- Alias : FIFO, files FIFO, topic FIFO
- Carte : sqs-eventbridge-standard-ou-fifo

## FilterExpression
- Définition : Filtre DynamoDB appliqué après la lecture : il retire des items de la réponse sans réduire ce qui est lu ni facturé.
- Exemple : Une `Query` qui lit 3 items et filtre sur `ok = true` en renvoie 1 mais paie les 3.
- Alias : filtre DynamoDB
- Carte : dynamodb-filterexpression-apres-lecture

## Firehose
- Définition : Amazon Data Firehose : service qui reçoit un flux de données et l'écrit par lots dans S3 (ou ailleurs), sans code ni serveur.
- Exemple : Firehose pourrait archiver dans le data lake chaque événement « annonce publiée », regroupé en fichiers Parquet.
- Alias : Data Firehose, Amazon Data Firehose, Kinesis Data Firehose
- Carte : sqs-eventbridge-firehose-ou-kinesis

## flux de logs
- Définition : Suite de lignes de log écrite par une même source (un environnement Lambda, un build) à l'intérieur d'un groupe de logs.
- Exemple : Chaque environnement d'exécution de l'ingestion écrit dans son propre flux du groupe `/aws/lambda/<nom>`.
- Alias : flux de log, log stream, log streams
- Carte : lambda-logs-flux-par-environnement

## GetItem
- Définition : Opération DynamoDB qui lit un seul item par sa clé complète (clé de partition, et clé de tri si la table en a une).
- Exemple : Lire la fiche d'un SIREN connu sur une table à clé simple se fait par un `GetItem`.
- Alias : get_item
- Carte : dynamodb-getitem-cle-complete

## Glacier
- Définition : Famille de classes de stockage S3 très bon marché pour l'archive rarement relue ; certaines demandent une restauration avant lecture.
- Exemple : Les annonces brutes de plusieurs années, relues seulement en cas d'audit, pourraient passer en Glacier.
- Alias : S3 Glacier, Glacier Instant Retrieval, Glacier Flexible Retrieval
- Carte : s3-classe-de-stockage

## Glue
- Définition : Service serverless d'AWS pour préparer les données : jobs Spark (ETL), catalogue des tables, crawlers ; facturé au temps de calcul.
- Exemple : Un job Glue pourrait transformer chaque nuit les annonces brutes JSONL en Parquet partitionné.
- Alias : AWS Glue, Glue ETL, job Glue
- Carte : glue-athena-glue-ou-emr

## grant
- Définition : Autorisation KMS temporaire et ciblée qui laisse un principal utiliser une clé pour certaines opérations, sans modifier la politique de clé.
- Exemple : Un job EMR recevrait un grant `Decrypt` sur la clé du projet le temps d'un traitement, retiré ensuite.
- Alias : grant KMS, grants
- Carte : kms-grant

## groupe de logs
- Définition : Conteneur CloudWatch Logs qui rassemble les flux de logs d'une ressource, avec une durée de rétention.
- Exemple : Terraform crée le groupe `/aws/lambda/<nom>` de chaque Lambda avec 14 jours de rétention.
- Alias : groupes de logs, log group, log groups
- Carte : lambda-log-group-avant-fonction

## GSI
- Définition : Index secondaire global : copie d'une table DynamoDB rangée sous une autre clé, pour lire efficacement par un autre attribut.
- Exemple : Un GSI de clé `tribunal` permettrait de lire les annonces d'un tribunal sans parcourir toute la table.
- Alias : GSIs, index secondaire global, index secondaires globaux, global secondary index
- Carte : dynamodb-gsi-autre-cle

## handler
- Définition : Fonction de votre code que Lambda appelle à chaque invocation, avec l'événement reçu et le `context` (`handler = "fichier.fonction"`).
- Exemple : Le handler de l'ingestion lit la date dans l'événement, puis appelle `ingest_day`, testable sans Lambda.
- Alias : handler Lambda, handlers
- Carte : lambda-handler-event-context

## HSM
- Définition : Hardware Security Module : boîtier matériel qui crée et garde des clés de chiffrement sans jamais les laisser sortir.
- Exemple : Les clés KMS de data-platform vivent dans les HSM d'AWS : on demande à KMS de chiffrer, on ne voit jamais la clé.
- Alias : Hardware Security Module
- Carte : kms-cle-ne-sort-jamais

## IAM
- Définition : Identity and Access Management : service qui gère qui (utilisateurs, rôles) peut faire quelle action sur quelle ressource AWS, par des politiques.
- Exemple : IAM n'autorise la Lambda d'ingestion qu'à écrire sous `bodacc/` du bucket raw et dans son groupe de logs.
- Alias : AWS IAM, Identity and Access Management
- Carte : iam-role-confiance-permissions

## identity id
- Définition : Identifiant stable (`eu-west-3:<uuid>`) qu'un identity pool Cognito attribue à un utilisateur, le même sur tous ses appareils.
- Exemple : L'app de révision range la progression sous l'identity id : iPhone et Mac écrivent dans la même partition.
- Alias : IdentityId, identity ids
- Carte : cognito-identity-id-vs-sub

## identity pool
- Définition : Partie de Cognito qui échange un jeton de connexion contre des clés AWS temporaires d'un rôle IAM, pour appeler AWS sans backend.
- Exemple : L'identity pool de l'app de révision donne au navigateur des clés limitées à la partition DynamoDB de l'utilisateur.
- Alias : identity pools, pool d'identités
- Carte : cognito-user-ou-identity-pool

## index creux
- Définition : Index DynamoDB qui ne contient que les items portant son attribut de clé : une liste filtrée maintenue gratuitement.
- Exemple : L'attribut `en_cours`, posé seulement sur les procédures ouvertes, fait d'un GSI la liste des procédures ouvertes.
- Alias : index creux DynamoDB, sparse index
- Carte : dynamodb-index-creux

## Intelligent-Tiering
- Définition : Classe de stockage S3 qui déplace seule chaque objet vers un niveau moins cher selon ses accès, contre un petit frais de suivi par objet.
- Exemple : Pour des exports dont on ne sait pas s'ils seront relus, Intelligent-Tiering évite de choisir la classe à l'avance.
- Alias : S3 Intelligent-Tiering
- Carte : s3-classe-de-stockage

## invalidation
- Définition : Demande à CloudFront de retirer des chemins de ses caches avant leur expiration, pour servir tout de suite la nouvelle version.
- Exemple : `make deploy` lance une invalidation `/*` après avoir envoyé la nouvelle version de l'app de révision.
- Alias : invalidations, invalidation CloudFront
- Carte : cloudfront-invalidation

## invocation
- Définition : Une exécution d'une fonction Lambda pour un événement donné ; chaque invocation est comptée, facturée et journalisée.
- Exemple : Le rejeu d'une journée BODACC est une nouvelle invocation de l'ingestion, avec son propre identifiant.
- Alias : invocations
- Carte : lambda-trois-modes-invocation

## invocation asynchrone
- Définition : Appel où Lambda met l'événement dans une file interne et répond aussitôt `202` ; elle réessaie seule 2 fois en cas d'erreur.
- Exemple : EventBridge Scheduler et les notifications S3 invoquent les Lambdas de data-platform en asynchrone.
- Alias : invocations asynchrones
- Carte : lambda-async-deux-retries

## invocation synchrone
- Définition : Appel où l'appelant attend la fin de la fonction et reçoit sa réponse ou son erreur ; Lambda ne réessaie rien.
- Exemple : `make replay` invoque l'ingestion en synchrone : l'erreur s'affiche dans le terminal, sans retry automatique.
- Alias : invocations synchrones
- Carte : lambda-trois-modes-invocation

## item
- Définition : Une ligne d'une table DynamoDB, identifiée par sa clé ; elle pèse au plus 400 Ko et porte ses propres attributs.
- Exemple : Chaque réponse à une carte de révision est un item `R#<date>#<carte>` dans la partition de l'utilisateur.
- Alias : items, ligne DynamoDB
- Carte : dynamodb-item-sans-schema

## jeton de session
- Définition : Troisième pièce des clés temporaires STS (`SessionToken`), à envoyer avec la clé d'accès `ASIA…` et son secret, sinon la requête est refusée.
- Exemple : L'app de révision envoie le jeton de session dans l'en-tête `x-amz-security-token` de chaque appel DynamoDB.
- Alias : SessionToken, session token, AWS_SESSION_TOKEN
- Carte : api-security-token

## JMESPath
- Définition : Langage de requête sur du JSON qu'utilise l'option `--query` de la CLI AWS pour filtrer ou extraire des champs de la réponse.
- Exemple : `aws s3api list-objects-v2 … --query 'length(CommonPrefixes)'` compte les partitions BODACC du bucket raw.
- Carte : s3-query-jmespath

## Kinesis
- Définition : Kinesis Data Streams : flux de données temps réel découpé en shards, gardé de 24 h à 365 jours, que plusieurs consommateurs lisent et relisent.
- Exemple : Deux équipes qui doivent lire et rejouer le même flux d'annonces brancheraient chacune un lecteur sur un flux Kinesis.
- Alias : Kinesis Data Streams, Amazon Kinesis
- Carte : dynamodb-kinesis-data-streams

## KMS
- Définition : Key Management Service : service qui crée et garde des clés de chiffrement ; chaque usage passe par une API autorisée par IAM et tracée.
- Exemple : Les buckets raw et processed de data-platform sont chiffrés par une clé KMS du projet.
- Alias : AWS KMS, Key Management Service, clé KMS, clés KMS
- Carte : kms-cle-ne-sort-jamais

## Lambda
- Définition : Service qui exécute votre fonction à chaque événement, sans serveur à gérer, 15 minutes au plus, facturé à la milliseconde (≈ une fonction serverless Vercel).
- Exemple : L'ingestion BODACC de data-platform est une Lambda Python lancée chaque matin.
- Alias : AWS Lambda, Lambdas, service Lambda
- Carte : lambda-quand-la-choisir

## Lambda@Edge
- Définition : Fonctions Lambda exécutées par CloudFront près des utilisateurs, plus puissantes que CloudFront Functions (réseau, corps), mais plus chères et plus lentes.
- Exemple : Appeler une API pour décider d'une redirection demanderait Lambda@Edge ; réécrire une URL, une CloudFront Function suffit.
- Carte : cloudfront-functions-viewer-request

## lecture éventuellement cohérente
- Définition : Lecture DynamoDB par défaut : rapide et moitié moins chère, mais elle peut rendre l'ancienne valeur juste après une écriture.
- Exemple : Afficher les statistiques de révision tolère une lecture éventuellement cohérente ; une seconde de retard ne gêne pas.
- Alias : lecture éventuelle, lectures éventuellement cohérentes, cohérence éventuelle
- Carte : dynamodb-lecture-forte

## lecture fortement cohérente
- Définition : Lecture DynamoDB (`ConsistentRead=True`) qui voit toutes les écritures réussies avant elle, pour un coût double ; impossible sur un GSI.
- Exemple : Relire un compteur juste après l'avoir incrémenté demande une lecture fortement cohérente.
- Alias : lecture forte, lectures fortes, ConsistentRead
- Carte : dynamodb-lecture-forte

## ligne REPORT
- Définition : Ligne écrite par Lambda dans les logs à la fin de chaque invocation : durée, durée facturée, mémoire utilisée et, à froid, durée d'init.
- Exemple : `REPORT … Duration: 4563 ms … Max Memory Used: 121 MB` sert à régler la mémoire de l'ingestion.
- Alias : REPORT, lignes REPORT
- Carte : lambda-ligne-report

## Logs Insights
- Définition : Langage de requête de CloudWatch qui cherche, filtre et agrège les lignes de plusieurs flux de logs à la fois.
- Exemple : Une requête Logs Insights retrouve toutes les lignes d'une invocation de l'ingestion par son `request_id`.
- Alias : CloudWatch Logs Insights
- Carte : lambda-aws-request-id

## LSI
- Définition : Index secondaire local : autre clé de tri sur la même clé de partition qu'une table DynamoDB ; déclaré seulement à la création de la table.
- Exemple : Un LSI `par-date` trierait les procédures d'un SIREN par date, avec lecture forte possible.
- Alias : LSIs, index secondaire local, index secondaires locaux
- Carte : dynamodb-lsi-ou-gsi-creation

## machine d'états
- Définition : Définition d'un workflow Step Functions : une suite d'états (tâches, choix, attentes) avec leurs reprises et leurs branches d'erreur.
- Exemple : La machine d'états du pipeline enchaîne ingestion, normalisation et publication, avec `Retry` sur les erreurs passagères.
- Alias : machines d'états, state machine, workflow Step Functions
- Carte : step-functions-quand-orchestrer

## métrique
- Définition : Série de valeurs numériques horodatées que CloudWatch stocke et agrège (`Errors`, `Duration`) ; une alarme la surveille.
- Exemple : Lambda publie seule la métrique `Errors` de chaque fonction de data-platform, sans une ligne de code.
- Alias : métriques, métrique CloudWatch, métriques CloudWatch
- Carte : cloudwatch-metriques-lambda

## moindre privilège
- Définition : Principe qui donne à chaque identité seulement les actions et ressources dont elle a besoin, pour borner les dégâts d'un bug ou d'une attaque.
- Exemple : Le rôle de build de revision-pwa ne peut écrire que dans le bucket du site : une dépendance npm piratée n'atteint rien d'autre.
- Alias : principe du moindre privilège, least privilege
- Carte : iam-moindre-privilege-build

## multipart upload
- Définition : Envoi d'un gros objet S3 en plusieurs parts envoyées séparément puis assemblées ; boto3 le fait seul au-delà de 8 Mo.
- Exemple : Un fichier BODACC de 30 Mo part en multipart upload ; sur un bucket SSE-KMS, il faut alors aussi `kms:Decrypt`.
- Alias : multipart, upload multipart, envoi multipart, multipart uploads
- Carte : s3-multipart-incomplet

## MWAA
- Définition : Amazon Managed Workflows for Apache Airflow : Airflow hébergé par AWS ; un environnement tourne et se paie en continu, même sans tâche.
- Exemple : Pour un premier pipeline de quatre étapes, MWAA coûterait plus que tout le budget de data-platform ; Step Functions suffit.
- Alias : Managed Workflows for Apache Airflow
- Carte : step-functions-mwaa-airflow

## NAT Gateway
- Définition : Passerelle qui laisse les ressources d'un sous-réseau privé sortir vers Internet ; facturée à l'heure et au Go, même sans trafic.
- Exemple : À Paris, une NAT Gateway coûte environ 36 $ par mois avant le premier octet, plus que le budget de data-platform.
- Alias : NAT, passerelle NAT
- Carte : couts-nat-gateway-endpoint

## notification S3
- Définition : Réglage d'un bucket qui envoie un événement (vers Lambda, SQS, SNS ou EventBridge) à chaque création ou suppression d'objet filtrée.
- Exemple : Déposer un fichier de cartes sous `sources/` déclenche la Lambda `catalog-build` par une notification S3.
- Alias : notifications S3, événement S3, événements S3
- Carte : s3-notification-boucle

## OAC
- Définition : Origin Access Control : réglage CloudFront qui signe ses requêtes vers un bucket S3, pour que ce bucket reste privé et n'accepte qu'elles.
- Exemple : Les buckets de l'app de révision ne sont lisibles que par la distribution, grâce à l'OAC et à la politique de bucket.
- Alias : Origin Access Control
- Carte : cloudfront-oac-signature

## Object Lock
- Définition : Option S3 qui interdit de supprimer ou d'écraser une version d'objet pendant une durée de rétention (stockage WORM).
- Exemple : Une archive réglementaire d'annonces serait protégée par Object Lock, même contre l'administrateur en mode `COMPLIANCE`.
- Alias : S3 Object Lock
- Carte : s3-object-lock

## objet S3
- Définition : Fichier stocké dans un bucket S3, identifié par sa clé, avec son contenu et ses métadonnées (taille, type, ETag).
- Exemple : Chaque partition BODACC contient un objet `part-0001.jsonl.gz` et un objet `_MANIFEST.json`.
- Alias : objets S3
- Carte : s3-cle-sans-dossier

## offre gratuite
- Définition : Quotas d'usage qu'AWS ne facture pas chaque mois (Free Tier), par exemple 100 minutes de build CodeBuild ou un million d'invocations Lambda.
- Exemple : Avec des builds de 2 minutes facturées, l'offre gratuite de CodeBuild couvre une cinquantaine de déploiements par mois.
- Alias : Free Tier, offre gratuite AWS
- Carte : codebuild-minutes-arrondies

## OIDC
- Définition : OpenID Connect : standard où un fournisseur de confiance (GitHub, Google, Cognito) prouve l'identité d'un utilisateur ou d'une machine par un jeton signé (JWT).
- Exemple : GitHub Actions présente son jeton OIDC à AWS et reçoit un rôle temporaire, sans aucune clé stockée dans le dépôt.
- Alias : OpenID Connect, fournisseur OIDC, jeton OIDC
- Carte : iam-oidc-ci-sans-cle

## OpenSearch
- Définition : Service de recherche plein texte managé (fork d'Elasticsearch) : il découpe les textes en mots et trie les résultats par pertinence.
- Exemple : Chercher « liquidation boulangerie » dans le texte des annonces demanderait OpenSearch, pas DynamoDB.
- Alias : Amazon OpenSearch Service, OpenSearch Serverless
- Carte : dynamodb-recherche-plein-texte

## origine CloudFront
- Définition : Source où CloudFront va chercher un fichier absent de son cache : un bucket S3, une API ou un serveur.
- Exemple : La distribution de l'app de révision a deux origines : le bucket du site et le bucket du catalogue.
- Alias : origines CloudFront
- Carte : cloudfront-origine-bucket-rest

## Parameter Store
- Définition : Partie de Systems Manager qui stocke des paramètres de configuration, en clair ou chiffrés par KMS, lus par le code au démarrage.
- Exemple : Un jeton d'API serait rangé dans Parameter Store et lu par la Lambda, jamais écrit en variable d'environnement.
- Alias : SSM Parameter Store, Systems Manager Parameter Store
- Carte : codebuild-variables-plaintext

## PartiQL
- Définition : Langage de requête compatible SQL que DynamoDB accepte ; il ne lit qu'une table à la fois, sans jointure.
- Exemple : `SELECT * FROM annonces WHERE pk = 'SIREN#483609327'` en PartiQL fait la même chose qu'une `Query`.
- Carte : dynamodb-jointures-aurora

## partition chaude
- Définition : Partition DynamoDB qui reçoit une part trop grande du trafic et atteint sa limite (1 000 écritures/s), d'où du throttling.
- Exemple : Écrire toutes les annonces du jour sous la même clé de partition `date` créerait une partition chaude.
- Alias : partitions chaudes, clé chaude
- Carte : dynamodb-debit-par-partition

## partition DynamoDB
- Définition : Unité de stockage interne de DynamoDB : les items de même clé de partition y sont rangés ensemble, chaque partition ayant un débit maximal.
- Exemple : Toutes les lignes d'un utilisateur de l'app de révision vivent dans la même partition DynamoDB, lue d'une seule `Query`.
- Alias : partitions DynamoDB
- Carte : dynamodb-cle-partition-et-tri

## partition projection
- Définition : Réglage Athena qui calcule les partitions d'une table à partir de règles (plage de dates, format) au lieu de les enregistrer une par une.
- Exemple : Avec la projection sur `dt`, Athena voit chaque nouveau jour d'annonces sans `ADD PARTITION` quotidien.
- Alias : projection de partitions
- Carte : glue-athena-partition-projection

## permission boundary
- Définition : Politique posée sur un rôle ou un utilisateur qui plafonne ses droits sans en accorder aucun : il faut un `Allow` des deux côtés.
- Exemple : Une CI autorisée à créer des rôles devrait leur poser une permission boundary, pour qu'aucun ne dépasse le plafond.
- Alias : permissions boundary, boundary
- Carte : iam-permission-boundary

## permission set
- Définition : Modèle de droits d'IAM Identity Center qu'AWS transforme en rôle dans chaque compte où un utilisateur est affecté.
- Exemple : L'auteur de data-platform se connecte avec le permission set `AdministratorAccess` sur son compte de dev.
- Alias : permission sets, jeu d'autorisations
- Carte : iam-identity-center

## PITR
- Définition : Point-in-time recovery : sauvegarde continue d'une table DynamoDB, restaurable à la seconde près sur les 35 derniers jours.
- Exemple : Un script qui écrase 1 000 items par erreur se répare en restaurant la table, avec PITR, à la minute d'avant.
- Alias : point-in-time recovery, point_in_time_recovery
- Carte : dynamodb-pitr-restauration

## point de présence
- Définition : Site de CloudFront proche des utilisateurs, où les fichiers sont mis en cache et servis sans revenir à l'origine.
- Exemple : Un utilisateur à Paris reçoit l'app de révision depuis un point de présence parisien de CloudFront.
- Alias : points de présence, PoP, edge location
- Carte : cloudfront-distribution-cdn

## politique d'identité
- Définition : Politique IAM attachée à un utilisateur ou un rôle : elle dit ce que cette identité peut faire, sans champ `Principal`.
- Exemple : La politique d'identité du rôle de l'ingestion lui permet `s3:PutObject` sous `bodacc/` du bucket raw.
- Alias : politiques d'identité, politique basée sur l'identité
- Carte : iam-politique-de-ressource

## politique de bucket
- Définition : Politique de ressource attachée à un bucket S3 : elle nomme qui (`Principal`) peut faire quoi sur le bucket et ses objets.
- Exemple : La politique du bucket du site n'autorise `s3:GetObject` qu'à la distribution CloudFront de l'app.
- Alias : politiques de bucket, bucket policy
- Carte : cloudfront-bucket-source-arn

## politique de cache
- Définition : Réglage CloudFront qui fixe la durée de cache (TTL minimum, défaut, maximum) et ce qui distingue deux objets en cache.
- Exemple : La politique `CachingOptimized` ignore la query string : `/?langage=AWS` et `/` partagent la même entrée.
- Alias : politiques de cache, cache policy
- Carte : cloudfront-cle-de-cache-query

## politique de clé
- Définition : Politique de ressource d'une clé KMS : elle fait toujours autorité et dit qui peut l'utiliser ou l'administrer, ou délègue à IAM.
- Exemple : La politique par défaut de la clé du projet délègue à IAM : `kms:Decrypt` dans le rôle de la Lambda suffit.
- Alias : politiques de clé, key policy
- Carte : kms-politique-de-cle-iam

## politique de confiance
- Définition : Politique d'un rôle IAM qui dit qui a le droit de l'endosser (un service, un compte, un fournisseur OIDC) ; elle n'accorde aucune action.
- Exemple : La politique de confiance du rôle de l'ingestion n'accepte que `lambda.amazonaws.com`.
- Alias : trust policy, politique d'approbation
- Carte : iam-role-confiance-permissions

## politique de ressource
- Définition : Politique attachée à une ressource (bucket, clé KMS, file, fonction) qui nomme ses `Principal` et s'ajoute aux politiques d'identité.
- Exemple : La politique de ressource de `catalog-build` autorise le service S3 à l'invoquer, seulement pour le bucket content.
- Alias : politiques de ressource, politique basée sur la ressource, resource policy
- Carte : iam-politique-de-ressource

## politique de topic
- Définition : Politique de ressource d'un topic SNS : elle dit quels services ou comptes peuvent y publier ou s'y abonner.
- Exemple : La politique du topic `alerts` autorise `cloudwatch.amazonaws.com` à publier, seulement pour les alarmes du compte.
- Alias : politiques de topic, topic policy
- Carte : sns-politique-de-topic

## politique IAM
- Définition : Document JSON de statements (`Effect`, `Action`, `Resource`) qui autorise ou refuse des actions AWS à une identité ou sur une ressource.
- Exemple : La politique IAM du rôle de build de revision-pwa liste exactement les actions sur le bucket du site et la distribution.
- Alias : politiques IAM
- Carte : iam-statement-structure

## politique inline
- Définition : Politique IAM écrite dans un seul rôle ou utilisateur : sans ARN propre, elle vit et disparaît avec lui.
- Exemple : Chaque Lambda de data-platform a des politiques inline `app` et `logs`, créées et détruites avec son rôle.
- Alias : politiques inline
- Carte : iam-politique-inline

## politique managée
- Définition : Politique IAM indépendante, avec son ARN, attachable à plusieurs rôles ; AWS en fournit (`AWSLambdaBasicExecutionRole`) ou on crée les siennes.
- Exemple : `AWSLambdaBasicExecutionRole` est une politique managée par AWS, trop large pour les rôles de data-platform.
- Alias : politiques managées, managed policy
- Carte : iam-politique-inline

## préfixe S3
- Définition : Début commun des clés d'objets S3 (`bodacc/date=2026-10-20/`) qui joue le rôle de dossier pour lister, filtrer ou donner des droits.
- Exemple : La Lambda d'ingestion n'a le droit d'écrire que sous le préfixe `bodacc/` du bucket raw.
- Alias : préfixes S3
- Carte : s3-cle-sans-dossier

## principal
- Définition : Qui fait la requête vu par IAM : un utilisateur, un rôle, un service AWS ou un compte ; le champ `Principal` d'une politique de ressource le nomme.
- Exemple : Un refus montre le principal `assumed-role/<rôle>/CognitoIdentityCredentials` : l'appel venait bien de l'app de révision.
- Alias : principaux, principal de service
- Carte : iam-role-confiance-permissions

## profil AWS
- Définition : Jeu de réglages nommé de la CLI et des SDK (compte, région, rôle ou session SSO) dans `~/.aws/config`, choisi par `--profile`.
- Exemple : Les commandes de data-platform utilisent le profil `data-platform`, région `eu-west-3`.
- Alias : profils AWS, profil CLI, AWS_PROFILE
- Carte : iam-sso-login-session

## projection
- Définition : Liste des attributs qu'un index DynamoDB recopie depuis la table : les clés seules, une liste choisie ou tout l'item.
- Exemple : Un GSI `par-tribunal` en projection `INCLUDE` copie seulement `nom` et `date`, ce qu'affiche l'écran.
- Alias : projections, projection d'index
- Carte : dynamodb-projection-index

## PutItem
- Définition : Opération qui écrit un item entier dans DynamoDB ; si la clé existe déjà, l'ancien item est remplacé en totalité.
- Exemple : La synchronisation de l'app de révision écrit chaque réponse avec `PutItem` : la rejouer donne le même résultat.
- Alias : put_item
- Carte : dynamodb-putitem-remplace

## PutObject
- Définition : Opération S3 qui écrit un objet entier sous une clé, en une requête ; elle crée ou remplace l'objet.
- Exemple : L'ingestion écrit `part-0001.jsonl.gz` puis `_MANIFEST.json` avec `put_object`, droit `s3:PutObject` sur `bodacc/*`.
- Alias : put_object, s3:PutObject
- Carte : s3-put-object-octets

## Query
- Définition : Opération DynamoDB qui lit les items d'une seule clé de partition, éventuellement une plage de clés de tri, dans l'ordre de tri.
- Exemple : Charger la progression d'un utilisateur de l'app de révision est une `Query` sur son identity id.
- Alias : Query DynamoDB
- Carte : dynamodb-query-une-partition

## quota AWS
- Définition : Limite d'usage fixée par AWS pour un service dans un compte et une région (appels par seconde, nombre de ressources) ; certains se relèvent sur demande.
- Exemple : Le quota de concurrence Lambda est de 1 000 exécutions simultanées par région, partagées par toutes les fonctions du compte.
- Alias : quotas AWS, Service Quotas
- Carte : dynamodb-quotas-index

## RCU
- Définition : Read Capacity Unit : unité de lecture DynamoDB, une lecture forte par seconde d'un item jusqu'à 4 Ko (ou deux lectures éventuelles).
- Exemple : Lire un item de 10 Ko en lecture forte consomme 3 RCU, arrondi au multiple de 4 Ko supérieur.
- Alias : RCUs, unité de lecture, unités de lecture, read_capacity
- Carte : dynamodb-rcu-arrondi-4ko

## RDS
- Définition : Relational Database Service : bases SQL managées (PostgreSQL, MySQL…) sur une instance qui tourne et se paie en continu.
- Exemple : La plus petite base RDS PostgreSQL coûte environ 16 $ par mois sans requête, là où DynamoDB coûte des centimes.
- Alias : Amazon RDS, Relational Database Service
- Carte : dynamodb-cout-au-repos-rds

## Redshift
- Définition : Entrepôt de données SQL d'AWS, optimisé pour l'analyse de gros volumes et de nombreux tableaux de bord ; existe en mode Serverless.
- Exemple : Des dizaines de tableaux de bord rafraîchis en continu sur des To d'annonces iraient sur Redshift plutôt qu'Athena.
- Alias : Amazon Redshift, Redshift Serverless
- Carte : glue-athena-athena-ou-redshift

## région AWS
- Définition : Zone géographique où AWS fait tourner ses services (`eu-west-3` = Paris) ; une ressource vit dans une région, les données n'en sortent pas seules.
- Exemple : Tout data-platform est déployé dans la région `eu-west-3`.
- Alias : régions AWS
- Carte : s3-create-bucket-region

## règle EventBridge
- Définition : Filtre attaché à un bus EventBridge : chaque événement qui correspond à son motif est envoyé à ses cibles (Lambda, CodeBuild, SQS).
- Exemple : La règle `push-main` de revision-pwa lance le build CodeBuild à chaque mise à jour de la branche main.
- Alias : règles EventBridge, règle d'événement
- Carte : sqs-eventbridge-event-pattern

## request ID
- Définition : Identifiant unique qu'AWS donne à chaque appel d'API ou invocation Lambda ; on le journalise pour retrouver l'appel dans les logs ou CloudTrail.
- Exemple : Chaque ligne de log de l'ingestion porte le request ID de son invocation, le même que dans la ligne REPORT.
- Alias : RequestId, aws_request_id, x-amzn-RequestId, identifiant de requête
- Carte : api-request-id

## requête canonique
- Définition : Forme normalisée d'une requête HTTP (méthode, chemin, en-têtes signés, empreinte du corps) que SigV4 hache puis signe.
- Exemple : Ajouter un champ au corps après la signature change la requête canonique : AWS refuse la requête de l'app.
- Alias : canonical request
- Carte : api-cle-signature-derivee

## rétention
- Définition : Durée pendant laquelle un service garde une donnée avant de la supprimer seul (logs CloudWatch, messages SQS).
- Exemple : Les logs des Lambdas de data-platform ont une rétention de 14 jours ; sans elle, ils seraient gardés et facturés sans fin.
- Alias : rétention des logs, durée de rétention, retention_in_days
- Carte : codebuild-log-group-terraform

## rôle d'exécution
- Définition : Rôle IAM qu'endosse une fonction Lambda : il fixe ce que son code peut faire (lire S3, écrire ses logs).
- Exemple : Le rôle d'exécution de `catalog-build` peut lire `sources/*` et écrire `content/catalog.json`, rien d'autre.
- Alias : rôles d'exécution, execution role
- Carte : lambda-role-execution

## rôle de service
- Définition : Rôle IAM qu'endosse un service AWS (CodeBuild, Step Functions, Scheduler) pour agir dans le compte avec des droits limités.
- Exemple : CodeBuild déploie l'app de révision avec son rôle de service : aucune clé d'accès stockée dans la CI.
- Alias : rôles de service, service role
- Carte : iam-role-de-service-ci

## rôle IAM
- Définition : Identité IAM sans mot de passe ni clé permanente, qu'un service, une personne ou une CI endosse pour obtenir des droits temporaires.
- Exemple : Chaque Lambda de data-platform a son propre rôle IAM, créé avec elle.
- Alias : rôles IAM, rôle AWS
- Carte : iam-utilisateur-ou-role

## rotation de clé
- Définition : Remplacement périodique du matériel secret d'une clé KMS, sans changer son identifiant ni rechiffrer les anciennes données.
- Exemple : La clé du projet a la rotation automatique : chaque année, les nouveaux chiffrements prennent un nouveau matériel.
- Alias : rotation des clés, rotation automatique
- Carte : kms-rotation-meme-arn

## runtime
- Définition : Environnement de langage fourni par AWS pour exécuter le code (`python3.12`, `nodejs22.x` pour Lambda, versions Node ou Python d'une image CodeBuild).
- Exemple : Passer l'ingestion de `python3.12` à `python3.13` impose de reconstruire le zip et ses dépendances compilées.
- Alias : runtime Lambda, runtimes
- Carte : lambda-so-version-python

## S3
- Définition : Simple Storage Service : stockage d'objets (fichiers) illimité d'AWS, rangés dans des buckets par clé, facturé au Go stocké et aux requêtes.
- Exemple : Les annonces BODACC brutes de data-platform sont écrites dans S3, une partition par jour.
- Alias : Amazon S3, Simple Storage Service
- Carte : s3-data-lake-choisir

## S3 Batch Operations
- Définition : Service S3 qui applique une même opération (copie, tags, restauration) à des millions d'objets listés, avec suivi et rapport.
- Exemple : Rechiffrer en SSE-KMS tous les anciens objets de raw passerait par S3 Batch Operations plutôt qu'une boucle de copies.
- Alias : Batch Operations
- Carte : s3-chiffrement-par-defaut

## SAM
- Définition : Serverless Application Model : extension de CloudFormation qui décrit et déploie des applications serverless (Lambda, API Gateway) avec une syntaxe abrégée.
- Exemple : Un projet SAM construit et déploie ses Lambdas avec `sam build` et `sam deploy`, là où data-platform utilise Terraform.
- Alias : AWS SAM, Serverless Application Model

## Scan
- Définition : Opération DynamoDB qui lit toute la table, toutes partitions, et facture tout ce qu'elle lit ; à éviter dans le chemin d'une app.
- Exemple : Le rôle de l'app de révision n'a pas `dynamodb:Scan` : un utilisateur ne peut pas lire la table entière.
- Alias : Scan DynamoDB
- Carte : dynamodb-scan-toute-la-table

## SCP
- Définition : Service Control Policy : politique d'AWS Organizations qui plafonne les droits de tout un compte membre, sans en accorder aucun.
- Exemple : Une SCP pourrait interdire toute région autre que `eu-west-3` sur le compte de prod de data-platform.
- Alias : SCPs, Service Control Policy
- Carte : iam-scp-plafond-compte

## SDK AWS
- Définition : Bibliothèque officielle qui appelle les API AWS depuis un langage (boto3 en Python, `@aws-sdk/*` en TypeScript) : signature, réessais, pagination.
- Exemple : La Lambda `catalog-build`, en TypeScript, utilise le SDK AWS v3 fourni par le runtime Node.
- Alias : AWS SDK, SDK v3, SDK JS v3
- Carte : api-aws4fetch-ou-sdk

## Secrets Manager
- Définition : Service qui stocke des secrets (mots de passe, jetons) chiffrés, avec rotation possible, lus par le code au moment voulu.
- Exemple : Un jeton d'API partenaire irait dans Secrets Manager, lu par la Lambda, jamais dans une variable d'environnement en clair.
- Alias : AWS Secrets Manager
- Carte : lambda-variables-env-chaines

## serverless
- Définition : Modèle où le fournisseur gère les serveurs et la mise à l'échelle : on paie à l'usage, rien au repos (Lambda, S3, DynamoDB).
- Exemple : data-platform est serverless : sans annonce à traiter, elle ne coûte presque rien.
- Alias : sans serveur
- Carte : couts-cout-au-repos

## shard
- Définition : Tranche d'un flux Kinesis ou DynamoDB Streams, lue dans l'ordre ; le débit et la lecture parallèle se répartissent par shard.
- Exemple : Un item invalide peut bloquer la lecture de son shard DynamoDB Streams jusqu'à 24 h sans réglage des retries.
- Alias : shards
- Carte : dynamodb-streams-ordre-24h

## sid
- Définition : Nom facultatif d'un statement IAM (`WriteBodaccPartitions`), unique dans la politique, qui dit à quoi sert le droit.
- Exemple : Le sid `UseProjectKey` explique pourquoi le rôle de l'ingestion a des droits sur la clé KMS.
- Carte : iam-sid-unique

## SigV4
- Définition : Signature Version 4 : méthode qui signe chaque requête AWS avec la clé secrète, sans jamais l'envoyer ; AWS refait le calcul pour vérifier.
- Exemple : Le navigateur de l'app de révision signe ses appels DynamoDB en SigV4 avec `aws4fetch`.
- Alias : Signature Version 4, signature SigV4
- Carte : api-sigv4-authorization

## SNS
- Définition : Simple Notification Service : service qui pousse chaque message publié dans un topic à tous ses abonnés (e-mail, SQS, Lambda).
- Exemple : Les alarmes de data-platform publient dans un topic SNS, qui envoie un mail à l'auteur.
- Alias : Amazon SNS, Simple Notification Service
- Carte : sns-topic-fan-out

## sous-réseau
- Définition : Plage d'adresses d'un VPC, dans une zone de disponibilité ; public s'il a une route vers Internet, privé sinon.
- Exemple : Un build CodeBuild placé dans un sous-réseau privé sans NAT ne peut plus télécharger ses paquets.
- Alias : sous-réseaux, subnet
- Carte : codebuild-vpc-config-nat

## SQS
- Définition : Simple Queue Service : file de messages qui garde les messages d'un producteur jusqu'à ce qu'un consommateur les traite et les supprime.
- Exemple : Une file SQS de jours à rejouer lisserait les appels à l'API BODACC quand elle répond 429.
- Alias : Amazon SQS, Simple Queue Service, file SQS, files SQS
- Carte : sqs-eventbridge-quand-sqs

## SSE-KMS
- Définition : Chiffrement côté serveur S3 avec une clé KMS : lire ou écrire demande aussi des droits sur la clé, révocables et tracés.
- Exemple : Les buckets raw et processed sont en SSE-KMS avec la clé du projet ; la Lambda a besoin de `kms:Decrypt`.
- Alias : aws:kms, chiffrement SSE-KMS
- Carte : kms-sse-kms-double-droit

## SSE-S3
- Définition : Chiffrement côté serveur S3 avec des clés gérées par S3 lui-même (`AES256`) : gratuit, sans droit KMS à donner.
- Exemple : Le bucket d'artefacts est en SSE-S3 : le déployeur lit les zips de Lambda sans droit sur une clé KMS.
- Alias : AES256, chiffrement SSE-S3
- Carte : s3-chiffrement-par-defaut

## SSM
- Définition : AWS Systems Manager : service d'exploitation qui regroupe notamment Parameter Store (paramètres de configuration) et l'accès aux serveurs sans SSH.
- Exemple : Un output partagé entre deux projets peut être publié comme paramètre SSM, lu par l'autre sans accès à son état Terraform.
- Alias : Systems Manager, AWS Systems Manager
- Carte : codebuild-variables-plaintext

## SSO
- Définition : IAM Identity Center (ex-AWS SSO) : connexion unique qui donne à une personne des droits temporaires sur un ou plusieurs comptes, sans clé permanente.
- Exemple : Avant `make plan`, l'auteur lance `aws sso login` : la session SSO fournit des clés temporaires à Terraform.
- Alias : IAM Identity Center, AWS SSO, Identity Center, session SSO
- Carte : iam-identity-center

## Standard-IA
- Définition : Classe de stockage moins chère au Go mais facturée à la lecture, pour des données rarement relues (S3 Standard-IA, table DynamoDB Standard-IA).
- Exemple : Les annonces BODACC de plus d'un an, relues seulement en cas de rejeu, iraient en Standard-IA.
- Alias : Standard-Infrequent Access, STANDARD_IA
- Carte : s3-classe-de-stockage

## statement
- Définition : Règle d'une politique IAM : `Effect` (`Allow` ou `Deny`), `Action`, `Resource` et une `Condition` facultative.
- Exemple : Le statement `WriteBodaccPartitions` autorise `s3:PutObject` sur `bodacc/*` du bucket raw.
- Alias : statements, instruction IAM
- Carte : iam-statement-structure

## statistique
- Définition : Façon dont CloudWatch agrège les valeurs d'une métrique sur une période : `Sum`, `Average`, `Maximum`, percentile.
- Exemple : L'alarme d'erreurs de l'ingestion utilise `Sum` : au moins une erreur dans la période suffit.
- Alias : statistiques
- Carte : cloudwatch-sum-ou-average

## Step Functions
- Définition : Service d'orchestration qui enchaîne des étapes AWS (Lambda, Glue, ECS) selon une machine d'états, avec reprises et historique.
- Exemple : Le pipeline quotidien enchaînerait ingestion, normalisation et publication dans Step Functions.
- Alias : AWS Step Functions
- Carte : step-functions-quand-orchestrer

## StreamingBody
- Définition : Objet de botocore qui représente le corps d'une réponse (S3 `Body`, Lambda `Payload`) : un flux lu une seule fois par `.read()`.
- Exemple : Lire deux fois le `Body` d'un manifest S3 donne une chaîne vide la seconde fois.
- Alias : flux de réponse
- Carte : s3-body-lu-une-fois

## STS
- Définition : Security Token Service : service qui délivre des clés AWS temporaires (préfixe `ASIA`, avec jeton de session) quand on endosse un rôle.
- Exemple : Cognito obtient de STS des clés d'une heure pour l'utilisateur connecté de l'app de révision.
- Alias : AWS STS, Security Token Service, clés STS, clés temporaires, identifiants temporaires
- Carte : iam-assumerole-temporaire

## table globale
- Définition : Table DynamoDB répliquée dans plusieurs régions, toutes lisibles et écrivables ; par défaut, la dernière écriture gagne en cas de conflit.
- Exemple : Une app multi-région servirait chaque utilisateur depuis la réplique la plus proche d'une table globale.
- Alias : global table, global tables, tables globales
- Carte : dynamodb-global-tables-mrec

## table unique
- Définition : Modèle DynamoDB où plusieurs types d'entités partagent une seule table, distingués par des préfixes dans les clés (single-table design).
- Exemple : Entreprises et annonces vivraient dans la même table sous `SIREN#…`, lues ensemble par une `Query`.
- Alias : single-table, single-table design, modèle une table
- Carte : dynamodb-surcharge-des-cles

## tableau de bord CloudWatch
- Définition : Page CloudWatch qui assemble des graphes de métriques (widgets) pour suivre un système en direct.
- Exemple : Un tableau de bord montrerait côte à côte invocations, erreurs et durée des Lambdas de data-platform.
- Alias : tableaux de bord CloudWatch, dashboard CloudWatch, widget
- Carte : cloudwatch-widget-image

## tag
- Définition : Paire clé-valeur posée sur une ressource AWS (`Project = data-platform`) pour la retrouver, la facturer ou en régler l'accès.
- Exemple : Chaque ressource de data-platform porte les tags du projet et de l'environnement, ajoutés par Terraform.
- Alias : tags, tag AWS, tags AWS, étiquette AWS
- Carte : dynamodb-pitr-reglages-perdus

## throttling
- Définition : Refus temporaire d'une requête parce qu'un débit maximal est atteint (« trop vite, réessaie plus tard ») ; ce n'est pas une erreur de données.
- Exemple : Une table DynamoDB dont la partition dépasse 1 000 écritures/s renvoie du throttling, réessayé par le SDK.
- Alias : limitation de débit, throttle, ThrottlingException
- Carte : dynamodb-throttling-exceptions

## topic SNS
- Définition : Canal SNS nommé où l'on publie des messages, distribués à tous les abonnés ; l'émetteur ne connaît que le topic.
- Exemple : Le topic `data-platform-dev-alerts` reçoit les alarmes et envoie le mail d'alerte.
- Alias : topics SNS
- Carte : sns-topic-fan-out

## TransactWriteItems
- Définition : Opération DynamoDB qui applique jusqu'à 100 écritures (`Put`, `Update`, `Delete`, `ConditionCheck`) toutes ou aucune, pour un coût double.
- Exemple : Créer une annonce et incrémenter le compteur de son tribunal dans la même `TransactWriteItems` évite un état à moitié écrit.
- Alias : transact_write_items, TransactGetItems
- Carte : dynamodb-transactwriteitems

## Transfer Family
- Définition : Service AWS qui offre un serveur SFTP ou FTPS managé et dépose directement les fichiers reçus dans S3.
- Exemple : Un partenaire qui envoie un CSV par jour en SFTP déposerait ses fichiers dans S3 via Transfer Family.
- Alias : AWS Transfer Family
- Carte : glue-athena-dms-cdc

## transformateur d'entrée
- Définition : Réglage d'une cible EventBridge (`input_transformer`) qui extrait des champs de l'événement et les place dans un gabarit JSON pour la cible.
- Exemple : Un transformateur d'entrée passerait le commit poussé à CodeBuild comme `sourceVersion`.
- Alias : input transformer, input_transformer
- Carte : sqs-eventbridge-input-transformer

## TTL DynamoDB
- Définition : Time To Live de DynamoDB : attribut date (en secondes depuis 1970) d'un item, après laquelle DynamoDB le supprime seul, sans frais.
- Exemple : Un cache d'API dans DynamoDB porte `expire_at` : le TTL efface l'item quelques heures ou jours après cette date.
- Alias : TTL de DynamoDB, Time To Live DynamoDB
- Carte : dynamodb-ttl-epoch-secondes

## UpdateItem
- Définition : Opération DynamoDB qui modifie certains attributs d'un item sans réécrire les autres, et le crée s'il n'existe pas.
- Exemple : Incrémenter le nombre de vues d'une carte se fait par `UpdateItem` avec `ADD vues :un`.
- Alias : update_item
- Carte : dynamodb-updateitem-partiel

## URL présignée
- Définition : Lien qui contient une signature SigV4 et donne accès à une seule opération S3 (lire ou écrire un objet) jusqu'à son expiration, sans identifiants.
- Exemple : Un export pour un partenaire lui serait envoyé sous forme d'URL présignée valable 24 h.
- Alias : URLs présignées, presigned URL
- Carte : s3-url-presignee

## user pool
- Définition : Annuaire d'utilisateurs de Cognito : inscription, mots de passe, connexion ; il émet des jetons JWT mais ne donne aucun droit AWS.
- Exemple : L'utilisateur de l'app de révision se connecte au user pool, qui lui rend un id token.
- Alias : user pools, pool d'utilisateurs
- Carte : cognito-user-ou-identity-pool

## utilisateur IAM
- Définition : Identité IAM permanente, avec mot de passe et clés d'accès qui ne changent pas seules ; à éviter au profit de rôles et du SSO.
- Exemple : data-platform n'a aucun utilisateur IAM : les humains passent par Identity Center, les services par des rôles.
- Alias : utilisateurs IAM, IAM user
- Carte : iam-utilisateur-ou-role

## variable de politique
- Définition : Champ `${…}` d'une politique IAM remplacé à chaque requête par une valeur de l'appelant, par exemple son identifiant Cognito.
- Exemple : `${cognito-identity.amazonaws.com:sub}` borne chaque utilisateur de l'app à sa propre partition DynamoDB.
- Alias : variables de politique, policy variable
- Carte : iam-variable-de-politique

## vCPU
- Définition : Processeur virtuel : part de processeur réservée à une machine, un conteneur ou une fonction dans le cloud.
- Exemple : Lambda donne environ 1 vCPU à 1 769 Mo de mémoire : monter la mémoire accélère aussi le calcul.
- Alias : vCPUs, processeur virtuel
- Carte : lambda-memoire-achete-cpu

## version de Lambda
- Définition : Copie figée et numérotée du code et de la configuration d'une fonction, créée à la publication ; `$LATEST` reste la seule modifiable.
- Exemple : Publier la version 3 de l'ingestion puis y faire pointer l'alias `live` fige le code qui tourne en prod.
- Alias : versions de Lambda, $LATEST
- Carte : lambda-versions-alias

## versioning
- Définition : Option S3 qui garde l'ancienne version d'un objet à chaque écrasement ou suppression, récupérable par son identifiant de version.
- Exemple : Le bucket raw est versionné : un rejeu fautif se répare en recopiant la version d'avant.
- Alias : versioning S3, bucket versionné, versionné, versions d'objet, VersionId
- Carte : s3-versioning-suppression

## visibility timeout
- Définition : Délai pendant lequel SQS cache un message lu aux autres consommateurs ; non supprimé à temps, il redevient visible et sera relu.
- Exemple : Devant une Lambda de 300 s, la file doit avoir un visibility timeout d'au moins 1 800 s.
- Alias : délai de visibilité
- Carte : sqs-eventbridge-visibility-timeout

## VPC
- Définition : Virtual Private Cloud : réseau privé isolé dans AWS, découpé en sous-réseaux, où l'on place des bases, conteneurs ou Lambdas.
- Exemple : Les Lambdas de data-platform ne sont pas dans un VPC : elles joignent S3 directement, sans NAT à payer.
- Alias : Virtual Private Cloud, VPCs
- Carte : couts-nat-gateway-endpoint

## WCU
- Définition : Write Capacity Unit : unité d'écriture DynamoDB, une écriture par seconde d'un item jusqu'à 1 Ko ; une transaction en coûte deux.
- Exemple : Incrémenter un compteur dans une ligne de 50 Ko consomme 50 WCU à chaque `+1`.
- Alias : WCUs, unité d'écriture, unités d'écriture, write_capacity
- Carte : dynamodb-wcu-arrondi

## write sharding
- Définition : Technique DynamoDB qui ajoute un suffixe à une clé de partition très sollicitée pour répartir ses écritures sur plusieurs partitions.
- Exemple : Écrire les annonces sous `2026-10-23.1` à `.10` au lieu de `2026-10-23` répartit la charge d'une grosse journée.
- Alias : sharding, sharding calculé
- Carte : dynamodb-write-sharding

## zone de disponibilité
- Définition : Centre de données isolé d'une région AWS ; une région en compte plusieurs, pour survivre à la panne de l'une.
- Exemple : Une base RDS mono-AZ tourne dans une seule zone de disponibilité de Paris : moins chère, mais sans secours.
- Alias : zones de disponibilité, AZ, mono-AZ
- Carte : dynamodb-cout-au-repos-rds
