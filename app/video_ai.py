"""Téléchargement de vidéos (yt-dlp) et rédaction de fiche par Gemini (offre gratuite de Google).

- yt-dlp récupère la vidéo TikTok / Instagram / YouTube, sa description et sa miniature.
- Gemini regarde la vidéo (image + son), lit les captures et le texte, et renvoie la fiche en JSON.
"""

from __future__ import annotations

import base64
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

import httpx

log = logging.getLogger("carnet")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com").rstrip("/")
# Les noms de modèles changent souvent : on essaie dans l'ordre et on garde le premier qui répond.
GEMINI_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-3-flash-preview,gemini-2.5-flash,gemini-flash-latest",
).split(",") if m.strip()]
MAX_INLINE_VIDEO = 14 * 1024 * 1024   # la requête complète doit rester sous 20 Mo
_working_model: str | None = None


# --------------------------------------------------------------------------
# yt-dlp
# --------------------------------------------------------------------------
def ytdlp_fetch(url: str, download: bool) -> dict:
    """À lancer dans un thread. Renvoie description, auteur, miniature et, si demandé, la vidéo."""
    import yt_dlp

    out = {"caption": "", "author": "", "thumb_url": "", "video": None, "url": url, "duration": None}
    tmp = tempfile.mkdtemp(prefix="carnet-")
    opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "socket_timeout": 15, "source_address": "0.0.0.0", "retries": 1,
        "outtmpl": os.path.join(tmp, "video.%(ext)s"),
        "format": "b[height<=720]/bv*[height<=720]+ba/b/bv*+ba/w",
        "merge_output_format": "mp4",
        "max_filesize": 40 * 1024 * 1024,
        "skip_download": not download,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=download)
        if info.get("_type") == "playlist" and info.get("entries"):
            info = next(e for e in info["entries"] if e)
        out["caption"] = (info.get("description") or info.get("title") or "").strip()
        out["author"] = info.get("uploader") or info.get("channel") or info.get("uploader_id") or ""
        out["thumb_url"] = info.get("thumbnail") or ""
        out["url"] = info.get("webpage_url") or url
        out["duration"] = info.get("duration")
        if download:
            files = [f for f in glob.glob(os.path.join(tmp, "video.*")) if not f.endswith(".part")]
            if files:
                with open(files[0], "rb") as fh:
                    data = fh.read()
                if len(data) > MAX_INLINE_VIDEO:
                    data = shrink_video(files[0], tmp) or data
                if len(data) <= MAX_INLINE_VIDEO:
                    out["video"] = data
                else:
                    log.info("Vidéo trop lourde pour Gemini (%s Mo) : on utilise la description", len(data) // 1_000_000)
        log.info("yt-dlp %s : description %s car., vidéo %s", url, len(out["caption"]),
                 f"{len(out['video']) // 1000} Ko" if out["video"] else "non")
    except Exception as e:  # noqa: BLE001
        log.info("yt-dlp %s : échec (%s)", url, str(e)[:200])
    finally:
        for f in glob.glob(os.path.join(tmp, "*")):
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
    return out


def shrink_video(path: str, tmp: str) -> bytes | None:
    """Réduit une vidéo trop lourde (480p, débit bas) pour qu'elle passe dans une requête Gemini."""
    if not shutil.which("ffmpeg"):
        return None
    dst = os.path.join(tmp, "petite.mp4")
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-t", "600",
                        "-vf", "scale=-2:480", "-r", "15", "-c:v", "libx264", "-preset", "veryfast",
                        "-b:v", "500k", "-c:a", "aac", "-b:a", "64k", "-ac", "1", dst],
                       check=True, timeout=120)
        with open(dst, "rb") as fh:
            data = fh.read()
        log.info("Vidéo réduite à %s Ko pour Gemini", len(data) // 1000)
        return data
    except (subprocess.SubprocessError, OSError) as e:
        log.info("Réduction de la vidéo impossible : %s", e)
        return None


# --------------------------------------------------------------------------
# Gemini
# --------------------------------------------------------------------------
class GeminiError(Exception):
    pass


def _parse_json(text: str) -> dict:
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


async def gemini_generate(prompt: str, video: bytes | None, images: list[bytes]) -> dict:
    """Envoie vidéo + images + consigne à Gemini et renvoie le JSON de la fiche."""
    global _working_model
    parts: list[dict] = []
    if video:
        parts.append({"inline_data": {"mime_type": "video/mp4", "data": base64.b64encode(video).decode()}})
    for img in images:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(img).decode()}})
    parts.append({"text": prompt})
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json", "maxOutputTokens": 4096},
    }
    models = ([_working_model] if _working_model else []) + [m for m in GEMINI_MODELS if m != _working_model]
    last = "aucun modèle disponible"
    async with httpx.AsyncClient(timeout=httpx.Timeout(150.0, connect=10.0),
                                 transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as c:
        for model in models:
            try:
                r = await c.post(f"{GEMINI_BASE_URL}/v1beta/models/{model}:generateContent",
                                 headers={"x-goog-api-key": GEMINI_API_KEY, "content-type": "application/json"},
                                 json=body)
            except httpx.HTTPError as e:
                raise GeminiError("Impossible de joindre Gemini. Réessaie dans un instant.") from e
            log.info("Gemini %s : HTTP %s", model, r.status_code)
            if r.status_code in (404, 400) and ("not found" in r.text.lower() or "not supported" in r.text.lower()):
                last = f"modèle {model} indisponible"
                continue
            if r.status_code == 429:
                # quota du modèle épuisé (ou nul en gratuit) : on tente le suivant
                last = "quota gratuit atteint"
                log.info("Gemini %s : %s", model, r.text[:300])
                continue
            if r.status_code in (401, 403):
                raise GeminiError("La clé Gemini est refusée. Vérifie GEMINI_API_KEY dans Coolify.")
            if r.status_code != 200:
                log.warning("Gemini %s : %s", model, r.text[:500])
                last = f"erreur {r.status_code}"
                continue
            data = r.json()
            cand = (data.get("candidates") or [{}])[0]
            text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))
            if not text:
                reason = cand.get("finishReason") or (data.get("promptFeedback") or {}).get("blockReason")
                raise GeminiError(f"Gemini n'a rien répondu ({reason or 'réponse vide'}). Réessaie ou ajoute des captures.")
            _working_model = model
            try:
                return _parse_json(text)
            except (json.JSONDecodeError, ValueError) as e:
                raise GeminiError("La réponse de Gemini était incomplète. Relance l'import.") from e
    if last == "quota gratuit atteint":
        raise GeminiError("Le quota gratuit de Gemini est atteint pour le moment. Réessaie dans une minute ou demain.")
    raise GeminiError(f"Gemini n'a pas pu répondre ({last}).")
