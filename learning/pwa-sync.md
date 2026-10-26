---
card: "revision-pwa · progression synchronisée entre appareils"
id_short: aucun
learning_id: pwa-sync
board: fMaiYRrn
url: aucune
created: 2026-10-25
updated: 2026-10-25
status: en-cours
---

# revision-pwa · progression synchronisée entre appareils
Liste : hors board (suite de `pwa-revision`) · Échéance : aucune · Étiquettes : front, Terraform, AWS, IAM, DynamoDB

## Objectif
Aujourd'hui la progression de l'app (cartes vues, temps passé, réponses au quiz) vit dans le `localStorage` de chaque appareil : l'iPhone et le Mac ne se voient pas, et vider Safari efface tout. À la fin de ce cours, un utilisateur connecté retrouve la même progression sur tous ses appareils, au moindre coût : l'app parle **directement** à DynamoDB avec des identifiants AWS temporaires donnés par un Cognito Identity Pool, sans API Gateway ni Lambda, et IAM garantit que chacun ne lit et n'écrit que ses propres lignes — Pourquoi ça compte : c'est le schéma « client riche + IAM fin » qu'on retrouve en entreprise pour les apps mobiles, et la synchro hors ligne (outbox, fusion sans conflit) est le même problème que l'ingestion idempotente côté data.

### Décisions du 2026-10-25
- **DynamoDB plutôt qu'un JSON par utilisateur dans S3** : un JSON unique impose lire → fusionner → écrire avec `If-Match` et des réessais quand deux appareils écrivent en même temps ; dans DynamoDB chaque fait est une ligne (`pk = identity id`, `sk = R#…`, `V#…`, `T#…`), deux appareils écrivent des lignes différentes et ne s'écrasent jamais.
- **Identity Pool + `dynamodb:LeadingKeys`** : l'isolation entre utilisateurs est faite par IAM (condition sur la clé de partition = `${cognito-identity.amazonaws.com:sub}`), pas par du code serveur. Coût : Identity Pool gratuit, DynamoDB à la demande ≈ 1,4 $ par million d'écritures (une session ≈ 7 requêtes).
- **Local d'abord** : l'écran lit et écrit toujours le `localStorage` (instantané, hors ligne) ; une outbox garde ce qui n'est pas encore envoyé ; la synchro tourne en arrière-plan (envoi groupé 5 s après la dernière action, à la mise en arrière-plan, au retour du réseau ; lecture à l'ouverture et au retour au premier plan).
- **Pas d'API à nous devant la table (décidé après l'étape 2)** : l'app appelle déjà une API HTTP, celle de DynamoDB (`POST` JSON + `x-amz-target`, signé SigV4). Une API Gateway + Lambda apporterait validation serveur et schéma masqué, au prix d'une infra et d'un code en plus ; pour une app perso où le seul risque est qu'un utilisateur triche sur ses propres stats, l'accès direct suffit. Bascule possible plus tard sans toucher à la table ni au modèle des lignes.
- **`localStorage` et non IndexedDB** : l'app l'utilise déjà partout (`progress.ts`, lecture synchrone), l'outbox tient en quelques Ko ; IndexedDB n'apporterait que de l'asynchrone partout.

## Prérequis
### Cognito : user pool ≠ identity pool
Le **user pool** (déjà en place, `infra/auth.tf`) répond à « qui es-tu ? » : e-mail + mot de passe → jetons JWT (id token, access token). L'**identity pool** répond à « qu'as-tu le droit de faire dans AWS ? » : il prend l'id token, attribue à l'utilisateur un **identity id** stable (`eu-west-3:1b2c…`), et échange le jeton contre des **identifiants AWS temporaires** (STS, 1 h) d'un rôle IAM. Analogie TS : le user pool, c'est NextAuth ; l'identity pool, c'est l'étape qui transforme la session en clé d'API AWS à durée limitée.
Doc : https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html · https://docs.aws.amazon.com/cognito/latest/developerguide/authentication-flow.html
Exercice 5 min : dans la doc « authentication flow », repérer les deux appels du flux « enhanced » (`GetId`, `GetCredentialsForIdentity`) et noter ce que chacun reçoit et renvoie.

### DynamoDB : clé de partition, clé de tri, Query
Une table DynamoDB est un grand dictionnaire trié : chaque ligne a une **clé de partition** (`pk`, qui regroupe) et une **clé de tri** (`sk`, qui ordonne dans le groupe). `Query` lit un seul `pk`, éventuellement une plage de `sk` (`BETWEEN`, `begins_with`) ; `Scan` lit toute la table (à éviter). En mode `PAY_PER_REQUEST`, aucune capacité à réserver : on paie chaque lecture et écriture.
Doc : https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html · https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table
Exercice 5 min : pour la table de la progression (`pk` = utilisateur, `sk` = `R#<date>#<carte>`), écrire la condition de `Query` qui lit les réponses d'un utilisateur depuis le 1er octobre.

### IAM : variables de politique et `dynamodb:LeadingKeys`
Une politique IAM peut contenir des **variables** remplacées au moment de la requête : `${cognito-identity.amazonaws.com:sub}` vaut l'identity id de l'appelant. La condition `dynamodb:LeadingKeys` porte sur les clés de partition touchées par la requête : `ForAllValues:StringEquals` + la variable = « toutes les lignes touchées ont `pk` = moi ». En Terraform, `$${…}` écrit un `${…}` littéral (sinon Terraform tente de l'interpoler).
Doc : https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html · https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_variables.html
Exercice 5 min : dans la première doc, trouver pourquoi `ForAllValues` laisse passer une requête qui ne porte **aucune** clé (ex. `Scan`), et ce que ça impose sur la liste `actions`.

## Étapes
### [x] Étape 1 — Table DynamoDB, identity pool et rôle « une partition par utilisateur »
- À faire : c'est quoi : la partie AWS de la synchro, sans une ligne d'app. Pourquoi ici : tout le reste (app, outbox) suppose qu'un utilisateur connecté peut obtenir des identifiants qui n'ouvrent **que** ses lignes. Objectif : après `make up`, depuis la CLI, un utilisateur lit sa partition et se fait refuser celle d'un autre.
  1. `infra/progress.tf` : table `revision-pwa-dev-progress` (`pk`/`sk` en chaînes, `PAY_PER_REQUEST`, protection et PITR en prod seulement).
  2. Identity pool `revision-pwa-dev-identities` branché sur le user pool et le client de l'app, sans identités invitées, sans flux « classic ».
  3. Rôle `revision-pwa-dev-progress-user` : confiance `cognito-identity.amazonaws.com` limitée à ce pool et aux identités authentifiées ; droits `dynamodb:Query` et `dynamodb:BatchWriteItem` sur la table, condition `LeadingKeys` ; rattaché au pool comme rôle `authenticated`.
  4. Outputs `identity_pool_id` et `progress_table`, variables `VITE_IDENTITY_POOL_ID` / `VITE_PROGRESS_TABLE` dans CodeBuild et `make auth-env`.
  5. `make plan` (lire : ce qui est ajouté, ce qui change), puis `make up` par toi.
- Concept : identity pool (jeton → identifiants STS), rôle à confiance fédérée (`AssumeRoleWithWebIdentity`, conditions `aud` et `amr`), variable de politique, `LeadingKeys`.
- Indice : `provider_name` du pool = `aws_cognito_user_pool.this.endpoint` (`cognito-idp.<région>.amazonaws.com/<pool id>`). Ne jamais ajouter `Scan` ni `*` dans les actions : `ForAllValues` sur une requête sans clé est vrai. Les 2 changements du plan : CodeBuild reçoit 2 variables, la politique `events` est relue (contenu identique). Le script lance d'abord une `Query` sur sa partition (un nombre), puis sur une autre et un `Scan` (deux `AccessDeniedException`).
- Vérifier : `make plan` → `5 to add, 2 to change, 0 to destroy` ; `tools/progress-access-test.sh <ton e-mail>` → `OK : isolation vérifiée`
- Cours : deux pools Cognito, deux questions. Le user pool dit « qui es-tu » (id token JWT) ; l'identity pool dit « que peux-tu faire dans AWS » : il donne un identity id stable par compte (`eu-west-3:…`, différent du `sub` du user pool) et échange l'id token contre des identifiants STS d'une heure du rôle `authenticated`. Deux appels publics, sans signature : `GetId` puis `GetCredentialsForIdentity` (flux « enhanced », le pool choisit le rôle).
- Cours : confiance du rôle = qui peut l'endosser : principal fédéré `cognito-identity.amazonaws.com`, `aud` = ce pool (un autre pool du compte ne passe pas), `amr` contient `authenticated` (pas d'invité). Droits du rôle = ce qu'il peut faire : `Query` et `BatchWriteItem`, seulement si toutes les clés de partition touchées valent `${cognito-identity.amazonaws.com:sub}`, variable que IAM remplace à chaque requête par l'identity id de l'appelant (`$$` dans Terraform pour l'écrire tel quel).
- Cours : `ForAllValues` sur un ensemble vide est vrai : une requête sans clé de partition (`Scan`) passerait la condition. La protection vient donc aussi de la liste `actions`, qui ne contient ni `Scan` ni `*`.
- Cours : un refus par condition ne dit pas « condition non remplie » : le message est `no identity-based policy allows the dynamodb:Query action`, le même que si l'action n'était pas accordée.
- Question : à quoi sert le `$$` devant `{cognito-identity.amazonaws.com:sub}` ? → sans lui Terraform chercherait une variable à lui ; avec, il écrit `${…}` dans le JSON et c'est IAM qui la remplace à chaque requête.
- Erreur vue : 1er run du script, ligne `1.` vide puis `OK : isolation vérifiée` → le script ne vérifiait que les refus ; il capture désormais `Count = N` et échoue si ce n'est pas un nombre (`AWS_PAGER=""` en plus).
- Résultat : `make up` (5 ajoutés, 2 modifiés) ; `tools/progress-access-test.sh` : sa partition `Count = 0`, partition d'un autre et `Scan` → `AccessDeniedException` (`assumed-role/revision-pwa-dev-progress-user/CognitoIdentityCredentials`), `OK : isolation vérifiée`.
- Cartes : +16 AWS / Cognito (16, nouveau thème), +11 AWS / IAM (47), +17 AWS / DynamoDB (18), +7 Terraform / Langage HCL (41), source `data-platform · pwa-sync` (publiées)

### [x] Étape 2 — Identifiants AWS dans l'app : `cloud.ts`
- À faire : l'app obtient l'identity id et des identifiants STS depuis l'id token (`GetId`, `GetCredentialsForIdentity`, appels `fetch` comme `auth.ts`), les garde jusqu'à 1 min avant expiration, et signe ses requêtes DynamoDB (SigV4, `aws4fetch`). Tests Vitest avec `fetch` simulé.
- Concept : signature SigV4, CORS des endpoints AWS, cache d'identifiants.
- Vérifier : `pnpm --dir app test` → vert ; Mon compte, app connectée → `Synchro : 0 ligne en ligne`
- Cours : SigV4 = une signature HMAC-SHA256 de la requête (méthode, URL, en-têtes, corps, date) avec la clé secrète temporaire ; l'en-tête `Authorization: AWS4-HMAC-SHA256 Credential=<clé>/<date>/<région>/<service>/aws4_request` et `x-amz-security-token` accompagnent l'appel. `aws4fetch` (≈ 3 Ko) la calcule avec `crypto.subtle`, au lieu de `@aws-sdk/*` (60-80 Ko).
- Cours : `crypto.subtle` n'existe qu'en contexte sécurisé (HTTPS ou `localhost`) : l'app ouverte sur l'iPhone via `http://192.168.x.x` ne peut pas signer ; on mesure sur le Mac en local, puis sur l'iPhone après déploiement.
- Cours : clés STS en mémoire seulement, renouvelées une minute avant expiration ; identity id gardé dans `localStorage` mais lié au `sub` du compte (un autre compte sur l'appareil refait `GetId`) ; une identité disparue du pool (`ResourceNotFoundException`) est oubliée et redemandée une fois.
- Cours : le client est construit par une fabrique (`createCloud`) qui reçoit `fetch` et le stockage : les tests injectent un faux AWS à la forme exacte des réponses JSON, sans réseau.
- Question : pourquoi pas une REST API devant la table ? → l'app appelle déjà une API HTTP, celle de DynamoDB ; une API à nous servirait à valider côté serveur et masquer le schéma, inutile ici (décision du 2026-10-25).
- Erreur vue : 1er build CodeBuild `ReferenceError: localStorage is not defined` (`src/cloud.ts:61`) → en CI les `VITE_*` sont définies, le client était créé à l'import et lisait `localStorage` sous Node ; reproduit en local avec les mêmes variables, stockage lu à l'usage.
- Erreur vue : relecture par l'agent des cartes, deux appels simultanés (`Promise.all`) → deux `GetId` et deux `GetCredentialsForIdentity` → une seule ouverture en cours, partagée (`ensure`), test ajouté (52 tests).
- Résultat : `cloud.ts` + 7 tests (44 au total) ; Mac `localhost:5175`, Mon compte → `Synchro : 0 ligne en ligne` ; commits `0f9362c`, `37bb9ef` poussés, build CodeBuild `SUCCEEDED` (mesure iPhone reportée à l'étape 4, avec de vraies lignes).
- Cartes : +22 AWS / API (22), +15 Web / Web Crypto (15), +10 Web / Vite (11), source `data-platform · pwa-sync` (publiées)

### [x] Étape 3 — Modèle des lignes et outbox dans `progress.ts`
- À faire : un `deviceId` par appareil ; chaque écriture locale (`markSeen`, `addTime`, `recordAnswer`) dépose aussi sa ligne dans l'outbox (`sk → dernière valeur` : le temps compté toutes les 5 s n'envoie que sa dernière valeur) ; fonction pure `mergeRemote` (vues : max, temps : par appareil, réponses : union). Tests.
- Concept : fusion sans conflit (CRDT simples), idempotence, outbox.
- Vérifier : `pnpm --dir app test` → tests de fusion verts (ordre d'arrivée indifférent, rejeu sans doublon)
- Cours : une ligne par fait et par écrivain : le temps passé est gardé par appareil (`T#<appareil>#<thème>`, l'affichage fait la somme) ; deux appareils n'écrivent jamais la même ligne, donc aucun conflit. Vues : max ; réponses : union par clé `R#<date>#<carte>`.
- Cours : outbox = `sk → dernière valeur` (le temps compté toutes les 5 s n'y occupe qu'une ligne par thème) ; `ackOutbox` ne retire que ce qui n'a pas changé pendant l'envoi.
- Cours : fusion pure (`mergeRows`) testée sur trois propriétés : ordre d'arrivée indifférent, rejeu sans effet, état d'entrée intact.
- Résultat : `progress.ts` (lignes, outbox, fusion) + 7 tests ; commit `97f0c6c`.

### [ ] Étape 4 — Moteur de synchro : envoi, lecture, déclencheurs
- À faire : `sync.ts` : `flush()` (lots de 25, `BatchWriteItem`, `UnprocessedItems` remis dans l'outbox), `pull()` (delta sur `R#<dernier pull − 1 jour>`, vues et temps en entier), déclencheurs (5 s, `visibilitychange`, `online`, ouverture), `keepalive` à la mise en arrière-plan ; premier envoi de tout le local à la première connexion ; changement d'utilisateur sur l'appareil = local vidé.
- Concept : debounce, `fetch` keepalive, delta par clé de tri, horloges d'appareils.
- Vérifier : tests verts ; iPhone en mode avion → 3 réponses → réseau rétabli → lignes visibles par `aws dynamodb query`
- Erreur vue : delta « réponses depuis la dernière lecture − 1 jour » → une réponse datée de lundi peut arriver jeudi (appareil resté hors ligne) et ne serait jamais lue : la date d'une ligne est celle du clic, pas de son arrivée ; lecture complète de la partition à chaque fois (quelques milliers de lignes, fraction de centime). Trouvé par un test.
- Erreur vue : refusés de `BatchWriteItem` jamais reconnus → comparaison de l'objet `{S: …}` au lieu de la chaîne : ils sortaient de l'outbox comme envoyés. Trouvé par un test.
- Cours : déclencheurs : envoi 5 s après la dernière écriture (au plus 1 min pendant une révision continue), envoi `keepalive` à la mise en arrière-plan, envoi + lecture à l'ouverture, au retour au premier plan et au retour du réseau ; une opération à la fois (file de promesses).
- Résultat : `sync.ts` + 9 tests, déployé (`97f0c6c`, CodeBuild `SUCCEEDED`) ; 81 lignes envoyées par le Mac mesurées dans la table. Reste : la mesure croisée iPhone ↔ Mac.

### [ ] Étape 5 — Réinitialisations et suppression du compte
- À faire : « Réinitialiser » (stats, progression) supprime les lignes côté DynamoDB et pose un marqueur `X#reset-…` daté, que les autres appareils appliquent à leur prochain pull ; « Supprimer mon compte » efface toute la partition avant `DeleteUser`.
- Concept : tombstone (marqueur de suppression), ordre des suppressions.
- Vérifier : réinitialiser sur le Mac → l'iPhone, rouvert, affiche 0 ; compte supprimé → `Count: 0` sur sa partition

### [ ] Étape 6 — Mesure sur deux appareils, coût, commits
- À faire : scénario iPhone + Mac (réponses croisées, hors ligne, réinitialisation), coût réel lu dans CloudWatch (`ConsumedWriteCapacityUnits`), README (`Synchro de la progression`), commits ciblés.
- Vérifier : `aws cloudwatch get-metric-statistics … ConsumedWriteCapacityUnits` → quelques dizaines par jour ; `git log --oneline -3` → commits `main: …`

## Pièges courants (dev TS → AWS)
1. Accorder `dynamodb:*` ou `Scan` avec `ForAllValues:StringEquals` sur `LeadingKeys` : une requête sans clé de partition satisfait la condition, l'utilisateur lit toute la table.
2. Oublier `amr = authenticated` dans la confiance du rôle : une identité invitée (si on l'active un jour) endosserait le rôle des connectés.
3. Écrire `${cognito-identity.amazonaws.com:sub}` sans le doubler en `$${…}` dans Terraform : erreur d'interpolation, ou pire, une chaîne vide.
4. Confondre le `sub` du user pool (UUID du compte) et l'identity id du pool (`eu-west-3:…`) : la politique ne connaît que le second.
5. Lire le résultat de `BatchWriteItem` sans regarder `UnprocessedItems` : DynamoDB peut accepter une partie du lot seulement, sans erreur.
6. Envoyer une requête à chaque tic de 5 s : 720 écritures par heure de révision au lieu de quelques-unes ; l'outbox garde la dernière valeur par clé.

## Critères de validation
- [ ] Déduit de la demande : un utilisateur connecté retrouve sur un 2e appareil ses cartes vues, son temps et ses réponses, sans action de sa part.
- [ ] Déduit de la demande : hors ligne, l'app marche comme avant et rien n'est perdu au retour du réseau.
- [x] Déduit de la demande : un utilisateur ne peut ni lire ni écrire la progression d'un autre (refus IAM mesuré).
- [ ] Déduit de la demande : coût mesuré de l'ordre du centime par mois pour un utilisateur, sans API Gateway ni Lambda.

## Question de compréhension
L'app parle directement à DynamoDB depuis le téléphone : qu'est-ce qui empêche un utilisateur qui modifie le code de l'app de lire la progression d'un autre, et pourquoi deux appareils qui écrivent au même moment ne s'écrasent-ils jamais ?

## Journal
- 2026-10-25 — Plan généré sans carte Trello (suite de `pwa-revision`, décidé en conversation) : comparaison S3 + `If-Match` / Lambda + DynamoDB / DynamoDB direct par identity pool ; retenu DynamoDB direct, une ligne par fait, synchro locale d'abord. 6 étapes, 4 critères déduits de la demande. Code dans `revision-pwa`, cours et cartes dans `data-platform/learning/`.
- 2026-10-25 — Étape 1 validée : table `progress`, identity pool, rôle `progress-user` (`LeadingKeys`) appliqués ; isolation mesurée avec un vrai compte (sa partition lisible, autre partition et `Scan` refusés). Critère 3 coché.
- 2026-10-25 — Étape 2 validée : accès AWS de l'app (`cloud.ts`, `aws4fetch`), état de la synchro dans Mon compte, mesuré sur le Mac ; build CI corrigé (`localStorage` à l'import). Décision : pas d'API Gateway devant la table.
- 2026-10-26 — Étape 3 validée (tests) ; étape 4 codée et déployée, deux défauts trouvés par les tests (delta par date, refusés de BatchWriteItem) ; mesure sur les deux appareils en attente.
