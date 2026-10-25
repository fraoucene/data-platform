---
title: "Cartes · S3"
type: cartes
langage: AWS
cours: S3
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · S3
AWS · S3 : choisir, clés, cycle de vie, accès, requêtes, événements (format spec v3 de revision-pwa).

## 1. clé S3 : pas de dossiers
- Sous-thème : clés
- Niveau : 1
- Définition : S3 stocke des clés plates ; un « dossier » n'est qu'un préfixe de chaîne, filtré par `Prefix` au listage.
- Contexte : Un bucket est un dictionnaire géant clé → objet, sans arborescence : la console dessine des dossiers en coupant les clés sur `/`. `list_objects_v2` filtre par début de chaîne (`Prefix`) et peut regrouper par `Delimiter` (renvoyé dans `CommonPrefixes`). Un dossier vide n'existe donc pas, et « renommer un dossier » veut dire copier puis supprimer chaque objet.
- Usage : ✅ préfixes qui suivent l'ordre de lecture (`raw/bodacc/dt=…/`) pour lister un jour d'un coup · ❌ compter sur un `mv` de dossier atomique : c'est N copies et N suppressions.

```python
# Exemple 1 : Prefix = startswith
keys = [
    "raw/bodacc/dt=2026-10-02/p.gz",
    "raw/bodacc/dt=2026-10-23/p.gz",
]
p = "raw/bodacc/dt=2026-10-23/"
[k for k in keys if k.startswith(p)]
# → ["raw/bodacc/dt=2026-10-23/p.gz"]
```

```bash
# Exemple 2 : Delimiter regroupe
aws s3api list-objects-v2 \
  --bucket dp-dev-lake \
  --prefix raw/bodacc/ \
  --delimiter /
# → CommonPrefixes :
#   raw/bodacc/dt=2026-10-02/
#   raw/bodacc/dt=2026-10-23/
```

- Quiz : Clés des jours 02, 23 et 29 octobre : que renvoie `Prefix="raw/bodacc/dt=2026-10-2"` ?
- [ ] Rien : un préfixe doit finir par `/`
- [ ] Le jour 23 seulement
- [x] Les jours 23 et 29
- [ ] Les jours 02, 23 et 29
- Réponse : les jours 23 et 29 : le préfixe est une comparaison de début de chaîne, sans notion de dossier ni de date ; `dt=2026-10-02` commence par `…-10-0`.

## 2. lifecycle : expirer raw à 90 j
- Sous-thème : cycle de vie
- Niveau : 1
- Définition : Une règle lifecycle supprime les objets d'un préfixe, ou change leur classe de stockage, après N jours, sans code ni cron.
- Contexte : S3 applique la règle de façon asynchrone, une fois par jour : l'objet disparaît vers minuit UTC qui suit l'échéance, pas à la seconde près. Les transitions ont des minimums : 30 jours en `STANDARD` avant `STANDARD_IA`, et chaque classe froide facture une durée minimale de stockage. Une règle s'applique aussi aux objets déjà présents.
- Usage : ✅ rétention réglementaire ou de coût sur `raw`, nettoyage des uploads multipart incomplets · ❌ suppression qui doit être immédiate ou conditionnelle : un job explicite.

```hcl
# Exemple 1 : raw supprimé à 90 j
rule {
  id     = "raw-90j"
  status = "Enabled"
  filter { prefix = "bodacc/" }
  expiration { days = 90 }
}
```

```python
# Exemple 2 : quand part l'objet ?
from datetime import date, timedelta

cree = date(2026, 10, 23)
cree + timedelta(days=90)
# → date(2027, 1, 21)
```

- Quiz : On ajoute `transition { days = 7, storage_class = "STANDARD_IA" }` à la règle : que répond l'API ?
- [ ] OK : passage en IA au 7e jour
- [x] Refus : il faut au moins 30 jours avant IA
- [ ] OK, mais S3 attend 30 jours sans rien dire
- [ ] Refus : IA est incompatible avec `expiration`
- Réponse : refus : un objet doit rester 30 jours en `STANDARD` avant `STANDARD_IA` ou `ONEZONE_IA` ; l'`apply` échoue avec `InvalidArgument`.

## 3. S3 : où poser le data lake
- Sous-thème : choisir
- Niveau : 1
- Définition : Pour un data lake, on choisit S3 : stockage objet illimité, payé au Go, lisible par Athena, Glue, Spark et Lambda sans serveur.
- Contexte : Rien à dimensionner : on paie ce qui est stocké (0,024 $/Go-mois en Standard à Paris) et les requêtes. Tous les moteurs lisent S3, donc le stockage et le calcul se choisissent séparément. Le prix de cette souplesse : S3 n'est pas un système de fichiers (pas d'écriture partielle, pas de verrou, pas de renommage atomique) ni une base (pas de requête sans moteur).
- Usage : ✅ zones `raw`, `processed`, `out`, archives, exports · ❌ disque de travail partagé avec `seek` ou verrous : EFS ; accès par clé en millisecondes : DynamoDB.

```
# Exemple 1 : la décision
Besoin  : garder chaque jour BODACC
          brut + nettoyé, des années
Volume  : ~50 Mo/jour, croissance lente
→ Choix : S3 (raw/, processed/, out/)
Pourquoi: rien à prévoir, lu par tous
Écarté  : EBS (attaché à 1 machine),
          RDS (cher pour du stockage)
```

```python
# Exemple 2 : 3 ans de BODACC
mo_jour = 50
go = mo_jour * 365 * 3 / 1000
prix = 0.024        # $/Go-mois, Paris
round(go, 1)        # → 54.8
round(go * prix, 2) # → 1.31  ($/mois)
```

- Quiz : Plusieurs tâches doivent partager un vrai système de fichiers (`open`, `seek`, verrous) : quel service ?
- [ ] S3, monté avec un préfixe partagé
- [x] EFS, monté comme un disque partagé
- [ ] EBS, attaché à toutes les tâches
- [ ] DynamoDB, une ligne par fichier
- Réponse : EFS : S3 n'est pas POSIX (ni écriture partielle, ni verrou) ; EFS se monte dans Lambda, ECS ou EC2 comme un disque partagé, EBS ne s'attache qu'à une instance.

## 4. aws s3 ou s3api : deux CLI
- Sous-thème : requêtes
- Niveau : 1
- Définition : `aws s3` offre des commandes de fichiers (`cp`, `sync`, `ls`) ; `aws s3api` expose une à une les opérations de l'API S3.
- Contexte : `aws s3 cp` découpe seul les gros fichiers en multipart, parcourt toutes les pages de listage et accepte `--recursive` : il cache l'API. `s3api` fait exactement un appel (`put-object`, `head-object`) et renvoie le JSON brut, filtrable par `--query`. `aws s3 ls` affiche des lignes `PRE` et des tailles pour un humain : ne pas le parser dans un script.
- Usage : ✅ `aws s3` pour copier ou synchroniser des fichiers · ❌ lire un attribut (ETag, chiffrement, version) ou poser une condition (`--if-none-match`) : `s3api` avec `--query`.

```bash
# Exemple 1 : même objet, deux outils
aws s3 cp p.gz \
  "s3://$RAW/bodacc/dt=2026-10-23/"
# → upload: ./p.gz to s3://…/p.gz
aws s3api head-object --bucket "$RAW" \
  --key bodacc/dt=2026-10-23/p.gz \
  --query ServerSideEncryption
# → "aws:kms"  (chiffrement du bucket)
```

```bash
# Exemple 2 : ls lisible, s3api scriptable
aws s3 ls "s3://$CONTENT/sources/"
# →  PRE data-platform/
aws s3api list-objects-v2 \
  --bucket "$CONTENT" --prefix sources/ \
  --query 'length(Contents)'
# → un nombre, utilisable en script
```

- Quiz : Que fait `aws s3 cp s3://$CONTENT/sources/ ./dl/`, sans `--recursive` ?
- [ ] Copie tout le préfixe `sources/`
- [ ] Copie le premier objet du préfixe
- [x] Échoue : `Key "sources/" does not exist`
- [ ] Crée un dossier `dl/sources/` vide
- Réponse : échec (404 sur `HeadObject`, mesuré) : sans `--recursive`, `cp` cherche un objet dont la clé est exactement `sources/`, qui n'existe pas.

## 5. list_objects_v2 : 1 000 clés par page
- Sous-thème : clés
- Niveau : 1
- Définition : `ListObjectsV2` renvoie au plus 1 000 clés par appel ; `IsTruncated` et `NextContinuationToken` mènent à la page suivante.
- Contexte : Un seul appel sur un préfixe de 1 500 fichiers en rend 1 000, sans erreur : le code qui oublie la pagination perd des données en silence. `aws s3 ls` et `aws s3api list-objects-v2` paginent seuls ; en boto3, `get_paginator("list_objects_v2")`. Les clés reviennent triées par octets UTF-8, jamais par date d'écriture.
- Usage : ✅ paginator boto3, ou boucle sur `ContinuationToken`, dès qu'un préfixe peut dépasser 1 000 clés · ❌ un seul `list_objects_v2` pour « tout lire » un jour de `raw`.

```python
# Exemple 1 : la boucle de pagination
cles = [f"p-{i:04}.gz" for i in range(2500)]

def lister(token=0):   # ≈ list_objects_v2
    page = cles[token:token + 1000]
    suite = token + 1000
    return {"Contents": page,
            "IsTruncated": suite < len(cles),
            "NextContinuationToken": suite}

tout, token = [], 0
while True:
    r = lister(token)
    tout += r["Contents"]
    if not r["IsTruncated"]:
        break
    token = r["NextContinuationToken"]
len(tout)        # → 2500
```

- Quiz : `list_objects_v2(MaxKeys=5000)` sur un bucket de plus de 1 000 objets : combien de clés reviennent ?
- [ ] 5 000
- [ ] Toutes : `MaxKeys` désactive la pagination
- [x] 1 000, avec `IsTruncated` à `true`
- [ ] `InvalidArgument` : maximum 1 000
- Réponse : 1 000 avec `IsTruncated: true` (mesuré) : `MaxKeys` ne peut que réduire la page, S3 plafonne à 1 000 sans erreur.

## 6. classe S3 : selon la lecture
- Sous-thème : cycle de vie
- Niveau : 2
- Définition : La classe S3 se choisit sur la fréquence de lecture : Standard si lu souvent, Standard-IA ou Glacier pour l'archive rarement relue.
- Contexte : À Paris : Standard 0,024 $/Go-mois, Standard-IA 0,0131 $ plus 0,01 $/Go relu, Glacier Instant Retrieval 0,005 $. Les classes froides facturent une durée minimale (30 jours en IA, 90 en Glacier IR) et 128 Ko minimum par objet. Intelligent-Tiering déplace seul les objets selon l'accès, contre 0,0025 $ pour 1 000 objets suivis par mois ; sous 128 Ko, il ne les déplace pas.
- Usage : ✅ IA ou Glacier IR pour des Go à des To rarement relus · ❌ classe froide pour des données lues chaque jour, ou de petits volumes : l'économie est nulle.

```
# Exemple 1 : la décision
Besoin  : raw/ relu seulement pour
          rejouer un bug (rare)
→ Choix : Standard, expiration 90 j
Pourquoi: 4,5 Go au total, IA
          ferait gagner 5 centimes
Écarté  : Standard-IA (minimum 30 j,
          lecture payante au Go)
```

```python
# Exemple 2 : l'économie réelle
go = 50 * 90 / 1000   # 90 jours de raw
standard = 0.024      # $/Go-mois
ia = 0.0131
round(go * (standard - ia), 3)
# → 0.049  ($/mois économisés)
```

- Quiz : Athena interroge `processed/` chaque jour ; on la passe en Glacier Flexible Retrieval pour économiser : que se passe-t-il ?
- [ ] Rien : Athena lit Glacier, plus lentement
- [ ] Les requêtes coûtent plus cher, mais marchent
- [x] Athena ne lit plus ces objets sans restauration
- [ ] S3 remonte seul les objets lus en Standard
- Réponse : Athena ne lit plus ces objets sans restauration préalable : Glacier Flexible est une archive ; une donnée requêtée reste en Standard, IA ou Glacier Instant Retrieval.

## 7. multipart incomplet : invisible et facturé
- Sous-thème : cycle de vie
- Niveau : 2
- Source : data-platform · S1-04
- Définition : Un upload multipart jamais terminé garde ses parts dans le bucket, invisibles au listage mais facturées, jusqu'à une règle `abort_incomplete_multipart_upload`.
- Contexte : Les SDK découpent les gros fichiers en parts (au-delà de 8 Mo pour `upload_file` de boto3) ; si le processus meurt avant `CompleteMultipartUpload`, les parts restent. Elles ne sont pas des objets : ni `aws s3 ls` ni la console ne les montrent. Une règle lifecycle dédiée les purge N jours après le début de l'upload.
- Usage : ✅ une règle `abort-mpu` à 7 jours sur chaque bucket, quel que soit son rôle · ❌ bucket qui reçoit de gros fichiers sans cette règle : une facture qui grossit sans rien de visible.

```hcl
# Exemple 1 : purger à 7 jours
rule {
  id     = "abort-mpu"
  status = "Enabled"
  filter {}
  abort_incomplete_multipart_upload {
    days_after_initiation = 7
  }
}
```

```bash
# Exemple 2 : voir ce que ls ne montre pas
aws s3api list-multipart-uploads \
  --bucket "$RAW" \
  --query 'Uploads[].[Key,Initiated]'
# → null : aucun upload en cours
#   sinon un couple clé, date par upload
```

- Quiz : Sur `raw`, une seule règle `expiration { days = 90 }` : les parts d'un upload abandonné partent-elles à 90 jours ?
- [ ] Oui, comme tout objet du bucket
- [ ] Oui, si le versioning est actif
- [x] Non : ce ne sont pas des objets
- [ ] Non : S3 les supprime seul sous 24 h
- Réponse : non : `expiration` ne vise que les objets ; les parts d'un upload incomplet restent facturées tant qu'`abort_incomplete_multipart_upload` ne les purge pas.

## 8. chiffrement par défaut : l'existant ne change pas
- Sous-thème : accès
- Niveau : 2
- Définition : Le chiffrement par défaut d'un bucket s'applique aux objets écrits ensuite ; changer d'algorithme ou de clé ne rechiffre aucun objet existant.
- Contexte : Le chiffrement est un attribut de chaque objet, fixé à l'écriture : `head-object` le montre (`ServerSideEncryption`, `SSEKMSKeyId`). Passer un bucket de SSE-S3 à SSE-KMS laisse les anciens objets en `AES256` ; pour les migrer, les recopier sur eux-mêmes (`cp` ou S3 Batch Operations). Un `PutObject` peut aussi imposer son chiffrement par en-tête, prioritaire sur celui du bucket.
- Usage : ✅ choisir le chiffrement à la création du bucket, vérifier un objet par `head-object` · ❌ croire qu'un `apply` de la configuration rechiffre `raw` : seuls les nouveaux objets changent.

```bash
# Exemple 1 : chaque objet garde le sien
aws s3api head-object --bucket "$CONTENT" \
  --key content/catalog.json \
  --query ServerSideEncryption
# → "AES256"  (SSE-S3, mesuré)
```

```bash
# Exemple 2 : rechiffrer un ancien objet
aws s3 cp "s3://$RAW/bodacc/p.gz" \
  "s3://$RAW/bodacc/p.gz" \
  --sse aws:kms --sse-kms-key-id "$K"
# → copy: … to …
#   nouvelle version, clé du projet
```

- Quiz : `raw` est versionné : après ce `cp` sur lui-même, la version `AES256` existe-t-elle encore ?
- [ ] Non : elle est remplacée
- [x] Oui, en version non courante
- [ ] Non : S3 la rechiffre aussi
- [ ] Oui, et elle reste la version courante
- Réponse : oui, en version non courante : la copie crée une nouvelle version ; l'ancienne, toujours en SSE-S3, part avec `noncurrent_version_expiration`.

## 9. URL présignée : accès sans identifiants
- Sous-thème : accès
- Niveau : 2
- Définition : Une URL présignée embarque une signature SigV4 : qui la détient peut faire cette seule requête (GET ou PUT d'une clé) jusqu'à expiration.
- Contexte : La signature se calcule en local, sans appel à AWS : `aws s3 presign` réussit même pour une clé absente. À l'usage, S3 vérifie la signature puis les droits du signataire : s'il perd `s3:GetObject`, l'URL ne marche plus. Durée : 7 jours au plus ; signée avec un rôle (STS), elle meurt aussi avec la session.
- Usage : ✅ télécharger un export `out/` chez un partenaire, envoi direct depuis un navigateur · ❌ lien public durable : CloudFront ; URL collée dans un ticket ou des logs : c'est un mot de passe.

```bash
# Exemple 1 : 15 min, sans identifiants
U=$(aws s3 presign \
  "s3://$CONTENT/content/catalog.json" \
  --expires-in 900)
curl -s -o /dev/null -w "%{http_code}" "$U"
# → 200   (mesuré)
# une fois expirée :
# → 403 AccessDenied "Request has expired"
```

```bash
# Exemple 2 : ce que contient l'URL
echo "$U" | tr '?&' '\n\n'
# → X-Amz-Algorithm=AWS4-HMAC-SHA256
#   X-Amz-Credential=AKIA…%2F20261024
#     %2Feu-west-3%2Fs3%2Faws4_request
#   X-Amz-Expires=900
#   X-Amz-SignedHeaders=host
#   X-Amz-Signature=559e03c3…
```

- Quiz : `aws s3 presign … --expires-in 604801` (7 jours et 1 s) : que se passe-t-il ?
- [ ] La CLI refuse : 7 jours au plus
- [ ] URL valable 7 jours, la seconde en trop ignorée
- [x] URL créée, mais S3 la refuse à l'usage
- [ ] URL qui n'expire jamais
- Réponse : URL créée puis refusée (mesuré : `AuthorizationQueryParametersError`, « X-Amz-Expires must be less than a week ») : la CLI signe sans contrôler, S3 vérifie à la requête.

## 10. clé absente : 403 au lieu de 404
- Sous-thème : accès
- Niveau : 2
- Définition : Sans `s3:ListBucket`, lire une clé absente renvoie `403 AccessDenied`, pas `404` : S3 ne dit pas à un inconnu qu'elle n'existe pas.
- Contexte : S3 évite de laisser deviner le contenu d'un bucket : seul un principal autorisé à lister apprend qu'une clé manque. Une Lambda qui teste l'existence d'un fichier (`head_object`) puis attrape `404` reçoit `403` et croit à un problème de droits. Le rôle Lambda de data-platform a `ListBucket` sur `raw` (statement `ListBuckets`) : il voit bien `404`.
- Usage : ✅ `s3:ListBucket` sur le bucket dès qu'un code teste l'existence d'une clé · ❌ conclure « droit manquant » sur un 403 de `GetObject` sans vérifier que la clé existe.

```bash
# Exemple 1 : même clé, ±ListBucket
aws s3api head-object --bucket "$RAW" \
  --key bodacc/dt=2026-10-31/p.gz
# avec s3:ListBucket :
# → (404) Not Found   (mesuré)
# sans s3:ListBucket :
# → (403) Forbidden
```

```python
# Exemple 2 : traiter les deux codes
def existe(code):
    if code == 200:
        return True
    if code == 404:
        return False
    raise PermissionError(code)

existe(404)   # → False
existe(403)   # ❌ PermissionError
```

- Quiz : `aws s3 ls s3://$RAW/bodacc/dt=2026-10-31/`, jour absent, avec `ListBucket` : que se passe-t-il ?
- [ ] `404 NoSuchKey`
- [ ] `403 AccessDenied`
- [ ] Une ligne `PRE dt=2026-10-31/` vide
- [x] Rien d'affiché, code de sortie 1
- Réponse : rien, code de sortie 1 (mesuré) : un préfixe n'est pas un objet, lister un préfixe vide n'est pas une erreur HTTP ; tester `$?` ou `KeyCount`.

## 11. politique de bucket : HTTPS obligatoire
- Sous-thème : accès
- Niveau : 2
- Définition : Une politique de bucket est attachée au bucket et nomme ses `Principal` ; un `Deny` y bloque tout appelant, administrateur compris.
- Contexte : `aws:SecureTransport` vaut `false` sur une requête en HTTP clair : un `Deny` conditionné, pour `Principal: "*"`, refuse ces requêtes quelles que soient les politiques IAM. Un `Deny` n'est jamais « public » : le blocage d'accès public l'accepte. Les SDK parlent déjà HTTPS ; la règle prouve qu'aucun client ne peut faire autrement (contrôle Security Hub S3.5).
- Usage : ✅ `HttpsOnly` sur chaque bucket de données (`raw`, `processed`, `out`) · ❌ `Deny` sans condition sur `Principal: "*"` : il enferme aussi l'admin et Terraform, seul le root peut alors retirer la politique.

```hcl
# Exemple 1 : refuser le HTTP clair
statement {
  sid     = "HttpsOnly"
  effect  = "Deny"
  actions = ["s3:*"]
  principals {
    type        = "*"
    identifiers = ["*"]
  }
  resources = [
    aws_s3_bucket.raw.arn,
    "${aws_s3_bucket.raw.arn}/*",
  ]
  condition {
    test     = "Bool"
    variable = "aws:SecureTransport"
    values   = ["false"]
  }
}
```

```bash
# Exemple 2 : simulé, admin avec s3:*
# aws:SecureTransport=true  → allowed
# aws:SecureTransport=false → explicitDeny
```

- Quiz : On écrit plutôt `Allow` à `Principal: "*"` si `aws:SecureTransport = true` : que fait le blocage d'accès public ?
- [ ] Accepte : la condition rend la politique privée
- [ ] Accepte, mais ignore la politique
- [x] Refuse : un `Allow` à `*` reste public
- [ ] Refuse : `Bool` est interdit en politique de bucket
- Réponse : refus : `SecureTransport` ne restreint pas qui appelle, donc tout internet serait autorisé en HTTPS ; `block_public_policy` rejette la politique.

## 12. ACL : désactivées par défaut
- Sous-thème : accès
- Niveau : 2
- Définition : `BucketOwnerEnforced`, le défaut depuis avril 2023, désactive les ACL : le bucket possède tout objet, et seules les politiques décident des accès.
- Contexte : Les ACL datent d'avant IAM : chaque objet avait un propriétaire, parfois le compte qui l'avait écrit, et le propriétaire du bucket pouvait perdre l'accès à ses propres données. Avec `BucketOwnerEnforced`, une requête qui pose une ACL autre que `bucket-owner-full-control` échoue (`AccessControlListNotSupported`). Les buckets data-platform sont dans ce mode sans l'avoir écrit.
- Usage : ✅ garder le défaut, gérer l'accès par IAM et politique de bucket · ❌ réactiver les ACL (`ObjectWriter`) : seulement pour un service ancien qui l'exige, comme les logs standard de CloudFront.

```bash
# Exemple 1 : le mode du bucket raw
aws s3api get-bucket-ownership-controls \
  --bucket "$RAW" --query \
  'OwnershipControls.Rules[0].ObjectOwnership'
# → "BucketOwnerEnforced"  (mesuré)
```

```hcl
# Exemple 2 : l'écrire explicitement
resource "aws_s3_bucket_ownership_controls" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
```

- Quiz : Un compte partenaire écrit dans `out`, autorisé par la politique de bucket : à qui appartient l'objet ?
- [ ] Au compte partenaire, qui l'a écrit
- [x] Au compte propriétaire du bucket
- [ ] Aux deux comptes
- [ ] À personne tant qu'aucune ACL n'est posée
- Réponse : au propriétaire du bucket : avec `BucketOwnerEnforced`, l'écrivain ne garde aucun droit propre sur l'objet.

## 13. logs d'accès S3 : jamais vers lui-même
- Sous-thème : accès
- Niveau : 2
- Source : data-platform · S1-04
- Définition : Le server access logging écrit une ligne par requête reçue par un bucket (qui, quoi, quand) dans un bucket cible, sous un préfixe.
- Contexte : La cible doit autoriser le service `logging.s3.amazonaws.com` à écrire (`s3:PutObject`, borné par `aws:SourceAccount`), d'où une politique posée avant l'activation (`depends_on`). Le bucket de logs ne se logge pas lui-même : chaque écriture de log serait une requête qui produit un log, une boucle facturée sans information. Qui lit `logs` : CloudTrail.
- Usage : ✅ un bucket `logs` qui reçoit tous les autres sous `s3/<nom>/`, avec une expiration (30 j) · ❌ activer le logging du bucket `logs` vers lui-même : la boucle.

```hcl
# Exemple 1 : tous sauf logs, vers logs
locals {
  logged = { for k, b in aws_s3_bucket.this : k => b if k != "logs" }
}
resource "aws_s3_bucket_logging" "this" {
  for_each      = local.logged
  bucket        = each.value.id
  target_bucket = aws_s3_bucket.this["logs"].id
  target_prefix = "s3/${each.key}/"
}
```

```bash
# Exemple 2 : vérifier sur AWS
aws s3api get-bucket-logging --bucket "$RAW"
# → "TargetPrefix": "s3/raw/"
aws s3api get-bucket-logging --bucket "$LOGS"
# → (vide : logs ne se logge pas)
```

- Quiz : Une lecture de `processed` à 10 h : quand sa ligne arrive-t-elle dans `logs` ?
- [ ] Aussitôt, à chaque requête
- [ ] Sous une minute, garanti
- [x] En général en quelques heures, sans garantie
- [ ] Jamais : il faut activer CloudTrail
- Réponse : en quelques heures, au mieux : la livraison est « best effort » et une requête peut manquer ; pour un audit complet et rapide, les data events CloudTrail.

## 14. GET Range : lire un morceau
- Sous-thème : requêtes
- Niveau : 2
- Définition : L'en-tête `Range: bytes=début-fin` lit une partie d'un objet (réponse `206`) : S3 n'écrit jamais en partie, mais lit en partie.
- Contexte : C'est ainsi qu'Athena ou Spark lisent un Parquet : d'abord le footer, à la fin du fichier, qui décrit colonnes et row groups, puis seulement les colonnes utiles. On paie la requête et les octets transférés, pas l'objet entier. Les bornes sont incluses : `bytes=0-99` rend 100 octets. Le chiffrement SSE ne change rien côté client.
- Usage : ✅ lire l'en-tête d'un gros fichier, télécharger en parallèle par tranches · ❌ modifier une ligne au milieu d'un objet : il faut réécrire l'objet entier.

```bash
# Exemple 1 : les 100 premiers octets
aws s3api get-object \
  --bucket "$CONTENT" \
  --key content/catalog.json \
  --range bytes=0-99 debut.json \
  --query ContentRange
# → "bytes 0-99/686306"  (mesuré)
```

```python
# Exemple 2 : bornes incluses, comme S3
data = b'{"generatedAt":"2026-10-24"}'

def lire(debut, fin):   # bytes=debut-fin
    return data[debut:fin + 1]

lire(0, 9)          # → b'{"generate'
len(lire(0, 99))    # → 28  (tronqué au bout)
```

- Quiz : Que renvoie `--range bytes=-500` sur `catalog.json` ?
- [ ] Les 500 premiers octets
- [x] Les 500 derniers octets
- [ ] Tout sauf les 500 derniers
- [ ] `InvalidRange`
- Réponse : les 500 derniers (mesuré : `bytes 685806-686305/686306`) : sans début, la plage compte depuis la fin, comme pour lire un footer Parquet.

## 15. s3 sync --delete : les exclus sont épargnés
- Sous-thème : requêtes
- Niveau : 2
- Source : revision-pwa · pwa-revision
- Définition : `aws s3 sync --delete` supprime de la destination ce qui manque à la source, sauf les chemins écartés par `--exclude` / `--include`.
- Contexte : Les filtres valent pour l'envoi comme pour la suppression. `make deploy` s'en sert : le 2e `sync` (tout sauf `assets/*`) supprime les anciens `sw.js` ou icônes mais garde les anciens assets, utiles aux visiteurs encore sur l'ancien `index.html` ; le 3e, limité à `assets/`, les supprime en dernier. `sync` compare taille et date : relancé sans changement, il n'envoie rien.
- Usage : ✅ `--dryrun` avant tout `--delete`, filtres pour borner ce qui peut disparaître · ❌ `--delete` sans filtre à la racine d'un bucket partagé : tout ce qui manque en local part.

```bash
# Exemple 1 : --dryrun, bucket site
# dist/ ne contient qu'index.html
aws s3 sync dist/ s3://$SITE_BUCKET/ \
  --delete --exclude "assets/*" \
  --dryrun
# → upload: dist/index.html
# → delete: …/sw.js, …/favicon.svg…
#   aucun delete sous assets/
```

- Quiz : Avec `--exclude "*" --include "cartes-*.md" --delete`, un `notes.txt` du préfixe distant est-il supprimé ?
- [ ] Oui : absent en local, `--delete` l'emporte
- [x] Non : exclu par les filtres, il n'est jamais touché
- [ ] Oui, sauf si le bucket est versionné
- [ ] Oui, mais au second lancement seulement
- Réponse : non : `--exclude "*"` l'écarte et aucun `--include` ne le reprend ; les filtres bornent aussi la suppression (même mécanisme que `assets/*`, vu au `--dryrun`).

## 16. événement S3 : clé URL-encodée
- Sous-thème : événements
- Niveau : 2
- Définition : Une notification S3 transmet la clé de l'objet URL-encodée (`=` → `%3D`, espace → `+`) : la décoder avant `get_object`.
- Contexte : L'événement contient bucket, clé, taille et ETag, jamais le contenu : la Lambda doit relire l'objet. La clé arrive encodée comme dans un formulaire HTML ; l'utiliser telle quelle donne `NoSuchKey` dès qu'elle contient `=`, une espace ou un accent. Le piège passe inaperçu en test avec des clés simples, puis casse sur les partitions `dt=`.
- Usage : ✅ toujours `unquote_plus` sur `object.key` avant tout appel S3 · ❌ `unquote` seul : laisse les `+` ; reconstruire la clé à la main.

```python
# Exemple 1 : décoder la clé reçue
from urllib.parse import unquote_plus

key = "bodacc/dt%3D2026-10-23/a+b.gz"
unquote_plus(key)
# → "bodacc/dt=2026-10-23/a b.gz"
```

```python
# Exemple 2 : dans le handler
from urllib.parse import unquote_plus

event = {"Records": [{"s3": {
    "bucket": {"name": "dp-dev-raw"},
    "object": {"key":
      "bodacc/dt%3D2026-10-23/p.gz"},
}}]}

def handler(event, context):
    s3 = event["Records"][0]["s3"]
    return (s3["bucket"]["name"],
            unquote_plus(s3["object"]["key"]))

handler(event, None)
# → ("dp-dev-raw", "bodacc/dt=2026-10-23/p.gz")
```

- Quiz : Que renvoie `unquote` (sans `_plus`) sur `"tribunal+de+paris.json"` ?
- [ ] `"tribunal de paris.json"`
- [x] `"tribunal+de+paris.json"`
- [ ] `"tribunal%20de%20paris.json"`
- [ ] `ValueError`
- Réponse : `"tribunal+de+paris.json"`, inchangé : `unquote` ne traduit pas `+` en espace ; `get_object` répond alors `NoSuchKey`.

## 17. notification S3 : la boucle
- Sous-thème : événements
- Niveau : 2
- Définition : Une notification S3 invoque une Lambda à chaque création d'objet qui correspond au filtre de préfixe et de suffixe.
- Contexte : L'invocation est asynchrone : S3 n'attend pas la Lambda et ne sait pas qui a écrit l'objet. Si la Lambda écrit dans le préfixe qu'elle surveille, elle se redéclenche elle-même, sans fin, et la facture suit. Un même couple préfixe / suffixe ne peut cibler qu'une destination ; pour plusieurs consommateurs, passer par EventBridge.
- Usage : ✅ contrôle d'un fichier dès son dépôt dans `raw` · ❌ Lambda qui écrit dans le préfixe qu'elle écoute : écrire dans un autre préfixe ou bucket, filtrer le suffixe.

```hcl
# Exemple 1 : seuls les .jsonl.gz
resource "aws_s3_bucket_notification" "n" {
  bucket = aws_s3_bucket.raw.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.check.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "bodacc/"
    filter_suffix = ".jsonl.gz"
  }
}
```

- Quiz : Sans `filter_suffix`, la Lambda écrit `bodacc/…/_MANIFEST.json` après chaque contrôle : que se passe-t-il ?
- [ ] Rien : S3 ignore les écritures des Lambdas
- [ ] Un seul redéclenchement, puis S3 déduplique
- [ ] `terraform apply` refuse la notification
- [x] Une boucle : chaque manifest relance la Lambda
- Réponse : une boucle : chaque manifest est un nouvel objet sous `bodacc/`, qui relance la Lambda, qui écrit un manifest ; filtrer le suffixe ou écrire ailleurs.

## 18. bucket versionné : supprimer
- Sous-thème : cycle de vie
- Niveau : 3
- Définition : Sur un bucket versionné, chaque écrasement garde l'ancienne version, récupérable par son `VersionId`, et facturée comme un objet normal.
- Contexte : Le versioning protège `raw` d'un rejeu qui écraserait un bon fichier. Mais l'espace ne baisse jamais tout seul : une règle `expiration` ne touche que la version courante. Pour purger, il faut `noncurrent_version_expiration`, et `expired_object_delete_marker` pour nettoyer les marqueurs orphelins. Une fois activé, le versioning ne peut que passer en pause (`Suspended`), jamais être retiré.
- Usage : ✅ versioning sur `raw` et sur le bucket d'état Terraform · ❌ versioning sans règle sur les versions non courantes : la facture grossit à chaque rejeu.

```bash
# Exemple 1 : un rejeu = 2 versions
aws s3api list-object-versions \
  --bucket dp-dev-raw \
  --prefix bodacc/dt=2026-10-23/
# → part-0001.jsonl.gz
#   IsLatest: true  (rejeu du 24)
#   IsLatest: false (run du 23)
```

```hcl
# Exemple 2 : purger aussi les anciennes
rule {
  id     = "raw-90j"
  status = "Enabled"
  filter { prefix = "bodacc/" }
  expiration { days = 90 }
  noncurrent_version_expiration {
    noncurrent_days = 7
  }
}
```

- Quiz : Sur ce bucket versionné, `aws s3 rm s3://dp-dev-raw/bodacc/…/part-0001.jsonl.gz` : l'objet est-il encore facturé ?
- [ ] Non : l'objet est supprimé
- [ ] Non : S3 purge les versions sous 24 h
- [x] Oui : un delete marker cache les versions
- [ ] Erreur : il faut préciser `--version-id`
- Réponse : oui : sans `VersionId`, S3 pose un delete marker ; les versions restent stockées et facturées jusqu'à `noncurrent_version_expiration`.

## 19. réplication : seulement les nouveaux objets
- Sous-thème : cycle de vie
- Niveau : 3
- Définition : La réplication S3 copie de façon asynchrone les nouveaux objets d'un bucket versionné vers un autre, dans une autre région (CRR) ou la même (SRR).
- Contexte : Un rôle IAM lit la source et écrit la destination, avec les droits KMS des deux clés en SSE-KMS. Les objets présents avant la règle ne sont pas copiés : il faut S3 Batch Replication. Par défaut, les delete markers ne suivent pas, et une suppression par `VersionId` n'est jamais répliquée : la copie survit à une erreur humaine sur la source.
- Usage : ✅ copie de secours de `raw` dans une autre région, exigence de résidence ou de latence · ❌ se protéger d'un rejeu qui écrase : le versioning suffit ; copie ponctuelle : `aws s3 sync`.

```hcl
# Exemple 1 : raw vers un bucket de secours
resource "aws_s3_bucket_replication_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  role   = aws_iam_role.repl.arn
  rule {
    id     = "vers-dr"
    status = "Enabled"
    filter { prefix = "bodacc/" }
    delete_marker_replication {
      status = "Disabled"
    }
    destination {
      bucket = aws_s3_bucket.dr.arn
    }
  }
}
```

- Quiz : Le bucket de destination n'est pas versionné : que se passe-t-il ?
- [x] AWS refuse la règle à l'`apply`
- [ ] La réplication marche, sans historique
- [ ] S3 active seul le versioning de la destination
- [ ] Seules les suppressions échouent
- Réponse : refus à l'`apply` (`InvalidRequest`, selon la doc) : source et destination doivent toutes deux être versionnées avant la règle.

## 20. Object Lock : écrire une fois
- Sous-thème : cycle de vie
- Niveau : 3
- Définition : Object Lock interdit de supprimer ou d'écraser une version d'objet pendant une durée de rétention : stockage WORM (écrire une fois, lire souvent).
- Contexte : Il exige le versioning. En mode `GOVERNANCE`, un principal qui a `s3:BypassGovernanceRetention` peut lever le verrou ; en `COMPLIANCE`, personne, root compris, avant l'échéance : seule la fermeture du compte libère la place. Un `DELETE` sans `VersionId` réussit quand même : il pose un delete marker, la version verrouillée reste. Le legal hold verrouille sans durée.
- Usage : ✅ archive réglementaire, journaux d'audit, sauvegardes contre un rançongiciel · ❌ `COMPLIANCE` en dev ou pour essayer : objets impossibles à supprimer avant l'échéance, et facturés jusque-là.

```hcl
# Exemple 1 : un an, sans dérogation
resource "aws_s3_bucket" "audit" {
  bucket              = "dp-dev-audit"
  object_lock_enabled = true
}
resource "aws_s3_bucket_object_lock_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 365
    }
  }
}
```

- Quiz : Ce bucket a `force_destroy = true` et des objets de moins d'un an : que fait `terraform destroy` ?
- [ ] Vide le bucket et le supprime
- [ ] Supprime les objets, garde le bucket
- [x] Échoue : les versions verrouillées résistent
- [ ] Demande la confirmation du root
- Réponse : échec : `force_destroy` supprime chaque version, ce que `COMPLIANCE` interdit à tous ; le bucket reste tant qu'une version est sous rétention.

## 21. S3 : écritures concurrentes
- Sous-thème : requêtes
- Niveau : 3
- Définition : S3 est fortement cohérent : un `GET` ou `LIST` après un `PUT` réussi voit l'objet ; une écriture conditionnelle refuse d'écraser une clé existante.
- Contexte : Depuis fin 2020, plus besoin d'attendre après un `PUT` pour lister. Mais S3 ne verrouille rien : deux `PUT` sur la même clé réussissent tous les deux. `If-None-Match: *` (2024) fait échouer l'écriture si la clé existe déjà (`412 Precondition Failed`) ; `If-Match: <ETag>` n'écrase que la version lue, comme un verrou optimiste.
- Usage : ✅ `If-None-Match` pour un marqueur « jour traité » écrit une seule fois · ❌ un fichier S3 comme compteur ou verrou partagé : DynamoDB et ses écritures conditionnelles.

```bash
# Exemple 1 : écrire une seule fois
aws s3api put-object \
  --bucket dp-dev-raw \
  --key bodacc/dt=2026-10-23/_DONE \
  --body done.txt \
  --if-none-match '*'
# 1er appel → OK (ETag)
# 2e appel  → 412 PreconditionFailed
```

```python
# Exemple 2 : la même règle, simulée
store = {}

def put_si_absente(cle, data):
    if cle in store:
        return 412          # refusé
    store[cle] = data
    return 200

put_si_absente("_DONE", "run-1")  # → 200
put_si_absente("_DONE", "run-2")  # → 412
store["_DONE"]  # → "run-1"
```

- Quiz : Sans condition, deux Lambdas font un `PutObject` sur la même clé au même moment : que se passe-t-il ?
- [ ] La seconde reçoit `409 Conflict`
- [x] Les deux réussissent, la dernière arrivée reste
- [ ] La première gagne, la seconde est ignorée
- [ ] S3 garde les deux objets sous la même clé
- Réponse : les deux réussissent et la dernière écriture reçue l'emporte, sans erreur ; seule une condition (`If-None-Match`, `If-Match`) fait échouer l'une des deux.

## 22. ETag : pas toujours un MD5
- Sous-thème : requêtes
- Niveau : 3
- Définition : L'ETag d'un objet envoyé d'un bloc est le MD5 de son contenu ; en multipart, c'est le MD5 des MD5 des parts, suffixé `-N`.
- Contexte : Comparer un MD5 local à l'ETag ne marche que pour un `PutObject` simple, et hors SSE-KMS, où l'ETag n'est pas non plus un MD5. Le même fichier envoyé avec une autre taille de part donne un autre ETag. Pour l'intégrité, demander une somme de contrôle (`--checksum-algorithm SHA256`, ou le CRC des SDK récents), conservée par S3 avec l'objet.
- Usage : ✅ ETag pour détecter un changement (`If-Match`, cache HTTP) · ❌ ETag comme preuve d'intégrité d'un fichier : checksum SHA-256 ou CRC.

```python
# Exemple 1 : ETag multipart recalculé
from hashlib import md5

parts = [b"a" * 10, b"b" * 10, b"c" * 3]
d = b"".join(md5(p).digest() for p in parts)
etag = f"{md5(d).hexdigest()}-{len(parts)}"
etag.endswith("-3")    # → True
etag == md5(b"".join(parts)).hexdigest()
# → False
```

```bash
# Exemple 2 : un zip de 22 Mo (CDK)
aws s3api list-objects-v2 --bucket "$B" \
  --query "Contents[?contains(ETag,'-')]
    .[Size,ETag]"
# → 22004168
#   "cd79d071…-5"   (5 parts, mesuré)
```

- Quiz : Un fichier de 3,7 Ko envoyé en multipart avec une seule part : quel ETag ?
- [ ] Le MD5 simple : sous 5 Mo, pas de multipart
- [x] Un MD5 de MD5, suffixé `-1`
- [ ] Erreur : une part fait au moins 5 Mo
- [ ] Le MD5 suffixé `-0`
- Réponse : un MD5 de MD5 suffixé `-1` (mesuré sur un artefact CodePipeline de 3 747 octets) : la dernière part peut faire moins de 5 Mo, même si c'est la seule.
