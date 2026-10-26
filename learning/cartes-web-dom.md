---
title: "Cartes · DOM"
type: cartes
langage: Web
chapitre: Navigateur
cours: DOM
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · DOM
Web · DOM : événements (écouteurs, propagation, nettoyage) et événements personnalisés (CustomEvent, dispatchEvent).

## 1. CustomEvent : transporter une donnée
- Id : dom-customevent-detail
- Sous-thème : customevent
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Voir aussi : dom-bus-window
- Source : revision-pwa · pwa-parcours
- Définition : `new CustomEvent(type, { detail })` crée un événement qui porte une donnée ; l'écouteur la lit dans `e.detail`.
- Contexte : `Event` ne transporte que son type ; `CustomEvent` ajoute `detail`, n'importe quelle valeur (id, objet). Il part avec `dispatchEvent` sur une cible (`window`, un élément, un `EventTarget` créé à la main) et s'écoute avec `addEventListener`, comme un clic. Il existe aussi dans Node (mesuré en 22), ce qui permet de le tester sans navigateur.
- Usage : ✅ prévenir d'autres parties de l'app sans les importer (ouvrir une carte, progression modifiée) · ❌ remonter une valeur d'un enfant à son parent React : une prop `onX`.

```ts
// Exemple 1 : comme openCard (data.ts)
const OPEN_CARD = 'revision:open-card'
addEventListener(OPEN_CARD, (e) => {
  const id = (e as CustomEvent<string>).detail
  console.log(id)
})
dispatchEvent(new CustomEvent(OPEN_CARD,
  { detail: 'Python/listes-lire' }))
// affiché : Python/listes-lire
```

- Quiz : Que vaut `new CustomEvent('x').detail` ?
- [ ] `undefined`
- [x] `null`
- [ ] `{}`
- [ ] `''`
- Réponse : `null` (mesuré dans Node 22) : sans `detail`, la valeur par défaut est `null`, pas `undefined` ; un test `=== undefined` ne la voit pas.

## 2. dispatchEvent : synchrone
- Id : dom-dispatchevent-synchrone
- Sous-thème : événements
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Prérequis : dom-customevent-detail
- Source : revision-pwa · pwa-parcours
- Définition : `dispatchEvent` appelle tous les écouteurs immédiatement, avant de rendre la main : ce n'est ni une file d'attente ni une promesse.
- Contexte : Venant d'un bus de messages, on imagine un envoi différé : non, la ligne qui suit `dispatchEvent` s'exécute après tous les écouteurs. Un écouteur lent bloque donc l'appelant, et un écouteur qui modifie un état l'a déjà fait à la ligne suivante. Pour différer, l'écouteur passe par `queueMicrotask` ou `setTimeout`.
- Usage : ✅ compter sur l'effet de l'écouteur juste après l'envoi (état mis à jour) · ❌ y lancer un travail long : le différer, ou le confier à un worker.

```js
// Exemple 1 : mesuré dans Node 22
const t = new EventTarget()
const log = []
t.addEventListener('ouvrir',
  (e) => log.push(e.detail))
log.push('avant')
t.dispatchEvent(new CustomEvent('ouvrir',
  { detail: 'listes-lire' }))
log.push('après')
// log : ['avant', 'listes-lire', 'après']
```

- Quiz : L'écouteur fait `queueMicrotask(() => log.push(e.detail))`. Que vaut `log` juste après `log.push('après')` ?
- [ ] `['avant', 'listes-lire', 'après']`
- [x] `['avant', 'après']`
- [ ] `['listes-lire', 'avant', 'après']`
- Réponse : `['avant', 'après']` (mesuré) : l'écouteur tourne tout de suite mais ne fait que planifier ; la micro-tâche passe quand la pile se vide, après le code synchrone.

## 3. once : un seul appel
- Id : dom-once
- Sous-thème : événements
- Type : recette
- Niveau : 1
- Profils : débutant, web
- Source : revision-pwa · pwa-parcours
- Définition : `addEventListener(type, f, { once: true })` retire l'écouteur dès son premier appel.
- Contexte : Évite le couple ajout / retrait à la main pour un événement attendu une fois (premier chargement, `transitionend`, réponse d'un worker). L'écouteur est retiré **avant** d'être appelé. Combiné à une promesse, il donne un « attendre tel événement » en trois lignes.
- Usage : ✅ attendre un événement une fois, transformer un événement en promesse · ❌ un écouteur permanent : il disparaît après le premier appel.

```js
// Exemple 1 : appelé une fois
const t = new EventTarget()
let n = 0
t.addEventListener('pret', () => n++,
  { once: true })
t.dispatchEvent(new Event('pret'))
t.dispatchEvent(new Event('pret'))
// n vaut 1
```

```js
// Exemple 2 : attendre un événement
const attendre = (cible, type) =>
  new Promise((ok) => cible.addEventListener(
    type, ok, { once: true }))
const e = await attendre(window, 'revision:pret')
```

- Quiz : Avec `once: true`, l'écouteur redéclenche le même événement sur la même cible. Combien d'appels au total ?
- [x] 1
- [ ] 2
- [ ] Une boucle sans fin
- [ ] 0
- Réponse : 1 (mesuré) : l'écouteur est retiré avant son appel ; le second envoi ne trouve plus personne.

## 4. window : un bus entre modules
- Id : dom-bus-window
- Sous-thème : customevent
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : dom-customevent-detail
- Voir aussi : dom-evenement-sans-rejeu, dom-typer-windoweventmap
- Source : revision-pwa · pwa-parcours
- Définition : `dispatchEvent` et `addEventListener` appelés sans objet visent `window` : un bus global qui relie deux modules sans import mutuel.
- Contexte : `data.ts` expose `openCard(id)`, qui envoie `revision:open-card` ; `App.tsx`, qui connaît la navigation, l'écoute. Un lien « Voir aussi » au fond de l'arbre ouvre ainsi une autre carte sans callback passé par props. Préfixer le nom (`revision:`) évite toute collision avec un événement natif ou d'une bibliothèque. Le prix : le lien n'apparaît plus dans les imports.
- Usage : ✅ quelques signaux transverses (ouvrir une carte, progression changée) · ❌ tout l'état de l'app en événements : un store ou un contexte React reste lisible.

```ts
// Exemple 1 : envoyer (data.ts)
export const OPEN_CARD = 'revision:open-card'
export const openCard = (id: string) =>
  dispatchEvent(new CustomEvent(OPEN_CARD,
    { detail: id }))
```

```tsx
// Exemple 2 : écouter (App.tsx)
useEffect(() => {
  const onOpen = (e: Event) =>
    ouvrir((e as CustomEvent<string>).detail)
  addEventListener(OPEN_CARD, onOpen)
  return () =>
    removeEventListener(OPEN_CARD, onOpen)
}, [ouvrir])
```

- Quiz : Pourquoi `dispatchEvent(…)` sans objet marche-t-il dans un module ES ?
- [ ] Dans un module, `this` vaut `window`
- [x] C'est une méthode de `window`, l'objet global
- [ ] Vite l'importe automatiquement
- [ ] React l'injecte dans chaque composant
- Réponse : c'est une méthode de `window` : les propriétés de l'objet global s'appellent sans préfixe ; dans un module, `this` vaut `undefined`, pas `window`.

## 5. CustomEvent : ne remonte pas par défaut
- Id : dom-customevent-bubbles
- Sous-thème : customevent
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : dom-customevent-detail
- Source : revision-pwa · pwa-parcours
- Définition : Un `CustomEvent` ne remonte pas l'arbre DOM par défaut (`bubbles: false`) : envoyé sur un élément, un écouteur sur `window` ne le reçoit pas.
- Contexte : Les clics remontent parce que le navigateur les crée avec `bubbles: true` ; un événement construit à la main part à `false`, comme `cancelable`. Pour qu'un composant prévienne un ancêtre ou `window` en envoyant depuis son élément, il faut `{ bubbles: true }`, ou envoyer directement sur `window`. À travers un shadow DOM, il faut en plus `composed: true`.
- Usage : ✅ `bubbles: true` pour un événement de composant écouté par un ancêtre · ❌ attendre d'un événement fait main le comportement d'un clic.

```js
// Exemple 1 : valeurs par défaut (Node 22)
const e = new CustomEvent('x')
e.bubbles      // false
e.cancelable   // false
```

```js
// Exemple 2 : ne remonte pas (spec DOM)
addEventListener('carte:vue',
  () => console.log('reçu'))
document.body.dispatchEvent(
  new CustomEvent('carte:vue'))
// rien d'affiché
document.body.dispatchEvent(
  new CustomEvent('carte:vue',
    { bubbles: true }))
// affiché : reçu
```

- Quiz : `bubbles: true`, envoyé sur `document.body` ; l'écouteur est sur un élément **enfant** de `body`. Le reçoit-il ?
- [ ] Oui : la propagation va dans les deux sens
- [x] Non : l'événement ne descend pas sous la cible
- [ ] Oui, pendant la phase de capture
- Réponse : non : la capture descend de `window` jusqu'à la cible, la remontée en repart vers `window` ; un enfant de la cible n'est sur aucun des deux trajets.

## 6. removeEventListener : la même fonction
- Id : dom-retirer-meme-reference
- Sous-thème : événements
- Type : piège
- Niveau : 2
- Profils : web
- Voir aussi : dom-signal-abortcontroller
- Source : revision-pwa · pwa-parcours
- Définition : `removeEventListener` ne retire que la fonction exacte passée à `addEventListener` : une flèche réécrite à l'identique est une autre fonction.
- Contexte : Deux flèches au même code sont deux objets ; `removeEventListener` ne trouve rien et ne dit rien. Dans un `useEffect`, garder la fonction dans une constante utilisée par l'ajout et par le nettoyage. Sinon, chaque exécution de l'effet ajoute un écouteur et le signal est traité plusieurs fois.
- Usage : ✅ une constante (`onOpen`) passée aux deux appels, ou `{ signal }` · ❌ `removeEventListener(type, () => …)` écrit en ligne.

```js
// Exemple 1 : mesuré dans Node 22
const t = new EventTarget()
const log = []
t.addEventListener('z', () => log.push('a'))
t.removeEventListener('z',
  () => log.push('a'))   // autre fonction
t.dispatchEvent(new Event('z'))
// log : ['a']   (toujours là)
```

- Quiz : `add('z', f, { capture: true })` puis `remove('z', f)`. L'écouteur est-il retiré ?
- [ ] Oui : même fonction, même type
- [x] Non : `capture` diffère
- [ ] Oui, au prochain envoi seulement
- Réponse : non (mesuré : toujours appelé) : un écouteur est identifié par type, fonction **et** `capture` ; il faut `remove('z', f, { capture: true })`.

## 7. TypeScript : déclarer ses événements
- Id : dom-typer-windoweventmap
- Sous-thème : customevent
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : dom-bus-window
- Source : revision-pwa · pwa-parcours
- Définition : Déclarer son événement dans `WindowEventMap` type `e.detail` dans les écouteurs de `window`, sans `as CustomEvent<…>`.
- Contexte : Pour un nom inconnu de TypeScript, l'écouteur reçoit un `Event` : `e.detail` est refusé (TS2339, mesuré avec TS 6), d'où le cast `(e as CustomEvent<string>)` d'`App.tsx`. Augmenter l'interface globale, une fois, fait vérifier le nom et le type de `detail` partout. Pour un élément, l'interface est `HTMLElementEventMap`.
- Usage : ✅ événements globaux de l'app, déclarés à côté de leur constante · ❌ un cast répété dans chaque écouteur : il ment dès que le type de `detail` change.

```ts
// Exemple 1 : déclaré une fois
declare global {
  interface WindowEventMap {
    'revision:open-card': CustomEvent<string>
  }
}
addEventListener('revision:open-card',
  (e) => ouvrir(e.detail))  // string
```

```ts
// Exemple 2 : sans déclaration
addEventListener('autre', (e) => e.detail)
// TS2339: Property 'detail' does not
// exist on type 'Event'.
```

- Quiz : Avec la déclaration, que dit TypeScript de `dispatchEvent(new CustomEvent('revision:open-card', { detail: 42 }))` ?
- [ ] Erreur : `detail` doit être une `string`
- [ ] Erreur : nom d'événement inconnu
- [x] Rien : l'envoi n'est pas relié à la map
- Réponse : rien (mesuré : `tsc` passe) : la map type les écouteurs, pas `dispatchEvent` ; d'où une fonction d'envoi typée (`openCard(id: string)`) comme seule porte d'entrée.

## 8. cancelable : laisser un écouteur dire non
- Id : dom-cancelable-preventdefault
- Sous-thème : customevent
- Type : concept
- Niveau : 2
- Profils : web
- Prérequis : dom-dispatchevent-synchrone
- Source : revision-pwa · pwa-parcours
- Définition : Un événement créé avec `cancelable: true` peut être annulé par un écouteur (`preventDefault()`) ; `dispatchEvent` renvoie alors `false`.
- Contexte : C'est un canal de retour : l'émetteur demande « quelqu'un s'y oppose-t-il ? » (quitter un écran avec un brouillon, fermer une modale). Comme l'envoi est synchrone, la réponse est connue dès le retour de `dispatchEvent`. Seule l'annulation remonte : pour renvoyer une vraie valeur, passer par `detail`.
- Usage : ✅ demander l'accord des écouteurs avant une action par défaut · ❌ s'en servir pour renvoyer une donnée : un objet dans `detail`.

```js
// Exemple 1 : un écouteur s'oppose
const t = new EventTarget()
t.addEventListener('quitter',
  (e) => e.preventDefault())
const ok = t.dispatchEvent(
  new CustomEvent('quitter',
    { cancelable: true }))
// ok vaut false : on reste sur l'écran
```

- Quiz : Même écouteur, mais l'événement est créé **sans** `cancelable`. Que vaut `ok` ?
- [x] `true`
- [ ] `false`
- [ ] `undefined`
- [ ] `TypeError`
- Réponse : `true` (mesuré) : sur un événement non annulable, `preventDefault()` est sans effet ; oublier `cancelable` désactive l'annulation en silence.

## 9. signal : retirer plusieurs écouteurs d'un coup
- Id : dom-signal-abortcontroller
- Sous-thème : événements
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : dom-retirer-meme-reference
- Source : revision-pwa · pwa-parcours
- Définition : `addEventListener(type, f, { signal })` retire l'écouteur quand le `AbortController` associé appelle `abort()`.
- Contexte : Un seul `abort()` retire tous les écouteurs posés avec ce signal, sans garder la référence de chaque fonction : pratique pour un écran qui en pose plusieurs. Dans un `useEffect`, le nettoyage devient `() => ac.abort()`, et les flèches en ligne redeviennent possibles. Mesuré dans Node 22 : après `abort()`, l'écouteur n'est plus appelé.
- Usage : ✅ plusieurs écouteurs à retirer ensemble, flèches en ligne · ❌ un seul écouteur dont on garde déjà la référence : `removeEventListener` suffit.

```tsx
// Exemple 1 : nettoyage en une ligne
useEffect(() => {
  const ac = new AbortController()
  const o = { signal: ac.signal }
  addEventListener(OPEN_CARD,
    (e) => ouvrir(e.detail), o)
  addEventListener(PROGRESS_CHANGE,
    () => rafraichir(), o)
  return () => ac.abort()
}, [])
```

- Quiz : On passe à `addEventListener` un signal **déjà** annulé. Que se passe-t-il ?
- [ ] L'écouteur est ajouté normalement
- [ ] `AbortError` est levée
- [x] L'écouteur n'est pas ajouté
- [ ] Il est retiré après son premier appel
- Réponse : il n'est pas ajouté (mesuré : 0 appel, aucune erreur) : un effet relancé avec un contrôleur déjà annulé n'écoute donc rien, sans le signaler.

## 10. événement : pas de rejeu
- Id : dom-evenement-sans-rejeu
- Sous-thème : customevent
- Type : choisir
- Niveau : 2
- Profils : web
- Prérequis : dom-bus-window
- Source : revision-pwa · pwa-parcours
- Définition : Un événement n'est reçu que par les écouteurs présents au moment de l'envoi : il n'est ni stocké ni rejoué pour ceux qui arrivent après.
- Contexte : Si `openCard` part avant que l'effet d'`App` ait posé son écouteur (premier rendu, écran pas encore monté), l'événement est perdu sans erreur. C'est une notification, pas un état : pour une valeur à lire plus tard (catalogue chargé, utilisateur connecté), un store, un contexte ou une promesse mémorisée conviennent mieux.
- Usage : ✅ signal ponctuel, écouteur posé au démarrage · ❌ valeur qu'un composant monté plus tard doit connaître : un état partagé.

```js
// Exemple 1 : trop tard
const t = new EventTarget()
t.dispatchEvent(new CustomEvent('pret',
  { detail: 1555 }))
let recu = null
t.addEventListener('pret',
  (e) => { recu = e.detail })
// recu vaut null : l'envoi est passé
```

- Quiz : Comment rendre « catalogue chargé » utilisable par un écran monté plus tard ?
- [ ] Renvoyer l'événement toutes les secondes
- [x] Garder une promesse du catalogue, que chacun attend
- [ ] Poser l'écouteur avec `{ once: true }`
- [ ] Envoyer l'événement avec `bubbles: true`
- Réponse : une promesse mémorisée : une fois résolue, elle donne la valeur à chaque `await`, même tardif ; un événement passé est perdu.

## 11. touchmove : l'écouteur passif
- Id : dom-ecouteur-passif
- Sous-thème : événements
- Type : piège
- Niveau : 3
- Profils : web, expert
- Source : revision-pwa · pwa-revision
- Définition : Un écouteur `passive: true` promet de ne pas appeler `preventDefault()` : le navigateur défile sans l'attendre et ignore l'appel.
- Contexte : React attache `onTouchStart`, `onTouchMove` et `onWheel` en passif à la racine (lu dans `react-dom`) : un `e.preventDefault()` dans `onTouchMove` n'empêche pas le défilement, Chrome affiche seulement « Unable to preventDefault inside passive event listener ». Pour piloter le geste, comme le pager qui fait suivre le doigt à la pile de cartes, poser l'écouteur dans un effet avec `{ passive: false }`.
- Usage : ✅ `{ passive: false }` sur le seul élément dont on pilote le geste · ❌ sur `window` ou `document` : chaque défilement attend le JS, la page saccade.

```ts
// Exemple 1 : comme pager.ts
useEffect(() => {
  const el = ref.current!
  const onMove = (e: TouchEvent) => {
    e.preventDefault() // efficace ici
    suivreLeDoigt(e)
  }
  el.addEventListener('touchmove',
    onMove, { passive: false })
  return () => el.removeEventListener(
    'touchmove', onMove)
}, [])
```

```js
// Exemple 2 : mesuré dans Chromium
const h = (e) => {
  e.preventDefault()
  console.log(e.defaultPrevented)
}
el.addEventListener('wheel', h,
  { passive: true })
// affiché : false (+ avertissement)
el.addEventListener('wheel', h,
  { passive: false })
// affiché : true
```

- Quiz : `document.addEventListener('wheel', h)` sans option : le `preventDefault()` de `h` bloque-t-il le défilement ?
- [ ] Oui : `passive` vaut `false` par défaut
- [ ] Oui, mais seulement sur iOS
- [ ] Non : `wheel` n'est jamais annulable
- [x] Non : sur `document`, `wheel` est passif par défaut
- Réponse : non (mesuré : `defaultPrevented` = `false`) : sur `window`, `document` et `body`, `wheel`, `touchstart` et `touchmove` sont passifs par défaut ; il faut `{ passive: false }` explicite.

## 12. écouteur : son exception ne remonte pas
- Id : dom-exception-ecouteur
- Sous-thème : événements
- Type : piège
- Niveau : 3
- Profils : web, expert
- Prérequis : dom-dispatchevent-synchrone
- Source : revision-pwa · pwa-parcours
- Définition : Une exception levée dans un écouteur ne remonte pas à `dispatchEvent` : les autres écouteurs sont appelés, l'erreur est seulement signalée.
- Contexte : Le navigateur la rapporte comme une erreur non capturée (console, `window.onerror`) et `dispatchEvent` revient normalement. Mesuré dans Node 22 : le second écouteur tourne, `dispatchEvent` renvoie `true`, l'erreur sort ensuite en `uncaughtException`. Un `try` autour de `dispatchEvent` ne sert à rien : la gestion d'erreur va dans l'écouteur.
- Usage : ✅ `try / catch` dans l'écouteur qui peut échouer · ❌ un `try` autour de `dispatchEvent` pour savoir si le traitement a réussi.

```js
// Exemple 1 : mesuré dans Node 22
const t = new EventTarget()
t.addEventListener('z', () => {
  throw new Error('boom')
})
t.addEventListener('z',
  () => console.log('second appelé'))
try {
  console.log(t.dispatchEvent(new Event('z')))
} catch { console.log('jamais') }
// affiché : second appelé, true
// puis l'erreur non capturée : boom
```

- Quiz : Comment l'émetteur peut-il savoir qu'un écouteur a échoué ?
- [ ] Un `try` autour de `dispatchEvent`
- [ ] `dispatchEvent` renvoie `false`
- [x] L'écouteur l'écrit dans un objet passé en `detail`
- [ ] `e.defaultPrevented` passe à `true`
- Réponse : par `detail` : l'émetteur et les écouteurs partagent le même objet (mesuré : une mutation de `detail.n` se voit après l'envoi) ; ni l'exception ni le retour ne le disent.

## 13. addEventListener : pas de doublon
- Id : dom-ecouteur-doublon
- Sous-thème : événements
- Type : piège
- Niveau : 3
- Profils : web, expert
- Prérequis : dom-retirer-meme-reference
- Source : revision-pwa · pwa-parcours
- Définition : Ajouter deux fois la même fonction avec les mêmes options n'enregistre qu'un écouteur : elle n'est appelée qu'une fois par envoi.
- Contexte : Le DOM dédoublonne sur type, fonction et `capture`. Cela masque un effet React relancé sans nettoyage… tant que la fonction est la même ; une flèche recréée à chaque rendu s'ajoute, elle, à chaque fois. Le Strict Mode de React, qui exécute deux fois les effets en développement, révèle les nettoyages manquants.
- Usage : ✅ un nettoyage explicite dans chaque effet · ❌ compter sur le dédoublonnage : il ne vaut que pour le même objet fonction.

```js
// Exemple 1 : mesuré dans Node 22
const t = new EventTarget()
let n = 0
const h = () => n++
t.addEventListener('z', h)
t.addEventListener('z', h)
t.dispatchEvent(new Event('z'))
// n vaut 1
```

- Quiz : Même chose avec `t.addEventListener('z', () => n++)` écrit deux fois. Que vaut `n` après un envoi ?
- [ ] 1
- [x] 2
- [ ] 0
- Réponse : 2 (mesuré) : deux flèches sont deux fonctions distinctes, donc deux écouteurs ; seul le même objet fonction est dédoublonné.
