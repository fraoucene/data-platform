---
card: "pwa-v2 · [Archi] revision-pwa v2 : catalogue en tranches, API serverless, site SSG, compétences, premium"
id_short: 72
learning_id: pwa-v2
board: fMaiYRrn
url: https://trello.com/c/HM6AVSnJ
created: 2026-10-27
updated: 2026-10-27
status: en-cours
---

# pwa-v2 · [Archi] revision-pwa v2 : catalogue en tranches, API serverless, site SSG, compétences, premium
Liste : revision-pwa v2 — mission autonome 2026-10-27 · Étiquettes : front, AWS, archi · [Carte Trello](https://trello.com/c/HM6AVSnJ)

## Objectif
Passer revision-pwa d'une app qui charge un `catalog.json` de 3,9 Mo et écrit sa progression directement dans DynamoDB à une plateforme : contenu en tranches immuables (ouverture indépendante de la taille du catalogue), couche serveur (API Gateway + Cognito, événements horodatés côté serveur, agrégats par Streams), site statique Next pour le SEO, compétences et parcours générés depuis les cartes, offre premium (cookies signés CloudFront), examens et certificats. Étude et décisions : `revision-pwa/docs/etude-v2-architecture.md`. Contrat du contenu : `revision-pwa/spec/contenu.md`. Mission menée en autonomie par l'orchestrateur (Fable 5.1) avec des agents exécutants (Opus 5.5) en worktrees parallèles, une branche par phase, intégration sur `v2`, merge sur `main` par Fraoucene.

### Décisions du 2026-10-27
- **Pas d'OpenSearch** : 2 OCU serverless ≈ 350 $/mois pour 4 Mo de données ; « aiguiller vers la bonne
  compétence » est un classement de quelques milliers de cartes par règles + état utilisateur, pas une recherche.
  Déclencheur futur : > 100 000 documents. Besoin sémantique : embeddings Bedrock + S3 Vectors / Aurora pgvector.
- **Catalogue en tranches** : `index.json` léger (`no-cache`, ETag) + une tranche immuable par thème
  (`<slug>.<hash8>.json`, `max-age=1 an`), tranches puis index (même principe que fichier puis `_MANIFEST.json`).
- **Événements plutôt qu'état** : le client envoie des gestes, la Lambda pose la date ; `aggregates` dérivés par
  DynamoDB Streams. Seule base crédible pour un certificat.
- **Premium hors ligne** : `content/premium/` + cookies signés CloudFront, cache SW séparé purgé au 403.
- **Stripe web d'abord**, IAP (15-30 %) quand l'app passe sur les stores via Capacitor.
- **Deux fronts, un back** : app Vite (PWA → Capacitor) + `web/` Next **SSG** (`output: 'export'`, S3 +
  CloudFront, pas d'OpenNext, pas de domaine pour l'instant). Tailwind sur les deux, composants de présentation
  dans `packages/ui`, modèle dans `packages/shared`.
- **Compétences = tags sur le registre** (domaine, chapitre), posés par `/cartes` à la création, jamais sur la
  carte ; parcours auto par domaine (débutant / praticien / expert) générés par `catalog-build`.
- **Seul l'orchestrateur applique Terraform** (`make up` sur `v2` après intégration) ; les agents font `make plan`.

## Prérequis
### Cache HTTP : revalidation et immuabilité
`Cache-Control: no-cache` ne veut pas dire « pas de cache » : le navigateur garde la réponse mais la revalide
(`If-None-Match` → 304 si l'ETag n'a pas changé). `public, max-age=31536000, immutable` : jamais revalidé ; le nom
du fichier porte un hash de son contenu, changer le contenu change le nom. C'est le modèle des bundles Vite,
appliqué aux données.
Doc : https://developer.mozilla.org/fr/docs/Web/HTTP/Headers/Cache-Control
Exercice 5 min : dans l'onglet Réseau, recharger l'app et repérer qui répond 304 et qui vient « (from disk cache) ».

### DynamoDB Streams
Journal ordonné des modifications d'une table, lu par une Lambda par lots ; `NEW_IMAGE` donne l'item écrit.
Permet de dériver une table d'agrégats sans que le client calcule rien, et sans Scan.
Doc : https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html

## Étapes

### [ ] Étape 0 — Étude et contrat du contenu
- À faire :
  1. Mesurer l'existant (taille du catalogue, parse, bundle, modèle de progression).
  2. Écrire `docs/etude-v2-architecture.md` et `spec/contenu.md`.
  3. Créer la liste Trello et une carte par phase ; branche `v2`, worktrees `v2-p0`, `v2-tailwind`, `v2-web`, `v2-api`.
- Vérifier : `git -C ~/Desktop/workspace/revision-pwa worktree list` → 5 lignes.
- Résultat : fait le 2026-10-27 (commit `v2: étude d'architecture v2 et contrat du contenu publié`).

### [x] Étape 1 — P0 : catalogue en tranches et monorepo `packages/shared`
- À faire : voir carte Trello v2-P0.
- Vérifier : `make cards` → 1 804 cartes, 103 fichiers de `content/` ; `make test` → shared 58, app 141.
- Cours : le gain ne vient pas d'un cache plus malin mais d'un **découpage** : l'app n'a besoin que de la hiérarchie pour s'ouvrir (`index.json`, 33 Ko) et d'un thème à la fois (une tranche, ≤ 322 Ko, lue en < 100 ms : le Web Worker devient inutile). Les tranches portent un hash dans leur nom → `CacheFirst` dans le SW, jamais revalidées ; l'index → `NetworkFirst`. Ordre d'écriture tranches → `catalog.json` → `index.json` : un lecteur ne voit un index que si ses tranches existent. Les orphelines vivent 7 jours (un client qui tient un vieil index les trouve encore) : une tranche inchangée est réécrite si sa date a plus d'un jour pour ne pas passer pour orpheline. Un paquet workspace consommé en source TypeScript (`@revision/shared`) évite un build intermédiaire, mais le chargeur de `vite.config.ts` ne lit pas le `.ts` d'un autre paquet : le plugin de dev passe par `ssrLoadModule`.
- Cartes : en attente
- Résultat : 2026-10-27, branche `v2-p0` (0522608) ; ouverture 3,92 Mo → 33 Ko, premier écran 1,47 s → 0,95 s, chunk principal 466 → 271 Ko ; intégration sur `v2` en cours.

### [x] Étape 2 — Tailwind sur la PWA et `packages/ui` (lot 1 : composants)
- À faire : voir carte Trello v2-UI.
- Vérifier : `make visual` → 15 captures identiques ; `make test` → paquet `ui` 16 tests.
- Cours : Tailwind v4 se configure en CSS (`@theme { --color-… }`) et non plus en `tailwind.config.js` ; on peut n'importer que `theme` + `utilities` sans le *preflight* (reset) tant que des écrans gardent leurs CSS Modules : l'ordre des `@layer` (theme < base < components < utilities) puis les modules décide qui gagne. Un paquet de composants « de présentation pure » (props en entrée, callbacks en sortie, ni routeur ni store) est ce qui rend un composant partageable entre la PWA et le site Next. La non-régression visuelle se mesure (captures Playwright avant / après, `toHaveScreenshot`), pas à l'œil ; trois écarts réels (bordure, dégradé, pointillé) ont été vus par le diff et corrigés.
- Cartes : en attente
- Résultat : 2026-10-27, branche `v2-tailwind` intégrée sur `v2` ; CSS 16 Kio gzip inchangé.

### [x] Étape 3 — Site Next SSG `web/` (lot 1)
- À faire : voir carte Trello v2-WEB.
- Vérifier : `curl -s -o /dev/null -w "%{http_code}" https://d1urszngzycgqo.cloudfront.net/` → `200` ; `curl -s https://d1urszngzycgqo.cloudfront.net/c/python/listes-index-negatif/ | grep -o "<title>[^<]*"`.
- Cours : `output: 'export'` + `generateStaticParams` = Next produit un dossier HTML pur, servi par S3 + CloudFront comme la PWA : pas de serveur Node, pas d'OpenNext. Les métadonnées SEO se **déduisent** du contenu (title = titre · thème · domaine, description = 1re phrase de la définition, JSON-LD `LearningResource` + `Quiz` + `BreadcrumbList`) : rien à écrire dans les cartes. Les fichiers `_next/*` ont un nom haché → `max-age=1 an, immutable` ; les pages HTML → `no-cache` ; les charges RSC `*.txt` ne servent qu'à `<Link>`, non publiées. CloudFront ne sert pas `index.html` sous `/x/` tout seul : une CloudFront Function réécrit l'URI. Piège vu : `NODE_ENV=development` dans le shell casse le prérendu (deux React) → `NODE_ENV=production` forcé dans `build`.
- Cartes : en attente
- Résultat : 2026-10-27, 2 844 pages, infra appliquée (20 ajouts, 1 changement, 0 destruction), site en ligne.

### [x] Étape 4 — P1 : API, événements, agrégats (lot 1 : serveur)
- À faire : voir carte Trello v2-P1.
- Vérifier : `curl -s "$(terraform -chdir=infra output -raw api_url)/health"` → `{"statut":"ok"}` ; `POST /events` avec JWT puis `GET /me/progress` → lignes `CARD#`, `THEME#`, `DAY#`, `TOTAL`.
- Cours : l'API HTTP (`aws_apigatewayv2_api`) coûte ≈ 1 $/million de requêtes et accepte un **authorizer JWT** natif : pas de Lambda d'autorisation, API Gateway vérifie la signature du jeton Cognito et expose `sub` à la Lambda. L'idempotence de `POST /events` tient à un marqueur `CID#<clientId>` écrit par `PutItem` conditionnel : un rejeu renvoie `doublon` sans réécrire. La Lambda `aggregates` lit le Stream par lots, applique chaque événement dans une transaction avec un marqueur `DONE#` (TTL 7 jours) : le Stream est « au moins une fois », le marqueur rend l'effet « exactement une fois ». Maîtrise d'un thème : `Σ s·r / max(répondues, total)` avec `s = 0,5·[dernière juste] + 0,5·ok/(ok+ko)` et récence `r = 2^(−(âge−30)/30)` au-delà de 30 jours ; répétition espacée 1 j → ×2 à chaque bonne réponse à échéance, plafond 180 j, retour à 1 j sur erreur.
- Erreur vue : `{"erreur":"invalide","problemes":[{"chemin":"events.0.clientId",…}]}` → `clientId` est **par événement** (clé d'idempotence de chaque geste), pas par lot.
- Cartes : en attente
- Résultat : 2026-10-27, `make plan` 28 ajouts / 0 changement / 0 destruction, `make up` OK, test de bout en bout avec un utilisateur Cognito de test : maîtrise 0,032 sur Python/Listes après 1 ok + 1 ko sur 31 cartes.

### [x] Étape 5 — Intégration sur `v2`, `make up`, déploiement dev
- À faire : merges P0 (agent dédié), P3, P4 ; publication des Lambdas ; plan ; apply ; registres ; déploiement app et site.
- Vérifier : `curl -sI https://d1non6rpr4vppb.cloudfront.net/content/index.json | grep -i cache-control` → `no-cache` ; `curl -s -o /dev/null -w "%{http_code}" https://d1non6rpr4vppb.cloudfront.net/content/premium/x.json` → `403`.
- Cours : un plan Terraform lancé depuis une branche qui n'a pas les ressources déjà appliquées par une autre branche propose de les **détruire** : on ne planifie que sur la branche d'intégration, jamais sur une branche de phase. Les pointeurs `current.json` des Lambdas doivent exister avant le plan (`make lambdas-publish` d'abord). Un bundle ESM esbuild qui embarque une dépendance CommonJS (`yaml`, `qrcode`, `firebase-admin`) n'a pas de vrai `require` : l'erreur « Dynamic require of "fs" is not supported » n'apparaît qu'au chargement dans Lambda, pas au build → bannière `createRequire` par défaut et contrôle de chargement du bundle sous Node après chaque build (la CI l'attrape avant publication).
- Erreur vue : `Dynamic require of "process" is not supported … yaml/dist/compose/composer.js` → `catalog-build` bundlé sans bannière `createRequire` après le passage par `packages/shared`.
- Cartes : en attente
- Résultat : 2026-10-27, apply 35 ajouts / 14 changements / 0 destruction puis 5 Lambdas mises à jour ; app, site et API v2 en ligne sur dev.
### [x] Étape 6 — P2 : compétences, parcours automatiques, `GET /me/next`
- À faire : voir cartes Trello v2-P2 ; registre (`spec/competences.json`, tags `competences` sur domaines et chapitres) puis code (`publishContent`, écran Compétences, route `/me/next`).
- Vérifier : `curl -s "$(terraform -chdir=infra output -raw api_url)/me/next?competence=backend-python" -H "Authorization: Bearer $TOKEN"` → `{"competence":"backend-python","maitrise":…,"etapes":[…],"etape":0,"cartes":[…]}` ; sans jeton → `401`.
- Cours : une **compétence est une règle**, pas une liste de cartes : tags posés sur le registre (domaine, chapitre, thème), résolus à la publication par `catalog-build` en tranches `competences/<id>.<hash>.json` ; la carte ne porte rien, un chapitre retagué déplace ses cartes partout. Les parcours « par domaine » (débutant / praticien / expert) se **génèrent** depuis le registre au lieu de s'écrire à la main. `GET /me/next` lit l'index à chaque appel (`no-cache`) mais garde les tranches en mémoire de la Lambda (nom haché = immuable) ; maîtrise d'une étape calculée sur les lignes `CARD#` de ses seules cartes au niveau visé (seuils 0,6 / 0,7 / 0,8), prochaines cartes = première étape non acquise, ordre niveau → échéance → prérequis.
- Cartes : en attente
- Résultat : 2026-10-27, `v2-p2` (registre, 8 compétences, 31 chapitres tagués) et `v2-p2b` (21 parcours auto, index 61 Ko, écran `/competences`, `GET /me/next`) intégrés et appliqués ; smoke test `/me/next` → maîtrise 0, 3 étapes, cartes proposées.
### [x] Étape 7 — P3 : premium et Stripe (serveur)
- À faire : voir carte Trello v2-P3.
- Cours : CloudFront **cookies signés** = politique JSON (ressource, expiration) signée RSA par une clé privée dont la clé publique est enregistrée dans un *key group* ; CloudFront vérifie à chaque requête sans lire le bucket (403 sinon) et sert ensuite la tranche du cache. La clé privée ne passe ni par le dépôt ni par l'état Terraform (`tls_private_key` l'y laisserait) : SSM SecureString posé à la main, `ignore_changes`. Piège : l'API répond depuis `execute-api.amazonaws.com`, un autre domaine que l'app → `Set-Cookie` inutile, l'app recopie les cookies du corps (`document.cookie`). Stripe : Checkout (session, `client_reference_id = sub`) → webhook signé (`constructEvent`) → entitlement ; idempotence par marqueur `STRIPE#<event.id>` en transaction ; l'abonnement est relu chez Stripe, l'ordre des webhooks n'importe pas.
- Cartes : en attente
- Résultat : 2026-10-27, branche `v2-p3` intégrée et appliquée ; clé privée dev en SSM ; clés Stripe à poser par Fraoucene.
### [x] Étape 8 — P4 : examens et certificat (serveur)
- À faire : voir carte Trello v2-P4.
- Vérifier : `curl -s "$(terraform -chdir=infra output -raw api_url)/certificates/01JBQ3XK7M2N4P6R8T0V2W4Y6Z"` → `{"erreur":"certificat-inconnu"}`.
- Cours : un examen crédible garde `bonne` **côté serveur** (session DynamoDB avec l'ordre mélangé), horodate les réponses à la réception, refuse après `expiresAt`, corrige à `finish` dans une transaction (session + événement + certificat). Tirage reproductible : graine = `examId`. Certificat = ligne `CERT#` + PDF (`pdf-lib`, QR) sous une clé non devinable, lue par URL **présignée** (SigV4 embarqué : le runtime Lambda ne garantit pas `@aws-sdk/s3-request-presigner`) ; vérification publique par une GSI qui ne projette que les champs publics. Limite connue : les quiz sont aussi dans le catalogue public.
- Cartes : en attente
- Résultat : 2026-10-27, branche `v2-p4` intégrée et appliquée (table `exams`, 8 routes) ; page `/verify/` en ligne.

### [x] Étape 9 — Lot 2 : l'app parle à l'API, le site sur `@revision/ui`
- À faire : outbox → `POST /events`, réconciliation `GET /me/progress`, `POST /me/identity` + script `migrate-progress-to-events`, cookies premium côté app, `ExamScreen` ; site : composants `@revision/ui`, pages `/k/`, `/premium/`, contrôle des liens (`make web-links`).
- Vérifier : `POST /me/identity` deux fois le même id → `200` puis `200`, un autre id → `409` ; `POST /events` rejoué avec le même `clientId` → `statut: "doublon"` ; `curl -s -o /dev/null -w "%{http_code}" https://d1urszngzycgqo.cloudfront.net/k/backend-python/` → `200`.
- Cours : **réconciliation** = le local ne recule jamais (max par compteur, union des cartes vues) ; un événement déjà envoyé ne se modifie plus jamais (le renvoi doit rester identique pour que le serveur reconnaisse le doublon) ; migration d'une table d'état vers un journal = événements **datés d'origine** avec un `clientId` déterministe (rejeu sans doublon) et un marqueur `migre: true` ignoré par l'agrégateur si besoin. Fusion de branches parallèles : deux agents qui ajoutent chacun une route dans le même `switch` / la même map Terraform / le même tableau de la spec se résolvent par **union** ; un composant déplacé par l'un (`Quiz` → `quiz.tsx`) et étendu par l'autre (`ExamQuestion` à côté) se résout en suivant le déplacement. Dette assumée : `QG#`/`X#`/`N#` restent sur la table `progress` en accès direct tant que l'API n'a pas d'événements palier/reset (lot 3).
- Erreur vue : `Expected } but found EOF` (oxc, `handler.ts`) → union de deux fonctions en conflit sans la `}` fermante de la première.
- Erreur vue : `Argument of type 'string' is not assignable to parameter of type '{ id: string; domaine: string; theme: string; }'` → `markCardSeen` a changé de signature dans le lot 2, un test P2b appelait l'ancienne.
- Cartes : en attente
- Résultat : 2026-10-27, `v2-lot2-app` (4 commits) et `v2-web2` fusionnés (e39c796) ; apply 1 ajout / 4 changements / 0 destruction ; PWA et site redéployés ; tests shared 69, ui 24, web 26, app 335.

### [x] Étape 10 — Lot 3 : palier/reset par l'API, fin de l'accès DynamoDB direct, écrans Tailwind, maîtrise ; revue sécurité
- À faire : événements `palier` et `reset` (`POST /events`, aggregates, réconciliation), `POST /me/push`, suppression du rôle du pool d'identités ; écrans restants en Tailwind + preflight, `TYPE_LABELS` et formule de maîtrise dans `@revision/shared`, « À réviser » (`/revision`), « Prochaines cartes » (`GET /me/next`), lien `/?competence=<id>` ; revue indépendante du diff `main…v2` et correctifs.
- Vérifier : `POST /events` kind `reset` portée `reponses` puis `GET /me/progress` → lignes `CARD#`/`THEME#`/`TOTAL` à `ok: 0, ko: 0`, `vues` conservées, ligne `RESET#reponses` ; `curl -s -o /dev/null -w "%{http_code}" https://d1non6rpr4vppb.cloudfront.net/examens` → `200` ; bundle de l'app sans `AssumeRoleWithWebIdentity`.
- Cours : une **remise à zéro est un événement** comme un autre, daté : elle efface les agrégats de sa portée pour les événements datés avant elle et jamais ceux datés après ; un événement antérieur arrivé en retard est ignoré (le serveur lit `RESET#`), un événement postérieur déjà compté est rejoué depuis le journal ; `RESET#` et `DONE#` s'écrivent en dernier, dans la même transaction, pour qu'une interruption se rejoue sans risque. Supprimer le dernier accès direct à la base depuis le client (`N#` → `POST /me/push`) permet de détruire le rôle IAM du pool d'identités : le pool ne sert plus qu'à `GetId` pour la migration. Une revue indépendante sur le diff complet trouve ce que les auteurs ne voient plus : contenu premium dans un fichier hérité public (latent : aucun thème premium encore), examens qui lisent les tranches premium avec le rôle de la Lambda, cache de secret sans durée (rotation impossible à chaud). Un correctif de revue se vérifie au typage : `sansPremium` lisait `domaine/theme`, les cartes portent `langage/cours`.
- Erreur vue : `Argument of type 'Catalog' is not assignable to parameter of type '{ cards: { domaine: string; theme: string; }[]; }'` → noms de champs du format v3 (`langage`, `cours`), pas ceux de l'index.
- Erreur vue : tests `findBy` en échec intermittent quand les projets vitest `node` et `dom` tournent ensemble → `configure({ asyncUtilTimeout: 4000 })` dans `setup-dom.ts`.
- Cartes : en attente
- Résultat : 2026-10-28, `v2-lot3-api` et `v2-lot3-ui` fusionnés sans conflit (89a759f) ; revue : 12 constats, 4 corrigés (56c3027), 8 listés dans `revision-pwa/docs/v2-merge-notes.md` ; 2 `make up` (3 Lambdas ; puis 1 ajout / 10 chg / 3 destructions IAM non stateful) ; app et site redéployés ; tests shared 72, ui 27, web 26, app 373.

## Critères de validation
- Ouverture de l'app : moins de 100 Ko téléchargés hors tranches, indépendant du nombre de cartes.
- `make check` vert sur `v2` ; `make plan` sans destruction de ressource stateful.
- Site statique : une page par carte avec meta + JSON-LD, servie par CloudFront.
- Progression : aucune écriture DynamoDB directe depuis le client ; agrégats visibles via `GET /me/progress`.

## Question de compréhension
Pourquoi un certificat calculé à partir de la table `progress` actuelle ne vaudrait rien, et qu'est-ce qui change avec `events` + `aggregates` ?

## Journal
- 2026-10-27 : étude, contrat, Trello, branches ; 4 agents lancés en parallèle (P0, Tailwind, Web, API). Agent P0 arrêté après 2 min (cause inconnue), relancé. API (19 min), Web (32 min), Tailwind (38 min) terminés et intégrés sur `v2` ; `make up` ×2 (28 puis 20 ressources) ; site en ligne ; test de bout en bout de l'API avec un utilisateur Cognito de test. P2a (registre compétences, 6 min), P3 (22 min), P4 (25 min), intégration P0 (14 min) ; correctif createRequire ; 3e et 4e `make up` ; PWA v2, site et API en ligne sur dev. Lot 2 lancé (3 agents). P2b (36 min) intégré, 5e `make up` ; lot2-app (90 min) et web2 (89 min) fusionnés avec 7 conflits (union), 6e `make up`, app et site redéployés, smoke test API (identity, events, progress, next). Lot 3 lancé (2 agents : API palier/reset + types partagés ; écrans Tailwind + maîtrise + lien `?competence=`). Nuit en autonomie (carte blanche) : CloudFront Function spa-index, revue sécurité (7 min, 12 constats) et 4 correctifs, lot 3 API (10 h 33) et UI (10 h 32) fusionnés, 7e et 8e `make up`, note de merge `docs/v2-merge-notes.md`.
