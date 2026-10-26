---
card: "revision-pwa · chapitres, parcours et qualité des cartes"
id_short: aucun
learning_id: pwa-parcours
board: fMaiYRrn
url: aucune
created: 2026-10-26
updated: 2026-10-26
status: en-cours
---

# revision-pwa · chapitres, parcours et qualité des cartes
Liste : hors board (suite de `pwa-revision` et `pwa-sync`) · Échéance : aucune · Étiquettes : front, contenu, agent, migration

## Objectif
Le catalogue grossit à chaque projet (1 555 cartes le 2026-10-26) : 25 thèmes Python à plat, aucun lien entre cartes, et un id de carte positionnel (`Python/Listes/12`) qui change dès que `/cartes` renumérote. À la fin de ce cours, chaque carte a un **id stable** et des métadonnées (type, profils, prérequis, voir aussi), les thèmes sont groupés en **chapitres**, et l'app propose des **parcours** (Python débutant, Python pour la data, Data engineer sur AWS…) composés de règles, qui se remplissent seuls à mesure que de nouvelles cartes arrivent — Pourquoi ça compte : c'est une migration de schéma sur des données déjà en production (réponses synchronisées), le même problème que faire évoluer un contrat de données sans casser les consommateurs.

### Décisions du 2026-10-26
- **Id stable par carte** (`- Id : listes-tranche-hors-bornes`, préfixé par le thème, unique dans le domaine) : les réponses, cartes vues et parcours s'y rattachent ; le numéro ne sert plus qu'à l'ordre d'affichage.
- **Chapitre au niveau du thème** (`chapitre:` dans l'en-tête du fichier + registre `chapitres` de `domaines.json`), pas sur chaque carte : un thème ne peut pas finir dans deux chapitres.
- **Parcours = règles** (`spec/parcours.json` : domaines / chapitres / thèmes, niveau, profils, types), jamais une liste de cartes ; ordre dans une étape par prérequis (tri topologique).
- **Migration sans réécrire les données** : les réponses déjà enregistrées gardent leur ancien id ; l'app les traduit à la lecture par la table `spec/ids-v3.json` (1 545 entrées).
- **Parser tolérant pendant la transition** : un fichier sans `chapitre:` reste lu en v3 ; la Lambda a reçu le parser v4 **avant** la publication des fichiers migrés.

## Prérequis
### Faire évoluer un format sans casser les lecteurs
Changer un format lu par un autre programme (ici : fichiers de cartes → Lambda → app) se fait en trois temps : 1) le lecteur accepte l'ancien et le nouveau format ; 2) les producteurs passent au nouveau ; 3) on rend le nouveau obligatoire. Déployer le producteur avant le lecteur = le lecteur rejette tout. Même logique que l'ajout d'une colonne dans un schéma de table partagé.
Doc : https://martinfowler.com/bliki/ParallelChange.html
Exercice 5 min : pour la v4, écrire dans quel ordre on déploie la Lambda, publie les fichiers et déploie l'app, et ce qui casse si on inverse les deux premiers.

### Tri topologique
Ordonner des éléments qui ont des dépendances (« A avant B ») : on prend à chaque tour un élément dont toutes les dépendances sont déjà placées. Un cycle (A avant B avant A) rend l'ordre impossible : on le détecte par un parcours en profondeur qui retombe sur un nœud « en cours ».
Doc : https://fr.wikipedia.org/wiki/Tri_topologique
Exercice 5 min : ordonner à la main `tranche` (prérequis `index`), `index`, `hors-bornes` (prérequis `tranche`) en gardant l'ordre initial quand rien ne l'empêche.

## Étapes
### [x] Étape 1 — Spec v4 et parser
- À faire : c'est quoi : le contrat des fichiers de cartes, version 4. Pourquoi ici : tout le reste (migration, app, agent) suit la spec et le parser. Objectif : un fichier v4 est validé champ par champ, un fichier v3 reste accepté.
  1. `spec/cartes.md` : `chapitre:` dans l'en-tête ; `Id`, `Type`, `Profils`, `Prérequis`, `Voir aussi` ; sections Qualité et Parcours.
  2. `app/scripts/parse-cards.ts` : nouveaux champs, obligatoires si `chapitre:` est présent ; id = `Domaine/Id`.
  3. `app/lambda/catalog.ts` : liens vers une carte absente et cycles de prérequis → avertissements (Lambda), erreurs pour `make cards`.
- Concept : changement parallèle (expand / contract), validation à deux niveaux (fichier, catalogue).
- Vérifier : `pnpm --dir app test` → vert (tests v4 : champs obligatoires, valeurs refusées, liens, cycle)
- Résultat : parser et catalogue v4, 9 tests ajoutés ; un fichier v3 reste lu avec son id positionnel.

### [x] Étape 2 — Chapitres et parcours
- À faire : `spec/domaines.json` : `chapitres` (7 domaines, 2 à 7 chapitres chacun) à la place de l'ordre `parcours` des thèmes, et `profils` (débutant, data, web, ops, expert) ; `spec/parcours.json` : 8 parcours en règles.
- Concept : regrouper par sens (chapitre) plutôt que par liste ; un parcours défini par des filtres reste juste quand le catalogue grossit.
- Vérifier : `pnpm --dir app test` → test « chapitres et thèmes cités existent dans domaines.json » vert
- Résultat : Python en 5 chapitres (Bases du langage, Python idiomatique, Fichiers et formats, Qualité et outillage, Système et réseau), AWS en 7.

### [x] Étape 3 — Migration des 1 545 cartes (phase 1)
- À faire : 9 agents en parallèle sur des fichiers disjoints : `chapitre:`, `Id`, `Type`, `Profils` sur chaque carte, sous-thèmes qui étaient des catégories (`bases`, `pièges`) renommés en sujets, et la checklist qualité (un point par carte, quiz sur ce point, affirmations à jour, exemples lisibles, niveaux). Chaque agent écrit la correspondance ancien numéro → Id.
- Concept : migration par lots isolés, validation sur une copie (les autres lots changent en même temps), table de correspondance.
- Vérifier : `make -C ~/Desktop/workspace/revision-pwa cards` → `1555 cartes valides` ; table `spec/ids-v3.json` → 1 545 ids traduits, 0 sans correspondance, 0 cible inexistante
- Résultat : 1 555 cartes v4 (10 scissions), dizaines de quiz recentrés sur leur point, affirmations corrigées après mesure (PEP 758 en 3.14, octet OS de gzip en 3.13, reflog 30 jours, `rate(1 day)`…).

### [x] Étape 4 — Liens entre cartes (phase 2)
- À faire : 4 agents par domaine, avec l'index de toutes les cartes : `Prérequis` (0 à 3, l'indispensable) et `Voir aussi` (0 à 3 : solution, suite, notion voisine).
- Vérifier : `make cards` → 0 lien vers une carte absente, 0 cycle
- Cours : un prérequis = ce sans quoi la carte est incompréhensible (0 à 3) ; un voir-aussi = la solution d'un problème montré, la suite, la notion voisine qu'on confond, l'équivalent dans un autre domaine. Les agents ont élagué les prérequis « carte d'ouverture du thème » et les voir-aussi qui doublaient un prérequis.
- Résultat : 943 cartes avec prérequis, liens croisés entre domaines (ETag HTTP ↔ ETag S3, `compare_digest` Python ↔ Web Crypto, OIDC CI ↔ IAM) ; `make cards` : 1 555 cartes, 0 avertissement.

### [x] Étape 5 — App : ids stables, chapitres, parcours, Voir aussi
- À faire : réponses v3 traduites à la lecture (`ids-v3.json`) ; cartes vues une à une (ligne `C#<id>` synchronisée) ; frise des thèmes coupée par chapitre ; écran Parcours (liste, étapes, « Continuer ») ; type et Voir aussi sur la carte.
- Vérifier : `pnpm --dir app test` → vert ; sur l'iPhone : Parcours guidés → Python débutant → Commencer
- Cours : un parcours est résolu à l'exécution sur le catalogue du moment (`resolveParcours`) ; une carte n'entre que dans la première étape qui la choisit ; dans l'étape, niveau croissant puis tri topologique stable (une carte attend ses prérequis présents dans l'étape).
- Cours : les réponses enregistrées avant la v4 ne sont pas réécrites (DynamoDB comme `localStorage`) : `readAnswers` traduit l'ancien id à la lecture par `spec/ids-v3.json` ; une carte vue devient une ligne synchronisée `C#<id>` (union, première date).
- Erreur vue : test de synchro en échec après l'ajout de la table : il utilisait `Python/Listes/1`, ancien id désormais traduit → ids de test hors table, et un test dédié à la traduction.
- Résultat : 76 tests ; tailles mesurées des parcours : Python débutant 119 cartes, Python pour la data 378, Python expert 153, AWS serverless 283, Data engineer sur AWS 409, Terraform débutant 113, DevOps 270, App web sur AWS 190.

### [x] Étape 6 — Agent `/cartes` v4, publication, déploiement
- À faire : la skill écrit Id / Type / Profils / liens, ne change jamais un Id, range un nouveau thème dans un chapitre ; Lambda v4 déployée avant la publication ; publication des 70 fichiers ; push de l'app.
- Vérifier : `make cards-publish` → catalogue en ligne en v4 (`curl …/content/catalog.json | jq '.cards[0].id'` → `"…/…-…"`)
- Résultat : `make up` (Lambda seule, `1 changed`) avant `make cards-publish` ; catalogue en ligne : 1 555 cartes, toutes v4, `AWS/api-sigv4-authorization` en tête ; commit `f3e7afe` (revision-pwa) poussé, sans le travail « splash » d'une autre session (exclu à la main, index vérifié par tsc, tests, lint et build).
- Cartes : +14 Data engineering / Évolution de schéma (15), +14 Data engineering / DAG (14), +12 Web / DOM (13), +14 Web / Modules ES (14), source `revision-pwa · pwa-parcours` (publiées)

### [ ] Étape 7 — Glossaire et mots-clés
- À faire : c'est quoi : un dictionnaire des termes techniques, et sur chaque carte la liste du jargon qu'elle suppose connu. Pourquoi ici : un lecteur qui découvre bute sur OIDC, STS, partition, idempotent, décorateur… et la carte ne les explique pas. Objectif : chaque mot-clé d'une carte s'ouvre en un tap sur une définition simple.
  1. Spec : `learning/glossaire-<domaine>.md` (`## Terme`, Définition ≤ 30 mots, Exemple, Alias, Carte) ; champ `- Mots-clés :` sur les cartes ; un terme défini une seule fois dans tout le catalogue (sans casse ni accents).
  2. Parser `parse-glossaire.ts`, catalogue (`glossaire` dans `catalog.json`, mot-clé inconnu → avertissement), Lambda déployée avant la publication.
  3. App : pastilles sous la définition, fiche en bas d'écran (définition, exemple, lien vers la carte) ; types de carte en clair (recette → Comment faire, choisir → Quel choix ?).
  4. Contenu : 4 agents par domaine (glossaire du domaine + mots-clés des cartes), puis une passe finale seule sur les termes demandés d'un domaine à l'autre.
  5. Skill `/cartes` : chaque génération remplit `Mots-clés` et définit les termes nouveaux dans le glossaire du domaine propriétaire.
- Concept : vocabulaire contrôlé (un terme = une définition, des alias), propriétaire unique d'une donnée partagée.
- Vérifier : `make cards` → 0 erreur, 0 mot-clé absent du glossaire ; sur l'iPhone : tap sur une pastille → définition
- Erreur vue : `make up` attendu pour la seule Lambda a aussi appliqué un changement Cognito d'une autre session (renommage « Stack » des e-mails, déjà commité) : relire chaque ligne du plan avant d'appliquer.
- Cartes : +11 Python / Unicode (13, nouveau thème), +11 Data engineering / Gouvernance (13, nouveau thème), +9 Terraform / CLI (31), +13 termes de glossaire, source `revision-pwa · pwa-parcours` (publiées)

## Pièges courants
1. Publier les fichiers v4 avant de déployer le parser v4 dans la Lambda : l'ancien parser ne connaît pas `- Id :`, la carte entière est rejetée, le catalogue se vide.
2. Renuméroter en gardant l'id positionnel : chaque régénération rattache les réponses enregistrées à une autre carte, sans erreur visible.
3. Changer un Id publié (renommage « pour faire propre ») : même effet ; l'Id est définitif.
4. Un parcours qui liste des cartes : il est faux dès la prochaine génération ; des règles restent justes.
5. Valider un lot pendant que d'autres agents écrivent le même dossier : erreurs fantômes ; valider une copie de ses fichiers.

## Critères de validation
- [x] Déduit de la demande : chaque carte a un id stable et ses réponses déjà enregistrées restent attachées à la bonne carte.
- [x] Déduit de la demande : les thèmes d'un domaine sont groupés en chapitres, choisis par l'agent selon le contenu.
- [ ] Déduit de la demande : l'utilisateur choisit un parcours (Python débutant, Python pour la data, Python expert…) et l'app le guide étape par étape, prochaine carte comprise.
- [ ] Déduit de la demande : une carte générée plus tard par `/cartes` entre seule dans les bons parcours.
- [ ] Déduit de la demande (2026-10-26) : le jargon de chaque carte est listé et défini simplement dans un glossaire, consultable d'un tap ; l'agent l'enrichit à chaque génération.

## Question de compréhension
Pourquoi les réponses déjà synchronisées ne sont-elles pas réécrites dans DynamoDB avec les nouveaux ids, et qu'est-ce qui garantit qu'une carte générée demain entre dans le parcours « Python pour la data » sans toucher à `parcours.json` ?

## Journal
- 2026-10-26 — Analyse de 11 cartes Python (un point par carte, quiz hors sujet, sous-thèmes-catégories, ordre, id positionnel instable) ; plan v4 validé par Fraoucene (« go fait tout ») ; étapes 1 à 3 réalisées le même jour.
- 2026-10-26 — Étapes 4 à 6 : liens posés (4 agents), app v4 (parcours, chapitres, Voir aussi, cartes vues par id), Lambda v4 déployée puis 70 fichiers publiés, `f3e7afe` poussé. Reste : vérifier les parcours sur l'iPhone (critère 3) et une carte générée plus tard (critère 4).
