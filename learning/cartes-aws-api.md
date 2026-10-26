---
title: "Cartes · API AWS"
type: cartes
langage: AWS
chapitre: Identité et sécurité
cours: API
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · API AWS
AWS · API : appeler un service en HTTP sans SDK, signature SigV4, protocole JSON, erreurs, identifiants temporaires (format spec v4 de revision-pwa).

## 1. SigV4 : l'en-tête Authorization
- Id : api-sigv4-authorization
- Sous-thème : sigv4
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Voir aussi : api-sigv4-portee
- Mots-clés : SigV4, HMAC, clé d'accès, SDK AWS
- Source : data-platform · pwa-sync
- Définition : SigV4 signe chaque requête AWS par HMAC-SHA256 avec la clé secrète ; le résultat part dans l'en-tête `Authorization`, la clé secrète jamais.
- Contexte : AWS recalcule la même signature de son côté et compare : la requête prouve qu'on détient la clé sans la transmettre, et toute modification en route casse la signature. L'en-tête porte trois parties : `Credential` (clé d'accès et portée), `SignedHeaders` (en-têtes couverts), `Signature` (64 caractères hexadécimaux). Les SDK, la CLI et `aws4fetch` le calculent ; il n'y a pas de jeton porteur comme un `Bearer` OAuth.
- Usage : ✅ toute requête vers une API AWS hors appels publics (Cognito `GetId`) · ❌ coder la signature à la main : une bibliothèque testée (`aws4fetch`, SDK).

```text
# Exemple 1 : mesuré (aws4fetch, DynamoDB)
Authorization: AWS4-HMAC-SHA256
  Credential=ASIAEXAMPLE/20261025/
    eu-west-3/dynamodb/aws4_request,
  SignedHeaders=host;x-amz-date;
    x-amz-security-token;x-amz-target,
  Signature=3d7c89ad675bd71c…
x-amz-date: 20261025T195027Z
x-amz-security-token: <jeton STS>
```

- Quiz : Laquelle de ces informations n'apparaît jamais dans une requête signée SigV4 ?
- [ ] L'identifiant de clé d'accès
- [ ] La région du service
- [x] La clé secrète
- [ ] La liste des en-têtes signés
- Réponse : la clé secrète : elle sert seulement à calculer le HMAC des deux côtés ; un intercepteur ne voit que la signature, inutilisable pour une autre requête.

## 2. Credential : date, région, service
- Id : api-sigv4-portee
- Sous-thème : sigv4
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Mots-clés : SigV4, région AWS, aws4fetch
- Source : data-platform · pwa-sync
- Définition : La portée `<clé>/<AAAAMMJJ>/<région>/<service>/aws4_request` lie la signature à un jour, une région et un service précis.
- Contexte : AWS contrôle la portée avant même la clé : une signature calculée pour `us-east-1` ou pour `s3` est refusée par DynamoDB à Paris, avec un message explicite. C'est pour cela que `aws4fetch` reçoit `service: 'dynamodb'` et `region` à la construction du client : un client signe pour un seul service.
- Usage : ✅ un client signeur par service et région (`AwsClient` de cloud.ts) · ❌ réutiliser le client DynamoDB pour appeler S3 ou STS : nouveau client, autre `service`.

```text
# Exemple 1 : mesuré, clé bidon, région fausse
POST https://dynamodb.eu-west-3.amazonaws.com/
Credential=AKIA…/20261025/us-east-1/
  dynamodb/aws4_request
→ 400 InvalidSignatureException
  "Credential should be scoped to
   a valid region."
```

- Quiz : Même requête vers DynamoDB, portée signée avec le service `s3`. Réponse ?
- [ ] 200 : seule la région compte
- [x] `InvalidSignatureException` sur le service
- [ ] `UnknownOperationException`
- [ ] 403 `AccessDenied` d'IAM
- Réponse : `InvalidSignatureException` (mesuré) : « Credential should be scoped to correct service: 'dynamodb' » ; la portée est vérifiée avant les droits IAM.

## 3. x-amz-security-token : clés temporaires
- Id : api-security-token
- Sous-thème : sigv4
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Voir aussi : cognito-renouveler-cles-sts
- Mots-clés : STS, utilisateur IAM, identity pool, jeton de session
- Source : data-platform · pwa-sync
- Définition : Des clés temporaires STS (préfixe `ASIA`) vont avec un jeton de session, envoyé dans `x-amz-security-token` et inclus dans les en-têtes signés.
- Contexte : Une clé permanente d'utilisateur IAM commence par `AKIA` et n'a pas de jeton ; une clé STS (rôle, Cognito identity pool, SSO) commence par `ASIA` et ne vaut rien sans son `SessionToken`. Les trois pièces (`AccessKeyId`, `SecretKey`, `SessionToken`) arrivent ensemble de `GetCredentialsForIdentity` et se passent ensemble au signeur (`sessionToken` d'`AwsClient`).
- Usage : ✅ toujours passer le jeton avec des clés `ASIA` · ❌ copier seulement clé d'accès et secret depuis une sortie STS : la requête est refusée.

```python
# Exemple 1 : le jeton suit les clés STS
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

def signe(creds):
    r = AWSRequest(method="POST", data="{}",
        url="https://dynamodb.eu-west-3.amazonaws.com/")
    SigV4Auth(creds, "dynamodb", "eu-west-3").add_auth(r)
    return r.headers

h = signe(Credentials("ASIAEX", "s", "jeton"))
h["X-Amz-Security-Token"]  # → 'jeton'
"x-amz-security-token" in h["Authorization"]  # → True : signé
h2 = signe(Credentials("AKIAEX", "s"))
"X-Amz-Security-Token" in h2  # → False
```

- Quiz : Clé `ASIA…` et secret exportés, mais `AWS_SESSION_TOKEN` oublié. L'appel DynamoDB ?
- [ ] Passe : le secret suffit à signer
- [ ] Passe, en lecture seule
- [x] Refusé : jeton de sécurité invalide
- [ ] Passe jusqu'à l'expiration
- Réponse : refusé : une clé `ASIA` n'existe qu'avec son jeton de session ; sans lui, AWS ne la reconnaît pas (« The security token included in the request is invalid »).

## 4. requête non signée : MissingAuthenticationToken
- Id : api-erreurs-authentification
- Sous-thème : erreurs
- Type : concept
- Niveau : 1
- Profils : débutant, web, ops
- Mots-clés : SigV4, politique IAM
- Source : data-platform · pwa-sync
- Définition : Une requête sans `Authorization` vers une API qui l'exige reçoit `MissingAuthenticationTokenException`, avant tout contrôle IAM.
- Contexte : Le diagnostic se lit dans l'ordre : pas de signature → `MissingAuthenticationToken` ; signature avec une clé inconnue → `UnrecognizedClientException` ; signature mal formée ou périmée → `InvalidSignatureException` ; signature valide mais droit manquant → `AccessDeniedException`. Seul ce dernier concerne la politique IAM : inutile d'y chercher la cause des trois premiers.
- Usage : ✅ lire le code d'erreur avant de toucher aux politiques · ❌ élargir une politique IAM sur une erreur de signature : elle n'a jamais été évaluée.

```bash
# Exemple 1 : mesuré, sans signature
curl -s https://dynamodb.eu-west-3.amazonaws.com/ \
  -H 'content-type: application/x-amz-json-1.0' \
  -H 'x-amz-target: DynamoDB_20120810.Query' \
  -d '{"TableName":"t"}'
# → 400 {"__type":"com.amazon.coral.service
#   #MissingAuthenticationTokenException",
#   "message":"Request is missing
#   Authentication Token"}
```

- Quiz : Même requête, signée avec la clé de la doc `AKIAIOSFODNN7EXAMPLE`. Erreur ?
- [ ] `AccessDeniedException`
- [x] `UnrecognizedClientException`
- [ ] `MissingAuthenticationTokenException`
- [ ] `ResourceNotFoundException`
- Réponse : `UnrecognizedClientException` (mesuré) : la signature est là mais la clé n'existe pas (« The security token included in the request is invalid ») ; IAM n'est pas consulté.

## 5. protocole JSON : POST / et x-amz-target
- Id : api-protocole-json-target
- Sous-thème : protocole
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Mots-clés : endpoint, Cognito
- Source : data-platform · pwa-sync
- Définition : Les API JSON d'AWS (DynamoDB, Cognito, KMS) reçoivent un `POST /` ; l'en-tête `x-amz-target` nomme l'opération, le corps JSON porte ses paramètres.
- Contexte : Pas de route par opération comme en REST : l'URL est toujours la racine de l'endpoint régional (`https://dynamodb.eu-west-3.amazonaws.com/`). `x-amz-target` vaut `<préfixe du service>.<Opération>` : `DynamoDB_20120810.Query`, `AWSCognitoIdentityService.GetId`. Les paramètres JSON ont les noms exacts de la doc de l'API (`TableName`, `KeyConditionExpression`), en PascalCase.
- Usage : ✅ appeler une API AWS avec `fetch` en suivant la référence de l'API (section Request Syntax) · ❌ chercher une URL `/tables/progress/query` : elle n'existe pas.

```bash
# Exemple 1 : mesuré, appel public Cognito
curl -s https://cognito-identity.eu-west-3.amazonaws.com/ \
  -H 'content-type: application/x-amz-json-1.1' \
  -H 'x-amz-target: AWSCognitoIdentityService.GetId' \
  -d '{"IdentityPoolId":"eu-west-3:0000…"}'
# → 400 {"__type":"ResourceNotFoundException",
#   "message":"IdentityPool '…' not found."}
```

- Quiz : Requête DynamoDB signée, mais sans l'en-tête `x-amz-target`. Réponse ?
- [ ] DynamoDB lit l'opération dans le corps
- [x] `UnknownOperationException`
- [ ] `ValidationException` sur `TableName`
- [ ] 404 : aucune route
- Réponse : `UnknownOperationException` (mesuré, 400, sans message) : sans `x-amz-target`, le service ne sait pas quelle opération exécuter.

## 6. erreur JSON : __type et message
- Id : api-erreur-json-type
- Sous-thème : erreurs
- Type : recette
- Niveau : 1
- Profils : web
- Prérequis : api-protocole-json-target
- Mots-clés : botocore, boto3, SDK AWS
- Source : data-platform · pwa-sync
- Définition : Une erreur d'API JSON arrive en 4xx ou 5xx avec un corps `{"__type": …, "message": …}` ; le code utile termine `__type`.
- Contexte : DynamoDB préfixe le code (`com.amazon.coral.service#AccessDeniedException`), Cognito Identity non (`ResourceNotFoundException`) : on garde ce qui suit le dernier `#`. Le message s'écrit `message` ou `Message` selon le service : cloud.ts lit les deux, comme botocore. Le SDK fait cette normalisation (`err.name` en JS, `Error.Code` en boto3) ; avec `fetch`, c'est à vous.
- Usage : ✅ décider sur le code court (`ResourceNotFoundException` → rejouer, `AccessDeniedException` → abandonner) · ❌ comparer le `__type` complet ou le texte du message : ils varient d'un service à l'autre.

```python
# Exemple 1 : le code court, comme cloud.ts
import json
corps = ('{"__type": "com.amazon.coral.service'
         '#AccessDeniedException",'
         ' "message": "not authorized"}')
err = json.loads(corps)
err["__type"].split("#")[-1]
# → 'AccessDeniedException'
err.get("message") or err.get("Message")
# → 'not authorized'
```

- Quiz : Cognito renvoie `{"__type": "ResourceNotFoundException"}`. Que vaut `__type.split('#').pop()` en TS ?
- [ ] `undefined` : pas de `#`
- [ ] `''`
- [x] `'ResourceNotFoundException'`
- [ ] Une `TypeError`
- Réponse : `'ResourceNotFoundException'` : sans séparateur, `split` renvoie `[chaîne entière]` ; le même code traite les deux formes de `__type`.

## 7. Expiration : des secondes, pas des millisecondes
- Id : api-expiration-secondes
- Sous-thème : identifiants
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Prérequis : api-security-token
- Voir aussi : cognito-renouveler-cles-sts
- Mots-clés : STS, epoch, SDK AWS
- Source : data-platform · pwa-sync
- Définition : Dans le protocole JSON brut, `Expiration` des clés STS est un nombre de secondes depuis l'epoch ; JavaScript compte en millisecondes.
- Contexte : La CLI et les SDK convertissent en date lisible (`2026-10-25T12:00:00Z`), d'où la surprise avec `fetch` : on reçoit `1792929600`. `new Date(1792929600)` tombe en janvier 1970 ; il faut `* 1000`, comme `expiresAt: creds.Expiration * 1000` dans cloud.ts. Même piège pour les autres horodatages des API JSON (`CreationDateTime` de DynamoDB).
- Usage : ✅ convertir une fois à la réception, stocker en millisecondes à côté de `Date.now()` · ❌ comparer directement `Expiration` à `Date.now()`.

```python
# Exemple 1 : la valeur brute de l'API
from datetime import datetime, UTC
exp = 1792929600  # Expiration reçue
datetime.fromtimestamp(exp, UTC).isoformat()
# → '2026-10-25T12:00:00+00:00'
```

```js
// Exemple 2 : mesuré, Node 22
new Date(1792929600).toISOString()
// → '1970-01-21T18:02:09.600Z'
new Date(1792929600 * 1000).toISOString()
// → '2026-10-25T12:00:00.000Z'
```

- Quiz : On oublie `* 1000` : `Date.now() < Expiration - 60_000` vaut toujours… ?
- [ ] `true` : les clés ne sont jamais renouvelées
- [x] `false` : renouvelées à chaque requête
- [ ] `NaN`
- [ ] Ça dépend de l'heure
- Réponse : `false` (mesuré) : `Date.now()` (~1,8 × 10¹²) dépasse toujours ~1,8 × 10⁹ ; l'app refait `GetCredentialsForIdentity` avant chaque requête, sans erreur visible.

## 8. CORS : DynamoDB ouvert au navigateur
- Id : api-cors-endpoints
- Sous-thème : protocole
- Type : concept
- Niveau : 1
- Profils : web
- Mots-clés : CORS, préflight, endpoint, IAM
- Source : data-platform · pwa-sync
- Définition : Les endpoints de DynamoDB, Cognito Identity et STS répondent au préflight CORS avec `Access-Control-Allow-Origin: *` : une page peut les appeler en `fetch`.
- Contexte : Les en-têtes `authorization`, `x-amz-date`, `x-amz-security-token`, `x-amz-target` sont autorisés, seule la méthode `POST` l'est, et la réponse est mise en cache 48 h (`Max-Age: 172800`). La sécurité ne repose pas sur l'origine mais sur la signature et IAM. S3, lui, applique la configuration CORS de chaque bucket : sans règle, le préflight est refusé.
- Usage : ✅ app web qui parle directement à DynamoDB avec des clés Cognito · ❌ croire qu'une origine autorisée protège la table : n'importe quel site peut appeler, seule la signature compte.

```bash
# Exemple 1 : mesuré
curl -s -o /dev/null -D - -X OPTIONS \
  https://dynamodb.eu-west-3.amazonaws.com/ \
  -H 'Origin: http://localhost:5175' \
  -H 'Access-Control-Request-Method: POST'
# → 200, Access-Control-Allow-Origin: *
#   Access-Control-Allow-Methods: POST
#   Access-Control-Max-Age: 172800
```

- Quiz : Même préflight vers un bucket S3 sans configuration CORS. Résultat ?
- [ ] 200 avec `Allow-Origin: *`, comme DynamoDB
- [ ] 200, sans en-tête CORS
- [x] Refusé : S3 applique le CORS du bucket
- [ ] 301 vers l'endpoint global
- Réponse : refusé (mesuré : 403 sur l'endpoint S3) : le CORS de S3 se configure bucket par bucket (`aws_s3_bucket_cors_configuration`), il n'est pas ouvert par défaut.

## 9. SigV4 : une clé de signature dérivée
- Id : api-cle-signature-derivee
- Sous-thème : sigv4
- Type : concept
- Niveau : 2
- Profils : web, expert
- Prérequis : api-sigv4-portee
- Mots-clés : SigV4, HMAC, SHA-256, requête canonique
- Source : data-platform · pwa-sync
- Définition : La clé qui signe n'est pas le secret : c'est une chaîne de quatre HMAC sur la date, la région, le service puis `aws4_request`.
- Contexte : `kDate = HMAC("AWS4" + secret, date)`, puis `kRegion`, `kService`, `kSigning`. La signature finale est `HMAC(kSigning, chaîne à signer)`, en hexadécimal. Une clé dérivée fuitée ne vaut que pour ce jour, cette région, ce service. La chaîne à signer contient l'algorithme, l'horodatage, la portée et le SHA-256 de la requête canonique (méthode, chemin, en-têtes signés, hash du corps).
- Usage : ✅ comprendre une `InvalidSignatureException` (portée, date) et les implémentations (`aws4fetch`, botocore) · ❌ réimplémenter SigV4 en production : bibliothèque testée.

```python
# Exemple 1 : la dérivation, en Python
import hashlib, hmac

def h(cle, msg):
    return hmac.new(cle, msg.encode(),
                    hashlib.sha256).digest()

k = h(b"AWS4" + b"secret", "20261025")
k = h(k, "eu-west-3")
k = h(k, "dynamodb")
k = h(k, "aws4_request")
len(k)  # → 32 : 256 bits
```

- Quiz : Lequel de ces changements ne modifie pas la clé de signature (`kSigning`) ?
- [ ] La date du jour
- [ ] La région
- [ ] Le service
- [x] Le corps de la requête
- Réponse : le corps : il entre dans la chaîne à signer (dernier HMAC), pas dans la clé, qui ne dépend que du secret, du jour, de la région et du service.

## 10. horloge : 5 minutes de tolérance
- Id : api-horloge-tolerance
- Sous-thème : sigv4
- Type : piège
- Niveau : 2
- Profils : web, ops
- Prérequis : api-sigv4-portee
- Mots-clés : SigV4, rejeu
- Source : data-platform · pwa-sync
- Définition : `x-amz-date` est signée ; AWS refuse une requête dont l'heure s'écarte de plus de 5 minutes de la sienne.
- Contexte : La fenêtre empêche de rejouer longtemps une requête interceptée. Côté client, l'heure vient de l'appareil : une horloge de téléphone déréglée donne `InvalidSignatureException` « Signature expired » sur toutes les requêtes, alors que clés et droits sont bons. Le contrôle passe avant celui de la clé : le message dit l'écart, pas un problème de clé.
- Usage : ✅ lire « Signature expired » comme un problème d'horloge (appareil, conteneur, VM en veille) · ❌ renouveler les clés ou toucher IAM pour cette erreur.

```text
# Exemple 1 : mesuré, x-amz-date 20 min en retard
→ 400 InvalidSignatureException
  "Signature expired: 20261025T193000Z
   is now earlier than 20261025T194501Z
   (20261025T195001Z - 5 min.)"
```

- Quiz : Horloge de l'appareil en retard de 4 minutes, clés valides. La requête ?
- [x] Passe : on reste dans la fenêtre
- [ ] `Signature expired`
- [ ] `ExpiredTokenException`
- [ ] Passe, avec un avertissement
- Réponse : passe (mesuré : un retard de 4 min franchit le contrôle d'heure) : la tolérance est de 5 min dans les deux sens.

## 11. SignedHeaders : ce que couvre la signature
- Id : api-signedheaders
- Sous-thème : sigv4
- Type : concept
- Niveau : 2
- Profils : web
- Mots-clés : SigV4, botocore, aws4fetch
- Source : data-platform · pwa-sync
- Définition : `SignedHeaders` liste les en-têtes inclus dans la signature ; les autres peuvent changer sans l'invalider, ceux-là non.
- Contexte : `host` et `x-amz-date` sont toujours signés, `x-amz-security-token` et `x-amz-target` aussi quand ils sont là. Chaque signeur choisit le reste : botocore signe `content-type`, `aws4fetch` l'exclut (avec `user-agent`, `range`… que les navigateurs ou proxys réécrivent). Modifier un en-tête signé après `sign()` donne une signature fausse.
- Usage : ✅ fixer tous les en-têtes avant de signer, puis envoyer la requête telle quelle · ❌ ajouter ou réécrire `x-amz-target` après la signature.

```text
# Exemple 1 : mesuré, même requête DynamoDB
botocore  : SignedHeaders=content-type;
  host;x-amz-date;x-amz-security-token;
  x-amz-target
aws4fetch : SignedHeaders=host;
  x-amz-date;x-amz-security-token;
  x-amz-target
```

- Quiz : On ajoute `x-trace: 42` à la requête après `sign()`, sans resigner. Refus ?
- [x] Non : l'en-tête n'est pas dans `SignedHeaders`
- [ ] Oui : tout en-tête ajouté casse la signature
- [ ] Oui, seulement pour DynamoDB
- [ ] Non, mais AWS le supprime
- Réponse : non : AWS ne recalcule la signature qu'avec les en-têtes listés dans `SignedHeaders` ; un en-tête hors liste n'y entre pas.

## 12. corps signé : un octet de plus, refus
- Id : api-corps-signe
- Sous-thème : sigv4
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : api-signedheaders
- Mots-clés : SigV4, SHA-256, requête canonique
- Source : data-platform · pwa-sync
- Définition : Le SHA-256 du corps entre dans la requête canonique : le corps envoyé doit être exactement celui qui a été signé, octet pour octet.
- Contexte : Deux JSON équivalents ne sont pas les mêmes octets : `json.dumps` de Python met des espaces, `JSON.stringify` non. D'où, dans cloud.ts, `JSON.stringify(body)` passé à `sign()` puis la `Request` signée envoyée sans retoucher : on ne resérialise jamais entre signature et envoi.
- Usage : ✅ sérialiser une fois, signer, envoyer la requête signée · ❌ reconstruire le corps après la signature (formatage, ajout d'un champ, middleware qui réécrit).

```python
# Exemple 1 : même objet, autres octets
import hashlib, json
corps = {"TableName": "progress"}
py = json.dumps(corps)
js = '{"TableName":"progress"}'  # JSON.stringify
py == js  # → False : espace après « : »

def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:8]

h(js)  # → '5f98d279'
h(py) == h(js)  # → False
```

- Quiz : On signe, puis on ajoute `ReturnConsumedCapacity` au corps avant `fetch`. Réponse d'AWS ?
- [ ] 200 : le corps n'est pas signé
- [x] `InvalidSignatureException`
- [ ] `ValidationException`
- [ ] 200, champ ignoré
- Réponse : `InvalidSignatureException` : AWS hache le corps reçu, la requête canonique diffère, la signature recalculée ne correspond plus.

## 13. json 1.0 ou 1.1 : le content-type du service
- Id : api-json-content-type
- Sous-thème : protocole
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : api-protocole-json-target
- Mots-clés : content-type, botocore
- Source : data-platform · pwa-sync
- Définition : Chaque API JSON attend son `content-type` : `application/x-amz-json-1.0` pour DynamoDB, `1.1` pour Cognito, KMS ou CloudWatch Logs.
- Contexte : La version est fixée par le service, pas par vous : elle se lit dans le modèle de l'API (champ `jsonVersion`, avec `targetPrefix` pour `x-amz-target`). Les modèles sont dans botocore et dans la doc. C'est pour cela que cloud.ts écrit `1.1` pour `cognito-identity` et `1.0` pour `dynamodb`.
- Usage : ✅ lire `jsonVersion` et `targetPrefix` dans le modèle botocore avant d'appeler un service en `fetch` · ❌ mettre `application/json` ou copier la version d'un autre service.

```python
# Exemple 1 : lu dans les modèles botocore
from botocore.loaders import Loader

def meta(svc):
    m = Loader().load_service_model(
        svc, "service-2")["metadata"]
    return m["jsonVersion"], m["targetPrefix"]

meta("dynamodb")
# → ('1.0', 'DynamoDB_20120810')
meta("cognito-identity")
# → ('1.1', 'AWSCognitoIdentityService')
```

- Quiz : Quel protocole utilise aujourd'hui l'API SQS (`SendMessage`), d'après botocore ?
- [ ] Query : paramètres en formulaire, réponse XML
- [x] JSON 1.0, préfixe `AmazonSQS`
- [ ] JSON 1.1, préfixe `AmazonSQS`
- [ ] REST-JSON, une route par file
- Réponse : JSON 1.0 (mesuré, botocore 1.43) : SQS a quitté le protocole Query ; un vieux tutoriel avec `Action=SendMessage` décrit l'ancien format.

## 14. protocoles : json, rest-json, rest-xml, query
- Id : api-protocoles-services
- Sous-thème : protocole
- Type : comparaison
- Niveau : 2
- Profils : web
- Prérequis : api-protocole-json-target
- Mots-clés : SigV4, REST, botocore, STS
- Source : data-platform · pwa-sync
- Définition : Les API AWS n'ont pas toutes le même format : JSON par `x-amz-target`, REST-JSON par routes, REST-XML (S3), Query en formulaire (STS, IAM, SNS).
- Contexte : SigV4 est commun à tous, le reste change : DynamoDB, Cognito, KMS = `json` (`POST /`) ; Lambda = `rest-json` (`POST /2015-03-31/functions/<nom>/invocations`) ; S3 = `rest-xml` (méthode HTTP et clé dans l'URL, réponses XML) ; STS, IAM, SNS = `query` (`Action=AssumeRole&…`, réponses XML). Le champ `protocol` du modèle botocore le dit.
- Usage : ✅ vérifier le protocole avant d'écrire un appel `fetch` à un nouveau service · ❌ supposer que le code DynamoDB de cloud.ts marche tel quel pour S3 ou STS.

```python
# Exemple 1 : lu dans les modèles botocore
from botocore.loaders import Loader

def protocole(svc):
    m = Loader().load_service_model(
        svc, "service-2")["metadata"]
    return m["protocol"]

protocole("dynamodb")  # → 'json'
protocole("lambda")    # → 'rest-json'
protocole("s3")        # → 'rest-xml'
```

- Quiz : Appeler `AssumeRole` de STS en `fetch` : quel format de requête ?
- [ ] JSON, `x-amz-target: STS.AssumeRole`
- [x] Formulaire `Action=AssumeRole`, réponse XML
- [ ] REST-JSON, `POST /roles/assume`
- [ ] XML dans le corps, comme S3
- Réponse : formulaire (mesuré : protocole `query` dans botocore) : `Action=AssumeRole&Version=2011-06-15&…`, réponse en XML.

## 15. identifiants en cache : liés à l'utilisateur
- Id : api-cache-par-utilisateur
- Sous-thème : identifiants
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : api-security-token
- Mots-clés : identity id, STS, sub, id token
- Source : data-platform · pwa-sync
- Définition : Un cache d'identity id ou de clés STS se rattache à l'utilisateur (`sub` du jeton) : un autre compte sur l'appareil repart de zéro.
- Contexte : cloud.ts garde `{sub, identityId}` dans le stockage et `session.sub` en mémoire ; à chaque ouverture il relit le `sub` de l'id token et compare. Sans cette clé, le compte B réutiliserait l'identity id ou les clés du compte A : au mieux un refus, au pire des écritures dans la partition de A tant que ses clés vivent.
- Usage : ✅ cache clé = identité (sub, utilisateur, rôle), invalidé à la déconnexion · ❌ cache global « les clés » sans propriétaire, ou clé = le jeton entier (change à chaque renouvellement).

```python
# Exemple 1 : cache rattaché au sub
cache = {}

def identite(sub, get_id):
    if cache.get("sub") != sub:
        cache.update(sub=sub, id=get_id())
    return cache["id"]

ids = iter(["eu-west-3:a", "eu-west-3:b"])
identite("sub-1", lambda: next(ids))
# → 'eu-west-3:a'
identite("sub-1", lambda: next(ids))
# → 'eu-west-3:a'  (pas de GetId)
identite("sub-2", lambda: next(ids))
# → 'eu-west-3:b'
```

- Quiz : Cache indexé par l'id token entier plutôt que par `sub`. Conséquence ?
- [ ] Fuite entre comptes
- [x] Un échange de plus à chaque nouveau jeton
- [ ] Aucune : le jeton identifie l'utilisateur
- [ ] Erreur à chaque renouvellement
- Réponse : un échange de plus : l'id token change à chaque renouvellement (1 h), le cache est perdu alors que l'utilisateur est le même ; `sub`, lui, est stable.

## 16. erreur de cache : oublier, réessayer une fois
- Id : api-cache-retry-unique
- Sous-thème : identifiants
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : api-cache-par-utilisateur
- Voir aussi : api-promesse-partagee
- Mots-clés : identity id, identity pool, localStorage
- Source : data-platform · pwa-sync
- Définition : Une valeur en cache refusée par un code précis (`ResourceNotFoundException`) est effacée et redemandée une seule fois ; toute autre erreur remonte.
- Contexte : Cas de cloud.ts : un identity id gardé dans `localStorage` alors que le pool a été recréé. `GetCredentialsForIdentity` répond `ResourceNotFoundException` : on oublie l'id, on refait `GetId`, puis on réessaie. Le filtrage par code est essentiel : réessayer un `AccessDeniedException` ou une erreur réseau ne ferait que répéter l'échec, voire boucler.
- Usage : ✅ cache périmé reconnaissable à un code précis · ❌ `catch` générique qui vide le cache et rejoue : boucle ou appels inutiles sur une vraie panne.

```python
# Exemple 1 : une seule nouvelle tentative
class Introuvable(Exception):
    pass

cache = {"id": "eu-west-3:ancienne"}
vus = []

def cles(retente=True):
    ident = cache.get("id") or "eu-west-3:neuve"
    vus.append(ident)
    if ident.endswith("ancienne"):
        if not retente:
            raise Introuvable
        cache.pop("id")
        return cles(retente=False)
    return "clés"

cles()  # → 'clés'
len(vus)  # → 2
```

- Quiz : Pourquoi ne pas rejouer aussi sur `AccessDeniedException` ?
- [ ] Le jeton serait révoqué
- [x] Même requête, même politique : même refus
- [ ] AWS bloque l'identité après deux refus
- [ ] Le cache ne serait pas effacé
- Réponse : même refus : un `AccessDenied` vient de la politique IAM, pas d'une valeur périmée ; rejouer ne change rien et masque la vraie cause.

## 17. aws4fetch ou SDK v3 : choisir
- Id : api-aws4fetch-ou-sdk
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : web
- Mots-clés : aws4fetch, SDK AWS, PWA, pagination
- Source : data-platform · pwa-sync
- Définition : `aws4fetch` signe seulement une requête `fetch` (quelques Ko) ; le SDK v3 sérialise, convertit, réessaie et pagine (60 à 80 Ko).
- Contexte : Dans une PWA, chaque Ko compte au premier chargement : l'app ne fait que deux opérations DynamoDB et deux appels Cognito publics, `aws4fetch` + `fetch` suffit. En échange, tout est à votre charge : JSON brut au format typé de DynamoDB (`{"S": "…"}`), codes d'erreur, pagination (`LastEvaluatedKey`), retries. Côté serveur (Lambda), la taille compte peu : le SDK.
- Usage : ✅ `aws4fetch` : front léger, peu d'opérations, formats simples · ❌ nombreuses opérations, pagination, retries fins : SDK v3 (`@aws-sdk/client-dynamodb`, `lib-dynamodb`).

```text
# Exemple 1 : ce que fait chacun
             aws4fetch    SDK v3
signature    oui          oui
JSON typé    à la main    lib-dynamodb
pagination   à la main    paginateQuery
retries      5xx/429      adaptatifs
taille       ~3 Ko        60-80 Ko
```

- Quiz : Avec `aws4fetch`, qui convertit `{"sk": {"S": "carte#1"}}` en `{"sk": "carte#1"}` ?
- [x] Votre code
- [ ] `aws4fetch`, à la réception
- [ ] DynamoDB, si `content-type` est JSON
- [ ] Le navigateur
- Réponse : votre code : `aws4fetch` signe et rend la `Response` telle quelle ; la conversion des types DynamoDB est le rôle de `lib-dynamodb` dans le SDK.

## 18. x-amzn-RequestId : la trace d'un appel
- Id : api-request-id
- Sous-thème : erreurs
- Type : recette
- Niveau : 2
- Profils : web, ops
- Prérequis : api-erreur-json-type
- Mots-clés : CloudTrail, SDK AWS, boto3
- Source : data-platform · pwa-sync
- Définition : Chaque réponse d'API AWS porte `x-amzn-RequestId`, l'identifiant de la requête côté AWS, à journaliser avec l'erreur.
- Contexte : C'est la clé pour retrouver l'appel dans CloudTrail ou la donner au support. Les endpoints JSON l'exposent au navigateur via `Access-Control-Expose-Headers` (avec `x-amzn-ErrorType`) : un `fetch` peut le lire. Les SDK le rangent dans `$metadata.requestId` (JS) ou `ResponseMetadata.RequestId` (boto3).
- Usage : ✅ joindre le RequestId au log d'une erreur AWS · ❌ ne journaliser que le message : impossible de relier l'erreur à un appel précis.

```text
# Exemple 1 : mesuré, préflight DynamoDB
Access-Control-Expose-Headers:
  x-amzn-RequestId,x-amzn-ErrorType,
  x-amzn-ErrorMessage,Date,
  smithy-protocol
```

- Quiz : Dans un `fetch` du navigateur vers DynamoDB, `res.headers.get('x-amzn-RequestId')` vaut ?
- [ ] `null` : CORS masque les en-têtes non standards
- [x] L'identifiant de la requête
- [ ] `null`, sauf avec `credentials: 'include'`
- [ ] Une erreur CORS
- Réponse : l'identifiant (mesuré dans Chromium, même sur un 400) : l'en-tête figure dans `Access-Control-Expose-Headers` ; un en-tête non exposé, lui, vaudrait `null`.

## 19. content-type faux : un 200 trompeur
- Id : api-content-type-200-trompeur
- Sous-thème : erreurs
- Type : piège
- Niveau : 3
- Profils : web, expert
- Prérequis : api-json-content-type
- Mots-clés : content-type, Cognito
- Source : data-platform · pwa-sync
- Définition : Avec `content-type: application/json` au lieu de `x-amz-json-1.x`, Cognito répond HTTP 200 avec l'erreur cachée dans `Output.__type`.
- Contexte : Le service bascule sur un autre protocole et enveloppe sa réponse : `{"Output": {"__type": "…UnknownOperationException"}, "Version": "1.0"}`. `res.ok` vaut `true` : un code qui ne teste que le statut croit au succès et lit `IdentityId` → `undefined`. D'où l'intérêt de valider la forme attendue de la réponse, pas seulement le statut.
- Usage : ✅ content-type exact du service, et contrôle d'un champ attendu après un 200 · ❌ `application/json` « parce que c'est du JSON ».

```bash
# Exemple 1 : mesuré
curl -s -w ' %{http_code}' \
  https://cognito-identity.eu-west-3.amazonaws.com/ \
  -H 'content-type: application/json' \
  -H 'x-amz-target: AWSCognitoIdentityService.GetId' \
  -d '{"IdentityPoolId":"eu-west-3:0000…"}'
# → {"Output":{"__type":"com.amazon.coral
#   .service#UnknownOperationException",
#   "message":null},"Version":"1.0"} 200
```

- Quiz : Avec ce content-type, que renvoie `parse()` de cloud.ts pour `GetId` ?
- [ ] Une `CloudError('UnknownOperationException')`
- [x] Un objet sans `IdentityId`, sans erreur
- [ ] Une `SyntaxError` JSON
- [ ] `ResourceNotFoundException`
- Réponse : un objet sans `IdentityId` : `res.ok` est vrai, `parse` rend le JSON tel quel ; l'erreur ressort plus loin, `IdentityId` vaut `undefined`.

## 20. retries : aws4fetch.fetch ne voit pas le throttling
- Id : api-aws4fetch-retries
- Sous-thème : erreurs
- Type : piège
- Niveau : 3
- Profils : web, expert
- Prérequis : api-aws4fetch-ou-sdk
- Voir aussi : dynamodb-backoff-jitter
- Mots-clés : throttling, backoff exponentiel, retry
- Source : data-platform · pwa-sync
- Définition : `AwsClient.fetch` réessaie seulement les réponses 5xx et 429 ; le throttling de DynamoDB arrive en HTTP 400 et n'est pas réessayé.
- Contexte : DynamoDB signale la surcharge par `ThrottlingException` ou `ProvisionedThroughputExceededException`, en 400 comme une erreur de validation : seul `__type` les distingue. Le SDK les reconnaît par code et réessaie avec backoff. cloud.ts appelle `sign()` puis son propre `fetch` : aucun retry du tout ; c'est l'outbox de la synchro qui rejoue plus tard.
- Usage : ✅ décider du retry sur le code (`__type`), backoff exponentiel avec aléa · ❌ compter sur le statut HTTP seul pour reconnaître une erreur transitoire AWS.

```js
// Exemple 1 : la boucle d'aws4fetch (extrait)
for (let i = 0; i <= this.retries; i++) {
  const res = await fetch(await this.sign(…))
  if (res.status < 500 && res.status !== 429)
    return res  // 400 Throttling : rendu tel quel
  await sleep(Math.random() * 50 * 2 ** i)
}
```

- Quiz : `AwsClient` par défaut (`retries: 10`), un service qui répond toujours 503. Combien de requêtes ?
- [ ] 10
- [x] 11
- [ ] 1 : pas de retry par défaut
- [ ] Sans limite
- Réponse : 11 : la boucle va de `i = 0` à `i = retries` inclus, soit une tentative plus 10 nouvelles, et la dernière réponse est rendue.

## 21. clé de signature : valable toute la journée
- Id : api-cle-signature-cache
- Sous-thème : sigv4
- Type : concept
- Niveau : 3
- Profils : expert
- Prérequis : api-cle-signature-derivee
- Mots-clés : aws4fetch, STS, HMAC
- Source : data-platform · pwa-sync
- Définition : `kSigning` ne dépend que du secret, du jour, de la région et du service : calculée une fois par jour, réutilisée ensuite.
- Contexte : `aws4fetch` la garde dans une `Map` indexée par `[secret, date, région, service]` : quatre HMAC économisés par requête. Le cache vit dans l'`AwsClient` : cloud.ts en crée un nouveau à chaque renouvellement des clés STS (nouveau secret), donc le cache repart, ce qui est correct. botocore, lui, recalcule à chaque fois.
- Usage : ✅ réutiliser un même client signeur tant que les clés ne changent pas · ❌ recréer un `AwsClient` par requête : chaque appel refait toute la dérivation.

```python
# Exemple 1 : la clé dépend du jour, pas de la requête
import hashlib, hmac

def h(c, m):
    return hmac.new(c, m.encode(), hashlib.sha256).digest()

def k_signing(secret, jour):
    k = h(("AWS4" + secret).encode(), jour)
    for part in ("eu-west-3", "dynamodb", "aws4_request"):
        k = h(k, part)
    return k

k_signing("s", "20261025") == k_signing("s", "20261025")  # → True
k_signing("s", "20261025") == k_signing("s", "20261026")  # → False
```

- Quiz : Deux requêtes le même jour, corps différents, même client. Que recalcule `aws4fetch` ?
- [ ] Toute la chaîne de HMAC
- [x] Le hash de la requête et le dernier HMAC
- [ ] Rien : la signature est en cache
- [ ] Seulement `kDate`
- Réponse : le hash et le dernier HMAC : `kSigning` vient du cache, mais la chaîne à signer (corps, date à la seconde) change à chaque requête.

## 22. appels simultanés : partager la promesse en vol
- Id : api-promesse-partagee
- Sous-thème : identifiants
- Type : recette
- Niveau : 3
- Profils : web, expert
- Prérequis : api-cache-par-utilisateur
- Mots-clés : promesse, Cognito, STS
- Source : data-platform · pwa-sync
- Définition : Deux requêtes lancées ensemble sans clés en cache déclenchent deux échanges ; garder la promesse en cours et la partager n'en fait qu'un.
- Contexte : Le test `session &&` ne protège que si le premier échange est terminé. Au démarrage, un `Promise.all([query, query])` voit `session` à `null` deux fois et lance deux `GetId` puis deux `GetCredentialsForIdentity`. Rien de faux, mais des appels en double et deux jeux de clés. Le remède : mémoriser la promesse (`pending ??= open()`), la vider à la fin.
- Usage : ✅ dédoublonner tout rafraîchissement partagé (jetons, clés, config) · ❌ mettre un verrou ou un booléen « en cours » sans rendre le résultat aux appelants suivants.

```python
# Exemple 1 : une seule demande pour deux appels
import asyncio

n = {"echanges": 0}
en_vol = {}

async def echange():
    n["echanges"] += 1
    await asyncio.sleep(0)
    return "clés"

async def ouvrir():
    if "p" not in en_vol:
        en_vol["p"] = asyncio.ensure_future(echange())
    return await en_vol["p"]

async def main():
    return await asyncio.gather(ouvrir(), ouvrir())
asyncio.run(main())  # → ['clés', 'clés']
n["echanges"]  # → 1
```

- Quiz : cloud.ts tel quel, premier lancement : `Promise.all([dynamo(…), dynamo(…)])`. Combien de `GetId` ?
- [ ] 1 : `session` est partagée
- [x] 2 : rien ne partage l'échange en cours
- [ ] 0 : l'identity id est déjà stocké
- [ ] 1 : le second attend le stockage
- Réponse : 2 (mesuré avec le faux AWS de cloud.test.ts : 2 `GetId`, 2 `GetCredentialsForIdentity`) : les deux appels passent le test `session` avant la fin du premier.
