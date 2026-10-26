---
title: "Cartes · Web Crypto"
type: cartes
langage: Web
chapitre: Navigateur
cours: Web Crypto
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Web Crypto
Web · Web Crypto : `crypto.subtle` (hachage, HMAC, clés), contexte sécurisé, encodage des octets (format spec v3 de revision-pwa).

## 1. crypto.subtle : une API asynchrone
- Id : web-crypto-subtle-asynchrone
- Sous-thème : subtle
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Mots-clés : aws4fetch, SigV4, SHA-256, HMAC
- Source : data-platform · pwa-sync
- Définition : `crypto.subtle` est la cryptographie native du navigateur (SHA-256, HMAC, AES, signatures) ; chaque opération renvoie une `Promise`, jamais une valeur directe.
- Contexte : Pas de dépendance à embarquer : c'est ce qui permet à `aws4fetch` de signer SigV4 en quelques Ko, là où une implémentation JS du SHA-256 pèserait plus. Différence avec Python, où `hashlib.sha256(b).hexdigest()` est synchrone : ici tout passe par `await`, et le résultat est un `ArrayBuffer` d'octets bruts, pas une chaîne.
- Usage : ✅ hachage, HMAC, chiffrement dans le navigateur ou Node 22 sans bibliothèque · ❌ réimplémenter SHA-256 en JS ou embarquer `crypto-js` : plus lourd et plus lent.

```js
// Exemple 1 : mesuré, Node 22
const octets = new TextEncoder().encode('abc')
const h = await crypto.subtle.digest(
  'SHA-256', octets)
h.constructor.name  // → 'ArrayBuffer'
h.byteLength        // → 32
```

```python
# Exemple 2 : le même hachage en Python
import hashlib
hashlib.sha256(b"abc").hexdigest()[:16]
# → 'ba7816bf8f01cfea'
```

- Quiz : `const h = crypto.subtle.digest('SHA-256', octets)` sans `await` : que vaut `h` ?
- [ ] Un `ArrayBuffer` de 32 octets
- [x] Une `Promise`
- [ ] `undefined`
- [ ] Une chaîne hexadécimale
- Réponse : une `Promise` (mesuré : `h instanceof Promise` → `true`) : toutes les opérations de `subtle` sont asynchrones ; l'oubli d'`await` passe le typage si `h` n'est pas annoté.

## 2. TextEncoder : une chaîne devient des octets
- Id : web-crypto-textencoder-octets
- Sous-thème : encodage
- Type : recette
- Niveau : 1
- Profils : débutant, web
- Voir aussi : web-crypto-digest-octets-pas-chaine
- Mots-clés : UTF-8, vue typée
- Source : data-platform · pwa-sync
- Définition : `new TextEncoder().encode(s)` convertit une chaîne en `Uint8Array` UTF-8 : c'est l'entrée attendue par `digest`, `importKey` et `sign`.
- Contexte : `subtle` ne travaille que sur des octets ; une chaîne JS est en UTF-16, et un caractère accentué fait 2 octets en UTF-8. La longueur d'une chaîne (`s.length`) n'est donc pas sa taille en octets. Équivalent Python : `s.encode()` (UTF-8 par défaut). Sens inverse : `new TextDecoder().decode(octets)`.
- Usage : ✅ encoder clés, messages et corps avant toute opération `subtle` · ❌ passer une chaîne brute à `digest` ou compter les octets avec `.length`.

```js
// Exemple 1 : mesuré, Node 22
const enc = new TextEncoder()
enc.encode('BODACC').length  // → 6
'é'.length                   // → 1
enc.encode('é').length       // → 2 : UTF-8
```

```python
# Exemple 2 : la même chose en Python
len("é"), len("é".encode())  # → (1, 2)
```

- Quiz : Que vaut `new TextEncoder().encode('Société').length` ?
- [ ] 7
- [ ] 8
- [x] 9
- [ ] 14
- Réponse : 9 (mesuré) : 7 caractères, dont deux `é` codés sur 2 octets chacun en UTF-8 ; 14 serait de l'UTF-16.

## 3. ArrayBuffer en hexadécimal : padStart
- Id : web-crypto-hex-padstart
- Sous-thème : encodage
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Voir aussi : web-crypto-arraybuffer-vue
- Mots-clés : ArrayBuffer, SHA-256
- Source : data-platform · pwa-sync
- Définition : Un hachage arrive en `ArrayBuffer` ; on l'affiche en hexadécimal en convertissant chaque octet sur deux caractères avec `padStart(2, '0')`.
- Contexte : `b.toString(16)` donne `'5'` pour l'octet 5, pas `'05'` : sans `padStart`, la chaîne est trop courte et ne correspond plus au `hexdigest()` de Python ni aux signatures SigV4 (64 caractères). `Uint8Array.prototype.toHex()` existe dans Chromium récent (mesuré), pas dans Node 22 : la conversion manuelle reste la plus portable.
- Usage : ✅ comparer un hachage du navigateur à celui d'un manifest Python, afficher une signature · ❌ `toString(16)` sans remplissage, ou `toHex()` sans vérifier sa présence.

```js
// Exemple 1 : la conversion portable
const hex = (buf) => [...new Uint8Array(buf)]
  .map((b) => b.toString(16).padStart(2, '0'))
  .join('')
hex(new Uint8Array([5, 255]).buffer)
// → '05ff'
```

- Quiz : Sans `padStart`, que donne la conversion des octets `[5, 255]` ?
- [ ] `'05ff'`
- [x] `'5ff'`
- [ ] `'5,255'`
- [ ] `'0x50xff'`
- Réponse : `'5ff'` (mesuré) : `(5).toString(16)` vaut `'5'` ; la chaîne perd un caractère et ne se compare plus à `hexdigest()`.

## 4. contexte sécurisé : crypto.subtle absent en HTTP
- Id : web-crypto-subtle-absent-en-http
- Sous-thème : contexte sécurisé
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Voir aussi : web-crypto-issecurecontext-detecter, pwa-service-worker-contexte-securise
- Mots-clés : CloudFront
- Source : data-platform · pwa-sync
- Définition : `crypto.subtle` n'existe que dans un contexte sécurisé : page en HTTPS, ou servie depuis `localhost` / `127.0.0.1` ; sur `http://192.168.x.x`, il vaut `undefined`.
- Contexte : Le navigateur réserve les API sensibles aux pages dont l'origine est authentifiée. En développement, le Mac sert l'app en HTTP : `localhost` passe, mais l'iPhone qui ouvre `http://<IP du Mac>:5175` est hors contexte sécurisé. L'app s'affiche, puis toute signature échoue. Les clés et la synchro se testent donc sur le Mac en local, puis sur l'iPhone via l'URL HTTPS déployée.
- Usage : ✅ tester la crypto en `localhost`, puis sur l'URL HTTPS (CloudFront) · ❌ conclure qu'une signature est cassée d'après l'IP locale du téléphone.

```text
# Exemple 1 : mesuré dans Chromium (HTTP)
                 isSecureContext  subtle
localhost        true             object
127.0.0.1        true             object
192.168.10.119   false            undefined
```

- Quiz : L'iPhone ouvre `http://mon-mac.local:5175`, un nom qui désigne le Mac. Que vaut `crypto.subtle` ?
- [ ] Un objet : le nom désigne la même machine que `localhost`
- [x] `undefined` : seul `localhost` (et le bouclage) est sécurisé en HTTP
- [ ] Un objet, mais `importKey` est refusé
- Réponse : `undefined` : le contexte sécurisé dépend de l'origine de la page, pas de la machine visée ; un nom réseau en HTTP n'est pas `localhost`.

## 5. l'erreur hors contexte sécurisé : reading 'importKey'
- Id : web-crypto-erreur-reading-importkey
- Sous-thème : contexte sécurisé
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Prérequis : web-crypto-subtle-absent-en-http
- Voir aussi : web-crypto-issecurecontext-detecter
- Mots-clés : aws4fetch, contexte sécurisé
- Source : data-platform · pwa-sync
- Définition : Hors contexte sécurisé, une signature `aws4fetch` lève `TypeError: Cannot read properties of undefined (reading 'importKey')` : c'est `crypto.subtle` qui manque.
- Contexte : Le message pointe une propriété de `undefined`, pas la crypto : on cherche d'abord un bug dans la bibliothèque ou dans les clés. Le nom lu (`importKey`, `digest`, `sign`) est la première méthode appelée sur `subtle`. Le réflexe : regarder `isSecureContext` dans la console de la page, puis l'URL (HTTP sur une IP ?).
- Usage : ✅ reconnaître ce message sur tout appel `subtle` (aws4fetch, hachage, Web Push) · ❌ remplacer la bibliothèque ou ajouter un polyfill : servir la page en HTTPS ou depuis `localhost`.

```text
# Exemple 1 : mesuré dans Chromium
# page http://192.168.10.119:8765/
await crypto.subtle.importKey('raw', …)
→ TypeError: Cannot read properties of
  undefined (reading 'importKey')
isSecureContext  // → false
```

- Quiz : Même code, page `http://localhost:5175` : `importKey` d'une clé HMAC ?
- [x] Réussit : `localhost` est un contexte sécurisé
- [ ] Même `TypeError`
- [ ] Exige `https://localhost`
- [ ] Réussit, mais la clé est extractible
- Réponse : réussit (mesuré) : `localhost` et les adresses de bouclage comptent comme sécurisées même en HTTP.

## 6. isSecureContext : détecter avant d'appeler
- Id : web-crypto-issecurecontext-detecter
- Sous-thème : contexte sécurisé
- Type : recette
- Niveau : 1
- Profils : débutant, web
- Prérequis : web-crypto-subtle-absent-en-http
- Mots-clés : service worker, CloudFront
- Source : data-platform · pwa-sync
- Définition : `isSecureContext` (booléen global) dit si la page est en contexte sécurisé : le tester permet de désactiver proprement une fonction qui en dépend.
- Contexte : Plutôt que laisser une `TypeError` obscure remonter à la première synchro, l'app peut afficher « synchro indisponible (page non sécurisée) ». C'est la même logique que `if ('serviceWorker' in navigator)` pour le service worker : on teste la capacité, pas le navigateur. En production derrière CloudFront, la valeur est toujours `true`.
- Usage : ✅ message clair en développement sur IP locale, détection d'une capacité · ❌ tester `location.protocol === 'https:'` : `localhost` en HTTP est sécurisé aussi.

```js
// Exemple 1 : capacité détectée une fois
const peutSigner =
  isSecureContext && !!crypto.subtle
// localhost        → true
// 192.168.x.x HTTP → false
if (!peutSigner)
  console.warn('synchro indisponible')
```

- Quiz : Page `http://localhost:5175`. Que vaut `location.protocol === 'https:'` ?
- [ ] `true`
- [x] `false`, alors que `isSecureContext` vaut `true`
- [ ] `false`, et `isSecureContext` aussi
- [ ] `undefined`
- Réponse : `false` : le protocole est `http:`, mais `localhost` est un contexte sécurisé ; tester le protocole désactiverait la crypto à tort.

## 7. HMAC : importKey puis sign
- Id : web-crypto-hmac-importkey-sign
- Sous-thème : subtle
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : web-crypto-subtle-asynchrone, web-crypto-textencoder-octets
- Voir aussi : web-crypto-verify-temps-constant, web-crypto-cle-non-extractible
- Mots-clés : HMAC, SigV4, aws4fetch
- Source : data-platform · pwa-sync
- Définition : Un HMAC se calcule en deux temps : `importKey('raw', …, {name: 'HMAC', hash: 'SHA-256'})` crée une `CryptoKey`, puis `sign('HMAC', clé, message)`.
- Contexte : `subtle` ne prend jamais une clé en octets directement : elle passe par un objet `CryptoKey` opaque, qui déclare ses usages (`['sign']`) et s'il est exportable. C'est exactement ce que fait `aws4fetch` à chaque étape de la dérivation SigV4. En Python, `hmac.new(cle, msg, hashlib.sha256)` fait tout en un appel, de façon synchrone.
- Usage : ✅ signatures SigV4, webhooks, jetons signés côté navigateur ou Node · ❌ HMAC « maison » avec `digest(cle + message)` : vulnérable (extension de longueur).

```js
// Exemple 1 : mesuré, Node 22
const enc = new TextEncoder()
const cle = await crypto.subtle.importKey(
  'raw', enc.encode('secret'),
  { name: 'HMAC', hash: 'SHA-256' },
  false, ['sign'])
const sig = await crypto.subtle.sign(
  'HMAC', cle, enc.encode('20261025'))
hex(sig).slice(0, 16)  // → 'eef0a7042a6782d2'
```

```python
# Exemple 2 : la même valeur en Python
import hashlib, hmac
hmac.new(b"secret", b"20261025",
         hashlib.sha256).hexdigest()[:16]
# → 'eef0a7042a6782d2'
```

- Quiz : Clé importée avec `['sign']` seulement, puis `subtle.verify` avec elle : résultat ?
- [ ] `true` si la signature est bonne
- [ ] `false` dans tous les cas
- [x] Rejet `InvalidAccessError`
- [ ] Ça marche : `verify` refait un `sign`
- Réponse : `InvalidAccessError` (mesuré, Chromium : « key.usages does not permit this operation ») : une `CryptoKey` ne sert qu'aux usages déclarés à l'import.

## 8. verify : comparer en temps constant
- Id : web-crypto-verify-temps-constant
- Sous-thème : subtle
- Type : piège
- Niveau : 2
- Profils : web, ops
- Prérequis : web-crypto-hmac-importkey-sign
- Voir aussi : Python/hachage-compare-digest-temps-constant
- Mots-clés : HMAC, webhook
- Source : data-platform · pwa-sync
- Définition : Pour vérifier un HMAC, `subtle.verify('HMAC', clé, signature, message)` compare en temps constant et rend un booléen ; pas de `===` sur deux chaînes hex.
- Contexte : Un `===` s'arrête au premier caractère différent : sa durée révèle combien de caractères sont justes, ce qu'un attaquant mesure pour deviner une signature octet par octet. `verify` (JS) et `hmac.compare_digest` (Python) prennent le même temps quel que soit l'écart. Cas typique : vérifier la signature d'un webhook dans une Lambda.
- Usage : ✅ toute vérification de signature ou de jeton secret · ❌ `sigCalculee === sigRecue` ou `==` en Python.

```python
# Exemple 1 : la version Python
import hashlib, hmac
cle, msg = b"secret", b"20261025"
recue = hmac.new(cle, msg, hashlib.sha256).hexdigest()
calc = hmac.new(cle, msg, hashlib.sha256).hexdigest()
hmac.compare_digest(calc, recue)  # → True
hmac.compare_digest(calc, "0" * 64)  # → False
```

```js
// Exemple 2 : mesuré, Node 22
await crypto.subtle.verify('HMAC', cle,
  sig, enc.encode('20261025'))  // → true
await crypto.subtle.verify('HMAC', cle,
  sig, enc.encode('20261026'))  // → false
```

- Quiz : `subtle.verify` avec une mauvaise signature : que se passe-t-il ?
- [ ] Rejet `InvalidSignatureError`
- [x] Résolue à `false`
- [ ] Résolue à `null`
- [ ] `TypeError`
- Réponse : `false` (mesuré) : une signature fausse n'est pas une erreur ; seul un mauvais usage (clé sans `verify`, mauvais type) rejette.

## 9. clé non extractible : extractable à false
- Id : web-crypto-cle-non-extractible
- Sous-thème : subtle
- Type : concept
- Niveau : 2
- Profils : web
- Prérequis : web-crypto-hmac-importkey-sign
- Mots-clés : CryptoKey, XSS, aws4fetch
- Source : data-platform · pwa-sync
- Définition : Le 4e argument d'`importKey` (`extractable`) à `false` interdit de relire les octets de la clé : `exportKey` est rejeté.
- Contexte : Une `CryptoKey` non extractible peut signer sans que le code (ou un script injecté) récupère le secret : il ne voit qu'un objet opaque. Ça limite les dégâts, sans les supprimer : le script peut toujours signer à la place de l'utilisateur tant que la page est ouverte. `aws4fetch` importe ses clés intermédiaires non extractibles.
- Usage : ✅ `false` par défaut ; `true` seulement s'il faut exporter (sauvegarde, transfert) · ❌ croire qu'une clé non extractible rend un XSS inoffensif.

```js
// Exemple 1 : mesuré dans Chromium
const cle = await crypto.subtle.importKey(
  'raw', enc.encode('secret'),
  { name: 'HMAC', hash: 'SHA-256' },
  false, ['sign'])
cle.extractable  // → false
await crypto.subtle.exportKey('raw', cle)
// ❌ InvalidAccessError: key is not
//    extractable
```

- Quiz : Même import avec `extractable: true` : longueur du `exportKey('raw', …)` de la clé `'secret'` ?
- [ ] 32 : SHA-256 l'étire
- [x] 6 : les octets d'origine
- [ ] 64 : la taille de bloc
- [ ] 0 : HMAC n'exporte rien
- Réponse : 6 (mesuré, Node 22) : l'export rend les octets importés tels quels ; la clé HMAC n'est pas transformée à l'import.

## 10. Node 22 : crypto.subtle global, pas localStorage
- Id : web-crypto-node-subtle-global
- Sous-thème : subtle
- Type : concept
- Niveau : 2
- Profils : web
- Voir aussi : vite-vitest-environnement-node
- Mots-clés : crypto.subtle, Vitest, aws4fetch
- Source : data-platform · pwa-sync
- Définition : Node 22 expose `globalThis.crypto.subtle` comme le navigateur : un test Vitest en environnement `node` peut signer avec `aws4fetch` sans navigateur.
- Contexte : C'est ce que vérifie `cloud.test.ts` : l'en-tête `Authorization` signé est réellement calculé, sous Node, avec de fausses clés. En revanche, les API du DOM n'y sont pas : `localStorage`, `document`, `window` valent `undefined`. D'où l'injection du stockage dans `createCloud`, et pas celle de la crypto.
- Usage : ✅ tester une signature ou un hachage sous Node avec le même code que le navigateur · ❌ supposer que tout le global du navigateur existe sous Node (stockage, DOM).

```js
// Exemple 1 : mesuré, node v22.17
typeof crypto.subtle      // → 'object'
typeof crypto.randomUUID  // → 'function'
typeof localStorage       // → 'undefined'
```

- Quiz : Sous Node 22, que fait `window.crypto.subtle.digest('SHA-256', octets)` ?
- [ ] Le hachage, comme dans le navigateur
- [x] `ReferenceError: window is not defined`
- [ ] `TypeError` : `subtle` absent sous Node
- [ ] Une `Promise` rejetée
- Réponse : `ReferenceError` (mesuré, node v22.17) : `window` n'existe pas sous Node ; écrire `crypto.subtle` (ou `globalThis.crypto`), présent des deux côtés.

## 11. résultat ArrayBuffer : passer par une vue
- Id : web-crypto-arraybuffer-vue
- Sous-thème : encodage
- Type : piège
- Niveau : 2
- Profils : web
- Voir aussi : web-crypto-base64-spread
- Mots-clés : crypto.subtle
- Source : data-platform · pwa-sync
- Définition : `digest` et `sign` rendent un `ArrayBuffer`, zone d'octets brute non indexable : on lit les octets via une vue `new Uint8Array(buf)`.
- Contexte : `buf[0]` vaut `undefined` sans erreur : le piège ne se voit qu'à l'usage. Un `ArrayBuffer` n'a ni `map` ni `length` (mais `byteLength`). Les vues (`Uint8Array`, `DataView`) partagent sa mémoire sans copie. Côté Python, `digest()` rend directement des `bytes`, indexables (`d[0]` → un entier).
- Usage : ✅ `new Uint8Array(buf)` avant de lire, convertir ou comparer · ❌ indexer ou `JSON.stringify` l'`ArrayBuffer` lui-même.

```js
// Exemple 1 : mesuré, Node 22
const sig = await crypto.subtle.sign(
  'HMAC', cle, enc.encode('20261025'))
sig[0]                   // → undefined
new Uint8Array(sig)[0]   // → 238
sig.byteLength           // → 32
```

```python
# Exemple 2 : en Python, des bytes indexables
import hashlib, hmac
d = hmac.new(b"secret", b"20261025",
             hashlib.sha256).digest()
d[0]  # → 238
```

- Quiz : Que vaut `JSON.stringify(sig)` pour un `ArrayBuffer` de 32 octets ?
- [ ] Une chaîne hexadécimale
- [ ] Un tableau de 32 nombres
- [x] `'{}'`
- [ ] Une `TypeError`
- Réponse : `'{}'` : un `ArrayBuffer` n'a aucune propriété énumérable ; il faut d'abord une vue et un encodage (hex, base64).

## 12. digest : des octets, pas une chaîne
- Id : web-crypto-digest-octets-pas-chaine
- Sous-thème : encodage
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : web-crypto-textencoder-octets
- Voir aussi : web-crypto-digest-pas-incremental
- Mots-clés : vue typée, ArrayBuffer, aws4fetch
- Source : data-platform · pwa-sync
- Définition : `digest` n'accepte qu'un `ArrayBuffer`, une vue typée ou un `DataView` : une chaîne lève `TypeError`, il faut l'encoder avant.
- Contexte : Pas de conversion implicite comme dans certaines bibliothèques (`crypto-js`, `createHash().update('abc')` de Node) : `subtle` refuse. aws4fetch encode lui-même ses chaînes avec `TextEncoder` avant `digest`. En Python, `hashlib.sha256('abc')` échoue aussi (`TypeError`) : il faut `b'abc'` ou `.encode()`.
- Usage : ✅ `digest('SHA-256', new TextEncoder().encode(s))` · ❌ passer la chaîne ou un objet JSON sans sérialiser puis encoder.

```js
// Exemple 1 : mesuré, Node 22
await crypto.subtle.digest('SHA-256', 'abc')
// ❌ TypeError: … 2nd argument is not
//    instance of ArrayBuffer, Buffer,
//    TypedArray, or DataView.
```

```python
# Exemple 2 : Python refuse aussi
import hashlib
hashlib.sha256("abc")  # ❌ TypeError
```

- Quiz : Que fait `await crypto.subtle.digest('SHA-256', [97, 98, 99])` (codes de `'abc'` dans un tableau JS) ?
- [ ] Le hachage de `'abc'`
- [ ] Le hachage de la chaîne `'97,98,99'`
- [x] `TypeError`
- [ ] Un `ArrayBuffer` vide
- Réponse : `TypeError` (mesuré, Node 22) : un `Array` n'est pas une vue typée ; `new Uint8Array([97, 98, 99])` donne le hachage de `'abc'`.

## 13. randomUUID ou getRandomValues
- Id : web-crypto-randomuuid-ou-getrandomvalues
- Sous-thème : contexte sécurisé
- Type : comparaison
- Niveau : 2
- Profils : web
- Mots-clés : contexte sécurisé, UUID
- Source : data-platform · pwa-sync
- Définition : `crypto.randomUUID()` exige un contexte sécurisé, `crypto.getRandomValues()` non : sur une IP en HTTP, le premier vaut `undefined`.
- Contexte : Les deux tirent du même générateur sûr, mais la spécification réserve `randomUUID` (comme `subtle`) aux contextes sécurisés. Un identifiant de ligne généré avec `randomUUID` casse donc l'app ouverte depuis le téléphone en développement, alors que tout marche sur le Mac. `Math.random()` n'est jamais une alternative pour un identifiant unique.
- Usage : ✅ `randomUUID` en production HTTPS ; `getRandomValues` si la page peut tourner en HTTP sur le réseau local · ❌ `Math.random()` pour des identifiants ou des jetons.

```text
# Exemple 1 : mesuré dans Chromium
                  randomUUID  getRandomValues
localhost         function    function
192.168.10.119    undefined   function
```

- Quiz : Sur `http://192.168.10.119`, que fait `crypto.randomUUID()` ?
- [ ] Renvoie un UUID moins sûr
- [x] `TypeError` : `randomUUID` n'est pas une fonction
- [ ] Renvoie `undefined`
- [ ] Renvoie une `Promise` rejetée
- Réponse : `TypeError` (mesuré, Chromium) : la propriété vaut `undefined`, l'appeler lève « crypto.randomUUID is not a function ».

## 14. digest : pas de hachage incrémental
- Id : web-crypto-digest-pas-incremental
- Sous-thème : subtle
- Type : piège
- Niveau : 3
- Profils : web, expert
- Prérequis : web-crypto-digest-octets-pas-chaine
- Voir aussi : Python/hachage-update-par-morceaux
- Mots-clés : crypto.subtle, multipart upload
- Source : data-platform · pwa-sync
- Définition : `subtle.digest` hache un tampon complet en un appel : pas de `update()` par morceaux, tout le contenu doit tenir en mémoire.
- Contexte : Pour un fichier de quelques Mo, aucun souci ; pour un gros fichier (vidéo, export de plusieurs centaines de Mo), le charger entier peut faire tomber l'onglet sur un téléphone. Python (`hashlib.sha256().update(bloc)`) et Node (`createHash`) hachent en flux. Côté navigateur, il faut une bibliothèque incrémentale ou découper (hachage par parties, comme les checksums multipart de S3).
- Usage : ✅ hacher un corps de requête, un petit fichier, une chaîne · ❌ gros fichiers dans le navigateur : bibliothèque incrémentale ou hachage côté serveur.

```python
# Exemple 1 : en Python, par blocs
import hashlib
h = hashlib.sha256()
for bloc in (b"ab", b"c"):
    h.update(bloc)
h.hexdigest() == hashlib.sha256(b"abc").hexdigest()
# → True : même résultat, mémoire bornée
```

- Quiz : On hache deux morceaux avec deux `digest`, puis on concatène les résultats : égal au `digest` du tout ?
- [ ] Oui : SHA-256 est additif
- [x] Non : on obtient deux hachages collés
- [ ] Oui, si les morceaux font 64 octets
- [ ] Non, `digest` refuse les morceaux
- Réponse : non : `H(a) + H(b)` n'est pas `H(a + b)` ; sans état incrémental, seul le tampon complet donne le bon hachage.

## 15. base64 d'une signature : attention au spread
- Id : web-crypto-base64-spread
- Sous-thème : encodage
- Type : piège
- Niveau : 3
- Profils : web, expert
- Prérequis : web-crypto-hmac-importkey-sign, web-crypto-arraybuffer-vue
- Mots-clés : vue typée, ArrayBuffer
- Source : data-platform · pwa-sync
- Définition : `btoa(String.fromCharCode(...new Uint8Array(buf)))` encode des octets en base64 ; correct pour une signature, il casse sur un gros tampon.
- Contexte : Le spread passe chaque octet comme un argument de fonction : au-delà de quelques centaines de milliers, la pile déborde (`RangeError`). Pour un gros contenu, on encode par tranches ou via `FileReader.readAsDataURL`. `Uint8Array.prototype.toBase64()` existe dans Chromium récent mais pas dans Node 22 (où `Buffer.from(buf).toString('base64')` sert).
- Usage : ✅ spread pour une signature ou un hachage (32 octets) · ❌ spread sur un fichier entier : boucle par tranches de 32 Ko.

```js
// Exemple 1 : mesuré, Node 22
btoa(String.fromCharCode(
  ...new Uint8Array(sig))).slice(0, 12)
// → '7vCnBCpngtJU'
String.fromCharCode(
  ...new Uint8Array(1_000_000))
// ❌ RangeError: Maximum call stack
//    size exceeded
```

```python
# Exemple 2 : la même valeur en Python
import base64, hashlib, hmac
d = hmac.new(b"secret", b"20261025",
             hashlib.sha256).digest()
base64.b64encode(d).decode()[:12]
# → '7vCnBCpngtJU'
```

- Quiz : Base64 de 32 octets : combien de caractères ?
- [ ] 32
- [x] 44
- [ ] 43
- [ ] 64
- Réponse : 44 : base64 code 3 octets en 4 caractères ; 32 octets → 11 groupes (le dernier incomplet) → 44 caractères, dont un `=` de remplissage.
