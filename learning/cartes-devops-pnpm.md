---
title: "Cartes · pnpm"
type: cartes
langage: DevOps
cours: pnpm
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · pnpm
DevOps · pnpm : scripts (format spec v3 de revision-pwa).

## 1. prebuild : le hook avant le script
- Sous-thème : scripts
- Niveau : 2
- Définition : Un script `pre<nom>` du `package.json` (`prebuild`, `predev`) s'exécute avant `<nom>` ; s'il échoue, le script principal ne tourne pas.
- Contexte : `pnpm build` enchaîne `prebuild`, `build`, puis `postbuild`, comme npm (mesuré, pnpm 10.33). L'étape 2 y branchait `pnpm cards` : une carte mal formée arrêtait le build avant `tsc` et `vite`. Le hook suit le nom du script, pas la commande : lancer `vite build` directement le saute.
- Usage : ✅ générer ou contrôler un fichier avant `build` / `dev` · ❌ chaîne de hooks cachés : l'écrire en clair (`"build": "pnpm cards && vite build"`).

```bash
# Exemple 1 : prebuild qui échoue
# "prebuild": "echo PRE && exit 1"
# "build":    "echo BUILD"
pnpm build
# affiché : PRE
# → ELIFECYCLE Command failed
#   with exit code 1
# (BUILD n'est jamais lancé)
```

- Quiz : Cette fois `build` échoue : `postbuild` s'exécute-t-il ?
- [ ] Oui, comme un `finally`
- [ ] Oui, avec le code de sortie en variable
- [x] Non : la chaîne s'arrête au premier échec
- Réponse : non (mesuré) : pnpm enchaîne pre → script → post et s'arrête au premier code ≠ 0 ; pour un nettoyage garanti, un `trap` dans le script.
