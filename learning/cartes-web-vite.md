---
title: "Cartes · Vite"
type: cartes
langage: Web
cours: Vite
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Vite
Web · Vite : build (format spec v3 de revision-pwa).

## 1. NODE_ENV : le build de dev caché
- Sous-thème : build
- Niveau : 2
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
