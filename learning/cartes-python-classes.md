---
title: "Cartes · Classes Python"
type: cartes
langage: Python
cours: Classes
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Classes Python
Python · Classes : dataclass, méthodes, propriétés (format spec v3 de revision-pwa).

## 1. @property : le getter
- Sous-thème : propriétés
- Niveau : 1
- Définition : `@property` expose une méthode comme un attribut calculé, lu sans parenthèses (≈ `get` en TS).
- Contexte : La valeur est recalculée à chaque lecture, sans stockage. Sans `setter`, l'attribut est en lecture seule : l'affecter lève `AttributeError`. C'est la façon pythonique d'exposer une donnée dérivée sans changer l'API d'appel : on commence par un attribut simple, on le transforme en propriété plus tard sans toucher aux appelants.
- Usage : ✅ donnée dérivée d'autres attributs (`nb_sirens`), attribut en lecture seule · ❌ calcul coûteux lu souvent : `functools.cached_property`.

```python
# Exemple 1 : attribut calculé
class Annonce:
    def __init__(self, sirens):
        self.sirens = sirens
    @property
    def nb_sirens(self):
        return len(self.sirens)
a = Annonce(["483609327", "552100554"])
a.nb_sirens  # → 2  (sans parenthèses)
```

```python
# Exemple 2 : recalculé à la lecture
class Annonce:
    def __init__(self, sirens):
        self.sirens = sirens

    @property
    def nb_sirens(self):
        return len(self.sirens)

a = Annonce(["483609327"])
a.sirens.append("552100554")
a.nb_sirens    # → 2  (suit la liste)
a.nb_sirens = 5  # ❌ AttributeError
```

- Quiz : Avec l'exemple 1, que fait `a.nb_sirens()` (avec parenthèses, comme une méthode) ?
- [ ] Renvoie `2`
- [ ] Lève `AttributeError`
- [x] Lève `TypeError`
- [ ] Renvoie la méthode liée
- Réponse : `TypeError` ('int' object is not callable) : `a.nb_sirens` vaut déjà `2`, et on essaie d'appeler cet entier.

## 2. @classmethod : constructeur alternatif
- Sous-thème : méthodes
- Niveau : 1
- Définition : `@classmethod` reçoit la classe (`cls`) au lieu de l'instance ; sert surtout à fabriquer des objets autrement (≈ `static from()` en TS).
- Contexte : Python n'a pas de surcharge de constructeur : un seul `__init__`. Pour construire depuis un dict, une ligne JSON ou une chaîne, on ajoute des méthodes de classe nommées (`depuis_dict`, `depuis_json`) qui appellent `cls(...)`. Utiliser `cls` plutôt que le nom de la classe en dur fait que la méthode fabrique la bonne sous-classe.
- Usage : ✅ constructeurs alternatifs (`depuis_dict`, `datetime.fromisoformat`), compteur partagé par la classe · ❌ fonction qui n'utilise ni classe ni instance : `@staticmethod` ou fonction de module.

```python
# Exemple 1 : depuis un dict
class Annonce:
    def __init__(self, id_, siren):
        self.id_ = id_
        self.siren = siren
    @classmethod
    def depuis_dict(cls, d):
        return cls(d["id"],
                   d["siren"])
a = Annonce.depuis_dict(
    {"id": "A1", "siren": "483609327"})
a.siren        # → "483609327"
```

```python
# Exemple 2 : la stdlib fait pareil
from datetime import date
d = date.fromisoformat("2026-10-23")
d.month        # → 10
```

- Quiz : Avec `class Radiation(Annonce): pass`, quel est le type de `Radiation.depuis_dict(d)` ?
- [x] `Radiation`
- [ ] `Annonce`
- [ ] `dict`
- [ ] `TypeError`
- Réponse : `Radiation` : `cls` est la classe sur laquelle on appelle la méthode, pas celle qui la définit.

## 3. @staticmethod : ni self ni cls
- Sous-thème : méthodes
- Niveau : 1
- Définition : `@staticmethod` range dans la classe une fonction qui ne reçoit ni instance ni classe : un simple utilitaire (≈ `static` en TS).
- Contexte : Par défaut, une fonction définie dans une classe devient une méthode : appelée sur une instance, Python lui passe l'instance en premier argument. `@staticmethod` supprime ce passage automatique. La méthode s'appelle alors aussi bien sur la classe que sur une instance. En Python, une simple fonction de module fait souvent mieux l'affaire.
- Usage : ✅ utilitaire étroitement lié à la classe (valider un SIREN pour `Siren`) · ❌ utilitaire général : fonction de module ; besoin de la classe : `@classmethod`.

```python
# Exemple 1 : un validateur rangé
class Siren:
    @staticmethod
    def valide(s):
        return (len(s) == 9
                and s.isdigit())

Siren.valide("483609327")  # → True
Siren().valide("12345")    # → False
```

- Quiz : Sans `@staticmethod`, que fait `Siren().valide("483609327")` ?
- [ ] Renvoie `True`
- [ ] Renvoie `False`
- [x] Lève `TypeError`
- Réponse : `TypeError` (takes 1 positional argument but 2 were given) : l'instance est passée en plus, comme premier argument.

## 4. @dataclass : classe de données
- Sous-thème : dataclass
- Niveau : 1
- Définition : `@dataclass` génère `__init__`, `__repr__` et `__eq__` à partir des attributs annotés : une classe de données sans code répétitif.
- Contexte : Le décorateur lit les annotations de la classe et écrit les méthodes à votre place : constructeur avec les champs dans l'ordre, affichage lisible, égalité champ par champ (deux objets égaux sans être le même objet). Les annotations ne sont **pas vérifiées** : `Annonce(1, 2)` passe. Pour valider les types à l'exécution, c'est Pydantic. Une valeur par défaut modifiable passe par `field(default_factory=…)`.
- Usage : ✅ enregistrements internes (annonce parsée, ligne de rapport) · ❌ données externes à valider (API BODACC, JSON) : `pydantic.BaseModel`.

```python
# Exemple 1 : init, repr, eq générés
from dataclasses import dataclass
@dataclass
class Annonce:
    id_: str
    siren: str
a = Annonce("A1", "483609327")
b = Annonce("A1", "483609327")
a == b    # → True  (champ à champ)
```

```python
# Exemple 2 : défaut modifiable
from dataclasses import (dataclass,
                         field)

@dataclass
class Annonce:
    id_: str
    tags: list = field(
        default_factory=list)
    # une liste neuve par objet
a = Annonce("A1")
a.tags         # → []
repr(a)
# → "Annonce(id_='A1', tags=[])"
```

- Quiz : Que se passe-t-il avec `tags: list = []` à la place de `field(default_factory=list)` ?
- [ ] La liste est partagée entre instances
- [x] `ValueError` à la définition de la classe
- [ ] `TypeError` à la création d'un objet
- [ ] Tout marche, chaque objet a sa liste
- Réponse : `ValueError` dès la définition : `dataclass` refuse un défaut `list`, `dict` ou `set`, qui serait partagé entre toutes les instances.

## 5. @x.setter : écrire une propriété
- Sous-thème : propriétés
- Niveau : 2
- Définition : `@nom.setter` ajoute l'écriture à une `@property` existante, avec contrôle de la valeur (≈ `set` en TS).
- Contexte : `@capital.setter` part de la propriété `capital` et en renvoie une copie dotée d'un setter : la méthode doit donc porter **le même nom** que la propriété. La vraie valeur est stockée dans un attribut préfixé `_` (convention « interne »). Affecter `self.capital = v` dans `__init__` passe aussi par le setter, ce qui valide dès la construction.
- Usage : ✅ valider ou normaliser une valeur à l'écriture (capital ≥ 0, SIREN sur 9 chiffres) · ❌ attribut sans règle : attribut simple, ou dataclass / Pydantic pour valider tout le modèle.

```python
# Exemple 1 : refuser une valeur
class Societe:
    def __init__(self):
        self._capital = 0
    @property
    def capital(self):
        return self._capital
    @capital.setter
    def capital(self, v):
        if v < 0:
            raise ValueError(v)
        self._capital = v
s = Societe()
s.capital = 10_000
s.capital      # → 10000
s.capital = -5  # ❌ ValueError
```

- Quiz : Si le setter s'appelle `def set_capital(self, v):` (toujours sous `@capital.setter`), que fait `s.capital = 10` ?
- [ ] Passe par `set_capital`
- [ ] Remplace la propriété par `10`
- [x] Lève `AttributeError`
- [ ] Lève `TypeError`
- Réponse : `AttributeError` (no setter) : la propriété avec setter est rangée sous `set_capital` ; `capital` reste sans setter.

## 6. @dataclass(frozen=True) : objet figé
- Sous-thème : dataclass
- Niveau : 2
- Définition : `frozen=True` interdit de modifier les attributs après création et rend l'objet hachable (clé de dict, élément de set).
- Contexte : Une dataclass ordinaire définit `__eq__`, ce qui supprime le `__hash__` hérité : ses objets ne peuvent pas aller dans un set. Figée, elle reçoit un `__hash__` calculé sur ses champs, cohérent avec l'égalité. Pour « modifier » un objet figé, on en crée un nouveau avec `dataclasses.replace(obj, champ=…)` (≈ `{...obj, champ}` en TS, ou `Readonly<T>`).
- Usage : ✅ valeurs immuables (SIREN, clé composée jour + tribunal), dédoublonnage par set · ❌ objet qu'on enrichit au fil d'un traitement : dataclass normale.

```python
# Exemple 1 : lecture seule
from dataclasses import dataclass
@dataclass(frozen=True)
class Siren:
    valeur: str
s = Siren("483609327")
s.valeur       # → "483609327"
s.valeur = "0"  # ❌ AttributeError
```

```python
# Exemple 2 : « modifier » = recréer
from dataclasses import (dataclass,
                         replace)

@dataclass(frozen=True)
class Cle:
    jour: str
    tribunal: str

c = Cle("2026-10-23", "7501")
c2 = replace(c, jour="2026-10-24")
c2.jour        # → "2026-10-24"
c.jour         # → "2026-10-23"
```

- Quiz : Que vaut `len({Siren("483609327"), Siren("483609327")})` ?
- [ ] `2`
- [x] `1`
- [ ] `TypeError` (unhashable)
- [ ] `0`
- Réponse : `1` : figée, la dataclass a un `__hash__` cohérent avec `__eq__` ; deux valeurs égales ne font qu'un élément.

## 7. @abstractmethod : imposer une méthode
- Sous-thème : méthodes
- Niveau : 2
- Définition : `@abstractmethod` dans une classe `ABC` interdit d'instancier toute sous-classe qui n'implémente pas la méthode (≈ `abstract` en TS).
- Contexte : La vérification a lieu à **l'instanciation**, pas à la définition de la sous-classe : `class Bodacc(Source): pass` passe, c'est `Bodacc()` qui lève `TypeError`. Elle n'existe que si la classe hérite de `ABC` (métaclasse `ABCMeta`). Python n'a pas d'`interface` : une ABC sert de contrat, `typing.Protocol` de typage structurel sans héritage.
- Usage : ✅ contrat commun à plusieurs sources (BODACC, INSEE) qui doivent toutes avoir `lire` · ❌ simple typage pour mypy sans héritage : `typing.Protocol`.

```python
# Exemple 1 : sous-classe incomplète
from abc import ABC, abstractmethod
class Source(ABC):
    @abstractmethod
    def lire(self, jour):
        """Annonces du jour."""
class Bodacc(Source):
    pass
Bodacc()       # ❌ TypeError
```

```python
# Exemple 2 : sous-classe complète
from abc import ABC, abstractmethod

class Source(ABC):
    @abstractmethod
    def lire(self, jour):
        """Annonces du jour."""

class Bodacc(Source):
    def lire(self, jour):
        return [f"annonce {jour}"]

Bodacc().lire("2026-10-23")
# → ["annonce 2026-10-23"]
```

- Quiz : Même code mais `class Source:` sans hériter de `ABC` : que fait `Bodacc()` ?
- [x] Crée l'objet, sans erreur
- [ ] Lève `TypeError`
- [ ] Lève `NotImplementedError`
- [ ] Lève `AttributeError`
- Réponse : Crée l'objet : sans `ABC` (métaclasse `ABCMeta`), `@abstractmethod` n'est jamais vérifié, le décorateur ne fait que poser une marque.

## 8. _nom ou __nom : privé par convention
- Sous-thème : propriétés
- Niveau : 2
- Source : data-platform · S1-06
- Définition : `_nom` signale un membre interne par simple convention ; `__nom` (sans `__` final) est renommé `_Classe__nom` par Python (≈ `private` TS, sans vraie protection).
- Contexte : Python n'a pas de `private` : `self._http` reste accessible, c'est un avertissement pour le lecteur et les outils. `__nom` déclenche le *name mangling* : l'attribut est stocké sous `_Classe__nom`, pour qu'une sous-classe ne l'écrase pas par accident, pas pour le cacher. `__nom__` (deux tirets de chaque côté) est réservé aux méthodes spéciales du langage (`__init__`, `__enter__`).
- Usage : ✅ `_nom` pour tout détail interne (`_owns_http`, `_day_params`) · ❌ `__nom` pour « faire privé » : complique tests et héritage sans rien protéger ; jamais inventer un `__nom__`.

```python
# Exemple 1 : convention, pas protection
class Client:
    def __init__(self):
        self._owns = True      # convention
        self.__cle = "s3cr3t"  # renommé
c = Client()
c._owns          # → True
c._Client__cle   # → "s3cr3t"
```

- Quiz : Avec l'exemple 1, que fait `c.__cle` hors de la classe ?
- [ ] Renvoie `"s3cr3t"`
- [x] `AttributeError`
- [ ] Renvoie `None`
- [ ] `PermissionError`
- Réponse : `AttributeError` : l'attribut n'existe que sous `_Client__cle` ; le renommage n'a lieu que dans le corps de la classe.

## 9. @cached_property : calculer une fois
- Sous-thème : propriétés
- Niveau : 3
- Définition : `functools.cached_property` calcule l'attribut au premier accès puis stocke le résultat dans l'instance ; les accès suivants ne recalculent plus.
- Contexte : Au premier accès, la valeur est écrite dans le `__dict__` de l'instance sous le même nom ; les lectures suivantes la trouvent là, sans repasser par la méthode. Elle ne suit donc plus les données dont elle dépend. `del obj.attr` efface la valeur et force le recalcul. Contrairement à `@cache` sur une méthode, le cache vit et meurt avec l'objet.
- Usage : ✅ calcul coûteux sur des données qui ne changent plus (index d'un lot d'annonces chargé) · ❌ données modifiées après coup : `@property`, recalculée à chaque lecture.

```python
# Exemple 1 : un seul calcul
from functools import cached_property
class Lot:
    def __init__(self, sirens):
        self.sirens = sirens
    @cached_property
    def nb(self):
        return len(self.sirens)
lot = Lot(["483609327"])
lot.nb         # → 1
```

```python
# Exemple 2 : stockée dans l'instance
from functools import cached_property

class Lot:
    def __init__(self, sirens):
        self.sirens = sirens

    @cached_property
    def nb(self):
        return len(self.sirens)

lot = Lot(["483609327"])
"nb" in vars(lot)  # → False
lot.nb
"nb" in vars(lot)  # → True
```

- Quiz : Avec l'exemple 1, après `lot.nb` puis `lot.sirens.append("552100554")`, que vaut `lot.nb` ?
- [x] `1`
- [ ] `2`
- [ ] `AttributeError`
- Réponse : `1` : la valeur est figée au premier accès ; `del lot.nb` force le recalcul, sinon préférer `@property`.
