---
title: "Cartes · Coûts AWS"
type: cartes
langage: AWS
chapitre: Exploitation
cours: Coûts
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Coûts AWS
AWS · Coûts : coût fixe, réseau (format spec v4 de revision-pwa).

## 1. coût au repos : le réflexe
- Id : couts-cout-au-repos
- Sous-thème : coût fixe
- Type : choisir
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : lambda-quand-la-choisir
- Définition : Avant tout choix, on demande ce que le service coûte quand personne ne l'utilise : à faible volume, le serverless facturé à l'usage gagne.
- Contexte : Avec un budget d'environ 35 $/mois pour data-platform, un seul service à coût fixe (NAT Gateway, environnement MWAA, base RDS) peut le consommer en entier. Les services à l'usage coûtent quelques centimes à ce volume. Le raisonnement s'inverse à forte charge constante : une capacité réservée devient moins chère que le paiement à l'unité.
- Usage : ✅ lister le coût fixe mensuel de chaque brique avant de la proposer · ❌ choisir sur le prix unitaire seul, sans regarder ce qui tourne 24 h/24.

```
# Exemple 1 : à l'usage ou fixe
0 $ au repos        coût fixe
S3, Lambda          NAT Gateway
Athena              MWAA
DynamoDB on-demand  OpenSearch
Step Functions      Redshift provisionné
SQS, EventBridge    RDS / Aurora
Glue (au job)       cluster EMR
```

```python
# Exemple 2 : un coût fixe vs le budget
budget = 35            # $ / mois
nat = 730 * 0.05       # 1 NAT, Paris
round(nat, 1)          # → 36.5
nat > budget           # → True
```

- Quiz : Le volume est devenu énorme et constant (requêtes 24 h/24) : le « tout à l'usage » reste-t-il le moins cher ?
- [ ] Oui : le serverless est toujours moins cher
- [x] Pas forcément : une capacité réservée peut coûter moins
- [ ] Non : il faut tout passer sur EC2
- [ ] Oui, si tout est en Graviton
- Réponse : pas forcément : à charge élevée et stable, une capacité réservée (Redshift provisionné, Savings Plans, débit provisionné DynamoDB) coûte moins que le paiement à l'unité.

## 2. NAT Gateway : le coût caché
- Id : couts-nat-gateway-endpoint
- Sous-thème : réseau
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : couts-cout-au-repos
- Définition : Une Lambda en VPC privé sort vers S3 par une NAT Gateway payante, sauf avec un endpoint VPC de type Gateway pour S3, gratuit.
- Contexte : À Paris, une NAT coûte 0,05 $ par heure et 0,05 $ par Go traité : plus que tout le budget de data-platform avant le premier octet. Un endpoint Gateway ajoute une route vers S3 dans la table de routage, sans frais ; les endpoints Interface (autres services) sont, eux, facturés à l'heure. Une Lambda qui n'a pas besoin du VPC n'y va pas : elle sort directement.
- Usage : ✅ endpoint Gateway S3 dans tout VPC data, Lambda hors VPC quand rien ne l'y oblige · ❌ NAT Gateway pour joindre S3 depuis un VPC.

```python
# Exemple 1 : NAT vs endpoint Gateway
h_mois = 730
nat_h, nat_go = 0.05, 0.05  # $, Paris
go_mois = 500   # lectures/écritures S3

nat = h_mois * nat_h + go_mois * nat_go
round(nat, 2)    # → 61.5
endpoint = 0     # Gateway S3 : gratuit
```

- Quiz : La même Lambda en VPC lit aussi une table DynamoDB via la NAT : comment supprimer ce trafic NAT ?
- [ ] Impossible : seul S3 a un endpoint Gateway
- [ ] Un endpoint Interface, gratuit lui aussi
- [x] Un endpoint Gateway DynamoDB, gratuit
- [ ] Un peering VPC vers DynamoDB
- Réponse : un endpoint Gateway DynamoDB : S3 et DynamoDB sont les deux seuls services à endpoint Gateway, gratuit ; les endpoints Interface sont facturés à l'heure et au Go.
