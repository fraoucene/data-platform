---
title: "Cartes · Modules ES"
type: cartes
langage: Web
chapitre: Application
cours: Modules ES
created: 2026-10-26
updated: 2026-10-26
---

# Cartes · Modules ES
Web · Modules ES : import statique et dynamique, modules JSON et import attributes, TypeScript, Vite.

## 1. import JSON : with { type: 'json' }
- Id : modules-es-import-json-with
- Sous-thème : json
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Voir aussi : modules-es-import-ou-fetch
- Source : revision-pwa · pwa-parcours
- Définition : `import d from './d.json' with { type: 'json' }` charge un fichier JSON comme module ; l'attribut `type` déclare ce qu'on attend.
- Contexte : Les import attributes (ES2025) disent à l'hôte comment traiter le fichier. Node les exige pour le JSON : sans `with`, `ERR_IMPORT_ATTRIBUTE_MISSING` (mesuré, Node 22). Vite l'accepte et met le JSON dans le bundle. C'est ainsi que `parcours.ts` charge `spec/parcours.json` : la spec reste un fichier JSON lisible, l'app la reçoit typée, sans `fetch`.
- Usage : ✅ données fixes livrées avec le code (registre, configuration, table de traduction) · ❌ données qui changent sans redéployer (catalogue) : `fetch`.

```js
// Exemple 1 : comme parcours.ts
import spec from '../../spec/parcours.json'
  with { type: 'json' }
spec.parcours.length   // 8
```

```js
// Exemple 2 : sans attribut (Node 22)
import spec from './parcours.json'
// TypeError [ERR_IMPORT_ATTRIBUTE_MISSING]:
// needs an import attribute of "type: json"
```

- Quiz : Dans Node 22, `with { type: 'css' }` sur un `.json` : que se passe-t-il ?
- [ ] Le fichier est lu comme JSON quand même
- [ ] L'attribut est ignoré
- [x] `ERR_IMPORT_ATTRIBUTE_UNSUPPORTED`
- [ ] Il est chargé comme feuille de style
- Réponse : `ERR_IMPORT_ATTRIBUTE_UNSUPPORTED` (mesuré) : Node ne connaît que `type: 'json'` ; l'attribut est vérifié, ce n'est pas un simple indice.

## 2. module JSON : un seul export, default
- Id : modules-es-json-export-default
- Sous-thème : json
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Prérequis : modules-es-import-json-with
- Voir aussi : modules-es-vite-tree-shaking-json
- Source : revision-pwa · pwa-parcours
- Définition : Un module JSON n'exporte que `default`, l'objet entier : `import { version } from './d.json' with { type: 'json' }` échoue dans Node.
- Contexte : Mesuré (Node 22) : `SyntaxError: The requested module './d.json' does not provide an export named 'version'`. Vite, lui, accepte les imports nommés de JSON : un code qui marche en dev peut casser dans un script Node (`tsx scripts/…`). Importer l'objet puis déstructurer marche partout.
- Usage : ✅ `import d from … with { type: 'json' }` puis `const { version } = d` · ❌ import nommé dans un code partagé entre Vite et Node.

```js
// Exemple 1 : portable Node et Vite
import d from './d.json'
  with { type: 'json' }
const { version } = d
```

```js
// Exemple 2 : refusé par Node 22
import { version } from './d.json'
  with { type: 'json' }
// SyntaxError: The requested module
// './d.json' does not provide an export
// named 'version'
```

- Quiz : Avec `import * as m from './d.json' with { type: 'json' }`, que vaut `Object.keys(m)` ?
- [ ] Les clés du JSON
- [ ] `[]`
- [x] `['default']`
- [ ] `SyntaxError`
- Réponse : `['default']` (mesuré) : l'espace de noms d'un module JSON n'a qu'une entrée ; les clés du fichier sont dans `m.default`.

## 3. import statique : hissé en tête
- Id : modules-es-import-hisse
- Sous-thème : import
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Voir aussi : vite-effet-de-bord-a-limport, modules-es-import-dynamique
- Source : revision-pwa · pwa-parcours
- Définition : Un `import` statique est hissé : le module importé s'exécute avant la première ligne de l'importeur, où que soit écrit l'`import`.
- Contexte : Mesuré : un `console.log` écrit avant l'`import` s'affiche après le code du module importé. Un `import` ne peut donc pas être conditionnel, et un effet de bord au chargement (lecture de `localStorage`) s'exécute dès l'import, avant le code de l'appelant. Pour charger à la demande : `await import(…)`.
- Usage : ✅ imports en tête de fichier, modules sans effet de bord au chargement · ❌ importer « plus tard » : `import()` dynamique.

```js
// Exemple 1 : mesuré dans Node 22
// dep.mjs : console.log('dep évalué')
console.log('début du module')
import { x } from './dep.mjs'
// affiché : dep évalué
//           début du module
```

- Quiz : Que donne `if (dev) { import d from './d.json' with { type: 'json' } }` ?
- [ ] L'import n'a lieu que si `dev` est vrai
- [ ] L'import a lieu dans tous les cas
- [x] `SyntaxError` au chargement du module
- [ ] Un avertissement, puis l'import
- Réponse : `SyntaxError` (mesuré : `Unexpected identifier 'd'`) : `import` statique n'est permis qu'au niveau du module ; dans un bloc, il faut `await import(…)`.

## 4. import() : charger à la demande
- Id : modules-es-import-dynamique
- Sous-thème : import
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Prérequis : modules-es-import-hisse
- Source : revision-pwa · pwa-parcours
- Définition : `await import(chemin, { with: { type: 'json' } })` charge un module à la demande ; le JSON est dans `default`.
- Contexte : L'appel dynamique accepte une expression et peut être conditionnel. Il renvoie une promesse de l'objet module : pour un JSON, une seule clé, `default`. Les attributs passent dans un second argument `{ with: { … } }`. Vite en fait un fichier séparé, chargé au premier appel.
- Usage : ✅ données lourdes ou rares (gros dictionnaire, écran peu visité) · ❌ données du premier écran : import statique, sans aller-retour réseau.

```js
// Exemple 1 : mesuré dans Node 22
const m = await import('./d.json',
  { with: { type: 'json' } })
Object.keys(m)     // ['default']
m.default.version  // 4
```

- Quiz : Dans l'exemple, que vaut `m.version` ?
- [ ] `4`
- [x] `undefined`
- [ ] `TypeError`
- [ ] `null`
- Réponse : `undefined` : `m` est l'espace de noms du module, sa seule clé est `default` ; la donnée est dans `m.default.version`.

## 5. assert : l'ancienne syntaxe
- Id : modules-es-assert-obsolete
- Sous-thème : json
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : modules-es-import-json-with
- Source : revision-pwa · pwa-parcours
- Définition : `assert { type: 'json' }`, l'ancienne syntaxe, est remplacée par `with { type: 'json' }` ; Node 22 la refuse.
- Contexte : La proposition s'appelait « import assertions » (`assert`), puis est devenue « import attributes » (`with`) : l'attribut peut influer sur le chargement, pas seulement le vérifier. Mesuré : Node 22 lève `SyntaxError: Unexpected identifier 'assert'`. Des tutoriels et des réponses générées montrent encore `assert` : changer le mot suffit.
- Usage : ✅ `with` partout (Node 22, navigateurs récents, TypeScript 5.3 et plus, Vite) · ❌ `assert`, copié d'un vieil exemple.

```js
// Exemple 1 : refusé par Node 22
import d from './d.json'
  assert { type: 'json' }
// SyntaxError: Unexpected identifier
// 'assert'
```

```js
// Exemple 2 : la forme actuelle
import d from './d.json'
  with { type: 'json' }
```

- Quiz : Et en dynamique : `await import('./d.json', { assert: { type: 'json' } })` dans Node 22 ?
- [ ] Ça marche : `assert` reste accepté ici
- [ ] `SyntaxError` sur `assert`
- [x] `ERR_IMPORT_ATTRIBUTE_MISSING`
- [ ] Le JSON est chargé comme du JavaScript
- Réponse : `ERR_IMPORT_ATTRIBUTE_MISSING` (mesuré) : la clé `assert` de l'objet d'options est ignorée en silence, Node ne voit aucun attribut.

## 6. module : un seul objet partagé
- Id : modules-es-singleton-partage
- Sous-thème : import
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : modules-es-import-json-with
- Source : revision-pwa · pwa-parcours
- Définition : Un module n'est évalué qu'une fois : tous les imports d'un même JSON reçoivent le même objet, et une mutation se voit partout.
- Contexte : Mesuré (Node 22) : après `d1.version = 99`, un `import()` du même fichier lit `99`, et les deux références sont `===`. Trier ou enrichir sur place l'objet de `domaines.json` dans un composant change donc ce que voient tous les autres. Copier avant de transformer.
- Usage : ✅ traiter un JSON importé comme une constante, copier avant de transformer · ❌ `spec.parcours.sort(…)` sur place.

```js
// Exemple 1 : mesuré dans Node 22
import d1 from './d.json'
  with { type: 'json' }
const m = await import('./d.json',
  { with: { type: 'json' } })
d1.version = 99
m.default.version   // 99
m.default === d1    // true
```

- Quiz : Quelle écriture trie les parcours sans toucher l'objet importé ?
- [ ] `spec.parcours.sort(cmp)`
- [x] `[...spec.parcours].sort(cmp)`
- [ ] `Object.freeze(spec).parcours.sort(cmp)`
- [ ] `spec.parcours.reverse().sort(cmp)`
- Réponse : `[...spec.parcours].sort(cmp)` (ou `toSorted`) : la copie est triée, l'objet partagé reste intact ; `Object.freeze` est superficiel et n'empêche pas de trier le tableau intérieur.

## 7. TypeScript : with selon l'option module
- Id : modules-es-ts-option-module
- Sous-thème : typescript
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : modules-es-import-json-with
- Source : revision-pwa · pwa-parcours
- Définition : TypeScript n'accepte `with { type: 'json' }` que si `module` vaut `esnext`, `node18`, `node20`, `nodenext` ou `preserve` ; sinon erreur TS2823.
- Contexte : Mesuré avec TypeScript 6 : `--module es2022` refuse l'attribut. L'app (`module: esnext`, `moduleResolution: bundler`) et les scripts (`module: nodenext`) l'acceptent. `resolveJsonModule` donne en plus au JSON un type déduit de son contenu.
- Usage : ✅ `module: esnext` (Vite) ou `nodenext` (Node) · ❌ `es2020` ou `es2022` hérités d'un vieux tsconfig.

```bash
# Exemple 1 : mesuré avec TypeScript 6
tsc --module es2022 a.ts
# error TS2823: Import attributes are only
# supported when the '--module' option is
# set to 'esnext', 'node18', 'node20',
# 'nodenext', or 'preserve'.
tsc --module esnext a.ts    # OK
```

- Quiz : `target: es2023` mais `module: es2022`. `with { type: 'json' }` passe-t-il ?
- [ ] Oui : `target` récent suffit
- [x] Non : TS2823, seul `module` compte
- [ ] Oui, avec un avertissement
- Réponse : non (mesuré) : `target` règle la syntaxe émise, `module` le système de modules ; l'attribut dépend du second.

## 8. nodenext : les règles de Node
- Id : modules-es-ts-nodenext-json
- Sous-thème : typescript
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : modules-es-ts-option-module
- Source : revision-pwa · pwa-parcours
- Définition : Avec `module: nodenext`, TypeScript applique les règles de Node : un JSON importé dans un module ES exige `with { type: 'json' }` (TS1543).
- Contexte : TypeScript reproduit à la compilation ce que Node ferait à l'exécution ; avec `esnext` (bundler), il laisse passer l'import sans attribut, que Vite accepte. Écrire l'attribut partout rend le même fichier valide dans les deux configurations : c'est pourquoi `data.ts` et `progress.ts` l'écrivent alors que Vite n'en a pas besoin.
- Usage : ✅ l'attribut sur tout import JSON, même sous Vite · ❌ compter sur `esnext` qui laisse passer : le même fichier cassera sous Node.

```bash
# Exemple 1 : mesuré avec TypeScript 6
# b.ts : import d from './d.json'
tsc --module nodenext b.ts
# error TS1543: Importing a JSON file into
# an ECMAScript module requires a 'type:
# "json"' import attribute when 'module'
# is set to 'NodeNext'.
tsc --module esnext b.ts     # OK
```

- Quiz : Avec `nodenext`, que dit `tsc` de `import { version } from './d.json' with { type: 'json' }` ?
- [ ] Rien : l'attribut est présent
- [ ] TS2823 : attribut non supporté
- [x] TS1544 : import nommé de JSON interdit
- [ ] TS2339 : `version` inconnue
- Réponse : TS1544 (mesuré) : comme Node, `nodenext` n'autorise que l'import par défaut d'un JSON.

## 9. JSON importé : des types élargis
- Id : modules-es-json-types-larges
- Sous-thème : typescript
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : modules-es-ts-option-module
- Source : revision-pwa · pwa-parcours
- Définition : Le type déduit d'un JSON importé élargit les chaînes en `string` : un champ `"type": "concept"` ne satisfait pas une union `'concept' | 'piège'`.
- Contexte : Mesuré (TS 6) : `const x: T = t.type` donne TS2322. On ne peut pas écrire `as const` sur un import. D'où le cast unique de `parcours.ts` : `parcoursSpec.parcours as ParcoursDef[]`. Le cast ne vérifie rien à l'exécution : une faute dans le JSON passe, et seul un test qui valide le fichier la voit.
- Usage : ✅ un cast vers le type métier à un seul endroit, plus un test qui valide le JSON · ❌ des casts dispersés, ou `any`.

```ts
// Exemple 1 : mesuré avec TypeScript 6
// t.json : { "type": "concept" }
import t from './t.json'
  with { type: 'json' }
type T = 'concept' | 'piège'
const x: T = t.type
// error TS2322: Type 'string' is not
// assignable to type 'T'.
```

```ts
// Exemple 2 : cast unique (parcours.ts)
export const PARCOURS =
  parcoursSpec.parcours as ParcoursDef[]
```

- Quiz : Et `const n: number = d.version` avec `{ "version": 4 }` ?
- [x] Accepté : `version` est typé `number`
- [ ] TS2322 : `version` est typé `4`
- [ ] TS2322 : `version` est typé `any`
- [ ] Refusé : un nombre JSON est une `string`
- Réponse : accepté (mesuré) : les nombres sont élargis en `number` comme les chaînes en `string` ; seul un type littéral ou une union demande un cast.

## 10. JSON : import ou fetch
- Id : modules-es-import-ou-fetch
- Sous-thème : json
- Type : choisir
- Niveau : 2
- Profils : web, ops
- Prérequis : modules-es-import-json-with
- Source : revision-pwa · pwa-parcours
- Définition : Un JSON importé est figé dans le build et change au déploiement ; lu par `fetch`, il change à chaque publication.
- Contexte : L'app importe `domaines.json`, `parcours.json` et `ids-v3.json` : registre et table changent avec le code, et un nouveau domaine attend le déploiement de l'app. Le catalogue, lui, est lu par `fetch('/content/catalog.json')` : une carte publiée apparaît sans redéployer. Mesuré avec Vite 8 : le JSON importé est écrit dans le bundle JS.
- Usage : ✅ import : configuration et données versionnées avec le code · ✅ `fetch` : contenu publié indépendamment · ❌ importer un contenu qui doit changer sans livraison.

```ts
// Exemple 1 : les deux dans l'app
import domaines from
  '../../spec/domaines.json'
  with { type: 'json' }  // figé au build
const res = await fetch(
  '/content/catalog.json') // à chaque visite
const catalog = await res.json()
```

- Quiz : `/cartes` ajoute un domaine dans `domaines.json` et publie ses cartes. Quand son icône apparaît-elle dans l'app ?
- [ ] Immédiatement, avec les cartes
- [x] Au prochain déploiement de l'app
- [ ] Au prochain `make cards-publish`
- [ ] Jamais : l'icône vient du catalogue
- Réponse : au prochain déploiement : `domaines.json` est importé, donc figé dans le bundle ; les cartes, lues par `fetch`, arrivent tout de suite.

## 11. require ou import : JSON en CommonJS
- Id : modules-es-require-ou-import-json
- Sous-thème : import
- Type : comparaison
- Niveau : 2
- Profils : web, ops
- Prérequis : modules-es-import-json-with
- Source : revision-pwa · pwa-parcours
- Définition : En CommonJS, `require('./d.json')` lit un JSON sans attribut ; dans un module ES, Node exige `import … with { type: 'json' }`.
- Contexte : `require` est synchrone et propre à Node ; il parse le JSON et le garde en cache. Un `.mjs`, ou un `.js` sous `"type": "module"`, est un module ES : `require` n'y existe pas. Mesuré dans Node 22 : `require('./d.json').version` → `4` dans un `.cjs`. Pour un vieux paquet CommonJS depuis un module ES : `createRequire(import.meta.url)`.
- Usage : ✅ `require` dans un script CommonJS existant · ❌ `require` dans un module ES : `import` avec attribut.

```js
// Exemple 1 : script.cjs (CommonJS)
const d = require('./d.json')
console.log(d.version)   // 4
```

```js
// Exemple 2 : script.mjs (module ES)
import d from './d.json'
  with { type: 'json' }
console.log(d.version)   // 4
```

- Quiz : Dans un `.mjs`, que fait `const d = require('./d.json')` ?
- [ ] Lit le JSON comme en CommonJS
- [ ] `ERR_IMPORT_ATTRIBUTE_MISSING`
- [x] `ReferenceError: require is not defined`
- [ ] Renvoie une promesse du JSON
- Réponse : `ReferenceError` (mesuré : `require is not defined in ES module scope`) : `require` n'est injecté que dans les modules CommonJS.

## 12. Vite : import nommé et tree shaking
- Id : modules-es-vite-tree-shaking-json
- Sous-thème : vite
- Type : concept
- Niveau : 3
- Profils : web, expert
- Prérequis : modules-es-json-export-default
- Source : revision-pwa · pwa-parcours
- Définition : Avec Vite, un import nommé d'un JSON ne met dans le bundle que les valeurs utilisées ; l'import par défaut y copie l'objet entier.
- Contexte : Vite transforme le JSON en module ES avec un export par clé de premier niveau (`json.namedExports`, actif par défaut). Mesuré (Vite 8) : `import { version }` donne `console.log(4)` dans le bundle, sans le reste ; `import d` puis `d.version` y inline tout l'objet. Utile pour un gros JSON dont on lit une clé, mais l'import nommé casse sous Node.
- Usage : ✅ import nommé d'un gros JSON dans du code purement Vite · ❌ dans du code aussi exécuté par Node (scripts, Lambda) : défaut puis déstructuration.

```js
// Exemple 1 : mesuré avec Vite 8
// d.json : { "version": 4, "gros": "zzz…" }
import { version } from './d.json'
console.log(version)
// bundle : console.log(4)
```

```js
// Exemple 2 : import par défaut
import d from './d.json'
console.log(d.version)
// bundle : console.log({version:4,
//   gros:`zzz…`,nom:`x`}.version)
```

- Quiz : `import d from './d.json'` puis `const { version } = d` : le bundle garde-t-il `gros` ?
- [x] Oui : l'objet entier est inliné
- [ ] Non : la déstructuration suffit au tree shaking
- [ ] Non : Vite convertit en import nommé
- Réponse : oui (mesuré, Vite 8) : seul un import nommé permet d'écarter les autres clés ; déstructurer après coup lit l'objet complet.

## 13. Vite : import() d'un JSON, un fichier à part
- Id : modules-es-vite-chunk-json
- Sous-thème : vite
- Type : concept
- Niveau : 3
- Profils : web, expert
- Prérequis : modules-es-import-dynamique
- Voir aussi : modules-es-import-ou-fetch
- Source : revision-pwa · pwa-parcours
- Définition : Avec Vite, `import('./d.json')` produit un fichier JS séparé, chargé au premier appel, au lieu d'inliner le JSON dans le bundle principal.
- Contexte : Mesuré (Vite 8) : le build sort `assets/d-<hash>.js` à côté de `index-<hash>.js`. Le bundle initial maigrit, au prix d'un aller-retour au premier appel ; le service worker d'une PWA doit le précacher pour le hors-ligne. Le JSON reste du code livré : il ne change qu'au déploiement.
- Usage : ✅ gros JSON utile sur un écran rare · ❌ JSON du premier écran (attente réseau), ou contenu à publier sans livraison (`fetch`).

```js
// Exemple 1 : mesuré avec Vite 8
const m = await import('./d.json')
console.log(m.default.version)
// dist/assets/d-D6HYk712.js
// dist/assets/index-mvrrrMNF.js
```

- Quiz : On modifie `d.json` sur le serveur, sans rebuild. Le chunk reflète-t-il le changement ?
- [ ] Oui : il est relu à chaque appel
- [x] Non : c'est du JS généré au build
- [ ] Oui, après expiration du cache
- Réponse : non : le JSON a été transformé en module JS au build (nom haché) ; personne ne lit plus le `d.json` du serveur.

## 14. type: 'json' : ne jamais exécuter des données
- Id : modules-es-attribut-securite
- Sous-thème : json
- Type : concept
- Niveau : 3
- Profils : web, expert
- Prérequis : modules-es-import-json-with
- Source : revision-pwa · pwa-parcours
- Définition : `type: 'json'` empêche un serveur de faire exécuter du code à la place de données : une réponse non JSON est refusée.
- Contexte : Le navigateur interprète un module d'après le type MIME de la réponse, pas d'après l'extension. Sans attribut, un serveur compromis ou mal configuré qui répond `text/javascript` pour `config.json` ferait exécuter du code. Avec `type: 'json'`, une réponse non JSON fait échouer l'import (spec HTML). C'est la raison d'être de l'attribut.
- Usage : ✅ `with { type: 'json' }` sur tout JSON importé, a fortiori depuis un autre domaine · ❌ compter sur l'extension `.json` : le navigateur ne la regarde pas.

```js
// Exemple 1 : le serveur répond du JS
import cfg from 'https://cdn.example/c.json'
  with { type: 'json' }
// réponse Content-Type: text/javascript
// → l'import échoue, rien n'est exécuté
```

- Quiz : Sans attribut, un navigateur importe `c.json` servi en `application/json`. Que se passe-t-il ?
- [ ] Il le charge comme JSON
- [ ] Il devine le type à l'extension
- [x] Échec : sans `type`, seul du JavaScript est accepté
- [ ] Il l'exécute comme du JavaScript
- Réponse : échec : un module sans attribut doit avoir un type MIME JavaScript (spec HTML) ; un JSON exige `type: 'json'`.
