# Source BODACC — annonces commerciales

Contrat d'entrée du pipeline d'ingestion : ce que l'API renvoie réellement, mesuré le 2026-10-23 sur la journée de parution du 2026-10-20.
Référence pour le client Python (S1-06), la Lambda d'ingestion (S1-07), le scheduler (S1-08), la normalisation (S2-02) et le MERGE Iceberg (S2-05).

BODACC = Bulletin officiel des annonces civiles et commerciales, publié par la DILA à partir des greffes. Chaque événement juridique d'une entreprise y paraît : création, modification, procédure collective, radiation, dépôt des comptes, vente de fonds.

## 1. Source et endpoints

Plateforme OpenDataSoft, API Explore v2.1, lecture publique sans clé.

| Rôle | URL |
| --- | --- |
| Base | `https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales` |
| Schéma et métadonnées | `<base>` : `fields` (32 champs), `metas.default.records_count`, `metas.default.data_processed` |
| Page de résultats | `<base>/records` : `limit` ≤ 100, `offset + limit` ≤ 10 000, `total_count` exact |
| Export complet | `<base>/exports/jsonl` : une annonce JSON par ligne, sans plafond |

Volume total au 2026-10-23 : 51 155 363 annonces.

Doc : https://help.opendatasoft.com/apis/ods-explore-v2/

## 2. Filtres ODSQL utiles

ODSQL est un sous-ensemble de SQL passé en query string (`where`, `select`, `group_by`, `order_by`). Un seul dataset à la fois : pas de jointure, pas de sous-requête.

| Besoin | Paramètre |
| --- | --- |
| Une journée de parution | `where=dateparution=date'2026-10-20'` |
| Familles utiles au projet | `where=... and familleavis in ('creation','collective','radiation')` |
| Volumes par famille | `select=familleavis,count(*) as n&group_by=familleavis` |
| Annulations et rectificatifs | `where=... and typeavis in ('annulation','rectificatif')` |

Règles de syntaxe vérifiées :

- `dateparution` est de type `date` : le littéral `date'…'` est obligatoire. `dateparution='2026-10-20'` renvoie HTTP 400 `IncompatibleTypesInComparisonFilter`.
- `'…'` est un littéral chaîne, `"…"` un nom de champ.
- `>`, `<` ne s'appliquent qu'aux champs `int` et `date`. Sur un champ `text` comme `id`, HTTP 400.
- `count(distinct …)` est approximatif (HyperLogLog) : 8 751 pour 8 596 lignes. Utiliser `total_count` pour tout contrôle de complétude.
- Une erreur renvoie HTTP 400 avec un JSON `{"error_code": "…", "message": "…"}`. Le client doit lire `error_code`.

## 3. Pagination et stratégie retenue

| Test | Résultat |
| --- | --- |
| `/records?limit=101` | HTTP 400 |
| `/records?limit=1&offset=10000` | HTTP 400 |
| `/records?limit=1&offset=9999` | HTTP 200 |

Une journée compte environ 32 000 annonces. La pagination par offset ne peut donc pas la parcourir.

| Stratégie | Appels par jour | Durée mesurée | Remarques |
| --- | --- | --- | --- |
| Offset | impossible | | plafond à 10 000 |
| Keyset sur `id` | impossible | | `id` est `text`, `>` refusé |
| Keyset sur `(publicationavis, numeroannonce)` | 325 | non mesurée | 3 boucles, A, B et C ; `numeroannonce` est contigu de 1 à n dans chaque bulletin |
| Export JSONL | 1 | 4,0 s pour les ids, 5,1 s complet | 59 432 342 octets, environ 1 835 octets par annonce |

**Décision pour `fetch_day(date) -> Iterator[dict]` : export JSONL en streaming.**

- Lecture ligne par ligne, jamais les 59 Mo en mémoire.
- Timeout de lecture d'au moins 60 s.
- Ne pas se fier au content-type : l'export renvoie `application/json` alors que le corps est du JSONL.
- Plan B si l'export devient instable : keyset `publicationavis='X' and numeroannonce > N order by numeroannonce`, une boucle par bulletin.

Forme de `id` : lettre du bulletin + numéro de parution + `numeroannonce` sans zéro de tête, par exemple `A202602018167`. Longueur variable, donc ordre lexical différent de l'ordre numérique.

## 4. Volumes d'une journée et heure de mise à jour

Journée de parution du 2026-10-20 : `total_count` = 32 373.

| `familleavis` | Annonces | Utile au projet |
| --- | ---: | --- |
| `dpc` (dépôt des comptes) | 15 310 | non |
| `creation` | 6 813 | oui |
| `modification` | 5 363 | à décider |
| `radiation` | 3 104 | oui |
| `collective` (procédures collectives) | 937 | oui |
| `immatriculation` | 475 | à décider |
| `vente` | 370 | non |
| `conciliation` | 1 | à décider |

Les trois familles cibles font 10 854 annonces, un tiers du total. Filtrer `familleavis` à la source divise le téléchargement par trois.

| `typeavis` | Annonces |
| --- | ---: |
| `annonce` | 32 182 |
| `annulation` | 166 |
| `rectificatif` | 25 |

Mise à jour : `data_processed` = `2026-10-22T06:17:43 UTC`, soit 08:17 à Paris en heure d'été et 07:17 en heure d'hiver.

Conséquences pour le scheduler (S1-08) :

- Planifier en UTC fixe, au plus tôt vers 07:00 UTC, pour ne pas dépendre du changement d'heure.
- La mise à jour n'est pas quotidienne : le 23 octobre, le dernier traitement datait du 22. Une journée sans parution est normale, `fetch_day` peut renvoyer zéro ligne sans erreur.

## 5. Champs clés et champs imbriqués

Le schéma ODS déclare 26 champs `text`, 1 `date` (`dateparution`) et 3 `int` (`numeroannonce`, `region_code`, `pdf_parution_subfolder`). Onze champs `text` contiennent en réalité du JSON sérialisé : il faut un second `json.loads` sur leur valeur.

Champs imbriqués présents selon la famille, `None` ailleurs :

| `familleavis` | Champs JSON-texte |
| --- | --- |
| toutes | `listepersonnes` |
| `creation`, `immatriculation` | `listeetablissements`, `acte` |
| `vente` | `listeetablissements`, `acte`, `listeprecedentproprietaire` |
| `collective`, `conciliation` | `jugement` |
| `radiation` | `radiationaurcs` |
| `modification` | `modificationsgenerales` |
| `dpc` | `depot` |
| `annulation`, `rectificatif` (tout `typeavis` non `annonce`) | `parutionavisprecedent` |

Pièges de forme constatés sur les 32 373 annonces :

- `listepersonnes.personne` est un objet, ou une liste d'objets quand il y a plusieurs personnes.
- `personne.prenom` est une chaîne, ou une liste de prénoms.
- `typePersonne` vaut `pm` (personne morale, 26 390) ou `pp` (personne physique, 5 983).

Mapping vers les colonnes cibles de `events` :

| Colonne `events` | Chemin source | Cas absent |
| --- | --- | --- |
| `siren` | `listepersonnes.personne.numeroImmatriculation.numeroIdentification`, espaces retirés | artisan : `personne.inscriptionRM.numeroIdentificationRM` (13 sur la journée) ; `personne.nonInscrit = "N"` : aucun SIREN (74 sur la journée, surtout `collective`) |
| `siren` (plusieurs) | une valeur par personne de `listepersonnes.personne`, qui peut être une liste | 2 annonces le 2026-10-20 visent deux sociétés d'un même groupe : un événement par SIREN |
| à ne pas utiliser | `registre` | mélange l'entreprise visée et l'ancien propriétaire ou exploitant du fonds (272 ventes et immatriculations le 2026-10-20) ; contient parfois seulement le vendeur quand l'acquéreur n'est pas inscrit (10 annonces) ; vide pour les artisans |
| `nom` | `personne.denomination` (pm), `personne.prenom` + `personne.nom` (pp) | |
| `type_evenement` | `familleavis`, précisé par `jugement.nature` pour `collective` | |
| `date_evenement` | `jugement.date` pour `collective`, `acte.dateCommencementActivite` pour `creation` | absent pour `radiation` : retomber sur `dateparution` |
| `date_publication` | `dateparution` | jamais absent |
| `tribunal` | `tribunal` (premier niveau) | |
| `dirigeants` | `personne.administration` (pm), texte libre, par exemple `Gérant : DAUMIN Max Pierre Marie` | souvent absent hors `creation` ; parsing à définir en S2-02 |
| `annonce_visee` | `parutionavisprecedent` : lettre de `nomPublication` + `numeroParution` + `numeroAnnonce` | seulement pour `annulation` et `rectificatif` |

Exemple de date : la procédure collective `A202602018167` a été jugée le 2026-10-09 et publiée le 2026-10-20. Les deux dates sont à conserver.

Les 191 annulations et rectificatifs de la journée ont tous un `parutionavisprecedent` complet. Vérifié sur l'exemple de la section 7 : `{"nomPublication": "BODACC B", "numeroParution": "20260002", "numeroAnnonce": "157"}` désigne l'annonce `B20260002157`, publiée le 2026-01-06 et présente dans l'API.

## 6. Limites de débit

En-têtes lus le 2026-10-23 sur `/records` et `/exports/jsonl` :

| En-tête | Valeur |
| --- | --- |
| `x-ratelimit-limit` | 5 000 000 appels par jour |
| `x-ratelimit-reset` | minuit UTC |
| `content-encoding` | gzip |
| `cache-control` | `public, max-age=60` |

- Le quota est partagé par toute l'instance. `x-ratelimit-remaining` a baissé de 2 523 en 69 secondes pour un seul appel de notre part.
- Les en-têtes `X-RateLimit-dataset-*` sont annoncés mais absents : pas de quota propre au dataset.
- Coût d'une journée : 1 appel avec l'export, 325 avec le keyset.
- Gestion du HTTP 429 : quelques nouvelles tentatives avec délai croissant, puis échec propre. Le quota repart à minuit UTC, inutile d'insister au-delà.
- Envoyer un `User-Agent` explicite qui identifie le projet.
- `curl` a besoin de `--compressed`. `httpx` décompresse automatiquement.

## 7. Exemples réels

Annonces brutes de la journée du 2026-10-20, telles que renvoyées par l'export. Les champs `null` sont omis. Deux adresses sont tronquées au code postal et à la ville : celle de la personne physique, et celle de la SCI, probablement le domicile de son gérant.

### Création, personne physique

```json
{
  "id": "A2026020111",
  "publicationavis": "A",
  "parution": "20260201",
  "dateparution": "2026-10-20",
  "numeroannonce": 11,
  "typeavis": "annonce",
  "typeavis_lib": "Avis initial",
  "familleavis": "creation",
  "familleavis_lib": "Créations",
  "numerodepartement": "01",
  "departement_nom_officiel": "Ain",
  "region_code": 84,
  "region_nom_officiel": "Auvergne-Rhône-Alpes",
  "tribunal": "Greffe du Tribunal de Commerce de Bourg-en-Bresse",
  "commercant": "BEN SDIRA, MOHAMED",
  "ville": "Lagnieu",
  "registre": ["483609327", "483 609 327"],
  "cp": "01150",
  "pdf_parution_subfolder": 0,
  "ispdf_unitaire": "oui",
  "listepersonnes": "{\"personne\": {\"typePersonne\": \"pp\", \"numeroImmatriculation\": {\"numeroIdentification\": \"483 609 327\", \"codeRCS\": \"RCS\", \"nomGreffeImmat\": \"Bourg-en-Bresse\"}, \"nom\": \"BEN SDIRA\", \"prenom\": \"MOHAMED\", \"nomUsage\": \"BEN SDIRA\", \"nomCommercial\": \"BENS CONNECT\"}}",
  "listeetablissements": "{\"etablissement\": {\"activite\": \"Apport d'affaires et intermédiation commerciale : mise en relation d'entreprises du bâtiment, de l'enseigne et de la signalétique avec leurs clients ; assistance à la réponse aux appels d'offres.\", \"adresse\": {\"codePostal\": \"01150\", \"ville\": \"Lagnieu\"}}}",
  "acte": "{\"dateCommencementActivite\": \"2026-10-09\", \"creation\": {\"categorieCreation\": \"Immatriculation d'une personne physique suite à création d'un établissement principal\"}}",
  "url_complete": "https://www.bodacc.fr/pages/annonces-commerciales-detail/?q.id=id:A2026020111"
}
```

### Création, personne morale

```json
{
  "id": "A2026020184",
  "publicationavis": "A",
  "parution": "20260201",
  "dateparution": "2026-10-20",
  "numeroannonce": 84,
  "typeavis": "annonce",
  "typeavis_lib": "Avis initial",
  "familleavis": "creation",
  "familleavis_lib": "Créations",
  "numerodepartement": "01",
  "departement_nom_officiel": "Ain",
  "region_code": 84,
  "region_nom_officiel": "Auvergne-Rhône-Alpes",
  "tribunal": "Greffe du Tribunal de Commerce de Bourg-en-Bresse",
  "commercant": "NAILIL",
  "ville": "Leyssard",
  "registre": ["131152613", "131 152 613"],
  "cp": "01450",
  "pdf_parution_subfolder": 0,
  "ispdf_unitaire": "oui",
  "listepersonnes": "{\"personne\": {\"typePersonne\": \"pm\", \"numeroImmatriculation\": {\"numeroIdentification\": \"131 152 613\", \"codeRCS\": \"RCS\", \"nomGreffeImmat\": \"Bourg-en-Bresse\"}, \"denomination\": \"NAILIL\", \"nomCommercial\": \"NAILIL\", \"formeJuridique\": \"Société Civile Immobilière\", \"capital\": {\"montantCapital\": \"1000.00\", \"devise\": \"EUR\"}, \"administration\": \"Gérant : DAUMIN Max Pierre Marie nom d'usage : DAUMIN\", \"adresseSiegeSocial\": {\"codePostal\": \"01450\", \"ville\": \"Leyssard\"}}}",
  "listeetablissements": "{\"etablissement\": {\"activite\": \"Acquisition, administration, exploitation, location biens immobiliers\"}}",
  "acte": "{\"dateCommencementActivite\": \"2026-10-02\", \"creation\": {\"categorieCreation\": \"Immatriculation d'une personne morale (B, C, D) suite à création d'un établissement principal\"}}",
  "url_complete": "https://www.bodacc.fr/pages/annonces-commerciales-detail/?q.id=id:A2026020184"
}
```

### Procédure collective

```json
{
  "id": "A202602018167",
  "publicationavis": "A",
  "parution": "20260201",
  "dateparution": "2026-10-20",
  "numeroannonce": 8167,
  "typeavis": "annonce",
  "typeavis_lib": "Avis initial",
  "familleavis": "collective",
  "familleavis_lib": "Procédures collectives",
  "numerodepartement": "59",
  "departement_nom_officiel": "Nord",
  "region_code": 32,
  "region_nom_officiel": "Hauts-de-France",
  "tribunal": "Greffe du Tribunal de Commerce de Douai",
  "commercant": "JIM'HYDRO ENGINEERING PERF",
  "ville": "Tilloy-lez-Cambrai",
  "registre": ["919917435", "919 917 435"],
  "cp": "59554",
  "pdf_parution_subfolder": 4,
  "ispdf_unitaire": "oui",
  "listepersonnes": "{\"personne\": {\"typePersonne\": \"pm\", \"numeroImmatriculation\": {\"numeroIdentification\": \"919 917 435\", \"codeRCS\": \"RCS\", \"nomGreffeImmat\": \"Douai\"}, \"denomination\": \"JIM'HYDRO ENGINEERING PERF\", \"activite\": \"Entretien et réparation de véhicules automobiles légers\", \"formeJuridique\": \"Société à responsabilité limitée\", \"adresseSiegeSocial\": {\"complGeographique\": \"9 Quartier de la Fontaine\", \"codePostal\": \"59554\", \"ville\": \"Tilloy-lez-Cambrai\"}}}",
  "jugement": "{\"type\": \"initial\", \"famille\": \"Avis de dépôt\", \"nature\": \"Dépôt de l'état des créances\", \"date\": \"2026-10-09\", \"complementJugement\": \"L'état des créances est déposé au greffe où tout intéressé peut présenter réclamation devant le juge-commissaire dans le délai d'un mois à compter de la présente publication.\"}",
  "url_complete": "https://www.bodacc.fr/pages/annonces-commerciales-detail/?q.id=id:A202602018167"
}
```

### Radiation

```json
{
  "id": "B20260201186",
  "publicationavis": "B",
  "parution": "20260201",
  "dateparution": "2026-10-20",
  "numeroannonce": 186,
  "typeavis": "annonce",
  "typeavis_lib": "Avis initial",
  "familleavis": "radiation",
  "familleavis_lib": "Radiations",
  "numerodepartement": "04",
  "departement_nom_officiel": "Alpes-de-Haute-Provence",
  "region_code": 93,
  "region_nom_officiel": "Provence-Alpes-Côte d'Azur",
  "tribunal": "Greffe du Tribunal de Commerce de Manosque",
  "commercant": "APES BIO CONCEPT",
  "ville": "Mallemoisson",
  "registre": ["879770428", "879 770 428"],
  "cp": "04510",
  "pdf_parution_subfolder": 0,
  "ispdf_unitaire": "oui",
  "listepersonnes": "{\"personne\": {\"typePersonne\": \"pm\", \"numeroImmatriculation\": {\"numeroIdentification\": \"879 770 428\", \"codeRCS\": \"RCS\", \"nomGreffeImmat\": \"Manosque\"}, \"denomination\": \"APES BIO CONCEPT\", \"formeJuridique\": \"Société par actions simplifiée\", \"capital\": {\"montantCapital\": \"1000.00\", \"devise\": \"EUR\"}, \"adresseSiegeSocial\": {\"numeroVoie\": \"1944\", \"nomVoie\": \"la Cornerie\", \"codePostal\": \"04510\", \"ville\": \"Mallemoisson\"}}}",
  "radiationaurcs": "{\"commentaire\": \"Radiation suite à clôture des opérations de liquidation\"}",
  "url_complete": "https://www.bodacc.fr/pages/annonces-commerciales-detail/?q.id=id:B20260201186"
}
```

### Annulation d'une annonce antérieure

```json
{
  "id": "B20260201284",
  "publicationavis": "B",
  "parution": "20260201",
  "dateparution": "2026-10-20",
  "numeroannonce": 284,
  "typeavis": "annulation",
  "typeavis_lib": "Avis d’annulation",
  "familleavis": "radiation",
  "familleavis_lib": "Radiations",
  "numerodepartement": "04",
  "departement_nom_officiel": "Alpes-de-Haute-Provence",
  "region_code": 93,
  "region_nom_officiel": "Provence-Alpes-Côte d'Azur",
  "tribunal": "Greffe du Tribunal de Commerce de Manosque",
  "commercant": "SCI SIROLANE II",
  "registre": ["451174338", "451 174 338"],
  "pdf_parution_subfolder": 0,
  "ispdf_unitaire": "oui",
  "listepersonnes": "{\"personne\": {\"typePersonne\": \"pm\", \"numeroImmatriculation\": {\"numeroIdentification\": \"451 174 338\", \"codeRCS\": \"RCS\", \"nomGreffeImmat\": \"Manosque\"}, \"denomination\": \"SCI SIROLANE II\"}}",
  "parutionavisprecedent": "{\"nomPublication\": \"BODACC B\", \"numeroParution\": \"20260002\", \"dateParution\": \"2026-01-06\", \"numeroAnnonce\": \"157\"}",
  "url_complete": "https://www.bodacc.fr/pages/annonces-commerciales-detail/?q.id=id:B20260201284"
}
```

## 8. Questions ouvertes

- **Clé d'upsert du MERGE (S2-05).** `id` est unique et stable : bonne clé naturelle. Une `annulation` doit marquer ou supprimer l'annonce `annonce_visee`. Un `rectificatif` doit la remplacer. Reste à choisir entre suppression physique et marquage, et à gérer une annulation qui arrive avant l'annonce visée, par exemple en cas de rattrapage historique.
- **Annonces sans SIREN.** 74 `nonInscrit` par jour ne peuvent pas être reliées à une entreprise. Les garder avec un SIREN nul ou les écarter ?
- **Familles à décider.** `modification`, `immatriculation` et `conciliation` sont-elles dans le périmètre ?
- **Dirigeants.** `administration` est un texte libre. Le format est-il assez régulier pour être découpé en S2-02 ?
- **Jours sans parution.** Confirmer le calendrier de parution pour distinguer une journée vide normale d'une panne de la source.
- **Fuseau horaire.** `dateparution` est une date sans heure, `data_processed` un horodatage UTC. Toute comparaison de « J-1 » se fait en UTC.
