"""Import gratuit, sans IA.

Transforme la légende d'une vidéo (TikTok, YouTube…), du texte collé et le texte
lu sur des captures d'écran (OCR Tesseract) en brouillon de fiche recette :
titre, ingrédients, étapes, saisons, catégorie, temps et portions.
"""

from __future__ import annotations

import io
import re
import shutil
import unicodedata

from PIL import Image, ImageOps

# --------------------------------------------------------------------------
# Lecture de texte sur image (OCR)
# --------------------------------------------------------------------------
OCR_AVAILABLE = bool(shutil.which("tesseract"))


def ocr_image(raw: bytes) -> str:
    if not OCR_AVAILABLE:
        return ""
    try:
        import pytesseract
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("L")
        if max(img.size) < 1600:  # agrandir aide Tesseract
            scale = 1600 / max(img.size)
            img = img.resize((int(img.width * scale), int(img.height * scale)))
        txt = pytesseract.image_to_string(img, lang="fra", config="--psm 6")
        lines = [ln.strip() for ln in txt.splitlines()]
        # on garde les lignes qui ressemblent à du texte (au moins 3 lettres)
        return "\n".join(ln for ln in lines if len(re.findall(r"[A-Za-zÀ-ÿ]", ln)) >= 3)
    except Exception:  # noqa: BLE001
        return ""


# --------------------------------------------------------------------------
# Nettoyage du texte
# --------------------------------------------------------------------------
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002190-\U000021FF\U00002300-\U000027BF\U00002B00-\U00002BFF"
    "\U0000FE00-\U0000FE0F\U0000200D\U000020E3]+"
)
GENERIC_TAGS = {
    "fyp", "foryou", "foryoupage", "pourtoi", "pourtoii", "viral", "tiktok", "tiktokfood", "food", "foodtiktok",
    "recette", "recettes", "recettefacile", "recettesimple", "recetterapide", "cuisine", "cuisinetiktok",
    "cooking", "recipe", "recipes", "easyrecipe", "yummy", "miam", "faitmaison", "homemade", "fypシ", "xyzbca",
    "trend", "trending", "apprendresurtiktok", "learnontiktok", "foodie", "cuisinefacile", "cuisinefrancaise",
}


def extract_tags(text: str) -> list[str]:
    tags = []
    for t in re.findall(r"#([\wÀ-ÿ]+)", text):
        tl = t.lower()
        if tl not in GENERIC_TAGS and tl not in tags and len(tl) <= 25:
            tags.append(tl)
    return tags[:4]


def normalize(text: str) -> str:
    text = re.sub(r"#[\wÀ-ÿ]+", " ", text)            # hashtags
    text = re.sub(r"@[\w.]+", " ", text)               # mentions
    text = re.sub(r"https?://\S+", " ", text)          # liens
    text = EMOJI_RE.sub("\n", text)                    # les emojis servent souvent de puces
    text = re.sub(r"[•▪◦●○►▶➡→✔✓☑✅]", "\n", text)
    text = re.sub(r"(?<=\s)[-–—*]\s+", "\n", text)     # « - 200 g farine » en milieu de ligne
    text = re.sub(r"(?:^|\s)(\d{1,2})\s*[).]\s+(?=[A-Za-zÀ-ÿ])", r"\n\1. ", text)  # « 1) Mélanger »
    text = text.replace("\r", "")
    lines = [re.sub(r"[ \t]+", " ", ln).strip(" .,;:-–—*") for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


# --------------------------------------------------------------------------
# Ingrédients
# --------------------------------------------------------------------------
UNIT_RE = re.compile(
    r"^(kg|mg|g|gr|grammes?|ml|cl|dl|l|litres?|c\.?\s?à\s?s\.?|c\.?\s?à\s?c\.?|càs|càc|cas|cac|cs|cc|"
    r"cuill[eè]res?\s+à\s+soupe|cuill[eè]res?\s+à\s+caf[eé]|pinc[ée]es?|sachets?|tranches?|gousses?|brins?|"
    r"verres?|tasses?|bottes?|feuilles?|bo[iî]tes?|pots?|poign[ée]es?|filets?|morceaux?|noix|noisettes?|"
    r"rouleaux?|pâtes?\s+feuillet[ée]es?|cubes?|briques?|bouquets?|branches?|zestes?)(?=[\s.]|$)\.?\s*",
    re.I,
)
QTY_RE = re.compile(r"^(\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?(?!\d)|[½¼¾⅓⅔]|(?:un|une|deux|trois|quatre|cinq|six|demi)\b)\s*", re.I)
WORD_NUM = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "demi": 0.5}
FRAC = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3}


def _norm_unit(u: str) -> str:
    x = re.sub(r"\s+", " ", u.lower())
    if re.fullmatch(r"c\.?\s?à\s?s\.?|càs|cas|cs|cuill[eè]res?\s+à\s+soupe", x):
        return "c. à s."
    if re.fullmatch(r"c\.?\s?à\s?c\.?|càc|cac|cc|cuill[eè]res?\s+à\s+caf[eé]", x):
        return "c. à c."
    if x in ("gr", "gramme", "grammes"):
        return "g"
    if x in ("litre", "litres"):
        return "l"
    return x


def _to_num(s: str):
    s = s.lower().replace(" ", "")
    if s in FRAC:
        return FRAC[s]
    if s in WORD_NUM:
        return WORD_NUM[s]
    if "/" in s:
        a, b = s.split("/", 1)
        try:
            return float(a) / float(b)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def parse_ingredient(line: str) -> dict:
    s = line.strip()
    qty, unit, rest = None, "", s
    m = QTY_RE.match(s)
    if m:
        qty = _to_num(m.group(1))
        rest = s[m.end():]
        # « 200g » collé
        u = UNIT_RE.match(rest)
        if u:
            unit = _norm_unit(u.group(1))
            rest = rest[u.end():]
        rest = re.sub(r"^(de |d['’]|d’)", "", rest, flags=re.I)
    else:
        # « Farine : 200 g » ou « farine 200g »
        m2 = re.match(r"^(.+?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Zàé.]{0,12})$", s)
        if m2 and len(m2.group(1)) > 2:
            u = UNIT_RE.match(m2.group(3) + " ") if m2.group(3) else None
            if u or not m2.group(3):
                qty = _to_num(m2.group(2))
                unit = _norm_unit(u.group(1)) if u else ""
                rest = m2.group(1)
    name = rest.strip(" :,-").strip()
    return {"qty": qty, "unit": unit, "name": (name or s)[:200]}


# --------------------------------------------------------------------------
# Classement des lignes
# --------------------------------------------------------------------------
VERBS = (
    "ajout", "mélang", "melang", "mettre", "mets", "met ", "verse", "verser", "coupe", "couper", "émince", "emince",
    "fais", "faire", "faites", "cuire", "cuis", "laisse", "laisser", "enfourne", "enfourner", "préchauff", "prechauff",
    "mixe", "mixer", "bat", "battre", "fouette", "fouetter", "incorpore", "incorporer", "dépose", "depose", "disposer",
    "dispose", "étale", "etale", "étaler", "etaler", "réserve", "reserver", "réserver", "sale", "saler", "poivre ",
    "poivrer", "épluche", "eplucher", "éplucher", "râpe", "raper", "râper", "hache", "hacher", "fais revenir",
    "faire revenir", "fais fondre", "faire fondre", "porte", "porter", "égoutte", "egoutter", "égoutter", "servir",
    "sers", "dégust", "degust", "recouvre", "recouvrir", "forme", "former", "roule", "rouler", "plie", "plier",
    "badigeonne", "badigeonner", "assaisonne", "assaisonner", "retire", "retirer", "sors", "sortir", "pose", "poser",
    "garnis", "garnir", "remplis", "remplir", "étape", "etape", "ensuite", "puis", "enfin", "pendant", "une fois",
    "dans un", "dans une", "sur une", "sur un", "au four", "à feu", "a feu",
)
ING_HEAD = re.compile(r"^(ingr[ée]dients?|il (?:te|vous|nous) faut|liste|pour la (?:p[âa]te|sauce|garniture|cr[èe]me)|"
                      r"pour \d+\s*(?:personnes?|pers|parts?|portions?))\b\s*[:\-]?\s*", re.I)
STEP_HEAD = re.compile(r"^(pr[ée]paration|[ée]tapes?|instructions?|m[ée]thode|d[ée]roul[ée]|r[ée]alisation|"
                       r"la recette|recette)\b\s*[:\-]?\s*", re.I)
META = re.compile(r"^(temps de )?(cuisson|pr[ée]paration|repos)\s*:?\s*\d+\s*(min|mn|h)\b[^.]{0,20}$", re.I)
NOISE = re.compile(r"(abonne|follow|like|partage|commente|enregistre|lien en bio|link in bio|code promo|"
                   r"sponsoris|collab|pub\b|ad\b|dis[- ]moi|tague|mentionne|n'h[ée]site|merci)", re.I)


def looks_like_step(line: str) -> bool:
    low = line.lower()
    if re.match(r"^\d{1,2}\.\s", line):
        return True
    if len(line) > 90:
        return True
    return any(low.startswith(v) or f" {v}" in low[:40] for v in VERBS) and len(line) > 18


def looks_like_ingredient(line: str) -> bool:
    if len(line) > 80:
        return False
    if QTY_RE.match(line) and not re.match(r"^\d{1,2}\.\s", line):
        return True
    if re.search(r"\d+\s*(g|gr|kg|ml|cl|l|c\.?\s?à\s?[sc])\b", line, re.I):
        return True
    return False


# --------------------------------------------------------------------------
# Saisons, catégorie, temps
# --------------------------------------------------------------------------
SEASON_WORDS = {
    "printemps": ["asperge", "petits pois", "petit pois", "radis", "fraise", "rhubarbe", "artichaut", "feve",
                  "ail des ours", "cresson", "agneau", "oseille", "morille", "printemps"],
    "ete": ["tomate", "courgette", "aubergine", "poivron", "melon", "pasteque", "peche", "abricot", "cerise",
            "framboise", "myrtille", "basilic", "concombre", "mais", "nectarine", "mure", "groseille", "gaspacho",
            "barbecue", "bbq", "ratatouille", "ete", "estival", "glace", "sorbet"],
    "automne": ["potiron", "potimarron", "courge", "butternut", "citrouille", "champignon", "cepe", "girolle",
                "chataigne", "marron", "pomme", "poire", "raisin", "coing", "figue", "patate douce", "noix",
                "automne", "halloween"],
    "hiver": ["poireau", "chou", "endive", "celeri", "panais", "topinambour", "orange", "clementine", "mandarine",
              "pamplemousse", "kiwi", "raclette", "fondue", "tartiflette", "vin chaud", "pot-au-feu", "pot au feu",
              "chocolat chaud", "galette des rois", "buche", "noel", "hiver", "blanquette", "bourguignon",
              "choucroute", "cassoulet", "potee"],
}
CATEGORY_WORDS = [
    ("Boisson", ["smoothie", "cocktail", "mocktail", "jus ", "latte", "milkshake", "limonade", "boisson",
                 "chocolat chaud", "the glace", "vin chaud", "sirop"]),
    ("Petit-déj", ["pancake", "porridge", "granola", "overnight", "petit-dej", "petit dej", "brunch", "bowl cake",
                   "pain perdu", "petit dejeuner"]),
    ("Dessert", ["gateau", "cake au chocolat", "tarte au citron", "tarte aux pommes", "tarte tatin", "cookie",
                 "brownie", "crepe", "mousse au chocolat", "tiramisu", "cheesecake", "fondant", "muffin", "flan",
                 "creme brulee", "panna cotta", "dessert", "biscuit", "madeleine", "beignet", "donut", "glace",
                 "sorbet", "crumble", "clafoutis", "moelleux", "cupcake", "macaron", "chou a la creme", "buche",
                 "sucre glace", "pepites de chocolat", "galette des rois", "banana bread", "riz au lait"]),
    ("Apéro", ["apero", "aperitif", "dip", "houmous", "hummus", "tapenade", "verrine", "toast", "tartinade",
               "guacamole", "chips", "feuillete", "bouchee", "tapas", "rillettes"]),
    ("Sauce", ["sauce", "vinaigrette", "pesto", "mayonnaise", "aioli", "coulis", "marinade"]),
    ("Entrée", ["soupe", "veloute", "salade", "gaspacho", "entree", "carpaccio", "tartare de", "oeuf mimosa"]),
    ("Accompagnement", ["puree", "gratin dauphinois", "frites", "accompagnement", "legumes rotis", "riz pilaf",
                        "poelee"]),
]


def guess_seasons(text: str) -> list[str]:
    t = _strip_accents(text)
    scores = {}
    for season, words in SEASON_WORDS.items():
        n = sum(1 for w in words if re.search(rf"\b{re.escape(w)}s?\b", t))
        if n:
            scores[season] = n
    if not scores:
        return []
    best = max(scores.values())
    return [s for s in ("printemps", "ete", "automne", "hiver") if scores.get(s, 0) >= max(1, best - 1)][:2]


def guess_category(title: str, text: str) -> str:
    for source in (_strip_accents(title), _strip_accents(text)):
        for cat, words in CATEGORY_WORDS:
            if any(w in source for w in words):
                return cat
    return "Plat"


def guess_times(text: str) -> tuple[int | None, int | None, int | None]:
    t = _strip_accents(text)
    prep = cook = serv = None

    def minutes(m):
        h = int(m.group(1)) if m.group(1) else 0
        mn = int(m.group(2)) if m.group(2) else 0
        return h * 60 + mn

    dur = r"(?:(\d{1,2})\s*h\s*)?(?:(\d{1,3})\s*(?:min|mn|minutes?))?"
    m = re.search(r"preparation\s*:?\s*" + dur, t)
    if m and (m.group(1) or m.group(2)):
        prep = minutes(m)
    m = re.search(r"cuisson\s*:?\s*" + dur, t)
    if m and (m.group(1) or m.group(2)):
        cook = minutes(m)
    if cook is None:
        found = [int(x) for x in re.findall(r"(\d{1,3})\s*(?:min|mn|minutes?)\b(?=[^.\n]{0,40}(?:four|cuire|cuisson|poele|feu))", t)]
        found += [int(x) for x in re.findall(r"(?:four|cuire|cuisson|enfourne)[^.\n]{0,40}?(\d{1,3})\s*(?:min|mn|minutes?)\b", t)]
        if found:
            cook = max(found)
    m = re.search(r"pour\s*(\d{1,2})\s*(?:personnes?|pers|parts?|portions?|gourmands?)", t) or \
        re.search(r"(\d{1,2})\s*(?:personnes|parts|portions)\b", t)
    if m:
        serv = int(m.group(1))
    return prep, cook, serv


# --------------------------------------------------------------------------
# Assemblage
# --------------------------------------------------------------------------
def make_title(lines: list[str], author: str) -> str:
    for ln in lines[:4]:
        if ING_HEAD.match(ln) or STEP_HEAD.match(ln) or NOISE.search(ln) or looks_like_ingredient(ln):
            continue
        t = re.split(r"(?<=[.!?])\s", ln)[0].strip(" !.?:")
        t = re.sub(r"^(recette( de| du| des)?|ma recette( de| du| des)?)\s+", "", t, flags=re.I)
        t = re.sub(r"\s+pour\s+\d+\s*(personnes?|pers|parts?|portions?)\b.*$", "", t, flags=re.I)
        if len(t) > 70:
            t = t[:70].rsplit(" ", 1)[0] + "…"
        if len(t) >= 3:
            return t[0].upper() + t[1:]
    return f"Recette de {author}" if author else "Nouvelle recette"


def parse_recipe_text(caption: str, extra: str = "", ocr: str = "", author: str = "") -> dict:
    raw_all = "\n".join(x for x in (caption, extra, ocr) if x)
    tags = extract_tags(raw_all)
    text = normalize(raw_all)
    lines = [ln for ln in text.split("\n") if ln and not NOISE.search(ln)]

    title = make_title(lines, author)
    ingredients, steps, others = [], [], []
    mode = None
    for ln in lines:
        h = ING_HEAD.match(ln)
        if h:
            mode = "ing"
            ln = ln[h.end():].strip()
            if not ln:
                continue
        h = STEP_HEAD.match(ln)
        if h and not looks_like_ingredient(ln):
            mode = "step"
            ln = ln[h.end():].strip()
            if not ln:
                continue
        if ln == title or ln.rstrip("…") == title.rstrip("…") or ln.startswith(title.rstrip("…")):
            continue
        if META.match(ln):
            continue
        if mode == "ing" and not looks_like_step(ln):
            # « 200 g farine, 2 œufs, sel » sur une seule ligne
            parts = [p.strip() for p in re.split(r",|;|\bet\b(?=\s+\d)", ln) if p.strip()]
            ingredients.extend(parts if len(parts) > 1 else [ln])
        elif mode == "step":
            steps.append(ln)
        elif looks_like_ingredient(ln):
            ingredients.append(ln)
        elif looks_like_step(ln):
            steps.append(ln)
        else:
            others.append(ln)

    split_steps = []
    for st in steps:
        split_steps.extend(x for x in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])", st) if x.strip())
    steps = [re.sub(r"^\d{1,2}\.\s*", "", s).strip(" .") for s in split_steps]
    steps = [s[0].upper() + s[1:] for s in steps if len(s) > 2]
    ings = [parse_ingredient(i) for i in ingredients if len(i) > 1]
    # dédoublonnage (OCR + légende peuvent répéter)
    seen, uniq = set(), []
    for i in ings:
        k = _strip_accents(i["name"])[:30]
        if k not in seen:
            seen.add(k)
            uniq.append(i)

    prep, cook, serv = guess_times(raw_all)
    desc = next((o for o in others if 15 <= len(o) <= 200), "")

    found = []
    if uniq:
        found.append(f"{len(uniq)} ingrédient{'s' if len(uniq) > 1 else ''}")
    if steps:
        found.append(f"{len(steps)} étape{'s' if len(steps) > 1 else ''}")
    if found:
        notes = ("Import sans IA, trouvé dans la description : " + " et ".join(found)
                 + ". Vérifie les quantités et l'ordre des étapes.")
    elif raw_all.strip():
        notes = ("La description de la vidéo ne contient pas la recette détaillée. "
                 "Complète les ingrédients et les étapes, ou ajoute des captures d'écran.")
        if not steps and others:
            steps = others[:12]
    else:
        notes = "Rien n'a pu être lu : complète la fiche à la main."

    return {
        "title": title,
        "description": desc,
        "category": guess_category(title, raw_all),
        "seasons": guess_seasons(raw_all),
        "prepMin": prep,
        "cookMin": cook,
        "servings": serv or 4,
        "ingredients": uniq,
        "steps": steps,
        "tips": "",
        "tags": tags,
        "notes": notes,
    }
