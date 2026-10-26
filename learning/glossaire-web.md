---
type: glossaire
langage: Web
updated: 2026-10-26
---

# Glossaire Web

## access token
- Définition : Jeton OAuth 2.0 de courte durée qui autorise l'appel d'une API au nom d'un utilisateur : il dit ce qu'on peut faire, pas qui on est.
- Exemple : Cognito renvoie un access token avec l'id token ; l'identity pool, lui, attend l'id token.
- Alias : access tokens, jeton d'accès

## API
- Définition : Application Programming Interface : ensemble d'opérations qu'un logiciel expose à d'autres programmes, avec un format de requête et de réponse documenté.
- Exemple : L'API DynamoDB expose `PutItem` ou `GetItem` ; Terraform nomme ses ressources d'après les objets de ces API (`aws_dynamodb_table`).
- Alias : APIs, Application Programming Interface
- Carte : AWS/api-protocoles-services

## ArrayBuffer
- Définition : Objet JavaScript qui représente une zone d'octets bruts de taille fixe ; on ne la lit pas directement mais à travers une vue typée.
- Exemple : `crypto.subtle.digest` rend un `ArrayBuffer` de 32 octets, lu ensuite avec `new Uint8Array(buf)`.
- Carte : web-crypto-arraybuffer-vue

## aud
- Définition : Claim « audience » d'un JWT : identifiant du destinataire prévu du jeton ; un service refuse un jeton dont `aud` ne le désigne pas.
- Exemple : La trust policy d'un rôle Cognito exige que `cognito-identity.amazonaws.com:aud` vaille l'id de l'identity pool attendu.
- Carte : AWS/iam-confiance-cognito

## aws4fetch
- Définition : Petite bibliothèque JavaScript qui signe les requêtes vers AWS (signature SigV4) avec la crypto native du navigateur, sans le SDK AWS.
- Exemple : L'app de révision signe ses appels à DynamoDB avec `aws4fetch`, à partir d'identifiants temporaires obtenus de Cognito.
- Carte : web-crypto-subtle-asynchrone

## Brotli
- Définition : Algorithme de compression de Google, plus efficace que gzip sur le texte web ; le navigateur l'annonce par `Accept-Encoding: br`.
- Exemple : Avec `compress = true`, CloudFront sert le bundle JavaScript en Brotli aux navigateurs qui l'acceptent.
- Alias : br
- Carte : AWS/cloudfront-compression-brotli

## bundle
- Définition : Fichier JavaScript produit au build, qui regroupe le code de l'app et de ses dépendances pour être servi au navigateur.
- Exemple : `vite build` écrit `dist/assets/index-<hash>.js`, le bundle que CloudFront sert à l'app de révision.
- Alias : bundles, bundler
- Carte : vite-env-remplace-au-build

## Cache Storage
- Définition : Stockage du navigateur qui range des paires requête → réponse HTTP, lisible par la page et par le service worker ; base du hors-ligne d'une PWA.
- Exemple : Le cache `catalogue` de l'app garde la dernière réponse de `/content/catalog.json` pour l'ouvrir hors ligne.
- Alias : CacheStorage
- Carte : pwa-stockage-vu-du-service-worker

## Cache-Control
- Définition : En-tête HTTP qui dit qui peut garder une réponse en cache et combien de temps (`max-age=60` : 60 secondes).
- Exemple : L'API BODACC répond `cache-control: public, max-age=60` : un proxy peut resservir une réponse vieille d'une minute.
- Alias : max-age
- Carte : Data engineering/api-de-donnees-max-age-reponse-datee

## CDN
- Définition : Content Delivery Network : réseau de serveurs proches des utilisateurs qui gardent en cache et servent les fichiers d'un site.
- Exemple : CloudFront est le CDN de l'app de révision ; `sw.js` y est servi en `no-cache` pour que les mises à jour se voient.
- Alias : Content Delivery Network

## CDP
- Définition : Chrome DevTools Protocol : interface par laquelle un programme pilote et inspecte Chrome (pages, réseau, manifest).
- Exemple : `Page.getAppManifest` par CDP montre l'`id` que Chrome attribue à l'app installée.
- Alias : Chrome DevTools Protocol

## Chromium
- Définition : Moteur de navigateur open source de Google, base de Chrome, Edge et Opera : un comportement mesuré dans Chromium vaut en général pour eux.
- Exemple : Les critères d'installation d'une PWA décrits ici sont ceux de Chromium ; Safari a ses propres règles.

## chunk
- Définition : Fichier JavaScript séparé que produit le bundler, chargé seulement quand le code qui en a besoin s'exécute (import dynamique).
- Exemple : `import('./d.json')` fait sortir à Vite un `assets/d-<hash>.js` chargé au premier appel.
- Alias : chunks
- Carte : modules-es-vite-chunk-json

## claim
- Définition : Champ d'un JWT qui affirme une information sur le sujet ou le jeton : identité (`sub`), destinataire (`aud`), émetteur (`iss`), expiration (`exp`).
- Exemple : La trust policy du rôle de CI teste le claim `sub` du jeton GitHub pour n'accepter qu'un dépôt et une branche.
- Alias : claims
- Carte : AWS/iam-oidc-ci-sans-cle

## code de statut HTTP
- Définition : Nombre à trois chiffres en tête d'une réponse HTTP : 2xx succès, 3xx redirection, 4xx erreur du client, 5xx erreur du serveur.
- Exemple : `r.raise_for_status()` lève sur un 404 ou un 503 ; `curl -w "%{http_code}"` affiche le statut seul.
- Alias : codes de statut HTTP, statut HTTP, status code
- Carte : Python/http-raise-for-status

## Content-Encoding
- Définition : En-tête HTTP qui indique la compression appliquée au corps d'une réponse (`gzip`, `br`) : le client décompresse avant de lire.
- Exemple : Le navigateur décompresse seul une réponse `Content-Encoding: gzip` ; `curl` ne le fait qu'avec `--compressed`.
- Carte : DevOps/curl-compressed-decompresser

## contexte sécurisé
- Définition : Page servie en HTTPS ou depuis `localhost` : seul cadre où le navigateur ouvre ses API sensibles (crypto, service worker).
- Exemple : Ouverte sur `http://192.168.x.x:5175` depuis l'iPhone, l'app n'est pas en contexte sécurisé : `crypto.subtle` vaut `undefined`.
- Alias : secure context, isSecureContext
- Carte : web-crypto-subtle-absent-en-http

## cookie
- Définition : Petite donnée qu'un serveur dépose dans le navigateur (`Set-Cookie`) et que celui-ci renvoie à chaque requête vers le même site.
- Exemple : La politique `CachingOptimized` de CloudFront ignore les cookies : deux visiteurs reçoivent le même objet en cache.
- Alias : cookies
- Carte : AWS/cloudfront-cle-de-cache-query

## CORS
- Définition : Cross-Origin Resource Sharing : en-têtes par lesquels un serveur autorise une page d'une autre origine à lire ses réponses.
- Exemple : Sans en-tête CORS, une image d'un autre site chargée en `no-cors` donne une réponse opaque, illisible par le script.
- Alias : Cross-Origin Resource Sharing
- Carte : pwa-reponse-opaque-status-0

## crypto.subtle
- Définition : API de cryptographie native du navigateur et de Node (hachage, HMAC, chiffrement, signatures), asynchrone, disponible seulement en contexte sécurisé.
- Exemple : `await crypto.subtle.digest('SHA-256', octets)` calcule une empreinte sans aucune bibliothèque.
- Alias : SubtleCrypto, Web Crypto
- Carte : web-crypto-subtle-asynchrone

## CryptoKey
- Définition : Objet opaque qui représente une clé dans Web Crypto : il déclare ses usages permis (signer, vérifier) et si ses octets peuvent être exportés.
- Exemple : `importKey('raw', secret, {name: 'HMAC', hash: 'SHA-256'}, false, ['sign'])` rend une `CryptoKey` qui sait seulement signer.
- Carte : web-crypto-hmac-importkey-sign

## CSP
- Définition : Content Security Policy : en-tête HTTP qui liste les sources de scripts, styles ou images qu'une page a le droit de charger, contre le XSS.
- Exemple : `Content-Security-Policy: script-src 'self'` bloque tout script chargé depuis un autre domaine.
- Alias : Content Security Policy, Content-Security-Policy
- Carte : AWS/cloudfront-en-tetes-securite

## CSS Grid
- Définition : Mise en page CSS en grille (`display: grid`) : on définit des rangées et des colonnes, puis on y place les éléments.
- Exemple : `grid-template-rows: auto minmax(0, 1fr) auto` : en-tête, contenu qui défile, onglets en bas.
- Alias : grille CSS, grid
- Carte : css-grid-minmax-zero

## DNS
- Définition : Domain Name System : annuaire d'Internet qui traduit un nom de domaine (`exemple.fr`) en adresse IP joignable.
- Exemple : Avant de se connecter à l'API BODACC, httpx fait résoudre son nom par DNS ; un échec lève `ConnectError`.
- Alias : Domain Name System

## dvh
- Définition : Unité CSS : 1 % de la hauteur visible de l'écran, qui suit l'apparition des barres du navigateur mobile (`100dvh` = tout l'écran visible).
- Exemple : `height: 100dvh` fait tenir une app exactement dans l'écran visible de l'iPhone, barres comprises.
- Alias : 100dvh

## effet de bord
- Définition : Action d'un code au-delà de renvoyer une valeur : écrire un fichier, lire ou modifier le stockage, changer une variable globale.
- Exemple : Lire `localStorage` au chargement de `cloud.ts` est un effet de bord qui a cassé le build sous Node.
- Alias : effets de bord
- Carte : vite-effet-de-bord-a-limport

## en-tête HTTP
- Définition : Paire `Nom: valeur` envoyée avant le corps d'une requête ou d'une réponse HTTP : type de contenu, cache, authentification, compression.
- Exemple : `curl -D - -o /dev/null` affiche les en-têtes de réponse, dont `Content-Type` et `ETag`.
- Alias : en-têtes HTTP, header HTTP, headers HTTP
- Carte : DevOps/curl-entetes-sans-corps

## encodage URL
- Définition : Écriture des caractères spéciaux d'une URL sous la forme `%XX` (code hexadécimal de l'octet) ; une espace devient `%20` ou `+`.
- Exemple : Une notification S3 envoie la clé `date%3D2026-10-20/…` : `unquote_plus` la décode avant `get_object`.
- Alias : URL-encodé, URL-encodée, percent-encoding
- Carte : AWS/s3-evenement-cle-encodee

## endpoint
- Définition : Adresse (URL) précise à laquelle un service répond, souvent une par région ou par opération.
- Exemple : `https://dynamodb.eu-west-3.amazonaws.com` est l'endpoint DynamoDB de Paris ; l'app y envoie ses `POST /` signés.
- Alias : endpoints, point de terminaison
- Carte : AWS/api-cors-endpoints

## esbuild
- Définition : Bundler et transpileur JavaScript et TypeScript très rapide, écrit en Go ; Vite s'en sert en développement.
- Exemple : `esbuild --bundle` réunit le handler TypeScript d'une Lambda et ses imports en un seul fichier `.mjs`.
- Carte : AWS/lambda-esbuild-bundle

## ETag
- Définition : En-tête HTTP qui porte une empreinte de la réponse ; renvoyé dans `If-None-Match`, il permet au serveur de répondre « inchangé » (304), sans corps.
- Exemple : Sur S3 chiffré par KMS, l'ETag change à chaque écriture : il ne prouve pas que le contenu a changé.
- Alias : ETags
- Carte : Data engineering/api-de-donnees-etag-if-none-match

## EventTarget
- Définition : Interface du DOM commune à tout objet qui émet et écoute des événements (`addEventListener`, `dispatchEvent`) : `window`, un élément, ou `new EventTarget()`.
- Exemple : Un test crée `new EventTarget()` pour vérifier un écouteur sans navigateur, sous Node.
- Carte : dom-customevent-detail

## fichier .env
- Définition : Fichier texte de variables `NOM=valeur` que l'outil (Vite, Vitest) charge au démarrage ; `.env.local` reste propre au poste et n'est pas commité.
- Exemple : `VITE_PROGRESS_TABLE=…` dans `app/.env.local` configure l'app de révision en local, sans toucher au dépôt.
- Alias : .env.local
- Carte : vite-priorite-shell-avant-env

## HSTS
- Définition : HTTP Strict Transport Security : en-tête qui demande au navigateur de n'utiliser que HTTPS pour ce domaine pendant une durée donnée.
- Exemple : `Strict-Transport-Security: max-age=31536000` : pendant un an, le navigateur remplace seul `http://` par `https://`.
- Alias : HTTP Strict Transport Security, Strict-Transport-Security
- Carte : AWS/cloudfront-en-tetes-securite

## HTTP 304
- Définition : Statut « Not Modified » : réponse sans corps à une requête conditionnelle, qui dit au client que sa copie est encore à jour.
- Exemple : Un client renvoie l'ETag reçu hier dans `If-None-Match` : rien n'a changé, le serveur répond 304.
- Alias : 304, Not Modified
- Carte : Data engineering/api-de-donnees-etag-if-none-match

## HTTP 429
- Définition : Statut « Too Many Requests » : le client a dépassé le quota du serveur et doit attendre avant de réessayer.
- Exemple : 20 threads qui paginent l'API BODACC en même temps reçoivent des 429 : il faut espacer les appels.
- Alias : 429, Too Many Requests
- Carte : Data engineering/api-de-donnees-codes-http-retenter-ou-lever

## HTTP/2
- Définition : Version du protocole HTTP qui fait passer plusieurs requêtes en parallèle sur une seule connexion et écrit les noms d'en-têtes en minuscules.
- Exemple : En HTTP/2, `content-type` arrive en minuscules : httpx lit les en-têtes sans tenir compte de la casse.
- Alias : HTTP2, h2
- Carte : Python/http-headers-casse

## id token
- Définition : Jeton JWT d'OpenID Connect qui dit qui est l'utilisateur (`sub`, e-mail) : il prouve une identité, pas un droit d'accès à une API.
- Exemple : L'app de révision envoie l'id token du user pool à l'identity pool, qui le vérifie et rend des clés STS.
- Alias : id tokens, id_token, IdToken, jeton d'identité
- Carte : AWS/cognito-identity-id-vs-sub

## import attributes
- Définition : Syntaxe `import … with { type: 'json' }` qui dit à l'environnement comment charger un module (ici, comme JSON) ; elle remplace l'ancien `assert`.
- Exemple : `parcours.ts` charge `spec/parcours.json` avec `with { type: 'json' }`, accepté par Vite comme par Node.
- Alias : attributs d'import
- Carte : modules-es-import-json-with

## import dynamique
- Définition : `import(chemin)` : chargement d'un module à la demande, pendant l'exécution ; il renvoie une promesse et peut être conditionnel.
- Exemple : `const m = await import('./gros.json', { with: { type: 'json' } })` ne charge le fichier qu'au besoin.
- Alias : import()
- Carte : modules-es-import-dynamique

## IndexedDB
- Définition : Base de données du navigateur, asynchrone, qui stocke des objets indexés, accessible depuis la page comme depuis un service worker.
- Exemple : Un service worker qui doit lire la progression la range dans IndexedDB, car `localStorage` lui est inaccessible.
- Carte : pwa-stockage-vu-du-service-worker

## ITP
- Définition : Intelligent Tracking Prevention : protections de Safari contre le pistage ; elles effacent notamment le stockage d'un site non visité depuis 7 jours.
- Exemple : Ouverte dans un onglet Safari, l'app perd sa progression après 7 jours sans visite ; installée sur l'écran d'accueil, non.
- Alias : Intelligent Tracking Prevention
- Carte : pwa-quotas-et-eviction

## Jest
- Définition : Framework de tests JavaScript (Meta) : lance les fichiers `*.test.js`, fournit `expect` et les mocks ; Vitest en reprend l'API.
- Exemple : `test('…', () => expect(x).toBe(1))` en Jest correspond à une fonction `test_…` avec `assert` dans pytest.
- Carte : Python/tests-decouverte-nommage

## jsdom
- Définition : Bibliothèque qui simule le DOM du navigateur (`document`, `window`) sous Node, pour tester du code front sans navigateur.
- Exemple : `environment: 'jsdom'` dans la config Vitest donne un `document` aux tests, au prix de tests plus lents.
- Carte : vite-vitest-environnement-node

## JSON
- Définition : JavaScript Object Notation : format texte d'échange de données fait d'objets, de tableaux, de chaînes, de nombres, de booléens et de `null`.
- Exemple : Les API d'AWS, `jq` et l'export BODACC parlent JSON ; Python le lit avec `json.loads`.
- Alias : JavaScript Object Notation
- Carte : Python/json-loads-dumps

## JWT
- Définition : JSON Web Token : jeton texte en trois parties (en-tête, contenu, signature) dont la signature prouve l'émetteur ; ses champs s'appellent des claims.
- Exemple : Cognito émet des JWT ; l'identity pool vérifie leur signature avant de rendre des clés STS.
- Alias : JSON Web Token, jeton JWT, jetons JWT
- Carte : AWS/cognito-user-ou-identity-pool

## localStorage
- Définition : Stockage clé-valeur du navigateur, synchrone, limité à quelques Mo de chaînes, propre à chaque origine et conservé entre les visites.
- Exemple : `localStorage.setItem('theme', 'sombre')` retient un choix d'affichage d'une visite à l'autre.

## manifest web
- Définition : Fichier JSON (`manifest.webmanifest`) qui décrit une PWA installable : nom, icônes, mode d'affichage, URL de départ.
- Exemple : vite-plugin-pwa génère le manifest web de l'app de révision et l'annonce par `<link rel="manifest">`.
- Alias : manifest.webmanifest, Web App Manifest, manifest PWA
- Carte : pwa-manifest-champs

## MFA
- Définition : Multi-Factor Authentication : connexion qui exige un second facteur (code d'une app, clé physique) en plus du mot de passe.
- Exemple : Le compte root AWS et les utilisateurs IAM humains se protègent par MFA.
- Alias : Multi-Factor Authentication, authentification multifacteur, 2FA
- Carte : AWS/iam-utilisateur-ou-role

## micro-tâche
- Définition : Petite tâche que JavaScript exécute dès que le code synchrone en cours se termine, avant tout autre événement (suite d'une promesse, `queueMicrotask`).
- Exemple : Le code après un `await` reprend dans une micro-tâche, avant le prochain clic ou `setTimeout`.
- Alias : micro-tâches, microtâche, microtask
- Carte : dom-dispatchevent-synchrone

## minifieur
- Définition : Outil du build qui réduit le JavaScript (noms raccourcis, espaces retirés, code mort supprimé) pour alléger le bundle.
- Exemple : Un `if (false) {…}` laissé par Vite est entièrement retiré du bundle par le minifieur.
- Alias : minification, minifier

## module ES
- Définition : Fichier JavaScript standard (ECMAScript) qui déclare ses dépendances par `import` et ce qu'il expose par `export` ; il n'est évalué qu'une fois.
- Exemple : `data.ts` et `App.tsx` sont des modules ES : un `import` les relie, résolu avant l'exécution.
- Alias : modules ES, ESM, ECMAScript module
- Carte : modules-es-import-hisse

## NODE_ENV
- Définition : Variable d'environnement de convention Node (`development` ou `production`) ; bibliothèques et bundlers en déduisent la version de code à embarquer.
- Exemple : Un `NODE_ENV=development` exporté dans `~/.zshrc` embarque la version de développement de React dans le bundle.
- Carte : vite-node-env-build-de-dev

## OAuth
- Définition : OAuth 2.0 : standard de délégation d'accès ; un serveur d'autorisation remet à une application des jetons au lieu du mot de passe de l'utilisateur.
- Exemple : Le user pool Cognito est un serveur OAuth 2.0 ; OpenID Connect y ajoute l'id token.
- Alias : OAuth 2.0, OAuth2
- Carte : AWS/cognito-client-sans-secret

## origine
- Définition : Triplet protocole + domaine + port d'une page (`https://exemple.fr:443`) ; le navigateur cloisonne stockage et droits par origine.
- Exemple : `http://localhost:5175` et `http://localhost:5176` sont deux origines : chacune a son propre `localStorage`.
- Alias : même origine

## PATCH
- Définition : Méthode HTTP de mise à jour partielle : le corps ne contient que les champs à changer, à l'inverse de PUT qui remplace tout.
- Exemple : `PATCH /annonces/42` avec `{"statut": "radiée"}` ne touche que ce champ ; `exclude_unset=True` construit ce corps.
- Alias : méthode PATCH
- Carte : Python/validation-exclude-unset-patch

## payload
- Définition : Contenu utile transporté par une requête, un message ou un événement, par opposition à son enveloppe (en-têtes, métadonnées).
- Exemple : `aws lambda invoke --payload '{"date": "2026-10-20"}'` passe cet objet JSON en `event` au handler.
- Alias : payloads, charge utile
- Carte : AWS/lambda-payload-lu-une-fois

## phase de capture
- Définition : Premier trajet d'un événement du DOM, de `window` jusqu'à la cible, avant la remontée ; un écouteur s'y place avec `{ capture: true }`.
- Exemple : `add('z', f, { capture: true })` doit être retiré par `remove('z', f, { capture: true })`, pas sans l'option.
- Alias : capture
- Carte : dom-customevent-bubbles

## piste de grille
- Définition : Rangée ou colonne d'une grille CSS, dont la taille se règle dans `grid-template-rows` ou `grid-template-columns`.
- Exemple : `minmax(0, 1fr)` donne à la piste du contenu l'espace restant, sans grandir avec la pile de cartes.
- Alias : piste, pistes
- Carte : css-grid-minmax-zero

## Playwright
- Définition : Outil qui pilote un vrai navigateur (Chromium, WebKit, Firefox) depuis un script, pour tester une app de bout en bout.
- Exemple : `context.setOffline(true)` dans Playwright simule le mode avion pour tester l'app hors ligne.

## pool de connexions
- Définition : Connexions réseau ouvertes gardées par un client pour les réutiliser d'une requête à l'autre, sans refaire l'établissement TCP et TLS.
- Exemple : Un `httpx.Client` réutilise ses connexions vers l'API BODACC ; `close()` les ferme toutes.
- Alias : pools de connexions, connection pool
- Carte : Python/http-client-ferme

## précache
- Définition : Liste de fichiers qu'un service worker télécharge et met en cache dès son installation, pour que l'app s'ouvre hors ligne.
- Exemple : Workbox précache `index.html`, le JS, le CSS et les icônes de l'app de révision.
- Alias : précacher
- Carte : pwa-precache-empreinte

## préflight
- Définition : Requête `OPTIONS` envoyée par le navigateur avant une requête CORS non simple, pour demander au serveur si l'origine, la méthode et les en-têtes sont permis.
- Exemple : Avant un `POST` signé vers DynamoDB, le navigateur envoie un préflight ; DynamoDB répond `Access-Control-Allow-Origin: *`.
- Alias : requête préflight
- Carte : AWS/api-cors-endpoints

## promesse
- Définition : Objet JavaScript (`Promise`) qui représente un résultat à venir, tenu (valeur) ou rompu (erreur) ; on l'attend avec `await` ou `.then`.
- Exemple : L'app garde la promesse du premier appel Cognito en cours et la rend aux appels suivants, au lieu d'en lancer d'autres.
- Alias : promesses, Promise
- Carte : AWS/api-promesse-partagee

## proxy
- Définition : Intermédiaire qui reçoit des requêtes et les relaie vers un autre serveur, pour filtrer, mettre en cache ou traverser un réseau.
- Exemple : En entreprise, la variable `HTTPS_PROXY` fait passer les appels httpx par le proxy du réseau.
- Alias : proxys, mandataire

## PWA
- Définition : Progressive Web App : site web installable comme une app (icône, plein écran) qui peut marcher hors ligne grâce à un service worker.
- Exemple : L'app de révision est une PWA : ajoutée à l'écran d'accueil de l'iPhone, elle s'ouvre en plein écran, même en mode avion.
- Alias : Progressive Web App
- Carte : pwa-manifest-champs

## query string
- Définition : Partie d'une URL après `?`, faite de paires `clé=valeur` séparées par `&`, qui passe des paramètres à la ressource.
- Exemple : `/api/records?limit=100&offset=0` : `limit` et `offset` sont dans la query string.
- Alias : query strings, chaîne de requête, paramètres de requête
- Carte : Python/http-params-query-string

## refresh token
- Définition : Jeton OAuth de longue durée qui sert seulement à obtenir de nouveaux id et access tokens, sans redemander le mot de passe.
- Exemple : Le refresh token Cognito dure 30 jours par défaut ; l'app le présente quand l'id token, valable une heure, expire.
- Alias : refresh tokens, jeton de rafraîchissement

## requête Range
- Définition : Requête HTTP qui ne demande qu'une plage d'octets d'un fichier (`Range: bytes=0-1023`), pour lire un morceau ou reprendre un téléchargement.
- Exemple : DuckDB lit un fichier sur S3 par requêtes Range successives, sans le télécharger en entier.
- Alias : Range

## REST
- Définition : Style d'API web où chaque ressource a une URL et où la méthode HTTP (`GET`, `PUT`, `DELETE`…) dit l'action.
- Exemple : L'API de S3 est REST : `PUT /<clé>` écrit l'objet ; DynamoDB, lui, reçoit tout en `POST /`.
- Alias : API REST, RESTful
- Carte : AWS/api-protocoles-services

## Retry-After
- Définition : En-tête HTTP d'une réponse 429 ou 503 qui dit quand réessayer : un nombre de secondes ou une date.
- Exemple : `Retry-After: 120` demande d'attendre deux minutes avant le prochain appel.
- Carte : Data engineering/api-de-donnees-retry-after-deux-formes

## RFC
- Définition : Request for Comments : documents de l'IETF, l'organisme des standards d'Internet ; HTTP y est décrit (RFC 9110, 9111).
- Exemple : La RFC 9110 autorise `Retry-After` en secondes ou en date HTTP.
- Alias : RFCs, Request for Comments

## SaaS
- Définition : Software as a Service : logiciel loué et utilisé en ligne, hébergé et exploité par son éditeur (≈ Slack, Datadog).
- Exemple : Un SaaS de monitoring qui lit votre compte AWS endosse un rôle chez vous, protégé par un `ExternalId`.
- Alias : Software as a Service
- Carte : AWS/iam-externalid-tiers

## safe area
- Définition : Zone de l'écran que ne masquent ni l'encoche, ni les coins arrondis, ni la barre d'accueil ; CSS la lit avec `env(safe-area-inset-*)`.
- Exemple : L'en-tête de l'app ajoute `env(safe-area-inset-top)` à son padding pour passer sous la Dynamic Island.
- Alias : safe-area, zone sûre
- Carte : pwa-safe-area-env

## service worker
- Définition : Script que le navigateur exécute à part de la page : il intercepte ses requêtes réseau et peut répondre depuis un cache, même hors ligne.
- Exemple : `sw.js`, généré par Workbox, sert l'app de révision depuis son cache quand l'iPhone est en mode avion.
- Alias : service workers, SW
- Carte : pwa-service-worker-cycle-de-vie

## shadow DOM
- Définition : Sous-arbre du DOM encapsulé, attaché à un élément (composant web) : ses styles et sa structure sont isolés du reste de la page.
- Exemple : Un événement émis dans un shadow DOM n'en sort que s'il est créé avec `composed: true`.

## socket
- Définition : Extrémité d'une connexion réseau ouverte par le système ; un programme y lit et y écrit des octets, puis doit la fermer.
- Exemple : `socket.create_connection((hôte, 443))` ouvre une connexion TCP ; un `with` la ferme même en cas d'erreur.
- Alias : sockets

## SPA
- Définition : Single Page Application : app web qui charge une seule page HTML puis change d'écran en JavaScript, sans recharger la page.
- Exemple : L'app de révision est une SPA : `/session/42` n'existe pas sur le serveur, le routeur JavaScript l'affiche.
- Alias : Single Page Application
- Carte : pwa-navigatefallback-toute-navigation

## SRP
- Définition : Secure Remote Password : protocole où le client prouve qu'il connaît le mot de passe sans jamais l'envoyer au serveur.
- Exemple : Le flux `USER_SRP_AUTH` de Cognito connecte un utilisateur sans faire transiter son mot de passe, à l'inverse de `USER_PASSWORD_AUTH`.
- Alias : Secure Remote Password, USER_SRP_AUTH
- Carte : AWS/cognito-explicit-auth-flows

## Strict Mode
- Définition : Mode de développement de React (`<StrictMode>`) qui exécute deux fois rendus et effets pour révéler les effets mal nettoyés.
- Exemple : En développement, un écouteur posé dans un `useEffect` sans nettoyage apparaît en double à cause du Strict Mode.
- Alias : StrictMode
- Carte : dom-ecouteur-doublon

## sub
- Définition : Claim « subject » d'un JWT : identifiant unique et stable de l'utilisateur chez l'émetteur du jeton.
- Exemple : Le `sub` d'un utilisateur du user pool Cognito est un UUID, distinct de l'identity id donné par l'identity pool.
- Carte : AWS/cognito-identity-id-vs-sub

## TCP
- Définition : Transmission Control Protocol : protocole qui établit une connexion fiable entre deux machines et livre les octets dans l'ordre, sans perte ; HTTP passe dessus.
- Exemple : `ConnectError` de httpx signale que la connexion TCP n'a pas pu s'établir : serveur injoignable ou port fermé.
- Alias : Transmission Control Protocol
- Carte : Python/http-transport-retries

## TLS
- Définition : Transport Layer Security : protocole qui chiffre et authentifie une connexion réseau ; c'est le « S » de HTTPS.
- Exemple : Une nouvelle connexion HTTPS coûte un échange TLS ; un client httpx réutilisé l'évite.
- Alias : Transport Layer Security, SSL

## TTL
- Définition : Time To Live : durée de vie d'une entrée de cache ou d'une donnée, après laquelle elle expire.
- Exemple : Le cache de prompt de Bedrock a un TTL de 5 minutes, prolongé à chaque lecture.
- Alias : Time To Live

## type MIME
- Définition : Étiquette du format d'un contenu, envoyée dans l'en-tête `Content-Type` (`application/json`, `text/javascript`) ; le navigateur s'y fie plutôt qu'à l'extension.
- Exemple : Un `config.json` servi en `text/javascript` serait exécuté comme du code sans `with { type: 'json' }`.
- Alias : MIME, Content-Type
- Carte : modules-es-attribut-securite

## unité fr
- Définition : Unité de CSS Grid : une fraction de l'espace restant d'une grille ; `1fr 2fr` partage la place en un tiers et deux tiers.
- Exemple : `1fr` seul vaut `minmax(auto, 1fr)` : la piste grandit avec son contenu.
- Alias : fr, 1fr
- Carte : css-grid-minmax-zero

## URL relative
- Définition : URL sans schéma ni domaine (`/api/records`, `../img.png`), résolue par rapport à une URL de base.
- Exemple : Avec `base_url="https://h/api/v2"`, httpx ajoute le chemin relatif `/records` à la base : `…/api/v2/records`.
- Alias : URLs relatives, chemin relatif
- Carte : Python/http-base-url-chemin

## User-Agent
- Définition : En-tête HTTP qui nomme le logiciel client (navigateur, `curl/8.7.1`, `python-httpx/0.28`) ; les API s'en servent pour identifier les appelants.
- Exemple : Un client d'ingestion envoie un `User-Agent` explicite pour que l'éditeur de l'API sache qui l'appelle.

## VAPID
- Définition : Voluntary Application Server Identification : paire de clés qui identifie le serveur qui envoie des notifications push web ; la page s'abonne avec la clé publique.
- Exemple : Une Lambda planifiée signe ses notifications de rappel avec la clé privée VAPID.
- Carte : pwa-push-limites-ios

## viewport
- Définition : Zone visible de la page ; la balise `<meta name="viewport">` règle sa largeur et son comportement sur mobile.
- Exemple : `viewport-fit=cover` dans la balise viewport fait occuper tout l'écran de l'iPhone, encoche comprise.
- Alias : balise viewport

## Vite
- Définition : Outil de build et serveur de développement front : il sert les modules ES en développement et produit le bundle de production.
- Exemple : En développement, Vite sert l'app de révision sur le port 5175 ; `vite build` produit le dossier `dist/` déployé.
- Carte : vite-env-remplace-au-build

## vite-plugin-pwa
- Définition : Plugin Vite qui génère le service worker (avec Workbox), le manifest web et le script d'enregistrement d'une PWA.
- Exemple : `VitePWA({ registerType: 'autoUpdate', manifest })` dans `vite.config.ts` configure la PWA de révision.
- Alias : VitePWA
- Carte : pwa-registertype-prompt-ou-autoupdate

## Vitest
- Définition : Lanceur de tests JavaScript intégré à Vite (même configuration, même transformation du code), proche de Jest.
- Exemple : `cloud.test.ts` vérifie sous Vitest l'en-tête `Authorization` signé des appels de l'app de révision.
- Carte : vite-vitest-environnement-node

## vue typée
- Définition : Objet qui lit un ArrayBuffer comme une suite de nombres d'un type donné (`Uint8Array` : octets de 0 à 255), sans copier la mémoire.
- Exemple : `new Uint8Array(buf)[0]` lit le premier octet d'une signature HMAC.
- Alias : vues typées, Uint8Array, tableau typé, typed array
- Carte : web-crypto-arraybuffer-vue

## webhook
- Définition : URL qu'un service appelle (souvent en POST) pour prévenir d'un événement, au lieu d'attendre qu'on l'interroge.
- Exemple : Un partenaire appelle le webhook d'une Lambda à chaque dépôt de fichier ; la Lambda vérifie sa signature HMAC.
- Alias : webhooks

## Workbox
- Définition : Bibliothèque de Google qui génère le code d'un service worker : précache, routes et stratégies de cache.
- Exemple : La route `NetworkFirst` du catalogue de l'app est écrite par Workbox dans `sw.js`.
- Carte : pwa-strategies-workbox-choisir

## XML
- Définition : eXtensible Markup Language : format texte à balises (`<id>1</id>`) pour échanger des données structurées.
- Exemple : L'API REST de S3 répond en XML ; converti en JSON, un élément seul devient un objet, plusieurs une liste.
- Alias : eXtensible Markup Language
- Carte : Python/json-xml-dict-ou-liste

## XSS
- Définition : Cross-Site Scripting : attaque qui fait exécuter un script malveillant dans une page, avec les droits de l'utilisateur.
- Exemple : Un script injecté peut signer à la place de l'utilisateur, même s'il ne peut pas lire une clé non extractible.
- Alias : cross-site scripting
- Carte : web-crypto-cle-non-extractible

## zod
- Définition : Bibliothèque TypeScript de validation : un schéma décrit la forme attendue, `schema.parse(x)` vérifie la donnée et en déduit le type.
- Exemple : `z.object({ siren: z.string() }).parse(data)` joue le rôle de `Modele.model_validate(data)` de Pydantic.
