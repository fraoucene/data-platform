---
title: "Cartes · Cognito"
type: cartes
langage: AWS
chapitre: Identité et sécurité
cours: Cognito
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Cognito
AWS · Cognito : user pool, identity pool, flux d'identifiants, identités (format spec v4 de revision-pwa).

## 1. user pool ou identity pool : deux questions
- Id : cognito-user-ou-identity-pool
- Sous-thème : pools
- Type : comparaison
- Niveau : 1
- Profils : débutant, web
- Voir aussi : cognito-ou-api-gateway
- Source : data-platform · pwa-sync
- Définition : Le user pool répond « qui es-tu ? » (jetons JWT) ; l'identity pool, « que peux-tu faire dans AWS ? » (identifiants IAM temporaires).
- Contexte : Le user pool gère comptes, mots de passe, MFA et émet id token, access token et refresh token, comme NextAuth ou Auth0. Il ne donne aucun droit AWS. L'identity pool prend un jeton (de Cognito, Google, OIDC…), attribue un identity id stable et l'échange contre des identifiants STS d'un rôle IAM. On peut utiliser l'un sans l'autre.
- Usage : ✅ user pool seul : login d'une app qui parle à votre API ; les deux : app qui appelle AWS directement (DynamoDB, S3) · ❌ identity pool pour gérer des mots de passe : il n'en stocke aucun.

```
# Exemple 1 : la chaîne de revision-pwa
e-mail + mot de passe
  → user pool     : id token (JWT, 1 h)
  → identity pool : identity id
                    + clés STS (1 h)
  → DynamoDB      : requêtes signées
```

```hcl
# Exemple 2 : l'identity pool branché
resource "aws_cognito_identity_pool" "this" {
  identity_pool_name = "${local.prefix}-identities"
  cognito_identity_providers {
    client_id     = aws_cognito_user_pool_client.app.id
    provider_name = aws_cognito_user_pool.this.endpoint
  }
}
```

- Quiz : Avec seulement un user pool, l'app peut-elle appeler `dynamodb:Query` avec l'access token ?
- [ ] Oui : l'access token sert à ça
- [x] Non : DynamoDB attend une requête signée SigV4
- [ ] Oui, si le scope `dynamodb` est accordé
- [ ] Non : seul l'id token est accepté
- Réponse : non : les API AWS n'acceptent que des requêtes signées avec des clés IAM ; un JWT du user pool doit d'abord être échangé par un identity pool.

## 2. identity id : pas le sub du user pool
- Id : cognito-identity-id-vs-sub
- Sous-thème : identités
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Source : data-platform · pwa-sync
- Définition : L'identity id (`eu-west-3:<uuid>`) est l'identifiant attribué par l'identity pool, distinct du `sub` du user pool, même pour le même compte.
- Contexte : Le `sub` (UUID sans préfixe) est dans l'id token ; l'identity id est créé par `GetId` au premier échange puis retrouvé à chaque fois pour le même compte. Côté IAM, `${cognito-identity.amazonaws.com:sub}` vaut l'identity id, jamais le `sub` du JWT : c'est lui qui doit servir de clé de partition.
- Usage : ✅ identity id comme `pk` des lignes accessibles depuis l'app · ❌ `sub` du JWT comme clé : la politique `LeadingKeys` ne le connaît pas, toutes les requêtes seraient refusées.

```python
# Exemple 1 : deux identifiants, un compte
sub = "8f2c1a7e-0b4d-4e1f-9a63-2d5b7c8e9f01"
identity_id = ("eu-west-3:"
    "1b2c3d4e-5f60-4718-8a9b-0c1d2e3f4a5b")
identity_id.split(":")[0]   # → 'eu-west-3'
sub == identity_id.split(":")[1]  # → False
```

```
# Exemple 2 : où les lire
sub         : claim de l'id token
identity id : réponse de GetId,
              puis ${cognito-identity
              .amazonaws.com:sub} dans IAM
```

- Quiz : Les lignes ont `pk` = `sub` du JWT ; la politique teste `LeadingKeys` = `${cognito-identity.amazonaws.com:sub}`. Résultat ?
- [ ] Accès normal à ses lignes
- [ ] Accès à toutes les lignes
- [x] `AccessDeniedException` sur ses propres lignes
- [ ] Erreur de validation de la politique
- Réponse : `AccessDeniedException` : la variable vaut l'identity id (`eu-west-3:…`), différent du `sub` ; aucune clé demandée ne correspond.

## 3. GetId puis GetCredentialsForIdentity
- Id : cognito-flux-enhanced-appels
- Sous-thème : flux
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Voir aussi : cognito-enhanced-ou-classic
- Source : data-platform · pwa-sync
- Définition : Le flux « enhanced » tient en deux appels : `GetId` (jeton → identity id), puis `GetCredentialsForIdentity` (identity id + jeton → clés STS).
- Contexte : Les deux reçoivent la même map `Logins` : `{"<fournisseur>": "<id token>"}`. Le second renvoie `AccessKeyId`, `SecretKey`, `SessionToken`, `Expiration`, pour le rôle `authenticated` choisi par le pool. Côté TS, c'est ce que fait `fromCognitoIdentityPool` du SDK v3 ; à la main, deux `fetch` JSON suffisent.
- Usage : ✅ app web ou mobile qui appelle AWS sans backend · ❌ backend qui a déjà un rôle IAM (Lambda, conteneur) : il utilise ses propres identifiants.

```bash
# Exemple 1 : les deux appels (CLI)
id=$(aws cognito-identity get-id \
  --identity-pool-id "$POOL" \
  --logins "$PROVIDER=$ID_TOKEN" \
  --query IdentityId --output text)
aws cognito-identity \
  get-credentials-for-identity \
  --identity-id "$id" \
  --logins "$PROVIDER=$ID_TOKEN"
```

```json
# Exemple 2 : la réponse (abrégée)
{"IdentityId": "eu-west-3:1b2c…",
 "Credentials": {
   "AccessKeyId": "ASIA…",
   "SecretKey": "…",
   "SessionToken": "…",
   "Expiration": "2026-10-25T21:00:00Z"}}
```

- Quiz : On appelle `GetCredentialsForIdentity` sans `--logins`, pour une identité authentifiée : résultat ?
- [ ] Les mêmes clés : l'identity id suffit
- [ ] Des clés du rôle invité
- [x] Refus : le jeton doit accompagner l'identity id
- [ ] Des clés sans aucun droit
- Réponse : refus : une identité authentifiée doit présenter son jeton à chaque échange ; l'identity id seul n'est pas une preuve (doc `GetCredentialsForIdentity`).

## 4. appels publics : sans signature
- Id : cognito-appels-publics
- Sous-thème : flux
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Voir aussi : api-sigv4-authorization
- Source : data-platform · pwa-sync
- Définition : `GetId` et `GetCredentialsForIdentity` sont des API publiques : l'app les appelle sans clé AWS, la preuve est le jeton dans `Logins`.
- Contexte : Logique : l'app n'a encore aucune clé, c'est justement ce qu'elle vient chercher. En CLI, `--no-sign-request` reproduit la situation de l'app (sinon la CLI signerait avec votre profil, ce qui masquerait un problème). Même chose pour `initiate-auth` du user pool. Ensuite seulement, les requêtes DynamoDB sont signées avec les clés reçues.
- Usage : ✅ tester le flux exact de l'app depuis un terminal · ❌ tester avec votre profil admin : un appel qui marche pour vous peut échouer pour l'app.

```bash
# Exemple 1 : comme l'app, sans profil
aws cognito-identity get-id \
  --no-sign-request \
  --region eu-west-3 \
  --identity-pool-id "$POOL" \
  --logins "$PROVIDER=$ID_TOKEN"
# → {"IdentityId": "eu-west-3:…"}
```

```bash
# Exemple 2 : puis on signe avec les clés reçues
export AWS_ACCESS_KEY_ID=$(jq -r .AccessKeyId <<<"$creds")
export AWS_SECRET_ACCESS_KEY=$(jq -r .SecretKey <<<"$creds")
export AWS_SESSION_TOKEN=$(jq -r .SessionToken <<<"$creds")
unset AWS_PROFILE   # par clarté
```

- Quiz : L'app appelle `GetId` en `fetch`, sans en-tête `Authorization`, avec un id token valide dans `Logins`. Réponse ?
- [x] L'identity id : l'appel est public
- [ ] `MissingAuthenticationTokenException`
- [ ] `AccessDeniedException` : aucun rôle IAM
- [ ] `UnrecognizedClientException`
- Réponse : l'identity id : `GetId` n'exige aucune signature SigV4, c'est le jeton de `Logins` qui prouve l'identité (un `curl` non signé reçoit une erreur métier, jamais `MissingAuthenticationToken`).

## 5. rôle authenticated : rattaché au pool
- Id : cognito-role-authenticated
- Sous-thème : pools
- Type : recette
- Niveau : 1
- Profils : web, ops
- Prérequis : iam-role-confiance-permissions
- Voir aussi : iam-confiance-cognito
- Source : data-platform · pwa-sync
- Définition : `aws_cognito_identity_pool_roles_attachment` dit quel rôle IAM l'identity pool donne aux identités connectées (`authenticated`) et invitées (`unauthenticated`).
- Contexte : Dans le flux enhanced, c'est le pool qui choisit le rôle, jamais l'app : un client modifié ne peut pas demander un autre rôle. Le rôle doit en plus faire confiance à `cognito-identity.amazonaws.com` pour ce pool. Sans rattachement, `GetCredentialsForIdentity` échoue : aucun rôle à endosser.
- Usage : ✅ un rôle `authenticated` aux droits minimaux, une clé `unauthenticated` seulement si les invités sont voulus · ❌ un rôle partagé avec d'autres usages : sa confiance et ses droits s'élargissent.

```hcl
# Exemple 1 : seuls les connectés ont un rôle
resource "aws_cognito_identity_pool_roles_attachment" "this" {
  identity_pool_id = aws_cognito_identity_pool.this.id
  roles = {
    authenticated = aws_iam_role.progress_user.arn
  }
}
```

- Quiz : Le rôle est rattaché comme `authenticated`, mais sa confiance n'a pas la condition `aud` = ce pool. Risque ?
- [ ] Aucun : le rattachement suffit
- [x] Un autre identity pool du compte pourrait l'endosser
- [ ] L'app ne reçoit plus de clés
- [ ] Les invités l'endossent automatiquement
- Réponse : un autre pool : le rattachement dit quel rôle CE pool donne ; seule la condition `aud` de la confiance empêche un autre pool de donner le même rôle.

## 6. Logins : la clé est le fournisseur
- Id : cognito-logins-fournisseur
- Sous-thème : flux
- Type : piège
- Niveau : 2
- Profils : web
- Source : data-platform · pwa-sync
- Définition : Dans `Logins`, la clé est le nom du fournisseur (`cognito-idp.<région>.amazonaws.com/<user pool id>`), la valeur est l'**id token** du user pool.
- Contexte : Le nom vient de l'attribut `endpoint` du user pool en Terraform, ou de `describe-identity-pool`. Une faute de région ou d'id dans la clé donne un `NotAuthorizedException`. On donne l'id token et non l'access token : c'est lui que l'identity pool vérifie (`aud` = client de l'app).
- Usage : ✅ lire le nom du fournisseur dans Terraform ou `describe-identity-pool` · ❌ le reconstruire à la main dans l'app : une région mal recopiée suffit à tout casser.

```bash
# Exemple 1 : lire le fournisseur enregistré
aws cognito-identity describe-identity-pool \
  --identity-pool-id "$POOL" \
  --query 'CognitoIdentityProviders[0].ProviderName' \
  --output text
# → cognito-idp.eu-west-3.amazonaws.com/
#   eu-west-3_AbCdEf123
```

```json
# Exemple 2 : la map envoyée par l'app
{"IdentityPoolId": "eu-west-3:…",
 "Logins": {
   "cognito-idp.eu-west-3.amazonaws.com/eu-west-3_AbCdEf123":
     "<id token>"}}
```

- Quiz : L'app met l'**access token** comme valeur de `Logins`. Résultat ?
- [ ] Ça marche : les deux jetons sont signés
- [x] Refus : l'identity pool attend l'id token
- [ ] Ça marche, avec des droits réduits
- [ ] Identité invitée créée
- Réponse : refus : pour un user pool Cognito, l'identity pool valide l'id token (claim `aud` = client de l'app) ; l'access token n'a pas ce claim.

## 7. allow_unauthenticated_identities : pas d'invité
- Id : cognito-sans-invites
- Sous-thème : identités
- Type : concept
- Niveau : 2
- Profils : web, ops
- Prérequis : cognito-role-authenticated
- Source : data-platform · pwa-sync
- Définition : `allow_unauthenticated_identities = false` interdit les identités invitées : sans jeton valide, `GetId` refuse au lieu de créer une identité anonyme.
- Contexte : Une identité invitée reçoit des clés du rôle `unauthenticated`, sans compte : utile pour une démo ou des métriques anonymes. Pour une synchro de progression, ça n'a pas de sens (rien à retrouver sur un autre appareil). Si on l'active un jour, la confiance du rôle des connectés doit tester `amr = authenticated`, sinon un invité endosse aussi ce rôle.
- Usage : ✅ `false` dès que les données sont liées à un compte · ❌ `true` « pour tester » : chaque visiteur obtient des clés AWS.

```hcl
# Exemple 1 : comptes seulement
resource "aws_cognito_identity_pool" "this" {
  identity_pool_name               = "${local.prefix}-identities"
  allow_unauthenticated_identities = false
  allow_classic_flow               = false
}
```

```bash
# Exemple 2 : sans Logins, refus
aws cognito-identity get-id \
  --no-sign-request \
  --identity-pool-id "$POOL"
# → NotAuthorizedException (doc)
#   (identités invitées désactivées)
```

- Quiz : Invités et flux classic activés, confiance du rôle connecté sans `amr` : un visiteur peut-il endosser ce rôle ?
- [ ] Non : le pool lui impose le rôle invité
- [ ] Non : sans jeton du user pool, STS refuse
- [x] Oui : `GetOpenIdToken` puis `AssumeRoleWithWebIdentity`
- [ ] Oui, mais en lecture seule
- Réponse : oui : en flux classic, l'app choisit le rôle avec son jeton OpenID d'invité ; seule la condition `amr` = `authenticated` de la confiance l'en empêche.

## 8. flux enhanced ou classic
- Id : cognito-enhanced-ou-classic
- Sous-thème : flux
- Type : comparaison
- Niveau : 2
- Profils : web, ops
- Source : data-platform · pwa-sync
- Définition : Enhanced : le pool choisit le rôle et appelle STS pour l'app. Classic (`allow_classic_flow`) : l'app reçoit un jeton OpenID et appelle elle-même `AssumeRoleWithWebIdentity`.
- Contexte : Classic = `GetId`, `GetOpenIdToken`, puis `sts:AssumeRoleWithWebIdentity` avec l'ARN de rôle de son choix : le client décide du rôle, la seule barrière est la confiance des rôles. Enhanced = `GetId`, `GetCredentialsForIdentity`, un appel de moins et le rôle imposé par le pool. AWS recommande l'enhanced.
- Usage : ✅ enhanced par défaut, `allow_classic_flow = false` · ❌ classic seulement pour un besoin précis (session policy maison, rôle choisi côté client sous contrôle).

```
# Exemple 1 : les deux enchaînements
enhanced : GetId
         → GetCredentialsForIdentity
           (rôle choisi par le pool)
classic  : GetId
         → GetOpenIdToken
         → sts:AssumeRoleWithWebIdentity
           (rôle choisi par l'app)
```

- Quiz : `allow_classic_flow = false` : un client appelle `GetOpenIdToken` pour son identité. Résultat ?
- [ ] Un jeton OpenID, utilisable avec STS
- [x] Refus : le flux classic est désactivé
- [ ] Des clés STS directement
- [ ] Un jeton, mais STS le refuse
- Réponse : refus (selon la doc) : sans flux classic, seul `GetCredentialsForIdentity` délivre des clés, pour le rôle choisi par le pool.

## 9. clés STS : 1 h, à renouveler avant
- Id : cognito-renouveler-cles-sts
- Sous-thème : flux
- Type : recette
- Niveau : 2
- Profils : web
- Voir aussi : api-expiration-secondes
- Source : data-platform · pwa-sync
- Définition : Les clés données par l'identity pool expirent (1 h, champ `Expiration`) : l'app les garde en cache et en redemande juste avant l'échéance.
- Contexte : Redemander à chaque requête coûte un aller-retour et ralentit ; attendre l'expiration donne un `ExpiredTokenException` en pleine écriture. On renouvelle avec une marge (1 min avant). L'id token, lui, vit 1 h aussi : s'il a expiré, il faut d'abord le rafraîchir avec le refresh token, puis refaire l'échange.
- Usage : ✅ cache en mémoire avec marge, renouvellement paresseux à la prochaine requête · ❌ clés en `localStorage` : un script injecté les lirait ; elles se renouvellent vite de toute façon.

```python
# Exemple 1 : garder ou renouveler
from datetime import datetime, timedelta, UTC
MARGE = timedelta(minutes=1)

def a_renouveler(expiration, maintenant):
    return maintenant >= expiration - MARGE

exp = datetime(2026, 10, 25, 21, 0, tzinfo=UTC)
a_renouveler(exp, exp - timedelta(minutes=5))  # → False
a_renouveler(exp, exp - timedelta(seconds=30))  # → True
```

- Quiz : Clés valides encore 30 min, mais l'id token a expiré il y a 5 min. La prochaine `Query` passe-t-elle ?
- [x] Oui : les clés STS restent valides jusqu'à leur `Expiration`
- [ ] Non : DynamoDB vérifie l'id token
- [ ] Non : les clés expirent avec l'id token
- [ ] Oui, mais en lecture seule
- Réponse : oui : une fois émises, les clés STS vivent leur propre durée ; l'id token n'est revérifié qu'au prochain échange.

## 10. server_side_token_check : revérifier le jeton
- Id : cognito-server-side-token-check
- Sous-thème : pools
- Type : concept
- Niveau : 2
- Profils : web, ops
- Prérequis : cognito-logins-fournisseur
- Source : data-platform · pwa-sync
- Définition : `server_side_token_check = true` : avant de donner des clés, l'identity pool vérifie auprès du user pool que le compte existe et reste connecté.
- Contexte : Sans cette option, un id token encore dans sa durée de vie suffit, même après `GlobalSignOut` ou suppression du compte. Avec, l'échange est refusé. Limite : les clés STS déjà délivrées restent valides jusqu'à leur expiration (1 h au plus) ; la révocation n'est donc jamais instantanée.
- Usage : ✅ dès que la suppression de compte ou la déconnexion doit couper l'accès vite · ❌ compter dessus pour couper à la seconde : réduire aussi la durée de vie des jetons.

```hcl
# Exemple 1 : revérifier à chaque échange
cognito_identity_providers {
  client_id     = aws_cognito_user_pool_client.app.id
  provider_name = aws_cognito_user_pool.this.endpoint
  # compte supprimé, GlobalSignOut → refus
  server_side_token_check = true
}
```

- Quiz : Compte supprimé à 20 h 00, clés STS obtenues à 19 h 50. Une `Query` à 20 h 10 passe-t-elle ?
- [ ] Non : `server_side_token_check` révoque les clés
- [x] Oui : les clés déjà émises courent jusqu'à leur expiration
- [ ] Non : DynamoDB interroge le user pool
- [ ] Oui, mais sans résultat
- Réponse : oui : la vérification se fait à l'échange de jeton ; des clés STS émises ne sont pas révoquées, elles expirent (ici vers 20 h 50).

## 11. client public : pas de secret
- Id : cognito-client-sans-secret
- Sous-thème : pools
- Type : piège
- Niveau : 2
- Profils : web
- Source : data-platform · pwa-sync
- Définition : Un client de user pool utilisé par un navigateur ou un mobile se crée sans secret (`generate_secret = false`) : embarqué, il serait public.
- Contexte : Avec un secret, chaque appel (`InitiateAuth`…) doit porter un `SECRET_HASH` calculé avec lui : impossible à garder secret dans du JavaScript livré au client. La sécurité vient alors du mot de passe, des jetons courts et, pour AWS, du rôle IAM minimal. Le secret sert aux clients serveurs (backend, confidential client OAuth).
- Usage : ✅ PWA, React Native, SPA : client sans secret · ❌ secret dans un `VITE_*` : il finit en clair dans le bundle.

```hcl
# Exemple 1 : client de la PWA
resource "aws_cognito_user_pool_client" "app" {
  name            = "${local.prefix}-app"
  user_pool_id    = aws_cognito_user_pool.this.id
  generate_secret = false
}
```

- Quiz : Un client **avec** secret, `initiate-auth` sans `SECRET_HASH` : résultat ?
- [ ] Connexion normale
- [x] `NotAuthorizedException` : le hash du secret manque
- [ ] Connexion, mais sans refresh token
- [ ] `InvalidParameterException` : flux inconnu
- Réponse : `NotAuthorizedException` (selon la doc, non mesuré ici) : un client à secret exige le `SECRET_HASH` à chaque appel.

## 12. explicit_auth_flows : USER_PASSWORD_AUTH
- Id : cognito-explicit-auth-flows
- Sous-thème : flux
- Type : concept
- Niveau : 2
- Profils : web
- Prérequis : cognito-client-sans-secret
- Source : data-platform · pwa-sync
- Définition : `explicit_auth_flows` liste les façons de se connecter qu'accepte un client ; `initiate-auth --auth-flow USER_PASSWORD_AUTH` exige `ALLOW_USER_PASSWORD_AUTH`.
- Contexte : `USER_PASSWORD_AUTH` envoie le mot de passe (en HTTPS) à Cognito : simple pour un script ou une app sans SDK. `USER_SRP_AUTH` ne l'envoie jamais (preuve SRP), au prix d'un calcul côté client. `ALLOW_REFRESH_TOKEN_AUTH` permet de renouveler les jetons sans redemander le mot de passe. Un flux absent de la liste est refusé.
- Usage : ✅ autoriser seulement les flux utilisés par l'app et les scripts · ❌ tous les flux « au cas où » : surface d'attaque inutile.

```hcl
# Exemple 1 : les flux du client de l'app
explicit_auth_flows = [
  "ALLOW_USER_PASSWORD_AUTH",
  "ALLOW_USER_SRP_AUTH",
  "ALLOW_REFRESH_TOKEN_AUTH",
]
```

```bash
# Exemple 2 : connexion depuis un script
aws cognito-idp initiate-auth \
  --no-sign-request \
  --client-id "$CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters "USERNAME=$EMAIL,PASSWORD=$PW" \
  --query AuthenticationResult.IdToken
```

- Quiz : Avec `USER_PASSWORD_AUTH`, le mot de passe est-il lisible par Cognito ?
- [ ] Non : la CLI le hache avant l'envoi
- [x] Oui : TLS le protège en transit, Cognito le reçoit tel quel
- [ ] Non : il est remplacé par une preuve SRP
- [ ] Oui, et il circule en clair sur le réseau
- Réponse : oui : TLS chiffre le transport, mais Cognito reçoit le mot de passe ; seul `USER_SRP_AUTH` évite de l'envoyer.

## 13. identity id : stable entre appareils
- Id : cognito-identity-id-stable
- Sous-thème : identités
- Type : concept
- Niveau : 2
- Profils : web
- Prérequis : cognito-identity-id-vs-sub
- Voir aussi : iam-variable-dans-resource
- Source : data-platform · pwa-sync
- Définition : Le même compte obtient le même identity id sur tous ses appareils : `GetId` retrouve l'identité liée au fournisseur et au `sub` du jeton.
- Contexte : C'est ce qui rend la synchro possible : iPhone et Mac écrivent sous la même clé de partition sans se concerter. L'identity id ne change pas tant que le compte existe dans le user pool et que l'identité n'est pas supprimée du pool. Supprimer puis recréer le compte (nouveau `sub`) donne une nouvelle identité : les anciennes lignes deviennent orphelines.
- Usage : ✅ identity id comme clé de toutes les données de l'utilisateur côté AWS · ❌ un id généré par l'app (`crypto.randomUUID()`) : différent sur chaque appareil, et IAM ne peut pas le vérifier.

```
# Exemple 1 : deux appareils, une partition
iPhone : id token (sub 8f2c…) → GetId
         → eu-west-3:1b2c…
Mac    : id token (sub 8f2c…) → GetId
         → eu-west-3:1b2c…   (le même)
pk = eu-west-3:1b2c… pour les deux
```

- Quiz : Compte supprimé puis recréé avec le même e-mail : que devient la progression déjà synchronisée ?
- [ ] Retrouvée : même e-mail, même identity id
- [x] Orpheline : nouveau `sub`, donc nouvel identity id
- [ ] Effacée automatiquement par Cognito
- [ ] Fusionnée au premier `GetId`
- Réponse : orpheline : le nouveau compte a un nouveau `sub`, `GetId` crée une nouvelle identité ; d'où l'effacement de la partition avant `DeleteUser`.

## 14. Cognito ou API Gateway + Lambda : choisir
- Id : cognito-ou-api-gateway
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : web
- Source : data-platform · pwa-sync
- Définition : Identity pool + IAM fin : l'app parle directement à AWS ; API Gateway + Lambda : un backend intermédiaire porte la logique métier.
- Contexte : Sans backend : identity pool gratuit, aucune Lambda à maintenir, latence d'un seul saut ; l'isolation tient dans la politique IAM (`LeadingKeys`). Limite : aucune règle métier côté serveur (validation, quotas, agrégats) ; l'app peut écrire n'importe quel contenu dans ses lignes. Avec Lambda : validation et logique centralisées, au prix d'un service à coder, tester, payer.
- Usage : ✅ direct : données privées par utilisateur, écriture libre dans sa partition · ❌ direct quand il faut valider, croiser des utilisateurs ou masquer la table : API Gateway + Lambda.

```
# Exemple 1 : la décision de pwa-sync
Besoin  : progression par utilisateur,
          lue et écrite par l'app
→ Choix : identity pool + DynamoDB
          direct, LeadingKeys
Pourquoi: 0 serveur, ~1,4 $ par
          million d'écritures
Écarté  : API GW + Lambda (code et
          coût sans valeur ajoutée)
```

- Quiz : On veut empêcher un utilisateur de s'attribuer 10 000 bonnes réponses en modifiant l'app. Accès direct suffisant ?
- [ ] Oui : `LeadingKeys` l'en empêche
- [ ] Oui : `server_side_token_check` le bloque
- [x] Non : IAM borne les lignes, pas leur contenu
- [ ] Non : il faut un second identity pool
- Réponse : non : IAM vérifie quelles lignes sont touchées, pas ce qu'elles contiennent ; une règle métier demande un backend (Lambda) entre l'app et la table.

## 15. session CognitoIdentityCredentials : lire le refus
- Id : cognito-session-dans-refus
- Sous-thème : identités
- Type : recette
- Niveau : 3
- Profils : web, ops
- Prérequis : cognito-role-authenticated
- Voir aussi : iam-refus-condition-message
- Source : data-platform · pwa-sync
- Définition : En flux enhanced, Cognito endosse le rôle avec le nom de session `CognitoIdentityCredentials` : on le retrouve dans l'ARN de l'appelant d'un refus.
- Contexte : Un `AccessDeniedException` affiche `assumed-role/<rôle>/CognitoIdentityCredentials` : on sait que l'appel venait bien des clés de l'identity pool, avec ce rôle-là, et non de votre profil. C'est le premier réflexe de lecture d'un refus : quel principal, quelle action, quelle ressource. Les données de l'utilisateur, elles, n'apparaissent pas dans ce nom.
- Usage : ✅ vérifier dans un refus ou dans CloudTrail que l'appel venait de l'app · ❌ conclure « politique fausse » sans lire le principal : le refus vient peut-être d'un autre profil.

```
# Exemple 1 : le refus mesuré (abrégé)
AccessDeniedException: User:
  arn:aws:sts::<account_id>:assumed-role/
  revision-pwa-dev-progress-user/
  CognitoIdentityCredentials
  is not authorized to perform:
  dynamodb:Query on resource: …progress
  because no identity-based policy
  allows the dynamodb:Query action
```

- Quiz : Un refus montre `assumed-role/AWSReservedSSO_Admin…/<votre e-mail>` sur la `Query`. Que conclure ?
- [ ] La politique `LeadingKeys` est fausse
- [x] Le test a signé avec votre profil, pas les clés Cognito
- [ ] L'identity pool a choisi le mauvais rôle
- [ ] Le flux classic a été utilisé
- Réponse : votre profil : l'ARN de l'appelant est celui de votre session SSO ; les variables `AWS_*` n'ont pas été prises (souvent `AWS_PROFILE` encore défini).

## 16. amr : ce que le jeton prouve
- Id : cognito-amr-liste
- Sous-thème : identités
- Type : concept
- Niveau : 3
- Profils : web, expert
- Voir aussi : iam-confiance-cognito
- Source : data-platform · pwa-sync
- Définition : `cognito-identity.amazonaws.com:amr` est une **liste** : `authenticated` ou `unauthenticated`, puis le fournisseur, puis le fournisseur suivi du `sub`.
- Contexte : Pour un compte du user pool : `["authenticated", "cognito-idp.<région>.amazonaws.com/<pool>", "cognito-idp…:CognitoSignIn:<sub>"]`. Comme c'est une liste, la confiance la teste avec `ForAnyValue:StringLike` : « au moins une valeur vaut `authenticated` ». On peut aussi y restreindre un rôle à un fournisseur précis (Google seulement, par exemple).
- Usage : ✅ `ForAnyValue:StringLike` sur `amr` dans toute confiance de rôle Cognito · ❌ `StringEquals` simple sur `amr` : la liste n'est jamais égale à une seule valeur.

```python
# Exemple 1 : la logique de ForAnyValue
amr = ["authenticated",
       "cognito-idp.eu-west-3.amazonaws.com/"
       "eu-west-3_AbCdEf123"]
any(v == "authenticated" for v in amr)  # → True
invite = ["unauthenticated"]
any(v == "authenticated" for v in invite)  # → False
```

- Quiz : On veut un rôle réservé aux comptes connectés **via Google**. Quelle valeur tester dans `amr` ?
- [ ] `authenticated` seulement
- [x] `accounts.google.com` (le fournisseur), en plus d'`authenticated`
- [ ] `cognito-idp…:CognitoSignIn:*`
- [ ] Le `sub` de chaque utilisateur Google
- Réponse : le fournisseur : `amr` contient aussi le nom du fournisseur qui a authentifié (`accounts.google.com` pour Google), testable avec `ForAnyValue:StringLike`.
