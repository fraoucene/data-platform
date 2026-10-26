---
title: "Cartes · Classes Python"
type: cartes
langage: Python
chapitre: Bases du langage
cours: Classes
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Classes Python
Python · Classes : dataclass, méthodes, propriétés (format spec v3 de revision-pwa).

## 1. @property : le getter
- Id : classes-property-getter
- Sous-thème : propriétés
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Mots-clés : décorateur, attribut
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
- Id : classes-classmethod-constructeur
- Sous-thème : méthodes
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Voir aussi : classes-staticmethod
- Mots-clés : décorateur
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
- Id : classes-staticmethod
- Sous-thème : méthodes
- Type : concept
- Niveau : 1
- Profils : débutant
- Voir aussi : classes-classmethod-constructeur
- Mots-clés : décorateur, module
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
- Id : classes-dataclass-generee
- Sous-thème : dataclass
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Mots-clés : décorateur, annotation de type, méthode spéciale, Pydantic
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

## 5. dataclass : un résultat nommé plutôt qu'un tuple
- Id : classes-dataclass-plutot-que-tuple
- Sous-thème : dataclass
- Type : choisir
- Niveau : 1
- Profils : débutant, data
- Prérequis : classes-dataclass-generee
- Voir aussi : collections-tuple-deballer
- Mots-clés : dataclass, NamedTuple, déballage
- Source : data-platform · S1-07
- Définition : Une fonction qui rend plusieurs valeurs rend une dataclass figée (`PartStats`) plutôt qu'un tuple : champs nommés, typés, lisibles à l'appel (≈ `Readonly<interface>` en TS).
- Contexte : `return count, sha, raw, gz` oblige l'appelant à connaître l'ordre : `stats[2]` ne dit rien et casse en silence si l'ordre change. `PartStats(count=..., sha256=...)` se lit `stats.sha256`, s'affiche lisiblement dans pytest et se compare d'un bloc. Pas d'indexation : une dataclass n'est pas une séquence. `typing.NamedTuple` est l'alternative si l'on veut garder le dépaquetage.
- Usage : ✅ statistiques d'écriture, résultat d'un parseur, clé composée · ❌ deux valeurs évidentes et locales (`quotient, reste = divmod(…)`) : un tuple suffit.

```python
# Exemple 1 : des champs, pas des positions
from dataclasses import dataclass
@dataclass(frozen=True)
class PartStats:
    count: int
    sha256: str
s = PartStats(count=3, sha256="bbdf3f0a")
s.sha256          # → "bbdf3f0a"
```

```python
# Exemple 2 : affichage lisible
from dataclasses import dataclass

@dataclass(frozen=True)
class PartStats:
    count: int
    gz_bytes: int

repr(PartStats(3, 120))
# → "PartStats(count=3, gz_bytes=120)"
```

- Quiz : Avec l'exemple 1, que fait `s[0]` ?
- [ ] Rend `3`
- [x] `TypeError` : pas indexable
- [ ] Rend `"count"`
- [ ] `IndexError`
- Réponse : `TypeError` : pas indexable : une dataclass n'est pas une séquence ; `NamedTuple` l'est, ou `dataclasses.astuple(s)[0]`.

## 6. dataclass : comparer d'un bloc dans un test
- Id : classes-dataclass-egalite-test
- Sous-thème : dataclass
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Prérequis : classes-dataclass-generee, tests-assert-introspection
- Mots-clés : dataclass, pytest, assert
- Source : data-platform · S1-07
- Définition : Le `__eq__` généré compare tous les champs, dans l'ordre, entre objets de la même classe : un test vérifie le résultat entier en une assertion.
- Contexte : Le test du writer fait `assert stats == PartStats(count=3, sha256=..., raw_bytes=..., gz_bytes=...)` : un seul `assert`, et pytest affiche le champ qui diffère. L'égalité exige la même classe : une dataclass n'est jamais égale à un tuple ni à un dict de mêmes valeurs. C'est une égalité de valeur, pas d'identité (`is`).
- Usage : ✅ `assert resultat == Attendu(...)` dans les tests · ❌ comparer champ par champ en plusieurs `assert`, ou à un dict : convertir avec `asdict` si besoin.

```python
# Exemple 1 : égalité champ par champ
from dataclasses import dataclass
@dataclass(frozen=True)
class P:
    count: int
    sha256: str
P(3, "ab") == P(3, "ab")    # → True
P(3, "ab") is P(3, "ab")    # → False
```

```python
# Exemple 2 : une assertion de test
from dataclasses import dataclass

@dataclass(frozen=True)
class P:
    count: int
    sha256: str

def ecrire():
    return P(count=3, sha256="ab")

assert ecrire() == P(count=3, sha256="ab")
```

- Quiz : Avec l'exemple 1, que vaut `P(3, "ab") == (3, "ab")` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : le `__eq__` généré rend `NotImplemented` pour une autre classe, et Python conclut à l'inégalité.

## 7. @x.setter : écrire une propriété
- Id : classes-property-setter
- Sous-thème : propriétés
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : classes-property-getter
- Mots-clés : @property, Pydantic
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

## 8. @dataclass(frozen=True) : objet figé
- Id : classes-dataclass-frozen
- Sous-thème : dataclass
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : classes-dataclass-generee
- Voir aussi : collections-hashable, validation-frozen
- Mots-clés : dataclass, hashable
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

## 9. @abstractmethod : imposer une méthode
- Id : classes-abstractmethod-contrat
- Sous-thème : méthodes
- Type : concept
- Niveau : 2
- Profils : web, data
- Mots-clés : ABC, métaclasse, Protocol, mypy
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

## 10. _nom ou __nom : privé par convention
- Id : classes-prive-par-convention
- Sous-thème : propriétés
- Type : piège
- Niveau : 2
- Profils : débutant, web
- Mots-clés : name mangling, méthode spéciale
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

## 11. dataclass : sans annotation, pas de champ
- Id : classes-dataclass-sans-annotation
- Sous-thème : dataclass
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : classes-dataclass-generee
- Mots-clés : dataclass, annotation de type, ClassVar
- Source : data-platform · S1-07
- Définition : Seuls les attributs **annotés** deviennent des champs d'une dataclass ; `x = 5` sans type reste un simple attribut de classe, absent de `__init__`.
- Contexte : Le décorateur lit `__annotations__` de la classe, pas ses affectations. Oublier l'annotation ne lève rien : le champ manque de `__init__`, de `__repr__` et de `__eq__`. Une constante partagée s'écrit volontairement sans annotation, ou avec `ClassVar[int]` pour l'annoncer. En TS, `x = 5` dans une classe crée bien un champ d'instance : réflexe trompeur.
- Usage : ✅ annoter chaque champ, `ClassVar` pour une vraie constante de classe · ❌ `niveau = 6` dans une dataclass en pensant ajouter un champ avec défaut : `niveau: int = 6`.

```python
# Exemple 1 : x n'est pas un champ
from dataclasses import dataclass, fields
@dataclass
class C:
    x = 5
    y: int = 1
[f.name for f in fields(C)]   # → ["y"]
```

```python
# Exemple 2 : ClassVar pour une constante
from dataclasses import dataclass, fields
from typing import ClassVar

@dataclass
class Writer:
    NIVEAU: ClassVar[int] = 6
    nom: str

[f.name for f in fields(Writer)]  # → ["nom"]
Writer("part").NIVEAU             # → 6
```

- Quiz : Avec l'exemple 1, que fait `C(2, 3)` ?
- [ ] `C(x=2, y=3)`
- [ ] `C(y=2)` : 3 est ignoré
- [x] `TypeError`
- Réponse : `TypeError` : `__init__` n'a qu'un paramètre, `y` ; `x` n'est pas un champ.

## 12. frozen : figé en surface seulement
- Id : classes-frozen-en-surface
- Sous-thème : dataclass
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : classes-dataclass-frozen
- Voir aussi : collections-copie-superficielle-profonde
- Mots-clés : dataclass, hashable, immuable
- Source : data-platform · S1-07
- Définition : `frozen=True` interdit de réaffecter un champ, pas de modifier l'objet qu'il contient : une liste dans une dataclass figée reste modifiable.
- Contexte : Comme `Readonly<T>` en TS, le gel est superficiel : `stats.lignes = []` lève, `stats.lignes.append(...)` passe. Pire, le `__hash__` généré hache les champs : avec une liste dedans, `hash(obj)` lève `TypeError: unhashable type: 'list'`, alors que l'objet est « figé ». Pour un vrai objet immuable : des champs immuables (`tuple`, `frozenset`, `str`).
- Usage : ✅ champs `tuple` ou `frozenset` dans une dataclass figée · ❌ `list` ou `dict` dans une dataclass figée qu'on veut mettre dans un set ou une clé de dict.

```python
# Exemple 1 : la liste bouge encore
from dataclasses import dataclass
@dataclass(frozen=True)
class Lot:
    sirens: list
lot = Lot(["483609327"])
lot.sirens.append("552100554")
len(lot.sirens)       # → 2
```

```python
# Exemple 2 : un tuple, vraiment figé
from dataclasses import dataclass

@dataclass(frozen=True)
class Lot:
    sirens: tuple

a = Lot(("483609327",))
b = Lot(("483609327",))
len({a, b})           # → 1
```

- Quiz : Avec la `Lot` de l'exemple 1, que fait `hash(lot)` ?
- [ ] Rend un entier : l'objet est figé
- [x] `TypeError`
- [ ] Rend `hash(id(lot))`
- Réponse : `TypeError` : le hash figé combine les hash des champs, et une `list` n'est pas hachable.

## 13. dataclass : un défaut, puis plus de champ sans défaut
- Id : classes-dataclass-ordre-defauts
- Sous-thème : dataclass
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : classes-dataclass-generee
- Voir aussi : classes-dataclass-kw-only
- Mots-clés : dataclass, argument nommé
- Source : data-platform · S1-07
- Définition : Un champ sans valeur par défaut ne peut pas suivre un champ qui en a une : la classe lève `TypeError` dès sa définition.
- Contexte : Les champs deviennent les paramètres de `__init__`, dans l'ordre : `def __init__(self, a=1, b)` est impossible en Python. Ajouter un champ obligatoire à la fin d'une dataclass dont le dernier champ a un défaut casse donc l'import du module. Solutions : réordonner, ou `kw_only=True` (3.10+), qui rend les paramètres nommés et lève la contrainte.
- Usage : ✅ champs obligatoires d'abord, puis ceux avec défaut ; `kw_only=True` pour une dataclass qui grandit · ❌ ajouter un champ obligatoire en dernier sans vérifier l'ordre.

```python
# Exemple 1 : refusé à la définition
from dataclasses import dataclass
try:
    @dataclass
    class Part:
        niveau: int = 6
        chemin: str
except TypeError as e:
    erreur = str(e)
"follows default" in erreur   # → True
```

```python
# Exemple 2 : réordonner les champs
from dataclasses import dataclass

@dataclass
class Part:
    chemin: str
    niveau: int = 6

Part("part-0001.jsonl.gz").niveau   # → 6
```

- Quiz : Même classe que l'exemple 1, mais `@dataclass(kw_only=True)` : que fait `Part(chemin="p.gz")` ?
- [ ] `TypeError` : ordre des champs
- [x] Crée `Part(niveau=6, chemin="p.gz")`
- [ ] Crée `Part(chemin="p.gz")` sans `niveau`
- Réponse : Crée `Part(niveau=6, chemin="p.gz")` : avec `kw_only`, tous les paramètres sont nommés, l'ordre défaut / sans défaut ne compte plus.

## 14. kw_only : imposer les noms à l'appel
- Id : classes-dataclass-kw-only
- Sous-thème : dataclass
- Type : recette
- Niveau : 2
- Profils : data
- Mots-clés : dataclass, argument positionnel, argument nommé
- Source : data-platform · S1-07
- Définition : `@dataclass(kw_only=True)` (Python 3.10+) oblige à nommer chaque argument : `PartStats(count=3, …)` passe, `PartStats(3, …)` lève `TypeError`.
- Contexte : Avec quatre entiers (`count`, `raw_bytes`, `gz_bytes`…), un appel positionnel `PartStats(3, "…", 120, 40)` inverse facilement deux tailles sans erreur. `kw_only` rend l'appel lisible et robuste à un réordonnancement des champs. `field(kw_only=True)` le fait pour un seul champ, et `_: KW_ONLY` pour tous les champs qui suivent.
- Usage : ✅ plusieurs champs de même type, dataclass publique d'un package · ❌ petite valeur à 1 ou 2 champs évidents (`Siren("483609327")`) : le positionnel reste clair.

```python
# Exemple 1 : noms obligatoires
from dataclasses import dataclass
@dataclass(kw_only=True, frozen=True)
class Tailles:
    raw: int
    gz: int
Tailles(raw=556, gz=44).gz   # → 44
Tailles(556, 44)  # ❌ TypeError
```

```python
# Exemple 2 : à partir d'un champ, avec KW_ONLY
from dataclasses import KW_ONLY, dataclass

@dataclass
class Part:
    chemin: str
    _: KW_ONLY
    niveau: int = 6

Part("p.gz", niveau=9).niveau    # → 9
```

- Quiz : Avec l'exemple 2, que fait `Part("p.gz", 9)` ?
- [ ] Crée `Part(chemin="p.gz", niveau=9)`
- [x] `TypeError`
- [ ] Ignore `9` et garde `niveau=6`
- Réponse : `TypeError` : après `_: KW_ONLY`, `niveau` ne peut être passé que par son nom.

## 15. order=True : trier des dataclasses
- Id : classes-dataclass-order
- Sous-thème : dataclass
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : classes-dataclass-generee
- Voir aussi : decorateurs-total-ordering, collections-sorted-plusieurs-cles
- Mots-clés : dataclass, fonction lambda
- Source : data-platform · S1-07
- Définition : `@dataclass(order=True)` génère `<`, `<=`, `>`, `>=` qui comparent les champs dans leur ordre de déclaration, comme des tuples.
- Contexte : Sans `order`, `sorted(liste_de_dataclasses)` lève `TypeError`. Avec, le premier champ décide, puis le second en cas d'égalité : l'ordre de déclaration devient un ordre de tri, à choisir exprès (`jour` avant `numero`). Pour un tri ponctuel sur un autre critère, `sorted(xs, key=lambda x: x.numero)` sans `order`.
- Usage : ✅ clé composée triée naturellement (jour, tribunal, numéro), `min` et `max` directs · ❌ `order=True` sur une classe dont l'ordre des champs n'a pas de sens de tri : `key=` explicite.

```python
# Exemple 1 : trier par jour puis numéro
from dataclasses import dataclass
@dataclass(order=True, frozen=True)
class Cle:
    jour: str
    numero: int
cles = [Cle("2026-10-21", 1), Cle("2026-10-20", 2)]
min(cles).jour         # → "2026-10-20"
```

```python
# Exemple 2 : sans order, pas de tri
from dataclasses import dataclass

@dataclass(frozen=True)
class Cle:
    jour: str

sorted([Cle("b"), Cle("a")])  # ❌ TypeError
```

- Quiz : Avec l'exemple 1, que vaut `Cle("2026-10-20", 9) < Cle("2026-10-20", 10)` ?
- [ ] `False` : `"9"` > `"10"`
- [x] `True`
- [ ] `TypeError`
- Réponse : `True` : à jour égal, on compare `numero`, un `int` : 9 < 10 ; la comparaison n'est lexicale que pour les `str`.

## 16. @cached_property : calculer une fois
- Id : classes-cached-property
- Sous-thème : propriétés
- Type : concept
- Niveau : 3
- Profils : data, expert
- Prérequis : classes-property-getter
- Voir aussi : decorateurs-choisir-cache
- Mots-clés : __dict__, @property, @cache
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

## 17. __post_init__ : dans une dataclass figée
- Id : classes-post-init-frozen
- Sous-thème : dataclass
- Type : recette
- Niveau : 3
- Profils : expert
- Prérequis : classes-dataclass-frozen
- Mots-clés : dataclass, méthode spéciale
- Source : data-platform · S1-07
- Définition : `__post_init__` s'exécute après le `__init__` généré ; dans une dataclass figée, y affecter `self.x` lève `FrozenInstanceError`, il faut `object.__setattr__`.
- Contexte : Le gel passe par un `__setattr__` qui lève toujours, y compris pendant la construction. Pour un champ dérivé (`nb = len(sirens)`), déclarer le champ avec `field(init=False)` et l'écrire par `object.__setattr__(self, "nb", …)`, qui contourne le `__setattr__` de la classe. Valider (lever `ValueError`) dans `__post_init__` ne pose aucun problème : seule l'écriture est bloquée.
- Usage : ✅ valider ou normaliser à la construction (SIREN sur 9 chiffres), champ dérivé d'objet figé · ❌ `object.__setattr__` hors de `__post_init__` : c'est casser le gel.

```python
# Exemple 1 : écrire un champ dérivé
from dataclasses import dataclass, field
@dataclass(frozen=True)
class Lot:
    sirens: tuple
    nb: int = field(init=False)
    def __post_init__(self):
        object.__setattr__(self, "nb", len(self.sirens))
Lot(("483609327", "552100554")).nb   # → 2
```

```python
# Exemple 2 : self.x = … est refusé
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Lot:
    sirens: tuple
    nb: int = field(init=False)

    def __post_init__(self):
        self.nb = len(self.sirens)

Lot(("483609327",))  # ❌ FrozenInstanceError
```

- Quiz : `FrozenInstanceError` hérite de quelle exception ?
- [ ] `TypeError`
- [ ] `ValueError`
- [x] `AttributeError`
- [ ] `RuntimeError`
- Réponse : `AttributeError` : comme pour une propriété sans setter ; un `except AttributeError` l'attrape.

## 18. slots=True : plus d'attribut inventé
- Id : classes-dataclass-slots
- Sous-thème : dataclass
- Type : concept
- Niveau : 3
- Profils : expert
- Mots-clés : dataclass, __dict__
- Source : data-platform · S1-07
- Définition : `@dataclass(slots=True)` (3.10+) génère `__slots__` : pas de `__dict__`, moins de mémoire, et un attribut mal orthographié lève au lieu d'être créé.
- Contexte : Sans slots, `stats.gz_byte = 10` (sans `s`) crée en silence un nouvel attribut : bug invisible, là où TS refuserait la compilation. Avec slots, `AttributeError`. Chaque instance pèse aussi moins (pas de dict), utile pour des millions d'objets en mémoire. Combinable avec `frozen=True`.
- Usage : ✅ dataclass non figée qu'on modifie (protège des fautes de frappe), très nombreuses instances · ❌ code qui ajoute des attributs dynamiques ou utilise `__dict__` / `vars(obj)`.

```python
# Exemple 1 : faute de frappe refusée
from dataclasses import dataclass
@dataclass(slots=True)
class Stats:
    gz_bytes: int = 0
s = Stats()
s.gz_byte = 10  # ❌ AttributeError
```

```python
# Exemple 2 : sans slots, accepté en silence
from dataclasses import dataclass

@dataclass
class Stats:
    gz_bytes: int = 0

s = Stats()
s.gz_byte = 10        # crée un attribut
s.gz_bytes            # → 0
```

- Quiz : Avec la `Stats` de l'exemple 1, que vaut `hasattr(Stats(), "__dict__")` ?
- [ ] `True`
- [x] `False`
- [ ] `AttributeError`
- Réponse : `False` : les attributs sont rangés dans des slots fixes, sans dictionnaire par instance.

## 19. field(compare=False) : un champ hors de l'égalité
- Id : classes-field-compare-false
- Sous-thème : dataclass
- Type : recette
- Niveau : 3
- Profils : data, expert
- Prérequis : classes-dataclass-egalite-test
- Mots-clés : dataclass, hash
- Source : data-platform · S1-07
- Définition : `field(compare=False)` exclut un champ de `__eq__`, des comparaisons et du hash : deux objets égaux peuvent différer sur ce champ.
- Contexte : Utile pour une donnée annexe qui ne fait pas l'identité : durée d'écriture, chemin temporaire, cache. Deux `PartStats` du même contenu restent égales même si l'écriture a pris 0,8 s puis 1,1 s. Dans une dataclass figée, un champ `dict` ou `list` doit aussi être exclu du hash, sinon `hash()` lève : `compare=False` le fait (ou `hash=False` seul).
- Usage : ✅ métadonnée technique (durée, chemin `/tmp`) à côté de champs d'identité · ❌ exclure un champ qui distingue vraiment deux valeurs : l'égalité ment.

```python
# Exemple 1 : la durée ne compte pas
from dataclasses import dataclass, field
@dataclass(frozen=True)
class Stats:
    sha256: str
    duree: float = field(compare=False)
Stats("bbdf", 0.8) == Stats("bbdf", 1.1)   # → True
```

```python
# Exemple 2 : un dict hors du hash
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Part:
    sha256: str
    meta: dict = field(default_factory=dict,
                       compare=False)

len({Part("ab", {"t": 1}), Part("ab")})   # → 1
```

- Quiz : Exemple 2 sans `compare=False` sur `meta` : que fait `hash(Part("ab"))` ?
- [ ] Rend un entier
- [ ] Hache seulement `sha256`
- [x] `TypeError`
- Réponse : `TypeError` : le hash figé inclut `meta`, un `dict`, qui n'est pas hachable.

## 20. héritage : figée ou pas, toute la lignée
- Id : classes-heritage-frozen
- Sous-thème : dataclass
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : classes-dataclass-frozen
- Mots-clés : dataclass
- Source : data-platform · S1-07
- Définition : Une dataclass figée ne peut hériter que d'une dataclass figée, et inversement : mélanger les deux lève `TypeError` à la définition.
- Contexte : Le gel repose sur un `__setattr__` posé sur la classe : une sous-classe non figée d'une classe figée aurait des champs à moitié protégés. Python refuse donc le mélange, dans les deux sens (`cannot inherit non-frozen dataclass from a frozen one`). Ajouter `frozen=True` à une classe de base oblige à le faire sur toutes ses sous-classes.
- Usage : ✅ décider du gel pour toute une hiérarchie (événements, annonces) · ❌ geler une classe de base partagée sans vérifier ses sous-classes.

```python
# Exemple 1 : le mélange est refusé
from dataclasses import dataclass
@dataclass(frozen=True)
class Annonce:
    id: str
try:
    @dataclass
    class Radiation(Annonce):
        motif: str
except TypeError as e:
    erreur = str(e)
"non-frozen" in erreur      # → True
```

```python
# Exemple 2 : figées toutes les deux
from dataclasses import dataclass

@dataclass(frozen=True)
class Annonce:
    id: str

@dataclass(frozen=True)
class Radiation(Annonce):
    motif: str

Radiation("A1", "cessation").id   # → "A1"
```

- Quiz : Une classe ordinaire (sans `@dataclass`) hérite d'une dataclass figée. Que fait `obj.id = "A2"` sur une instance ?
- [ ] Réaffecte : la sous-classe n'est pas figée
- [x] `FrozenInstanceError`
- [ ] `TypeError` à la définition de la classe
- Réponse : `FrozenInstanceError` : la sous-classe hérite du `__setattr__` qui lève ; seule une sous-classe `@dataclass` non figée est refusée.
