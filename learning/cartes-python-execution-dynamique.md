---
title: "Cartes · Exécution dynamique Python"
type: cartes
langage: Python
cours: Exécution dynamique
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Exécution dynamique Python
Python · Exécution dynamique : ast, eval (format spec v3 de revision-pwa).

## 1. eval : une expression, pas une instruction
- Sous-thème : eval
- Niveau : 1
- Définition : `eval(texte)` calcule une expression et renvoie sa valeur ; `exec(texte)` exécute des instructions et renvoie toujours `None`.
- Contexte : Python sépare expression (`len(s)`, `a if c else b`) et instruction (`x = 1`, `import`, `def`). `exec` écrit dans le dict qu'on lui passe : c'est là qu'on relit les noms créés. `check_cards.py` combine les deux : `exec` pour chaque instruction d'un bloc, `eval` pour l'expression annotée `# →`, dans un espace de noms neuf par carte.
- Usage : ✅ outillage sur du code de confiance (dépôt, tests de documentation) · ❌ texte venu d'un utilisateur ou d'une API : exécution de code arbitraire ; `ast.literal_eval` ou `json.loads`.

```python
# Exemple 1 : expression → valeur
eval("len('483609327')")  # → 9
eval("x * 2", {"x": 21})  # → 42

# exec : des instructions, pas de valeur
ns = {}
exec("siren = '483609327'", ns)  # → None
ns["siren"]  # → '483609327'
```

- Quiz : Que fait `eval("x = 1")` ?
- [ ] Renvoie `1`
- [ ] Renvoie `None` et crée `x`
- [x] `SyntaxError`
- [ ] `NameError`
- Réponse : `SyntaxError` : une affectation est une instruction, `eval` n'accepte qu'une expression (en JS, `eval("x = 1")` renvoie `1`).

## 2. ast.literal_eval : des littéraux seulement
- Sous-thème : ast
- Niveau : 2
- Définition : `ast.literal_eval(texte)` relit un littéral Python (nombre, chaîne, liste, dict, tuple, set, booléen, `None`) sans exécuter de code.
- Contexte : Ni appel de fonction, ni nom, ni opération : tout le reste lève `ValueError`. Il relit une valeur écrite à la Python (`['483609327']`, `{'a': 1}`, `(1,)`) que `json.loads` refuserait (guillemets simples, tuple, `None`). `check_cards.py` l'essaie d'abord sur la valeur d'un `# →` et ne retombe sur `eval` que pour un objet (`Page(...)`).
- Usage : ✅ relire une valeur Python écrite en texte (commentaire `# →`, config, cache) · ❌ JSON d'une API : `json.loads` ; expression à calculer : ce n'est pas son rôle.

```python
# Exemple 1 : littéraux acceptés
import ast

ast.literal_eval("['483609327', 2]")
# → ['483609327', 2]
ast.literal_eval("(1,)")  # → (1,)
ast.literal_eval("None")  # → None
```

```python
# Exemple 2 : un appel est refusé
import ast

ast.literal_eval("len('abc')")  # ❌ ValueError
```

- Quiz : Que donne `ast.literal_eval("1 + 2")` ?
- [ ] `3`
- [ ] `'1 + 2'`
- [x] `ValueError`
- [ ] `SyntaxError`
- Réponse : `ValueError` (mesuré, Python 3.12) : une opération n'est pas un littéral ; seule l'écriture d'un complexe (`1+2j`) est tolérée.
