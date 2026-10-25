# Livrable de fin de semaine 1

Preuve que l'ingestion BODACC tourne : partitions du bucket raw et invocations de la Lambda. Généré par commande
(lecture seule sur AWS), jamais par capture de la console, qui afficherait le numéro de compte.

| Fichier | Contenu |
|---|---|
| `partitions-raw.txt` | une ligne par dossier `date=` du bucket raw : `count`, `gz_bytes`, `fetched_at` lus dans son `_MANIFEST.json` |
| `invocations.json` | définition du graphe CloudWatch (même format qu'un widget de tableau de bord) |
| `invocations.png` | le graphe rendu par `aws cloudwatch get-metric-widget-image` |
| `generer.sh` | regénère les deux sorties ; masque tout nombre à 12 chiffres avant écriture |

```bash
bash docs/livrables/s1/generer.sh          # PROFILE=data-platform par défaut
grep -rE '[0-9]{12}' docs/livrables/s1/    # doit ne rien renvoyer
```

Lecture du 2026-10-25 : 20 partitions (1er au 20 octobre), 0 annonce les samedis et lundis (bulletins jumelés,
voir `docs/source-bodacc.md` §4). Sur le graphe : ingestion et rejeu du 20 (vers 14:00 et 14:30, heure de Paris), rejeu du 1er
au 19 octobre (pic de 19 invocations vers 17:30), erreurs volontaires du test de l'alarme (S1-08, étape 7).
