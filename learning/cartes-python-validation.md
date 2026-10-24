---
title: "Cartes · Validation Python (pydantic)"
type: cartes
langage: Python
cours: Validation
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Validation Python (pydantic)
Python · Validation : modèles, sérialisation, types, validateurs (format spec v3 de revision-pwa).

## 1. BaseModel : champ requis ou optionnel
- Sous-thème : modèles
- Niveau : 1
- Définition : Une classe `BaseModel` déclare ses champs par annotations ; un champ sans valeur par défaut est requis, avec défaut il est facultatif.
- Contexte : Les annotations ne sont pas décoratives comme en TS : pydantic les lit à la création de la classe et valide chaque instance à la construction. Le constructeur n'accepte que des arguments nommés. Le piège venant de TS : `str | None` dit seulement que `None` est une valeur permise ; c'est le `= None` qui rend le champ facultatif, pas le type (≈ `tribunal?: string`).
- Usage : ✅ toute donnée qui entre de l'extérieur (annonce BODACC, payload d'API, config) · ❌ structure interne déjà typée et sûre : `@dataclass`, plus léger.

```python
# Exemple 1 : requis et facultatif
from pydantic import BaseModel
class Annonce(BaseModel):
    id: str                     # requis
    tribunal: str | None = None # facultatif
a = Annonce(id="A1")
a.tribunal  # → None
```

```python
# Exemple 2 : arguments nommés seulement
from pydantic import BaseModel

class Annonce(BaseModel):
    id: str

Annonce(id="A1").id  # → "A1"
Annonce("A1")        # ❌ TypeError
```

- Quiz : Avec `tribunal: str | None` (sans `= None`), que fait `Annonce(id="A1")` ?
- [ ] Modèle créé, `tribunal` vaut `None`
- [ ] Modèle créé, `tribunal` absent
- [x] `ValidationError` : champ requis
- [ ] `TypeError` à la définition
- Réponse : `ValidationError` (`missing`) : `str | None` autorise la valeur `None`, mais sans défaut le champ reste requis.

## 2. model_validate : les champs en trop
- Sous-thème : modèles
- Niveau : 1
- Définition : `Modele.model_validate(dict)` construit et valide un modèle depuis un dict (≈ `schema.parse` de zod) ; `extra` décide du sort des clés non déclarées.
- Contexte : Par défaut (`extra="ignore"`), les clés inconnues disparaissent sans erreur : pratique pour un export qui renvoie 40 champs dont on garde 15, dangereux pour une faute de frappe dans une config. `extra="forbid"` les rejette en `ValidationError`, `extra="allow"` les garde dans `model_dump()`. Les types sont convertis (`"2026-10-20"` → `date`). `parse_obj` et `.dict()` sont l'API v1, dépréciée en v2.
- Usage : ✅ `ignore` pour une source externe large (export BODACC), `forbid` pour une config ou un payload qu'on contrôle · ❌ `parse_obj`, `.dict()` des vieux tutos : `model_validate`, `model_dump`.

```python
# Exemple 1 : clé inconnue ignorée
from datetime import date
from pydantic import BaseModel
class Annonce(BaseModel):
    id: str
    dateparution: date
a = Annonce.model_validate({"id": "A1",
    "dateparution": "2026-10-20", "x": 1})
"x" in a.model_dump()  # → False
a.dateparution  # → date(2026, 10, 20)
```

```python
# Exemple 2 : forbid attrape la faute
from pydantic import BaseModel, ConfigDict

class Config(BaseModel):
    model_config = ConfigDict(
        extra="forbid")
    max_attempts: int = 5

Config.model_validate(
    {"max_attemps": 3})  # ❌ ValidationError
```

- Quiz : Que fait `Annonce.model_validate({"id": 1, "dateparution": "2026-10-20"})` (exemple 1) ?
- [ ] Modèle créé, `id` vaut `"1"`
- [ ] Modèle créé, `id` vaut `1`
- [x] `ValidationError`
- [ ] `TypeError`
- Réponse : `ValidationError` : Pydantic v2 convertit une chaîne en `date`, mais refuse un `int` pour un champ `str` (la v1 le convertissait).

## 3. coercion : le mode lax
- Sous-thème : types
- Niveau : 1
- Définition : Par défaut (mode lax), pydantic convertit une entrée compatible vers le type annoté : `"10000"` devient `10000`, `"true"` devient `True`.
- Contexte : La conversion n'accepte que ce qui est sans perte : `"1.0"` donne `1`, mais `1.5` est refusé (`int_from_float`) plutôt qu'arrondi. Pour `bool`, seules quelques chaînes anglaises passent (`true`, `yes`, `on`, `1` et leurs contraires). En v2, un nombre n'est plus converti en `str` : un SIREN `int` est rejeté. Différence avec TS : le type agit à l'exécution, il ne se contente pas de décrire.
- Usage : ✅ entrées texte (CSV, query string, variables d'environnement) converties une fois pour toutes · ❌ compter sur une conversion « intelligente » (arrondi, français) : nettoyer avant, en `mode="before"`.

```python
# Exemple 1 : les chaînes converties
from pydantic import BaseModel
class Societe(BaseModel):
    capital: int
    actif: bool
s = Societe(capital="10000", actif="true")
(s.capital, s.actif)  # → (10000, True)
```

```python
# Exemple 2 : pas de perte silencieuse
from pydantic import BaseModel

class Societe(BaseModel):
    capital: int

Societe(capital="1.0").capital  # → 1
Societe(capital=1.5)  # ❌ ValidationError
```

- Quiz : Que fait `Societe(capital="10000", actif="oui")` (exemple 1) ?
- [ ] `actif` vaut `True`
- [ ] `actif` vaut `"oui"`
- [ ] `actif` vaut `False`
- [x] `ValidationError`
- Réponse : `ValidationError` (`bool_parsing`) : seules `true/false`, `yes/no`, `on/off`, `1/0` (et `t`, `f`, `y`, `n`) sont lues comme booléens.

## 4. Field : contraintes déclaratives
- Sous-thème : types
- Niveau : 1
- Définition : `Field(...)` ajoute des contraintes à un champ (`pattern`, `ge`, `min_length`, `max_length`) vérifiées à la validation, sans écrire de validateur.
- Contexte : Chaque contrainte a son type d'erreur (`string_pattern_mismatch`, `greater_than_equal`), lisible dans `errors()`. `pattern` est une regex cherchée avec `re.search` : sans `^…$`, une sous-chaîne suffit. Les contraintes s'appliquent après la conversion de type, donc sur l'`int`, pas sur la chaîne reçue. `Field` porte aussi `default`, `default_factory`, `alias` et `description` (reprise dans le JSON Schema).
- Usage : ✅ règles simples et déclaratives (format SIREN, montant positif, longueur) · ❌ règle métier conditionnelle ou qui transforme la valeur : `@field_validator`.

```python
# Exemple 1 : format SIREN
from pydantic import BaseModel, Field
class Annonce(BaseModel):
    siren: str = Field(
        pattern=r"^\d{9}$")
Annonce(siren="483609327").siren
# → "483609327"
Annonce(siren="48360932")  # ❌ ValidationError
```

```python
# Exemple 2 : bornes numériques
from pydantic import BaseModel, Field

class Societe(BaseModel):
    capital: int = Field(ge=0)

Societe(capital="500").capital  # → 500
Societe(capital=-1)  # ❌ ValidationError
```

- Quiz : Avec `nom: str = Field(min_length=1)`, que donne `nom="   "` (trois espaces) ?
- [ ] `ValidationError` : chaîne vide après strip
- [x] Accepté : `"   "`
- [ ] Accepté : `""`
- [ ] Accepté : `None`
- Réponse : accepté, `"   "` : les espaces comptent dans la longueur ; `ConfigDict(str_strip_whitespace=True)` les retire avant le contrôle.

## 5. modèles imbriqués : du dict à l'objet
- Sous-thème : modèles
- Niveau : 1
- Définition : Un champ typé par un autre `BaseModel` (ou `list[Personne]`) convertit les dicts reçus en instances, validées récursivement.
- Contexte : Une seule validation traite tout l'arbre : chaque dict imbriqué devient un objet, avec ses propres règles et défauts. On lit alors les champs par attribut (`p.siren`), jamais par clé. `model_dump()` refait le chemin inverse, récursivement, jusqu'aux dicts et listes. Les erreurs d'un sous-modèle portent le chemin complet (`personnes.1.siren`).
- Usage : ✅ JSON structuré de l'API (annonce → personnes → adresse), un modèle par niveau · ❌ sous-structure variable, sans schéma connu : `dict[str, Any]`.

```python
# Exemple 1 : la liste devient des objets
from pydantic import BaseModel
class Personne(BaseModel):
    siren: str
class Annonce(BaseModel):
    personnes: list[Personne] = []
a = Annonce(personnes=[{"siren": "483609327"}])
a.personnes[0].siren  # → "483609327"
```

```python
# Exemple 2 : retour aux dicts
from pydantic import BaseModel

class Personne(BaseModel):
    siren: str

class Annonce(BaseModel):
    id: str
    personnes: list[Personne] = []

a = Annonce(id="A1",
    personnes=[Personne(siren="1")])
a.model_dump()
# → {"id": "A1", "personnes": [{"siren": "1"}]}
```

- Quiz : Avec l'exemple 1, que donne `a.personnes[0]["siren"]` ?
- [ ] `"483609327"`
- [ ] `None`
- [ ] `KeyError`
- [x] `TypeError`
- Réponse : `TypeError` (`'Personne' object is not subscriptable`) : le dict est devenu un objet, on lit `a.personnes[0].siren`.

## 6. model_dump : choisir les champs
- Sous-thème : sérialisation
- Niveau : 1
- Définition : `model_dump()` rend le modèle en dict ; `exclude_none`, `include` et `exclude` choisissent les champs qui sortent.
- Contexte : Par défaut, tous les champs sortent, même `None` : un JSON écrit dans S3 traîne alors des dizaines de `null`. `exclude_none=True` les retire. `include` et `exclude` prennent un ensemble de noms (ou un dict pour descendre dans les sous-modèles). Les valeurs restent des objets Python (`date`) : `mode="json"` ou `model_dump_json()` pour des types JSON.
- Usage : ✅ alléger une sortie (`exclude_none`), masquer un champ sensible (`exclude`) · ❌ construire le dict à la main champ par champ : on oublie le prochain champ ajouté.

```python
# Exemple 1 : sans les None
from pydantic import BaseModel
class Personne(BaseModel):
    siren: str
    nom: str | None = None
p = Personne(siren="483609327")
p.model_dump(exclude_none=True)
# → {"siren": "483609327"}
```

```python
# Exemple 2 : include et exclude
from pydantic import BaseModel

class Personne(BaseModel):
    siren: str
    nom: str = "ACME"
    email: str = "a@acme.fr"

p = Personne(siren="483609327")
p.model_dump(exclude={"email"})
# → {"siren": "483609327", "nom": "ACME"}
p.model_dump(include={"siren"})
# → {"siren": "483609327"}
```

- Quiz : Avec l'exemple 1, que rend `Personne(siren="483609327", nom="").model_dump(exclude_none=True)` ?
- [ ] `{"siren": "483609327"}`
- [x] `{"siren": "483609327", "nom": ""}`
- [ ] `{"siren": "483609327", "nom": None}`
- Réponse : `{"siren": "483609327", "nom": ""}` : `exclude_none` ne retire que `None` ; une chaîne vide est une vraie valeur.

## 7. Pydantic : @field_validator
- Sous-thème : validateurs
- Niveau : 2
- Définition : `@field_validator("champ")` + `@classmethod` vérifie ou transforme un champ à la création du modèle ; lever `ValueError` le rejette.
- Contexte : Le validateur reçoit la valeur (déjà convertie au type annoté, en mode par défaut) et **renvoie la valeur à garder** : il peut donc normaliser (strip, majuscules) en plus de contrôler. Une `ValueError` levée dedans devient une `ValidationError` qui liste le champ fautif. `@classmethod` se place sous `@field_validator` : le validateur n'a pas d'instance, le modèle n'existe pas encore.
- Usage : ✅ règle métier sur un champ (SIREN sur 9 chiffres, normaliser un code tribunal) · ❌ règle qui croise plusieurs champs : `@model_validator` ; simple contrainte de longueur : `Field(min_length=…)`.

```python
# Exemple 1 : rejeter un SIREN
from pydantic import (BaseModel,
                      field_validator)
class Annonce(BaseModel):
    siren: str
    @field_validator("siren")
    @classmethod
    def neuf(cls, v):
        if len(v) != 9:
            raise ValueError("9")
        return v
Annonce(siren="123")  # ❌ ValueError
```

```python
# Exemple 2 : normaliser
from pydantic import (BaseModel,
                      field_validator)

class Annonce(BaseModel):
    ville: str

    @field_validator("ville")
    @classmethod
    def majuscules(cls, v):
        return v.strip().upper()

Annonce(ville=" lyon ").ville
# → "LYON"
```

- Quiz : Si `neuf` oublie sa dernière ligne `return v`, que vaut `Annonce(siren="483609327").siren` ?
- [ ] `"483609327"`
- [x] `None`
- [ ] `ValidationError`
- [ ] `AttributeError`
- Réponse : `None` : la valeur renvoyée par le validateur remplace celle du champ ; sans `return`, c'est `None`.

## 8. Pydantic : @model_validator
- Sous-thème : validateurs
- Niveau : 2
- Définition : `@model_validator(mode="after")` vérifie plusieurs champs ensemble, une fois le modèle construit, et doit renvoyer `self`.
- Contexte : En mode `after`, c'est une méthode d'instance : tous les champs sont déjà validés et convertis (ici les chaînes en `date`), on compare donc des valeurs typées. Lever `ValueError` rejette tout le modèle. Le mode `before` reçoit au contraire le dict brut, avant tout champ : utile pour renommer ou réorganiser l'entrée.
- Usage : ✅ cohérence entre champs (fin après début, montant et devise ensemble) · ❌ contrôle d'un seul champ : `@field_validator`, plus précis dans le message d'erreur.

```python
# Exemple 1 : fin avant début
from datetime import date
from pydantic import (BaseModel,
                      model_validator)
class Periode(BaseModel):
    debut: date
    fin: date
    @model_validator(mode="after")
    def ordre(self):
        if self.fin < self.debut:
            raise ValueError("fin")
        return self
Periode(debut="2026-10-01",
  fin="2026-09-01")  # ❌ ValueError
```

```python
# Exemple 2 : les champs sont typés
from datetime import date
from pydantic import (BaseModel,
                      model_validator)

class Periode(BaseModel):
    debut: date
    fin: date

    @model_validator(mode="after")
    def ordre(self):
        assert type(self.fin) is date
        return self

p = Periode(debut="2026-09-01",
            fin="2026-10-01")
(p.fin - p.debut).days  # → 30
```

- Quiz : Que se passe-t-il si `ordre` oublie `return self`, avec des dates valides ?
- [ ] `ValidationError`
- [ ] Le constructeur renvoie `None`
- [x] Modèle créé, avec un `UserWarning`
- [ ] `TypeError`
- Réponse : Modèle créé, avec un `UserWarning` (« returning a value other than `self` ») : Pydantic tolère mais avertit, toujours `return self`.

## 9. ValidationError : toutes les erreurs d'un coup
- Sous-thème : validateurs
- Niveau : 2
- Définition : Une `ValidationError` regroupe toutes les erreurs du modèle, chacune avec son chemin (`loc`), son type et son message.
- Contexte : Pydantic ne s'arrête pas à la première erreur : il valide tous les champs et rend la liste complète (`errors()`, `error_count()`), comme zod avec `issues`. `loc` est un tuple qui descend dans l'arbre : `("personnes", 0, "siren")`. Dans un validateur, seules `ValueError` et `AssertionError` sont converties en `ValidationError` ; une autre exception remonte telle quelle.
- Usage : ✅ journaliser `errors()` dans les rejets (type et chemin), corriger le modèle sur une journée complète · ❌ parser le texte de `str(e)` : il change entre versions, `errors()` est stable.

```python
# Exemple 1 : deux erreurs, deux chemins
from pydantic import (BaseModel,
                      ValidationError)
class Personne(BaseModel):
    siren: str
class Annonce(BaseModel):
    id: str
    personnes: list[Personne]
try:
    Annonce(personnes=[{"nom": "X"}])
except ValidationError as e:
    n = e.error_count()
    locs = [x["loc"] for x in e.errors()]
n     # → 2
locs  # → [("id",), ("personnes", 0, "siren")]
```

- Quiz : Un `@field_validator` lève `TypeError("pas un SIREN")` : que reçoit l'appelant ?
- [ ] `ValidationError`, de type `type_error`
- [ ] `ValidationError`, de type `value_error`
- [x] `TypeError`, telle quelle
- [ ] `PydanticUserError`
- Réponse : `TypeError` telle quelle : seules `ValueError` (et `AssertionError`) deviennent des `ValidationError` ; lever `ValueError` dans un validateur.

## 10. Pydantic : @computed_field
- Sous-thème : sérialisation
- Niveau : 2
- Définition : `@computed_field` sur une `@property` ajoute la valeur calculée à la sortie du modèle (`model_dump`, JSON).
- Contexte : Une propriété ordinaire se lit sur l'objet mais Pydantic l'ignore à la sérialisation : seuls les champs déclarés sortent. `@computed_field`, placé au-dessus de `@property`, l'inscrit dans le schéma de sortie. Le type de retour annoté (`-> int`) sert au schéma JSON. La valeur est recalculée à chaque dump, elle n'est pas acceptée en entrée.
- Usage : ✅ champ dérivé à exposer dans une réponse API ou un fichier S3 (`nb_sirens`, `annee`) · ❌ valeur seulement utile en Python : `@property` simple suffit.

```python
# Exemple 1 : sérialisée avec le reste
from pydantic import (BaseModel,
                      computed_field)
class Annonce(BaseModel):
    sirens: list[str]
    @computed_field
    @property
    def nb(self) -> int:
        return len(self.sirens)
a = Annonce(sirens=["483609327"])
a.model_dump()
# → {"sirens": ["483609327"], "nb": 1}
```

```python
# Exemple 2 : aussi dans le JSON
from pydantic import (BaseModel,
                      computed_field)

class Annonce(BaseModel):
    date: str

    @computed_field
    @property
    def annee(self) -> int:
        return int(self.date[:4])

a = Annonce(date="2026-10-23")
a.model_dump_json()
# → '{"date":"2026-10-23","annee":2026}'
```

- Quiz : Avec une simple `@property` (sans `@computed_field`), que contient `model_dump()` de l'exemple 1 ?
- [x] `{"sirens": ["483609327"]}`
- [ ] `{"sirens": ["483609327"], "nb": 1}`
- [ ] `{"nb": 1}`
- [ ] `PydanticUserError`
- Réponse : `{"sirens": ["483609327"]}` : une propriété ordinaire se lit sur l'objet mais n'est pas sérialisée.

## 11. défaut [] : copié par instance
- Sous-thème : modèles
- Niveau : 2
- Définition : Dans un `BaseModel`, `registre: list[str] = []` est sûr : Pydantic copie le défaut pour chaque instance, contrairement à un argument par défaut Python.
- Contexte : En Python pur, un défaut mutable (`def __init__(self, r=[])`) est créé une seule fois, quand la fonction est définie : toutes les instances partagent la même liste, et un `append` sur l'une apparaît dans les autres. Pydantic copie le défaut à chaque création, comme `Field(default_factory=list)`. C'est l'inverse du réflexe TS, où un défaut est réévalué à chaque appel.
- Usage : ✅ `= []` ou `= {}` dans un modèle Pydantic · ❌ dans un `def` ou un `__init__` : `None` par défaut, puis créer la liste dans le corps.

```python
# Exemple 1 : Pydantic copie le défaut
from pydantic import BaseModel
class Annonce(BaseModel):
    registre: list[str] = []
a, b = Annonce(), Annonce()
a.registre.append("483609327")
b.registre   # → []
```

```python
# Exemple 2 : classe ordinaire, partagée
class Annonce:
    def __init__(self, registre=[]):
        self.registre = registre

a, b = Annonce(), Annonce()
a.registre.append("483609327")
b.registre   # → ["483609327"]
```

- Quiz : Avec `@dataclass` et `registre: list[str] = []`, que se passe-t-il ?
- [ ] Liste partagée entre instances
- [ ] Liste copiée par instance
- [x] `ValueError` à la définition de la classe
- [ ] `TypeError` à la création d'une instance
- Réponse : `ValueError` dès la définition : `@dataclass` refuse un défaut mutable et impose `field(default_factory=list)`.

## 12. alias : le nom de l'API
- Sous-thème : sérialisation
- Niveau : 2
- Définition : `Field(alias="dateParution")` lit la clé de l'API sous ce nom, tout en gardant un nom Python en snake_case (`date_parution`).
- Contexte : Par défaut, l'alias sert en entrée seulement : le constructeur et `model_validate` attendent `dateParution`, et `model_dump()` rend le nom Python ; `by_alias=True` rend l'alias. Construire avec le nom Python demande `ConfigDict(validate_by_name=True)` (ou l’ancien `populate_by_name`). Pour toute une API en camelCase, `alias_generator=to_camel` évite d'écrire chaque alias.
- Usage : ✅ API en camelCase ou clé non valide en Python (`"@id"`, `"class"`) · ❌ renommer pour le goût dans un modèle interne : garder le nom de la source, moins de surprises.

```python
# Exemple 1 : lire sous l'alias
from datetime import date
from pydantic import BaseModel, Field
class Annonce(BaseModel):
    date_parution: date = Field(
        alias="dateParution")
a = Annonce.model_validate(
    {"dateParution": "2026-10-20"})
a.date_parution  # → date(2026, 10, 20)
a.model_dump(by_alias=True)
# → {"dateParution": date(2026, 10, 20)}
```

```python
# Exemple 2 : accepter aussi le nom Python
from datetime import date
from pydantic import (BaseModel,
                      ConfigDict, Field)

class Annonce(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True)
    date_parution: date = Field(
        alias="dateParution")

Annonce(date_parution="2026-10-20"
        ).date_parution
# → date(2026, 10, 20)
```

- Quiz : Sans `validate_by_name` (exemple 1), que fait `Annonce(date_parution="2026-10-20")` ?
- [ ] Modèle créé : le nom Python marche toujours
- [x] `ValidationError` : `dateParution` manquant
- [ ] `TypeError` : argument inattendu
- [ ] Modèle créé, avec un avertissement
- Réponse : `ValidationError` (`missing`, `loc=("dateParution",)`) : avec un alias, seul l'alias est lu en entrée ; le nom Python est ignoré comme une clé en trop.

## 13. model_validate_json : du texte au modèle
- Sous-thème : sérialisation
- Niveau : 2
- Définition : `Modele.model_validate_json(texte)` parse et valide un JSON (`str` ou `bytes`) en une seule passe, sans `json.loads` préalable.
- Contexte : Le parseur JSON de pydantic-core (en Rust) construit directement le modèle : plus rapide que `json.loads` puis `model_validate`, et une erreur de syntaxe devient une `ValidationError` (`json_invalid`) comme les autres. Pour une ligne d'export JSONL, c'est l'appel naturel. L'inverse, `model_dump_json()`, rend une chaîne JSON avec dates et `Decimal` déjà sérialisés.
- Usage : ✅ corps de réponse HTTP, ligne JSONL, message SQS, objet S3 · ❌ donnée déjà décodée en dict : `model_validate`.

```python
# Exemple 1 : une ligne JSONL
from datetime import date
from pydantic import BaseModel
class Annonce(BaseModel):
    id: str
    dateparution: date
l = '{"id": "A1", "dateparution": "2026-10-20"}'
Annonce.model_validate_json(l).dateparution
# → date(2026, 10, 20)
```

```python
# Exemple 2 : JSON cassé = ValidationError
from pydantic import BaseModel

class Annonce(BaseModel):
    id: str

Annonce.model_validate_json(
    b'{"id": "A1"}').id  # → "A1"
Annonce.model_validate_json(
    '{"id": "A1",}')  # ❌ ValidationError
```

- Quiz : Que fait `Annonce.model_validate(l)` avec la chaîne `l` de l'exemple 1 ?
- [ ] Parse la chaîne, comme `model_validate_json`
- [ ] `TypeError` : un dict est attendu
- [x] `ValidationError` : instance ou dict attendu
- [ ] `JSONDecodeError`
- Réponse : `ValidationError` (`model_type`) : `model_validate` ne parse jamais de texte, il attend un dict (ou une instance).

## 14. affectation : non validée par défaut
- Sous-thème : modèles
- Niveau : 2
- Définition : Après la création, `a.capital = "abc"` n'est pas validé par défaut ; `ConfigDict(validate_assignment=True)` valide (et convertit) chaque affectation.
- Contexte : La validation a lieu à la construction. Une affectation ordinaire écrit la valeur telle quelle : le modèle porte alors une chaîne dans un champ `int`, et l'erreur n'apparaît que plus loin (avertissement à la sérialisation, plantage d'un calcul). `validate_assignment=True` repasse par le pipeline complet, conversion comprise, au prix d'un léger coût à chaque écriture.
- Usage : ✅ modèle modifié après création (enrichissement, normalisation en plusieurs étapes) · ❌ modèle écrit une fois puis lu : `frozen=True`, plus sûr encore.

```python
# Exemple 1 : la mauvaise valeur passe
from pydantic import BaseModel
class Societe(BaseModel):
    capital: int
s = Societe(capital=1)
s.capital = "abc"     # aucune erreur
s.capital  # → "abc"
```

```python
# Exemple 2 : valider chaque affectation
from pydantic import BaseModel, ConfigDict

class Societe(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True)
    capital: int

s = Societe(capital=1)
s.capital = "500"
s.capital  # → 500  (converti)
s.capital = "abc"  # ❌ ValidationError
```

- Quiz : Avec l'exemple 1, que fait `s.inconnu = 1` (champ non déclaré) ?
- [ ] Ajoute l'attribut, comme en JS
- [ ] `AttributeError`
- [x] `ValueError` : pas de champ `inconnu`
- [ ] `ValidationError`
- Réponse : `ValueError` (`"Societe" object has no field "inconnu"`) : un modèle refuse tout attribut non déclaré, même sans `validate_assignment`.

## 15. frozen : un modèle immuable
- Sous-thème : modèles
- Niveau : 2
- Définition : `ConfigDict(frozen=True)` interdit toute affectation après création et rend le modèle hachable (clé de dict, élément de set).
- Contexte : Affecter un champ lève `ValidationError` (`frozen_instance`). Le hash est calculé sur les valeurs des champs : deux annonces identiques font un seul élément de set, pratique pour dédoublonner. Le gel est superficiel, comme `Object.freeze` en JS : il bloque l'affectation, pas la modification d'une liste contenue. Un champ `list` rend d'ailleurs le hash impossible.
- Usage : ✅ enregistrement validé qui ne doit plus bouger (annonce de `processed`), clé de cache · ❌ modèle enrichi par étapes : `validate_assignment=True`.

```python
# Exemple 1 : affectation refusée
from pydantic import BaseModel, ConfigDict
class Annonce(BaseModel):
    model_config = ConfigDict(frozen=True)
    siren: str
a = Annonce(siren="483609327")
a.siren = "x"  # ❌ ValidationError
```

```python
# Exemple 2 : dédoublonner par un set
from pydantic import BaseModel, ConfigDict

class Annonce(BaseModel):
    model_config = ConfigDict(frozen=True)
    siren: str

vues = {Annonce(siren="483609327"),
        Annonce(siren="483609327")}
len(vues)  # → 1
```

- Quiz : Modèle `frozen` avec `tags: list[str] = []` : que fait `a.tags.append("LJ")` ?
- [ ] `ValidationError` : instance gelée
- [x] Rien n'empêche : la liste est modifiée
- [ ] `AttributeError` : liste en lecture seule
- [ ] `TypeError` : liste convertie en tuple
- Réponse : la liste est modifiée : `frozen` bloque l'affectation du champ, pas la mutation de l'objet qu'il contient ; préférer `tuple[str, ...]`.

## 16. field_validator : mode before ou after
- Sous-thème : validateurs
- Niveau : 3
- Définition : `mode="before"` reçoit la valeur brute avant conversion de type ; `mode="after"` (défaut) reçoit la valeur déjà convertie et validée.
- Contexte : Pydantic valide en pipeline : validateurs `before`, puis conversion vers le type annoté (`"10000"` → `10000`), puis validateurs `after`. Si la donnée brute ne peut pas être convertie (capital BODACC écrit `"10 000"`), la conversion échoue avant tout validateur `after` : seul un `before` peut la nettoyer. En `before`, la valeur peut être de n'importe quel type, d'où le `isinstance`.
- Usage : ✅ `before` pour nettoyer une donnée brute (espaces, `""` → `None`), `after` pour une règle métier sur une valeur typée · ❌ règle métier en `before` : la valeur n'est pas encore typée.

```python
# Exemple 1 : nettoyer avant
from pydantic import (BaseModel,
                      field_validator)
class Annonce(BaseModel):
    capital: int
    @field_validator("capital",
                     mode="before")
    @classmethod
    def sans_espaces(cls, v):
        if isinstance(v, str):
            return v.replace(" ", "")
        return v
Annonce(capital="10 000").capital
# → 10000
```

```python
# Exemple 2 : after reçoit un int
from pydantic import (BaseModel,
                      field_validator)

class Annonce(BaseModel):
    capital: int

    @field_validator("capital")
    @classmethod
    def positif(cls, v):
        assert isinstance(v, int)
        if v < 0:
            raise ValueError("< 0")
        return v

Annonce(capital="500").capital
# → 500  (déjà un int)
```

```python
# Exemple 3 : un validateur, plusieurs champs
import json
from pydantic import (BaseModel,
                      field_validator)
CHAMPS = ("jugement", "acte")

class Annonce(BaseModel):
    jugement: dict | None = None
    acte: dict | None = None

    @field_validator(*CHAMPS,
                     mode="before")
    @classmethod
    def decode(cls, v):  # str → dict
        if isinstance(v, str):
            return json.loads(v)
        return v

a = Annonce(jugement='{"nature": "LJ"}')
a.jugement  # → {"nature": "LJ"}
```

- Quiz : Avec l'exemple 1 passé en `mode="after"`, que fait `Annonce(capital="10 000")` ?
- [ ] Renvoie un modèle, `capital` vaut `10000`
- [ ] Renvoie un modèle, `capital` vaut `"10000"`
- [ ] Lève `TypeError`
- [x] Lève `ValidationError`
- Réponse : `ValidationError` (sous-classe de `ValueError`) : la conversion de `"10 000"` en `int` échoue avant que le validateur `after` ne soit appelé.

## 17. strict : sans conversion
- Sous-thème : types
- Niveau : 3
- Définition : `ConfigDict(strict=True)` (ou `Field(strict=True)`, `StrictInt`) refuse toute conversion : la valeur doit déjà avoir le bon type.
- Contexte : Le mode strict s'applique au modèle, à un champ, ou à un seul appel (`model_validate(d, strict=True)`). Il protège d'une conversion qui masquerait un bug amont : un `capital` arrivé en chaîne signale un parseur mal réglé. Exception logique en JSON : JSON n'a ni date ni UUID, donc `model_validate_json` accepte toujours une date en chaîne ISO, même en strict.
- Usage : ✅ données internes déjà typées (sortie d'un autre modèle), détection d'un type faux en amont · ❌ entrée texte (CSV, query string, env) : le mode lax est fait pour ça.

```python
# Exemple 1 : la chaîne est refusée
from pydantic import BaseModel, ConfigDict
class Societe(BaseModel):
    model_config = ConfigDict(strict=True)
    capital: int
Societe(capital=10).capital  # → 10
Societe(capital="10")  # ❌ ValidationError
```

```python
# Exemple 2 : strict pour un seul appel
from pydantic import BaseModel

class Societe(BaseModel):
    capital: int

d = {"capital": "10"}
Societe.model_validate(d).capital  # → 10
Societe.model_validate(
    d, strict=True)  # ❌ ValidationError
```

- Quiz : Modèle `strict=True` avec `d: date` : que fait `model_validate_json('{"d": "2026-10-20"}')` ?
- [ ] `ValidationError` : `date_type`
- [ ] `d` reste la chaîne `"2026-10-20"`
- [x] `d` vaut `date(2026, 10, 20)`
- [ ] `TypeError`
- Réponse : `date(2026, 10, 20)` : en JSON une date ne peut être qu'une chaîne, le mode strict l'accepte donc en ISO ; en Python (`model_validate`), il la refuserait.

## 18. Annotated : un type réutilisable
- Sous-thème : types
- Niveau : 3
- Définition : `Siren = Annotated[str, AfterValidator(f)]` crée un type portant sa validation, réutilisable dans tous les modèles (≈ un schéma zod partagé).
- Contexte : Un `@field_validator` est attaché à un modèle ; un type annoté voyage : `list[Siren]`, `Siren | None`, `TypeAdapter(Siren)`. `BeforeValidator` agit avant la conversion, `AfterValidator` après. Piège d'ordre : les `AfterValidator` s'appliquent de gauche à droite, mais les `BeforeValidator` de droite à gauche (chaque nouveau « before » enveloppe les précédents). La fonction lève `ValueError` comme dans un validateur classique.
- Usage : ✅ règle partagée par plusieurs modèles (SIREN, code tribunal, montant) · ❌ règle propre à un seul champ d'un seul modèle : `@field_validator`, plus lisible sur place.

```python
# Exemple 1 : le type et sa règle
from typing import Annotated
from pydantic import (AfterValidator,
                      BaseModel)
def neuf(v):
    if not (len(v) == 9 and v.isdigit()):
        raise ValueError("9 chiffres")
    return v
Siren = Annotated[str, AfterValidator(neuf)]
class Etab(BaseModel):
    sirens: list[Siren]
# loc de l'erreur : ("sirens", 1)
Etab(sirens=["483609327",
     "12"])  # ❌ ValidationError
```

```python
# Exemple 2 : nettoyer puis contrôler
from typing import Annotated
from pydantic import (AfterValidator,
    BeforeValidator, TypeAdapter)

def neuf(v):
    if len(v) != 9:
        raise ValueError("9 chiffres")
    return v

Siren = Annotated[str,
    BeforeValidator(
        lambda v: v.replace(" ", "")),
    AfterValidator(neuf)]
TypeAdapter(Siren).validate_python(
    "483 609 327")  # → "483609327"
```

- Quiz : `Annotated[str, BeforeValidator(a), BeforeValidator(b)]` : dans quel ordre `a` et `b` s'exécutent-ils ?
- [ ] `a` puis `b`
- [x] `b` puis `a`
- [ ] En parallèle, résultats fusionnés
- [ ] Seul `b`, il remplace `a`
- Réponse : `b` puis `a` : les validateurs `before` s'enveloppent, le dernier déclaré passe en premier ; les `after` vont de gauche à droite.

## 19. TypeAdapter : valider sans modèle
- Sous-thème : types
- Niveau : 3
- Définition : `TypeAdapter(T)` applique la validation pydantic à n'importe quel type (`list[Annonce]`, `dict[str, int]`, `date`) sans écrire de `BaseModel`.
- Contexte : Un `BaseModel` décrit un objet à champs nommés ; pour une liste de modèles au sommet d'un JSON, ou un simple type, il faudrait un modèle enveloppe artificiel. `TypeAdapter` offre les mêmes méthodes : `validate_python`, `validate_json`, `dump_python`, `json_schema`. Sa construction compile un schéma : la créer une fois au niveau du module, pas dans une boucle.
- Usage : ✅ réponse JSON qui est une liste, paramètre typé isolé, type `Annotated` partagé · ❌ `TypeAdapter(...)` recréé à chaque ligne d'une journée de 32 000 annonces : le sortir de la boucle.

```python
# Exemple 1 : une liste de modèles
from pydantic import BaseModel, TypeAdapter
class Personne(BaseModel):
    siren: str
LISTE = TypeAdapter(list[Personne])
ps = LISTE.validate_python(
    [{"siren": "483609327"}])
ps[0].siren  # → "483609327"
```

```python
# Exemple 2 : depuis du JSON
from pydantic import BaseModel, TypeAdapter

class Personne(BaseModel):
    siren: str

LISTE = TypeAdapter(list[Personne])
ps = LISTE.validate_json(
    '[{"siren": "1"}, {"siren": "2"}]')
len(ps)  # → 2
LISTE.dump_python(ps)[1]
# → {"siren": "2"}
```

- Quiz : Que rend `TypeAdapter(list[int]).validate_python("12")` ?
- [ ] `[1, 2]`
- [ ] `["1", "2"]`
- [ ] `[12]`
- [x] `ValidationError`
- Réponse : `ValidationError` (`list_type`) : une chaîne n'est pas acceptée comme liste, même si elle est itérable ; un tuple ou un set le serait.

## 20. exclude_unset : un PATCH partiel
- Sous-thème : sérialisation
- Niveau : 3
- Définition : `model_dump(exclude_unset=True)` ne rend que les champs fournis à la création, défauts exclus : la base d'une mise à jour partielle.
- Contexte : Pour un PATCH, `nom` absent signifie « ne pas toucher », `nom: null` « effacer » : deux sens que `exclude_none` confond. Pydantic retient les champs reçus dans `model_fields_set`, valeur `None` comprise. `exclude_unset` s'appuie dessus : un champ fourni sort, même égal à son défaut ; un champ non fourni ne sort jamais (≈ `Partial<T>` où l'absence compte).
- Usage : ✅ PATCH d'API, mise à jour partielle d'un enregistrement (DynamoDB `update_item`) · ❌ sortie complète d'un enregistrement : `model_dump()` simple, sinon les défauts disparaissent.

```python
# Exemple 1 : absent ou effacé
from pydantic import BaseModel
class Maj(BaseModel):
    nom: str | None = None
    ville: str | None = None
Maj(nom=None).model_dump(
    exclude_unset=True)  # → {"nom": None}
Maj().model_dump(exclude_unset=True)
# → {}
```

```python
# Exemple 2 : les champs reçus
from pydantic import BaseModel

class Maj(BaseModel):
    nom: str | None = None
    ville: str | None = None

m = Maj.model_validate({"ville": "Lyon"})
m.model_fields_set  # → {"ville"}
```

- Quiz : Avec `statut: str = "actif"`, que rend `Maj(statut="actif").model_dump(exclude_unset=True)` ?
- [ ] `{}` : égal au défaut
- [x] `{"statut": "actif"}`
- [ ] `{"statut": None}`
- Réponse : `{"statut": "actif"}` : `exclude_unset` regarde si le champ a été fourni, pas s'il diffère de son défaut (ça, c'est `exclude_defaults`).

## 21. model_copy : copier sans revalider
- Sous-thème : modèles
- Niveau : 3
- Définition : `a.model_copy(update={...})` crée une copie modifiée du modèle, sans aucune validation des valeurs de `update`.
- Contexte : `model_copy` est rapide parce qu'il ne repasse pas par le pipeline : une valeur fausse dans `update` entre telle quelle, comme une affectation non validée. Pour une copie modifiée et vérifiée, on revalide : `Modele.model_validate(a.model_dump() | maj)`. La copie est superficielle par défaut (≈ spread `{...a}` en JS) : `deep=True` copie aussi les listes et dicts.
- Usage : ✅ variante d'un modèle avec des valeurs déjà sûres (produites par le code) · ❌ appliquer une mise à jour venue de l'extérieur : `model_validate` sur le dict fusionné.

```python
# Exemple 1 : update non validé
from pydantic import BaseModel
class Societe(BaseModel):
    capital: int
s = Societe(capital=1)
c = s.model_copy(update={"capital": "abc"})
c.capital  # → "abc"  (aucune erreur)
```

```python
# Exemple 2 : revalider la fusion
from pydantic import BaseModel

class Societe(BaseModel):
    capital: int

s = Societe(capital=1)
maj = {"capital": "5000"}
c = Societe.model_validate(
    s.model_dump() | maj)
c.capital  # → 5000  (converti)
```

- Quiz : `l = Etab(tags=["LJ"])`, `c = l.model_copy()`, puis `c.tags.append("RJ")` : que vaut `l.tags` ?
- [ ] `["LJ"]`
- [x] `["LJ", "RJ"]`
- [ ] `["RJ"]`
- [ ] `[]`
- Réponse : `["LJ", "RJ"]` : la copie est superficielle, les deux modèles partagent la même liste ; `model_copy(deep=True)` les sépare.
