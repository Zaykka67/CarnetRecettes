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
        from PIL import ImageStat
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("L")
        if ImageStat.Stat(img).mean[0] < 110:      # mode sombre : texte clair sur fond foncé
            img = ImageOps.invert(img)
        img = ImageOps.autocontrast(img)
        if img.width < 1500:                       # capture de téléphone : on agrandit le petit texte
            scale = 1500 / img.width
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        txt = pytesseract.image_to_string(img, lang="fra", config="--psm 6", timeout=25)
        lines = [ln.strip() for ln in txt.splitlines()]
        return "\n".join(ln for ln in lines if len(re.findall(r"[A-Za-zÀ-ÿ]", ln)) >= 3)
    except Exception:  # noqa: BLE001  (délai dépassé, image illisible…)
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
    if text.count("\n") < 3:                           # légende sur une seule ligne : « - » sert de puce
        text = re.sub(r"(?<=\s)[-–—*]\s+(?=\S)", "\n", text)
    text = re.sub(r"(?m)^\s*[-–—*]\s+", "", text)      # puce en début de ligne
    text = re.sub(r"(?:^|\s)(\d{1,2})\s*[).]\s+(?=[A-Za-zÀ-ÿ])", r"\n\1. ", text)  # « 1) Mélanger »
    text = text.replace("\r", "")
    lines = [re.sub(r"[ \t]+", " ", ln).strip(" .,;:-–—*|[]{}_~<>\\/") for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln and not _is_garbage(ln))


GENERIC_H = re.compile(r"\b[H#](recette\w*|fyp\w*|pourtoi\w*|food\w*|cuisine\w*|viral\w*)\b", re.I)


def _is_garbage(ln: str) -> bool:
    """Ligne de bruit OCR : peu de lettres, mots trop courts, ou hashtags mal lus."""
    if GENERIC_H.search(ln) and len(GENERIC_H.sub("", ln).strip()) < 25:
        return True
    letters = len(re.findall(r"[A-Za-zÀ-ÿ]", ln))
    words = re.findall(r"[A-Za-zÀ-ÿ']+", ln)
    if re.match(r"^(\d+(?:\s*[.,/-]\s*\d+)?|[½¼¾])\s*[a-zA-Zà-ÿ]", ln):   # « 2 c. à s. de sauce » : ingrédient
        return letters < 3
    if letters < 4 or letters / max(1, len(ln.replace(" ", ""))) < 0.6:
        return True
    if len(words) >= 3 and sum(1 for w in words if len(w) <= 2) / len(words) > 0.6:
        return True
    if len(words) <= 3 and all(len(w) <= 2 or w.isupper() for w in words) and len(ln) < 12:
        return True
    # mots sans voyelle ou casse aléatoire (« mnrinA tamatzs ») : texte incrusté mal lu
    weird = sum(1 for w in words if len(w) >= 4 and (not re.search(r"[aeiouyàâéèêëîïôûœ]", w, re.I)
                                                      or re.search(r"[a-zà-ÿ][A-Z]", w)))
    return len(words) >= 3 and weird / len(words) > 0.3


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


# --------------------------------------------------------------------------
# Ingrédients
# --------------------------------------------------------------------------
UNIT_RE = re.compile(
    r"^(kg|mg|g|gr|grammes?|ml|cl|ci|dl|l|litres?|c\.?\s?à\s?s\.?|c\.?\s?à\s?c\.?|càs|càc|cas|cac|cs|cc|"
    r"cuill[eè]res?\s+à\s+soupe|cuill[eè]res?\s+à\s+caf[eé]|pinc[ée]es?|sachets?|tranches?|gousses?|brins?|"
    r"verres?|tasses?|bottes?|feuilles?|bo[iî]tes?|pots?|poign[ée]es?|filets?|morceaux?|noix|noisettes?|"
    r"rouleaux?|pâtes?\s+feuillet[ée]es?|cubes?|briques?|bouquets?|branches?|zestes?)(?=[\s.]|$)\.?\s*",
    re.I,
)
QTY_RE = re.compile(r"^(\d+(?:[.,]\d+)?(?:\s*(?:-|à|a)\s*\d+(?:[.,]\d+)?)?(?:\s*/\s*\d+)?(?!\d)|[½¼¾⅓⅔]|(?:un|une|deux|trois|quatre|cinq|six|demi)\b)\s*", re.I)
WORD_NUM = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "demi": 0.5}
FRAC = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3}


def _norm_unit(u: str) -> str:
    x = re.sub(r"\s+", " ", u.lower())
    if re.fullmatch(r"c\.?\s?à\s?s\.?|càs|cas|cs|cuill[eè]res?\s+à\s+soupe", x):
        return "c. à s."
    if re.fullmatch(r"c\.?\s?à\s?c\.?|càc|cac|cc|cuill[eè]res?\s+à\s+caf[eé]", x):
        return "c. à c."
    if x in ("ci", "c1"):
        return "cl"
    if x in ("gr", "gramme", "grammes"):
        return "g"
    if x in ("litre", "litres"):
        return "l"
    return x


def _to_num(s: str):
    s = s.lower().replace(" ", "")
    rng = re.match(r"^(\d+(?:[.,]\d+)?)(?:-|à|a)(\d+(?:[.,]\d+)?)$", s)
    if rng:  # fourchette : on garde la valeur haute
        s = rng.group(2)
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
        rest = re.sub(r"^[:\-–]\s*", "", rest)
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
NOISE = re.compile(r"(abonne|follow|like|partage|commente|commentaire|enregistre|lien en bio|link in bio|code promo|"
                   r"il y a \d+|voir la traduction|r[ée]pondre|r[ée]ponses?\b|j'aime|ajoutez|ajouter un|"
                   r"son original|original sound|\bvues\b|\bvues?\s*$|tiktok|instagram|"
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
            "framboise", "myrtille", "basilic", "concombre", "nectarine", "mure", "groseille", "gaspacho",
            "barbecue", "bbq", "ratatouille", "ete", "estival", "glace", "sorbet"],
    "automne": ["potiron", "potimarron", "courge", "butternut", "citrouille", "champignon", "cepe", "girolle",
                "chataigne", "marron", "pomme", "poire", "raisin", "coing", "figue", "patate douce", "noix",
                "automne", "halloween", "soupe", "veloute"],
    "hiver": ["poireau", "chou", "endive", "celeri", "panais", "topinambour", "orange", "clementine", "mandarine",
              "pamplemousse", "kiwi", "raclette", "fondue", "tartiflette", "vin chaud", "pot-au-feu", "pot au feu",
              "chocolat chaud", "galette des rois", "buche", "noel", "hiver", "blanquette", "bourguignon",
              "choucroute", "cassoulet", "potee", "soupe", "veloute"],
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
    t = re.sub(r"(sauce|coulis|concentre|puree|pulpe|tomates? pelees?|passata)\s*(de |d')?\s*tomates?", " ", t)
    scores = {}
    for season, words in SEASON_WORDS.items():
        n = sum(1 for w in words if re.search(rf"\b{re.escape(w)}s?\b", t))
        if n:
            scores[season] = n
    if re.search(r"\bma[iï]s (doux|en grains?|grill[ée])|\bmaïs\b", text.lower()):
        scores["ete"] = scores.get("ete", 0) + 1   # « maïs » sans confondre avec « mais »
    if not scores:
        return []
    best = max(scores.values())
    return [s for s in ("printemps", "ete", "automne", "hiver") if scores.get(s, 0) >= max(1, best - 1)][:2]


def guess_category(title: str, text: str) -> str:
    for idx, source in enumerate((_strip_accents(title), _strip_accents(text))):
        for cat, words in CATEGORY_WORDS:
            if cat == "Sauce" and idx == 1:
                continue  # « sauce tomate » dans les ingrédients ne fait pas une sauce
            if any(re.search(rf"\b{re.escape(w.strip())}", source) for w in words):
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
    for ln in lines[:6]:
        if ING_HEAD.match(ln) or STEP_HEAD.match(ln) or NOISE.search(ln) or looks_like_ingredient(ln):
            continue
        if ln[:1].islower():
            continue
        t = re.split(r"(?<=[.!?])\s", ln)[0].strip(" !.?:|[]")
        t = re.sub(r"^(recette( de| du| des)?|ma recette( de| du| des)?)\s+", "", t, flags=re.I)
        t = re.sub(r"\s+pour\s+\d+\s*(personnes?|pers|parts?|portions?)\b.*$", "", t, flags=re.I)
        if len(t) > 70:
            t = t[:70].rsplit(" ", 1)[0] + "…"
        if len(t) >= 3:
            return t[0].upper() + t[1:]
    return f"Recette de {author}" if author else "Nouvelle recette"


def parse_recipe_text(caption: str, extra: str = "", ocr: str | list[str] = "", author: str = "") -> dict:
    ocr_blocks = ocr if isinstance(ocr, list) else ([ocr] if ocr else [])
    blocks = [b for b in [caption, extra, *ocr_blocks] if b and b.strip()]
    raw_all = "\n".join(blocks)
    tags = extract_tags(raw_all)
    block_lines = [[ln for ln in normalize(b).split("\n") if ln and not NOISE.search(ln)] for b in blocks]
    all_lines = [ln for bl in block_lines for ln in bl]

    title = make_title(all_lines, author)
    ingredients, steps, others = [], [], []
    for lines in block_lines:
        mode = None                      # chaque capture repart sans section connue
        for ln in lines:
            h = ING_HEAD.match(ln)
            if h:
                mode = "ing"
                ln = ln[h.end():].strip()
                ln = re.sub(r"^pour\s*\d+\s*(personnes?|pers|parts?|portions?)?\s*:?\s*", "", ln, flags=re.I)
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
            # ligne coupée par l'écran : « …ajouter » / « le bouillon »
            if ln[:1].islower() and mode == "step" and steps and not re.search(r"[.!?]$", steps[-1]):
                steps[-1] = steps[-1] + " " + ln
                continue
            if mode == "ing":
                ln = re.sub(r"^[lI|]['’]?\s*(?=[a-zà-ÿ]{3})", "1 ", ln)   # OCR : « 1 oignon » lu « l'oignon »
            if mode == "ing" and not looks_like_step(ln):
                parts = [p.strip() for p in re.split(r",|;", ln) if p.strip()]
                if len(parts) > 1 and sum(1 for p in parts if QTY_RE.match(p)) >= 2:
                    ingredients.extend(parts)   # « 200 g farine, 2 œufs » sur une ligne
                else:
                    ingredients.append(ln)
            elif mode == "step":
                steps.append(ln)
            elif looks_like_ingredient(ln):
                ingredients.append(ln)
            elif looks_like_step(ln):
                steps.append(ln)
            else:
                others.append(ln)

    ing_keys = {_strip_accents(i)[:30] for i in ingredients}
    others = [o for o in others if _strip_accents(o)[:30] not in ing_keys]
    # une ligne courte sans quantité, entre deux ingrédients (« Parmesan »), est un ingrédient
    known = {_strip_accents(i)[:30] for i in ingredients}
    for o in list(others):
        if len(o) <= 30 and not looks_like_step(o) and o[:1].isupper() and len(o.split()) <= 3 \
                and any(_strip_accents(o) in k or k.endswith(_strip_accents(o)) for k in known):
            others.remove(o)
    split_steps = []
    for st in steps:
        split_steps.extend(x for x in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])", st) if x.strip())
    steps = [re.sub(r"^\d{1,2}\.\s*", "", s).strip(" .") for s in split_steps]
    steps = [s[0].upper() + s[1:] for s in steps if len(s) > 2]
    seen_steps, uniq_steps = set(), []
    for st in steps:
        k = _strip_accents(st)[:40]
        if k not in seen_steps:
            seen_steps.add(k)
            uniq_steps.append(st)
    steps = uniq_steps
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
