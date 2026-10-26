---
title: "Cartes · curl"
type: cartes
langage: DevOps
chapitre: Terminal
cours: curl
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · curl
DevOps · curl : compression, en-têtes (format spec v3 de revision-pwa).

## 1. --compressed : décompresser la réponse
- Id : curl-compressed-decompresser
- Sous-thème : compression
- Type : piège
- Niveau : 1
- Profils : débutant, web, data
- Source : data-platform · S1-05
- Définition : `curl --compressed` demande une réponse compressée et la décompresse ; sans l'option, curl écrit les octets reçus tels quels.
- Contexte : Le navigateur, `fetch` et `httpx` décompressent seuls, curl non. Certains serveurs (OpenDataSoft, donc BODACC) envoient du gzip même sans `Accept-Encoding` : la sortie commence par les octets `1f 8b`, et le `json.load` derrière le pipe plante. L'en-tête `content-encoding: gzip` le confirme. Sur un JSON répétitif, gzip divise le transfert par 5 à 10.
- Usage : ✅ toujours pour explorer une API : `curl -s --compressed` · ❌ le reproduire en Python : `httpx` et `requests` décompressent déjà, `gzip.decompress` en plus casserait.

```bash
# Exemple 1 : sans l'option, du binaire
# serveur qui envoie toujours du gzip
U="$BODACC/records?limit=1&select=id"
curl -s "$U" | head -c 4 | xxd
# 00000000: 1f8b 0800   (gzip)
curl -s --compressed "$U" | head -c 18
# {"total_count": 51
```

```python
# Exemple 2 : httpx décompresse seul
import gzip
import httpx

r = httpx.Response(200,
    headers={"content-encoding": "gzip"},
    content=gzip.compress(b'{"n": 1}'))
r.json()   # → {"n": 1}
```

- Quiz : `curl -s -H "Accept-Encoding: gzip" "$U"`, sans `--compressed` : que reçoit-on ?
- [ ] Du JSON lisible
- [x] Des octets gzip bruts
- [ ] Une erreur 406
- [ ] Du JSON, mais sans les accents
- Réponse : des octets gzip bruts : l'en-tête demande la compression, seul `--compressed` fait décompresser par curl.

## 2. -D - : les en-têtes sans le corps
- Id : curl-entetes-sans-corps
- Sous-thème : en-têtes
- Type : recette
- Niveau : 2
- Profils : web, data, ops
- Source : data-platform · S1-05
- Définition : `curl -D - -o /dev/null` affiche les en-têtes de réponse et jette le corps ; `-w "%{http_code}"` imprime le statut HTTP.
- Contexte : Les en-têtes disent ce que le corps tait : quota (`x-ratelimit-*`), compression (`content-encoding`), cache (`cache-control: max-age=60`), type annoncé (`content-type`, parfois faux). `-D -` écrit les en-têtes sur la sortie standard, `-o /dev/null` supprime le corps, `-w` imprime des variables après la requête (`%{http_code}`, `%{time_total}`, `%{url_effective}`). `-I` envoie un HEAD, que certains serveurs traitent autrement qu'un GET.
- Usage : ✅ vérifier un plafond (400 ou 200), lire un quota, chronométrer · ❌ `-I` pour diagnostiquer un GET : la réponse peut différer ; `-D - -o /dev/null` envoie le vrai GET.

```bash
# Exemple 1 : seulement le statut
curl -s --compressed -o /dev/null \
  -w "%{http_code}\n" \
  "$BODACC/records?limit=101"
# → 400
```

```bash
# Exemple 2 : les en-têtes utiles
curl -s --compressed -D - -o /dev/null \
  "$BODACC/records?limit=1" \
  | grep -i -E "ratelimit|encoding"
# x-ratelimit-remaining: 2996594
# x-ratelimit-limit: 5000000
# x-ratelimit-reset: 2026-10-25 00:00:00+00:00
# content-encoding: gzip
```

- Quiz : Que fait `curl -s -D - "$U"`, sans `-o /dev/null` ?
- [ ] Seulement les en-têtes
- [x] Les en-têtes puis le corps
- [ ] Le corps puis les en-têtes
- [ ] Seulement le statut
- Réponse : les en-têtes puis le corps, mêlés sur la sortie standard : `-D -` ajoute les en-têtes, il ne remplace pas le corps.
