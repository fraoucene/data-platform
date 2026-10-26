---
title: "Cartes · DAG"
type: cartes
langage: Data engineering
chapitre: Orchestrer
cours: DAG
created: 2026-10-26
updated: 2026-10-26
---

# Cartes · DAG
Data engineering · DAG : graphes de dépendances, tri topologique, détection de cycles, graphlib.

## 1. DAG : des dépendances sans boucle
- Id : dag-graphe-de-dependances
- Sous-thème : dépendances
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : dag-tri-topologique
- Mots-clés : Makefile
- Source : revision-pwa · pwa-parcours
- Définition : Un DAG (graphe orienté acyclique) relie des éléments par des flèches « A avant B », sans boucle : il décrit un ordre partiel.
- Contexte : Les tâches d'un pipeline (extraire avant charger), les prérequis des cartes, les cibles d'un Makefile ou les ressources Terraform forment des DAG. « Partiel » : deux éléments sans lien n'ont pas d'ordre imposé, ils peuvent passer dans n'importe quel ordre ou en parallèle. En Python, on le représente souvent par un dict nœud → ensemble de ses prérequis.
- Usage : ✅ décrire des dépendances avant de les ordonner ou de les paralléliser · ❌ une liste ordonnée à la main : elle devient fausse dès qu'une dépendance change.

```python
# Exemple 1 : nœud → ses prérequis
prerequis = {
    "listes-lire": set(),
    "listes-tranche": {"listes-lire"},
    "listes-trier": {"listes-lire"},
}
racines = [n for n, p in prerequis.items()
           if not p]
racines   # → ['listes-lire']
```

- Quiz : Dans l'exemple, quel ordre le graphe impose-t-il entre `listes-tranche` et `listes-trier` ?
- [ ] tranche d'abord : ordre du dict
- [x] Aucun : l'un ou l'autre d'abord
- [ ] trier d'abord : ordre alphabétique
- Réponse : aucun : ils ne dépendent que de `listes-lire` ; un DAG est un ordre partiel, l'ordre entre eux reste à choisir (stabilité, parallélisme).

## 2. tri topologique : chacun après ses prérequis
- Id : dag-tri-topologique
- Sous-thème : tri topologique
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : dag-graphe-de-dependances
- Voir aussi : dag-tri-stable
- Mots-clés : DAG, graphlib, Airflow
- Source : revision-pwa · pwa-parcours
- Définition : Un tri topologique range les nœuds d'un DAG dans une liste où chacun vient après tous ses prérequis.
- Contexte : Il existe dès que le graphe n'a pas de cycle, souvent en plusieurs versions (l'ordre partiel laisse des choix). Python le fournit depuis 3.9 : `graphlib.TopologicalSorter(graphe).static_order()`, avec un dict nœud → prérequis. Make, Terraform ou Airflow en font un avant de lancer quoi que ce soit ; `orderByPrerequis` ordonne ainsi les cartes d'une étape de parcours.
- Usage : ✅ ordonner tâches, migrations, cartes selon leurs dépendances · ❌ `sorted` avec une clé : une dépendance n'est pas une comparaison deux à deux.

```python
# Exemple 1 : l'exercice du cours
from graphlib import TopologicalSorter
g = {"tranche": {"index"},
     "hors-bornes": {"tranche"},
     "index": set()}
ts = TopologicalSorter(g)
list(ts.static_order())
# → ['index', 'tranche', 'hors-bornes']
```

- Quiz : Combien d'ordres topologiques valides pour `{"b": {"a"}, "c": {"a"}}` ?
- [ ] 1
- [x] 2
- [ ] 3
- [ ] 6
- Réponse : 2 : `a` d'abord, puis `b` et `c` dans un ordre ou l'autre ; un tri topologique n'est pas unique, d'où l'intérêt d'un tri stable.

## 3. cycle : aucun ordre possible
- Id : dag-cycle-ordre-impossible
- Sous-thème : cycles
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : dag-tri-topologique
- Voir aussi : dag-dfs-trois-etats
- Mots-clés : DAG, graphlib
- Source : revision-pwa · pwa-parcours
- Définition : Un cycle (A avant B, B avant A) rend tout ordre impossible : `graphlib` lève `CycleError`, un outil de build refuse de démarrer.
- Contexte : Aucun nœud du cycle n'a tous ses prérequis placés : l'algorithme se bloque. Un cycle naît souvent d'un lien posé dans le mauvais sens (« Prérequis » au lieu de « Voir aussi »). On le refuse à l'écriture (`make cards` échoue) plutôt que de le découvrir à l'exécution. L'erreur porte le chemin du cycle dans `e.args[1]`.
- Usage : ✅ valider le graphe dès qu'un lien est ajouté, avant de publier · ❌ ignorer le cycle et prendre « un ordre quelconque » sans le signaler.

```python
# Exemple 1 : deux cartes qui s'attendent
from graphlib import (CycleError,
                      TopologicalSorter)
g = {"a": {"b"}, "b": {"a"}}
ts = TopologicalSorter(g)
list(ts.static_order())  # ❌ CycleError
```

- Quiz : Un `except ValueError:` attrape-t-il le `CycleError` de `graphlib` ?
- [x] Oui : `CycleError` hérite de `ValueError`
- [ ] Non : il hérite directement d'`Exception`
- [ ] Non : il hérite de `RuntimeError`
- Réponse : oui (mesuré : `issubclass(CycleError, ValueError)` → `True`) : un `except ValueError` large l'avale aussi, et le cycle passe inaperçu.

## 4. auto-référence : le cycle d'un seul nœud
- Id : dag-auto-reference
- Sous-thème : cycles
- Type : piège
- Niveau : 1
- Profils : data
- Prérequis : dag-cycle-ordre-impossible
- Mots-clés : graphlib, cycle
- Source : revision-pwa · pwa-parcours
- Définition : Une carte prérequise d'elle-même forme un cycle de longueur 1 : `graphlib` la refuse comme n'importe quel cycle.
- Contexte : Typique d'un copier-coller de lien ou d'un Id renommé d'un côté seulement. `catalog.ts` le signale à part (« la carte se cite elle-même ») pour un message clair ; `orderByPrerequis` l'ignore (`p === c.id`) pour ne pas bloquer l'app. Un message précis coûte une ligne et épargne une enquête.
- Usage : ✅ un contrôle dédié, avec son message, avant la recherche de cycles · ❌ l'erreur générique « cycle » sur un seul nœud.

```python
# Exemple 1 : refusé par graphlib
from graphlib import (CycleError,
                      TopologicalSorter)
g = {"a": {"a"}}
try:
    list(TopologicalSorter(g).static_order())
except CycleError as e:
    chemin = e.args[1]
chemin   # → ['a', 'a']
```

- Quiz : Que vaut `[c for c, p in g.items() if c in p]` pour `g = {"a": {"a"}, "b": {"a"}}` ?
- [ ] `['a', 'b']`
- [ ] `[]`
- [x] `['a']`
- [ ] `['b']`
- Réponse : `['a']` : seul `a` se cite lui-même ; `b` dépend de `a` sans boucle. Ce contrôle d'une ligne précède la recherche de cycles.

## 5. graphlib : la valeur est un prérequis
- Id : dag-sens-des-aretes
- Sous-thème : graphlib
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : dag-tri-topologique
- Mots-clés : graphlib, Airflow, DAG
- Source : revision-pwa · pwa-parcours
- Définition : `TopologicalSorter` attend nœud → ses **prérequis** ; lui donner nœud → ses **suivants** inverse l'ordre, sans erreur.
- Contexte : Deux conventions coexistent : prédécesseurs (`graphlib`, champ `Prérequis`, `depends_on` Terraform) et successeurs (listes d'adjacence classiques, `a >> b` d'Airflow). Le graphe reste acyclique dans les deux sens, donc rien ne lève : seul l'ordre obtenu est à l'envers. Vérifier sur deux nœuds avant de brancher le vrai graphe.
- Usage : ✅ nommer le dict selon son sens (`prerequis`, `suivants`) · ❌ un dict `graphe` qui ne dit pas dans quel sens vont les flèches.

```python
# Exemple 1 : même dict, lu comme prérequis
from graphlib import TopologicalSorter
def ordre(g):
    ts = TopologicalSorter(g)
    return list(ts.static_order())

ordre({"tranche": {"lire"}})
# → ['lire', 'tranche']
ordre({"lire": {"tranche"}})
# → ['tranche', 'lire']   (sens inversé)
```

- Quiz : `graphlib` reçoit `{"extraire": {"charger"}}`, écrit pour « extraire puis charger ». Quelle tâche sort en premier ?
- [ ] `extraire`
- [x] `charger`
- [ ] Les deux à égalité
- [ ] Aucune : `CycleError`
- Réponse : `charger` : la valeur est un prérequis de la clé ; « extraire puis charger » s'écrit `{"charger": {"extraire"}}`.

## 6. Kahn : placer ce qui est prêt
- Id : dag-algorithme-de-kahn
- Sous-thème : tri topologique
- Type : concept
- Niveau : 2
- Profils : data, expert
- Prérequis : dag-tri-topologique
- Voir aussi : dag-prerequis-hors-liste
- Mots-clés : DAG, tri topologique, cycle
- Source : revision-pwa · pwa-parcours
- Définition : L'algorithme de Kahn place à chaque tour un nœud dont tous les prérequis sont déjà placés, jusqu'à épuisement.
- Contexte : Les nœuds sans prérequis restant sont prêts ; placer un nœud le retire des prérequis des autres, ce qui en libère de nouveaux. S'il reste des nœuds mais aucun prêt, c'est un cycle. La version efficace compte les prérequis restants (degré entrant) au lieu de tout reparcourir. `orderByPrerequis` en est une version simple : `findIndex` cherche la première carte prête.
- Usage : ✅ écrire son tri quand l'ordre entre nœuds prêts compte (stabilité, priorité) · ❌ le réécrire quand `graphlib` suffit.

```python
# Exemple 1 : Kahn en quelques lignes
def kahn(prerequis):
    reste = {n: set(p) for n, p
             in prerequis.items()}
    ordre = []
    while reste:
        prets = [n for n, p in reste.items()
                 if not p]
        if not prets:
            raise ValueError("cycle")
        n = prets[0]
        ordre.append(n)
        del reste[n]
        for p in reste.values():
            p.discard(n)
    return ordre

kahn({"b": {"a"}, "a": set()})
# → ['a', 'b']
```

- Quiz : Que fait `kahn({"b": {"a"}})`, sans clé `"a"` ?
- [ ] Renvoie `['a', 'b']`
- [ ] Renvoie `['b']`
- [x] Lève `ValueError("cycle")`
- [ ] Lève `KeyError: 'a'`
- Réponse : `ValueError` : `a` n'est pas un nœud, `b` attend un prérequis jamais placé et rien n'est prêt ; il faut ignorer les prérequis absents (comme `orderByPrerequis`) ou les ajouter comme nœuds.

## 7. tri stable : bouger le moins possible
- Id : dag-tri-stable
- Sous-thème : tri topologique
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : dag-algorithme-de-kahn
- Voir aussi : dag-graphlib-ordre-non-stable
- Mots-clés : tri topologique
- Source : revision-pwa · pwa-parcours
- Définition : Un tri topologique stable garde l'ordre d'origine et ne recule un élément que si l'un de ses prérequis vient après lui.
- Contexte : Pour un parcours, l'ordre initial a un sens (chapitre, thème, niveau) : on prend à chaque tour la **première** carte de la liste dont les prérequis présents sont placés. Si aucune n'est prête (cycle toléré), on prend la première restante. Coût quadratique, sans importance pour quelques centaines de cartes. C'est `orderByPrerequis` de `parcours.ts`.
- Usage : ✅ réordonner le minimum dans une liste déjà triée (parcours, migrations numérotées) · ❌ `graphlib` quand l'ordre entre éléments prêts compte.

```python
# Exemple 1 : port de orderByPrerequis
def stable(cartes, prerequis):
    presentes = set(cartes)
    faites, out = set(), []
    reste = list(cartes)
    while reste:
        i = next((k for k, c in enumerate(reste)
                  if all(p not in presentes
                         or p in faites
                         for p in prerequis.get(c, ()))),
                 0)   # aucune prête : la 1re
        c = reste.pop(i)
        faites.add(c)
        out.append(c)
    return out

stable(["trier", "tranche", "lire"],
       {"tranche": {"lire"}})
# → ['trier', 'lire', 'tranche']
```

- Quiz : Même appel avec `{"tranche": {"lire"}, "lire": {"tranche"}}` (cycle). Que renvoie `stable` ?
- [ ] `CycleError`
- [ ] `['trier', 'lire', 'tranche']`
- [x] `['trier', 'tranche', 'lire']`
- [ ] Rien : boucle sans fin
- Réponse : `['trier', 'tranche', 'lire']` : après `trier`, aucune carte n'est prête, le défaut `0` prend la première restante ; l'app tolère le cycle au lieu de planter.

## 8. graphlib : pas d'ordre stable
- Id : dag-graphlib-ordre-non-stable
- Sous-thème : graphlib
- Type : piège
- Niveau : 2
- Profils : data, expert
- Prérequis : dag-tri-topologique
- Mots-clés : graphlib, tri topologique
- Source : revision-pwa · pwa-parcours
- Définition : `static_order()` ne garde pas l'ordre d'insertion entre nœuds prêts : deux nœuds indépendants peuvent sortir dans un ordre inattendu.
- Contexte : La doc ne garantit qu'une chose : chaque nœud après ses prérequis. Mesuré en 3.12 : `add("d", "b", "c")` puis `add("b", "a")` donne `c` avant `a`. Pour un ordonnanceur, c'est sans importance ; pour un ordre montré à un humain (parcours, rapport), il surprend et peut changer d'une version à l'autre.
- Usage : ✅ `graphlib` pour exécuter des tâches dans un ordre valide · ❌ pour un ordre affiché : un tri stable maison.

```python
# Exemple 1 : c sort avant a
from graphlib import TopologicalSorter
ts = TopologicalSorter()
ts.add("d", "b", "c")
ts.add("b", "a")
list(ts.static_order())
# → ['c', 'a', 'b', 'd']
```

- Quiz : `static_order()` accepte-t-il un paramètre pour garder l'ordre d'insertion ?
- [ ] Oui : `stable=True`
- [ ] Oui : `key=`, comme `sorted`
- [x] Non : il ne prend aucun argument
- [ ] Oui : `sort=True`
- Réponse : non : `static_order()` ne prend aucun argument (mesuré : `TypeError` sur `stable=True`) ; pour un ordre maîtrisé, écrire un tri stable.

## 9. DFS : en cours ou fait
- Id : dag-dfs-trois-etats
- Sous-thème : cycles
- Type : concept
- Niveau : 2
- Profils : data, expert
- Prérequis : dag-cycle-ordre-impossible
- Voir aussi : dag-recursion-profondeur
- Mots-clés : cycle
- Source : revision-pwa · pwa-parcours
- Définition : Un parcours en profondeur marque chaque nœud « en cours » puis « fait » : retomber sur un nœud en cours signale un cycle.
- Contexte : « En cours » = sur le chemin actuel ; « fait » = exploré sans cycle. Retrouver un nœud « fait » n'est pas un cycle : deux chemins mènent à lui (un losange). Avec un seul ensemble `vus`, le losange passerait pour un cycle. C'est `checkLinks` de `catalog.ts`, qui garde aussi le chemin pour le message (`a → b → a`).
- Usage : ✅ détecter un cycle et afficher son chemin · ❌ un seul ensemble `vus` : faux cycles sur les losanges.

```python
# Exemple 1 : trois états, chemin gardé
def cycle(g):
    etat = {}
    def visite(n, chemin):
        etat[n] = "en-cours"
        for p in g.get(n, ()):
            if etat.get(p) == "en-cours":
                return chemin + [n, p]
            if p not in etat:
                c = visite(p, chemin + [n])
                if c:
                    return c
        etat[n] = "fait"
    for n in g:
        if n not in etat and (c := visite(n, [])):
            return " → ".join(c)

cycle({"a": {"b"}, "b": {"c"}, "c": {"a"}})
# → 'a → b → c → a'
```

- Quiz : Que renvoie `cycle({"a": {"a"}})` ?
- [ ] `None`
- [x] `'a → a'`
- [ ] `'a'`
- [ ] `RecursionError`
- Réponse : `'a → a'` : `a` est « en cours » quand il se trouve dans ses propres prérequis ; l'auto-référence est le plus court des cycles.

## 10. orchestrateur : exécuter un DAG de tâches
- Id : dag-orchestrateur
- Sous-thème : dépendances
- Type : concept
- Niveau : 2
- Profils : data, ops
- Prérequis : dag-graphe-de-dependances
- Voir aussi : AWS/step-functions-quand-orchestrer, AWS/step-functions-mwaa-airflow
- Mots-clés : DAG, tri topologique, Step Functions
- Source : revision-pwa · pwa-parcours
- Définition : Un orchestrateur (Airflow, Step Functions, Dagster) exécute un DAG de tâches : il lance chacune quand ses prérequis ont réussi.
- Contexte : Il ajoute au tri topologique ce qu'un script n'a pas : reprises sur erreur, rejeu d'une tâche et de ses suivantes, planification, historique des runs. Airflow déclare le DAG en Python (`a >> b`), Step Functions en JSON (états et transitions). Pour trois étapes linéaires, un script ou un Makefile qui suit l'ordre topologique suffit.
- Usage : ✅ beaucoup de tâches, reprises et rejeux partiels, plusieurs équipes · ❌ trois étapes linéaires : un script ou une Lambda.

```python
# Exemple 1 : rejouer une tâche et l'aval
suivants = {"extraire": ["valider"],
            "valider": ["charger", "alerter"],
            "charger": [], "alerter": []}
def aval(n):
    out = [n]
    for s in suivants[n]:
        out += aval(s)
    return out

aval("valider")
# → ['valider', 'charger', 'alerter']
```

- Quiz : Dans Airflow, une tâche échoue : que deviennent ses suivantes, par défaut ?
- [ ] Elles tournent quand même
- [x] Elles ne sont pas lancées (`upstream_failed`)
- [ ] Le DAG entier repart du début
- Réponse : elles ne sont pas lancées : la règle par défaut `all_success` exige que tous les prérequis aient réussi (selon la doc Airflow) ; d'autres règles (`all_done`) servent aux tâches de nettoyage ou d'alerte.

## 11. graphe : refuser à l'écriture, tolérer à la lecture
- Id : dag-refuser-ecrire-tolerer-lire
- Sous-thème : cycles
- Type : choisir
- Niveau : 2
- Profils : data, web
- Prérequis : dag-cycle-ordre-impossible
- Voir aussi : qualite-contrat-de-donnees
- Mots-clés : cycle, Lambda
- Source : revision-pwa · pwa-parcours
- Définition : Un lien cassé ou un cycle se refuse à l'écriture (validation avant publication) et se tolère à la lecture, pour ne jamais bloquer l'utilisateur.
- Contexte : `make cards` traite un cycle ou un lien vers une carte absente comme une erreur : le producteur corrige avant de publier. La Lambda, elle, publie quand même avec un avertissement, et l'app ignore le lien ou garde un ordre de repli : un fichier déposé à la main ne doit pas vider un parcours. Même contrôle, deux sévérités.
- Usage : ✅ erreur chez le producteur, avertissement et repli chez le consommateur · ❌ planter l'app sur une donnée imparfaite qu'elle peut contourner.

```python
# Exemple 1 : un contrôle, deux sévérités
def liens(cartes, ids):
    return [f"{c} : {p} inconnue"
            for c, ps in cartes.items()
            for p in ps if p not in ids]

cartes = {"tranche": ["lire", "lire-v2"]}
pb = liens(cartes, {"tranche", "lire"})
pb   # → ['tranche : lire-v2 inconnue']
refuse_avant_publication = bool(pb)
refuse_avant_publication   # → True
```

- Quiz : Où un cycle de prérequis doit-il faire **échouer** une commande ?
- [ ] Dans la Lambda `catalog-build`
- [x] Dans `make cards-validate`, chez le producteur
- [ ] Dans l'app, au chargement du catalogue
- [ ] Nulle part : un cycle est sans gravité
- Réponse : `make cards-validate` : le producteur peut corriger ; plus loin (Lambda, app), refuser priverait l'utilisateur de cartes justes pour un lien faux.

## 12. graphlib : exécuter par vagues
- Id : dag-get-ready-paralleles
- Sous-thème : graphlib
- Type : recette
- Niveau : 3
- Profils : data, expert
- Prérequis : dag-tri-topologique
- Voir aussi : dag-orchestrateur
- Mots-clés : graphlib, DAG, Makefile
- Source : revision-pwa · pwa-parcours
- Définition : `prepare()`, `get_ready()` et `done()` de `TopologicalSorter` livrent les nœuds par vagues : tout ce qui est prêt peut tourner en parallèle.
- Contexte : `get_ready()` renvoie les nœuds dont les prérequis sont terminés ; on les confie à des workers, et chaque `done(n)` peut en débloquer d'autres. `is_active()` dit s'il reste du travail. C'est le cœur d'un ordonnanceur (`make -j`, Terraform qui crée dix ressources à la fois). `prepare()` lève `CycleError` tout de suite.
- Usage : ✅ exécuter un DAG de tâches avec un pool de workers · ❌ `static_order()` puis exécution une à une : le parallélisme est perdu.

```python
# Exemple 1 : par vagues
from graphlib import TopologicalSorter
g = {"b": {"a"}, "c": {"a"},
     "d": {"b", "c"}}
ts = TopologicalSorter(g)
ts.prepare()
ts.get_ready()           # → ('a',)
ts.done("a")
sorted(ts.get_ready())   # → ['b', 'c']
```

- Quiz : Suite de l'exemple : après `ts.done("b")` seulement, que renvoie `ts.get_ready()` ?
- [ ] `('d',)`
- [x] `()`
- [ ] `('c',)`
- [ ] `ValueError`
- Réponse : `()` : `d` attend encore `c`, et `c`, déjà livré par le `get_ready()` précédent, n'est pas redonné.

## 13. sous-ensemble : ignorer les prérequis absents
- Id : dag-prerequis-hors-liste
- Sous-thème : tri topologique
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : dag-algorithme-de-kahn
- Mots-clés : graphlib, algorithme de Kahn, cycle
- Source : revision-pwa · pwa-parcours
- Définition : Trier un sous-ensemble (une étape de parcours) exige d'ignorer les prérequis absents de ce sous-ensemble, sinon le tri les ajoute ou se bloque.
- Contexte : Une carte de l'étape 3 peut citer une carte de l'étape 1, déjà vue. `graphlib` ajoute ce prérequis comme nœud dans le résultat ; un Kahn naïf ne le place jamais et croit à un cycle. `orderByPrerequis` ne compte que les prérequis présents (`!inList.has(p) || done.has(p)`). Filtrer le graphe d'abord rend l'intention explicite.
- Usage : ✅ restreindre les prérequis au sous-ensemble avant de trier · ❌ trier un sous-ensemble avec le graphe complet.

```python
# Exemple 1 : graphlib ajoute l'absent
from graphlib import TopologicalSorter
def ordre(g):
    ts = TopologicalSorter(g)
    return list(ts.static_order())

etape = {"tranche": {"lire"}}  # lire : étape 1
ordre(etape)    # → ['lire', 'tranche']
filtre = {c: p & etape.keys()
          for c, p in etape.items()}
ordre(filtre)   # → ['tranche']
```

- Quiz : Avec ce filtre, que donne l'étape `{"b": {"a"}, "a": set()}` ?
- [ ] `['b']`
- [ ] `['b', 'a']`
- [x] `['a', 'b']`
- [ ] `CycleError`
- Réponse : `['a', 'b']` : `a` fait partie de l'étape, le filtre garde ce prérequis ; seuls ceux d'autres étapes disparaissent.

## 14. DFS récursif : la pile de Python
- Id : dag-recursion-profondeur
- Sous-thème : cycles
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : dag-dfs-trois-etats
- Mots-clés : DFS, algorithme de Kahn, graphlib, lignage
- Source : revision-pwa · pwa-parcours
- Définition : Un parcours récursif sur une longue chaîne de dépendances dépasse la pile de Python : `RecursionError` vers 1 000 niveaux.
- Contexte : Python n'optimise pas la récursion terminale et limite la profondeur (`sys.getrecursionlimit()` → 1000). Une chaîne de 5 000 prérequis, rare pour des cartes, est courante pour un lignage de données ou un historique de versions. Remède : une pile explicite (liste) au lieu d'appels récursifs, ou Kahn, sans récursion. Relever la limite repousse le problème et peut faire planter l'interpréteur.
- Usage : ✅ pile explicite ou Kahn pour des graphes profonds · ❌ `sys.setrecursionlimit(10**6)` en production.

```python
# Exemple 1 : une chaîne de 5 000
import sys
sys.getrecursionlimit()   # → 1000
def prof(g, n):
    return 1 + max((prof(g, p)
                    for p in g.get(n, ())),
                   default=0)

chaine = {i: [i + 1] for i in range(5000)}
prof(chaine, 4990)   # → 11
prof(chaine, 0)      # ❌ RecursionError
```

- Quiz : Et `TopologicalSorter(chaine).static_order()` sur la même chaîne ?
- [x] Il trie les 5 001 nœuds sans erreur
- [ ] `RecursionError` aussi
- [ ] `CycleError`
- Réponse : il trie sans erreur (mesuré : 5 001 nœuds, le dernier n'étant qu'un prérequis) : `graphlib` suit l'algorithme de Kahn, itératif.
