"""Liste de courses : fusion des quantités, conversion d'unités et classement par rayon."""

from __future__ import annotations

import re
import unicodedata

# unité -> (unité de base, facteur)
UNITS = {
    "kg": ("g", 1000), "g": ("g", 1), "mg": ("g", 0.001),
    "l": ("ml", 1000), "dl": ("ml", 100), "cl": ("ml", 10), "ml": ("ml", 1),
}
PANTRY = ("sel", "poivre", "eau", "sel et poivre", "sel, poivre", "fleur de sel")

AISLES = [
    ("Fruits et légumes", [
        "pomme", "poire", "banane", "citron", "orange", "clementine", "mandarine", "fraise", "framboise", "myrtille",
        "cerise", "peche", "abricot", "raisin", "kiwi", "ananas", "mangue", "melon", "pasteque", "figue", "avocat",
        "tomate", "courgette", "aubergine", "poivron", "concombre", "salade", "laitue", "roquette", "mache", "epinard",
        "chou", "brocoli", "carotte", "poireau", "oignon", "echalote", "ail", "pomme de terre", "patate", "potiron",
        "potimarron", "courge", "butternut", "champignon", "celeri", "radis", "navet", "panais", "betterave", "fenouil",
        "asperge", "haricot vert", "petits pois", "mais", "gingembre", "persil", "basilic", "coriandre", "menthe",
        "ciboulette", "thym", "romarin", "aneth", "estragon", "citron vert", "endive", "artichaut", "patate douce"]),
    ("Boucherie et poisson", [
        "boeuf", "bœuf", "veau", "porc", "agneau", "poulet", "dinde", "canard", "lapin", "viande", "steak", "escalope",
        "filet mignon", "cote", "roti", "saucisse", "chorizo", "lardon", "jambon", "bacon", "merguez", "poisson",
        "saumon", "thon", "cabillaud", "colin", "crevette", "moule", "calamar", "sardine", "truite", "dorade", "lieu"]),
    ("Crèmerie", [
        "lait", "creme", "beurre", "oeuf", "œuf", "yaourt", "fromage", "mozzarella", "parmesan", "gruyere", "emmental",
        "comte", "feta", "chevre", "ricotta", "mascarpone", "burrata", "camembert", "reblochon", "raclette", "cheddar",
        "creme fraiche", "fromage blanc", "skyr", "pate brisee", "pate feuilletee", "pate sablee", "pate a pizza"]),
    ("Boulangerie", ["pain", "baguette", "brioche", "pain de mie", "tortilla", "wrap", "burger", "pita"]),
    ("Épicerie salée", [
        "pate", "pâtes", "spaghetti", "tagliatelle", "penne", "riz", "semoule", "quinoa", "lentille", "pois chiche",
        "haricot rouge", "farine", "maizena", "fecule", "huile", "vinaigre", "moutarde", "mayonnaise", "ketchup",
        "sauce", "bouillon", "cube", "concentre", "coulis", "conserve", "olive", "capre", "cornichon", "epice",
        "paprika", "cumin", "curry", "curcuma", "muscade", "cannelle", "herbes de provence", "origan", "piment",
        "sel", "poivre", "soja", "gnocchi", "chapelure", "levure", "bicarbonate", "noix", "amande", "noisette",
        "pignon", "graines", "lait de coco", "tomates pelees", "passata"]),
    ("Épicerie sucrée", [
        "sucre", "cassonade", "miel", "sirop", "chocolat", "cacao", "vanille", "confiture", "biscuit", "speculoos",
        "pepites", "sucre glace", "nutella", "praline", "caramel", "gelatine", "agar", "flocons d'avoine", "avoine"]),
    ("Surgelés", ["surgele", "glace", "sorbet"]),
    ("Boissons", ["vin", "biere", "jus", "eau gazeuse", "cidre", "rhum", "whisky", "cognac", "porto", "sirop de"]),
]


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def key_of(name: str) -> str:
    """Nom normalisé pour fusionner « Œufs », « oeuf » et « œuf frais »."""
    k = strip_accents(name).replace("œ", "oe")
    k = re.sub(r"\(.*?\)", " ", k)                 # « bouillon (selon la soupe) »
    k = re.sub(r"[^a-z0-9' ]+", " ", k)
    words = [w[:-1] if len(w) > 3 and w.endswith(("s", "x")) else w for w in k.split()]
    return " ".join(words).strip()


def aisle_of(name: str) -> str:
    n = " " + strip_accents(name).replace("œ", "oe") + " "
    best, best_len = "Autres", 0
    for aisle, words in AISLES:
        for w in words:
            ww = strip_accents(w).replace("œ", "oe")
            if re.search(rf"\b{re.escape(ww)}", n) and len(ww) > best_len:
                best, best_len = aisle, len(ww)      # le mot le plus précis gagne (« lait de coco » > « lait »)
    return best


def to_base(qty, unit: str):
    u = (unit or "").strip().lower()
    if qty is not None and u in UNITS:
        base, f = UNITS[u]
        return qty * f, base
    return qty, u


def display_qty(qty, unit: str) -> tuple[float | None, str]:
    """Remet une quantité de base dans l'unité la plus lisible (1500 g -> 1,5 kg ; 700 ml -> 70 cl)."""
    if qty is None:
        return None, unit
    if unit == "g" and qty >= 1000:
        return round(qty / 1000, 2), "kg"
    if unit == "ml":
        if qty >= 1000:
            return round(qty / 1000, 2), "l"
        if qty >= 10 and abs(qty / 10 - round(qty / 10)) < 1e-6:
            return round(qty / 10, 1), "cl"
    return round(qty, 2), unit


def is_pantry(name: str) -> bool:
    return key_of(name) in {key_of(p) for p in PANTRY}
