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

### [ ] Étape 1 — P0 : catalogue en tranches et monorepo `packages/shared`
- À faire : voir carte Trello v2-P0.

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

### [ ] Étape 5 — Intégration sur `v2`, `make up`, déploiement dev
### [ ] Étape 6 — P2 : compétences
### [ ] Étape 7 — P3 : premium et Stripe
### [ ] Étape 8 — P4 : examens et certificat

## Critères de validation
- Ouverture de l'app : moins de 100 Ko téléchargés hors tranches, indépendant du nombre de cartes.
- `make check` vert sur `v2` ; `make plan` sans destruction de ressource stateful.
- Site statique : une page par carte avec meta + JSON-LD, servie par CloudFront.
- Progression : aucune écriture DynamoDB directe depuis le client ; agrégats visibles via `GET /me/progress`.

## Question de compréhension
Pourquoi un certificat calculé à partir de la table `progress` actuelle ne vaudrait rien, et qu'est-ce qui change avec `events` + `aggregates` ?

## Journal
- 2026-10-27 : étude, contrat, Trello, branches ; 4 agents lancés en parallèle (P0, Tailwind, Web, API). Agent P0 arrêté après 2 min (cause inconnue), relancé. API (19 min), Web (32 min), Tailwind (38 min) terminés et intégrés sur `v2` ; `make up` ×2 (28 puis 20 ressources) ; site en ligne ; test de bout en bout de l'API avec un utilisateur Cognito de test.
