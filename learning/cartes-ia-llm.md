---
title: "Cartes · LLM"
type: cartes
langage: IA
cours: LLM
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · LLM
IA · LLM : appel, bedrock, coûts, production (format spec v3 de revision-pwa).

## 1. Bedrock : un LLM derrière une API AWS
- Sous-thème : bedrock
- Niveau : 1
- Définition : Bedrock expose des modèles de plusieurs fournisseurs derrière l'API AWS `bedrock-runtime` : pas de GPU à gérer, facturation au token, accès par IAM.
- Contexte : On appelle un modèle comme n'importe quel service AWS : SDK ou CLI, signature SigV4, rôle IAM de la Lambda, aucune clé d'API du fournisseur. Deux plans distincts : `bedrock` (lister les modèles, créer des jobs) et `bedrock-runtime` (inférer). L'ID du modèle change à chaque version : le garder en variable Terraform, jamais en dur dans le code.
- Usage : ✅ LLM dans un pipeline AWS (Lambda, Step Functions) avec IAM, VPC et CloudTrail déjà en place · ❌ besoin d'un modèle absent du catalogue Bedrock : API du fournisseur, avec gestion de la clé.

```bash
# Exemple 1 : un appel Converse en CLI
aws bedrock-runtime converse \
  --model-id "$MODEL_ID" \
  --messages '[{"role":"user",
    "content":[{"text":
    "Résume : RJ de SAS ALPHA"}]}]'
# → {"output":{"message":{...}},
#    "stopReason":"end_turn",
#    "usage":{"inputTokens":21,...}}
```

```bash
# Exemple 2 : lister les modèles (lecture)
aws bedrock list-foundation-models \
  --region eu-west-3 \
  --by-output-modality TEXT \
  --query 'modelSummaries[].modelId'
# plan de contrôle : client "bedrock"
# inférence : client "bedrock-runtime"
```

- Quiz : La Lambda reçoit `AccessDeniedException` sur `Converse` : quelle action IAM manque à son rôle ?
- [ ] `bedrock:Converse`
- [ ] `bedrock-runtime:Converse`
- [x] `bedrock:InvokeModel`
- [ ] `bedrock:InvokeAgent`
- Réponse : `bedrock:InvokeModel` : Converse n'a pas d'action IAM propre, il réutilise celle d'InvokeModel (`InvokeModelWithResponseStream` pour ConverseStream).

## 2. Profil d'inférence : le préfixe de l'ID
- Sous-thème : bedrock
- Niveau : 1
- Définition : Un profil d'inférence interrégional (`eu.`, `us.`, `apac.`, `global.`) devant l'ID du modèle répartit les appels entre plusieurs régions.
- Contexte : Les modèles récents ne s'appellent souvent à la demande que via un profil : l'ID de base seul est refusé. La requête part de la région source (celle du client) et Bedrock la route vers une région de destination du profil, selon la charge. Le profil fait gagner du débit ; il ne coûte pas plus cher que la région source, mais change l'endroit où la donnée est traitée.
- Usage : ✅ appels à la demande d'un modèle récent, absorber les pics de charge · ❌ contrainte stricte de résidence sans vérifier les régions de destination du profil.

```bash
# Exemple 1 : deux façons de nommer
# modèle de base (région de l'appel)
anthropic.claude-<version>
# profil interrégional Europe
eu.anthropic.claude-<version>

# lister les profils (lecture seule)
aws bedrock list-inference-profiles \
  --region eu-west-3 \
  --type-equals SYSTEM_DEFINED \
  --query 'inferenceProfileSummaries[].inferenceProfileId'
```

- Quiz : Que renvoie `Converse` avec l'ID de base d'un modèle servi seulement via profil, sans débit provisionné ?
- [x] `ValidationException`
- [ ] `ThrottlingException`
- [ ] `AccessDeniedException`
- [ ] Une réponse, traitée dans la région de l'appel
- Réponse : `ValidationException` (« on-demand throughput isn't supported ») : ce modèle ne s'appelle à la demande qu'avec l'ID d'un profil d'inférence.

## 3. Données : où le prompt est traité
- Sous-thème : bedrock
- Niveau : 1
- Définition : Bedrock n'utilise pas les prompts pour entraîner les modèles ; la région de traitement dépend de l'ID ou du profil appelé.
- Contexte : Un ID de base reste dans la région de l'appel ; un profil géographique (`eu.`) reste dans sa zone ; `global.` peut aller dans toute région commerciale. La liste des destinations peut dépendre de la région source : la doc AWS demande de la vérifier avec `GetInferenceProfile` plutôt que de se fier au préfixe. Pour des données BODACC nominatives (dirigeants, RGPD), on choisit `eu.` au minimum.
- Usage : ✅ choisir le profil d'après la contrainte de résidence, vérifier ses destinations depuis chaque région source · ❌ `global.` pour des données personnelles soumises à une contrainte UE.

```python
# Exemple 1 : préfixe → zone de traitement
zone = {"": "région de l'appel",
        "eu.": "régions UE du profil",
        "global.": "toute région"}

def prefixe(model_id):
    p = model_id.split(".")[0] + "."
    return p if p in zone else ""

zone[prefixe("eu.anthropic.x")]
# → "régions UE du profil"
zone[prefixe("anthropic.x")]
# → "région de l'appel"
```

```bash
# Exemple 2 : les vraies destinations
aws bedrock get-inference-profile \
  --region eu-west-3 \
  --inference-profile-identifier \
    "$PROFILE_ID" \
  --query 'models[].modelArn'
# une région par ARN de modèle
```

- Quiz : Une SCP n'autorise Bedrock qu'en `eu-west-3` ; la Lambda de Paris appelle un profil `eu.` : résultat ?
- [ ] Succès, traité uniquement à Paris
- [x] Échec, une destination du profil est bloquée
- [ ] Succès, routé vers une région UE autorisée
- [ ] Succès, la SCP ne s'applique pas aux profils
- Réponse : Échec : selon la doc, si une région de destination du profil est bloquée par une SCP, la requête échoue même si d'autres restent permises.

## 4. Converse : lire la réponse
- Sous-thème : appel
- Niveau : 1
- Définition : `Converse` est l'API unifiée de Bedrock : mêmes `messages` en entrée et même enveloppe de réponse, quel que soit le modèle appelé.
- Contexte : Changer de modèle ne change pas le code de lecture : la réponse a toujours `output.message.content` (liste de blocs), `stopReason`, `usage` et `metrics`. Le contenu est une liste, pas une chaîne : un bloc peut être du texte, un appel d'outil (`toolUse`) ou autre. Lire `content[0]["text"]` sans vérifier le type de bloc casse dès que le modèle appelle un outil.
- Usage : ✅ tout appel texte, pour pouvoir changer de modèle sans réécrire le parsing · ❌ paramètre propre à un modèle absent de Converse : `additionalModelRequestFields`, ou `InvokeModel` au format natif.

```python
# Exemple 1 : réponse Converse (simulée)
resp = {"output": {"message": {
    "role": "assistant",
    "content": [{"text": "RJ ouvert"}]}},
  "stopReason": "end_turn",
  "usage": {"inputTokens": 21,
            "outputTokens": 3}}
msg = resp["output"]["message"]
msg["content"][0]["text"]  # → "RJ ouvert"
resp["usage"]["outputTokens"]  # → 3
```

```python
# Exemple 2 : ne lire que les blocs texte
content = [
    {"text": "Je cherche."},
    {"toolUse": {"name": "lookup",
                 "input": {"siren": "1"}}},
]
textes = [b["text"] for b in content
          if "text" in b]
textes         # → ["Je cherche."]
content[1]["text"]  # ❌ KeyError
```

- Quiz : Où va la consigne système dans un appel `Converse` ?
- [ ] Un message `{"role": "system"}` en tête de `messages`
- [x] Le paramètre séparé `system=[{"text": …}]`
- [ ] Le champ `inferenceConfig.system`
- [ ] Un message `user` qui commence par « Système : »
- Réponse : Le paramètre `system` : `messages` n'accepte que les rôles `user` et `assistant` ; un rôle `system` y est refusé (`ValidationException`).

## 5. stopReason : la réponse tronquée
- Sous-thème : appel
- Niveau : 1
- Définition : `stopReason` dit pourquoi le modèle s'est arrêté ; `"max_tokens"` signifie que `inferenceConfig.maxTokens` a coupé la réponse en cours.
- Contexte : Les valeurs utiles : `end_turn` (fin normale), `max_tokens` (plafond atteint), `tool_use` (le modèle veut un outil), `stop_sequence`, `guardrail_intervened`, `content_filtered`. Une sortie coupée a l'air normale : seul `stopReason` le dit. Dans un pipeline, on le teste avant tout parsing, et on journalise la valeur pour savoir s'il faut monter `maxTokens` ou raccourcir la demande.
- Usage : ✅ tester `stopReason` à chaque appel de pipeline, avant de lire le contenu · ❌ se fier à la longueur ou à l'aspect du texte pour détecter une coupure.

```python
# Exemple 1 : refuser une sortie coupée
import json

resp = {"stopReason": "max_tokens",
        "text": '{"siren": "4836'}

def lire(r):
    if r["stopReason"] != "end_turn":
        raise RuntimeError(r["stopReason"])
    return json.loads(r["text"])

lire(resp)       # ❌ RuntimeError
```

```json
# Exemple 2 : plafonner la sortie
{"inferenceConfig": {
   "maxTokens": 300
 }}
// réponse si le plafond est atteint :
// "stopReason": "max_tokens"
// "usage": {"outputTokens": 300}
```

- Quiz : Sans le test sur `stopReason`, que ferait `json.loads('{"siren": "4836')` ?
- [ ] Renvoie `{"siren": "4836"}`
- [ ] Renvoie `None`
- [x] `JSONDecodeError`
- [ ] Renvoie `{}`
- Réponse : `JSONDecodeError` : une erreur de parsing qui masque la vraie cause ; tester `stopReason` d'abord donne le bon diagnostic.

## 6. temperature : extraire ou rédiger
- Sous-thème : appel
- Niveau : 1
- Définition : `inferenceConfig.temperature` règle le hasard du choix des tokens : proche de 0 pour extraire ou classer, plus haute pour rédiger.
- Contexte : À chaque token, le modèle a une distribution de probabilités ; une température basse la resserre sur le plus probable, une haute laisse passer des choix moins attendus. Pour une extraction BODACC, on veut la même réponse pour la même annonce : température 0. On règle `temperature` ou `topP`, rarement les deux : certains modèles refusent les deux à la fois.
- Usage : ✅ 0 pour extraction, classification, JSON ; 0,5 à 0,8 pour résumé ou rédaction · ❌ monter la température pour « corriger » une mauvaise extraction : revoir le prompt.

```json
# Exemple 1 : extraction, température 0
{"inferenceConfig": {
   "maxTokens": 300,
   "temperature": 0
 },
 "system": [{"text":
   "Classe : vente ou procol."}]}
// extraction → 0
// résumé rédigé → 0.5 à 0.7
```

- Quiz : Avec `temperature: 0`, deux appels identiques renvoient-ils toujours exactement le même texte ?
- [ ] Oui, c'est garanti par l'API
- [ ] Oui, si `maxTokens` est identique
- [ ] Non, seulement avec `topP: 1`
- [x] Non, ce n'est pas garanti
- Réponse : Non, pas garanti : le service n'est pas strictement déterministe ; un pipeline rejouable met en cache les réponses par empreinte.

## 7. Coût : estimer un run avant de le lancer
- Sous-thème : coûts
- Niveau : 1
- Définition : Coût = tokens d'entrée × prix d'entrée + tokens de sortie × prix de sortie, estimé sur le vrai volume quotidien avant de lancer.
- Contexte : Le fournisseur facture séparément entrée et sortie, et renvoie les deux comptes dans la réponse (`usage` chez Bedrock). La sortie coûte en général plusieurs fois plus cher par token, mais l'entrée se répète à chaque appel : consignes et exemples sont payés sur chaque annonce. Les prix changent : on les garde en configuration et on mesure les tokens sur un échantillon réel.
- Usage : ✅ chiffrer un run avant de le lancer, comparer deux prompts ou deux modèles · ❌ extrapoler depuis une annonce courte de fixture : mesurer sur une vraie journée.

```python
# Exemple 1 : une journée de BODACC
annonces = 32_000
tok_in, tok_out = 600, 80
prix_in = 3 / 1e6     # $/token (fictif)
prix_out = 15 / 1e6
cout = annonces * (tok_in * prix_in
                   + tok_out * prix_out)
round(cout, 2)   # → 96.0
```

```python
# Exemple 2 : un appel, la sortie pèse
usage = {"inputTokens": 1200,
         "outputTokens": 300}
c_in = usage["inputTokens"] * 3 / 1e6
c_out = usage["outputTokens"] * 15 / 1e6
round(c_in, 4), round(c_out, 4)
# → (0.0036, 0.0045)
c_out > c_in     # → True  (4× moins de tokens)
```

- Quiz : Exemple 1 : on ajoute 20 exemples au prompt (+1 400 tokens d'entrée) ; le coût journalier devient environ ?
- [ ] 96 $, l'entrée coûte peu
- [ ] 110 $
- [x] 230 $
- [ ] 1 400 $
- Réponse : Environ 230 $ (×2,4) : l'entrée passe de 600 à 2 000 tokens, payés sur chacune des 32 000 annonces.

## 8. Règles d'abord : LLM en repli
- Sous-thème : coûts
- Niveau : 1
- Définition : On traite par règles (regex, champs structurés) tout ce qui est sûr, et on n'envoie au LLM que le reste.
- Contexte : Une regex coûte zéro, répond en microsecondes et donne toujours le même résultat ; un appel LLM coûte, prend des secondes et varie. Le LLM sert de repli pour la longue traîne des formats imprévus. On trace la voie utilisée (`regle` ou `llm`) par enregistrement : on mesure ainsi la part de chaque voie et on repère les règles à ajouter.
- Usage : ✅ champ au format régulier (SIREN, date, code postal), LLM pour le texte ambigu · ❌ envoyer tout au LLM « pour simplifier » ; empiler des regex fragiles sur du texte vraiment libre.

```python
# Exemple 1 : la règle trouve, ou rend None
import re

def siren(texte):
    m = re.search(
        r"\b\d{3} ?\d{3} ?\d{3}\b", texte)
    return m and m.group().replace(" ", "")

siren("RCS Lyon 483 609 327")
# → "483609327"
siren("RCS en cours") is None   # → True
```

```python
# Exemple 2 : tracer la voie utilisée
import re

def extraire(texte):
    m = re.search(r"\b\d{9}\b", texte)
    if m:
        return m.group(), "regle"
    return None, "llm"   # à envoyer

extraire("RCS 483609327")
# → ("483609327", "regle")
extraire("SIREN illisible")[1]  # → "llm"
```

- Quiz : Sur 32 000 annonces, la regex en résout 31 000 : combien d'appels LLM, et quel risque reste ?
- [x] 1 000 ; la regex peut se tromper sans le dire
- [ ] 1 000 ; aucun, la regex est déterministe
- [ ] 32 000 ; il faut confirmer la regex
- [ ] 31 000 ; le LLM vérifie chaque règle
- Réponse : 1 000 appels : mais une regex déterministe peut quand même produire des faux positifs ; on la mesure aussi sur une journée complète.

## 9. Lambda : un timeout pour le LLM
- Sous-thème : production
- Niveau : 2
- Définition : Une Lambda qui appelle un LLM attend souvent plusieurs secondes : son `timeout` doit couvrir l'appel, ses retries et la marge.
- Contexte : Le timeout se règle par fonction, de 1 s à 900 s. Un appel LLM dure de une à plusieurs dizaines de secondes selon la longueur de sortie. Le client boto3 a aussi son propre `read_timeout` (60 s par défaut) : s'il dépasse le timeout Lambda, c'est la Lambda qui coupe, sans exception attrapable. On aligne donc les deux, et on facture la durée réelle.
- Usage : ✅ timeout ≥ durée d'appel × tentatives, mesuré sur de vraies annonces · ❌ appels longs en chaîne dans une seule Lambda : Step Functions ou inférence par lot.

```hcl
# Exemple 1 : timeout explicite (Terraform)
resource "aws_lambda_function" "resume" {
  function_name = "bodacc-resume"
  runtime       = "python3.12"
  handler       = "app.handler"
  timeout       = 60    # secondes
  memory_size   = 512
  role          = aws_iam_role.resume.arn
  filename      = "build/resume.zip"
}
```

```python
# Exemple 2 : le budget de temps
appel_s = 8          # mesuré (p99)
tentatives = 3
marge_s = 10
budget = appel_s * tentatives + marge_s
budget             # → 34
budget <= 60       # → True
```

- Quiz : Sans la ligne `timeout`, au bout de combien de temps la Lambda est-elle coupée pendant l'appel Bedrock ?
- [ ] 60 s
- [ ] 15 min
- [x] 3 s
- [ ] 30 s
- Réponse : 3 s : c'est le timeout par défaut d'une Lambda (`Task timed out after 3.00 seconds`), bien trop court pour un LLM.

## 10. ThrottlingException : retenter avec jitter
- Sous-thème : production
- Niveau : 2
- Définition : Bedrock limite requêtes et tokens par minute ; au-delà, `ThrottlingException`, à retenter avec un délai croissant et aléatoire (backoff exponentiel avec jitter).
- Contexte : Les quotas sont par compte, région et modèle (RPM, TPM ; RPM seul pour les modèles d'embedding). On ne retente que le transitoire : `ThrottlingException`, `ServiceUnavailableException`, `InternalServerException`, `ModelTimeoutException`. Une `ValidationException` ou `AccessDeniedException` échouera pareil : la retenter ne fait que consommer du quota. boto3 sait retenter seul via `Config(retries={"mode": "adaptive"})`.
- Usage : ✅ appels à la demande en parallèle (fan-out Lambda, SQS) · ❌ gros volume sans besoin de temps réel : inférence par lot, hors quotas à la demande.

```python
# Exemple 1 : délais croissants, aléatoires
import random

def delais(n, base=1, cap=20, seed=0):
    random.seed(seed)
    return [random.uniform(
                0, min(cap, base * 2 ** i))
            for i in range(n)]

d = delais(5)
len(d), max(d) <= 16   # → (5, True)
```

```python
# Exemple 2 : retenter ou abandonner
TRANSITOIRES = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "InternalServerException",
    "ModelTimeoutException"}

def retenter(code):
    return code in TRANSITOIRES

retenter("ThrottlingException")  # → True
retenter("ValidationException")  # → False
```

- Quiz : 50 Lambdas throttlées retentent toutes après exactement 1 s, 2 s puis 4 s, sans aléa : que se passe-t-il ?
- [ ] Elles réussissent, l'attente suffit
- [x] Elles retombent ensemble en throttling
- [ ] Bedrock les met en file d'attente
- [ ] Les retries ne comptent pas dans le quota
- Réponse : Elles retombent ensemble en throttling : des délais identiques resynchronisent les appels ; le jitter les étale dans le temps.

## 11. Guardrails : filtrer entrée et sortie
- Sous-thème : production
- Niveau : 2
- Définition : Un guardrail Bedrock filtre sujets interdits, contenus et données personnelles, sur le prompt comme sur la réponse du modèle.
- Contexte : On crée le guardrail (politiques, version) puis on le référence dans l'appel `Converse` via `guardrailConfig`. S'il bloque, la réponse arrive quand même, avec `stopReason: "guardrail_intervened"` et le message configuré : pas d'exception. `ApplyGuardrail` évalue un texte sans appeler de modèle. Il s'ajoute à l'appel : coût et latence en plus, facturés à part.
- Usage : ✅ application exposée à des utilisateurs, masquage de PII en sortie · ❌ seule protection des données : minimiser en amont ; seule défense contre l'injection : valider la sortie.

```json
# Exemple 1 : guardrail dans Converse
{"guardrailConfig": {
   "guardrailIdentifier": "gr-bodacc",
   "guardrailVersion": "1"
 }}
// réponse si bloqué :
// "stopReason": "guardrail_intervened"
```

```python
# Exemple 2 : un refus n'est pas une réponse
resp = {"stopReason":
          "guardrail_intervened",
        "text": "Contenu bloqué."}

def utile(r):
    return r["stopReason"] == "end_turn"

utile(resp)    # → False
```

- Quiz : Un guardrail masque les noms de dirigeants : dispense-t-il de minimiser les données avant l'appel ?
- [ ] Oui, il filtre avant l'envoi au modèle
- [ ] Oui, si le guardrail est versionné
- [x] Non, le prompt est déjà parti vers Bedrock
- Réponse : Non : le prompt est déjà envoyé à Bedrock quand le guardrail l'évalue ; la minimisation se fait en amont, dans le pipeline.

## 12. Cache par empreinte : payer une fois
- Sous-thème : coûts
- Niveau : 2
- Définition : La clé de cache est un hash de toutes les entrées de l'appel LLM ; un rejeu relit le résultat au lieu de repayer.
- Contexte : Un pipeline data se rejoue souvent : correction d'un bug en aval, backfill, reprise après échec. Sans cache, chaque rejeu repaie tous les appels et peut donner des réponses différentes. La clé (SHA-256 du modèle, de la version du prompt, des paramètres et du texte) pointe vers la réponse stockée, par exemple dans S3 sous `cache/<clé>.json`.
- Usage : ✅ backfills, rejeux, mise au point en aval sans repayer l'amont · ❌ clé partielle (texte seul) : un changement de prompt servirait d'anciennes réponses.

```python
# Exemple 1 : même entrée, même clé
import hashlib

def cle(modele, prompt_v, texte):
    s = f"{modele}|{prompt_v}|{texte}"
    return hashlib.sha256(
        s.encode()).hexdigest()[:12]

k1 = cle("m1", "v1", "SAS ALPHA")
k1 == cle("m1", "v1", "SAS ALPHA")
# → True
k1 == cle("m1", "v2", "SAS ALPHA")
# → False
```

- Quiz : Si la clé ne hache que `texte`, que se passe-t-il quand on passe le prompt en `v2` ?
- [ ] Le cache est vidé automatiquement
- [x] Le cache sert les réponses `v1`
- [ ] Chaque appel repasse au LLM
- [ ] `KeyError` sur les anciennes clés
- Réponse : Le cache sert les réponses `v1` : toute entrée qui change le résultat (modèle, prompt, paramètres) doit entrer dans la clé.

## 13. Prompt caching : un préfixe stable
- Sous-thème : production
- Niveau : 3
- Définition : Un `cachePoint` marque la fin d'un préfixe à mettre en cache ; les appels qui partagent ce préfixe le relisent moins cher et plus vite.
- Contexte : Le cache porte sur un préfixe identique, traité dans l'ordre `tools` → `system` → `messages` : tout ce qui varie va après le `cachePoint`. Durée de vie de 5 minutes (1 h sur certains modèles), prolongée à chaque lecture. L'écriture en cache peut coûter plus qu'une entrée normale, la lecture beaucoup moins. Avec cache, `inputTokens` ne compte que la part non cachée. Non supporté en inférence par lot.
- Usage : ✅ mêmes longues règles d'extraction envoyées à chaque annonce, à la demande · ❌ préfixe qui change à chaque appel, appels espacés de plus que le TTL.

```json
# Exemple 1 : règles fixes en cache
{"system": [
   {"text": "Règles d'extraction BODACC
     (2 000 tokens, identiques)"},
   {"cachePoint": {"type": "default"}}
 ],
 "messages": [{"role": "user",
   "content": [{"text":
     "<annonce>SAS ALPHA…</annonce>"}]}]}
```

```python
# Exemple 2 : total d'entrée avec cache
usage = {"inputTokens": 150,
         "cacheReadInputTokens": 2000,
         "cacheWriteInputTokens": 0}
# inputTokens = part non cachée seule
total = sum(usage.values())
total          # → 2150
```

- Quiz : Le préfixe fixe fait moins de tokens que le minimum du modèle : que fait l'appel avec `cachePoint` ?
- [x] Il réussit, sans rien mettre en cache
- [ ] `ValidationException`
- [ ] Il met en cache quand même
- [ ] Il complète le préfixe jusqu'au minimum
- Réponse : Il réussit sans cache : sous le minimum de tokens par point de cache (selon le modèle), l'inférence marche mais le préfixe n'est pas caché.

## 14. Inférence par lot : -50 % en différé
- Sous-thème : production
- Niveau : 3
- Définition : L'inférence par lot lit un JSONL de requêtes dans S3 et écrit les réponses dans S3, en asynchrone, à prix réduit.
- Contexte : La page de prix Bedrock annonce l'inférence par lot 50 % moins chère que la demande, pour les modèles éligibles. Chaque ligne porte un `recordId` et un `modelInput` ; le job tourne sous un rôle de service qui lit et écrit les préfixes S3. Résultat en minutes ou heures, pas en secondes. Avec le format Converse, pas d'appel d'outil (`toolConfig` → erreur 400) ; la sortie structurée, elle, est supportée.
- Usage : ✅ classer chaque nuit les ~32 000 annonces de la veille, réindexer un corpus · ❌ réponse attendue par un utilisateur ou une API : appel à la demande.

```bash
# Exemple 1 : lancer un job de lot
# s3://lake/ia/in/2026-10-23.jsonl
# {"recordId":"a1","modelInput":{...}}
aws bedrock create-model-invocation-job \
  --job-name bodacc-2026-10-23 \
  --model-id "$MODEL_ID" \
  --role-arn "$ROLE_ARN" \
  --input-data-config \
'{"s3InputDataConfig":{"s3Uri":"s3://lake/ia/in/"}}' \
  --output-data-config \
'{"s3OutputDataConfig":{"s3Uri":"s3://lake/ia/out/"}}'
```

```python
# Exemple 2 : une ligne du JSONL d'entrée
import json

ligne = {"recordId": "a1",
         "modelInput": {"messages": [
             {"role": "user", "content":
              [{"text": "SAS ALPHA…"}]}]}}
s = json.dumps(ligne)
"\n" in s       # → False  (1 ligne)
```

- Quiz : Les requêtes du JSONL de lot portent un `cachePoint` : l'économie du cache s'ajoute-t-elle aux -50 % ?
- [ ] Oui, les deux se cumulent
- [ ] Oui, mais seulement sur `system`
- [x] Non, pas de prompt caching en lot
- [ ] Non, le job échoue à cause du `cachePoint`
- Réponse : Non : selon la doc, le prompt caching n'est supporté qu'en inférence à la demande, pas avec l'API d'inférence par lot.
