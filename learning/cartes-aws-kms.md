---
title: "Cartes · KMS"
type: cartes
langage: AWS
cours: KMS
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · KMS
AWS · KMS : clés, chiffrement, politique, s3 (format spec v3 de revision-pwa).

## 1. clé gérée par AWS ou par le client
- Sous-thème : clés
- Niveau : 1
- Définition : `aws/s3` est une clé gérée par AWS, gratuite au repos ; une clé client (`aws_kms_key`) se paie, mais on écrit sa politique.
- Contexte : La clé `aws/s3` est utilisable par tout le compte, mais seulement à travers S3, jamais en direct ni par un autre compte ; AWS la fait tourner chaque année. La clé du projet (`KeyManager: CUSTOMER`) permet de choisir qui chiffre et déchiffre, de la désactiver, de la partager. Les clés détenues par AWS, celles de SSE-S3, n'apparaissent même pas dans le compte.
- Usage : ✅ clé client pour les données du projet (accès bornés, audit, partage possible) · ❌ `aws/s3` pour des données à partager avec un autre compte : sa politique l'interdit.

```bash
# Exemple 1 : deux clés du compte
aws kms describe-key --key-id alias/aws/s3 \
  --query KeyMetadata.KeyManager
# → "AWS"
aws kms describe-key \
  --key-id alias/data-platform-dev \
  --query KeyMetadata.KeyManager
# → "CUSTOMER"   (mesuré)
```

```bash
# Exemple 2 : la politique de aws/s3
aws kms get-key-policy --key-id "$AWS_S3" \
  --query Policy --output text
# → "Principal": {"AWS": "*"}
#   "kms:CallerAccount": "<id>"
#   "kms:ViaService":
#     "s3.eu-west-3.amazonaws.com"
```

- Quiz : Qui peut programmer la suppression de la clé `aws/s3` du compte ?
- [ ] L'administrateur, avec 7 jours de délai
- [ ] Le root du compte seulement
- [ ] Terraform, après un `import`
- [x] Personne : AWS gère son cycle de vie
- Réponse : personne : une clé gérée par AWS ne se supprime, ne se désactive ni ne se modifie ; seules les clés client ont un cycle de vie à la main.

## 2. alias KMS : le nom, l'ARN pour les ressources
- Sous-thème : clés
- Niveau : 1
- Source : data-platform · S1-04
- Définition : Une clé KMS est désignée par un ARN opaque ; l'alias `alias/<nom>` est un nom lisible et stable qui pointe vers elle.
- Contexte : On ne voit jamais la clé : on demande à KMS de chiffrer ou déchiffrer, chaque appel est autorisé par IAM et tracé dans CloudTrail. L'ARN change à chaque recréation, l'alias reste : les humains utilisent l'alias, les ressources Terraform l'ARN (`module.kms.key_arn`), qui crée la dépendance. Une clé coûte 1 $/mois plus les appels ; `enable_key_rotation` renouvelle le matériel chaque année sans changer l'ARN.
- Usage : ✅ une clé par projet et environnement, alias `alias/<projet>-<env>`, ARN passé aux modules · ❌ ARN recopié en dur : il change au prochain `make down` / `make up`.

```hcl
# Exemple 1 : la clé et son alias
resource "aws_kms_key" "this" {
  description             = "data-platform-dev"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}
resource "aws_kms_alias" "this" {
  name          = "alias/data-platform-dev"
  target_key_id = aws_kms_key.this.key_id
}
# aws_kms_key.this.arn → arn:aws:kms:
#   eu-west-3:<id>:key/<uuid>
```

```bash
# Exemple 2 : lire la clé par son alias
aws kms describe-key \
  --key-id alias/data-platform-dev \
  --query KeyMetadata.KeyState
# → "Enabled"
K=$(aws kms describe-key \
  --key-id alias/data-platform-dev \
  --query KeyMetadata.Arn --output text)
```

- Quiz : Que répond `aws kms get-key-rotation-status --key-id alias/data-platform-dev` ?
- [ ] `"KeyRotationEnabled": true`
- [ ] `"KeyRotationEnabled": false`
- [x] `InvalidArnException` : alias refusé
- [ ] `NotFoundException` : alias inconnu
- Réponse : `InvalidArnException` (« Key Aliases are not supported for this operation », mesuré) : `get-key-rotation-status` et `get-key-policy` exigent l'id ou l'ARN de la clé, d'où le `$K` de l'exemple 2.

## 3. coût KMS : la clé et les appels
- Sous-thème : clés
- Niveau : 1
- Définition : Une clé client coûte 1 $ par mois, plus 0,03 $ les 10 000 appels (`Decrypt`, `GenerateDataKey`) au-delà de 20 000 gratuits par mois.
- Contexte : Le poste qui surprend est celui des appels : en SSE-KMS sans bucket key, S3 en fait un par objet écrit ou lu. Les clés gérées par AWS ne coûtent rien au repos, mais leurs appels se paient. La rotation automatique ajoute aussi un coût par version de matériel conservée, plafonné.
- Usage : ✅ une clé par projet et environnement, bucket key sur les buckets · ❌ une clé par bucket ou par table « pour isoler » : 1 $/mois chacune, et autant de politiques à tenir.

```python
# Exemple 1 : un mois, sans bucket key
objets_jour = 1500        # écrits + relus
appels = objets_jour * 2 * 30
payants = max(0, appels - 20_000)
round(1 + payants / 10_000 * 0.03, 2)
# → 1.21  ($/mois)
```

- Quiz : Clé avec rotation annuelle, au bout de 5 ans (5 rotations) : combien coûte-t-elle au repos par mois ?
- [ ] 1 $
- [x] 3 $
- [ ] 5 $
- [ ] 6 $
- Réponse : 3 $ (grille tarifaire KMS) : chaque rotation ajoute 1 $/mois pour les deux premières seulement ; au-delà, le prix ne bouge plus.

## 4. KMS : la clé ne sort jamais
- Sous-thème : chiffrement
- Niveau : 1
- Définition : KMS garde la clé dans ses HSM : on lui envoie les données (`Encrypt`, 4 096 octets au plus), il renvoie le texte chiffré.
- Contexte : Aucune API ne rend le matériel d'une clé symétrique : c'est ce qui permet de couper un accès en retirant un droit, et de tracer chaque usage dans CloudTrail. La contrepartie : chaque opération est un appel réseau, limité à 4 Ko en entrée. Pour un fichier BODACC, on chiffre localement avec une clé de données : le chiffrement d'enveloppe.
- Usage : ✅ `Encrypt` direct pour un petit secret (jeton, mot de passe) · ❌ `Encrypt` sur un fichier : `ValidationException` au-delà de 4 Ko ; clé de données, ou SSE-KMS côté S3.

```bash
# Exemple 1 : un petit secret
aws kms encrypt \
  --key-id alias/data-platform-dev \
  --plaintext fileb://jeton.txt \
  --query CiphertextBlob --output text
# → AQICAHh…  (base64)
```

```python
# Exemple 2 : la limite d'entrée
LIMITE = 4096                 # octets

def chiffrable(data: bytes):
    return len(data) <= LIMITE

chiffrable(b"jeton-api-1234")  # → True
chiffrable(b"x" * 5000)        # → False
```

- Quiz : Un secret de 3 000 caractères `é` : `kms encrypt` l'accepte-t-il ?
- [ ] Oui : 3 000 < 4 096
- [x] Non : 6 000 octets en UTF-8
- [ ] Oui, KMS compresse l'entrée
- [ ] Non : KMS refuse l'UTF-8
- Réponse : non : la limite compte des octets, et `é` en prend 2 en UTF-8 ; `len("é" * 3000)` vaut 3 000, `len(("é" * 3000).encode())` 6 000.

## 5. rotation : même ARN, nouveau matériel
- Sous-thème : clés
- Niveau : 2
- Définition : `enable_key_rotation` génère un nouveau matériel de clé chaque année (ou tous les `rotation_period_in_days`) sans changer l'ARN ni rechiffrer les données.
- Contexte : KMS garde toutes les versions du matériel : les nouveaux chiffrements prennent la dernière, les anciens blobs se déchiffrent avec la leur. Rien à changer dans le code. La rotation ne protège donc pas ce qui a déjà été chiffré avec un matériel compromis : elle limite seulement le volume chiffré par version. `rotate-key-on-demand` force une rotation immédiate.
- Usage : ✅ rotation automatique sur toute clé client symétrique (365 jours par défaut) · ❌ créer une nouvelle clé « pour tourner » : nouvel ARN, et l'ancienne doit rester pour lire l'existant.

```bash
# Exemple 1 : l'état de la rotation
aws kms get-key-rotation-status \
  --key-id "$K"
# → "KeyRotationEnabled": true
#   "RotationPeriodInDays": 365
#   "NextRotationDate": "2027-10-23…"
```

```hcl
# Exemple 2 : tous les 90 jours
resource "aws_kms_key" "this" {
  description             = "data-platform-dev"
  enable_key_rotation     = true
  rotation_period_in_days = 90
  deletion_window_in_days = 7
}
```

- Quiz : `rotation_period_in_days = 30` pour tourner chaque mois : que se passe-t-il ?
- [ ] Rotation chaque mois
- [ ] Valeur ignorée : 365 jours
- [ ] `apply` refusé par AWS
- [x] `validate` échoue : de 90 à 2 560 jours
- Réponse : `validate` échoue (`expected rotation_period_in_days to be in the range (90 - 2560), got 30`, mesuré) : KMS ne tourne pas plus souvent que tous les 90 jours.

## 6. clé désactivée : tout s'arrête
- Sous-thème : clés
- Niveau : 2
- Définition : `disable-key` suspend une clé : chiffrer et déchiffrer échouent (`DisabledException`) jusqu'à `enable-key`, sans rien perdre.
- Contexte : C'est l'interrupteur d'urgence : en cas de fuite, désactiver la clé rend illisibles d'un coup tous les objets SSE-KMS de `raw` et `processed`, même pour l'administrateur, sans toucher aux données ni aux politiques. Contrairement à la suppression, c'est réversible. Une clé désactivée reste facturée 1 $/mois.
- Usage : ✅ couper l'accès en incident, vérifier ce qui dépend d'une clé avant de la supprimer · ❌ supprimer d'emblée une clé qu'on croit inutile : la désactiver d'abord, puis guetter les erreurs.

```bash
# Exemple 1 : couper puis rétablir
aws kms disable-key --key-id "$K"
aws s3 cp "s3://$RAW/bodacc/p.gz" .
# → KMS.DisabledException
aws kms enable-key --key-id "$K"
# → la lecture refonctionne
```

- Quiz : Clé désactivée : `aws s3 ls s3://$RAW/bodacc/` fonctionne-t-il ?
- [x] Oui : lister ne déchiffre rien
- [ ] Non : `DisabledException`
- [ ] Non : `AccessDenied`
- [ ] Oui, mais les clés sont masquées
- Réponse : oui : le listage lit les métadonnées du bucket, en clair ; seuls `GetObject` et `PutObject` passent par KMS.

## 7. clé KMS : suppression différée
- Sous-thème : clés
- Niveau : 2
- Source : data-platform · S1-04
- Définition : Supprimer une clé KMS la place en `PendingDeletion` pendant 7 à 30 jours (`deletion_window_in_days`) ; elle n'est détruite qu'à l'échéance.
- Contexte : Une clé détruite rend illisible tout ce qu'elle chiffre, d'où le délai : pendant la fenêtre, la clé ne chiffre ni ne déchiffre plus, mais `cancel-key-deletion` la récupère. L'alias, lui, est supprimé tout de suite. Après `make down` puis `make up`, Terraform crée donc une nouvelle clé (nouvel ARN) sous le même alias ; les objets encore chiffrés par l'ancienne seront perdus à l'échéance.
- Usage : ✅ 7 jours en dev (environnement jetable, buckets vidés au `down`) · ❌ 7 jours en prod : 30 jours, et `prevent_destroy` sur la clé.

```bash
# Exemple 1 : après make down puis make up
# → Enabled          (nouvelle clé)
#   PendingDeletion  (ancienne, 7 j)
for k in $(aws kms list-keys \
    --query 'Keys[].KeyId' --output text)
do
  aws kms describe-key --key-id "$k" \
    --query 'KeyMetadata.KeyState'
done
```

```bash
# Exemple 2 : annuler pendant la fenêtre
aws kms cancel-key-deletion --key-id "$K"
# → la clé revient en Disabled
aws kms enable-key --key-id "$K"
# → Enabled : elle déchiffre de nouveau
```

- Quiz : `deletion_window_in_days = 0` pour supprimer la clé tout de suite en dev : que se passe-t-il ?
- [ ] La clé est détruite dès `destroy`
- [ ] Valeur ignorée : 30 jours par défaut
- [ ] `destroy` échoue côté AWS
- [x] `validate` échoue : plage de 7 à 30
- Réponse : `validate` échoue (`expected deletion_window_in_days to be in the range (7 - 30), got 0`, mesuré) : KMS n'offre aucune suppression immédiate.

## 8. chiffrement d'enveloppe : la clé de données
- Sous-thème : chiffrement
- Niveau : 2
- Définition : `GenerateDataKey` renvoie une clé de données en clair (pour chiffrer localement) et la même clé chiffrée par la clé KMS (à stocker avec les données).
- Contexte : On chiffre le fichier en AES-256 avec `Plaintext`, on l'efface de la mémoire, on garde `CiphertextBlob` à côté du fichier. Pour relire : `Decrypt` sur le blob rend la clé de données, qui déchiffre le fichier. Un seul appel KMS par fichier, quelle que soit sa taille. C'est ce que fait S3 en SSE-KMS, et l'AWS Encryption SDK.
- Usage : ✅ chiffrer côté client un export `out/` avant de l'envoyer · ❌ stocker la clé de données en clair à côté du fichier : on ne garde que `CiphertextBlob`.

```bash
# Exemple 1 : demander une clé de données
aws kms generate-data-key \
  --key-id alias/data-platform-dev \
  --key-spec AES_256
# → "Plaintext": "base64…"
#   "CiphertextBlob": "AQIDAHh…"
#   "KeyId": "arn:…:key/aa494944…"
```

```python
# Exemple 2 : le principe, simulé
import secrets
from hashlib import sha256

def xor(data, cle):        # jouet, pas AES
    flux = sha256(cle).digest() * 64
    return bytes(a ^ b for a, b
                 in zip(data, flux))

MAITRE = secrets.token_bytes(32)  # dans KMS
cle = secrets.token_bytes(32)     # data key
blob = xor(cle, MAITRE)    # CiphertextBlob
fichier = xor(b"SIREN 552100554", cle)

cle2 = xor(blob, MAITRE)   # ≈ Decrypt(blob)
xor(fichier, cle2)  # → b"SIREN 552100554"
```

- Quiz : Avec `--key-spec AES_256`, quelle taille fait `Plaintext` une fois décodé du base64 ?
- [ ] 256 octets
- [x] 32 octets
- [ ] 16 octets
- [ ] 4 096 octets
- Réponse : 32 octets : AES-256 désigne une clé de 256 bits, soit 32 octets ; `AES_128` en donne 16.

## 9. Decrypt : pas besoin de KeyId
- Sous-thème : chiffrement
- Niveau : 2
- Définition : Pour une clé symétrique, `Decrypt` retrouve seul la clé KMS : son identifiant est inscrit dans le `CiphertextBlob`, `--key-id` est facultatif.
- Contexte : Le blob porte en métadonnées la clé et la version du matériel : après rotation, les anciens blobs se déchiffrent toujours. Préciser `--key-id` reste la bonne pratique : KMS refuse alors un blob d'une autre clé, ce qui évite de déchiffrer, avec les droits du rôle, un texte forgé sur une clé que le projet ne maîtrise pas. Le droit vérifié est `kms:Decrypt` sur la clé d'origine.
- Usage : ✅ `--key-id` explicite dans le code de production · ❌ croire qu'un `Decrypt` réussi prouve que la donnée vient du projet : sans `key-id`, toute clé accessible convient.

```bash
# Exemple 1 : sans --key-id
aws kms decrypt \
  --ciphertext-blob fileb://jeton.enc \
  --query KeyId --output text
# → arn:aws:kms:eu-west-3:<id>:key/
#   aa494944-…   (retrouvée dans le blob)
```

- Quiz : `decrypt --key-id alias/autre-cle` sur un blob chiffré par `data-platform-dev` : résultat ?
- [ ] Déchiffré : le blob prime sur le paramètre
- [ ] `InvalidCiphertextException`
- [x] `IncorrectKeyException`
- [ ] `NotFoundException`
- Réponse : `IncorrectKeyException` (selon la doc) : la clé demandée n'est pas celle qui a chiffré ; le blob est intact, d'où une erreur distincte d'`InvalidCiphertext`.

## 10. SSE-KMS : la seconde serrure
- Sous-thème : s3
- Niveau : 2
- Source : data-platform · S1-04
- Définition : Sur un bucket `aws:kms`, lire ou écrire exige deux droits : l'action S3 et l'action KMS sur la clé (`kms:Decrypt`, `kms:GenerateDataKey`).
- Contexte : S3 appelle KMS au nom de l'appelant : `GetObject` déchiffre la clé de données (`kms:Decrypt`), `PutObject` en génère une (`kms:GenerateDataKey`). Un rôle qui a `s3:GetObject` sans droit KMS reçoit `AccessDenied`, alors que sa politique S3 paraît juste. C'est voulu : la clé est une serrure indépendante, tracée dans CloudTrail, révocable d'un geste en la désactivant.
- Usage : ✅ un statement `UseProjectKey` sur l'ARN de la clé dans chaque rôle qui touche aux buckets · ❌ `kms:*` ou `resources = ["*"]` : borner aux actions utiles et à l'ARN de la clé.

```hcl
# Exemple 1 : S3 et KMS dans le même rôle
statement {
  sid       = "ReadRaw"
  actions   = ["s3:GetObject"]
  resources = ["${var.bucket_arns["raw"]}/*"]
}
statement {
  sid       = "UseProjectKey"
  actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
  resources = [var.kms_key_arn]
}
```

```bash
# Exemple 2 : S3 sans KMS
# rôle : s3:GetObject sur raw/*, rien en KMS
aws s3 cp "s3://$RAW/bodacc/p.gz" .
# → AccessDenied : not authorized
#   to perform: kms:Decrypt
```

- Quiz : `UseProjectKey` vise `arn:aws:kms:eu-west-3:<id>:alias/data-platform-dev` : la Lambda lit-elle `raw` ?
- [ ] Oui : l'alias désigne la clé
- [x] Non : `AccessDenied` sur `kms:Decrypt`
- [ ] Oui, si la rotation est active
- [ ] Non : `validate` refuse un ARN d'alias
- Réponse : non : dans une politique IAM, un ARN d'alias ne désigne que l'alias, jamais la clé ; il faut l'ARN de la clé (ou la condition `kms:ResourceAliases`).

## 11. bucket key : SSE-KMS moins cher
- Sous-thème : s3
- Niveau : 2
- Source : data-platform · S1-04
- Définition : `bucket_key_enabled = true` : S3 dérive une clé de bucket depuis la clé KMS et appelle KMS bien moins souvent qu'une fois par objet.
- Contexte : En SSE-KMS (`aws:kms`), chaque `PutObject` demande une clé de données à KMS et chaque `GetObject` la déchiffre : sur des milliers de petits fichiers, la facture KMS (0,03 $ les 10 000 appels) et le quota d'appels montent vite. La bucket key réduit ces appels jusqu'à 99 %. CloudTrail trace alors le bucket, plus chaque objet. Les droits ne changent pas : `kms:Decrypt` et `kms:GenerateDataKey`.
- Usage : ✅ tout bucket en `aws:kms` (`raw`, `processed`) · ❌ audit KMS exigé objet par objet : sans bucket key ; SSE-S3 (`AES256`) : aucun appel KMS, sans objet.

```hcl
# Exemple 1 : aws:kms + bucket key
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = aws_s3_bucket.this
  bucket   = each.value.id
  rule {
    bucket_key_enabled = true
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
  }
}
```

```bash
# Exemple 2 : vérifier sur AWS
R='ServerSideEncryptionConfiguration.Rules[0]'
aws s3api get-bucket-encryption \
  --bucket "$RAW" --query "$R.BucketKeyEnabled"
# → true
aws s3api get-bucket-encryption --bucket "$RAW" \
  --query "$R.ApplyServerSideEncryptionByDefault.SSEAlgorithm"
# → "aws:kms"
```

- Quiz : `bucket_key_enabled = true` écrit dans `apply_server_side_encryption_by_default` : résultat ?
- [ ] Accepté, même effet
- [ ] Accepté, mais ignoré par AWS
- [x] `validate` : `Unsupported argument`
- [ ] `apply` refusé par AWS
- Réponse : `Unsupported argument` (mesuré, provider 6) : l'argument appartient au bloc `rule`, frère de `apply_server_side_encryption_by_default`.

## 12. multipart SSE-KMS : Decrypt pour écrire
- Sous-thème : s3
- Niveau : 2
- Définition : Un upload multipart vers un bucket SSE-KMS exige `kms:Decrypt` en plus de `kms:GenerateDataKey`, alors que l'appel ne fait qu'écrire.
- Contexte : S3 génère une clé de données au début de l'upload, puis doit la déchiffrer pour chaque part et pour assembler l'objet. Un rôle qui n'a que `GenerateDataKey` réussit les petits `PutObject` et échoue sur les gros fichiers, ceux que la CLI ou boto3 découpent seuls : le bug n'apparaît qu'en production, sur une grosse journée.
- Usage : ✅ `kms:Decrypt` et `kms:GenerateDataKey` pour tout rôle qui écrit (comme `kms_actions` du module `iam`) · ❌ « écriture seule = `GenerateDataKey` seul » : faux dès le multipart.

```hcl
# Exemple 1 : les actions KMS du projet
locals {
  kms_actions = [
    "kms:Decrypt",          # multipart
    "kms:Encrypt",
    "kms:GenerateDataKey",  # PutObject
    "kms:DescribeKey",
  ]
}
```

```bash
# Exemple 2 : rôle sans kms:Decrypt
aws s3 cp petit.json "s3://$RAW/t/"
# → upload: OK   (2 Ko, un PutObject)
aws s3 cp jour.jsonl.gz "s3://$RAW/t/"
# → AccessDenied … kms:Decrypt
#   (40 Mo : CreateMultipartUpload)
```

- Quiz : Même rôle sans `kms:Decrypt`, `aws s3 cp` d'un fichier de 6 Mo : résultat ?
- [ ] `AccessDenied` : tout upload KMS l'exige
- [x] Réussi : sous 8 Mo, un seul `PutObject`
- [ ] Réussi, mais l'objet reste illisible
- [ ] `AccessDenied` dès 5 Mo
- Réponse : réussi : la CLI ne passe en multipart qu'au-delà de `multipart_threshold`, 8 Mo par défaut ; sous ce seuil, `GenerateDataKey` suffit.

## 13. kms:ViaService : la clé, seulement via S3
- Sous-thème : politique
- Niveau : 2
- Définition : La condition `kms:ViaService` n'autorise une clé que si l'appel passe par un service donné (`s3.eu-west-3.amazonaws.com`), jamais en appel direct.
- Contexte : Le rôle Lambda a besoin de `kms:Decrypt` pour lire `raw`, mais rien ne l'empêche alors d'appeler `kms decrypt` lui-même sur n'importe quel blob de la clé. Avec `ViaService`, la clé ne sert qu'aux lectures et écritures S3. C'est le verrou de la clé `aws/s3`, avec `kms:CallerAccount`. Le nom du service inclut la région.
- Usage : ✅ rôles qui n'utilisent la clé qu'à travers S3 (Lambda, EMR) · ❌ `ViaService` sur un rôle qui chiffre lui-même (enveloppe côté client) : ses appels directs échouent.

```hcl
# Exemple 1 : Decrypt, mais via S3
statement {
  sid       = "KeyViaS3Only"
  actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
  resources = [var.kms_key_arn]
  condition {
    test     = "StringEquals"
    variable = "kms:ViaService"
    values   = ["s3.eu-west-3.amazonaws.com"]
  }
}
```

- Quiz : On écrit `values = ["s3.amazonaws.com"]`, sans région : la Lambda de Paris lit-elle `raw` ?
- [ ] Oui : S3 est un service global
- [ ] Oui, si la bucket key est active
- [ ] `validate` refuse la valeur
- [x] Non : `AccessDenied` sur `kms:Decrypt`
- Réponse : non : S3 appelle KMS sous le nom `s3.eu-west-3.amazonaws.com` ; la valeur sans région ne correspond jamais, la condition est fausse.

## 14. politique de clé : déléguer à IAM
- Sous-thème : politique
- Niveau : 3
- Source : data-platform · S1-04
- Définition : Sans `policy`, une clé KMS reçoit la politique par défaut : `kms:*` au compte (`root`), ce qui délègue l'accès aux politiques IAM du compte.
- Contexte : Pour KMS, la politique de clé fait autorité : un rôle n'utilise une clé que si elle le permet, directement ou en déléguant à IAM par le principal `arn:aws:iam::<id>:root`. Avec la politique par défaut, `kms:Decrypt` dans la politique du rôle suffit. Une politique écrite à la main sans cette clause coupe ce relais : seuls les principaux listés passent, et l'admin peut perdre la main sur la clé.
- Usage : ✅ politique par défaut tant que tous les consommateurs sont dans le compte · ❌ politique custom sans la clause `root` ; un autre compte ou un service (CloudFront) : politique custom qui garde `root`.

```bash
# Exemple 1 : la politique par défaut
aws kms get-key-policy --key-id "$K" \
  --query Policy --output text
# → "Sid": "Enable IAM User Permissions"
#   "Principal": {"AWS":
#     "arn:aws:iam::<id>:root"}
#   "Action": "kms:*"
#   "Resource": "*"   (= cette clé)
```

```hcl
# Exemple 2 : un droit IAM suffit alors
data "aws_iam_policy_document" "lambda" {
  statement {
    sid       = "UseProjectKey"
    actions   = ["kms:Decrypt"]
    resources = [var.kms_key_arn]
  }
}
```

- Quiz : Une `policy` custom n'accorde `kms:*` qu'au rôle Lambda : que répond KMS à la création de la clé ?
- [ ] Accepté : seule la Lambda utilise la clé
- [x] Refusé : l'appelant ne pourrait plus la gérer
- [ ] Accepté : l'admin garde la main par IAM
- [ ] Refusé : il faut au moins deux principaux
- Réponse : refusé (`MalformedPolicyDocumentException`) : le contrôle anti-verrouillage rejette une politique qui empêche l'appelant de la modifier ensuite ; `bypass_policy_lockout_safety_check` le contourne, à ne jamais faire.

## 15. clé KMS : partager avec un autre compte
- Sous-thème : politique
- Niveau : 3
- Définition : Un autre compte n'utilise une clé client que si la politique de clé l'autorise et si ce compte accorde lui-même l'action à son rôle.
- Contexte : Même règle que toute politique de ressource entre comptes : les deux côtés. La politique de clé nomme le compte (`arn:aws:iam::<autre>:root`) ; le compte étranger ajoute `kms:Decrypt` sur l'ARN complet de la clé, un alias ne se résolvant pas d'un compte à l'autre. La politique de bucket ne donne aucun droit sur la clé : il faut les deux.
- Usage : ✅ partenaire qui lit des exports `out/` chiffrés, compte d'analytique séparé · ❌ ouvrir la clé à `Principal: "*"` sans condition : tout compte AWS pourrait s'en servir avec un simple droit IAM.

```hcl
# Exemple 1 : statement de la politique de clé
statement {
  sid     = "PartnerDecrypt"
  actions = ["kms:Decrypt", "kms:DescribeKey"]
  principals {
    type        = "AWS"
    identifiers = ["arn:aws:iam::111122223333:root"]
  }
  resources = ["*"]   # = cette clé
}
```

- Quiz : `out` est chiffré avec `aws/s3` ; la politique de bucket ouvre `GetObject` au partenaire : lit-il ?
- [ ] Oui : la politique de bucket suffit
- [x] Non : `aws/s3` refuse tout autre compte
- [ ] Oui, s'il a `kms:Decrypt` côté IAM
- [ ] Non : SSE-KMS interdit tout accès externe
- Réponse : non : la politique de `aws/s3` exige `kms:CallerAccount` = ce compte et ne se modifie pas ; partager des objets SSE-KMS demande une clé client.

## 16. grant : un droit délégué
- Sous-thème : politique
- Niveau : 3
- Définition : Un grant autorise un principal à utiliser une clé pour des opérations précises (`Decrypt`), sans toucher à la politique de clé.
- Contexte : Les services AWS en créent pour agir au nom de l'appelant : un volume EBS chiffré, RDS ou les variables d'environnement d'une Lambda posent un grant sur la clé. Un grant ne permet que des opérations cryptographiques, jamais d'administrer la clé, et ne connaît pas de `Deny`. Il se retire par `retire-grant` ou `revoke-grant`, et peut mettre quelques secondes à se propager.
- Usage : ✅ accès temporaire et programmatique (un job EMR le temps d'un traitement), délégation à un service · ❌ accès permanent d'un rôle connu : politique IAM ou de clé, lisibles dans le code.

```hcl
# Exemple 1 : le job EMR du 23 octobre
resource "aws_kms_grant" "emr" {
  name              = "emr-job-2026-10-23"
  key_id            = aws_kms_key.this.key_id
  grantee_principal = aws_iam_role.emr.arn
  operations        = ["Decrypt", "GenerateDataKey"]
}
```

```bash
# Exemple 2 : lister les grants
aws kms list-grants --key-id "$K" \
  --query 'Grants[].[Name,Operations]'
# → []  (aucun aujourd'hui, mesuré)
```

- Quiz : `operations = ["kms:Decrypt"]` dans `aws_kms_grant` : que se passe-t-il ?
- [ ] Accepté, même effet
- [ ] Accepté : AWS retire le préfixe
- [x] `validate` échoue : `Decrypt`, sans préfixe
- [ ] `apply` refusé par AWS
- Réponse : `validate` échoue (`expected operations to be one of ["Decrypt" "Encrypt" …], got kms:Decrypt`, mesuré) : un grant liste des opérations, pas des actions IAM.

## 17. contexte de chiffrement : la donnée liée
- Sous-thème : chiffrement
- Niveau : 3
- Définition : Le contexte de chiffrement est un jeu de paires clé-valeur non secrètes lié au texte chiffré : `Decrypt` échoue s'il ne reçoit pas le même.
- Contexte : Il sert de donnée authentifiée additionnelle (AAD) : un blob déplacé d'un usage à un autre devient indéchiffrable. Il apparaît en clair dans CloudTrail, d'où l'audit et les conditions de politique (`kms:EncryptionContext:…`). S3 en SSE-KMS l'utilise : `aws:s3:arn` vaut l'ARN de l'objet, ou du bucket avec une bucket key. Jamais de donnée sensible dedans.
- Usage : ✅ contexte qui nomme l'usage (`projet`, `table`) en chiffrement direct ou d'enveloppe · ❌ y mettre un nom de dirigeant ou un secret : il est journalisé en clair.

```bash
# Exemple 1 : chiffrer avec un contexte
aws kms encrypt --key-id "$K" \
  --plaintext fileb://jeton.txt \
  --encryption-context projet=dp \
  --query CiphertextBlob --output text \
  | base64 -d > jeton.enc
aws kms decrypt \
  --ciphertext-blob fileb://jeton.enc
# → InvalidCiphertextException
#   (contexte absent au déchiffrement)
```

```python
# Exemple 2 : l'idée, simulée par HMAC
import hmac, json
from hashlib import sha256

CLE = b"materiel-dans-kms"

def tag(data, ctx):
    aad = json.dumps(ctx, sort_keys=True)
    return hmac.new(CLE, data + aad.encode(),
                    sha256).hexdigest()

t = tag(b"blob", {"projet": "dp"})
t == tag(b"blob", {"projet": "dp"})  # → True
t == tag(b"blob", {"projet": "rp"})  # → False
```

- Quiz : Contexte `projet=dp,env=dev` au chiffrement, `env=dev,projet=dp` au déchiffrement : résultat ?
- [x] Déchiffré : l'ordre des paires ne compte pas
- [ ] `InvalidCiphertextException` : ordre différent
- [ ] Déchiffré seulement avec `--key-id`
- [ ] `IncorrectKeyException`
- Réponse : déchiffré (selon la doc) : le contexte est un ensemble de paires, comparé sans ordre ; clés et valeurs restent sensibles à la casse.

## 18. clé multi-région : même clé, deux régions
- Sous-thème : clés
- Niveau : 3
- Définition : Une clé multi-région a des répliques dans d'autres régions, même id `mrk-…`, même matériel : un blob chiffré à Paris se déchiffre à Dublin.
- Contexte : Une clé normale ne quitte jamais sa région : un blob chiffré à Paris est indéchiffrable ailleurs, même si l'on copie les données. La réplique (`aws_kms_replica_key`) partage le matériel et la rotation, mais a sa propre politique, ses alias et ses grants. Chaque réplique est facturée comme une clé, 1 $/mois.
- Usage : ✅ données chiffrées côté client et répliquées entre régions, reprise après sinistre · ❌ « au cas où » : la réplication S3 rechiffre déjà avec une clé de la région de destination.

```hcl
# Exemple 1 : primaire Paris, réplique Dublin
resource "aws_kms_key" "mr" {
  description  = "dp-dev-mr"
  multi_region = true
}
resource "aws_kms_replica_key" "dublin" {
  provider        = aws.dublin
  primary_key_arn = aws_kms_key.mr.arn
}
# key_id des deux : mrk-…
```

- Quiz : On ajoute `multi_region = true` à la clé existante du projet : que montre `terraform plan` ?
- [ ] `~` mise à jour sur place
- [x] `-/+` : remplacement par une nouvelle clé
- [ ] Erreur : attribut en lecture seule
- [ ] Aucun changement
- Réponse : remplacement (`-/+`, selon la doc) : une clé régionale ne devient jamais multi-région ; nouvelle clé, nouvel ARN, et l'ancienne passe en `PendingDeletion`.

## 19. quotas KMS : ThrottlingException
- Sous-thème : chiffrement
- Niveau : 3
- Définition : KMS limite les opérations cryptographiques par compte et par région (10 000 par seconde à Paris pour les clés symétriques) ; au-delà, `ThrottlingException`.
- Contexte : Le quota est commun à toutes les clés symétriques du compte : `Decrypt`, `GenerateDataKey`, `Encrypt`, y compris ceux que S3 fait pour chaque objet en SSE-KMS. Un job Spark qui lit 100 000 petits fichiers `raw` d'un coup, sans bucket key, peut le saturer et faire échouer d'autres applications. Les SDK réessaient avec backoff ; le quota se relève par Service Quotas.
- Usage : ✅ bucket key, cache des clés de données (Encryption SDK), retries avec backoff · ❌ un appel KMS par enregistrement : une clé de données par fichier ou par lot.

```bash
# Exemple 1 : le quota du compte
aws service-quotas \
  list-aws-default-service-quotas \
  --service-code kms --query \
  "Quotas[?contains(QuotaName,
  'Cryptographic operations (symmetric)')]
  .Value"
# → [10000.0]   (mesuré, eu-west-3)
```

- Quiz : Deux Lambdas à 6 000 `Decrypt`/s chacune, sur deux clés différentes du compte : que se passe-t-il ?
- [ ] Rien : 6 000 < 10 000 par clé
- [x] Throttling : 12 000/s sur un quota commun
- [ ] Throttling sur une seule des deux clés
- [ ] KMS met les appels en file d'attente
- Réponse : throttling : le quota vaut pour le compte et la région, toutes clés symétriques confondues ; 12 000/s dépasse 10 000.
