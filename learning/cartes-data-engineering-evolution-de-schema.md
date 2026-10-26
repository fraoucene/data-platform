---
title: "Cartes · Évolution de schéma"
type: cartes
langage: Data engineering
chapitre: Fiabiliser
cours: Évolution de schéma
created: 2026-10-26
updated: 2026-10-26
---

# Cartes · Évolution de schéma
Data engineering · Évolution de schéma : changements compatibles ou cassants, changement parallèle, identifiants stables, migration de données existantes.

## 1. changement : compatible ou cassant
- Id : evolution-de-schema-compatible-ou-cassant
- Sous-thème : changements
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : ingestion-evenement-cles-inconnues, qualite-contrat-de-donnees
- Source : revision-pwa · pwa-parcours
- Définition : Un changement de format est compatible si les lecteurs existants lisent encore les données ; renommer, supprimer ou retyper un champ les casse.
- Contexte : Ajouter un champ facultatif passe : un lecteur tolérant l'ignore. Renommer revient à supprimer puis ajouter : l'ancien lecteur ne trouve plus son champ. Rendre obligatoire un champ nouveau casse dans l'autre sens : les anciennes données deviennent invalides pour le nouveau lecteur. Avant de livrer, poser la question des deux côtés : l'ancien lecteur lit-il la nouvelle donnée, le nouveau lecteur lit-il l'ancienne ?
- Usage : ✅ classer chaque changement d'un contrat (fichiers, événements, API, colonnes) avant de le livrer · ❌ livrer un renommage « cosmétique » d'un coup : passer par un changement parallèle.

```python
# Exemple 1 : l'ancien lecteur, deux formats
def lire_v3(carte):
    return carte["Niveau"]

ajout = {"Niveau": 1, "Id": "listes-lire"}
lire_v3(ajout)        # → 1   (champ en plus ignoré)
renomme = {"niveau": 1}
lire_v3(renomme)      # ❌ KeyError
```

- Quiz : Le nouveau lecteur exige un `Id` sur chaque carte. Quelles données casse-t-il ?
- [ ] Aucune : ajouter un champ est compatible
- [x] Les anciens fichiers, sans `Id`
- [ ] Les nouveaux fichiers, avec `Id`
- [ ] Seulement les `Id` en double
- Réponse : les anciens fichiers : un champ ajouté **et obligatoire** est cassant pour le nouveau lecteur ; on ne l'exige que pour les fichiers qui se déclarent dans la nouvelle version.

## 2. changement parallèle : expand, migrate, contract
- Id : evolution-de-schema-changement-parallele
- Sous-thème : changements
- Type : concept
- Niveau : 1
- Profils : débutant, data, ops
- Prérequis : evolution-de-schema-compatible-ou-cassant
- Voir aussi : evolution-de-schema-lecteur-avant-producteur, evolution-de-schema-quand-contracter
- Source : revision-pwa · pwa-parcours
- Définition : Le changement parallèle (expand / contract) fait évoluer un format en trois temps : accepter les deux, migrer les producteurs, retirer l'ancien.
- Contexte : Expand : le lecteur accepte l'ancien et le nouveau format. Migrate : les producteurs passent au nouveau, à leur rythme. Contract : quand plus aucun n'émet l'ancien, le lecteur cesse de l'accepter. À chaque instant, tout ce qui circule reste lisible. C'est ainsi qu'on renomme une colonne partagée (ajouter, remplir, basculer les lecteurs, supprimer) et qu'on est passé des cartes v3 aux v4.
- Usage : ✅ format lu par un autre programme déployé séparément (fichiers, événements, colonnes, API) · ❌ code interne livré d'un bloc : un simple refactor suffit.

```python
# Exemple 1 : phase expand du lecteur
def lire_id(entete, carte):
    if "chapitre" in entete:   # v4
        return carte["Id"]
    # v3 : id positionnel
    return f"{entete['cours']}/{carte['n']}"

v3 = {"cours": "Listes"}
lire_id(v3, {"n": 12})   # → 'Listes/12'
v4 = {"cours": "Listes", "chapitre": "B"}
lire_id(v4, {"Id": "listes-lire"})
# → 'listes-lire'
```

- Quiz : Renommer la colonne `dateparution` en `date_parution`, lue par trois jobs : première étape ?
- [ ] Renommer la colonne, puis corriger les jobs
- [ ] Corriger les trois jobs pour lire `date_parution`
- [x] Ajouter `date_parution` et la remplir, sans toucher l'autre
- [ ] Supprimer `dateparution` en fenêtre de maintenance
- Réponse : ajouter la nouvelle colonne : expand d'abord ; les jobs basculent ensuite (migrate), l'ancienne colonne ne part qu'en dernier (contract).

## 3. identifiant positionnel : il désigne une place
- Id : evolution-de-schema-id-positionnel
- Sous-thème : identifiants
- Type : piège
- Niveau : 1
- Profils : débutant, data, web
- Voir aussi : evolution-de-schema-id-stable
- Source : revision-pwa · pwa-parcours
- Définition : Un identifiant positionnel (`Listes/12`) dépend de la place de l'élément : insérer, trier ou supprimer lui fait désigner un autre élément.
- Contexte : Pratique au départ (rien à inventer), il casse dès que la liste bouge : une carte insérée au niveau 1 décale toutes les suivantes, et les réponses enregistrées sur `Listes/12` se rattachent sans erreur à la carte qui a pris cette place. Le bug est silencieux : les données restent valides, leur sens a changé. Même problème que l'index d'un tableau utilisé comme `key` React.
- Usage : ✅ ordre d'affichage, numéro dans un message d'erreur · ❌ clé de stockage, de lien ou de jointure : un identifiant stable.

```python
# Exemple 1 : une insertion décale tout
cartes = ["lire", "tranche", "trier"]
reponse = 2          # sur « tranche »
cartes[reponse - 1]  # → 'tranche'
cartes.insert(0, "créer")
cartes[reponse - 1]  # → 'lire'
```

- Quiz : On supprime la **dernière** carte d'un thème de 20. Les réponses sur `Listes/1` à `Listes/19` restent-elles justes ?
- [x] Oui : aucune carte avant elle n'a bougé
- [ ] Non : toutes sont décalées d'un cran
- [ ] Non : la suppression renumérote depuis 0
- Réponse : oui : seules les positions après la modification changent ; c'est ce qui rend le bug intermittent (une insertion en tête, elle, décale tout).

## 4. identifiant stable : écrit une fois
- Id : evolution-de-schema-id-stable
- Sous-thème : identifiants
- Type : concept
- Niveau : 1
- Profils : débutant, data, web
- Prérequis : evolution-de-schema-id-positionnel
- Voir aussi : evolution-de-schema-id-jamais-reattribue
- Source : revision-pwa · pwa-parcours
- Définition : Un identifiant stable est choisi une fois pour un élément et ne change plus, quels que soient son ordre, son titre ou son contenu.
- Contexte : Il est écrit dans la donnée (`- Id : listes-tranche-hors-bornes`), pas déduit de sa place. Lisible et préfixé par son espace (le thème) pour rester unique, il sert de clé aux réponses, aux liens et aux parcours ; le numéro ne garde que l'ordre d'affichage. Côté React, c'est la `key` tirée d'un id métier plutôt que de l'index.
- Usage : ✅ tout ce que d'autres données référencent (réponses, liens, jointures) · ❌ le dériver d'un champ qui peut changer (titre, position) : il change avec lui.

```python
# Exemple 1 : la place change, l'id non
cartes = [{"id": "listes-lire"},
          {"id": "listes-tranche"}]
reponse = "listes-tranche"
cartes.insert(0, {"id": "listes-creer"})
ids = [c["id"] for c in cartes]
ids.index(reponse)   # → 2   (même carte)
```

- Quiz : Pourquoi ne pas calculer l'Id à la lecture avec `slug(titre)` ?
- [ ] Un slug ne peut pas contenir d'accents
- [x] Corriger le titre changerait l'Id
- [ ] Deux slugs ne se comparent pas
- [ ] Le calcul est trop lent à la lecture
- Réponse : corriger le titre changerait l'Id : un id calculé suit sa source ; il s'écrit une fois dans la donnée et ne bouge plus.

## 5. déploiement : le lecteur avant le producteur
- Id : evolution-de-schema-lecteur-avant-producteur
- Sous-thème : déploiement
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : evolution-de-schema-changement-parallele
- Voir aussi : evolution-de-schema-marqueur-de-version
- Source : revision-pwa · pwa-parcours
- Définition : Un nouveau format se déploie lecteur d'abord, producteurs ensuite : l'ancien lecteur ne sait pas lire ce qu'il n'a jamais vu.
- Contexte : Publier les fichiers v4 avant de déployer le parser v4 dans la Lambda : l'ancien parser rencontre `- Id :`, rejette chaque fichier, le catalogue se vide. Dans l'autre ordre, rien ne casse : le nouveau parser lit encore les fichiers v3. Même règle pour une API (le serveur accepte le champ avant que les clients l'envoient) ou une table (la colonne existe avant d'être écrite).
- Usage : ✅ lecteur tolérant déployé et vérifié, puis producteurs, puis contract · ❌ un seul commit pour lecteur et producteurs déployés séparément : l'ordre réel n'est plus maîtrisé.

```python
# Exemple 1 : l'ancien lecteur est strict
CHAMPS_V3 = {"Niveau", "Quiz"}
def lire_v3(carte):
    inconnus = set(carte) - CHAMPS_V3
    if inconnus:
        raise ValueError(sorted(inconnus))
    return carte

lire_v3({"Niveau": 1, "Quiz": "?"})
lire_v3({"Niveau": 1, "Quiz": "?",
         "Id": "listes-lire"})  # ❌ ValueError
```

- Quiz : Lambda v4 déployée, fichiers encore en v3, puis on publie **un** fichier v4. Que contient le catalogue ?
- [ ] Seulement le fichier v4
- [ ] Rien : formats mélangés
- [x] Tous les fichiers, v3 et v4
- [ ] Les v3 ; le v4 est rejeté
- Réponse : tous : pendant l'expand le lecteur accepte les deux formats ; c'est ce qui permet de migrer les producteurs un par un.

## 6. marqueur de version : la donnée dit ses règles
- Id : evolution-de-schema-marqueur-de-version
- Sous-thème : changements
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : evolution-de-schema-changement-parallele
- Source : revision-pwa · pwa-parcours
- Définition : Un marqueur de version dans la donnée (champ `version`, ou présence d'un champ comme `chapitre:`) dit au lecteur quelles règles appliquer.
- Contexte : Sans marqueur, le lecteur devine : il valide trop peu (un v4 incomplet passe pour un v3) ou trop (un v3 rejeté). Avec un marqueur, les champs v4 sont obligatoires dès que le fichier se déclare v4, facultatifs sinon. Un numéro explicite (`"version": 2`) est plus clair qu'une présence de champ, pratique quand le format n'avait pas prévu de version.
- Usage : ✅ un marqueur par fichier ou par message, lu avant le reste · ❌ deviner la version à la forme du contenu (« s'il y a un Id, c'est du v4 »).

```python
# Exemple 1 : obligatoire selon la version
def manquants(entete, carte):
    v4 = "chapitre" in entete
    requis = {"Id", "Type"} if v4 else set()
    return sorted(requis - set(carte))

manquants({"cours": "Listes"}, {})
# → []
manquants({"chapitre": "B"}, {"Id": "x"})
# → ['Type']
```

- Quiz : Un fichier migré a perdu son `chapitre:` mais ses cartes ont un `Id`. Que fait ce lecteur ?
- [ ] Il le rejette : `chapitre` manque
- [x] Il le lit en v3, sans contrôler `Type`
- [ ] Il le lit en v4 grâce aux `Id`
- [ ] Il lève `KeyError` sur `chapitre`
- Réponse : il le lit en v3 : le marqueur décide seul ; l'oublier désactive les contrôles v4 sans erreur, d'où un test qui vérifie que les fichiers migrés le portent.

## 7. évolution de schéma : ajouter, jamais renommer
- Id : ingestion-evolution-de-schema
- Sous-thème : changements
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : evolution-de-schema-compatible-ou-cassant
- Voir aussi : qualite-contrat-de-donnees
- Définition : Une source change de schéma avec le temps : un champ ajouté se tolère, un champ renommé ou retypé casse les consommateurs.
- Contexte : Un lecteur tolérant ignore les champs inconnus et met une valeur par défaut aux absents : l'ajout passe sans incident. Un renommage, lui, ressemble à « un champ disparu, un nouveau apparu » : la colonne devient nulle en silence. On compare donc à chaque run les clés reçues aux clés attendues, et on alerte sur toute disparition. BODACC expose son schéma (32 champs typés) dans les métadonnées du dataset.
- Usage : ✅ comparer reçu et attendu à chaque run, alerter sur un champ disparu, tolérer l'ajout · ❌ attendre un `KeyError` en production, ou `.get()` partout sans contrôle : le renommage passe inaperçu.

```python
# Exemple 1 : ce qui a changé
attendu = {"id", "dateparution",
           "familleavis"}
recu = {"id", "date_parution",
        "familleavis", "region_code"}
sorted(attendu - recu)
# → ["dateparution"]   (disparu : alerte)
sorted(recu - attendu)
# → ["date_parution", "region_code"]
```

```python
# Exemple 2 : .get() masque le renommage
a = {"id": "A1",
     "date_parution": "2026-10-20"}
a.get("dateparution")  # → None
# colonne nulle, aucune erreur
```

- Quiz : Exemple 1 : la source garde les mêmes clés mais `familleavis` passe d'une chaîne à une liste. Que vaut `attendu - recu` ?
- [ ] `{"familleavis"}`
- [x] `set()`
- [ ] `TypeError`
- Réponse : `set()` : comparer les noms de clés ne voit pas les types ; contrôler aussi le type de chaque champ (modèle pydantic, schéma déclaré).

## 8. identifiant : jamais réattribué
- Id : evolution-de-schema-id-jamais-reattribue
- Sous-thème : identifiants
- Type : piège
- Niveau : 2
- Profils : data, web
- Prérequis : evolution-de-schema-id-stable
- Source : revision-pwa · pwa-parcours
- Définition : Un identifiant libéré par une suppression n'est jamais redonné à un autre élément : les données qui le citent désigneraient la nouvelle chose.
- Contexte : Réponses, cartes vues et liens d'autres cartes gardent l'ancien id. Le réattribuer les fait pointer, sans erreur, vers un autre point. Une carte réécrite sur le même point garde son Id ; une carte supprimée laisse un id orphelin, que le lecteur ignore. Même règle qu'un numéro de facture ou une clé primaire : pas de recyclage.
- Usage : ✅ supprimer et laisser les références orphelines être ignorées · ❌ « boucher le trou » avec un nouvel élément sous l'ancien id.

```python
# Exemple 1 : la réponse change de sens
reponses = {"listes-tranche-pas": "ok"}
cartes = {"listes-tranche-pas": "pas"}
del cartes["listes-tranche-pas"]
# recyclé pour une autre notion :
cartes["listes-tranche-pas"] = "tri"
cible = next(iter(reponses))
cartes[cible]   # → 'tri'
```

- Quiz : Une carte est supprimée ; ses réponses restent dans DynamoDB sous son Id. Que doit faire l'app ?
- [ ] Les supprimer au démarrage
- [ ] Les rattacher à la carte suivante
- [x] Les ignorer : aucune carte ne porte cet Id
- [ ] Refuser de charger le catalogue
- Réponse : les ignorer : un id inconnu ne désigne rien et ne compte pas ; rien n'oblige à nettoyer la donnée, et la rattacher ailleurs la fausserait.

## 9. table de correspondance : traduire à la lecture
- Id : evolution-de-schema-table-de-correspondance
- Sous-thème : migration
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : evolution-de-schema-id-stable
- Voir aussi : evolution-de-schema-traduire-ou-reecrire
- Source : revision-pwa · pwa-parcours
- Définition : Une table de correspondance (ancien id → nouvel id), produite une fois à la migration, traduit à la lecture les données enregistrées avant.
- Contexte : Les réponses v3 (`Python/Listes/12`) restent stockées telles quelles ; l'app les traduit en chargeant `spec/ids-v3.json` (1 545 entrées). La table est figée : elle décrit le catalogue au jour de la migration, quand les anciennes positions avaient encore un sens. Les nouvelles écritures utilisent directement le nouvel id.
- Usage : ✅ données dispersées (plusieurs appareils, hors ligne) qu'on ne peut pas toutes réécrire · ❌ table regénérée après coup : les anciennes positions ne désignent plus les mêmes cartes.

```python
# Exemple 1 : traduire à la lecture
IDS_V3 = {"Python/Listes/12":
          "Python/listes-tranche"}
lues = ["Python/Listes/12",
        "Python/listes-lire"]
ids = [IDS_V3.get(i, i) for i in lues]
ids[0]   # → 'Python/listes-tranche'
ids[1]   # → 'Python/listes-lire'
```

- Quiz : Pourquoi traduire avec `IDS_V3.get(i, i)` plutôt que `IDS_V3[i]` ?
- [ ] `.get` est plus rapide sur un gros dict
- [x] Les ids déjà stables ne sont pas dans la table
- [ ] `IDS_V3[i]` renvoie `None` si absent
- [ ] La table contient des clés en double
- Réponse : les ids v4 (et ceux de cartes supprimées) ne sont pas dans la table : `[i]` lèverait `KeyError` ; `.get(i, i)` les laisse tels quels.

## 10. migration : lots disjoints en parallèle
- Id : evolution-de-schema-lots-disjoints
- Sous-thème : migration
- Type : recette
- Niveau : 2
- Profils : data, ops
- Voir aussi : evolution-de-schema-valider-sur-copie
- Source : revision-pwa · pwa-parcours
- Définition : Une migration de nombreux fichiers se découpe en lots disjoints traités en parallèle : aucun fichier n'appartient à deux lots.
- Contexte : Deux agents (ou workers) qui écrivent le même fichier se marchent dessus : la dernière écriture gagne et efface l'autre, sans erreur. Avec des lots disjoints, chaque lot se lance, se relance et se vérifie seul. Chaque lot produit aussi sa part de la table de correspondance, fusionnée à la fin ; une clé présente dans deux parts trahit un découpage faux.
- Usage : ✅ beaucoup de fichiers indépendants (70 fichiers de cartes, partitions d'un lake) · ❌ fichiers qui se citent entre eux pendant la migration : une seconde passe séquentielle (les liens, phase 2).

```python
# Exemple 1 : répartir sans recouvrement
fichiers = [f"cartes-{n}.md"
            for n in range(7)]
lots = [fichiers[i::3] for i in range(3)]
len(lots[0]), len(lots[2])  # → (3, 2)
tous = [f for lot in lots for f in lot]
len(set(tous)) == len(tous) == 7  # → True
```

- Quiz : On fusionne deux tables partielles par `{**t1, **t2}` ; une clé est dans les deux. Qu'obtient-on ?
- [ ] Une `KeyError` à la fusion
- [ ] La valeur de `t1`
- [x] La valeur de `t2`, sans avertissement
- [ ] Une liste des deux valeurs
- Réponse : la valeur de `t2` : la fusion écrase en silence ; vérifier avant que `t1.keys() & t2.keys()` est vide, sinon deux lots ont migré la même carte.

## 11. migration : valider sur une copie
- Id : evolution-de-schema-valider-sur-copie
- Sous-thème : migration
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : evolution-de-schema-lots-disjoints
- Source : revision-pwa · pwa-parcours
- Définition : Pendant une migration en parallèle, chaque lot se valide sur une copie de ses propres fichiers, pas sur le dossier partagé.
- Contexte : Valider le dossier commun pendant que d'autres lots l'écrivent montre leurs fichiers à moitié écrits : erreurs fantômes, ou faux vert si un fichier est lu avant d'être modifié. Copier ses fichiers dans un dossier temporaire (`CARDS_DIR=…`) donne un état figé, imputable au seul lot. La validation complète a lieu une fois, à la fin, quand plus rien n'écrit.
- Usage : ✅ validation isolée par lot, puis une validation globale finale · ❌ la validation globale relancée à chaque lot fini pendant que d'autres tournent.

```bash
# Exemple 1 : valider son lot seul
d=$(mktemp -d)
cp learning/cartes-web-dom.md \
   learning/cartes-web-vite.md "$d"
make -C ~/Desktop/workspace/revision-pwa \
  cards-validate CARDS_DIR="$d"
# ne lit que les 2 fichiers copiés
```

- Quiz : Chaque lot a validé sa copie : tout est vert. Que peut encore refuser la validation finale ?
- [ ] Rien : des lots valides font un tout valide
- [ ] Un exemple Python d'un des lots
- [ ] Le format d'un fichier d'un lot
- [x] Un même Id dans deux lots
- Réponse : un même Id dans deux lots : l'unicité dans le domaine (et les liens entre fichiers) ne se voit qu'avec tous les fichiers réunis ; d'où la validation globale à la fin.

## 12. table de correspondance : vérifier les deux sens
- Id : evolution-de-schema-verifier-la-table
- Sous-thème : migration
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : evolution-de-schema-table-de-correspondance
- Source : revision-pwa · pwa-parcours
- Définition : Une table de correspondance se vérifie dans les deux sens : chaque ancien id a une cible, et chaque cible existe dans le nouveau catalogue.
- Contexte : Un ancien id sans correspondance perd ses données en silence ; une cible inexistante (faute de frappe, carte renommée après coup) les rattache à rien. Les deux contrôles se font avant publication, contre l'ancien et le nouveau catalogue : « 1 545 ids traduits, 0 sans correspondance, 0 cible inexistante ».
- Usage : ✅ deux comptes à zéro avant de livrer la table · ❌ vérifier seulement que le JSON se charge.

```python
# Exemple 1 : les deux contrôles
anciens = {"L/1", "L/2", "L/3"}
nouveaux = {"listes-lire", "listes-tri"}
table = {"L/1": "listes-lire",
         "L/2": "listes-trie"}
sorted(anciens - table.keys())
# → ['L/3']   (sans correspondance)
sorted(set(table.values()) - nouveaux)
# → ['listes-trie']   (cible inexistante)
```

- Quiz : Une carte v3 a été scindée en deux cartes v4. Combien d'entrées pour son ancien id ?
- [x] Une : vers une seule des deux cartes
- [ ] Deux : une par carte issue de la scission
- [ ] Aucune : une carte scindée perd ses réponses
- Réponse : une : une clé n'a qu'une valeur ; la réponse va à la carte qui garde le point principal (1 545 ids traduits pour 1 555 cartes : 10 scissions).

## 13. migrer : traduire à la lecture ou réécrire
- Id : evolution-de-schema-traduire-ou-reecrire
- Sous-thème : migration
- Type : choisir
- Niveau : 3
- Profils : data, expert
- Prérequis : evolution-de-schema-table-de-correspondance
- Source : revision-pwa · pwa-parcours
- Définition : Migrer des données existantes : soit les réécrire une fois (backfill), soit les laisser et les traduire à chaque lecture.
- Contexte : Réécrire donne des données propres mais exige de toutes les atteindre : ici, des réponses sur plusieurs appareils, hors ligne, dans le localStorage et dans DynamoDB ; un appareil oublié resterait en v3. Traduire à la lecture ne touche à rien, marche partout et se teste seul ; le prix est une table à garder tant que d'anciennes données peuvent arriver. Pour une table centrale, le backfill est souvent plus simple.
- Usage : ✅ réécrire : données centralisées, volume connu, un job · ✅ traduire : données dispersées ou hors ligne · ❌ réécrire pendant que des clients écrivent encore l'ancien format.

```python
# Exemple 1 : un appareil revient en ligne
IDS_V3 = {"Python/Listes/12":
          "Python/listes-tranche"}
def lire(i):
    return IDS_V3.get(i, i)

# réponse créée hier, hors ligne,
# synchronisée aujourd'hui en v3
lire("Python/Listes/12")
# → 'Python/listes-tranche'
```

- Quiz : Toutes les réponses de DynamoDB ont été réécrites en v4. Un iPad hors ligne depuis une semaine se synchronise : que se passe-t-il ?
- [ ] Rien : DynamoDB refuse les anciens ids
- [x] Il envoie des réponses v3 que le backfill n'a pas vues
- [ ] DynamoDB traduit ses ids à l'écriture
- Réponse : il envoie des réponses v3 : sa file d'envoi locale n'a jamais été migrée ; un backfill central rate les données encore en route, d'où la traduction à la lecture.

## 14. contract : seulement après la mesure
- Id : evolution-de-schema-quand-contracter
- Sous-thème : déploiement
- Type : concept
- Niveau : 3
- Profils : data, ops, expert
- Prérequis : evolution-de-schema-changement-parallele
- Source : revision-pwa · pwa-parcours
- Définition : La phase contract (retirer l'ancien format) n'a lieu qu'après avoir mesuré qu'aucun producteur ni aucune donnée stockée ne l'utilise encore.
- Contexte : Tant qu'un fichier v3 existe dans une source, retirer le support v3 l'écarte du catalogue. On compte d'abord (fichiers sans `chapitre:` dans toutes les sources : 0), puis on rend le marqueur obligatoire. Les données stockées comptent aussi : `ids-v3.json` reste tant que des réponses v3 peuvent arriver. Beaucoup de migrations restent bloquées en expand faute de cette mesure.
- Usage : ✅ contract après une mesure à zéro, dans un changement séparé · ❌ contract dans le même déploiement que l'expand, ou « plus tard » sans mesure.

```python
# Exemple 1 : la mesure avant contract
sources = {
    "data-platform": ["v4", "v4"],
    "revision-pwa": ["v4", "v3"],
}
restants = [p for p, fs in sources.items()
            if "v3" in fs]
restants   # → ['revision-pwa']
# contract interdit tant que non vide
```

- Quiz : Tous les fichiers sont en v4 depuis un mois. Peut-on supprimer `ids-v3.json` ?
- [ ] Oui : plus aucun fichier n'est en v3
- [ ] Oui : les réponses ont été traduites une fois
- [x] Non : un appareil peut encore envoyer des réponses v3
- [ ] Non : le parser en a besoin pour lire le v4
- Réponse : non : fichiers et données stockées sont deux contrats distincts ; un appareil resté hors ligne renvoie encore des ids v3, que seule la table traduit.

## 15. table de correspondance : figée à la migration
- Id : evolution-de-schema-table-figee
- Sous-thème : migration
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : evolution-de-schema-table-de-correspondance
- Source : revision-pwa · pwa-parcours
- Définition : Une table qui traduit des ids positionnels se produit une seule fois, au moment de la migration, puis ne se régénère jamais.
- Contexte : Elle traduit « la 12e carte de Listes le 2026-10-26 ». Le lendemain, `/cartes` renumérote : `Listes/12` désigne une autre carte. Régénérer la table depuis les fichiers du jour rattacherait les vieilles réponses aux mauvaises cartes, sans erreur. On la commite comme une donnée historique et on n'y touche plus.
- Usage : ✅ produite pendant la migration depuis l'état d'avant, puis commitée et figée · ❌ la recalculer à chaque build depuis les numéros actuels.

```python
# Exemple 1 : régénérer = rattacher ailleurs
def table(cartes):
    return {f"Listes/{n}": f"listes-{c}"
            for n, c in enumerate(cartes, 1)}

jour_j = table(["lire", "tranche"])
apres = table(["creer", "lire", "tranche"])
jour_j["Listes/2"]  # → 'listes-tranche'
apres["Listes/2"]   # → 'listes-lire'
```

- Quiz : `/cartes` ajoute une carte v4 au thème Listes. Faut-il une entrée dans `ids-v3.json` ?
- [ ] Oui : chaque carte doit y figurer
- [x] Non : elle n'a jamais eu d'id v3
- [ ] Oui : sinon ses réponses sont perdues
- [ ] Non, mais il faut régénérer la table
- Réponse : non : la table ne traduit que des ids écrits avant la migration ; une carte v4 naît avec son Id stable, que ses réponses utilisent directement.
