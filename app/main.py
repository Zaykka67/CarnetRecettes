"""Carnet de recettes — serveur FastAPI.

- Stocke les recettes dans SQLite et les photos sur disque (dossier DATA_DIR).
- Protège l'appli par un mot de passe unique (APP_PASSWORD).
- Importe une recette depuis un lien (TikTok, YouTube, Instagram, site web) :
  récupère la description et la miniature de la vidéo, puis demande à Claude
  (API Anthropic) d'en faire une fiche recette.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import html as html_lib
import io
import ipaddress
import json
import logging
import os
import re
import socket
import sqlite3
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps

from .free_import import OCR_AVAILABLE, ocr_image, parse_recipe_text

log = logging.getLogger("carnet")
logging.basicConfig(level=logging.INFO)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
PHOTOS_DIR = DATA_DIR / "photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "recettes.db"
STATIC_DIR = Path(__file__).parent / "static"

APP_PASSWORD = os.getenv("APP_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "") or hashlib.sha256(("carnet:" + APP_PASSWORD).encode()).hexdigest()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")

COOKIE = "carnet_session"
SESSION_DAYS = 365
MAX_UPLOAD = 15 * 1024 * 1024
MAX_SHOTS = 6

SEASONS = ["printemps", "ete", "automne", "hiver"]
CATEGORIES = ["Apéro", "Entrée", "Plat", "Accompagnement", "Dessert", "Petit-déj", "Boisson", "Sauce"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")

if not APP_PASSWORD:
    log.warning("APP_PASSWORD n'est pas défini : l'appli est accessible sans mot de passe.")
if not ANTHROPIC_API_KEY:
    log.info("ANTHROPIC_API_KEY absent : import gratuit (lecture de la description + OCR %s).",
             "actif" if OCR_AVAILABLE else "indisponible")

# --------------------------------------------------------------------------
# Base de données
# --------------------------------------------------------------------------
def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


with db() as _c:
    _c.execute("""CREATE TABLE IF NOT EXISTS recipes(
        id TEXT PRIMARY KEY, data TEXT NOT NULL,
        created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)""")


def now_ms() -> int:
    return int(time.time() * 1000)


def row_to_recipe(row: sqlite3.Row) -> dict:
    d = json.loads(row["data"])
    d["id"] = row["id"]
    d["createdAt"] = row["created_at"]
    d["updatedAt"] = row["updated_at"]
    return d


def get_recipe(rid: str) -> dict | None:
    with db() as c:
        row = c.execute("SELECT * FROM recipes WHERE id=?", (rid,)).fetchone()
    return row_to_recipe(row) if row else None


# --------------------------------------------------------------------------
# Nettoyage des données reçues
# --------------------------------------------------------------------------
def _s(v, n=500) -> str:
    return str(v or "").strip()[:n]


def _int(v):
    try:
        n = int(round(float(v)))
        return n if 0 <= n < 100000 else None
    except (TypeError, ValueError):
        return None


def _num(v):
    try:
        n = float(v)
        return n if 0 <= n < 1e6 else None
    except (TypeError, ValueError):
        return None


def _url(v) -> str:
    u = _s(v, 1000)
    return u if re.match(r"^https?://", u, re.I) else ""


def clean_recipe(d: dict) -> dict:
    photo = d.get("photo") if isinstance(d.get("photo"), dict) else None
    pid = photo.get("id") if photo else None
    return {
        "title": _s(d.get("title"), 160) or "Sans titre",
        "description": _s(d.get("description"), 400),
        "category": d.get("category") if d.get("category") in CATEGORIES else "Plat",
        "seasons": [s for s in SEASONS if s in (d.get("seasons") or [])],
        "prepMin": _int(d.get("prepMin")),
        "cookMin": _int(d.get("cookMin")),
        "servings": _int(d.get("servings")) or None,
        "ingredients": [
            {"qty": _num(i.get("qty")), "unit": _s(i.get("unit"), 30), "name": _s(i.get("name"), 200)}
            for i in (d.get("ingredients") or [])[:80]
            if isinstance(i, dict) and _s(i.get("name"))
        ],
        "steps": [_s(s, 2000) for s in (d.get("steps") or [])[:60] if _s(s)],
        "tips": _s(d.get("tips"), 2000),
        "tags": [_s(t, 40).lstrip("#") for t in (d.get("tags") or [])[:10] if _s(t)],
        "sourceUrl": _url(d.get("sourceUrl")),
        "favorite": bool(d.get("favorite")),
        "photo": {"id": pid} if isinstance(pid, str) and re.fullmatch(r"[a-f0-9]{32}", pid) else None,
    }


# --------------------------------------------------------------------------
# Photos
# --------------------------------------------------------------------------
def save_image(raw: bytes, max_side: int = 1600) -> str:
    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "Image illisible.") from e
    img.thumbnail((max_side, max_side))
    pid = uuid.uuid4().hex
    img.save(PHOTOS_DIR / f"{pid}.jpg", "JPEG", quality=84, optimize=True)
    return pid


def crop_video_frame(raw: bytes) -> bytes:
    """Sur une capture de téléphone (TikTok description ouverte), l'image de la vidéo est en haut :
    on garde cette zone pour la photo de la fiche plutôt que le texte."""
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    except Exception:  # noqa: BLE001
        return raw
    w, h = img.size
    if h / w > 1.6:
        img = img.crop((0, int(h * 0.06), w, int(h * 0.38)))
        cw, ch = img.size
        target = int(cw * 3 / 4)          # format 4:3 centré
        if ch > target:
            top = (ch - target) // 2
            img = img.crop((0, top, cw, top + target))
        elif ch < target:
            nw = int(ch * 4 / 3)
            left = (cw - nw) // 2
            img = img.crop((left, 0, left + nw, ch))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def image_b64(raw: bytes, max_side: int = 1200) -> str:
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82)
    return base64.b64encode(buf.getvalue()).decode()


def delete_photo(photo: dict | None) -> None:
    if photo and photo.get("id"):
        p = PHOTOS_DIR / f"{photo['id']}.jpg"
        p.unlink(missing_ok=True)


# --------------------------------------------------------------------------
# Session
# --------------------------------------------------------------------------
def make_token() -> str:
    exp = str(int(time.time()) + SESSION_DAYS * 86400)
    sig = hmac.new(SECRET_KEY.encode(), exp.encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def is_authed(request: Request) -> bool:
    if not APP_PASSWORD:
        return True
    tok = request.cookies.get(COOKIE, "")
    exp, _, sig = tok.partition(".")
    if not exp.isdigit() or int(exp) < time.time():
        return False
    good = hmac.new(SECRET_KEY.encode(), exp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good)


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
app = FastAPI(title="Carnet de recettes", docs_url=None, redoc_url=None)

PUBLIC_API = {"/api/login", "/api/config"}


@app.middleware("http")
async def auth_mw(request: Request, call_next):
    p = request.url.path
    protected = (p.startswith("/api/") and p not in PUBLIC_API) or p.startswith("/photos/")
    if protected and not is_authed(request):
        return JSONResponse({"detail": "Connexion requise."}, status_code=401)
    return await call_next(request)


@app.get("/api/config")
async def config(request: Request):
    return {"ai": bool(ANTHROPIC_API_KEY), "ocr": OCR_AVAILABLE, "auth": bool(APP_PASSWORD), "loggedIn": is_authed(request)}


@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    pwd = str(body.get("password", ""))
    if not APP_PASSWORD or not hmac.compare_digest(pwd.encode(), APP_PASSWORD.encode()):
        await asyncio.sleep(1.5)
        raise HTTPException(401, "Mot de passe incorrect.")
    resp = JSONResponse({"ok": True})
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    resp.set_cookie(COOKIE, make_token(), max_age=SESSION_DAYS * 86400, httponly=True,
                    secure=secure, samesite="lax", path="/")
    return resp


@app.post("/api/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/")
    return resp


# ---- Recettes ----------------------------------------------------------------
@app.get("/api/recipes")
async def list_recipes():
    with db() as c:
        rows = c.execute("SELECT * FROM recipes ORDER BY created_at DESC").fetchall()
    return [row_to_recipe(r) for r in rows]


@app.post("/api/recipes")
async def create_recipe(request: Request):
    data = clean_recipe(await request.json())
    rid, ts = uuid.uuid4().hex[:12], now_ms()
    with db() as c:
        c.execute("INSERT INTO recipes VALUES (?,?,?,?)", (rid, json.dumps(data, ensure_ascii=False), ts, ts))
    return get_recipe(rid)


@app.put("/api/recipes/{rid}")
async def replace_recipe(rid: str, request: Request):
    old = get_recipe(rid)
    if not old:
        raise HTTPException(404, "Recette introuvable.")
    data = clean_recipe(await request.json())
    if (old.get("photo") or {}).get("id") != (data.get("photo") or {}).get("id"):
        delete_photo(old.get("photo"))
    with db() as c:
        c.execute("UPDATE recipes SET data=?, updated_at=? WHERE id=?",
                  (json.dumps(data, ensure_ascii=False), now_ms(), rid))
    return get_recipe(rid)


@app.patch("/api/recipes/{rid}")
async def patch_recipe(rid: str, request: Request):
    old = get_recipe(rid)
    if not old:
        raise HTTPException(404, "Recette introuvable.")
    body = await request.json()
    if "favorite" in body:
        old["favorite"] = bool(body["favorite"])
    data = clean_recipe(old)
    with db() as c:
        c.execute("UPDATE recipes SET data=?, updated_at=? WHERE id=?",
                  (json.dumps(data, ensure_ascii=False), now_ms(), rid))
    return get_recipe(rid)


@app.delete("/api/recipes/{rid}")
async def delete_recipe(rid: str):
    old = get_recipe(rid)
    if old:
        delete_photo(old.get("photo"))
        with db() as c:
            c.execute("DELETE FROM recipes WHERE id=?", (rid,))
    return Response(status_code=204)


# ---- Photos ------------------------------------------------------------------
@app.post("/api/photos")
async def upload_photo(file: UploadFile = File(...)):
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "Image trop lourde (15 Mo maximum).")
    return {"id": save_image(raw)}


@app.get("/photos/{pid}")
async def get_photo(pid: str):
    pid = pid.removesuffix(".jpg")
    if not re.fullmatch(r"[a-f0-9]{32}", pid):
        raise HTTPException(404)
    p = PHOTOS_DIR / f"{pid}.jpg"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=31536000, immutable"})


# ---- Import depuis un lien ------------------------------------------------------
async def _public_host(host: str) -> bool:
    """Refuse les adresses internes (localhost, réseau privé…). Résolution asynchrone, 5 s maximum."""
    try:
        loop = asyncio.get_running_loop()
        infos = await asyncio.wait_for(loop.getaddrinfo(host, None, family=socket.AF_INET), timeout=5)
    except (OSError, asyncio.TimeoutError):
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def _platform(host: str) -> str:
    h = host.lower()
    for key, name in (("tiktok", "TikTok"), ("instagram", "Instagram"), ("youtu", "YouTube"),
                      ("facebook", "Facebook"), ("fb.watch", "Facebook"), ("pinterest", "Pinterest"), ("pin.it", "Pinterest")):
        if key in h:
            return name
    return h.removeprefix("www.")


def _meta(html: str, prop: str) -> str:
    for pat in (rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]+content=["\']([^"\']*)',
                rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{prop}["\']'):
        m = re.search(pat, html, re.I)
        if m:
            return html_lib.unescape(m.group(1)).strip()
    return ""


async def _get_limited(client: httpx.AsyncClient, url: str, limit: int) -> bytes | None:
    """Télécharge au plus `limit` octets, uniquement depuis une adresse publique."""
    host = urlparse(url).hostname or ""
    if not host or not await _public_host(host):
        return None
    async with client.stream("GET", url) as r:
        if r.status_code >= 400:
            return None
        chunks, size = [], 0
        async for chunk in r.aiter_bytes():
            size += len(chunk)
            if size > limit:
                break
            chunks.append(chunk)
    return b"".join(chunks)


def _text(raw: bytes | None) -> str:
    return raw.decode("utf-8", errors="replace") if raw else ""


def _tiktok_from_html(html: str) -> dict:
    """Lit la légende et la miniature dans le HTML d'une page TikTok."""
    res = {"caption": "", "author": "", "thumb_url": ""}
    m = re.search(r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
    if m:
        try:
            data = json.loads(m.group(1))
            item = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]
            res["caption"] = item.get("desc", "") or ""
            res["author"] = (item.get("author") or {}).get("uniqueId", "")
            video = item.get("video") or {}
            res["thumb_url"] = video.get("originCover") or video.get("cover") or video.get("dynamicCover") or ""
            if not res["thumb_url"]:
                imgs = ((item.get("imagePost") or {}).get("images") or [])
                if imgs:
                    res["thumb_url"] = (imgs[0].get("imageURL") or {}).get("urlList", [""])[0]
        except (ValueError, KeyError, TypeError, IndexError):
            pass
    if not res["caption"]:
        res["caption"] = _meta(html, "og:description") or _meta(html, "description")
    if not res["thumb_url"]:
        res["thumb_url"] = _meta(html, "og:image")
    return res


async def tiktok_info(c: httpx.AsyncClient, url: str, out: dict) -> str:
    """Récupère légende, auteur et miniature d'une vidéo TikTok. Renvoie l'URL de la miniature."""

    async def oembed(u: str) -> dict | None:
        try:
            r = await c.get("https://www.tiktok.com/oembed", params={"url": u})
        except httpx.HTTPError as e:
            log.info("TikTok oEmbed %s : erreur réseau %s", u, e)
            return None
        log.info("TikTok oEmbed %s : HTTP %s", u, r.status_code)
        if r.status_code == 200:
            try:
                j = r.json()
            except ValueError:
                return None
            if j.get("title") or j.get("thumbnail_url"):
                return j
        return None

    # 1. oEmbed directement avec le lien partagé
    j = await oembed(url)
    html = ""
    if not j:
        # 2. on suit le lien court jusqu'à la vraie page de la vidéo
        try:
            r = await c.get(url)
            final = str(r.url)
            html = r.text if r.status_code < 400 else ""
            log.info("TikTok lien %s -> %s (HTTP %s, %s octets)", url, final.split("?")[0], r.status_code, len(r.content))
        except httpx.HTTPError as e:
            final = url
            log.info("TikTok lien %s : erreur réseau %s", url, e)
        m = re.search(r"tiktok\.com/@([\w.\-]+)/(?:video|photo)/(\d+)", final)
        if m:
            out["url"] = f"https://www.tiktok.com/@{m.group(1)}/video/{m.group(2)}"
            j = await oembed(out["url"])
        elif final != url:
            out["url"] = final.split("?")[0]
            j = await oembed(out["url"])
    if j:
        out["caption"], out["author"] = j.get("title", "") or "", j.get("author_name", "") or ""
        return j.get("thumbnail_url", "") or ""
    # 3. dernier recours : lire la page elle-même
    if html:
        res = _tiktok_from_html(html)
        log.info("TikTok page : légende %s, miniature %s", "trouvée" if res["caption"] else "absente",
                 "trouvée" if res["thumb_url"] else "absente")
        out["caption"], out["author"] = res["caption"], res["author"]
        return res["thumb_url"]
    log.info("TikTok : rien de lisible pour %s", url)
    return ""


FB_UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"


async def instagram_info(c: httpx.AsyncClient, url: str, out: dict) -> str:
    """Instagram ne montre la légende qu'aux robots d'aperçu de lien (Facebook, WhatsApp…)."""
    clean = url.split("?")[0]
    try:
        r = await c.get(clean, headers={"User-Agent": FB_UA, "Accept-Language": "fr-FR,fr;q=0.9"})
    except httpx.HTTPError as e:
        log.info("Instagram %s : erreur réseau %s", clean, e)
        return ""
    html = r.text[:3_000_000] if r.status_code < 400 else ""
    log.info("Instagram %s : HTTP %s, %s octets", clean, r.status_code, len(r.content))
    if not html:
        return ""
    desc = _meta(html, "og:description") or _meta(html, "description")
    # « 1 234 likes, 56 comments - auteur le 3 novembre 2026: "la légende" »
    m = re.match(r'^.*?(?:comments?|commentaires?)\s*-\s*([\w.]+)[^:]*:\s*["“](.*)["”]\.?\s*$', desc, re.S)
    if m:
        out["author"], desc = m.group(1), m.group(2)
    if not out["author"]:
        t = _meta(html, "og:title")
        m2 = re.match(r"^(.+?) (?:on|sur) Instagram", t)
        if m2:
            out["author"] = m2.group(1)
    out["caption"] = desc
    log.info("Instagram : légende %s", "trouvée" if desc else "absente")
    return _meta(html, "og:image")


async def fetch_link_info(url: str) -> dict:
    """Récupère la légende, l'auteur et la miniature d'une vidéo ou d'une page."""
    out = {"caption": "", "author": "", "thumb": None, "platform": "", "url": url}
    if not re.match(r"^https?://", url, re.I):
        return out
    # IPv4 forcé : dans Docker, une route IPv6 absente fait attendre chaque requête jusqu'au délai maximum
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=1)
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, transport=transport,
                                 headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}) as c:
        try:
            host = (urlparse(url).hostname or "").lower()
            out["platform"] = _platform(host)
            thumb_url = ""
            if "tiktok" in host:
                thumb_url = await tiktok_info(c, url, out)
            elif "youtu" in host:
                r = await c.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"})
                if r.status_code == 200:
                    j = r.json()
                    out["caption"], out["author"], thumb_url = j.get("title", ""), j.get("author_name", ""), j.get("thumbnail_url", "")
                page = _text(await _get_limited(c, url, 3_000_000))
                if page:
                    desc = _meta(page, "og:description") or _meta(page, "description")
                    if desc:
                        out["caption"] = f"{out['caption']}\n\n{desc}".strip()
            elif "instagram" in host:
                thumb_url = await instagram_info(c, url, out)
            else:
                t = _text(await _get_limited(c, url, 3_000_000))
                if t:
                    title = _meta(t, "og:title")
                    desc = _meta(t, "og:description") or _meta(t, "description")
                    out["caption"] = "\n\n".join(x for x in (title, desc) if x)
                    thumb_url = _meta(t, "og:image")
                    # Recette structurée (schema.org) présente sur la plupart des sites de cuisine
                    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', t, re.S | re.I):
                        if '"Recipe"' in m.group(1):
                            out["caption"] += "\n\nDonnées structurées de la page :\n" + m.group(1)[:15000]
                            break
            if thumb_url and re.match(r"^https?://", thumb_url):
                raw = await _get_limited(c, thumb_url, 8_000_000)
                if raw:
                    out["thumb"] = raw
        except (httpx.HTTPError, ValueError) as e:
            log.info("Lecture du lien impossible (%s) : %s", url, e)
    return out


IMPORT_PROMPT = """Tu aides à remplir un carnet de recettes personnel, en français.
À partir des éléments ci-dessous (légende d'une vidéo de recette TikTok, Instagram, YouTube ou d'une page web, texte collé par l'utilisateur, et images), retranscris la recette.

{images_desc}

Règles :
- N'invente pas de quantité absente : mets "qty": null. Une quantité lisible dans le texte ou sur une image doit être reprise.
- "qty" est un nombre (0.5 pour un demi). "unit" est court : g, kg, ml, cl, l, c. à s., c. à c., pincée, gousse, tranche, sachet, botte… ou "" pour une pièce (ex. 3 œufs).
- "name" est l'ingrédient seul, sans "de" au début.
- Étapes courtes et claires, à l'impératif, dans l'ordre. Corrige les fautes, retire emojis, hashtags et appels à s'abonner.
- Si la légende ne donne que les ingrédients, déduis des étapes simples et logiques, et signale-le dans "notes".
- "seasons" : parmi ["printemps","ete","automne","hiver"] selon la saisonnalité en France des ingrédients frais principaux ; tableau vide si la recette se cuisine toute l'année.
- "category" : une valeur parmi {categories}.
- "prepMin", "cookMin", "servings" : entiers, estime-les raisonnablement s'ils sont absents.
- "coverImageIndex" : numéro de l'image qui montre le mieux le plat fini, ou null s'il n'y a pas d'image.
- "notes" : une phrase courte sur ce qui manquait ou a été déduit, ou "".
- "tags" : 1 à 4 mots-clés courts en minuscules.

Réponds uniquement avec un objet JSON de cette forme :
{{"title":"Velouté de potimarron","description":"Une phrase qui donne envie.","category":"Entrée","seasons":["automne"],"prepMin":15,"cookMin":30,"servings":4,"ingredients":[{{"qty":1,"unit":"","name":"potimarron"}},{{"qty":20,"unit":"cl","name":"crème liquide"}}],"steps":["Coupe le potimarron en cubes."],"tips":"","tags":["soupe"],"coverImageIndex":0,"notes":""}}
Si les éléments ne contiennent aucune recette exploitable, réponds {{"error":"explication courte en français"}}.

Lien : {url}
Auteur : {author}

Légende de la vidéo / texte de la page :
\"\"\"
{caption}
\"\"\"

Texte ajouté par l'utilisateur :
\"\"\"
{user_text}
\"\"\"
"""


def parse_json_reply(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        a, b = text.find("{"), text.rfind("}")
        if a >= 0 and b > a:
            return json.loads(text[a:b + 1])
        raise


@app.post("/api/import")
async def import_recipe(url: str = Form(""), caption: str = Form(""), source: str = Form(""),
                        images: list[UploadFile] | None = File(None)):
    url = url.strip()
    log.info("Import demandé : lien=%s, texte=%s car., captures=%s", url or "-", len(caption), len(images or []))
    shots: list[bytes] = []
    for f in (images or [])[:MAX_SHOTS]:
        raw = await f.read(MAX_UPLOAD + 1)
        if raw and len(raw) <= MAX_UPLOAD:
            shots.append(raw)

    empty = {"caption": "", "author": "", "thumb": None, "platform": "", "url": url}
    info = empty
    if url:
        t0 = time.time()
        try:
            info = await asyncio.wait_for(fetch_link_info(url), timeout=30)
        except asyncio.TimeoutError:
            log.info("Lecture du lien abandonnée après 30 s : %s", url)
            info = {**empty, "platform": _platform(urlparse(url).hostname or "")}
        log.info("Lecture du lien en %.1f s (légende %s, miniature %s)", time.time() - t0,
                 "oui" if info["caption"] else "non", "oui" if info["thumb"] else "non")
    all_imgs = shots + ([info["thumb"]] if info["thumb"] else [])

    if not (info["caption"].strip() or caption.strip() or all_imgs):
        raise HTTPException(422, "Je n'ai rien pu lire depuis ce lien. Colle la description de la vidéo ou ajoute des captures d'écran.")

    if not ANTHROPIC_API_KEY:
        return await free_import(info, url, caption, shots, source)

    lines = []
    for i in range(len(shots)):
        lines.append(f"Image {i} : capture d'écran de la vidéo envoyée par l'utilisateur.")
    if info["thumb"]:
        lines.append(f"Image {len(shots)} : miniature de la vidéo.")
    images_desc = "\n".join(lines) if lines else "Aucune image."

    content: list[dict] = []
    for raw in all_imgs:
        try:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64(raw)}})
        except Exception:  # noqa: BLE001
            content.append({"type": "text", "text": "(image illisible)"})
    content.append({"type": "text", "text": IMPORT_PROMPT.format(
        images_desc=images_desc, categories=json.dumps(CATEGORIES, ensure_ascii=False),
        url=info["url"] or url or "(aucun)", author=info["author"] or "(inconnu)",
        caption=(info["caption"] or "(rien trouvé)")[:20000], user_text=(caption or "(rien)")[:12000])})

    try:
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(f"{ANTHROPIC_BASE_URL}/v1/messages",
                             headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                                      "content-type": "application/json"},
                             json={"model": ANTHROPIC_MODEL, "max_tokens": 4096,
                                   "messages": [{"role": "user", "content": content}]})
    except httpx.HTTPError as e:
        raise HTTPException(502, "Impossible de joindre Claude. Réessaie dans un instant.") from e
    if r.status_code != 200:
        log.warning("API Anthropic %s : %s", r.status_code, r.text[:500])
        msg = {401: "La clé API Anthropic est refusée. Vérifie ANTHROPIC_API_KEY.",
               404: f"Le modèle « {ANTHROPIC_MODEL} » est introuvable. Vérifie ANTHROPIC_MODEL.",
               429: "Trop de demandes envoyées à Claude. Réessaie dans une minute.",
               529: "Claude est surchargé. Réessaie dans une minute."}.get(r.status_code, "Claude n'a pas pu répondre. Réessaie.")
        raise HTTPException(502, msg)

    text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    try:
        res = parse_json_reply(text)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(502, "La réponse de Claude était incomplète. Relance l'import.")
    if not isinstance(res, dict) or res.get("error"):
        raise HTTPException(422, f"Pas de recette trouvée : {res.get('error') if isinstance(res, dict) else 'réponse vide'}")

    idx = res.get("coverImageIndex")
    cover = all_imgs[idx] if isinstance(idx, int) and 0 <= idx < len(all_imgs) else (info["thumb"] or (shots[-1] if shots else None))
    photo = None
    if cover:
        try:
            photo = {"id": save_image(cover)}
        except HTTPException:
            photo = None

    res["sourceUrl"] = info["url"] or url or source
    res["photo"] = photo
    draft = clean_recipe(res)
    draft["favorite"] = False
    return {"draft": draft, "notes": _s(res.get("notes"), 400),
            "captionFound": bool(info["caption"].strip()), "platform": info["platform"]}


async def free_import(info: dict, url: str, caption: str, shots: list[bytes], source: str = "") -> dict:
    """Import sans IA : on découpe la légende et le texte lu sur les captures."""
    t0 = time.time()
    texts = await asyncio.gather(*(asyncio.to_thread(ocr_image, raw) for raw in shots))
    ocr_text = "\n".join(t for t in texts if t)
    if shots:
        log.info("OCR de %s capture(s) en %.1f s : %s caractères lus", len(shots), time.time() - t0, len(ocr_text))
    res = parse_recipe_text(info["caption"], caption, [t for t in texts if t], info["author"])
    photo = None
    try:
        if info["thumb"]:
            photo = {"id": save_image(info["thumb"])}
        elif shots:
            photo = {"id": save_image(crop_video_frame(shots[0]))}
    except HTTPException:
        photo = None
    notes = res.pop("notes")
    if info["platform"] and not info["caption"] and not caption and not ocr_text:
        notes = (f"Je n'ai pas pu lire la description sur {info['platform']}. "
                 "Colle-la dans « Texte en plus » ou ajoute des captures d'écran.")
    res["sourceUrl"] = info["url"] or url or source
    res["photo"] = photo
    draft = clean_recipe(res)
    draft["favorite"] = False
    return {"draft": draft, "notes": notes, "captionFound": bool(info["caption"].strip()),
            "platform": info["platform"], "ai": False}


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
@app.get("/share")
async def share_page():
    # Cible du menu « Partager » (Android) : on sert l'appli, qui lit les paramètres
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/sw.js")
async def service_worker():
    return FileResponse(STATIC_DIR / "sw.js", media_type="text/javascript",
                        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@app.get("/healthz")
async def health():
    return {"ok": True}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
