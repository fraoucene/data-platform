---
title: "Cartes · Formats de fichiers"
type: cartes
langage: Data engineering
cours: Formats de fichiers
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Formats de fichiers
Data engineering · Formats de fichiers : formats (format spec v3 de revision-pwa).

## 1. JSON Lines : un objet par ligne
- Sous-thème : formats
- Niveau : 1
- Définition : JSON Lines (NDJSON) écrit un objet JSON par ligne, ce qui permet de lire et d'écrire en flux sans tout charger.
- Contexte : Un tableau JSON doit être lu en entier avant d'avoir le premier élément ; une journée BODACC pèse ~59 Mo. En JSON Lines, chaque ligne est un document autonome : on lit, valide et écrit ligne à ligne, et une ligne corrompue n'empêche pas de lire les autres. C'est le format de l'export `/exports/jsonl` de l'API, et Athena le lit nativement.
- Usage : ✅ gros volumes, streaming, fichiers `raw` et `processed` · ❌ petit document de config ou réponse d'API unique : JSON classique.

```python
# Exemple 1 : lire ligne par ligne
import json

ndjson = ('{"id": 1}\n'
          '{"id": 2}\n')
[json.loads(l) for l in
 ndjson.splitlines()]
# → [{"id": 1}, {"id": 2}]
```

```python
# Exemple 2 : écrire en JSON Lines
import json

docs = [{"ville": "Sète"}, {"ville": "Lyon"}]
out = "".join(
    json.dumps(d, ensure_ascii=False) + "\n"
    for d in docs)
out  # → '{"ville": "Sète"}\n{"ville": "Lyon"}\n'
```

- Quiz : Avec `ndjson` de l'exemple 1, que fait `json.loads(ndjson)` ?
- [ ] `[{"id": 1}, {"id": 2}]`
- [ ] `{"id": 1}` (la première ligne)
- [x] `JSONDecodeError`
- Réponse : `JSONDecodeError` (Extra data) : un fichier JSON Lines n'est pas un document JSON unique, il se lit ligne par ligne.

## 2. gzip : compresser le brut
- Sous-thème : formats
- Niveau : 1
- Définition : `gzip` compresse les fichiers bruts avant S3 : stockage et transfert réduits, très efficace sur du JSON répétitif.
- Contexte : Le JSON répète les mêmes clés à chaque ligne : gzip les factorise et divise souvent la taille par 5 à 10. Athena, Spark et `aws s3 cp` lisent le `.json.gz` directement, et on paie S3 et Athena au volume. Revers : un fichier gzip ne se découpe pas, un seul worker le lit en entier ; viser des fichiers de taille raisonnable.
- Usage : ✅ `raw` et `processed` en JSON Lines, archives · ❌ fichiers énormes à traiter en parallèle : découper en plusieurs parts, ou Parquet (compressé par colonne).

```python
# Exemple 1 : compresser, décompresser
import gzip, json

brut = json.dumps([{"id": 1}] * 500)
gz = gzip.compress(brut.encode())
len(brut), len(gz)  # → (5500, 64)
json.loads(gzip.decompress(gz))[0]
# → {"id": 1}
```

```python
# Exemple 2 : écrire un .jsonl.gz en texte
import gzip, os, tempfile

p = os.path.join(tempfile.mkdtemp(),
                 "part-000.jsonl.gz")
with gzip.open(p, "wt") as f:  # t = texte
    f.write('{"id": 1}\n')
with gzip.open(p, "rt") as f:
    ligne = f.readline()
ligne  # → '{"id": 1}\n'
```

- Quiz : Avec `gz` de l'exemple 1, que fait `json.loads(gz)` ?
- [ ] `[{"id": 1}, …]` : `loads` décompresse
- [x] `UnicodeDecodeError`
- [ ] `TypeError` : `loads` refuse les octets
- Réponse : `UnicodeDecodeError` : `loads` accepte des octets mais les décode en UTF-8 ; des octets gzip ne le sont pas, décompresser d'abord.

## 3. Parquet : colonnaire plutôt que CSV
- Sous-thème : formats
- Niveau : 1
- Définition : Parquet stocke les données par colonne, typées et compressées, avec des statistiques : un moteur ne lit que les colonnes demandées.
- Contexte : Un CSV ou du JSON se relit en entier, toutes colonnes comprises, et tout y est texte. Parquet gagne deux fois : la compression par colonne (souvent 5 à 10 fois plus petit, valeurs semblables côte à côte) et la lecture des seules colonnes citées ; les min / max par bloc font sauter des blocs entiers. Sur un moteur facturé au scanné (Athena, 7 $ par To à Paris), c'est autant d'économie. Revers : binaire, illisible.
- Usage : ✅ zone `processed` interrogée par Athena ou Spark · ❌ export destiné à un humain ou à Excel : CSV dans `out` ; `raw` : garder le format de la source, pour rejouer à l'identique.

```python
# Exemple 1 : lignes ou colonnes
lignes = [
    {"siren": "483609327", "ville": "Lyon"},
    {"siren": "552100554", "ville": "Sète"},
]
# Parquet range par colonne
cols = {k: [l[k] for l in lignes]
        for k in lignes[0]}
cols["ville"]  # → ["Lyon", "Sète"]
# lire ville = 1 colonne sur 2
```

```python
# Exemple 2 : même requête, 2 formats
prix_to = 7          # $ / To (Athena)
csv_go = 100         # table en CSV
parquet_go = 15      # même table
part_col = 2 / 20    # 2 colonnes / 20

csv = csv_go / 1000 * prix_to
pq = (parquet_go * part_col
      / 1000 * prix_to)
round(csv, 3), round(pq, 4)
# → (0.7, 0.0105)
round(csv / pq)      # → 67  (fois moins)
```

- Quiz : Même table qu'à l'exemple 2, mais la requête fait `SELECT *` sur le Parquet : que devient le gain d'environ 67 fois ?
- [ ] Inchangé : Parquet est toujours lu par colonne
- [x] Environ 7 fois : la compression seule
- [ ] Nul : autant que le CSV
- [ ] Plus grand : les colonnes se compressent mieux
- Réponse : environ 7 fois (100 Go contre 15 Go) : `SELECT *` lit toutes les colonnes, il ne reste que le gain de compression ; nommer les colonnes utiles.
