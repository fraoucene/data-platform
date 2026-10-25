---
title: "Cartes · DOM"
type: cartes
langage: Web
cours: DOM
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · DOM
Web · DOM : événements (format spec v3 de revision-pwa).

## 1. touchmove : l'écouteur passif
- Sous-thème : événements
- Niveau : 3
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
