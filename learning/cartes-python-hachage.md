---
title: "Cartes · Hachage Python"
type: cartes
langage: Python
chapitre: Fichiers et formats
cours: Hachage
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Hachage Python
Python · Hachage : hashlib, empreintes, flux, choix de l'algorithme (format spec v4 de revision-pwa).

## 1. sha256 : l'empreinte d'octets
- Id : hachage-sha256-empreinte
- Sous-thème : empreinte
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Mots-clés : empreinte, manifest, bytes
- Source : data-platform · S1-07
- Définition : `hashlib.sha256(data).hexdigest()` calcule l'empreinte SHA-256 de `bytes` : 64 caractères hexadécimaux (≈ `crypto.createHash("sha256")` en Node).
- Contexte : Même entrée, même empreinte, sur toute machine et toute version : c'est ce qui en fait l'identité d'un contenu (manifest, cache, détection de changement). Un octet de différence change toute l'empreinte. L'objet renvoyé par `sha256()` est un calculateur, pas une valeur : on compare les `hexdigest()`, jamais les objets eux-mêmes.
- Usage : ✅ identité d'une partition, clé de cache, vérification d'intégrité · ❌ mot de passe (lent exprès : `hashlib.scrypt`, bcrypt) ou pseudonymisation (HMAC à clé).

```python
# Exemple 1 : une empreinte
import hashlib
h = hashlib.sha256(b"A1\n").hexdigest()
len(h)       # → 64
h[:8]        # → "4fc93a7e"
```

```python
# Exemple 2 : un octet change tout
import hashlib

a = hashlib.sha256(b"A1\n").hexdigest()
b = hashlib.sha256(b"A2\n").hexdigest()
sum(x == y for x, y in zip(a, b)) < 16
# → True
```

- Quiz : Que vaut `hashlib.sha256(b"a") == hashlib.sha256(b"a")` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : ce sont deux objets de calcul, comparés par identité ; comparer `.hexdigest()` ou `.digest()`.

## 2. hashlib : des bytes, pas une str
- Id : hachage-bytes-pas-str
- Sous-thème : empreinte
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Prérequis : hachage-sha256-empreinte
- Voir aussi : compression-bytes-pas-str
- Mots-clés : bytes, UTF-8, encodage
- Source : data-platform · S1-07
- Définition : `hashlib` ne hache que des octets : une `str` doit être encodée (`.encode("utf-8")`), sinon `TypeError: Strings must be encoded`.
- Contexte : Node accepte une chaîne dans `hash.update` et l'encode en UTF-8 en silence ; Python refuse, parce qu'une même chaîne donne d'autres octets selon l'encodage. Fixer l'encodage (`utf-8`) partout où l'on hache : sinon « Créteil » n'a pas la même empreinte sur deux systèmes. `bytes`, `bytearray` et `memoryview` sont acceptés.
- Usage : ✅ `json.dumps(...).encode("utf-8")` avant de hacher, encodage écrit en toutes lettres · ❌ hacher `str(obj)` ou `repr` : la représentation Python n'est pas un format stable.

```python
# Exemple 1 : encoder d'abord
import hashlib
s = '{"tribunal":"Créteil"}'
hashlib.sha256(s.encode()).hexdigest()[:8]
# → "9f87f10a"
hashlib.sha256(s)  # ❌ TypeError
```

```python
# Exemple 2 : deux encodages, deux hash
import hashlib

u = hashlib.sha256("é".encode("utf-8"))
l = hashlib.sha256("é".encode("latin-1"))
u.hexdigest() == l.hexdigest()   # → False
```

- Quiz : Que fait `hashlib.sha256(bytearray(b"A1"))` ?
- [x] Calcule l'empreinte de `b"A1"`
- [ ] `TypeError` : `bytes` attendu
- [ ] Calcule l'empreinte de `"bytearray(b'A1')"`
- Réponse : Calcule l'empreinte de `b"A1"` : tout objet bytes-like est accepté ; seule une `str` est refusée.

## 3. update : hacher par morceaux
- Id : hachage-update-par-morceaux
- Sous-thème : flux
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Prérequis : hachage-sha256-empreinte
- Voir aussi : hachage-concatenation-frontieres
- Mots-clés : sha256, BODACC
- Source : data-platform · S1-07
- Définition : `h.update(b)` ajoute des octets au calcul ; plusieurs `update` donnent la même empreinte qu'un seul appel sur la concaténation.
- Contexte : C'est ce qui permet de hacher une journée sans la garder en mémoire : le writer appelle `digest.update(line)` à chaque ligne écrite, puis `hexdigest()` à la fin. Contrairement à Node, `update` renvoie `None` : pas de chaînage `h.update(a).update(b)`, ni de `sha256().update(x).hexdigest()` sur une ligne.
- Usage : ✅ fichier ou flux lu par morceaux, hash calculé pendant l'écriture · ❌ accumuler les lignes dans une liste pour hacher `b"".join(...)` à la fin.

```python
# Exemple 1 : morceaux ou bloc, même hash
import hashlib
h = hashlib.sha256()
h.update(b"A1\n")
h.update(b"A2\n")
h.digest() == hashlib.sha256(b"A1\nA2\n").digest()  # → True
```

```python
# Exemple 2 : pendant un flux
import hashlib

def lignes():
    for i in range(3):
        yield f"A{i}\n".encode()

h = hashlib.sha256()
n = 0
for ligne in lignes():
    h.update(ligne)
    n += 1
n, len(h.hexdigest())   # → (3, 64)
```

- Quiz : Que vaut `hashlib.sha256().update(b"A1")` ?
- [ ] L'objet hash, pour chaîner
- [x] `None`
- [ ] L'empreinte de `b"A1"`
- [ ] `TypeError`
- Réponse : `None` : `update` modifie l'objet en place et ne renvoie rien ; en Node, `update` renvoie le hash et se chaîne.

## 4. b"" : l'empreinte du vide
- Id : hachage-empreinte-du-vide
- Sous-thème : empreinte
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Mots-clés : sha256, manifest, partition, JSONL
- Source : data-platform · S1-07
- Définition : Le contenu vide a une empreinte connue, `e3b0c442…b855` : un fichier vide ou une journée sans annonce ont donc un hash valide, toujours le même.
- Contexte : Le writer BODACC hache le JSONL au fil des lignes : un samedi, aucune ligne n'est écrite et le hash vaut celui de `b""`. C'est utile en contrôle : `sha256 == e3b0c442…` dans un manifest signale une partition vide, à distinguer d'une partition absente. Tout outil le connaît (`sha256sum /dev/null`, ETag de checksum S3 d'un objet vide).
- Usage : ✅ reconnaître une partition vide dans un manifest, tester le cas « journée vide » · ❌ prendre un hash comme preuve de contenu : le vide aussi a une empreinte.

```python
# Exemple 1 : rien haché, hash connu
import hashlib
h = hashlib.sha256()          # aucun update
h.hexdigest()[:8]             # → "e3b0c442"
h.hexdigest() == hashlib.sha256(b"").hexdigest()
# → True
```

```bash
# Exemple 2 : le même en terminal
printf '' | shasum -a 256
# e3b0c44298fc1c149afbf4c8996fb924
# 27ae41e4649b934ca495991b7852b855  -
```

- Quiz : Que vaut `hashlib.sha256(b"\n").hexdigest() == hashlib.sha256(b"").hexdigest()` ?
- [ ] `True` : un saut de ligne est vide
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : `b"\n"` est un octet (0x0A) ; seule l'absence totale d'octets donne `e3b0c442…`.

## 5. hexdigest ou digest : texte ou octets
- Id : hachage-hexdigest-ou-digest
- Sous-thème : format
- Type : comparaison
- Niveau : 1
- Profils : débutant, data
- Prérequis : hachage-sha256-empreinte
- Voir aussi : hachage-base64-ou-hex-s3
- Mots-clés : bytes, hexadécimal, base64, HMAC
- Source : data-platform · S1-07
- Définition : `digest()` rend l'empreinte brute en `bytes` (32 octets pour SHA-256), `hexdigest()` la même en texte hexadécimal (64 caractères).
- Contexte : `hexdigest()` sert partout où l'on écrit l'empreinte en texte : manifest JSON, log, nom de fichier. `digest()` sert à la combiner avec d'autres octets (HMAC, base64 pour S3). Les deux se convertissent : `bytes.fromhex(hex)` et `d.hex()`. Lire l'un ou l'autre ne termine pas le calcul : on peut encore appeler `update`.
- Usage : ✅ `hexdigest()` dans un manifest ou un log, `digest()` pour du base64 ou une comparaison binaire · ❌ écrire `digest()` dans du JSON : `bytes` n'est pas sérialisable.

```python
# Exemple 1 : deux formes, une empreinte
import hashlib
h = hashlib.sha256(b"A1\n")
len(h.digest()), len(h.hexdigest())  # → (32, 64)
h.digest().hex() == h.hexdigest()    # → True
```

```python
# Exemple 2 : continuer après lecture
import hashlib

h = hashlib.sha256(b"A1\n")
avant = h.hexdigest()
h.update(b"A2\n")
h.hexdigest() == hashlib.sha256(b"A1\nA2\n").hexdigest()
# → True
```

- Quiz : Que vaut `type(hashlib.sha256(b"A1").digest()).__name__` ?
- [ ] `"str"`
- [x] `"bytes"`
- [ ] `"int"`
- [ ] `"bytearray"`
- Réponse : `"bytes"` : `digest()` rend les 32 octets bruts ; seul `hexdigest()` rend une `str`.

## 6. hash() : pas une empreinte
- Id : hachage-hash-builtin-instable
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : data
- Prérequis : hachage-sha256-empreinte
- Voir aussi : collections-hashable
- Mots-clés : hash, sha256, clé S3
- Source : data-platform · S1-07
- Définition : La fonction intégrée `hash()` sert aux dicts et aux sets ; pour les `str` et `bytes`, elle change à chaque lancement de Python.
- Contexte : Python « sale » le hash des chaînes avec une graine aléatoire par processus (`PYTHONHASHSEED`), contre les attaques par collisions de dict. `hash("A1")` est stable pendant un run, différent au run suivant et sur une autre Lambda. Il ne doit jamais être stocké, comparé entre runs ou servir à partitionner des fichiers : utiliser `hashlib`. Les petits entiers, eux, se hachent sur eux-mêmes (`hash(1) == 1`).
- Usage : ✅ `__hash__` d'une classe, clé de dict en mémoire · ❌ empreinte stockée, clé S3, répartition en buckets entre deux runs : `hashlib.sha256`.

```python
# Exemple 1 : deux processus, deux hash
import subprocess, sys
cmd = [sys.executable, "-c", "print(hash('A1'))"]
r = [subprocess.run(cmd, capture_output=True, text=True).stdout for _ in range(2)]
r[0] == r[1]          # → False
```

```python
# Exemple 2 : répartir en buckets, stable
import hashlib

def bucket(siren, n=4):
    d = hashlib.sha256(siren.encode()).digest()
    return int.from_bytes(d[:4], "big") % n

bucket("483609327") == bucket("483609327")
# → True  (même valeur à chaque run)
```

- Quiz : Que vaut `hash(42)`, dans n'importe quel processus Python ?
- [ ] Un entier aléatoire par processus
- [x] `42`
- [ ] `TypeError` : un entier ne se hache pas
- Réponse : `42` : seuls `str` et `bytes` sont salés ; un petit entier se hache sur lui-même.

## 7. copy : partager un préfixe
- Id : hachage-copy-prefixe-commun
- Sous-thème : flux
- Type : recette
- Niveau : 2
- Profils : data, expert
- Prérequis : hachage-update-par-morceaux
- Mots-clés : empreinte, référence
- Source : data-platform · S1-07
- Définition : `h.copy()` duplique l'état d'un calcul en cours : on hache une fois le préfixe commun, puis chaque copie continue avec sa propre suite.
- Contexte : Utile quand plusieurs empreintes partagent un long début (même en-tête, même journée suivie de suffixes différents) : on évite de rehacher le préfixe. La copie est indépendante : `update` sur l'une ne touche pas l'autre. `h2 = h` ne copie rien, c'est le même objet (comme en JS).
- Usage : ✅ plusieurs empreintes avec un préfixe commun coûteux · ❌ `h2 = h` pour « sauvegarder » un état : les deux noms désignent le même calcul.

```python
# Exemple 1 : un préfixe, deux suites
import hashlib
base = hashlib.sha256(b"dt=2026-10-20/")
a = base.copy(); a.update(b"part-0001")
a.digest() == hashlib.sha256(b"dt=2026-10-20/part-0001").digest()  # → True
```

```python
# Exemple 2 : l'original ne bouge pas
import hashlib

base = hashlib.sha256(b"A1\n")
avant = base.hexdigest()
c = base.copy()
c.update(b"A2\n")
base.hexdigest() == avant   # → True
```

- Quiz : Avec `h2 = h` puis `h2.update(b"x")`, que vaut `h.hexdigest()` ?
- [ ] L'empreinte d'avant `update`
- [x] L'empreinte avec `b"x"` ajouté
- [ ] `ValueError` : objet partagé
- Réponse : L'empreinte avec `b"x"` ajouté : `h2 = h` ne copie pas, les deux noms désignent le même objet ; il fallait `h.copy()`.

## 8. hashlib.new : choisir l'algorithme par son nom
- Id : hachage-new-par-nom
- Sous-thème : algorithmes
- Type : recette
- Niveau : 2
- Profils : data
- Mots-clés : OpenSSL, manifest
- Source : data-platform · S1-07
- Définition : `hashlib.new("sha256", data)` crée un hash à partir du nom de l'algorithme ; `hashlib.algorithms_guaranteed` liste ceux présents partout.
- Contexte : Pratique quand l'algorithme vient d'une configuration ou d'un manifest (`"algo": "sha256"`). Un nom inconnu lève `ValueError: unsupported hash type`. `algorithms_available` dépend de l'OpenSSL de la machine, `algorithms_guaranteed` non : s'en tenir à ce dernier pour un code qui tourne en Lambda et sur un Mac.
- Usage : ✅ algorithme lu dans une config, vérification d'un manifest qui nomme son algo · ❌ code qui n'utilise qu'un algorithme : `hashlib.sha256(...)` direct, plus lisible.

```python
# Exemple 1 : par le nom
import hashlib
algo = "sha256"               # lu du manifest
h = hashlib.new(algo, b"A1\n")
h.name                        # → "sha256"
"sha256" in hashlib.algorithms_guaranteed  # → True
```

```python
# Exemple 2 : un nom inconnu
import hashlib

hashlib.new("sha257")  # ❌ ValueError
```

- Quiz : Que vaut `hashlib.new("SHA256", b"A1").name` ?
- [ ] `ValueError` : nom inconnu
- [x] `"sha256"`
- [ ] `"SHA256"`
- Réponse : `"sha256"` : `new` accepte le nom sans tenir compte de la casse et `name` le rend toujours en minuscules.

## 9. file_digest : hacher un fichier
- Id : hachage-file-digest
- Sous-thème : flux
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : hachage-update-par-morceaux
- Mots-clés : empreinte, bytes
- Source : data-platform · S1-07
- Définition : `hashlib.file_digest(f, "sha256")` (Python 3.11+) hache un fichier ouvert en binaire par morceaux, sans le charger en mémoire.
- Contexte : Avant 3.11, on lisait par blocs : `for b in iter(lambda: f.read(65536), b""): h.update(b)`. `file_digest` fait la même chose, plus vite (il peut éviter des copies). Le fichier doit être ouvert en `"rb"` : un fichier texte lève une erreur. Pour un `.gz`, on hache le `.gz` (intégrité du transfert), pas son contenu : pour l'identité de la donnée, hacher le brut à l'écriture.
- Usage : ✅ vérifier un fichier téléchargé ou avant envoi S3 · ❌ `hashlib.sha256(p.read_bytes())` sur un fichier de taille non bornée.

```python
# Exemple 1 : sans tout charger
import hashlib, io
f = io.BytesIO(b"A1\n" * 100_000)
h = hashlib.file_digest(f, "sha256")
h.hexdigest() == hashlib.sha256(b"A1\n" * 100_000).hexdigest()
# → True
```

```python
# Exemple 2 : la version par blocs
import hashlib, io

f = io.BytesIO(b"A1\n" * 100_000)
h = hashlib.sha256()
for bloc in iter(lambda: f.read(65536), b""):
    h.update(bloc)
h.hexdigest()[:8] == hashlib.sha256(b"A1\n" * 100_000).hexdigest()[:8]
# → True
```

- Quiz : Que fait `hashlib.file_digest(open(p), "sha256")` (fichier ouvert en texte) ?
- [ ] Hache le texte encodé en UTF-8
- [x] Lève une erreur : binaire attendu
- [ ] Hache le texte en latin-1
- Réponse : Lève une erreur : binaire attendu : `file_digest` lit des octets ; un fichier texte rend des `str` (`ValueError` mesuré).

## 10. md5 et sha1 : intégrité, pas sécurité
- Id : hachage-md5-sha1-integrite
- Sous-thème : sécurité
- Type : choisir
- Niveau : 2
- Profils : data, ops
- Mots-clés : collision, ETag, FIPS
- Source : data-platform · S1-07
- Définition : MD5 et SHA-1 sont cassés pour la sécurité (collisions fabriquées) mais restent utilisés pour vérifier qu'un fichier n'a pas été abîmé (ETag S3).
- Contexte : Un attaquant sait fabriquer deux fichiers de même MD5 ; un disque ou un réseau qui corrompt des octets, non. D'où MD5 encore présent dans l'ETag S3 (envoi simple) et `Content-MD5`. Sur un système en mode FIPS, `hashlib.md5()` est refusé sauf `usedforsecurity=False`, qui documente l'intention. Pour une identité de donnée, préférer SHA-256.
- Usage : ✅ comparer à un ETag S3, somme de contrôle d'un vieux format · ❌ signature, identifiant d'un contenu fourni par un tiers, mot de passe.

```python
# Exemple 1 : md5 pour l'intégrité
import hashlib
h = hashlib.md5(b"A1\n", usedforsecurity=False)
len(h.hexdigest())    # → 32
h.name                # → "md5"
```

```python
# Exemple 2 : tailles d'empreinte
import hashlib

{a: hashlib.new(a).digest_size
 for a in ("md5", "sha1", "sha256")}
# → {"md5": 16, "sha1": 20, "sha256": 32}
```

- Quiz : Quel est l'ETag S3 d'un objet envoyé en un seul `PutObject`, sans chiffrement KMS ?
- [ ] Le sha256 du contenu
- [x] Le md5 du contenu, en hexadécimal
- [ ] Un identifiant aléatoire
- [ ] Le md5 du nom de la clé
- Réponse : Le md5 du contenu, en hexadécimal : pour un envoi simple sans SSE-KMS ; en multipart ou avec KMS, l'ETag n'est plus un md5 du contenu.

## 11. empreinte tronquée : le risque de collision
- Id : hachage-troncature-collision
- Sous-thème : empreinte
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : hachage-hexdigest-ou-digest
- Mots-clés : collision, hexadécimal, empreinte
- Source : data-platform · S1-07
- Définition : Garder 8 caractères hexadécimaux d'une empreinte, c'est 32 bits : les collisions deviennent probables dès quelques dizaines de milliers d'éléments.
- Contexte : Paradoxe des anniversaires : avec n bits, on a une chance sur deux de collision vers 1,18 × 2^(n/2) éléments. 8 hex = 32 bits → environ 77 000 ; 16 hex = 64 bits → 5 milliards. Tronquer suffit pour l'afficher dans un log ou comparer deux fichiers connus ; pour identifier chaque annonce d'un historique (des millions), garder au moins 16 hex, ou l'empreinte entière.
- Usage : ✅ préfixe de 8 à 12 hex dans un log ou un nom lisible · ❌ préfixe court comme clé unique d'une table de plusieurs millions de lignes.

```python
# Exemple 1 : le seuil de 50 %
import math
seuil = lambda bits: math.sqrt(2 * math.log(2) * 2**bits)
round(seuil(32))      # → 77163
seuil(64) > 5e9       # → True
```

```python
# Exemple 2 : provoquer une collision
import hashlib

vus = {}
for i in range(5000):
    p = hashlib.sha256(str(i).encode()).hexdigest()[:4]
    if p in vus:
        break
    vus[p] = i
i < 5000              # → True  (16 bits)
```

- Quiz : 100 000 annonces identifiées par les 8 premiers hex de leur sha256 : une collision est…
- [ ] Impossible : sha256 n'a pas de collision
- [ ] Très peu probable (1 sur 1 million)
- [x] Plus probable qu'improbable
- Réponse : Plus probable qu'improbable : 100 000 dépasse le seuil de 50 % (≈ 77 000) pour 32 bits.

## 12. concaténation : séparer les morceaux
- Id : hachage-concatenation-frontieres
- Sous-thème : flux
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : hachage-update-par-morceaux
- Mots-clés : empreinte, sérialisation, JSONL
- Source : data-platform · S1-07
- Définition : Hacher des morceaux à la suite ne garde pas leurs frontières : `["A1", "2"]` et `["A", "12"]` donnent la même empreinte sans séparateur.
- Contexte : `update` concatène : l'empreinte ne voit qu'un flux d'octets. Pour hacher une liste de champs (clé composée jour + tribunal + id), il faut un encodage sans ambiguïté : un séparateur qui ne peut pas apparaître dans les valeurs (`\n` en JSONL, `\x00`), un préfixe de longueur, ou mieux une sérialisation (`json.dumps` d'une liste). Le JSONL du writer est sûr : chaque ligne finit par `\n` et JSON échappe les `\n` des valeurs.
- Usage : ✅ clé de cache sur plusieurs entrées : `json.dumps([a, b])` puis hash · ❌ `update(a); update(b)` ou `f"{a}{b}"` sans séparateur.

```python
# Exemple 1 : frontières perdues
import hashlib
def emp(*parts):
    h = hashlib.sha256()
    for p in parts: h.update(p)
    return h.hexdigest()
emp(b"A1", b"2") == emp(b"A", b"12")   # → True
```

```python
# Exemple 2 : sérialiser la liste d'abord
import hashlib, json

def emp(*parts):
    s = json.dumps(parts)
    return hashlib.sha256(s.encode()).hexdigest()

emp("A1", "2") == emp("A", "12")   # → False
```

- Quiz : Avec `"|"` comme séparateur, que vaut l'égalité des clés `"a|b" + "|" + "c"` et `"a" + "|" + "b|c"` ?
- [ ] `False` : le séparateur suffit
- [x] `True`
- [ ] `ValueError`
- Réponse : `True` : les deux font `"a|b|c"` ; un séparateur ne protège que s'il ne peut pas apparaître dans les valeurs.

## 13. blake2b : rapide, taille et clé réglables
- Id : hachage-blake2b-taille-cle
- Sous-thème : algorithmes
- Type : choisir
- Niveau : 3
- Profils : expert
- Mots-clés : MAC, HMAC, sha256
- Source : data-platform · S1-07
- Définition : `hashlib.blake2b` est plus rapide que SHA-256 en logiciel, avec une taille d'empreinte réglable (`digest_size`) et une clé intégrée (`key`) qui en fait un MAC.
- Contexte : `blake2b(data, digest_size=16)` rend une empreinte courte calculée pour cette taille, pas un sha256 tronqué. Avec `key=`, seule une personne qui a la clé reproduit l'empreinte (comme HMAC, sans construction en deux passes). Moins répandu hors Python : pour une empreinte lue par d'autres outils (S3, `sha256sum`, Athena), SHA-256 reste le choix commun.
- Usage : ✅ empreintes internes en grand nombre, pseudonymisation à clé en pur Python · ❌ empreinte à comparer avec un outil externe ou un service AWS : SHA-256.

```python
# Exemple 1 : taille au choix
import hashlib
h = hashlib.blake2b(b"A1\n", digest_size=16)
len(h.hexdigest())     # → 32
len(hashlib.blake2b(b"A1\n").hexdigest())  # → 128
```

```python
# Exemple 2 : une clé change tout
import hashlib

sans = hashlib.blake2b(b"483609327").hexdigest()
avec = hashlib.blake2b(b"483609327",
                       key=b"secret").hexdigest()
sans == avec           # → False
```

- Quiz : `blake2b(x, digest_size=32)` et `blake2b(x).digest()[:32]` : mêmes octets ?
- [ ] Oui : c'est une troncature
- [x] Non : la taille entre dans le calcul
- [ ] `ValueError` : 32 est trop court
- Réponse : Non : la taille entre dans le calcul : `digest_size` est un paramètre de l'algorithme, l'empreinte courte n'est pas un préfixe de la longue.

## 14. compare_digest : comparer sans fuite de temps
- Id : hachage-compare-digest-temps-constant
- Sous-thème : sécurité
- Type : recette
- Niveau : 3
- Profils : web, ops, expert
- Prérequis : hachage-hexdigest-ou-digest
- Mots-clés : HMAC, webhook
- Source : data-platform · S1-07
- Définition : `hmac.compare_digest(a, b)` compare deux empreintes en temps constant ; `==` s'arrête au premier caractère différent et laisse deviner le secret.
- Contexte : Pour une signature de webhook ou un jeton, un attaquant mesure le temps de réponse : plus `==` va loin avant d'échouer, plus le préfixe essayé est bon. `compare_digest` parcourt toujours tout. Il accepte deux `str` ASCII ou deux `bytes`, pas un mélange. Pour comparer deux sha256 de partitions (rien de secret), `==` suffit.
- Usage : ✅ vérifier une signature HMAC, un jeton d'API, un mot de passe haché · ❌ comparaison d'empreintes publiques (manifest, cache) : `==` est plus lisible.

```python
# Exemple 1 : vérifier une signature
import hashlib, hmac
cle = b"secret"
sig = hmac.new(cle, b"payload", hashlib.sha256).hexdigest()
recue = sig
hmac.compare_digest(sig, recue)   # → True
```

```python
# Exemple 2 : types à ne pas mélanger
import hmac

hmac.compare_digest("ab", "ab")    # → True
hmac.compare_digest(b"ab", b"ab")  # → True
hmac.compare_digest("ab", b"ab")  # ❌ TypeError
```

- Quiz : Que fait `hmac.compare_digest("é", "é")` ?
- [ ] `True`
- [ ] `False`
- [x] `TypeError`
- [ ] `UnicodeEncodeError`
- Réponse : `TypeError` (non-ASCII characters is not supported) : une `str` doit être ASCII ; comparer les `bytes` encodés ou un `hexdigest()`.

## 15. base64 ou hex : le format attendu par S3
- Id : hachage-base64-ou-hex-s3
- Sous-thème : format
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : hachage-hexdigest-ou-digest
- Voir aussi : AWS/s3-checksum-sha256
- Mots-clés : base64, hexadécimal, boto3
- Source : data-platform · S1-07
- Définition : Une même empreinte s'écrit en hexadécimal (64 caractères) ou en base64 (44) ; S3 attend `ChecksumSHA256` en base64 du `digest()`, pas le `hexdigest()`.
- Contexte : `boto3.put_object(..., ChecksumSHA256=...)` fait vérifier l'intégrité par S3 à la réception ; la valeur est `base64(digest())`. Passer le `hexdigest()` fait rejeter l'envoi (`InvalidRequest`). Base64 de l'hexadécimal est l'autre erreur courante : 88 caractères, faux aussi. Les deux formes se convertissent sans recalcul.
- Usage : ✅ base64 pour les en-têtes et API AWS (`x-amz-checksum-sha256`), hex pour manifest et logs · ❌ réutiliser le `hexdigest()` du manifest tel quel dans un en-tête de checksum S3.

```python
# Exemple 1 : deux écritures d'une empreinte
import base64, hashlib
d = hashlib.sha256(b"A1\n").digest()
len(d.hex())                         # → 64
len(base64.b64encode(d))             # → 44
```

```python
# Exemple 2 : passer de l'une à l'autre
import base64, hashlib

h = hashlib.sha256(b"A1\n")
b64 = base64.b64encode(h.digest()).decode()
base64.b64decode(b64).hex() == h.hexdigest()
# → True
```

- Quiz : Que vaut `len(base64.b64encode(h.hexdigest().encode()))` pour un sha256 ?
- [ ] `44`
- [ ] `64`
- [x] `88`
- [ ] `32`
- Réponse : `88` : c'est le base64 des 64 caractères hexadécimaux, pas des 32 octets ; S3 attend le base64 du `digest()` (44).
