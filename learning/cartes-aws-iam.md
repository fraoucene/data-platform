---
title: "Cartes · IAM"
type: cartes
langage: AWS
cours: IAM
created: 2026-10-24
updated: 2026-10-25
---

# Cartes · IAM
AWS · IAM : rôles, politiques, évaluation, moindre privilège (format spec v3 de revision-pwa).

## 1. identités IAM : utilisateur ou rôle
- Sous-thème : rôles
- Niveau : 1
- Définition : Un utilisateur IAM a des identifiants permanents (mot de passe, clés d'accès) ; un rôle n'en a aucun et s'endosse pour obtenir des identifiants temporaires.
- Contexte : Le compte a aussi son root (l'e-mail d'inscription), tout-puissant : MFA, et jamais au quotidien. Un groupe n'est qu'un moyen d'attacher des politiques à plusieurs utilisateurs. Les clés d'un utilisateur commencent par `AKIA` et vivent jusqu'à leur rotation manuelle ; celles d'un rôle commencent par `ASIA`, viennent avec un jeton de session et expirent seules.
- Usage : ✅ rôle pour tout ce qui tourne (Lambda, CodeBuild, CI), utilisateur pour un humain faute de SSO · ❌ utilisateur « technique » avec des clés pour une appli ou une CI.

```bash
# Exemple 1 : qui suis-je ?
aws sts get-caller-identity \
  --query Arn --output text
# → arn:aws:iam::<id>:user/fraoucene-data
#   (utilisateur : clés AKIA… du profil)
```

- Quiz : Peut-on nommer un groupe IAM comme `Principal` d'une trust policy ou d'une politique de bucket ?
- [ ] Oui : tous ses membres sont autorisés
- [ ] Oui, avec son ARN `:group/…`
- [x] Non : un groupe n'est pas un principal
- [ ] Non, sauf dans le même compte
- Réponse : non : un groupe ne s'authentifie jamais, il ne fait que porter des politiques ; on nomme un utilisateur, un rôle, un compte ou un service.

## 2. rôle IAM : confiance et permissions
- Sous-thème : rôles
- Niveau : 1
- Définition : Un rôle IAM porte deux politiques distinctes : la trust policy dit qui peut l'endosser, la politique de permissions dit ce qu'il peut faire.
- Contexte : La trust policy (`assume_role_policy`) n'accorde que `sts:AssumeRole` à un principal, ici le service CodeBuild ; elle ne donne aucun droit sur S3 ou CloudFront. Les droits arrivent par une politique attachée au rôle. Confondre les deux est l'erreur classique : un droit placé dans la trust policy n'autorise rien.
- Usage : ✅ un rôle par service qui appelle AWS (CodeBuild, EventBridge, Lambda) · ❌ un rôle partagé entre services : sa trust policy s'élargit et ses droits s'additionnent.

```hcl
# Exemple 1 : qui peut endosser le rôle
data "aws_iam_policy_document" "codebuild_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      identifiers = ["codebuild.amazonaws.com"]
      type        = "Service"
    }
  }
}
```

```hcl
# Exemple 2 : le rôle relie la confiance
resource "aws_iam_role" "deploy" {
  name = "${local.prefix}-deploy"
  assume_role_policy = (
    data.aws_iam_policy_document
    .codebuild_assume.json
  )
}
# droits : aws_iam_role_policy à part
```

- Quiz : On ajoute `s3:PutObject` dans `codebuild_assume` au lieu de `deploy` : le build peut-il écrire dans S3 ?
- [x] Non : la trust policy n'accorde aucun droit d'action
- [ ] Oui : les deux politiques s'additionnent
- [ ] Oui, mais seulement sur le bucket du projet
- [ ] Non : il faut aussi `s3:ListBucket`
- Réponse : non : la trust policy dit seulement qui endosse le rôle ; les actions autorisées viennent de la politique de permissions attachée.

## 3. rôle de service : aucune clé dans la CI
- Sous-thème : rôles
- Niveau : 1
- Définition : CodeBuild s'exécute avec un rôle IAM de service : la CLI du build reçoit des identifiants temporaires, aucune clé d'accès n'est stockée.
- Contexte : Le conteneur obtient les identifiants du rôle par un endpoint local, renouvelés automatiquement ; la CLI et les SDK les trouvent seuls, comme sur une Lambda. Pas de `AWS_ACCESS_KEY_ID` en variable de CI à faire tourner ou à fuiter. Le piège : tout `--profile` passé à la CLI cherche un fichier `~/.aws/config` absent du conteneur et échoue.
- Usage : ✅ tout build qui appelle AWS (S3, CloudFront, Terraform) · ❌ clés IAM en variables de build : jamais, même en `SECRETS_MANAGER`.

```hcl
# Exemple 1 : le projet porte un rôle
resource "aws_codebuild_project" "deploy" {
  name         = "${local.prefix}-deploy"
  service_role = aws_iam_role.deploy.arn
  # identifiants temporaires (STS)
}
```

```bash
# Exemple 2 : dans le build
aws sts get-caller-identity \
  --query Arn --output text
# → arn:aws:sts::…:assumed-role/
#   revision-pwa-dev-deploy/…
```

- Quiz : Pourquoi le buildspec lance-t-il `make deploy PROFILE=` (vide) et non `make deploy` ?
- [ ] `PROFILE` vide active le mode `--dry-run`
- [x] Le profil `data-platform` n'existe pas dans le conteneur
- [ ] Pour déployer dans tous les comptes du profil
- [ ] Pour forcer la région par défaut
- Réponse : le profil n'existe pas dans le conteneur : le Makefile ajoute `--profile data-platform` par défaut ; vide, la CLI prend le rôle de service.

## 4. statement : Effect, Action, Resource
- Sous-thème : politiques
- Niveau : 1
- Définition : Un statement IAM combine `Effect` (`Allow` ou `Deny`), `Action` (`s3:GetObject`), `Resource` (un ARN) et une `Condition` facultative.
- Contexte : Une action s'écrit `service:Opération` ; une ressource par son ARN (`arn:aws:s3:::bucket/clé`, sans région ni compte pour S3). Une politique d'identité n'a pas de `Principal` : c'est l'identité qui la porte ; une politique de ressource en a toujours un. `"Version": "2012-10-17"` n'est pas une date à tenir à jour : c'est la version du langage, nécessaire aux variables `${aws:…}`.
- Usage : ✅ un statement par intention, nommé par `sid` · ❌ `Allow` avec `NotAction` pour « tout sauf » : il accorde aussi IAM, KMS et tout service à venir.

```json
# Exemple 1 : le JSON du rôle Lambda
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadRaw",
    "Effect": "Allow",
    "Action": "s3:GetObject",
    "Resource":
      "arn:aws:s3:::data-platform-dev-raw-<id>/*"
  }]
}
```

```bash
# Exemple 2 : Allow + NotAction, simulé
# Allow, NotAction s3:DeleteObject, Resource *
# → s3:DeleteObject          implicitDeny
#   iam:CreateUser           allowed
#   kms:ScheduleKeyDeletion  allowed
```

- Quiz : Une politique d'identité contient un statement sans `Resource` : qu'en dit IAM ?
- [ ] Acceptée : `*` par défaut
- [ ] Acceptée : ressources du compte seulement
- [x] Refusée : `Resource` est obligatoire
- [ ] Acceptée, statement ignoré
- Réponse : refusée (Access Analyzer : `ERROR MISSING_RESOURCE`, mesuré) : hors trust policy, chaque statement doit porter `Resource` ou `NotResource`.

## 5. évaluation : le Deny explicite gagne
- Sous-thème : évaluation
- Niveau : 1
- Définition : IAM refuse par défaut ; un `Allow` ouvre l'accès, un `Deny` explicite le ferme, quel que soit le nombre d'`Allow` ailleurs.
- Contexte : Pour chaque requête, IAM rassemble toutes les politiques applicables (identité, ressource, boundary, SCP, session), sans ordre : la place des statements ne compte pas. Un seul `Deny` qui correspond donne un refus. Sinon, au moins un `Allow` donne l'accès ; aucun, un refus implicite. Contrairement à un pare-feu, pas de « première règle qui gagne ».
- Usage : ✅ `Deny` ciblé en garde-fou (`s3:DeleteObject` sur `raw`) au-dessus d'`Allow` larges · ❌ « rouvrir » par un `Allow` plus précis : rien ne lève un `Deny` qui correspond.

```python
# Exemple 1 : l'algorithme, simplifié
def decide(statements, action):
    effets = {s["Effect"] for s in statements
              if action in s["Action"]}
    if "Deny" in effets:
        return "explicitDeny"
    if "Allow" in effets:
        return "allowed"
    return "implicitDeny"

pol = [{"Effect": "Allow",
        "Action": ["s3:GetObject",
                   "s3:DeleteObject"]},
       {"Effect": "Deny",
        "Action": ["s3:DeleteObject"]}]
decide(pol, "s3:GetObject")  # → "allowed"
decide(pol, "s3:DeleteObject")
# → "explicitDeny"
decide(pol, "s3:PutObject")  # → "implicitDeny"
```

- Quiz : Le `Deny` sur `s3:*` a pour condition `aws:SecureTransport = false` ; requête en HTTPS : décision ?
- [ ] `explicitDeny`
- [x] `allowed`, grâce à l'`Allow`
- [ ] `implicitDeny`
- [ ] Erreur : condition inconnue
- Réponse : `allowed` (mesuré au simulateur) : la condition est fausse, le `Deny` ne s'applique pas ; reste l'`Allow`.

## 6. s3:PutObject : borné à un préfixe
- Sous-thème : moindre privilège
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `s3:PutObject` sur `"${arn_raw}/bodacc/*"` autorise l'écriture sous `bodacc/` seulement : le reste du bucket `raw` reste fermé à la fonction.
- Contexte : L'ARN d'un objet est `arn:aws:s3:::<bucket>/<clé>` ; le joker `*` couvre toute la suite de la clé, `/` compris (`bodacc/date=2026-10-20/part-0001.jsonl.gz`). Une Lambda par source, un préfixe par source : un bug dans l'ingestion BODACC ne peut pas écraser les données INSEE du même bucket. Le préfixe se construit depuis l'output du module (`module.s3.bucket_arns["raw"]`), jamais en dur.
- Usage : ✅ un préfixe par producteur dans un bucket partagé · ❌ `"${arn_raw}/*"` par facilité : toute la zone brute devient inscriptible.

```hcl
# Exemple 1 : écrire sous bodacc/ seul
data "aws_iam_policy_document" "ingest_bodacc" {
  statement {
    sid     = "WriteBodaccPartitions"
    actions = ["s3:PutObject"]
    resources = [
      "${module.s3.bucket_arns["raw"]}/bodacc/*",
    ]
  }
}
# PutObject raw/bodacc/date=…/x.gz → allowed
# PutObject raw/insee/x.gz         → implicitDeny
```

- Quiz : Avec cette politique, `PutObject` de la clé `bodacc` (sans `/` ni suite) : décision ?
- [ ] `allowed` : `*` accepte une suite vide
- [x] `implicitDeny` : le `/` manque
- [ ] `allowed` : même préfixe
- [ ] `explicitDeny`
- Réponse : `implicitDeny` : le motif exige `bodacc/` puis n'importe quoi ; la clé `bodacc` ne contient pas le `/`, donc ne correspond pas.

## 7. s3:PutObject : écrire, c'est aussi écraser
- Sous-thème : politiques
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `s3:PutObject` autorise la création comme le remplacement d'un objet : IAM n'a pas de droit séparé pour « écrire sans écraser ».
- Contexte : Pour S3, réécrire une clé est un `PutObject` comme un autre. L'ingestion en a besoin : rejouer une journée réécrit la même partition, c'est ce qui la rend idempotente. Pour interdire l'écrasement, il faut d'autres outils : versioning (l'ancienne version reste), Object Lock, ou écriture conditionnelle (`If-None-Match`). `s3:DeleteObject` est un droit à part, absent ici.
- Usage : ✅ `PutObject` seul pour un producteur qui réécrit ses partitions · ❌ croire qu'un rôle sans `DeleteObject` ne peut rien détruire : il peut écraser par un objet vide.

```bash
# Exemple 1 : remplacer, pas supprimer
aws s3api put-object --bucket "$RAW" \
  --key bodacc/date=2026-10-20/part-0001.jsonl.gz
# → allowed : objet remplacé par 0 octet
aws s3 rm \
  "s3://$RAW/bodacc/date=2026-10-20/part-0001.jsonl.gz"
# → AccessDenied : pas de DeleteObject
```

- Quiz : Bucket `raw` versionné, rôle avec `PutObject` seul : un objet écrasé par erreur est-il perdu ?
- [ ] Oui : l'écrasement remplace l'objet
- [x] Non : l'ancienne version reste
- [ ] Non : S3 refuse d'écraser
- [ ] Oui, sauf avec `DeleteObject`
- Réponse : non : avec le versioning, `PutObject` crée une nouvelle version et garde l'ancienne ; la récupérer demande `GetObjectVersion`, que ce rôle n'a pas.

## 8. sid : unique dans la politique
- Sous-thème : politiques
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `sid` nomme un statement (`WriteBodaccPartitions`, `UseProjectKey`) : facultatif, mais unique dans une politique, il dit à quoi sert chaque droit.
- Contexte : IAM ignore le `sid` pour décider ; il sert aux humains (revue de MR, Access Analyzer, `simulate-principal-policy` qui cite le statement décisif). Lettres et chiffres seulement, sans espace ni tiret. Avec `aws_iam_policy_document`, un `sid` répété fait échouer la lecture du data source, et `override_policy_documents` s'en sert pour remplacer un statement du même nom.
- Usage : ✅ un `sid` par statement, qui dit l'intention (`WriteOwnLogs`) · ❌ des `sid` génériques (`Stmt1`) : la revue ne sait plus pourquoi le droit existe.

```hcl
# Exemple 1 : l'intention dans le nom
statement {
  sid       = "WriteBodaccPartitions"
  actions   = ["s3:PutObject"]
  resources = ["${local.raw_arn}/bodacc/*"]
}
statement {
  sid       = "UseProjectKey"
  actions   = ["kms:GenerateDataKey"]
  resources = [local.key_arn]
}
```

- Quiz : Deux statements du même `aws_iam_policy_document` ont `sid = "UseProjectKey"` : que se passe-t-il ?
- [ ] Le second remplace le premier
- [ ] Les deux sont fusionnés
- [x] Erreur : `duplicate Sid`
- [ ] Rien : IAM ignore le `sid`
- Réponse : erreur `duplicate Sid (UseProjectKey)` à la lecture du data source (message du provider AWS 6.69) ; le remplacement par `sid` n'existe qu'entre documents, via `override_policy_documents`.

## 9. IAM Identity Center : un humain sans clé permanente
- Sous-thème : rôles
- Niveau : 1
- Source : data-platform · S1-09
- Définition : IAM Identity Center (ex-AWS SSO) connecte un humain à un compte par un rôle temporaire, issu d'un permission set, au lieu de clés d'accès permanentes.
- Contexte : Sur un compte neuf, il n'existe que le root. On active Identity Center, on crée un utilisateur, on lui attribue le compte avec un permission set (`AdministratorAccess` pour un compte perso de dev, plus étroit en entreprise) : AWS crée le rôle correspondant dans le compte. Les identifiants obtenus commencent par `ASIA` et expirent seuls ; une clé `AKIA` d'utilisateur IAM vit jusqu'à sa rotation manuelle.
- Usage : ✅ tout accès humain à la CLI ou à la console, un ou plusieurs comptes · ❌ travailler en root, ou créer un utilisateur IAM avec des clés pour soi : clés permanentes sur le disque.

```bash
# Exemple 1 : quel type d'identifiants ?
aws configure list --profile data-platform
# → access_key ****DXH2
#   shared-credentials-file
#   (clés permanentes d'utilisateur IAM)
# avec un profil SSO : TYPE sso
```

- Quiz : Avec des identifiants Identity Center, par quoi commence l'`AccessKeyId` renvoyé ?
- [ ] `AKIA`
- [x] `ASIA`
- [ ] `AROA`
- [ ] `SSO-`
- Réponse : `ASIA` : ce sont des identifiants temporaires de rôle, avec un jeton de session ; `AKIA` est une clé permanente d'utilisateur, `AROA` l'identifiant unique d'un rôle.

## 10. aws_iam_policy_document : écrire du JSON en HCL
- Sous-thème : politiques
- Niveau : 2
- Définition : `aws_iam_policy_document` écrit une politique IAM en HCL et produit son JSON via `.json`, avec références et validation à la place d'un heredoc.
- Contexte : C'est un data source calculé localement, sans appel AWS : Terraform assemble le JSON à partir des blocs `statement`. Les ARN viennent de références (`aws_s3_bucket.this["site"].arn`), donc le graphe de dépendances est juste et aucune chaîne n'est recopiée à la main. Chaque `sid` nomme un statement, utile pour lire la politique dans la console.
- Usage : ✅ toute politique IAM, trust policy ou politique de bucket · ❌ `jsonencode` ou heredoc JSON pour une politique : pas de validation des champs, faute de frappe silencieuse.

```hcl
# Exemple 1 : un statement nommé
data "aws_iam_policy_document" "deploy" {
  statement {
    sid     = "ListSite"
    actions = ["s3:ListBucket"]
    resources = [
      aws_s3_bucket.this["site"].arn
    ]
  }
}
# .json → {"Version":"2012-10-17",
#   "Statement":[{"Sid":"ListSite",…}]}
```

- Quiz : Un `statement` écrit sans `effect` : la politique produite autorise ou interdit ?
- [ ] Interdit : `Deny` par défaut
- [ ] Erreur : `effect` est obligatoire
- [x] Autorise : `Allow` par défaut
- [ ] Ni l'un ni l'autre : le statement est ignoré
- Réponse : autorise : `effect` vaut `Allow` par défaut ; mesuré, la trust policy du rôle `deploy` sort en `"Effect": "Allow"` sans l'avoir écrit.

## 11. aws_iam_role_policy : politique inline
- Sous-thème : politiques
- Niveau : 2
- Définition : `aws_iam_role_policy` attache une politique inline à un seul rôle : elle vit et meurt avec lui, adaptée à des droits sur mesure.
- Contexte : Une politique inline n'a pas d'ARN propre : elle n'existe que dans le rôle, et supprimer le rôle la supprime. Une politique managée (`aws_iam_policy`) est un objet indépendant, versionné, attachable à plusieurs rôles par `aws_iam_role_policy_attachment`. Ici chaque rôle a des droits propres à son projet : l'inline évite un objet de plus.
- Usage : ✅ droits propres à un seul rôle (ce build, ce bucket) · ❌ mêmes droits pour plusieurs rôles : politique managée attachée à chacun.

```hcl
# Exemple 1 : attachée au rôle deploy
resource "aws_iam_role_policy" "deploy" {
  name = "deploy"
  role = aws_iam_role.deploy.id
  policy = (
    data.aws_iam_policy_document.deploy.json
  )
}
# rôle revision-pwa-dev-deploy
#  └ inline « deploy »
```

- Quiz : Trois rôles ont besoin exactement des mêmes droits : inline ou managée ?
- [ ] Inline : une copie par rôle, plus sûr
- [x] Managée : un objet, attaché trois fois
- [ ] Inline : une managée ne s'attache qu'à un rôle
- [ ] Peu importe : IAM fusionne les doublons
- Réponse : managée : une seule politique modifiée à un seul endroit ; en inline, chaque changement se recopie dans les trois rôles.

## 12. s3:ListBucket : sur le bucket, pas /*
- Sous-thème : politiques
- Niveau : 2
- Définition : `s3:ListBucket` s'applique à l'ARN du bucket, `PutObject` et `DeleteObject` à ses objets (`arn/*`) : deux statements, deux ressources.
- Contexte : Dans IAM, chaque action S3 porte sur un type de ressource : le bucket (`arn:aws:s3:::nom`) ou l'objet (`arn:aws:s3:::nom/clé`). Une action associée au mauvais type ne matche jamais, sans erreur à l'`apply` : la politique est acceptée, l'appel est refusé à l'exécution. `s3 sync` liste toujours la destination pour comparer.
- Usage : ✅ un statement par type de ressource, `sid` explicite (`ListSite`, `WriteSite`) · ❌ `resources = ["*"]` pour « faire marcher » : droits sur tous les buckets du compte.

```hcl
# Exemple 1 : objets du bucket
statement {
  sid = "WriteSite"
  actions = ["s3:PutObject",
  "s3:DeleteObject"]
  resources = [
    "${aws_s3_bucket.this["site"].arn}/*"
  ]
}
```

```hcl
# Exemple 2 : le bucket lui-même
statement {
  sid     = "ListSite"
  actions = ["s3:ListBucket"]
  resources = [
    aws_s3_bucket.this["site"].arn
  ]
}
```

- Quiz : On met `s3:ListBucket` dans `WriteSite`, sur `"${arn}/*"` seul : que fait `aws s3 sync --delete` ?
- [ ] Il marche : `/*` couvre aussi le bucket
- [ ] Il envoie les fichiers mais ne supprime rien
- [x] `AccessDenied` sur `ListObjectsV2`
- [ ] `apply` refuse la politique
- Réponse : `AccessDenied` sur `ListObjectsV2` : `ListBucket` ne matche pas une ressource objet, et `sync` doit lister le bucket avant d'envoyer.

## 13. condition s3:prefix : borner le listage
- Sous-thème : politiques
- Niveau : 2
- Définition : Un bloc `Condition` teste la requête (`s3:prefix`, `aws:SourceArn`) : le statement ne s'applique que si le test est vrai.
- Contexte : `s3:ListBucket` porte sur le bucket entier ; pour ne laisser lister qu'un préfixe, on teste `s3:prefix`, le paramètre `Prefix` de la requête. Plusieurs valeurs d'une même clé valent OU ; plusieurs clés ou opérateurs valent ET. `StringLike` accepte `*` et `?`, `StringEquals` compare à l'identique. Une clé absente de la requête rend le test faux.
- Usage : ✅ rôle de publication qui ne liste que `sources/<projet>/` · ❌ borner `ListBucket` par l'ARN `bucket/sources/*` : ce n'est pas une ressource de `ListBucket`, aucun accès.

```hcl
# Exemple 1 : lister son seul préfixe
statement {
  sid       = "ListOwnPrefix"
  actions   = ["s3:ListBucket"]
  resources = [aws_s3_bucket.this["content"].arn]
  condition {
    test     = "StringLike"
    variable = "s3:prefix"
    values   = ["sources/data-platform/*"]
  }
}
```

```bash
# Exemple 2 : simulé, selon le Prefix
# sources/data-platform/   → allowed
# sources/data-platform/x  → allowed
# sources/                 → implicitDeny
# (sans Prefix)            → implicitDeny
```

- Quiz : Avec ce rôle, `aws s3 ls s3://$CONTENT/sources/data-platform` (sans `/` final) : résultat ?
- [ ] Liste les cartes du projet
- [x] `AccessDenied`
- [ ] Liste vide, sans erreur
- [ ] Liste tout `sources/`
- Réponse : `AccessDenied` (mesuré : `implicitDeny`) : `sources/data-platform` ne correspond pas à `sources/data-platform/*`, il manque le `/`.

## 14. jokers : * dans les actions et les ARN
- Sous-thème : politiques
- Niveau : 2
- Définition : `*` (plusieurs caractères) et `?` (un seul) sont permis dans les actions (`s3:Get*`) et les ARN (`function:${prefix}-*`) pour viser une famille.
- Contexte : `s3:Get*` couvre `GetObject`, mais aussi `GetBucketPolicy`, `GetObjectAcl` et toute action `Get` ajoutée demain ; `ListBucket` n'en fait pas partie. Dans un ARN, `*` traverse les `/` : `raw/*` couvre toutes les sous-clés. Le rôle Step Functions invoque `function:data-platform-dev-*` : toute Lambda au préfixe du projet, y compris celles créées plus tard.
- Usage : ✅ joker sur un préfixe de nom maîtrisé (`${prefix}-*`) · ❌ `s3:Get*` pour « lire les objets » : la liste exacte (`s3:GetObject`) ; `*` en tête d'ARN.

```bash
# Exemple 1 : Allow s3:Get* sur *, simulé
# → s3:GetObject        allowed
#   s3:GetBucketPolicy  allowed
#   s3:GetObjectAcl     allowed
#   s3:ListBucket       implicitDeny
```

```hcl
# Exemple 2 : les Lambdas du projet
statement {
  sid     = "InvokeProjectLambdas"
  actions = ["lambda:InvokeFunction"]
  resources = [
    "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.prefix}-*"
  ]
}
```

- Quiz : `"Action": "S3:getobject"` sur `"…raw-<id>/Bodacc/*"` ; `GetObject` de `raw-<id>/bodacc/x` : décision ?
- [ ] `allowed` : la casse est ignorée partout
- [x] `implicitDeny` : l'ARN distingue la casse
- [ ] `implicitDeny` : `S3:getobject` est invalide
- [ ] `explicitDeny`
- Réponse : `implicitDeny` (mesuré) : le nom d'action ignore la casse (`S3:getobject` marche sur `Bodacc/x`), pas l'ARN : `Bodacc` ≠ `bodacc`.

## 15. politique de ressource : l'autre côté
- Sous-thème : évaluation
- Niveau : 2
- Définition : Une politique basée sur la ressource (bucket, clé KMS, file SQS) est attachée à la ressource, nomme ses `Principal` et s'ajoute aux politiques d'identité.
- Contexte : Entre deux comptes, il faut l'accord des deux côtés : la ressource autorise le compte étranger, et ce compte accorde l'action à son rôle. Elle sert aussi aux services AWS (CloudFront, logging S3), qui n'ont pas de politique IAM dans le compte. KMS est à part : sa politique de clé fait toujours autorité.
- Usage : ✅ ouvrir une ressource à un service ou à un autre compte · ❌ disperser les droits d'un rôle interne dans dix politiques de bucket : on ne sait plus lire ce qu'il peut faire.

```bash
# Exemple 1 : autre compte, simulé
aws iam simulate-custom-policy \
  --policy-input-list file://iam.json \
  --resource-policy file://bucket.json \
  --resource-owner arn:aws:iam::<id>:root \
  --caller-arn \
    arn:aws:iam::111122223333:user/alice \
  --action-names s3:GetObject \
  --resource-arns "$RAW_ARN/x"
# bucket Allow + IAM vide  → implicitDeny
# bucket Allow + IAM Allow → allowed
```

- Quiz : Même compte : le rôle n'a aucun droit S3, la politique de bucket lui accorde `GetObject` : décision ?
- [ ] `implicitDeny` : il faut aussi IAM
- [x] `allowed`
- [ ] `explicitDeny`
- [ ] Erreur : un rôle ne peut pas être `Principal`
- Réponse : `allowed` (mesuré) : dans un même compte, un `Allow` d'un seul côté suffit ; seul l'accès entre comptes exige les deux.

## 16. AssumeRole : identifiants temporaires
- Sous-thème : rôles
- Niveau : 2
- Définition : `sts:AssumeRole` échange l'identité de l'appelant contre des identifiants temporaires du rôle (clé `ASIA…`, secret, jeton de session), valables 1 h par défaut.
- Contexte : La trust policy du rôle `publish` nomme le compte (`root`) : elle délègue à IAM, l'appelant doit donc aussi avoir `sts:AssumeRole` dans ses politiques. La CLI fait l'échange seule depuis un profil `role_arn` + `source_profile`, et le renouvelle. Durée : jusqu'à `max_session_duration` (12 h au plus) ; un rôle endossé depuis un autre rôle (chaînage) plafonne à 1 h.
- Usage : ✅ profil CLI `role_arn` pour agir avec les droits réduits d'un rôle (`make cards-publish`) · ❌ copier `AWS_SESSION_TOKEN` depuis la console dans le shell : il expire et reste dans l'historique.

```ini
# Exemple 1 : ~/.aws/config
[profile revision-publish-data-platform]
role_arn = arn:aws:iam::<id>:role/revision-pwa-dev-publish-data-platform
source_profile = data-platform
region = eu-west-3
```

```bash
# Exemple 2 : la CLI endosse le rôle
aws sts get-caller-identity \
  --profile revision-publish-data-platform \
  --query Arn --output text
# → arn:aws:sts::<id>:assumed-role/
#   revision-pwa-dev-publish-data-platform/
#   botocore-session-…   (mesuré)
```

- Quiz : Le rôle a `max_session_duration = 3600` ; `aws sts assume-role --duration-seconds 7200` : résultat ?
- [ ] Session de 2 h
- [ ] Session ramenée à 1 h, sans erreur
- [x] `ValidationError` : au-delà du maximum du rôle
- [ ] `AccessDenied`
- Réponse : `ValidationError` (selon la doc : « DurationSeconds exceeds the MaxSessionDuration ») : STS refuse au lieu de raccourcir.

## 17. OIDC : la CI sans clé
- Sous-thème : rôles
- Niveau : 2
- Définition : Un fournisseur OIDC fait confiance aux jetons signés de GitHub : la CI appelle `sts:AssumeRoleWithWebIdentity` et reçoit des identifiants temporaires, sans clé stockée.
- Contexte : Le jeton porte des claims : `aud` (ici `sts.amazonaws.com`) et `sub`, qui nomme dépôt et ref (`repo:<org>/<dépôt>:ref:refs/heads/main`). La trust policy doit tester `sub` : sans cette condition, n'importe quel dépôt GitHub du monde peut endosser le rôle. Un seul fournisseur par URL et par compte ; le workflow demande `permissions: id-token: write`. GitLab CI fonctionne pareil, avec ses propres claims.
- Usage : ✅ toute CI hors AWS (GitHub, GitLab) qui déploie sur AWS · ❌ `sub` en `StringLike` sur `repo:<org>/*` : toutes les branches de tous les dépôts de l'organisation peuvent déployer.

```hcl
# Exemple 1 : ce dépôt, branche main
statement {
  actions = ["sts:AssumeRoleWithWebIdentity"]
  principals {
    type        = "Federated"
    identifiers = [aws_iam_openid_connect_provider.github.arn]
  }
  condition {
    test     = "StringEquals"
    variable = "token.actions.githubusercontent.com:sub"
    values = [
      "repo:fraoucene/data-platform:ref:refs/heads/main"
    ]
  }
}
```

- Quiz : Le workflow tourne sur une pull request vers `main` : le `sub` vaut-il `…:ref:refs/heads/main` ?
- [ ] Oui : la PR vise `main`
- [ ] Oui, si la PR vient du même dépôt
- [x] Non : `repo:<org>/<dépôt>:pull_request`
- [ ] Non : pas de jeton OIDC sur une PR
- Réponse : non (doc GitHub) : sur un événement `pull_request`, `sub` vaut `repo:<org>/<dépôt>:pull_request` ; la condition `main` refuse donc les PR, ce qui est voulu.

## 18. iam:PassRole : confier un rôle à un service
- Sous-thème : moindre privilège
- Niveau : 2
- Définition : Créer une Lambda, un projet CodeBuild ou un cluster EMR avec un rôle exige `iam:PassRole` sur ce rôle, en plus de l'action de création.
- Contexte : Sans ce contrôle, qui peut créer une Lambda pourrait lui attacher un rôle administrateur et agir par procuration : élévation de privilège classique. `PassRole` n'est pas une API qu'on appelle, c'est une permission que le service vérifie quand on lui passe l'ARN du rôle. La condition `iam:PassedToService` borne le service qui peut le recevoir.
- Usage : ✅ `iam:PassRole` sur l'ARN exact du rôle (`data-platform-dev-lambda`), avec `iam:PassedToService` · ❌ `iam:PassRole` sur `*` : tout rôle du compte, administrateur compris, devient utilisable.

```hcl
# Exemple 1 : créer les Lambdas du projet
statement {
  sid       = "PassLambdaRole"
  actions   = ["iam:PassRole"]
  resources = [aws_iam_role.lambda.arn]
  condition {
    test     = "StringEquals"
    variable = "iam:PassedToService"
    values   = ["lambda.amazonaws.com"]
  }
}
```

```bash
# Exemple 2 : CreateFunction seul, simulé
# → lambda:CreateFunction  allowed
#   iam:PassRole           implicitDeny
# donc create-function --role … échoue
```

- Quiz : `make up` crée la Lambda par Terraform : quel principal a besoin d'`iam:PassRole` ?
- [ ] Le rôle de la Lambda
- [x] Celui qui lance `terraform apply`
- [ ] Le service `lambda.amazonaws.com`
- [ ] Personne : Terraform crée aussi le rôle
- Réponse : celui qui lance `terraform apply` : c'est lui qui passe l'ARN du rôle à `CreateFunction` ; avoir créé le rôle ne dispense pas du droit de le confier.

## 19. moindre privilège : borner un build piraté
- Sous-thème : moindre privilège
- Niveau : 2
- Définition : Le rôle de build n'a de droits que sur ce qu'il touche : bucket `site`, invalidation, groupe de logs, `GitPull` du dépôt.
- Contexte : Un build exécute du code tiers (dépendances npm, scripts `postinstall`) avec les droits du rôle. Le moindre privilège ne l'empêche pas d'être compromis, il borne ce qu'un attaquant peut faire ensuite. Chaque statement liste des actions précises sur des ARN précis, jamais `*`. Le bucket `content` (les cartes) n'apparaît nulle part.
- Usage : ✅ partir de zéro droit et ajouter l'action exacte que l'erreur `AccessDenied` réclame · ❌ `AdministratorAccess` ou `s3:*` « le temps de tester ».

```bash
# Exemple 1 : les statements réels
aws iam get-role-policy \
  --role-name revision-pwa-dev-deploy \
  --policy-name deploy --query \
  'PolicyDocument.Statement[].Sid'
# → Source ListSite WriteSite
#   Invalidate Logs
```

- Quiz : Une dépendance npm compromise s'exécute pendant `make install` : que peut-elle faire avec ce rôle ?
- [ ] Rien : CodeBuild isole `make install`
- [ ] Lire et effacer les cartes du bucket `content`
- [ ] Créer un utilisateur IAM administrateur
- [x] Réécrire ou vider le site, pas plus
- Réponse : réécrire ou vider le site : elle a les droits du rôle, limités au bucket `site`, à l'invalidation et aux logs ; ni `content`, ni IAM.

## 20. simulate-principal-policy : tester sans appeler
- Sous-thème : politiques
- Niveau : 2
- Source : data-platform · S1-04
- Définition : `aws iam simulate-principal-policy` évalue les politiques d'un rôle pour une action et un ARN, sans rien exécuter : `allowed`, `implicitDeny` ou `explicitDeny`.
- Contexte : Une politique fausse passe l'`apply` : elle est acceptée, puis l'appel échoue à l'exécution. Le simulateur répond tout de suite. `implicitDeny` : aucun `Allow` ne couvre la demande, le défaut d'IAM ; `explicitDeny` : un `Deny` l'interdit, et aucun `Allow` ne le lève. Côté code, les deux donnent le même `AccessDenied` (HTTP 403).
- Usage : ✅ prouver le moindre privilège après `make up`, en script ou en CI · ❌ s'y fier seul : les politiques de bucket et de clé ne comptent que passées par `--resource-policy`.

```bash
# Exemple 1 : Lambda lit raw, n'écrit pas out
# → GetObject raw/x : "allowed"
#   PutObject out/x : "implicitDeny"
sim() { aws iam simulate-principal-policy \
  --policy-source-arn "$LAMBDA_ROLE" \
  --action-names "$1" --resource-arns "$2" \
  --query 'EvaluationResults[0].EvalDecision'; }
sim s3:GetObject "$RAW_ARN/x"
sim s3:PutObject "$OUT_ARN/x"
```

```bash
# Exemple 2 : un Deny explicite
# p.json : Allow s3:* + Deny s3:DeleteObject
aws iam simulate-custom-policy \
  --policy-input-list file://p.json \
  --action-names s3:DeleteObject s3:GetObject
# → s3:DeleteObject  explicitDeny
#   s3:GetObject     allowed
```

- Quiz : Même rôle Lambda, `s3:GetObject` simulé sur `$RAW_ARN` (sans `/x`) : quelle décision ?
- [ ] `allowed` : c'est bien le bucket raw
- [x] `implicitDeny`
- [ ] `explicitDeny`
- [ ] Erreur : un ARN d'objet est attendu
- Réponse : `implicitDeny` (mesuré) : `GetObject` porte sur un objet, `raw/*` ne couvre pas l'ARN du bucket ; aucun `Allow`, donc refus implicite.

## 21. DeleteObject absent : le rejeu ne nettoie pas
- Sous-thème : moindre privilège
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Sans `s3:DeleteObject`, la fonction ne peut que réécrire ses fichiers : une partie devenue inutile après un rejeu reste en place.
- Contexte : Le moindre privilège a un effet métier. Une journée écrite en deux parties, puis rejouée en une seule, laisse `part-0002` : un lecteur qui liste la partition compterait des annonces en double. D'où le manifest `_MANIFEST.json`, réécrit à chaque passage : il fait foi sur la liste des parties. Ajouter `DeleteObject` sur `bodacc/*` est possible, mais élargit ce qu'un bug peut détruire.
- Usage : ✅ un manifest qui liste les fichiers valides, lu par les consommateurs · ❌ ajouter `DeleteObject` pour faire le ménage : un bug efface des journées entières.

```bash
# Exemple 1 : rejeu en moins de parties
# 1er passage : part-0001, part-0002
# rejeu       : part-0001 seule
aws s3 ls "s3://$RAW/bodacc/date=2026-10-20/"
# → _MANIFEST.json
#   part-0001.jsonl.gz
#   part-0002.jsonl.gz   (périmée)
```

- Quiz : Un job Athena lit `bodacc/date=2026-10-20/` par un `LOCATION` sur le dossier : voit-il `part-0002` ?
- [ ] Non : le manifest l'exclut
- [x] Oui : Athena lit tout le préfixe
- [ ] Non : S3 masque les fichiers périmés
- [ ] Oui, mais en lecture seule
- Réponse : oui : Athena lit chaque objet sous le `LOCATION`, il ne connaît pas `_MANIFEST.json` ; il faut lire via le manifest ou réécrire le dossier entier.

## 22. log stream : l'ARN du groupe suivi de :*
- Sous-thème : politiques
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `logs:CreateLogStream` et `logs:PutLogEvents` portent sur les flux : la ressource est `"${aws_cloudwatch_log_group.this.arn}:*"`, pas l'ARN du groupe seul.
- Contexte : Un flux a pour ARN `arn:aws:logs:<région>:<account_id>:log-group:<nom>:log-stream:<flux>`. Le provider AWS renvoie l'ARN du groupe sans le suffixe `:*` que l'API ajoute parfois ; il faut le remettre pour couvrir ses flux. Sans lui, la politique est acceptée, et les écritures de logs sont refusées en silence à l'exécution.
- Usage : ✅ `"${arn}:*"` pour les actions sur les flux d'un groupe précis · ❌ `"*"` par commodité : la fonction peut écrire dans les logs de toutes les autres.

```hcl
# Exemple 1 : les flux d'un seul groupe
statement {
  sid     = "WriteOwnLogs"
  actions = ["logs:CreateLogStream",
             "logs:PutLogEvents"]
  resources = [
    "${aws_cloudwatch_log_group.this.arn}:*",
  ]
}
# → …:log-group:/aws/lambda/<nom>:*
```

- Quiz : On écrit `resources = [aws_cloudwatch_log_group.this.arn]`, sans `:*` : que donnent les invocations ?
- [ ] Échec : `AccessDenied` remonté au code
- [x] Réussies, mais sans aucun log
- [ ] Réussies, logs dans un groupe par défaut
- [ ] Erreur à l'`apply` de la politique
- Réponse : réussies, sans logs : l'ARN du groupe ne correspond à aucun flux, les écritures sont refusées par le runtime sans faire échouer le code.

## 23. ListBucket absent : 403 au lieu de 404
- Sous-thème : évaluation
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Sans `s3:ListBucket` sur le bucket, lire une clé absente répond `403 AccessDenied`, pas `404 NoSuchKey` : S3 ne révèle pas qu'elle n'existe pas.
- Contexte : Avec `ListBucket`, l'appelant pourrait de toute façon lister : S3 lui dit donc `404`. Sans, répondre `404` ou `403` selon l'existence ferait fuiter le contenu du bucket. Un code qui attrape `NoSuchKey` pour « pas encore écrit » reçoit alors un `ClientError` 403 et plante. L'ingestion n'a ni `GetObject` ni `ListBucket` : elle n'a rien à relire.
- Usage : ✅ ajouter `ListBucket` (borné par `s3:prefix`) au rôle qui doit tester l'existence d'une clé · ❌ traiter tout `403` comme « absent » : un vrai refus passerait inaperçu.

```python
# Exemple 1 : le code qui attend un 404
from botocore.exceptions import ClientError

def code_erreur(status):
    err = {"Error": {"Code": status}}
    return ClientError(err, "HeadObject")

e = code_erreur("403")
e.response["Error"]["Code"] == "404"  # → False
```

- Quiz : Rôle avec `GetObject` sur `raw/*` mais sans `ListBucket` : `get_object` d'une clé présente répond ?
- [x] L'objet, normalement
- [ ] `403` : `ListBucket` manque
- [ ] `404` : la clé est masquée
- [ ] `400` : requête invalide
- Réponse : l'objet : `ListBucket` ne change que la réponse pour une clé absente ; une clé présente se lit avec `GetObject` seul.

## 24. kms:Encrypt : pas pour SSE-KMS
- Sous-thème : politiques
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Écrire dans un bucket SSE-KMS exige `kms:GenerateDataKey` sur la clé, pas `kms:Encrypt` : S3 chiffre avec une clé de données, pas avec la clé KMS.
- Contexte : `kms:Encrypt` sert à chiffrer directement au plus 4 Ko par la clé KMS, appel que S3 ne fait jamais. S3 demande une clé de données (`GenerateDataKey`), chiffre l'objet localement et stocke la clé de données chiffrée avec lui. La lecture appelle `kms:Decrypt` sur cette clé de données. La ressource est l'ARN de la clé (`module.kms.key_arn`), pas son alias.
- Usage : ✅ `GenerateDataKey` pour écrire, `Decrypt` pour lire ou pour un envoi multipart · ❌ `kms:*` ou `kms:Encrypt` « au cas où » : trop large ou inutile.

```hcl
# Exemple 1 : les deux actions utiles
statement {
  sid = "UseProjectKey"
  actions = ["kms:GenerateDataKey",
             "kms:Decrypt"]
  resources = [module.kms.key_arn]
}
# PutObject petit : GenerateDataKey
# PutObject multipart : + Decrypt
```

- Quiz : Le rôle a `s3:PutObject` et `kms:Encrypt` seul sur la clé du bucket : que donne un `put_object` de 1 Ko ?
- [ ] Réussi : 1 Ko est sous la limite d'Encrypt
- [x] `AccessDenied` : `GenerateDataKey` manque
- [ ] Réussi, chiffré en SSE-S3 à la place
- [ ] `KMSInvalidStateException`
- Réponse : `AccessDenied` : S3 appelle `GenerateDataKey` quelle que soit la taille ; `Encrypt` n'est jamais utilisé par SSE-KMS.

## 25. code Lambda : lu avec les droits du déployeur
- Sous-thème : rôles
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Lambda lit le zip sur S3 avec les droits de celui qui appelle `CreateFunction` ou `UpdateFunctionCode`, jamais avec le rôle d'exécution de la fonction.
- Contexte : Le rôle d'exécution sert au code, à l'invocation ; le déploiement est fait par Terraform, avec le profil du poste ou le rôle de la CI. C'est donc ce principal qui a besoin de `s3:GetObject` sur `artifacts/lambdas/*`, et de `kms:Decrypt` si le bucket était en SSE-KMS. C'est l'autre raison du SSE-S3 sur `artifacts` : aucune clé à autoriser pour chaque déployeur.
- Usage : ✅ droits de lecture des artefacts sur le rôle de déploiement de la CI · ❌ ajouter `GetObject` sur `artifacts` au rôle de la fonction : inutile.

```hcl
# Exemple 1 : rôle de déploiement de la CI
statement {
  sid     = "ReadArtifacts"
  actions = ["s3:GetObject"]
  resources = [
    "${aws_s3_bucket.artifacts.arn}/lambdas/*",
  ]
}
# + lambda:UpdateFunctionCode, iam:PassRole
# rien de tout cela sur le rôle de la Lambda
```

- Quiz : Le déployeur n'a pas `s3:GetObject` sur le zip, le rôle de la fonction l'a : que donne l'`apply` ?
- [ ] Réussi : Lambda prend le rôle de la fonction
- [x] Échec : le déployeur ne peut pas lire le zip
- [ ] Réussi, mais la fonction n'a pas de code
- [ ] Échec au `plan`
- Réponse : échec à l'`apply` : Lambda lit l'objet au nom du principal qui appelle l'API ; le rôle d'exécution n'existe que pendant les invocations.

## 26. aws:SourceAccount : un rôle de service borné au compte
- Sous-thème : rôles
- Niveau : 2
- Source : data-platform · S1-08
- Définition : La condition `aws:SourceAccount` dans la confiance d'un rôle de service n'accepte que les appels que le service fait pour ce compte-là.
- Contexte : Le principal `scheduler.amazonaws.com` désigne le service entier, utilisé par tous les comptes AWS. La condition lie l'endossement au compte propriétaire de la ressource à l'origine de l'appel (la planification) : c'est la protection « confused deputy » que la doc de chaque service recommande. Même idée que `sts:ExternalId` pour un SaaS, mais posée par AWS, sans identifiant à transmettre.
- Usage : ✅ toute confiance vers un principal de service (`scheduler`, `budgets`, `events`) · ❌ principal de service seul, sans condition : accepté par l'API, mais plus large que nécessaire.

```hcl
# Exemple 1 : confiance de Scheduler
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}
```

- Quiz : La condition vaut `aws:SourceAccount = <ton compte>`. Ta propre planification endosse le rôle : quelle valeur porte la requête ?
- [ ] Le compte d'AWS qui opère Scheduler
- [x] Ton compte, propriétaire de la planification
- [ ] Aucune : la clé n'existe que pour S3
- [ ] Le compte du dernier utilisateur connecté
- Réponse : ton compte : `aws:SourceAccount` est le compte de la ressource qui déclenche l'appel du service, ici la planification.

## 27. ARN Lambda : `:*` pour versions et alias
- Sous-thème : politiques
- Niveau : 2
- Source : data-platform · S1-08
- Définition : `lambda:InvokeFunction` sur l'ARN nu d'une fonction ne couvre pas ses versions et alias ; il faut aussi `<arn>:*`.
- Contexte : Une version (`:3`) ou un alias (`:prod`) a son propre ARN, dit qualifié, et IAM le compare tel quel. `<arn>:*` couvre tous les qualificatifs de cette fonction, et seulement d'elle : `…ingest-bodacc-v2` n'y correspond pas, car le nom est suivi de `-`, pas de `:`. En revanche `…ingest-bodacc*` (sans `:`) ouvre toute fonction dont le nom commence pareil.
- Usage : ✅ ARN nu + `:*` quand la cible peut devenir un alias · ❌ `function:<nom>*` : ouvre les fonctions homonymes ; `function:*` : toutes.

```bash
# Exemple 1 : simulé (simulate-custom-policy)
# politique : <arn> et <arn>:*
# …ingest-bodacc        → allowed
# …ingest-bodacc:3      → allowed
# …ingest-bodacc:prod   → allowed
# …ingest-bodacc-v2     → implicitDeny
# …autre                → implicitDeny
```

- Quiz : Politique sur l'ARN nu seul. L'appelant invoque `…:function:data-platform-dev-ingest-bodacc:prod` : décision ?
- [ ] `allowed` : l'alias pointe vers la même fonction
- [x] `implicitDeny`
- [ ] `allowed`, mais seulement pour `$LATEST`
- [ ] `explicitDeny`
- Réponse : `implicitDeny` (simulé) : l'ARN qualifié ne correspond pas à l'ARN nu, aucun `Allow` ne s'applique.

## 28. simulate-custom-policy : tester avant de poser
- Sous-thème : évaluation
- Niveau : 2
- Source : data-platform · S1-08
- Définition : `aws iam simulate-custom-policy` évalue une politique JSON non attachée contre des actions et des ARN, sans créer de rôle ni appeler le service.
- Contexte : Pratique avant un `apply` : coller le JSON rendu par `aws_iam_policy_document`, lister les ARN à autoriser et ceux à refuser, et lire `EvalDecision`. Les ARN n'ont pas besoin d'exister. Avec plusieurs `--resource-arns`, le résultat global agrège : simuler un ARN à la fois, ou lire `ResourceSpecificResults`. Il ne voit ni SCP ni politique de ressource.
- Usage : ✅ vérifier une politique avant de la poser, documenter une décision · ❌ preuve qu'un appel réel passera : SCP, boundary et politique de ressource comptent aussi.

```bash
# Exemple 1 : un ARN, une décision
aws iam simulate-custom-policy \
  --policy-input-list "$P" \
  --action-names lambda:InvokeFunction \
  --resource-arns "$ARN:prod" \
  --query 'EvaluationResults[0].EvalDecision' \
  --output text
# → allowed  (si P contient "$ARN:*")
```

- Quiz : Cinq ARN passés d'un coup dans `--resource-arns` : que montre `EvaluationResults[].EvalResourceName` ?
- [ ] Les cinq ARN, une ligne chacun
- [x] Une seule ligne, l'ARN gabarit `${Region}:${Account}…`
- [ ] Le premier ARN seulement
- [ ] Une erreur : un seul ARN permis
- Réponse : une ligne gabarit (mesuré) : le détail par ARN est dans `ResourceSpecificResults` ; d'où un ARN par appel pour lire vite.

## 29. aws sso login : une session qui expire
- Sous-thème : rôles
- Niveau : 2
- Source : data-platform · S1-09
- Définition : `aws configure sso` écrit le profil SSO une fois ; `aws sso login` ouvre une session par le navigateur, à refaire quand elle expire.
- Contexte : Le profil ne contient aucune clé : l'URL du portail, le compte, le nom du rôle (permission set), la région. `aws sso login` met un jeton en cache dans `~/.aws/sso/cache/` ; la CLI, boto3 et Terraform en tirent des identifiants temporaires. Session expirée : erreur de jeton jusqu'au prochain `aws sso login`, sans rien changer d'autre.
- Usage : ✅ poste de développement, plusieurs comptes avec un seul login · ❌ CI : pas de navigateur ; rôle OIDC à la place.

```ini
# Exemple 1 : profil SSO (~/.aws/config)
[profile data-platform]
sso_session    = perso
sso_account_id = <account_id>
sso_role_name  = AdministratorAccess
region         = eu-west-3

[sso-session perso]
sso_start_url  = https://<id>.awsapps.com/start
sso_region     = eu-west-3
```

- Quiz : La session SSO a expiré pendant la nuit. Que faut-il refaire avant `make plan` ?
- [ ] `aws configure sso` en entier
- [x] `aws sso login --profile data-platform`
- [ ] Supprimer `~/.aws/credentials`
- [ ] `terraform init -reconfigure`
- Réponse : `aws sso login` : le profil n'a pas changé, seul le jeton en cache a expiré ; un nouveau login le renouvelle.

## 30. permission boundary : le plafond
- Sous-thème : évaluation
- Niveau : 3
- Définition : Une permission boundary est une politique managée posée sur un rôle ou un utilisateur : elle plafonne ses droits sans en accorder aucun.
- Contexte : Le droit effectif est l'intersection : il faut un `Allow` dans la politique d'identité ET dans la boundary. Usage type : laisser une équipe ou une CI créer ses rôles, à condition (clé `iam:PermissionsBoundary`) que chaque rôle créé porte la boundary : personne ne fabrique alors un rôle plus puissant que le plafond.
- Usage : ✅ rôles que la CI ou un développeur crée lui-même, compte partagé entre équipes · ❌ boundary pour donner un droit qui manque : elle n'accorde rien.

```hcl
# Exemple 1 : le rôle porte son plafond
resource "aws_iam_role" "sandbox" {
  name                 = "dp-dev-sandbox"
  assume_role_policy   = data.aws_iam_policy_document.gh_assume.json
  permissions_boundary = aws_iam_policy.boundary.arn
}
```

```bash
# Exemple 2 : identité s3:*, boundary
# GetObject + ListBucket, simulé
# → s3:GetObject    allowed
#   s3:PutObject    implicitDeny
#   iam:CreateUser  implicitDeny
```

- Quiz : Identité : `s3:GetObject` seul ; boundary : `s3:*` et `iam:*`. Le rôle peut-il créer un utilisateur IAM ?
- [ ] Oui : la boundary l'autorise
- [ ] Oui, si l'identité ne l'interdit pas
- [x] Non : la boundary n'accorde rien
- [ ] Non : `iam:*` est interdit en boundary
- Réponse : non (mesuré : `implicitDeny`) : il faut un `Allow` des deux côtés ; la boundary large ne compense pas l'identité étroite.

## 31. SCP : le plafond du compte
- Sous-thème : évaluation
- Niveau : 3
- Définition : Une SCP (Service Control Policy) d'AWS Organizations plafonne tous les principaux d'un compte membre, sans accorder aucun droit.
- Contexte : Comme une boundary, mais pour tout un compte : un `Allow` IAM n'aboutit que si chaque SCP sur le chemin (racine, OU, compte) l'autorise aussi. `FullAWSAccess`, attachée par défaut, laisse tout passer. Une SCP ne s'applique ni au compte de gestion de l'organisation, ni aux rôles liés à un service. Usages types : interdire toute région hors `eu-west-3`, ou la sortie de l'organisation.
- Usage : ✅ garde-fous d'entreprise non négociables (régions, CloudTrail) sur les comptes membres · ❌ compter sur une SCP pour protéger le compte de gestion : elle ne s'y applique pas, n'y faire tourner aucune charge.

```bash
# Exemple 1 : ce compte et ses SCP
aws organizations describe-organization \
  --query 'Organization.MasterAccountId'
# → "<id>"  (ce compte = gestion)
aws organizations list-policies \
  --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[].Name'
# → ["FullAWSAccess"]   (mesuré)
```

```json
# Exemple 2 : Paris seulement (extrait)
{"Effect": "Deny",
 "NotAction": ["iam:*", "sts:*",
   "organizations:*", "cloudfront:*"],
 "Resource": "*",
 "Condition": {"StringNotEquals": {
   "aws:RequestedRegion": ["eu-west-3"]}}}
```

- Quiz : Une SCP refuse `s3:DeleteBucket` sur un compte membre ; son utilisateur root essaie : résultat ?
- [ ] Autorisé : le root échappe aux SCP
- [ ] Autorisé s'il se connecte avec MFA
- [x] Refusé : la SCP vaut aussi pour le root
- [ ] Refusé dans la console seulement
- Réponse : refusé : dans un compte membre, la SCP borne aussi le root ; seul le compte de gestion échappe aux SCP.

## 32. ExternalId : le tiers confus
- Sous-thème : rôles
- Niveau : 3
- Définition : `sts:ExternalId` est une condition de trust policy : un tiers qui endosse le rôle d'un client doit fournir l'identifiant propre à ce client.
- Contexte : Un SaaS (monitoring, FinOps) sert des milliers de clients depuis son propre compte AWS. Si la trust policy ne nomme que ce compte, un autre client du SaaS peut saisir l'ARN du rôle de quelqu'un d'autre, et le SaaS l'endossera pour lui : le « confused deputy ». L'ExternalId, fixé par le SaaS et unique par client, ferme ce trou. C'est un identifiant de contexte, pas un secret fort.
- Usage : ✅ tout rôle endossé par un compte tiers multi-clients · ❌ ExternalId entre deux comptes à soi, ou pour un service AWS : `aws:SourceArn` et `aws:SourceAccount`.

```hcl
# Exemple 1 : rôle pour un outil FinOps
statement {
  actions = ["sts:AssumeRole"]
  principals {
    type        = "AWS"
    identifiers = ["arn:aws:iam::111122223333:root"]
  }
  condition {
    test     = "StringEquals"
    variable = "sts:ExternalId"
    values   = ["dp-7f3a9c"]
  }
}
```

- Quiz : L'outil appelle `AssumeRole` sur ce rôle sans `--external-id` : résultat ?
- [ ] Accordé : le compte est nommé
- [x] `AccessDenied`
- [ ] Accordé, en lecture seule
- [ ] `ValidationError` : paramètre requis
- Réponse : `AccessDenied` : la clé `sts:ExternalId` est absente de la requête, la condition est fausse, aucun `Allow` ne s'applique.

## 33. Access Analyzer : valider avant de poser
- Sous-thème : moindre privilège
- Niveau : 3
- Définition : IAM Access Analyzer valide une politique avant de la poser (`validate-policy`) et repère les ressources ouvertes hors du compte ou les droits inutilisés.
- Contexte : `validate-policy` relit le JSON sans rien déployer : erreurs (`INVALID_ACTION` sur une faute de frappe, `MISSING_RESOURCE`), avertissements de sécurité (`PassRole` sur `*`, `NotAction` large). Un analyseur de compte, gratuit pour l'accès externe, liste en continu buckets, clés KMS ou rôles ouverts à un autre compte ; l'analyse des droits inutilisés est payante. Il ne dit pas si la politique fait ce que l'on veut.
- Usage : ✅ `validate-policy` en CI sur chaque politique générée, un analyseur par compte · ❌ le prendre pour un simulateur : `simulate-principal-policy` répond à « ce rôle peut-il faire X ? ».

```bash
# Exemple 1 : une faute de frappe
aws accessanalyzer validate-policy \
  --policy-type IDENTITY_POLICY \
  --policy-document file://p.json \
  --query 'findings[].[findingType,issueCode]'
# p.json : "Action": "s3:GetObjet"
# → ERROR  INVALID_ACTION   (mesuré)
```

```bash
# Exemple 2 : PassRole sur *
# → SECURITY_WARNING
#   PASS_ROLE_WITH_STAR_IN_RESOURCE
aws accessanalyzer list-analyzers \
  --query 'analyzers[].name'
# → []  aucun analyseur dans ce compte
```

- Quiz : `validate-policy` sur `s3:ListBucket` avec pour ressource `raw-<id>/*` (mauvais type) : quel finding ?
- [x] Aucun
- [ ] `ERROR INVALID_ACTION`
- [ ] `ERROR` : ressource invalide pour l'action
- [ ] `SECURITY_WARNING`
- Réponse : aucun (mesuré) : la grammaire est juste, seule la sémantique est fausse ; c'est le simulateur qui montre l'`implicitDeny`.

## 34. multipart : couvert par s3:PutObject, sauf Abort
- Sous-thème : politiques
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `CreateMultipartUpload`, `UploadPart` et `CompleteMultipartUpload` sont autorisés par `s3:PutObject` ; annuler exige `s3:AbortMultipartUpload`, un droit à part.
- Contexte : IAM n'a pas d'action par appel multipart : les trois appels d'écriture se rangent sous `s3:PutObject`. `upload_file` de boto3 découpe au-delà de 8 Mo et, en cas d'échec d'une part, tente d'annuler : sans `AbortMultipartUpload`, l'annulation échoue et les parts déjà envoyées restent facturées. D'où la règle `abort_incomplete_multipart_upload` du cycle de vie, qui les supprime après quelques jours.
- Usage : ✅ `PutObject` pour écrire, règle `abort_incomplete_multipart_upload` sur chaque bucket · ❌ ajouter `s3:*Multipart*` par réflexe : `PutObject` suffit à écrire.

```hcl
# Exemple 1 : le filet du cycle de vie
rule {
  id     = "abort-mpu"
  status = "Enabled"
  filter {}
  abort_incomplete_multipart_upload {
    days_after_initiation = 7
  }
}
# parts orphelines → supprimées à J+7
```

- Quiz : Le rôle a `s3:PutObject` sur `bodacc/*` et la clé KMS ; un fichier de 30 Mo part en multipart : l'envoi réussit-il ?
- [ ] Non : `s3:UploadPart` manque
- [x] Oui : `PutObject` couvre les trois appels
- [ ] Non : `s3:CreateMultipartUpload` manque
- [ ] Oui, s'il a aussi `ListBucket`
- Réponse : oui : `UploadPart` et les autres appels d'écriture multipart sont autorisés par `s3:PutObject` ; seuls l'annulation et le listage des parts ont leurs propres droits.

## 35. inline : 10 240 caractères par rôle
- Sous-thème : politiques
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Les politiques inline d'un rôle totalisent au plus 10 240 caractères ; une politique managée, 6 144 : au-delà, l'`apply` échoue.
- Contexte : Les espaces ne comptent pas, mais chaque ARN répété, si. Un rôle partagé par des dizaines de fonctions finit par dépasser ; un rôle par fonction garde chaque politique courte. Si une politique grossit vraiment, les jokers (`bodacc/*`) et le regroupement d'actions réduisent la taille ; un rôle peut aussi porter 10 politiques managées par défaut (quota relevable à 20).
- Usage : ✅ des politiques courtes, une par rôle et par usage (`app`, `logs`) · ❌ empiler toutes les Lambdas dans un rôle : quota atteint, et droits mélangés.

```hcl
# Exemple 1 : deux inline, chacune courte
resource "aws_iam_role_policy" "logs" {
  name   = "logs"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.logs.json
}
resource "aws_iam_role_policy" "app" {
  name   = "app"
  role   = aws_iam_role.this.id
  policy = var.policy_json
}
```

- Quiz : Une politique inline de 9 000 caractères existe ; on ajoute au même rôle une seconde inline de 2 000 : résultat ?
- [ ] Réussi : chaque politique est sous 10 240
- [x] `LimitExceeded` : 11 000 au total
- [ ] Réussi, la seconde devient managée
- [ ] Erreur au `plan`
- Réponse : `LimitExceeded` à l'`apply` : la limite de 10 240 caractères porte sur le total des politiques inline du rôle, pas sur chacune.

## 36. aws:SourceArn : le groupe de planifications
- Sous-thème : rôles
- Niveau : 3
- Source : data-platform · S1-08
- Définition : Pour EventBridge Scheduler, `aws:SourceArn` vaut l'ARN du **groupe** de planifications (`schedule-group/<nom>`), jamais celui d'une planification.
- Contexte : `SourceArn` borne plus finement que `SourceAccount` : seul un groupe précis peut faire endosser le rôle. La doc Scheduler est explicite : ne pas viser une planification ni un préfixe de nom, la condition ne correspondrait jamais. Avec un joker (`schedule-group/*`), l'opérateur doit être `ArnLike`, pas `StringEquals`. Sans `group_name`, une planification est dans le groupe `default`.
- Usage : ✅ isoler un groupe par équipe ou par environnement, en plus de `aws:SourceAccount` · ❌ `aws:SourceArn` sur `…:schedule/default/ingest` : le rôle n'est plus jamais endossé.

```hcl
# Exemple 1 : borné au groupe default
condition {
  test     = "ArnLike"
  variable = "aws:SourceArn"
  values = [
    "arn:aws:scheduler:*:${local.account_id}:schedule-group/default",
  ]
}
```

- Quiz : `StringEquals` avec la valeur `arn:aws:scheduler:*:<compte>:schedule-group/*` : que se passe-t-il ?
- [ ] Tous les groupes du compte sont acceptés
- [x] Rien ne correspond : `*` y est un caractère littéral
- [ ] Erreur à l'`apply` : joker interdit
- [ ] Seul le groupe `default` est accepté
- Réponse : rien ne correspond : `StringEquals` compare au caractère près ; les jokers ne valent que pour `ArnLike` ou `StringLike` (doc Scheduler).
