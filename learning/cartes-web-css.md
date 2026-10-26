---
title: "Cartes · CSS"
type: cartes
langage: Web
chapitre: Navigateur
cours: CSS
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · CSS
Web · CSS : grid (format spec v3 de revision-pwa).

## 1. minmax(0, 1fr) : la piste qui ne grandit pas
- Id : css-grid-minmax-zero
- Sous-thème : grid
- Type : piège
- Niveau : 2
- Profils : web
- Source : revision-pwa · pwa-revision
- Définition : `minmax(0, 1fr)` donne à une piste de grille l'espace restant, sans jamais grandir avec un contenu plus grand qu'elle.
- Contexte : `1fr` vaut `minmax(auto, 1fr)` : son minimum est la taille du contenu. La rangée qui porte une pile de cartes de 2 000 px grandit donc à 2 000 px, le pied sort de l'écran et rien ne défile. Avec `0` pour minimum, la rangée garde l'espace restant et l'enfant (`overflow-y: auto`) défile. Même piège en colonnes : un `pre` large élargit tout l'écran.
- Usage : ✅ en-tête / contenu / pied sur `100dvh`, colonne contenant du code qui défile horizontalement · ❌ `1fr` seul dès que le contenu peut dépasser la place disponible.

```css
/* Exemple 1 : mesuré, écran de 600 px */
.screen {
  display: grid;
  height: 600px;
  grid-template-rows: auto 1fr auto;
}
/* main (sans overflow) contient
   un fil de 2 000 px qui défile :
   1fr            → main 2 000 px,
                    pied hors écran
   minmax(0, 1fr) → main 500 px,
                    le fil défile */
```

```css
/* Exemple 2 : les colonnes aussi */
.screen {
  grid-template-columns: minmax(0, 1fr);
}
/* pre de 200 caractères, 390 px :
   1fr            → colonne 1 560 px
   minmax(0, 1fr) → colonne 390 px */
```

- Quiz : Avec `1fr`, si `main` porte lui-même `overflow-y: auto`, la rangée grandit-elle encore ?
- [ ] Oui, à 2 000 px comme sans overflow
- [ ] Oui, sauf avec `height: 100%` sur `main`
- [x] Non : un conteneur qui défile a un minimum `auto` de 0
- [ ] Non, mais le pied sort quand même de l'écran
- Réponse : non (mesuré : 500 px) : pour un élément dont `overflow` n'est pas `visible`, le minimum automatique vaut 0 ; le piège frappe quand le défilement est porté par un enfant.
