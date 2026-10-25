---
title: "Cartes · PWA"
type: cartes
langage: Web
cours: PWA
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · PWA
Web · PWA : manifest, service worker, cache, stockage, iOS, débogage (format spec v3 de revision-pwa).

## 1. manifest : les champs qui comptent
- Sous-thème : manifest
- Niveau : 1
- Définition : Le manifest web (`manifest.webmanifest`) décrit l'app installée : nom, icônes, mode d'affichage, URL de départ, portée et couleurs.
- Contexte : vite-plugin-pwa le génère depuis l'option `manifest` et injecte `<link rel="manifest">` dans `index.html`. `short_name` s'affiche sous l'icône, `name` à l'installation. `display: standalone` retire la barre d'URL. Sans `scope`, la portée est le dossier de `start_url` (mesuré : `/app/index.html` → `/app/`) ; une navigation hors portée rouvre l'interface du navigateur. `background_color` peint l'écran de lancement, `theme_color` la barre système.
- Usage : ✅ un seul manifest, déclaré dans `VitePWA({ manifest })`, avec `start_url` et `scope` explicites · ❌ un `manifest.json` écrit à la main dans `public/` en plus : deux sources qui divergent.

```json
// Exemple 1 : manifest généré (extrait)
{
  "name": "Révision",
  "short_name": "Révision",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#222341",
  "theme_color": "#34355c",
  "icons": [
    { "src": "icon-192.png",
      "sizes": "192x192" },
    { "src": "icon-maskable-512.png",
      "sizes": "512x512",
      "purpose": "maskable" }
  ]
}
```

- Quiz : Sans champ `id`, on passe `start_url` de `/` à `/?src=pwa` : Chrome y voit-il la même app installée ?
- [ ] Oui : même origine, donc même app
- [ ] Oui : la query string est ignorée
- [x] Non : `id` vaut par défaut `start_url`
- [ ] Non, sauf si `scope` reste `/`
- Réponse : non (mesuré via CDP `Page.getAppManifest` : `id` = `start_url` complet, query comprise) : l'identité de l'app change ; fixer `id: '/'` avant de toucher à `start_url`.

## 2. installabilité : les critères de Chromium
- Sous-thème : manifest
- Niveau : 1
- Définition : Chromium propose d'installer une page en contexte sécurisé si son manifest a un nom, un `start_url`, une icône de 144 px et un `display` d'app.
- Contexte : Mesuré avec `Page.getInstallabilityErrors` : `display: browser` donne `manifest-display-not-supported`, une seule icône de 96 px `no-acceptable-icon:144`, pas de `start_url` `start-url-not-valid`. Le service worker n'est plus exigé : un manifest complet suffit. Chrome émet alors `beforeinstallprompt`. iOS n'a ni critère vérifiable ni invite : installation manuelle par Partager, « Sur l'écran d'accueil ».
- Usage : ✅ vérifier l'onglet Manifest des DevTools (erreurs listées) avant de tester sur téléphone · ❌ attendre `beforeinstallprompt` sur iPhone : il n'existe pas dans Safari.

```js
// Exemple 1 : mesuré (Chromium, CDP)
// manifest complet, sans SW → []
// display: 'browser'
// → ['manifest-display-not-supported']
// icônes : une seule de 96 px
// → ['no-acceptable-icon:144']
// start_url absent
// → ['start-url-not-valid']
// name et short_name absents
// → ['manifest-missing-name-or-short-name']
```

- Quiz : Le manifest ne déclare que l'icône 192 px (pas de 512) : Chrome propose-t-il l'installation ?
- [ ] Non : la 512 px est obligatoire
- [x] Oui : 144 px minimum suffit
- [ ] Non : il faut aussi une icône `maskable`
- [ ] Oui, mais seulement sur Android
- Réponse : oui (mesuré : aucune erreur d'installabilité) : le critère est une icône d'au moins 144 px ; la 512 sert à l'écran de lancement et aux stores, elle reste conseillée.

## 3. service worker : HTTPS ou localhost
- Sous-thème : service worker
- Niveau : 1
- Source : revision-pwa · pwa-revision
- Définition : Un service worker ne s'enregistre que dans un contexte sécurisé : page servie en HTTPS, ou depuis `localhost` en HTTP.
- Contexte : Hors contexte sécurisé, `navigator.serviceWorker` n'existe pas : le `registerSW.js` de vite-plugin-pwa (`if ('serviceWorker' in navigator)`) ne fait rien, sans erreur. L'app ouverte sur l'iPhone via `http://192.168.x.x:5175` s'affiche et s'installe, mais ne marche pas hors ligne : le test du mode avion attend l'URL CloudFront (HTTPS inclus sur `*.cloudfront.net`).
- Usage : ✅ tester le hors-ligne sur `vite preview` en local, puis sur l'URL HTTPS déployée · ❌ conclure sur le service worker depuis l'IP locale du téléphone.

```js
// Exemple 1 : mesuré dans Chromium
// http://localhost:5175
isSecureContext  // → true
typeof navigator.serviceWorker
// → 'object'

// http://192.168.1.20:5175
isSecureContext  // → false
typeof navigator.serviceWorker
// → 'undefined'
```

- Quiz : Sur `http://127.0.0.1:5175` (et non `localhost`), le service worker peut-il s'enregistrer ?
- [x] Oui : `127.0.0.1` est aussi un contexte sécurisé
- [ ] Non : seul le nom `localhost` est exempté
- [ ] Non : une IP exige toujours HTTPS
- [ ] Oui, mais seulement avec `devOptions.enabled`
- Réponse : oui (mesuré : `isSecureContext` = `true`) : les adresses de bouclage (`127.0.0.0/8`, `::1`) sont sûres comme `localhost` ; une IP du réseau local, non.

## 4. service worker : install, activate, fetch
- Sous-thème : service worker
- Niveau : 1
- Définition : Un service worker vit en trois temps : `install` (remplir le cache), `activate` (nettoyer les anciens caches), puis `fetch` (intercepter les requêtes de ses pages).
- Contexte : `event.waitUntil(promesse)` prolonge l'étape jusqu'à la fin de la promesse ; `respondWith` fournit la réponse d'un `fetch`. Le SW n'a ni DOM ni `window`, et le navigateur l'arrête dès qu'il est inactif : aucune variable globale ne survit entre deux événements. Workbox génère ces écouteurs (`precacheAndRoute`, `cleanupOutdatedCaches`) ; l'écrire une fois à la main aide à relire `dist/sw.js`.
- Usage : ✅ comprendre et déboguer le `sw.js` généré, cas très simple sans dépendance · ❌ écrire précache et révisions à la main en projet : Workbox les calcule au build.

```js
// Exemple 1 : sw.js à la main (testé)
const C = 'shell-v2'
self.addEventListener('install', e =>
  e.waitUntil(caches.open(C).then(c =>
    c.addAll(['/', '/index.css']))))
self.addEventListener('activate', e =>
  e.waitUntil(caches.keys().then(ks =>
    Promise.all(ks.filter(k => k !== C)
      .map(k => caches.delete(k))))))
self.addEventListener('fetch', e =>
  e.respondWith(caches.match(e.request)
    .then(r => r ?? fetch(e.request))))
// mesuré : caches.keys() → ['shell-v2']
// (shell-v1 supprimé), hors ligne :
// /index.css → 200 depuis le cache
```

- Quiz : Un fichier de la liste `addAll` répond 404 : que devient ce nouveau service worker ?
- [ ] Installé, sans ce fichier en cache
- [ ] Activé, avec une erreur en console
- [x] `redundant` : jamais activé
- [ ] Réinstallé à la requête suivante
- Réponse : `redundant` (mesuré) : `addAll` rejette sur toute réponse non 2xx, la promesse d'`install` échoue et le SW est jeté ; l'ancien continue de servir.

## 5. apple-touch-icon : l'icône d'iOS
- Sous-thème : iOS
- Niveau : 1
- Définition : `<link rel="apple-touch-icon">` fournit l'icône de l'écran d'accueil iOS : un PNG carré de 180 × 180 px, sans transparence.
- Contexte : Safari l'utilise en priorité sur les icônes du manifest (doc Apple / WebKit ; avant iOS 15.4, il ignorait celles du manifest). iOS arrondit lui-même les coins : pas de coins arrondis ni d'ombre dans l'image, un fond plein jusqu'aux bords. Les icônes `maskable` du manifest servent Android ; elles ne remplacent pas cette balise. Comme les autres balises `apple-*`, elle est lue à l'ajout sur l'écran d'accueil.
- Usage : ✅ un `apple-touch-icon.png` 180 px opaque dans `public/`, lié depuis `index.html` · ❌ compter sur `icon-192.png` du manifest pour l'iPhone, ou un PNG à fond transparent.

```html
<!-- Exemple 1 : index.html de l'app -->
<link rel="apple-touch-icon"
  href="/apple-touch-icon.png" />
<meta name="apple-mobile-web-app-title"
  content="Révision" />
```

```bash
# Exemple 2 : vérifier l'image (mesuré)
sips -g pixelWidth -g hasAlpha \
  public/apple-touch-icon.png
# pixelWidth: 180
# hasAlpha: no
```

- Quiz : L'`apple-touch-icon.png` a un fond transparent : comment iOS l'affiche-t-il sur l'écran d'accueil ?
- [ ] Sur fond blanc
- [ ] Sur la `background_color` du manifest
- [x] Sur fond noir
- [ ] Avec la transparence, sur le fond d'écran
- Réponse : sur fond noir (comportement documenté, non mesuré ici) : iOS ne garde pas l'alpha des icônes ; peindre le fond dans l'image.

## 6. DevTools : le panneau Application
- Sous-thème : débogage
- Niveau : 1
- Définition : Le panneau Application de Chrome DevTools montre le manifest, les service workers, Cache Storage, IndexedDB et l'espace occupé par le site.
- Contexte : Service workers : « Update on reload » installe et active le nouveau `sw.js` à chaque rechargement, « Bypass for network » ignore le SW, « Offline » coupe le réseau. Storage → « Clear site data » remet l'origine à zéro (SW, caches, `localStorage`). Manifest liste les erreurs d'installabilité. Pour l'iPhone : Safari sur Mac, menu Développement → l'appareil → l'app (Inspecteur web activé dans Réglages → Safari → Avancé).
- Usage : ✅ « Clear site data » entre deux essais de mise à jour, Cache Storage pour voir ce qui est en cache · ❌ juger le hors-ligne avec « Update on reload » coché : le vrai cycle est court-circuité.

```js
// Exemple 1 : console de l'app (CloudFront)
await caches.keys()
// → ['workbox-precache-v2-https://…']
const r = await navigator
  .serviceWorker.getRegistration()
r.active.scriptURL
// → 'https://d1non6rpr4vppb
//    .cloudfront.net/sw.js'
!!navigator.serviceWorker.controller
// → true : la page est contrôlée
```

- Quiz : Après un rechargement forcé (Cmd+Shift+R), la page est-elle contrôlée par le service worker ?
- [ ] Oui : le SW sert toujours ses pages
- [x] Non : le SW est contourné pour ce chargement
- [ ] Non : le rechargement forcé le désinscrit
- [ ] Oui, mais sans lire son cache
- Réponse : non (mesuré : `controller` = `null`, puis `true` au rechargement normal suivant) : un rechargement forcé contourne le SW sans le supprimer.

## 7. register : la portée du service worker
- Sous-thème : service worker
- Niveau : 2
- Définition : Un service worker ne contrôle que les pages sous sa portée, par défaut le dossier de son script : `/js/sw.js` donne `/js/`.
- Contexte : Demander une portée plus large que ce dossier lève `SecurityError`, sauf si le serveur envoie l'en-tête `Service-Worker-Allowed: /` avec le script (mesuré). D'où `sw.js` à la racine de `dist/` : `registerSW.js` enregistre `/sw.js` avec `scope: '/'`. Une inscription par portée : réenregistrer la même portée remplace le script, ne la duplique pas.
- Usage : ✅ `sw.js` servi à la racine, portée `/` · ❌ ranger `sw.js` dans `assets/` (nom haché, portée `/assets/`) : il ne contrôlerait aucune page.

```js
// Exemple 1 : mesuré dans Chromium
const r = await navigator.serviceWorker
  .register('/js/sw.js')
r.scope  // → 'http://localhost:5199/js/'

await navigator.serviceWorker
  .register('/js/sw.js', { scope: '/' })
// ❌ SecurityError
// OK si la réponse de /js/sw.js porte
// Service-Worker-Allowed: /
```

- Quiz : `/sw.js` (portée `/`) et `/admin/sw.js` (portée `/admin/`) sont actifs : qui contrôle `/admin/stats` ?
- [ ] `/sw.js` : il a été inscrit en premier
- [x] `/admin/sw.js` : la portée la plus longue
- [ ] Les deux, l'un après l'autre
- [ ] Aucun : les portées se chevauchent
- Réponse : `/admin/sw.js` (mesuré : `controller.scriptURL` et réponse du SW admin) : la portée qui correspond le plus précisément à l'URL gagne.

## 8. mise à jour : le nouveau SW attend
- Sous-thème : service worker
- Niveau : 2
- Définition : Un nouveau `sw.js` s'installe puis attend (`waiting`) tant qu'une page est servie par l'ancien ; `skipWaiting()` l'active sans attendre.
- Contexte : L'attente évite qu'une page chargée avec l'ancien build parle à un SW dont le précache est déjà le nouveau. Mesuré : v2 installé, un 2e onglet ouvert reste sur v1 ; fermer tous les onglets puis rouvrir sert v2. Sur iPhone, l'app installée compte comme une page tant qu'elle n'est pas fermée dans le sélecteur d'apps. `registerType: 'autoUpdate'` écrit `self.skipWaiting()` et `clientsClaim()` dans `sw.js`.
- Usage : ✅ `skipWaiting` quand un mélange ancien et nouveau build est sans risque, sinon proposer la mise à jour · ❌ supposer qu'un déploiement est visible dès la réouverture d'un onglet.

```js
// Exemple 1 : mesuré, v1 actif, v2 déployé
const r = await navigator.serviceWorker
  .getRegistration()
await r.update()
!!r.waiting   // → true : v2 attend
await (await fetch('/v')).text()
// → 'v1' : l'ancien répond encore
// tous les onglets fermés, réouverture :
// → 'v2'
```

- Quiz : v2 est en attente, un seul onglet ouvert : un simple rechargement (F5) active-t-il v2 ?
- [ ] Oui : la page est recréée
- [ ] Oui, si `sw.js` est servi en `no-cache`
- [ ] Non : il faut désinscrire v1
- [x] Non : l'onglet reste servi par v1
- Réponse : non (mesuré : toujours `'v1'`, `waiting` présent) : au rechargement, l'ancienne et la nouvelle page se chevauchent, l'onglet n'est jamais libéré ; `skipWaiting()` ou fermer l'onglet.

## 9. registerType : prompt ou autoUpdate
- Sous-thème : service worker
- Niveau : 2
- Définition : Dans vite-plugin-pwa, `registerType` décide qui active une nouvelle version : l'utilisateur (`'prompt'`, la valeur par défaut) ou le service worker seul (`'autoUpdate'`).
- Contexte : En `prompt`, `sw.js` n'appelle pas `skipWaiting` mais écoute le message `SKIP_WAITING` (vérifié dans le build). Le hook `useRegisterSW` de `virtual:pwa-register/react` passe `needRefresh` à `true` quand v2 attend ; `updateServiceWorker()` envoie ce message puis recharge. En `autoUpdate`, une page ouverte de l'ancien build peut demander un chunk chargé à la demande déjà retiré du précache.
- Usage : ✅ `prompt` avec bandeau si couper une session coûte (formulaire en cours) ; `autoUpdate` pour une app sans état critique (l'app de révision) · ❌ `prompt` sans interface pour le proposer.

```tsx
// Exemple 1 : registerType: 'prompt'
import { useRegisterSW } from
  'virtual:pwa-register/react'

function Maj() {
  const { needRefresh: [maj],
    updateServiceWorker } = useRegisterSW()
  if (!maj) return null
  return (
    <button onClick={() =>
      updateServiceWorker()}>
      Nouvelle version : recharger
    </button>
  )
}
```

- Quiz : `registerType: 'prompt'`, mais rien n'importe `virtual:pwa-register` : que devient une nouvelle version déployée ?
- [ ] Le build échoue sans le hook
- [x] Elle attend la fermeture de toutes les pages
- [ ] Elle s'active au rechargement suivant
- [ ] Le service worker n'est jamais enregistré
- Réponse : elle attend (vérifié : `registerSW.js` injecté, `sw.js` sans `skipWaiting`) : personne n'envoie `SKIP_WAITING`, v2 reste `waiting` jusqu'à ce que plus aucune page n'utilise v1.

## 10. précache : une empreinte par fichier
- Sous-thème : cache
- Niveau : 2
- Source : revision-pwa · pwa-revision
- Définition : Workbox écrit dans `sw.js` la liste des fichiers du build à mettre en cache à l'installation, chacun avec une empreinte de son contenu.
- Contexte : `precacheAndRoute` reçoit des `{ url, revision }`. Un fichier à nom fixe (`index.html`, icônes) porte un MD5 : s'il change, `sw.js` change, et le nouveau service worker ne retélécharge que les entrées modifiées. Un asset au nom haché a `revision: null` : son nom suffit. La liste est figée au build : une donnée publiée ensuite (le catalogue) n'y est jamais.
- Usage : ✅ tout le shell de l'app (`html`, `js`, `css`, icônes) via `globPatterns`, décrit une seule fois · ❌ données qui changent sans redéploiement : `runtimeCaching`.

```js
// Exemple 1 : extrait de dist/sw.js
precacheAndRoute([
  { url: 'index.html',
    revision: '84ce14f6' }, // MD5 tronqué
  { url: 'icon-192.png',
    revision: '1c9dc91e' },
  { url: 'assets/index-Coy71iMz.js',
    revision: null }, // nom haché
])
```

- Quiz : On modifie seulement `icon-192.png` et on redéploie : que retélécharge l'app installée ?
- [ ] Tout le précache, puisque `sw.js` a changé
- [x] Le nouveau `sw.js`, puis la seule `icon-192.png`
- [ ] Toutes les icônes du manifest
- [ ] Rien avant l'expiration du cache CloudFront
- Réponse : le nouveau `sw.js` puis la seule icône : Workbox compare les `revision` entrée par entrée ; `sw.js` en `no-cache` rend le changement visible à l'ouverture suivante.

## 11. NetworkFirst : frais en ligne, dernier vu hors ligne
- Sous-thème : cache
- Niveau : 2
- Source : revision-pwa · pwa-revision
- Définition : La stratégie Workbox `NetworkFirst` demande d'abord au réseau, garde la réponse en cache, et ne sert ce cache qu'en cas d'échec ou de délai dépassé.
- Contexte : Le catalogue change sans redéploiement : il ne peut pas être précaché. `StaleWhileRevalidate` répondrait d'abord avec le cache et mettrait à jour en arrière-plan : une carte publiée n'apparaîtrait qu'à l'ouverture suivante. `NetworkFirst` est frais en ligne ; `networkTimeoutSeconds: 4` évite d'attendre un réseau de métro muet. `CacheFirst`, lui, ne revalide jamais.
- Usage : ✅ JSON qui change souvent et doit rester lisible hors ligne · ❌ shell de l'app (précache) ou assets hachés (`CacheFirst`) : une requête réseau inutile à chaque ouverture.

```ts
// Exemple 1 : vite.config.ts
runtimeCaching: [{
  urlPattern: ({ url }) =>
    url.pathname ===
    '/content/catalog.json',
  handler: 'NetworkFirst',
  options: {
    cacheName: 'catalogue',
    networkTimeoutSeconds: 4,
  },
}]
```

- Quiz : Hors ligne, catalogue jamais mis en cache : que reçoit le `fetch` de l'app ?
- [ ] Un `200` avec un catalogue vide
- [x] Une erreur : la promesse est rejetée
- [ ] Le `index.html` précaché
- [ ] Un `504` généré par Workbox
- Réponse : une erreur (mesuré : `TypeError: Failed to fetch`, « Load failed » sur l'iPhone) : ni réseau ni entrée en cache, `NetworkFirst` n'a rien à servir.

## 12. stratégies : choisir
- Sous-thème : cache
- Niveau : 2
- Définition : Workbox propose cinq stratégies, `CacheFirst`, `NetworkFirst`, `StaleWhileRevalidate`, `NetworkOnly` et `CacheOnly`, qui arbitrent entre fraîcheur et disponibilité hors ligne.
- Contexte : `CacheFirst` lit le cache et ne va au réseau que s'il manque : pour un contenu immuable (polices, images versionnées), avec `expiration` pour borner le cache. `StaleWhileRevalidate` répond avec le cache puis le rafraîchit en arrière-plan. `NetworkOnly` ne met jamais en cache (POST, authentification). `CacheOnly` ne sert que ce qui a été précaché. Chaque route a son `cacheName` : on voit et vide chaque cache séparément.
- Usage : ✅ une route par type de ressource, du plus stable (`CacheFirst`) au plus vivant (`NetworkFirst`) · ❌ `CacheFirst` sans `expiration` sur des URL qui varient : le cache grossit sans fin.

```ts
// Exemple 1 : runtimeCaching
runtimeCaching: [{
  urlPattern: /^https:\/\/fonts\.gstatic/,
  handler: 'CacheFirst',
  options: {
    cacheName: 'polices',
    expiration: { maxEntries: 20,
      maxAgeSeconds: 31536000 },
  },
}, {
  urlPattern: /\/stats\.json$/,
  handler: 'StaleWhileRevalidate',
  options: { cacheName: 'stats' },
}]
```

- Quiz : Une route `CacheFirst` puis une route `NetworkFirst` correspondent toutes deux à `/content/catalog.json` : laquelle s'applique ?
- [x] `CacheFirst` : la première déclarée
- [ ] `NetworkFirst` : la dernière déclarée
- [ ] La plus précise des deux
- [ ] Les deux, l'une après l'autre
- Réponse : la première déclarée : le routeur de Workbox teste les routes dans l'ordre d'inscription et s'arrête à la première qui correspond (source de workbox-routing).

## 13. navigateFallback : index.html pour toute navigation
- Sous-thème : cache
- Niveau : 2
- Définition : `generateSW` ajoute une `NavigationRoute` : toute navigation dans la portée reçoit l'`index.html` du précache, en ligne comme hors ligne.
- Contexte : C'est ce qui ouvre les routes de la SPA hors ligne (`/session/42`). Mais le SW répond à toute navigation, même vers un fichier : mesuré sur CloudFront, ouvrir `/rapport.pdf` ou `/content/x.json` dans l'onglet renvoie `200` et l'app, sans toucher le réseau (sans SW : `403` de S3). `navigateFallbackDenylist` exclut des chemins de cette règle.
- Usage : ✅ SPA avec routeur côté client · ❌ fichiers ouverts par lien direct (PDF, exports, JSON publiés) sans les exclure par `navigateFallbackDenylist`.

```js
// Exemple 1 : mesuré sur CloudFront
// sans service worker :
//   GET /rapport.pdf → 403 (S3)
// SW actif, même URL dans l'onglet :
//   → 200, fromServiceWorker: true,
//     contenu : index.html (l'app)
// hors ligne, /session/42 → 200
```

```ts
// Exemple 2 : vite.config.ts
workbox: {
  navigateFallbackDenylist: [
    /^\/content\//, /\.pdf$/,
  ],
}
```

- Quiz : SW actif, l'app appelle `fetch('/rapport.pdf')` (pas une navigation) : que reçoit-elle ?
- [ ] `200` et le HTML de l'app
- [ ] Une promesse rejetée
- [x] `403` : la réponse du réseau
- [ ] `404` généré par Workbox
- Réponse : `403` (mesuré sur CloudFront) : `NavigationRoute` ne vise que les requêtes `mode: 'navigate'` ; un `fetch()` passe aux autres routes, puis au réseau.

## 14. navigator.onLine : réseau n'est pas Internet
- Sous-thème : cache
- Niveau : 2
- Définition : `navigator.onLine` et les événements `online` / `offline` indiquent si l'appareil a une interface réseau, pas si le serveur répond.
- Contexte : `false` est fiable : aucun réseau (mode avion, `setOffline` de Playwright, mesuré). `true` ne garantit rien : Wi-Fi sans Internet, réseau de métro muet. La vraie mesure reste l'échec du `fetch`, que l'app doit gérer de toute façon ; côté SW, `networkTimeoutSeconds` évite d'attendre. Le hook React se branche sur `useSyncExternalStore`, sans `useEffect` ni état dupliqué.
- Usage : ✅ bandeau « hors ligne » quand `onLine` vaut `false` · ❌ bloquer un `fetch` ou conclure « en ligne » sur `onLine === true`.

```ts
// Exemple 1 : hook React
const sub = (cb: () => void) => {
  addEventListener('online', cb)
  addEventListener('offline', cb)
  return () => {
    removeEventListener('online', cb)
    removeEventListener('offline', cb)
  }
}
export const useEnLigne = () =>
  useSyncExternalStore(sub,
    () => navigator.onLine)
```

```js
// Exemple 2 : mesuré (Playwright)
await ctx.setOffline(true)
navigator.onLine   // → false
await ctx.setOffline(false)
navigator.onLine   // → true
```

- Quiz : iPhone connecté au Wi-Fi d'un hôtel, portail captif pas encore validé : que vaut `navigator.onLine` ?
- [x] `true` : une interface est connectée
- [ ] `false` : aucun serveur ne répond
- [ ] `undefined` jusqu'au premier `fetch`
- [ ] `false` après 4 s sans réponse
- Réponse : `true` (doc MDN, non mesuré) : le navigateur ne teste pas Internet, il voit seulement un réseau actif.

## 15. stockage : ce que voit le service worker
- Sous-thème : stockage
- Niveau : 2
- Définition : Dans un service worker, Cache Storage (`caches`) et IndexedDB sont disponibles ; `localStorage` et `sessionStorage` n'existent pas.
- Contexte : `localStorage` est synchrone, réservé aux pages, limité à quelques Mo de chaînes. Cache Storage range des paires `Request` → `Response` (fichiers, JSON) et existe aussi côté page ; IndexedDB stocke des objets structurés, indexés, depuis la page comme depuis le SW. L'app range sa progression dans `localStorage` : lisible par l'app, pas par `sw.js`. Un SW qui en a besoin passe par IndexedDB (`idb-keyval`) ou un `postMessage` de la page.
- Usage : ✅ réponses HTTP : Cache Storage ; données partagées avec le SW ou volumineuses : IndexedDB · ❌ `localStorage` pour ce que le SW doit lire, ou pour des Mo de données.

```js
// Exemple 1 : mesuré dans un SW
typeof caches        // → 'object'
typeof indexedDB     // → 'object'
typeof localStorage  // → 'undefined'
// localStorage.getItem('x') dans sw.js
// → ReferenceError
```

- Quiz : Le cache contient `/content/catalog.json?v=2` : que renvoie `caches.match('/content/catalog.json')` ?
- [ ] La réponse : la query string est ignorée
- [x] `undefined` : l'URL doit correspondre en entier
- [ ] La réponse, si une seule entrée existe
- [ ] Une erreur `NotFoundError`
- Réponse : `undefined` (mesuré ; `true` avec `{ ignoreSearch: true }`) : la clé est l'URL complète, query comprise.

## 16. safe-area : env() et viewport-fit
- Sous-thème : iOS
- Niveau : 2
- Définition : `env(safe-area-inset-*)` donne la marge à laisser autour de l'encoche, de la Dynamic Island et de la barre d'accueil de l'iPhone.
- Contexte : Ces valeurs restent à 0 tant que la page n'occupe pas tout l'écran : il faut `viewport-fit=cover` dans la balise `viewport` (doc WebKit). L'app s'en sert pour son en-tête (`env(safe-area-inset-top) + 0.75rem`) et ses onglets du bas. `max()` garantit une marge minimale sur un écran sans encoche. Valeurs à mesurer sur l'appareil : elles changent avec le modèle, l'orientation et le `status-bar-style`.
- Usage : ✅ `viewport-fit=cover` + `env()` dans les paddings des barres fixes · ❌ marges en dur (`44px`) copiées d'un modèle d'iPhone.

```css
/* Exemple 1 : index.css de l'app */
header {
  padding-top: calc(
    env(safe-area-inset-top) + 0.75rem);
}
:root {
  --bottom-gap: max(0.5rem, calc(
    env(safe-area-inset-bottom) - 14px));
}
/* index.html : viewport-fit=cover,
   sans quoi tous les insets valent 0 */
```

- Quiz : `padding-bottom: env(safe-area-inset-bottom, 16px)` dans Chrome sur ordinateur : quelle marge ?
- [ ] `16px` : la valeur de repli
- [x] `0px` : la variable existe et vaut 0
- [ ] Aucune : la déclaration est ignorée
- [ ] `auto`
- Réponse : `0px` (mesuré ; `16px` avec une variable inconnue) : le repli ne sert que si la variable n'existe pas ; pour un minimum, `max(16px, env(…))`.

## 17. urlPattern : Workbox recopie le texte
- Sous-thème : cache
- Niveau : 3
- Source : revision-pwa · pwa-revision
- Définition : Une fonction `urlPattern` de `runtimeCaching` est recopiée en texte dans `sw.js`, telle qu'écrite, sans ses imports.
- Contexte : `generateSW` sérialise la configuration avec le code source de la fonction. Dans `sw.js`, `CATALOG_KEY` importé de `catalog.ts` n'existe pas : la fonction lève `ReferenceError` à chaque requête testée, la route ne correspond jamais, le catalogue n'est jamais mis en cache. Le build passe, l'app marche en ligne : le défaut n'apparaît qu'hors ligne. Relire le `sw.js` construit.
- Usage : ✅ chemin en dur dans la fonction, ou une `RegExp` (recopiée telle quelle) · ❌ constante importée dans `urlPattern`.

```ts
// Exemple 1 : vite.config.ts
import { CATALOG_KEY } from
  './lambda/catalog.ts'
urlPattern: ({ url }) =>
  url.pathname === `/${CATALOG_KEY}`,
// dans dist/sw.js (mesuré) :
// ({url:e})=>e.pathname===
//   `/${CATALOG_KEY}`
// → ReferenceError dans le SW
```

```ts
// Exemple 2 : le correctif, vérifié
urlPattern: ({ url }) =>
  url.pathname ===
  '/content/catalog.json',
// dans dist/sw.js :
// ({url:e})=>"/content/catalog.json"
//   ===e.pathname
```

- Quiz : `const KEY = '/content/catalog.json'` déclarée en haut de `vite.config.ts`, utilisée dans `urlPattern` : ça marche ?
- [ ] Oui : seuls les imports sont perdus
- [ ] Oui : Vite remplace les constantes au build
- [ ] Non : Workbox refuse le build
- [x] Non : `KEY` n'existe pas non plus dans `sw.js`
- Réponse : non (mesuré : `e.pathname===local` recopié tel quel) : seul le texte de la fonction part dans `sw.js`, aucune variable de `vite.config.ts` ne la suit.

## 18. première ouverture : rien n'est intercepté
- Sous-thème : service worker
- Niveau : 3
- Source : revision-pwa · pwa-revision
- Définition : À la première visite, les requêtes parties avant l'installation du service worker ne passent pas par lui : rien n'est mis en cache.
- Contexte : `registerSW.js` enregistre `sw.js` à l'événement `load` ; l'app a déjà lancé `fetch('/content/catalog.json')` au montage. Le service worker installe le précache, puis `clientsClaim()` lui fait contrôler la page, trop tard pour cette requête : le cache `catalogue` reste vide (mesuré). Hors ligne avant une 2e ouverture en ligne, l'app n'a pas de catalogue.
- Usage : ✅ tester le hors-ligne après deux ouvertures en ligne, ou précacher la donnée à l'installation · ❌ conclure « le hors-ligne est cassé » sur une première visite.

```js
// Exemple 1 : mesuré sur CloudFront
// 1re ouverture, après 4 s :
!!navigator.serviceWorker.controller
// → true (clientsClaim)
await caches.keys()
// → ['workbox-precache-v2-…']
//   pas de cache 'catalogue'
// 2e ouverture :
await caches.keys()
// → [precache, 'catalogue']
```

- Quiz : Sans `clientsClaim()`, quand une page ouverte avant l'installation est-elle contrôlée ?
- [ ] Dès l'installation du service worker
- [ ] Dès que `skipWaiting()` l'active
- [x] Au prochain chargement de la page
- [ ] Jamais, sans nouvel appel à `register`
- Réponse : au prochain chargement : une page reste servie par ce qui l'a chargée ; `clients.claim()` prend la main sur les pages ouvertes, `skipWaiting()` ne fait qu'activer le SW sans attendre.

## 19. mise à jour : quand le navigateur relit sw.js
- Sous-thème : service worker
- Niveau : 3
- Définition : Le navigateur retélécharge `sw.js` à chaque navigation dans la portée et à chaque `update()`, puis l'installe si un seul octet a changé.
- Contexte : Pour ce contrôle, il contourne par défaut son propre cache HTTP (`updateViaCache: 'imports'`) : mesuré, un `sw.js` servi en `max-age=3600` puis modifié est vu par `update()`. Un CDN qui garde l'ancienne copie masque en revanche le changement : d'où `no-cache` sur `sw.js` dans CloudFront. Avec Workbox, tout fichier précaché modifié change le manifest de `sw.js`. Une app iPhone laissée ouverte ne navigue pas : rien n'est vérifié.
- Usage : ✅ `r.update()` au retour au premier plan, pour une app installée rarement fermée · ❌ un `setInterval` serré sur `update()` : une requête de plus toutes les minutes, sur batterie.

```ts
// Exemple 1 : vérifier au retour
document.addEventListener(
  'visibilitychange', async () => {
    if (document.visibilityState
      !== 'visible') return
    const r = await navigator
      .serviceWorker.getRegistration()
    await r?.update()
  })
```

```js
// Exemple 2 : mesuré dans Chromium
// sw.js v1 servi en max-age=3600,
// remplacé par v2 sur le serveur
await r.update()
!!r.waiting  // → true : v2 vu
```

- Quiz : Même scénario, mais `register('/sw.js', { updateViaCache: 'all' })` : quand `update()` voit-il v2 ?
- [ ] Tout de suite, comme par défaut
- [ ] À la navigation suivante
- [x] Pas avant l'expiration du cache HTTP
- [ ] Jamais, sans désinscription
- Réponse : après l'expiration (mesuré : ni `waiting` ni `installing`) : avec `'all'`, le cache HTTP sert l'ancien `sw.js`, son `max-age` étant plafonné à 24 h pour ce contrôle.

## 20. réponse opaque : status 0
- Sous-thème : cache
- Niveau : 3
- Définition : Un `fetch` en `mode: 'no-cors'` vers une autre origine renvoie une réponse opaque : `status` 0, corps et en-têtes illisibles.
- Contexte : Une `<img>` ou un `<script>` d'un CDN sans CORS produit ce type de réponse. `NetworkFirst` et `StaleWhileRevalidate` les mettent en cache (plugin `cacheOkAndOpaque`) ; `CacheFirst` ne garde que les `200` (source de workbox-strategies 7.4). Chrome compte en outre chaque réponse opaque pour plusieurs Mo de quota (doc Chrome) : quelques centaines d'images tierces suffisent à gonfler l'usage.
- Usage : ✅ ressources tierces servies avec CORS (`crossorigin`), ou `cacheableResponse: { statuses: [0, 200] }` en connaissance de cause · ❌ mettre en cache des réponses opaques sans `expiration`.

```js
// Exemple 1 : mesuré depuis localhost
const cdn =
  'https://d1non6rpr4vppb.cloudfront.net'
const r = await fetch(
  `${cdn}/favicon.svg`,
  { mode: 'no-cors' })
r.type    // → 'opaque'
r.status  // → 0
r.ok      // → false
```

```ts
// Exemple 2 : CacheFirst qui accepte 0
handler: 'CacheFirst',
options: {
  cacheName: 'cdn',
  cacheableResponse: {
    statuses: [0, 200] },
}
```

- Quiz : Image tierce en `no-cors` qui répond `403`, route `StaleWhileRevalidate` : qu'est-ce qui est mis en cache ?
- [ ] Rien : seul un `200` est mis en cache
- [ ] La dernière version valide de l'image
- [ ] Rien : les réponses opaques sont refusées
- [x] Le `403`, vu comme un `status` 0
- Réponse : le `403` (mesuré : `opaque`, `status` 0, `cache.put` accepté) : l'erreur est invisible, elle est servie ensuite comme une image valide, et cassée.

## 21. quotas : estimate, persist, éviction
- Sous-thème : stockage
- Niveau : 3
- Définition : `navigator.storage.estimate()` donne l'espace utilisé et le quota de l'origine ; `navigator.storage.persist()` demande que ses données ne soient pas évincées.
- Contexte : Le stockage est « best effort » : sous pression disque, le navigateur efface une origine entière (caches, IndexedDB, `localStorage`). Safari efface en plus le stockage écrit par script d'un site sans visite depuis 7 jours ; une app ajoutée à l'écran d'accueil en est exemptée et garde son stockage, séparé de celui de Safari (blog WebKit, non mesuré). Le quota dépend du disque : environ 10 Go mesurés dans Chromium.
- Usage : ✅ `estimate()` pour surveiller l'usage des caches, `persist()` pour une progression à ne pas perdre · ❌ `localStorage` comme unique copie de données importantes : prévoir une sauvegarde serveur.

```js
// Exemple 1 : mesuré sur CloudFront
const e = await navigator.storage
  .estimate()
e.usage                // → 1861829
e.usageDetails.caches  // → 1844246
await navigator.storage
  .persisted()         // → false
```

- Quiz : Progression rangée dans `localStorage`, app utilisée dans un onglet Safari (non installée), 8 jours sans visite : que devient-elle ?
- [ ] Conservée : `localStorage` est permanent
- [x] Effacée par Safari (7 jours sans visite)
- [ ] Copiée dans l'app de l'écran d'accueil
- [ ] Effacée seulement si le disque est plein
- Réponse : effacée (règle ITP de WebKit, doc) : sans visite pendant 7 jours de navigation, Safari supprime le stockage écrit par script ; l'app installée y échappe.

## 22. push : notifications et limites iOS
- Sous-thème : service worker
- Niveau : 3
- Définition : Le push web combine Push API (le serveur réveille le service worker) et Notifications API (le service worker affiche le message).
- Contexte : La page s'abonne avec `pushManager.subscribe` et la clé VAPID publique ; le backend (une Lambda) signe avec la clé privée et poste vers l'`endpoint` reçu (FCM, Apple…). `userVisibleOnly: true` est obligatoire : chaque `push` affiche une notification, pas de push silencieux. Sur iOS 16.4 et plus, la permission ne se demande qu'après un geste de l'utilisateur (doc WebKit).
- Usage : ✅ rappel de révision quotidien envoyé par une Lambda planifiée · ❌ demander la permission au chargement : refusée ou ignorée, et impossible à redemander depuis l'app.

```js
// Exemple 1 : sw.js, recevoir
self.addEventListener('push', e => {
  const d = e.data?.json() ?? {}
  e.waitUntil(self.registration
    .showNotification(d.titre, {
      body: d.texte,
      icon: '/icon-192.png',
    }))
})
```

```ts
// Exemple 2 : page, s'abonner au clic
bouton.onclick = async () => {
  const ok = await Notification
    .requestPermission()
  if (ok !== 'granted') return
  const r = await navigator
    .serviceWorker.ready
  const sub = await r.pushManager
    .subscribe({ userVisibleOnly: true,
      applicationServerKey: VAPID_PUB })
  await fetch('/api/abonnements', {
    method: 'POST',
    body: JSON.stringify(sub) })
}
```

- Quiz : Sur iPhone, la même app ouverte dans un onglet Safari (non installée) peut-elle s'abonner au push ?
- [ ] Oui, depuis iOS 16.4
- [ ] Oui, après un geste de l'utilisateur
- [ ] Non : iOS n'a pas de push web
- [x] Non : réservé aux apps de l'écran d'accueil
- Réponse : non (doc WebKit, non mesuré) : iOS n'ouvre Push API et notifications qu'aux web apps ajoutées à l'écran d'accueil.

## 23. status-bar-style : lu à l'installation
- Sous-thème : iOS
- Niveau : 3
- Source : revision-pwa · pwa-revision
- Définition : `apple-mobile-web-app-status-bar-style` règle la barre d'état d'une PWA installée sur iPhone : `default`, `black` ou `black-translucent`.
- Contexte : `black-translucent` fait passer la page sous la barre d'état ; mesuré sur un iPhone à Dynamic Island, iOS coupe alors le bas de la fenêtre (873 sur 932 pt) et aucune hauteur CSS (`100dvh`, `inset: 0`, `screen.height`) ne peint cette bande. `black` fait commencer la page sous la barre et la laisse aller jusqu'en bas. Mesurer sur l'appareil (`innerHeight`, `env(safe-area-inset-*)`) avant de corriger.
- Usage : ✅ `black`, avec un fond de page de la couleur de l'en-tête · ❌ `black-translucent` pour gagner le haut quand le bas de l'écran porte des onglets.

```html
<!-- Exemple 1 : index.html de l'app -->
<meta name="apple-mobile-web-app-capable"
  content="yes" />
<meta
  name="apple-mobile-web-app-status-bar-style"
  content="black" />
<link rel="apple-touch-icon"
  href="/apple-touch-icon.png" />
```

- Quiz : On passe de `black-translucent` à `black` et on redéploie : que montre l'app déjà installée ?
- [ ] La barre noire, dès la réouverture
- [ ] La barre noire, après l'invalidation CloudFront
- [ ] La barre noire, après la mise à jour du service worker
- [x] L'ancien réglage, jusqu'à la réinstallation
- Réponse : l'ancien réglage : iOS lit ces balises au moment de l'ajout sur l'écran d'accueil ; supprimer l'icône et réinstaller (même chose pour le manifest).
