---
title: "Cartes · CloudFront"
type: cartes
langage: AWS
cours: CloudFront
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · CloudFront
AWS · CloudFront : cache, comportements, distribution, origines, sécurité (format spec v3 de revision-pwa).

## 1. distribution : le CDN devant S3
- Sous-thème : distribution
- Niveau : 1
- Définition : Une distribution CloudFront sert des fichiers depuis des caches proches des utilisateurs, en HTTPS, sur un domaine `dxxxx.cloudfront.net` (≈ CDN Vercel).
- Contexte : Le navigateur ne parle jamais à S3 : il interroge le point de présence (PoP) le plus proche, qui répond depuis son cache ou va chercher l'objet à l'origine. Une seule distribution sert ici l'app et le catalogue sur le même domaine, donc pas de CORS. `price_class` limite les régions de PoP utilisées pour réduire le coût.
- Usage : ✅ site statique, SPA, fichiers publics servis depuis S3 · ❌ API dynamique à faible trafic : API Gateway ou URL de Lambda suffisent, sans couche de cache.

```hcl
# Exemple 1 : la distribution du projet
resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  default_root_object = "index.html"
  http_version        = "http2and3"
  price_class         = "PriceClass_100"
}
```

```bash
# Exemple 2 : qui a répondu ?
curl -sI https://d1non6rpr4vppb\
.cloudfront.net/ | grep -iE \
  "x-cache|x-amz-cf-pop"
# → x-cache: RefreshHit from cloudfront
#   x-amz-cf-pop: DUB2-P1  (Dublin)
```

- Quiz : Avec `PriceClass_100` (Europe, Amérique du Nord, Israël), qu'obtient un utilisateur à Tokyo ?
- [ ] Une erreur `403` : sa zone est exclue
- [x] La page, servie depuis un PoP d'une zone incluse
- [ ] La page, servie directement par le bucket S3
- [ ] Une redirection vers un PoP de Tokyo payant
- Réponse : la page, depuis un PoP inclus : la classe de prix réduit les PoP utilisés et le coût, elle ne bloque personne ; la latence augmente.

## 2. default_root_object : servir la racine
- Sous-thème : distribution
- Niveau : 1
- Définition : `default_root_object` désigne l'objet servi quand on demande la racine `/` du domaine (≈ `index` d'un serveur web).
- Contexte : Sans lui, `GET /` demande à S3 la clé vide, qui n'existe pas : `403`. CloudFront ne fait que cette substitution, à la racine seulement ; ce n'est pas un vrai serveur web qui chercherait `index.html` dans chaque dossier. L'app n'a qu'une page et se navigue par query string (`/?langage=AWS`), donc la racine suffit.
- Usage : ✅ SPA à une page servie à la racine · ❌ site statique à sous-dossiers (`/docs/`) : fonction CloudFront qui réécrit `/docs/` en `/docs/index.html`.

```hcl
# Exemple 1 : la racine sert index.html
default_root_object = "index.html"
# GET /            → index.html
# GET /?langage=AWS → index.html
```

- Quiz : Le bucket contient `docs/index.html` : que renvoie `GET /docs/` ?
- [ ] `200` avec `docs/index.html`
- [ ] `301` vers `/docs/index.html`
- [x] `403`
- [ ] `404`
- Réponse : `403` (mesuré) : `default_root_object` ne vaut que pour la racine ; CloudFront demande la clé `docs/` telle quelle, absente, et S3 répond `403`.

## 3. viewer_certificate : le certificat par défaut
- Sous-thème : distribution
- Niveau : 1
- Définition : `cloudfront_default_certificate = true` utilise le certificat d'AWS pour `*.cloudfront.net` : HTTPS immédiat, sans ACM ni domaine à gérer.
- Contexte : Le certificat par défaut ne couvre que le domaine généré par AWS. Pour un domaine perso, il faut un certificat ACM, un alias (`aliases`) sur la distribution et un enregistrement DNS. CloudFront est un service global : il ne lit les certificats ACM que dans une seule région, quelle que soit celle des buckets.
- Usage : ✅ app interne ou personnelle sur `*.cloudfront.net`, zéro configuration · ❌ domaine de marque : certificat ACM et `ssl_support_method = "sni-only"`.

```hcl
# Exemple 1 : HTTPS sans ACM
viewer_certificate {
  cloudfront_default_certificate = true
}
# https://d1non6rpr4vppb.cloudfront.net
# → certificat *.cloudfront.net valide
```

- Quiz : Pour servir `revision.mondomaine.fr`, dans quelle région créer le certificat ACM ?
- [ ] `eu-west-3`, celle des buckets
- [x] `us-east-1`
- [ ] Dans toutes les régions des PoP
- [ ] Aucune : ACM est global
- Réponse : `us-east-1` : CloudFront ne lit les certificats ACM que dans cette région, même si tout le reste est à Paris.

## 4. origin : le domaine régional du bucket
- Sous-thème : origines
- Niveau : 1
- Définition : Une origine est la source que CloudFront interroge quand l'objet manque au cache ; pour un bucket privé, son domaine régional REST.
- Contexte : `bucket_regional_domain_name` donne `<bucket>.s3.<région>.amazonaws.com`, l'endpoint REST qui accepte les requêtes signées. `origin_id` est un nom libre, cité par les comportements via `target_origin_id`. La clé S3 demandée garde le chemin entier de l'URL : `/content/catalog.json` lit la clé `content/catalog.json`.
- Usage : ✅ endpoint régional REST + OAC pour tout bucket privé · ❌ endpoint « site web statique » du bucket : HTTP seulement, bucket forcément public.

```hcl
# Exemple 1 : origine S3 privée
origin {
  origin_id   = "site"
  domain_name = (aws_s3_bucket.this["site"]
  .bucket_regional_domain_name)
}
# → revision-pwa-dev-site-<account_id>
#   .s3.eu-west-3.amazonaws.com
```

- Quiz : On remplace par l'endpoint « site web statique » (`website_endpoint`) : l'OAC fonctionne-t-il encore ?
- [ ] Oui, l'OAC marche sur tout endpoint S3
- [x] Non : l'OAC exige l'endpoint REST
- [ ] Oui, si le bucket est en HTTPS
- [ ] Non : il faut un OAI à la place
- Réponse : non : l'endpoint web est une origine HTTP « custom », sans signature SigV4 ; ni OAC ni OAI ne s'y appliquent, il faudrait un bucket public.

## 5. ordered_cache_behavior : router par chemin
- Sous-thème : comportements
- Niveau : 1
- Définition : `ordered_cache_behavior` envoie les URL qui correspondent à `path_pattern` vers une autre origine ; le reste suit `default_cache_behavior`.
- Contexte : Chaque comportement porte sa propre origine, sa politique de cache, ses méthodes et ses en-têtes. Ici `/content/*` part vers le bucket `content` (le catalogue), tout le reste vers le bucket `site` (l'app) : un seul domaine pour deux buckets. Les comportements ordonnés sont testés dans l'ordre de la liste ; le défaut ramasse ce qui reste.
- Usage : ✅ plusieurs origines derrière un domaine (app, données, API) · ❌ un comportement par fichier : un motif par famille de chemins.

```hcl
# Exemple 1 : deux buckets, un domaine
ordered_cache_behavior {
  path_pattern     = "/content/*"
  target_origin_id = "content"
}
default_cache_behavior {
  target_origin_id = "site"
}
# /content/catalog.json → content
# /assets/index-RvyxYAT2.js → site
```

- Quiz : `/content/*` est listé avant `/content/catalog.json` : quel comportement sert le catalogue ?
- [x] `/content/*`
- [ ] `/content/catalog.json`, plus précis
- [ ] Le comportement par défaut
- [ ] Les deux : CloudFront fusionne leurs réglages
- Réponse : `/content/*` : CloudFront prend le premier motif qui correspond dans l'ordre de la liste ; le plus précis doit venir en premier.

## 6. viewer_protocol_policy : forcer HTTPS
- Sous-thème : sécurité
- Niveau : 1
- Définition : `viewer_protocol_policy` fixe le sort des requêtes HTTP du navigateur : `redirect-to-https` renvoie une redirection 301 vers la même URL en HTTPS.
- Contexte : La politique se règle par comportement : chacun doit la porter, le défaut comme `/content/*`. Le 301 est mis en cache par le navigateur, et l'en-tête HSTS posé ensuite fait passer les visites suivantes directement en HTTPS, sans aller-retour HTTP. La valeur `allow-all` laisserait servir le site en clair.
- Usage : ✅ `redirect-to-https` pour toute app publique · ❌ `allow-all` : contenu servi en clair, et service worker refusé hors HTTPS.

```hcl
# Exemple 1 : HTTP → HTTPS
viewer_protocol_policy = "redirect-to-https"
# curl -sI http://d1non6rpr4vppb
#   .cloudfront.net/ | head -1
# → HTTP/1.1 301 Moved Permanently
```

- Quiz : Et avec `viewer_protocol_policy = "https-only"`, que reçoit un lien `http://` partagé ?
- [ ] Un `301` vers HTTPS, comme avant
- [ ] La page, servie en HTTP
- [x] Un `403`
- [ ] Un `426 Upgrade Required`
- Réponse : un `403` : `https-only` refuse le HTTP sans rediriger ; un lien `http://` devient une erreur, d'où `redirect-to-https` pour une app publique.

## 7. OAC : CloudFront signe ses requêtes
- Sous-thème : sécurité
- Niveau : 1
- Définition : Un Origin Access Control fait signer (SigV4) les requêtes de CloudFront vers S3, pour que le bucket reste privé et n'accepte qu'elles.
- Contexte : Le bucket bloque tout accès public ; sa politique n'autorise `s3:GetObject` qu'au service CloudFront, et S3 vérifie la signature de chaque requête. Lire le bucket en direct par son URL renvoie donc `403` (mesuré). L'OAC remplace l'ancien OAI (Origin Access Identity), qui ne gérait ni SSE-KMS ni toutes les régions récentes.
- Usage : ✅ tout bucket servi par CloudFront, gardé privé · ❌ bucket public ou OAI hérité : contournable en direct, ou déprécié.

```hcl
# Exemple 1 : un OAC pour les deux buckets
resource "aws_cloudfront_origin_access_control" "s3" {
  name     = "${local.prefix}-s3"
  origin_access_control_origin_type = "s3"
  signing_behavior = "always"
  signing_protocol = "sigv4"
}
```

```bash
# Exemple 2 : le bucket en direct
curl -sI https://revision-pwa-dev-site\
-<account_id>.s3.eu-west-3\
.amazonaws.com/index.html | head -1
# → HTTP/1.1 403 Forbidden
```

- Quiz : Les buckets seraient chiffrés avec une clé KMS du projet : que faut-il ajouter pour que CloudFront les lise ?
- [ ] Rien : l'OAC déchiffre tout seul
- [x] `kms:Decrypt` pour CloudFront dans la politique de la clé
- [ ] `kms:Decrypt` dans la politique du bucket
- [ ] `signing_protocol = "kms"` sur l'OAC
- Réponse : `kms:Decrypt` pour `cloudfront.amazonaws.com` (avec `AWS:SourceArn`) dans la politique de la clé ; sans ça, `403`, d'où SSE-S3 ici.

## 8. Cache-Control : la durée de cache
- Sous-thème : cache
- Niveau : 1
- Définition : CloudFront garde un objet le temps dit par son `Cache-Control`, borné par les TTL minimum et maximum de la politique de cache.
- Contexte : `Managed-CachingOptimized` fixe min 1 s, défaut 86 400 s, max 31 536 000 s (mesuré). Le `Cache-Control` est posé sur chaque objet au dépôt S3 par `make deploy` : `immutable` un an pour `assets/` (noms hachés, jamais réécrits), `no-cache` pour `index.html`, `sw.js` et `catalog.json`. Le navigateur suit le même en-tête.
- Usage : ✅ un an + `immutable` pour les fichiers à nom haché · ❌ un an sur `index.html` : les utilisateurs gardent l'ancienne version, qui pointe vers des assets supprimés.

```bash
# Exemple 1 : ce que porte un asset
curl -sI https://d1non6rpr4vppb\
.cloudfront.net/assets/index-RvyxYAT2.js \
  | grep -i cache-control
# → public,max-age=31536000,immutable
```

```hcl
# Exemple 2 : la politique gérée, lue
data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}
# min 1 s · défaut 86400 s · max 1 an
```

- Quiz : Un objet déposé **sans** `Cache-Control` : combien de temps CloudFront le garde-t-il ?
- [ ] 1 seconde, le minimum
- [ ] Pas du tout
- [ ] 1 an, le maximum
- [x] 24 heures, le TTL par défaut
- Réponse : 24 heures : sans en-tête de l'origine, CloudFront applique le TTL par défaut (86 400 s) ; d'où un `Cache-Control` explicite sur chaque fichier.

## 9. dynamic : un bloc origin par bucket
- Sous-thème : origines
- Niveau : 2
- Définition : `dynamic "origin"` génère un bloc `origin` par élément de `for_each`, dans une seule ressource (≈ `.map()` qui rend des blocs).
- Contexte : Un `for_each` sur la ressource créerait plusieurs distributions ; on en veut une seule, à plusieurs origines. `dynamic` répète un bloc imbriqué ; dans `content`, l'itérateur porte le nom du bloc (`origin.key`, `origin.value`). Les buckets venant de `aws_s3_bucket.this` (un `for_each`), ajouter un bucket ajoute une origine.
- Usage : ✅ blocs imbriqués répétés depuis une map (origines, règles, statements) · ❌ deux blocs fixes et différents : les écrire en clair, plus lisible.

```hcl
# Exemple 1 : une origine par bucket
dynamic "origin" {
  for_each = aws_s3_bucket.this
  content {
    origin_id = origin.key
    domain_name = (origin.value
    .bucket_regional_domain_name)
  }
}
# → origin "content" + origin "site"
```

- Quiz : On écrit `origin_id = each.key` dans ce `content` : que se passe-t-il ?
- [ ] Ça marche : `each` vaut l'itérateur courant
- [ ] `origin_id` vaut `null`
- [x] Erreur : `each` sans `for_each` sur la ressource
- [ ] Erreur seulement à l'`apply`
- Réponse : erreur `Reference to "each" in context without for_each` (au `plan`, mesuré) : dans un `dynamic`, l'itérateur porte le nom du bloc.

## 10. path_pattern : sensible à la casse
- Sous-thème : comportements
- Niveau : 2
- Définition : `path_pattern` accepte `*` et `?` et se compare au chemin de l'URL, sans le domaine ni la query string.
- Contexte : `*` couvre n'importe quelle suite de caractères, `/` compris : `/content/*` attrape aussi `/content/a/b.json`. La comparaison est sensible à la casse : une URL qui ne correspond à aucun motif tombe dans le comportement par défaut, donc vers le bucket `site`. Mesuré : `/Content/catalog.json` renvoie `403`, `/content/catalog.json` renvoie `200`.
- Usage : ✅ motifs en minuscules, URL générées par le code · ❌ chemins saisis à la main ou casse variable : normaliser en amont (fonction CloudFront).

```hcl
# Exemple 1 : ce qui correspond
path_pattern = "/content/*"
# /content/catalog.json → content
# /content/a/b.json     → content
# /Content/catalog.json → site (403)
```

- Quiz : Avec le motif `/content/*`, où part `GET /content` (sans barre finale) ?
- [ ] Vers `content` : `*` accepte le vide
- [x] Vers `site`, le comportement par défaut
- [ ] Redirigé en `301` vers `/content/`
- [ ] `400` : chemin invalide
- Réponse : vers `site` : le motif exige la barre après `content` ; `/content` ne correspond pas et tombe dans le comportement par défaut.

## 11. no-cache : le TTL minimum gagne
- Sous-thème : cache
- Niveau : 2
- Définition : `Cache-Control: no-cache` demande de revalider l'objet à chaque requête ; on le pose sur `index.html`, `sw.js` et `catalog.json`.
- Contexte : Pour le navigateur, `no-cache` veut dire « redemande avant de réutiliser ». Pour CloudFront, le TTL minimum de la politique l'emporte : avec `CachingOptimized` (min 1 s), l'objet reste en cache 1 seconde, puis CloudFront le revalide auprès de S3 (`If-None-Match`). D'où `x-cache: RefreshHit` (mesuré) : copie en cache, confirmée par l'origine.
- Usage : ✅ `no-cache` sur les fichiers à nom fixe qui changent (`index.html`, `sw.js`, catalogue) · ❌ `no-store` « pour être sûr » : plus aucun cache, chaque visite relit S3.

```bash
# Exemple 1 : déposé en no-cache
aws s3 cp app/dist/index.html \
  s3://$SITE_BUCKET/ \
  --cache-control no-cache
# catalog.json, lui aussi en no-cache :
curl -sI https://d1non6rpr4vppb\
.cloudfront.net/content/catalog.json \
  | grep -i x-cache
# → RefreshHit from cloudfront
```

- Quiz : Avec `CachingOptimized`, un `index.html` en `no-cache` reste-t-il en cache CloudFront ?
- [ ] Non : `no-cache` désactive le cache CloudFront
- [x] Oui, 1 seconde : le TTL minimum
- [ ] Oui, 24 heures : le TTL par défaut
- [ ] Oui, jusqu'à la prochaine invalidation
- Réponse : oui, 1 seconde : un TTL minimum supérieur à 0 l'emporte sur `no-cache` ; il faut une politique à TTL min 0 pour ne rien garder.

## 12. clé de cache : query string ignorée
- Sous-thème : cache
- Niveau : 2
- Définition : La clé de cache dit quelles parties de la requête distinguent deux objets ; `CachingOptimized` ignore query string, cookies et en-têtes.
- Contexte : Deux URL qui ne diffèrent que par la query string partagent donc la même entrée de cache : mesuré, `/?zz=<aléatoire>` répond `Hit` dès la première requête. C'est sans danger ici, car l'app lit `location.search` côté client et le même `index.html` convient à toutes les URL. Moins de variantes en cache, plus de hits.
- Usage : ✅ SPA ou fichiers statiques qui ne dépendent pas de la query string · ❌ origine qui rend une réponse différente selon `?param=` : politique qui inclut ce paramètre dans la clé.

```bash
# Exemple 1 : query inédite, déjà en cache
curl -sI "https://d1non6rpr4vppb\
.cloudfront.net/?zz=$RANDOM$RANDOM" \
  | grep -i x-cache
# → Hit (ou RefreshHit) : jamais Miss
```

- Quiz : Une API derrière cette politique répond selon `?siren=…` : que reçoit le 2e appelant, avec un autre SIREN ?
- [ ] Sa propre réponse : la query fait partie de l'URL
- [x] La réponse mise en cache pour le 1er SIREN
- [ ] Un `400` : la query est retirée
- [ ] Une réponse vide
- Réponse : la réponse du 1er SIREN : la query string est hors de la clé de cache, tous les appelants partagent la même entrée.

## 13. invalidation : vider le cache
- Sous-thème : cache
- Niveau : 2
- Définition : Une invalidation retire des chemins des caches CloudFront avant leur expiration, pour servir tout de suite la nouvelle version.
- Contexte : `make deploy` en lance une sur `/*` après chaque `s3 sync`. Elle met de quelques secondes à quelques minutes à se propager (`InProgress` puis `Completed`). Elle ne touche pas le cache des navigateurs : un fichier servi avec `max-age` d'un an reste chez l'utilisateur, d'où les noms hachés pour les assets.
- Usage : ✅ `/*` après un déploiement de site statique · ❌ invalidation comme seule stratégie de cache : noms de fichiers hachés et `Cache-Control` adapté d'abord.

```bash
# Exemple 1 : ce que lance make deploy
aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/*"
# → Status: InProgress, puis Completed
```

- Quiz : Les 1 000 premiers chemins invalidés par mois sont gratuits : combien en compte `--paths "/*"` ?
- [x] Un seul
- [ ] Un par fichier du bucket
- [ ] Un par PoP de la distribution
- [ ] Un par dossier du bucket
- Réponse : un seul : un chemin avec joker compte pour un, quel que soit le nombre de fichiers retirés du cache.

## 14. politique de bucket : AWS:SourceArn
- Sous-thème : sécurité
- Niveau : 2
- Définition : La politique du bucket autorise `s3:GetObject` au service CloudFront, seulement pour les requêtes venant de la distribution désignée par `AWS:SourceArn`.
- Contexte : Le principal `cloudfront.amazonaws.com` désigne le service entier, toutes distributions et tous comptes confondus. La condition `AWS:SourceArn` restreint à l'ARN de cette distribution : c'est elle qui rend l'OAC sûr. Le compte AWS est partagé avec d'autres projets, donc une autre distribution du compte, même avec un OAC, est refusée.
- Usage : ✅ condition `AWS:SourceArn` sur toute politique qui ouvre un bucket à un service · ❌ principal de service seul : ouvert à tout client de ce service.

```hcl
# Exemple 1 : CloudFront, cette distribution
statement {
  actions = ["s3:GetObject"]
  principals {
    identifiers = ["cloudfront.amazonaws.com"]
    type        = "Service"
  }
  condition {
    test     = "StringEquals"
    variable = "AWS:SourceArn"
    values = [
      aws_cloudfront_distribution.this.arn
    ]
  }
}
```

- Quiz : Sans le bloc `condition`, qui peut lire le bucket ?
- [ ] Seulement cette distribution, via l'OAC
- [ ] Les distributions de ce compte seulement
- [ ] Personne : la politique devient invalide
- [x] Toute distribution CloudFront, même d'un autre compte
- Réponse : toute distribution CloudFront, même ailleurs : le principal de service ne désigne pas la distribution, seule `AWS:SourceArn` le fait.

## 15. 403 au lieu de 404
- Sous-thème : sécurité
- Niveau : 2
- Définition : S3 ne dit qu'un objet est absent (`404`) qu'à qui a le droit `s3:ListBucket` ; sinon il répond `403`, sans rien révéler.
- Contexte : Sans droit de lister, savoir qu'une clé n'existe pas serait déjà une information : S3 répond donc « accès refusé » pour tout objet absent. CloudFront n'ayant que `s3:GetObject`, une URL inconnue donne `403` (mesuré sur `/absent.js`). Au débogage, un `403` ne veut donc pas forcément dire « problème de droits ».
- Usage : ✅ lire un `403` comme « absent ou interdit », vérifier la clé S3 d'abord · ❌ ajouter `s3:ListBucket` à CloudFront pour avoir des `404` : il expose la liste des objets.

```bash
# Exemple 1 : un fichier qui n'existe pas
curl -sI https://d1non6rpr4vppb\
.cloudfront.net/absent.js | head -1
# → HTTP/2 403
# CloudFront : s3:GetObject seulement
```

- Quiz : On ajoute `s3:ListBucket` dans ce statement, sur `"${arn}/*"` : obtient-on des `404` ?
- [ ] Oui, dès le prochain déploiement
- [x] Non, toujours `403`
- [ ] Oui, mais seulement sur `/content/*`
- [ ] Non : `500`, la politique est invalide
- Réponse : non, toujours `403` : `ListBucket` porte sur le bucket (`arn:aws:s3:::nom`), pas sur les objets (`…/*`) ; la ressource ne correspond jamais.

## 16. en-têtes de sécurité gérés
- Sous-thème : sécurité
- Niveau : 2
- Définition : Une `response_headers_policy` ajoute des en-têtes à chaque réponse ; `Managed-SecurityHeadersPolicy` pose HSTS, `nosniff`, `SAMEORIGIN` et une `Referrer-Policy` stricte.
- Contexte : Mesuré : `strict-transport-security: max-age=31536000`, `x-frame-options: SAMEORIGIN`, `x-content-type-options: nosniff`, `referrer-policy: strict-origin-when-cross-origin`, plus `x-xss-protection`. La politique est lue par un `data` (gérée par AWS, jamais recréée) et attachée à chaque comportement, le défaut comme `/content/*`. S3 n'a pas à les poser.
- Usage : ✅ politique gérée sur toute distribution publique, en une ligne · ❌ en-têtes propres à l'app (CSP, `Permissions-Policy`) : politique d'en-têtes personnalisée.

```bash
# Exemple 1 : les en-têtes ajoutés
curl -sI https://d1non6rpr4vppb\
.cloudfront.net/ | grep -iE \
  "strict|frame|nosniff"
# → x-frame-options: SAMEORIGIN
#   referrer-policy:
#     strict-origin-when-cross-origin
#   x-content-type-options: nosniff
#   strict-transport-security:
#     max-age=31536000
```

- Quiz : `Managed-SecurityHeadersPolicy` pose-t-elle une `Content-Security-Policy` ?
- [ ] Oui, `default-src 'self'`
- [ ] Oui, mais en mode `Report-Only`
- [x] Non : aucune CSP
- [ ] Oui, seulement sur `index.html`
- Réponse : non (mesuré) : une CSP dépend des scripts, styles et `fetch` de chaque app ; il faut une politique d'en-têtes personnalisée.

## 17. compress : Brotli à la volée
- Sous-thème : cache
- Niveau : 2
- Définition : `compress = true` laisse CloudFront compresser en Brotli ou Gzip les réponses textuelles, selon l'`Accept-Encoding` du navigateur.
- Contexte : La compression se fait au PoP, une fois par variante, puis la version compressée est mise en cache : S3 garde les fichiers bruts. Mesuré : `content-encoding: br` sur un asset JS et sur `catalog.json` (247 Ko bruts). La politique `CachingOptimized` inclut l'encodage dans la clé de cache, pour ne pas servir du Brotli à un client qui ne le lit pas.
- Usage : ✅ JS, CSS, JSON, HTML servis depuis S3 · ❌ fichiers déjà compressés (images, `.zip`, vidéos) : aucun gain, CloudFront les ignore.

```bash
# Exemple 1 : réponse compressée
curl -s -o /dev/null -D - \
  -H "Accept-Encoding: br,gzip" \
  https://d1non6rpr4vppb\
.cloudfront.net/content/catalog.json \
  | grep -i content-encoding
# → content-encoding: br
```

- Quiz : Avec `compress = true`, un fichier JSON de 600 octets est-il compressé ?
- [ ] Oui, comme tout fichier JSON
- [ ] Oui, mais seulement en Gzip
- [ ] Non : JSON n'est jamais compressé
- [x] Non : en dessous de 1 000 octets
- Réponse : non : CloudFront ne compresse qu'entre 1 000 et 10 000 000 octets ; un petit fichier gagnerait trop peu.

## 18. custom_error_response : toute la distribution
- Sous-thème : comportements
- Niveau : 3
- Définition : `custom_error_response` remplace une erreur de l'origine (403, 404) par une autre page, typiquement `/index.html` en `200` pour une SPA.
- Contexte : Le réglage vaut pour toute la distribution, pas par comportement : il s'appliquerait aussi à `/content/*`. C'est pourquoi `cdn.tf` n'en a pas : l'app se navigue par query string (`/?langage=…`), une seule page, donc aucune URL profonde à rattraper. Une SPA à routes `/cours/python` en aurait besoin, avec ce piège.
- Usage : ✅ SPA à routes profondes servie depuis S3 · ❌ distribution qui sert aussi des données (JSON) : préférer des routes par query string ou une fonction CloudFront ciblée.

```hcl
# Exemple 1 : le repli SPA classique
custom_error_response {
  error_code         = 403
  response_code      = 200
  response_page_path = "/index.html"
}
# GET /cours/python (clé absente)
# → 200 + index.html, routeur JS
```

- Quiz : Avec ce bloc, `catalog.json` n'est pas encore publié : que donne `await (await fetch('/content/catalog.json')).json()` ?
- [ ] `res.ok` vaut `false` : un `403`
- [ ] `null`
- [x] `SyntaxError` : du HTML reçu en `200`
- [ ] Un `404` propre
- Réponse : `SyntaxError` : le `403` du bucket `content` est aussi remplacé par `index.html` en `200`, et `.json()` échoue sur du HTML.

## 19. politique content : jamais sources/
- Sous-thème : sécurité
- Niveau : 3
- Définition : La politique du bucket `content` n'autorise CloudFront que sur `content/*` : les `.md` bruts sous `sources/` restent privés même via la distribution.
- Contexte : Le bucket `content` contient deux choses : `sources/<projet>/cartes-*.md`, déposés par les producteurs, et `content/catalog.json`, écrit par la Lambda. Seul le catalogue doit être public. Le comportement `/content/*` limite déjà le routage, mais la politique de bucket le garantit indépendamment : une erreur de motif ou un comportement ajouté plus tard n'exposerait rien.
- Usage : ✅ restreindre la politique de bucket au préfixe réellement servi · ❌ `"${arn}/*"` sur un bucket qui mélange public et privé : un seul comportement mal réglé expose tout.

```hcl
# Exemple 1 : un préfixe par bucket
for_each = {
  site = "${aws_s3_bucket.this["site"].arn}/*"
  content = (
  "${aws_s3_bucket.this["content"].arn}/content/*")
}
# statement : s3:GetObject sur each.value
```

- Quiz : On ajoute un comportement `/sources/*` vers l'origine `content` : que renvoie `/sources/data-platform/cartes-aws-cloudfront.md` ?
- [ ] `200` avec le fichier Markdown
- [x] `403`
- [ ] `404`
- [ ] `301` vers `/content/`
- Réponse : `403` : CloudFront demande bien la clé `sources/…`, mais la politique n'accorde `GetObject` que sur `content/*` ; S3 refuse.

## 20. déploiement : les assets avant index.html
- Sous-thème : cache
- Niveau : 3
- Définition : `make deploy` envoie d'abord les nouveaux `assets/`, puis `index.html` en `no-cache`, et ne supprime les anciens assets qu'à la fin.
- Contexte : `index.html` référence des fichiers à nom haché (`index-RvyxYAT2.js`). Pendant le déploiement, un utilisateur peut charger l'ancien ou le nouvel `index.html` : l'ordre garantit que chacun pointe vers des fichiers présents. Les anciens assets ne disparaissent qu'après la mise en ligne du nouvel `index.html`, puis l'invalidation `/*` vide les caches.
- Usage : ✅ ordre assets → index → suppression pour tout déploiement S3 sans interruption · ❌ un seul `aws s3 sync --delete` : ordre des envois non garanti, fenêtre de fichiers absents.

```bash
# Exemple 1 : l'ordre du Makefile
# 1. nouveaux assets, cache 1 an
aws s3 sync app/dist/assets/ \
  s3://$B/assets/ $IMMUTABLE
# 2. le reste en no-cache
aws s3 sync app/dist/ s3://$B/ \
  --delete --exclude "assets/*" \
  --cache-control no-cache
# 3. anciens assets supprimés
aws s3 sync app/dist/assets/ \
  s3://$B/assets/ --delete $IMMUTABLE
```

- Quiz : On inverse les étapes 1 et 3 (suppression des anciens assets d'abord) : que voit un utilisateur pendant le déploiement ?
- [ ] Rien : l'invalidation finale corrige tout
- [ ] L'ancienne version, intacte jusqu'à la fin
- [ ] La nouvelle version, sans styles
- [x] Une page blanche : son `index.html` cite des JS supprimés
- Réponse : une page blanche : l'ancien `index.html`, encore servi, demande des assets déjà supprimés, et S3 répond `403`.

## 21. CloudFront Functions : réécrire au bord
- Sous-thème : comportements
- Niveau : 3
- Définition : Une CloudFront Function est un petit JavaScript exécuté au point de présence sur la requête ou la réponse : réécrire une URL, poser un en-tête.
- Contexte : Associée à un seul comportement (`function_association`), elle remplace le repli SPA de `custom_error_response` sans toucher `/content/*`. Elle tourne en moins d'une milliseconde, sans réseau ni accès au corps, à 0,10 $ le million d'appels. Lambda@Edge (Node ou Python) peut appeler une API ou lire le corps, mais coûte 0,60 $ le million plus la durée et se déploie depuis `us-east-1`.
- Usage : ✅ routes profondes d'une SPA, redirection, en-tête calculé · ❌ appel réseau, lecture du corps, traitement long : Lambda@Edge.

```hcl
# Exemple 1 : /cours/python → /index.html
resource "aws_cloudfront_function" "spa" {
  name    = "spa-rewrite"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-JS
    function handler(event) {
      var r = event.request;
      // pas d'extension : route de l'app
      if (r.uri.indexOf(".") === -1) {
        r.uri = "/index.html";
      }
      return r;
    }
  JS
}
```

```hcl
# Exemple 2 : sur le seul comportement par défaut
default_cache_behavior {
  function_association {
    event_type   = "viewer-request"
    function_arn = aws_cloudfront_function.spa.arn
  }
}
# /content/* garde ses vraies 404
```

- Quiz : En `viewer-request`, la fonction s'exécute-t-elle quand l'objet est déjà en cache dans le point de présence ?
- [ ] Non, seulement sur un miss de cache
- [x] Oui, à chaque requête, avant la lecture du cache
- [ ] Seulement à la première requête du point de présence
- [ ] Seulement si le TTL vaut 0
- Réponse : oui, à chaque requête : `viewer-request` passe avant le cache ; seuls les événements `origin-*` (Lambda@Edge) attendent un miss.
