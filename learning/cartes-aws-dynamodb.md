---
title: "Cartes · DynamoDB"
type: cartes
langage: AWS
cours: DynamoDB
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · DynamoDB
AWS · DynamoDB : choisir (format spec v3 de revision-pwa).

## 1. DynamoDB : lookup par clé
- Sous-thème : choisir
- Niveau : 1
- Définition : Pour lire un enregistrement par sa clé en quelques ms, à n'importe quel débit, on choisit DynamoDB (≈ une `Map` géante managée).
- Contexte : On conçoit la table à partir des requêtes : clé de partition (`siren`), éventuellement clé de tri (`date`), index secondaires pour les autres accès prévus. En mode à la demande, on paie à la requête et au Go, rien au repos. Un item fait 400 Ko au plus. Ce qui n'a pas été prévu dans les clés coûte un `Scan` complet de la table.
- Usage : ✅ API « fiche entreprise » par SIREN, état d'un traitement, déduplication · ❌ requêtes ad hoc, agrégats, jointures : Athena ou une base SQL.

```
# Exemple 1 : la décision
Besoin  : API « fiche entreprise »,
          GET /siren/483609327 < 20 ms
→ Choix : DynamoDB, PK = siren,
          à la demande (on-demand)
Pourquoi: accès par clé, payé à
          la requête, 0 $ au repos
Écarté  : Aurora (instance qui
          tourne sans trafic)
```

```python
# Exemple 2 : get par clé (simulé)
table = {"483609327": {"nom": "ACME",
                       "procedures": 2}}
table["483609327"]["procedures"]  # → 2
# un get = la clé exacte, rien d'autre
```

- Quiz : Le métier veut « procédures par tribunal et par mois, croisées avec le secteur » : quel service ?
- [ ] DynamoDB, avec un index secondaire
- [ ] DynamoDB, avec un `Scan` filtré
- [x] Athena sur `processed`
- [ ] S3 Select sur chaque fichier
- Réponse : Athena : DynamoDB n'a ni jointure ni `GROUP BY` ; il sert des accès prévus par clé, pas des questions ad hoc, et un `Scan` relit toute la table.
