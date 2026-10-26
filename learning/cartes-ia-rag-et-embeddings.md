---
title: "Cartes · RAG et embeddings"
type: cartes
langage: IA
chapitre: Applications
cours: RAG et embeddings
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · RAG et embeddings
IA · RAG et embeddings : embeddings, rag, recherche (format spec v3 de revision-pwa).

## 1. Embedding : la similarité cosinus
- Id : rag-et-embeddings-similarite-cosinus
- Sous-thème : embeddings
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : rag-et-embeddings-vecteurs-normes-produit-scalaire
- Mots-clés : recherche sémantique
- Définition : Un modèle d'embedding transforme un texte en vecteur de floats, proches quand les sens sont proches ; le cosinus mesure cette proximité.
- Contexte : Le cosinus vaut 1 pour deux vecteurs de même direction, 0 pour des vecteurs orthogonaux, -1 pour des opposés. Il compare le sens, pas les mots : « redressement judiciaire » et « procédure collective » sont proches sans mot commun. Les vrais vecteurs ont des centaines de dimensions ; le calcul est le même qu'en 3 dimensions.
- Usage : ✅ recherche sémantique, regroupement d'annonces, dédoublonnage approximatif · ❌ correspondance exacte (SIREN, code) : égalité ou index classique.

```python
# Exemple 1 : proches ou éloignés
import math

def cos(a, b):
    d = sum(x * y for x, y in zip(a, b))
    return d / (math.hypot(*a)
                * math.hypot(*b))

redress = [0.9, 0.1, 0.0]
procol  = [0.8, 0.2, 0.1]
vente   = [0.0, 0.2, 0.9]
cos(redress, procol) > cos(redress, vente)
# → True
```

```python
# Exemple 2 : orthogonaux et opposés
import math

def cos(a, b):
    d = sum(x * y for x, y in zip(a, b))
    return d / (math.hypot(*a)
                * math.hypot(*b))

cos([1, 0], [0, 1])    # → 0.0
cos([1, 0], [-1, 0])   # → -1.0
```

- Quiz : Que vaut `cos([1, 0], [2, 0])` ?
- [ ] `2.0`
- [ ] `0.5`
- [x] `1.0`
- [ ] `0.0`
- Réponse : `1.0` : le cosinus mesure l'angle, pas la longueur ; deux vecteurs de même direction ont un score de 1 quelle que soit leur norme.

## 2. Chunking : découper avec chevauchement
- Id : rag-et-embeddings-chunking-chevauchement
- Sous-thème : indexation
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Voir aussi : rag-et-embeddings-rag-contexte-puis-question
- Mots-clés : embedding, token
- Définition : On découpe un long texte en morceaux de taille fixe qui se chevauchent, pour qu'une phrase coupée reste entière dans au moins un morceau.
- Contexte : Un embedding résume tout un morceau : trop long, il dilue le sens ; trop court, il perd le contexte. Le chevauchement évite qu'une information à cheval sur deux morceaux soit perdue. En vrai, on compte en tokens et on coupe de préférence aux frontières de phrase ou de paragraphe ; une annonce BODACC courte tient souvent en un seul morceau.
- Usage : ✅ documents longs à indexer (jugements, actes) · ❌ textes courts (une annonce) : un morceau par document ; coupe en plein mot sans chevauchement.

```python
# Exemple 1 : taille 4, recouvrement 1
def chunks(texte, taille, recouv):
    pas = taille - recouv
    return [texte[i:i + taille]
            for i in range(0, len(texte),
                           pas)]

chunks("ABCDEFGH", 4, 1)
# → ["ABCD", "DEFG", "GH"]
chunks("ABCDEFGH", 4, 0)
# → ["ABCD", "EFGH"]
```

- Quiz : Avec la fonction de l'exemple, que fait `chunks("ABCDEFGH", 4, 4)` ?
- [ ] Boucle infinie
- [ ] `["ABCD", "EFGH"]`
- [x] `ValueError`
- [ ] `[]`
- Réponse : `ValueError` : `pas` vaut 0 et `range` refuse un pas nul ; le recouvrement doit rester strictement inférieur à la taille.

## 3. Embeddings Titan V2 : un texte → un vecteur
- Id : rag-et-embeddings-titan-v2-vecteur
- Sous-thème : embeddings
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : rag-et-embeddings-similarite-cosinus, llm-bedrock-api-aws
- Mots-clés : embedding, InvokeModel, Converse, token
- Définition : Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`) transforme un texte en vecteur de 1024, 512 ou 256 floats, via `InvokeModel`.
- Contexte : Pas de Converse ici : `InvokeModel` avec un corps propre au modèle. 1024 dimensions par défaut ; moins de dimensions = index plus léger, précision un peu moindre. Entrée jusqu'à 8 192 tokens, mais la doc conseille de découper par paragraphe. Optimisé pour l'anglais, le français est en support multilingue (preview). Le quota est en requêtes par minute, pas en tokens.
- Usage : ✅ indexer des annonces pour la recherche sémantique ou une Knowledge Base · ❌ comparer des vecteurs issus de modèles ou de dimensions différents.

```json
# Exemple 1 : requête et réponse
// InvokeModel
// modelId: amazon.titan-embed-text-v2:0
{"inputText": "RJ de SAS ALPHA",
 "dimensions": 512,
 "normalize": true}

// réponse
{"embedding": [0.031, -0.12, ...],
 "inputTextTokenCount": 8}
```

- Quiz : On réindexe en passant de `dimensions: 1024` à `512` : que deviennent les anciens vecteurs de l'index ?
- [ ] Comparables, la norme est identique
- [ ] Tronqués automatiquement à 512
- [ ] Comparables si `normalize` vaut `true`
- [x] Inutilisables, tout réindexer
- Réponse : Inutilisables : dimensions différentes, l'index refuse ou compare n'importe quoi ; changer de dimension ou de modèle impose de tout réindexer.

## 4. Recherche top-k : garder les k meilleurs
- Id : rag-et-embeddings-recherche-top-k
- Sous-thème : recherche
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : rag-et-embeddings-similarite-cosinus, rag-et-embeddings-titan-v2-vecteur
- Mots-clés : base vectorielle, ANN, RAG
- Définition : La recherche sémantique note chaque morceau par similarité avec la question et ne garde que les k meilleurs pour le prompt.
- Contexte : k règle le compromis : trop petit, on rate l'info ; trop grand, le prompt coûte cher et noie la réponse. Une base vectorielle fait ce tri sur des millions de vecteurs avec un index approximatif (ANN), plus rapide mais pas toujours exact. Un top-k renvoie toujours k résultats, même hors sujet : d'où un seuil de score en plus.
- Usage : ✅ choisir le contexte d'un RAG, suggérer des annonces proches · ❌ k fixe sans seuil de score sur un corpus où la question peut n'avoir aucune réponse.

```python
# Exemple 1 : les 2 meilleurs scores
import heapq

scores = {"ouverture RJ": 0.91,
          "cession fonds": 0.42,
          "plan de RJ": 0.87,
          "radiation": 0.15}
heapq.nlargest(2, scores,
               key=scores.get)
# → ["ouverture RJ", "plan de RJ"]
```

- Quiz : Aucun document ne parle du sujet demandé : que renvoie un top-k (k = 3) sans seuil ?
- [ ] Une liste vide
- [x] Les 3 moins mauvais, hors sujet
- [ ] `None`
- [ ] Une erreur « aucun résultat »
- Réponse : Les 3 moins mauvais : un top-k renvoie toujours k résultats ; sans seuil minimal, le LLM reçoit du contexte hors sujet.

## 5. RAG : contexte puis question
- Id : rag-et-embeddings-rag-contexte-puis-question
- Sous-thème : rag
- Type : concept
- Niveau : 2
- Profils : data, web
- Prérequis : rag-et-embeddings-recherche-top-k, rag-et-embeddings-chunking-chevauchement
- Voir aussi : rag-et-embeddings-knowledge-base-managee
- Mots-clés : top-k, prompt, LLM
- Définition : Le RAG injecte les passages retrouvés dans le prompt, et le modèle répond à partir d'eux plutôt que de sa mémoire.
- Contexte : Le modèle ne connaît pas les annonces d'hier : sa mémoire s'arrête à son entraînement. Le RAG = recherche (top-k) + prompt qui contient les passages, balisés et datés, avec une consigne « réponds avec ces seules sources ». La qualité dépend surtout de la recherche : un passage absent ou périmé donne une réponse fausse mais sûre d'elle.
- Usage : ✅ questions sur des données fraîches ou privées (statut d'un SIREN) · ❌ calcul exact ou agrégat (combien de RJ hier) : requête SQL, pas RAG.

```python
# Exemple 1 : assembler le prompt
passages = ["483609327 : RJ le 2026-10-05",
            "483609327 : plan le 2026-10-20"]
question = "Statut actuel du 483609327 ?"
prompt = ("Réponds avec ces seules sources.\n"
          + "\n".join(f"<doc>{p}</doc>"
                      for p in passages)
          + f"\nQuestion : {question}")
prompt.count("<doc>")   # → 2
```

- Quiz : L'annonce du 2026-10-20 (plan adopté) n'est pas encore indexée : que risque la réponse ?
- [ ] Rien, le modèle connaît l'annonce
- [ ] Une erreur, il manque un document
- [x] Fausse mais sourcée : « en RJ »
- [ ] Une réponse vide, faute de contexte
- Réponse : Fausse mais sourcée (« en RJ ») : le RAG est aussi frais que son index ; la réindexation fait partie du pipeline.

## 6. Knowledge Base : le RAG managé
- Id : rag-et-embeddings-knowledge-base-managee
- Sous-thème : rag
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : rag-et-embeddings-rag-contexte-puis-question
- Voir aussi : rag-et-embeddings-store-vectoriel-cout-au-repos
- Mots-clés : RAG, chunking, embedding, base vectorielle
- Définition : Une Knowledge Base découpe, vectorise et indexe les documents d'une source (bucket S3), puis `RetrieveAndGenerate` cherche et répond en citant ses sources.
- Contexte : Bedrock gère le chunking, l'appel au modèle d'embedding, l'écriture dans le store vectoriel et l'assemblage du prompt. `Retrieve` seul renvoie les passages (on garde la main sur le prompt) ; `RetrieveAndGenerate` fait tout et renvoie des `citations`. On paie l'embedding, la génération et le store vectoriel, qui tourne en continu selon le type choisi.
- Usage : ✅ question-réponse sur un corpus de documents qui évolue lentement, avec citations · ❌ besoin de contrôler finement chunking et prompt : `Retrieve`, ou un RAG écrit à la main.

```bash
# Exemple 1 : question à la KB
aws bedrock-agent-runtime \
  retrieve-and-generate \
  --input '{"text":
    "Statut du SIREN 483609327 ?"}' \
  --retrieve-and-generate-configuration \
  '{"type":"KNOWLEDGE_BASE",
    "knowledgeBaseConfiguration":{
      "knowledgeBaseId":"KB123",
      "modelArn":"<arn-modèle>"}}'
# → {"output":{"text":"..."},
#    "citations":[...]}
```

- Quiz : On dépose un nouveau fichier dans le bucket source : quand la KB le trouve-t-elle ?
- [ ] Tout de suite, via un événement S3
- [x] Après une synchronisation (`StartIngestionJob`)
- [ ] Au prochain `RetrieveAndGenerate`
- [ ] Après un redémarrage de la KB
- Réponse : Après une synchronisation (`StartIngestionJob`) : sans elle, l'index ignore le fichier et la réponse reste ancienne.

## 7. Store vectoriel : le coût au repos
- Id : rag-et-embeddings-store-vectoriel-cout-au-repos
- Sous-thème : indexation
- Type : piège
- Niveau : 2
- Profils : data, ops
- Voir aussi : rag-et-embeddings-knowledge-base-managee
- Mots-clés : Knowledge Base, OpenSearch Serverless, S3
- Définition : Les vecteurs d'une Knowledge Base vivent dans un store dédié (S3 Vectors, OpenSearch Serverless, Aurora pgvector…), dont le modèle de prix pèse lourd.
- Contexte : Le store se choisit à la création de la KB : en changer impose de recréer et réindexer. OpenSearch Serverless facture des unités de calcul (OCU) à l'heure tant que la collection existe, même sans requête ; Aurora facture l'instance, ou les ACU en Serverless v2 (qui peut se mettre en pause à 0 ACU, réveil lent) ; S3 Vectors facture surtout stockage et requêtes. À faible trafic, le coût fixe compte plus que la latence.
- Usage : ✅ S3 Vectors pour un petit volume peu interrogé ; OpenSearch pour recherche hybride et faible latence à fort trafic · ❌ laisser tourner une collection OpenSearch de test.

```python
# Exemple 1 : ce qui coûte au repos
store = {
    "S3 Vectors": "stockage + requêtes",
    "OpenSearch Svl": "OCU à l'heure",
    "Aurora provisionné": "instance",
}
fixe = {"OpenSearch Svl",
        "Aurora provisionné"}
# projet perso, peu de requêtes
[s for s in store if s not in fixe]
# → ["S3 Vectors"]
```

- Quiz : Une KB de test sur OpenSearch Serverless n'a reçu aucune requête du mois : que coûte son store ?
- [ ] Rien, facturation à la requête
- [ ] Seulement le stockage des vecteurs
- [ ] Rien après 30 jours d'inactivité
- [x] Les OCU, facturées en continu
- Réponse : Les OCU, en continu : OpenSearch Serverless facture ses unités de calcul même au repos ; supprimer la collection après le test.

## 8. Vecteurs normés : le produit scalaire suffit
- Id : rag-et-embeddings-vecteurs-normes-produit-scalaire
- Sous-thème : embeddings
- Type : concept
- Niveau : 3
- Profils : expert
- Prérequis : rag-et-embeddings-similarite-cosinus
- Mots-clés : similarité cosinus, base vectorielle, embedding
- Définition : Si les vecteurs sont normés (longueur 1), le cosinus se réduit au produit scalaire, moins coûteux à calculer en base vectorielle.
- Contexte : Le cosinus divise le produit scalaire par les deux normes ; normer une fois à l'indexation évite ce calcul à chaque requête. Beaucoup de modèles d'embedding proposent de renvoyer des vecteurs déjà normés, et les bases vectorielles laissent choisir la métrique (cosinus, produit scalaire, distance euclidienne). La métrique doit correspondre à la façon dont les vecteurs ont été produits.
- Usage : ✅ vecteurs normés à l'indexation et à la requête, métrique « produit scalaire » · ❌ produit scalaire sur des vecteurs non normés : la longueur fausse le classement.

```python
# Exemple 1 : normer puis comparer
import math

def norme(v):
    n = math.hypot(*v)
    return [x / n for x in v]

a, b = norme([3, 4]), norme([4, 3])
round(math.hypot(*a), 6)   # → 1.0
round(sum(x * y for x, y in zip(a, b)),
      2)                   # → 0.96
```

- Quiz : Sans normer, que vaut le produit scalaire de `[3, 4]` avec lui-même ?
- [ ] `1.0`
- [ ] `7`
- [ ] `5.0`
- [x] `25`
- Réponse : `25` (9 + 16) : sans normalisation, le produit scalaire grandit avec la longueur ; seul le vecteur normé donne 1.
