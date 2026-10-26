---
title: "Cartes · Vite"
type: cartes
langage: Web
chapitre: Application
cours: Vite
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Vite
Web · Vite : variables d'environnement, build, tests avec Vitest (format spec v3 de revision-pwa).

## 1. VITE_ : seules ces variables arrivent dans le code
- Id : vite-prefixe-vite-seul-expose
- Sous-thème : env
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Voir aussi : vite-variables-publiques
- Mots-clés : fichier .env, bundle
- Source : data-platform · pwa-sync
- Définition : `import.meta.env` ne contient que les variables préfixées `VITE_` (plus `MODE`, `DEV`, `PROD`, `BASE_URL`, `SSR`) ; les autres valent `undefined`.
- Contexte : Le préfixe est un filtre de sécurité : un `.env` contient souvent des secrets de build ou de déploiement qui ne doivent pas finir dans le bundle. Contrairement à `process.env` côté Node (tout l'environnement), le front ne voit que ce qu'on a explicitement nommé `VITE_*`. Le préfixe se change avec `envPrefix` dans `vite.config.ts`, rarement utile.
- Usage : ✅ `VITE_IDENTITY_POOL_ID`, `VITE_PROGRESS_TABLE` : configuration publique du front · ❌ lire `import.meta.env.API_SECRET` : `undefined`, et c'est voulu.

```js
// Exemple 1 : mesuré, .env avec
//   VITE_REGION=eu-west-3
//   SECRET_KEY=s3cr3t
import.meta.env.VITE_REGION  // → 'eu-west-3'
import.meta.env.SECRET_KEY   // → undefined
// bundle : aucune trace de « s3cr3t »
```

- Quiz : `.env` contient `REGION=eu-west-3` (sans préfixe). Que vaut `import.meta.env.REGION` dans l'app ?
- [ ] `'eu-west-3'`
- [x] `undefined`
- [ ] `''`
- [ ] Erreur de build
- Réponse : `undefined` : sans le préfixe `VITE_`, Vite n'expose pas la variable ; aucun avertissement au build.

## 2. import.meta.env : remplacé au build
- Id : vite-env-remplace-au-build
- Sous-thème : env
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Voir aussi : vite-acces-dynamique-objet-complet
- Mots-clés : bundle, CodeBuild, output Terraform
- Source : data-platform · pwa-sync
- Définition : `vite build` remplace chaque `import.meta.env.VITE_X` par sa valeur littérale : la configuration est figée dans le bundle, pas lue au chargement.
- Contexte : Le JS servi par CloudFront contient `"eu-west-3"` en dur. Changer une variable demande donc de reconstruire et redéployer ; il n'y a pas d'environnement d'exécution pour un fichier statique. D'où, dans revision-pwa, les `VITE_*` passées au build CodeBuild à partir des outputs Terraform. Un même bundle ne peut pas servir deux environnements avec deux valeurs.
- Usage : ✅ configuration connue au build (région, pool, table) · ❌ valeur à changer sans redéployer : la charger au démarrage (fichier `config.json` servi à côté).

```js
// Exemple 1 : mesuré, source puis bundle
console.log(import.meta.env.VITE_REGION)
// dist/assets/index-….js :
console.log(`eu-west-3`)
```

- Quiz : On change `VITE_PROGRESS_TABLE` dans l'environnement de CodeBuild, sans relancer de build. L'app déployée ?
- [ ] Lit la nouvelle table au prochain chargement
- [x] Garde l'ancienne : la valeur est dans le JS
- [ ] Plante : variable incohérente
- [ ] Lit la nouvelle après invalidation CloudFront
- Réponse : l'ancienne : la valeur a été écrite dans le bundle au dernier build ; il faut reconstruire puis redéployer (et invalider le cache).

## 3. valeurs : toujours des chaînes
- Id : vite-valeurs-toujours-chaines
- Sous-thème : env
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Voir aussi : AWS/lambda-variables-env-chaines
- Mots-clés : fichier .env
- Source : data-platform · pwa-sync
- Définition : Une variable `VITE_*` arrive toujours en chaîne : `VITE_SYNC=false` donne `'false'`, une valeur vraie dans un `if`.
- Contexte : Le `.env` et l'environnement du shell ne connaissent que du texte ; Vite ne convertit rien (seuls `DEV`, `PROD`, `SSR` sont des booléens). Le piège classique est un drapeau désactivé qui reste actif. On compare explicitement (`=== 'true'`) ou on teste la présence, comme cloud.ts qui crée le client seulement si les trois variables sont définies.
- Usage : ✅ `import.meta.env.VITE_SYNC === 'true'`, `Number(…)` pour un nombre · ❌ `if (import.meta.env.VITE_SYNC)` pour un booléen.

```js
// Exemple 1 : mesuré, .env : VITE_SYNC=false
typeof import.meta.env.VITE_SYNC
// → 'string'
import.meta.env.VITE_SYNC ? 'actif' : 'coupé'
// → 'actif'  ⚠️ 'false' est vraie
```

- Quiz : `VITE_SYNC=` (vide) dans `.env`. Que vaut `!!import.meta.env.VITE_SYNC` ?
- [ ] `true` : la variable existe
- [x] `false` : chaîne vide
- [ ] `undefined`
- [ ] Erreur de build
- Réponse : `false` (mesuré) : une variable vide arrive en `''`, valeur fausse ; seule une chaîne non vide (même `'false'` ou `'0'`) est vraie.

## 4. VITE_ : public par construction
- Id : vite-variables-publiques
- Sous-thème : env
- Type : piège
- Niveau : 1
- Profils : débutant, web, ops
- Prérequis : vite-prefixe-vite-seul-expose
- Mots-clés : bundle, Cognito, Secrets Manager
- Source : data-platform · pwa-sync
- Définition : Une variable `VITE_*` lue par le code est lisible par n'importe qui dans le bundle : jamais de secret dans une `VITE_*`.
- Contexte : Un identity pool id, un client id Cognito, un nom de table sont des identifiants, pas des secrets : la sécurité vient de la signature et d'IAM. Une clé d'API tierce, un secret de client, une clé AWS, eux, deviennent publics dès qu'ils passent par `VITE_`. Ce qui doit rester secret vit côté serveur (Lambda, Secrets Manager).
- Usage : ✅ identifiants publics : pool, client id, région, URL d'API · ❌ secret de client OAuth, clé AWS, clé d'API payante.

```bash
# Exemple 1 : la valeur se lit dans le bundle
grep -o 'eu-west-3:[0-9a-f-]*' dist/assets/*.js
# → l'identity pool id, en clair
# (normal : c'est un identifiant public)
```

- Quiz : On met `VITE_ANTHROPIC_KEY` dans `.env.local` (gitignoré) et on la lit dans l'app. Protégée ?
- [ ] Oui : `.env.local` n'est pas commité
- [ ] Oui : Vite chiffre les variables `VITE_`
- [x] Non : elle est en clair dans le JS servi
- [ ] Oui, si le build est minifié
- Réponse : non : gitignorer protège le dépôt, pas le bundle ; la valeur est écrite telle quelle dans le JS envoyé à chaque visiteur.

## 5. NODE_ENV : le build de dev caché
- Id : vite-node-env-build-de-dev
- Sous-thème : build
- Type : piège
- Niveau : 2
- Profils : web, ops
- Voir aussi : vite-dev-suit-node-env
- Mots-clés : bundle
- Source : revision-pwa · pwa-revision
- Définition : `vite build` remplace `process.env.NODE_ENV` dans le code ; s'il vaut `development`, React part dans sa version de dev, deux fois plus lourde.
- Contexte : Vite ne force `production` que si la variable est vide. Un `export NODE_ENV=development` dans `~/.zshrc` embarque donc les contrôles et messages de dev de React (« unique key… ») dans le bundle, sans erreur ni avertissement. D'où `"build": "tsc -b && NODE_ENV=production vite build"` dans `app/package.json`.
- Usage : ✅ fixer `NODE_ENV=production` dans le script `build` · ❌ compter sur l'environnement du shell ou de la CI pour obtenir un build de prod.

```bash
# Exemple 1 : même code, mesuré
NODE_ENV=production vite build
# → index.js 219 kB
NODE_ENV=development vite build
# → index.js 427 kB, avec les
#   messages de dev de React
```

- Quiz : Shell sans `NODE_ENV`, `vite build --mode development` : quel React part dans le bundle ?
- [ ] Développement : le mode fixe `NODE_ENV`
- [x] Production : le mode ne touche pas `NODE_ENV`
- [ ] Développement, avec un avertissement de Vite
- [ ] Aucun : Vite refuse ce mode en build
- Réponse : production (mesuré : 219 kB, Vite 8.3) : `--mode` choisit les fichiers `.env.[mode]` et `import.meta.env.MODE`, pas `NODE_ENV`, qui reste `production` en build.

## 6. priorité : le shell passe avant .env
- Id : vite-priorite-shell-avant-env
- Sous-thème : env
- Type : concept
- Niveau : 2
- Profils : web, ops
- Mots-clés : fichier .env, CodeBuild, variable d'environnement
- Source : data-platform · pwa-sync
- Définition : Une variable `VITE_*` déjà définie dans l'environnement du processus (shell, CI) l'emporte sur la même variable des fichiers `.env*`.
- Contexte : Vite charge `.env`, `.env.local`, `.env.[mode]`, `.env.[mode].local` (le plus spécifique gagne), mais n'écrase jamais une variable déjà exportée. En CI, aucun `.env.local` : les `VITE_*` viennent de l'environnement du build (CodeBuild), alimenté par Terraform. En local, une variable exportée par erreur dans `~/.zshrc` masque silencieusement `.env.local`.
- Usage : ✅ CI : `VITE_*` en variables d'environnement du build ; local : `.env.local` · ❌ commiter un `.env` avec les valeurs d'un environnement réel.

```bash
# Exemple 1 : mesuré, .env : VITE_FROM_ENV=env
vite build
# bundle → `env`
VITE_FROM_ENV=shell vite build
# bundle → `shell`
```

- Quiz : `.env` : `VITE_A=1`, `.env.local` : `VITE_A=2`, shell sans `VITE_A`. Valeur dans le bundle ?
- [ ] `'1'` : `.env` est lu en premier
- [x] `'2'` : `.env.local` est plus spécifique
- [ ] `'1,2'`
- [ ] Erreur : variable en double
- Réponse : `'2'` (mesuré) : à mode égal, `.env.local` passe devant `.env` ; seule une variable du shell l'emporterait.

## 7. Vitest : .env et .env.local chargés aussi
- Id : vite-vitest-charge-env
- Sous-thème : tests
- Type : concept
- Niveau : 2
- Profils : web
- Voir aussi : vite-priorite-shell-avant-env
- Mots-clés : fichier .env
- Source : data-platform · pwa-sync
- Définition : Vitest charge les fichiers `.env*` comme Vite, en mode `test` : un test voit les `VITE_*` de `.env.local` et de l'environnement.
- Contexte : Le code testé lit donc la même configuration qu'en développement : un module qui agit dès que `VITE_PROGRESS_TABLE` est définie le fera aussi pendant les tests, sur le poste comme en CI. `import.meta.env.MODE` vaut `'test'` et `DEV` vaut `true`. Pour un test indépendant de la config, on injecte les valeurs (`createCloud({ … })`) au lieu de lire `import.meta.env`.
- Usage : ✅ tests qui injectent leur configuration et leurs dépendances · ❌ tests dont le résultat dépend du `.env.local` du poste.

```js
// Exemple 1 : mesuré dans un test Vitest
// .env : VITE_REGION=eu-west-3
// .env.local : VITE_LOCAL=local
import.meta.env.VITE_REGION // → 'eu-west-3'
import.meta.env.VITE_LOCAL  // → 'local'
import.meta.env.MODE        // → 'test'
import.meta.env.DEV         // → true
```

- Quiz : Dans un test Vitest, que vaut `import.meta.env.PROD` ?
- [ ] `true` : `vitest run` est un build
- [x] `false`
- [ ] `undefined` : réservé au build
- [ ] `'test'`
- Réponse : `false` (mesuré) : en mode `test`, `DEV` vaut `true` et `PROD` `false` ; `MODE` porte la chaîne `'test'`.

## 8. effet de bord à l'import : localStorage is not defined
- Id : vite-effet-de-bord-a-limport
- Sous-thème : tests
- Type : piège
- Niveau : 2
- Profils : web
- Voir aussi : vite-vitest-environnement-node
- Mots-clés : module ES, CodeBuild
- Source : data-platform · pwa-sync
- Définition : Le code au niveau d'un module s'exécute dès qu'un fichier l'importe, tests compris : lire `localStorage` à ce moment casse sous Node.
- Contexte : Erreur vue dans revision-pwa : le premier build CodeBuild a échoué avec `ReferenceError: localStorage is not defined` (`src/cloud.ts:61`). En CI, les `VITE_*` étaient définies, donc `cloud` était créé à l'import, et le client lisait `localStorage` tout de suite. Correction : stockage lu à l'usage (`const storage = () => config.storage ?? localStorage`), plus rien au chargement.
- Usage : ✅ au niveau module, seulement des déclarations ; accès au navigateur dans les fonctions, à l'appel · ❌ lire `localStorage`, `window` ou `document` au chargement d'un module partagé.

```js
// Exemple 1 : mesuré avec Vitest (env. node)
// store.js
export const saved = import.meta.env.VITE_REGION
  ? localStorage.getItem('k') : null
// store.test.js : import { saved } …
// → FAIL ReferenceError:
//   localStorage is not defined
```

```js
// Exemple 2 : la correction de cloud.ts
const storage = () =>
  config.storage ?? localStorage
// lu à l'usage : storage().getItem(…)
```

- Quiz : Même `store.js`, mais dans un test où `VITE_REGION` n'est pas définie. Le test ?
- [x] Passe : la branche `localStorage` n'est pas évaluée
- [ ] Échoue : l'import lit toujours `localStorage`
- [ ] Échoue : `import.meta.env` est absent sous Node
- [ ] Passe, avec un avertissement
- Réponse : passe : le ternaire n'évalue `localStorage` que si la variable est vraie ; d'où un bug qui n'apparaît qu'avec la configuration de la CI.

## 9. Vitest : environnement node, sans DOM
- Id : vite-vitest-environnement-node
- Sous-thème : tests
- Type : concept
- Niveau : 2
- Profils : web
- Voir aussi : web-crypto-node-subtle-global
- Mots-clés : jsdom
- Source : data-platform · pwa-sync
- Définition : Par défaut, Vitest exécute les tests sous Node (`environment: 'node'`) : `fetch` et `crypto` existent, `localStorage`, `window` et `document` non.
- Contexte : `jsdom` ou `happy-dom` simulent le DOM, mais s'installent à part et ralentissent les tests. Pour un module comme cloud.ts, plus simple et plus juste : injecter `fetch` et le stockage (`memoryStorage()` dans le test) et rester en `node`. On ne teste que ce qu'on contrôle, sans faux navigateur.
- Usage : ✅ logique (client AWS, calculs) testée en `node` avec dépendances injectées · ❌ passer tout le projet en `jsdom` pour un seul `localStorage`.

```js
// Exemple 1 : mesuré dans un test Vitest
typeof fetch         // → 'function'
typeof crypto.subtle // → 'object'
typeof localStorage  // → 'undefined'
typeof window        // → 'undefined'
```

- Quiz : Sans configuration, un test Vitest appelle `document.querySelector('h1')`. Résultat ?
- [ ] `null` : aucun `h1` dans la page
- [x] `ReferenceError: document is not defined`
- [ ] `TypeError` : `querySelector` absent
- [ ] Un `h1` vide fourni par Vitest
- Réponse : `ReferenceError` : l'environnement par défaut est `node`, sans DOM ; il faut `environment: 'jsdom'` (ou `happy-dom`) ou ne pas toucher au DOM dans ce module.

## 10. import.meta.env[clé] : tout l'objet dans le bundle
- Id : vite-acces-dynamique-objet-complet
- Sous-thème : build
- Type : piège
- Niveau : 3
- Profils : web, expert
- Prérequis : vite-env-remplace-au-build
- Mots-clés : bundle, minifieur
- Source : data-platform · pwa-sync
- Définition : Un accès dynamique `import.meta.env[cle]` ne peut pas être remplacé par une valeur : Vite insère l'objet complet de toutes les variables `VITE_*`.
- Contexte : Le remplacement statique ne marche que sur une expression écrite en toutes lettres (`import.meta.env.VITE_REGION`). Avec une clé calculée, Vite écrit `{BASE_URL:…, MODE:…, VITE_A:…, VITE_B:…}[cle]` : toutes les `VITE_*` du build atterrissent dans le bundle, même celles qu'aucun code ne lit. Le minifieur ne peut plus rien supprimer.
- Usage : ✅ accès littéraux, un par variable · ❌ boucle ou fonction utilitaire `env(cle)` sur `import.meta.env`.

```js
// Exemple 1 : mesuré, source puis bundle
const k = 'VITE_REGION'
console.log(import.meta.env[k])
// dist :
// {BASE_URL:`/`,DEV:!1,MODE:`production`,
//  PROD:!0,SSR:!1,VITE_LOCAL:`local`,
//  VITE_REGION:`eu-west-3`,…}.VITE_REGION
```

- Quiz : Une `VITE_DEBUG_TOKEN` jamais lue par le code, mais un `import.meta.env[k]` ailleurs. Dans le bundle ?
- [ ] Non : Vite n'inclut que les variables lues
- [x] Oui : l'objet complet est inséré
- [ ] Non : le minifieur la retire
- [ ] Oui, mais chiffrée
- Réponse : oui : l'accès dynamique force l'objet entier des `VITE_*` dans le JS, variables inutilisées comprises.

## 11. DEV en build : il suit NODE_ENV
- Id : vite-dev-suit-node-env
- Sous-thème : build
- Type : piège
- Niveau : 3
- Profils : web, expert
- Prérequis : vite-node-env-build-de-dev
- Mots-clés : NODE_ENV, bundle, minifieur
- Source : data-platform · pwa-sync
- Définition : Dans `vite build`, `import.meta.env.DEV` et `PROD` suivent `NODE_ENV`, alors que `MODE` reste `'production'` : un `NODE_ENV=development` exporté laisse `DEV` à `true`.
- Contexte : Complément de la carte NODE_ENV : ce n'est pas seulement React qui part en version de dev, ce sont aussi les branches du code de l'app `if (import.meta.env.DEV)` (logs, outils de debug) qui restent dans le bundle de production. `MODE` ne bouge pas : un test sur `MODE` et un test sur `DEV` peuvent donc se contredire dans le même build.
- Usage : ✅ fixer `NODE_ENV=production` dans le script `build`, tester `DEV`/`PROD` pour le code de debug · ❌ mélanger `MODE` et `DEV` pour la même décision.

```js
// Exemple 1 : mesuré, même source, deux builds
// NODE_ENV=development vite build
MODE, DEV, PROD  // → 'production', true, false
// NODE_ENV=production vite build
MODE, DEV, PROD  // → 'production', false, true
```

- Quiz : Shell avec `NODE_ENV=development`, `vite build` : le bloc `if (import.meta.env.PROD) {…}` est-il dans le bundle ?
- [ ] Oui, et il s'exécute
- [x] Non : `PROD` vaut `false`, code retiré
- [ ] Oui : `MODE` vaut `'production'`
- [ ] Erreur de build
- Réponse : non (mesuré : `PROD` = `false`) : la condition devient `if (false)` et le minifieur supprime le bloc ; le code « de production » manque au bundle de production.
