import os
import sys
import json
import time
import requests
import tempfile
import yt_dlp
from typing import Dict, List, Optional, Tuple

# Forzar codificacion UTF-8 en la consola
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Cargar variables de entorno si existe .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROCESSED_FILE = "processed_videos.json"

# ==============================================================================
# UTILIDADES
# ==============================================================================

def load_processed_ids() -> List[str]:
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_processed_id(video_id: str):
    processed = load_processed_ids()
    if video_id not in processed:
        processed.append(video_id)
        with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
            json.dump(processed, f, indent=2)

# ==============================================================================
# GENERADOR DE CAPTIONS CON IA (GEMINI)
# ==============================================================================

def generate_ai_captions(original_title: str, config: Dict) -> Dict[str, str]:
    """Genera un caption diferente y adaptado para cada red social usando Gemini AI."""
    base_title = original_title.strip() if original_title.strip() else "Nuevo video viral"

    default_captions = {
        "youtube": f"{base_title[:80]} #Shorts",
        "instagram": f"{base_title}\n\n#Reels #Viral #ContentCreator #Trending #FYP",
        "x": f"{base_title[:240]} #Trending",
        "reddit": base_title[:250]
    }

    gemini_api_key = config.get("GEMINI_API_KEY")
    if not gemini_api_key:
        print("[AI] Sin GEMINI_API_KEY. Usando captions optimizados por defecto.")
        return default_captions

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
        prompt = f"""Eres un experto en marketing de contenido para redes sociales.
Dado este video de TikTok con titulo/descripcion: '{base_title}',
crea 4 textos DIFERENTES adaptados al tono y formato de cada red:

1. "youtube": Titulo llamativo para YouTube Shorts (max 90 chars, incluye #Shorts, SEO optimizado).
2. "instagram": Caption visual con emojis, enganche emocional y 5 hashtags virales relevantes.
3. "x": Tweet impactante max 250 chars, directo al punto, con 1-2 hashtags.
4. "reddit": Titulo natural y curioso para Reddit (sin hashtags, max 250 chars).

Responde SOLO con un JSON valido con esas 4 claves exactas."""

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=12).json()
        text_response = res['candidates'][0]['content']['parts'][0]['text']
        clean_json = text_response.replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(clean_json)
        if all(k in ai_data for k in ["youtube", "instagram", "x", "reddit"]):
            print("[AI SUCCESS] Captions personalizados generados con Gemini AI.")
            return ai_data
    except Exception as e:
        print(f"[AI WARNING] Fallo Gemini AI ({e}). Usando captions por defecto.")

    return default_captions

# ==============================================================================
# DETECCION DE VIDEOS EN TIKTOK (via yt-dlp)
# ==============================================================================

def fetch_latest_tiktok_videos(username: str, count: int = 10) -> List[Dict]:
    """
    Obtiene los ultimos videos del perfil de TikTok usando yt-dlp.
    Devuelve lista de dicts con id, title, webpage_url.
    """
    clean_username = username.strip().replace("@", "")
    profile_url = f"https://www.tiktok.com/@{clean_username}"
    print(f"[SEARCH] Buscando videos nuevos en TikTok @{clean_username}...")

    ydl_opts = {
        'extract_flat': 'in_playlist',
        'playlistend': count,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(profile_url, download=False)
            entries = info.get('entries', [])
            videos = []
            for e in entries:
                video_id = str(e.get('id', ''))
                if not video_id:
                    continue
                title = e.get('title') or e.get('description') or ""
                webpage_url = e.get('url') or f"https://www.tiktok.com/@{clean_username}/video/{video_id}"
                videos.append({
                    "id": video_id,
                    "title": title,
                    "webpage_url": webpage_url
                })
            if videos:
                print(f"[SEARCH] {len(videos)} videos encontrados en el perfil.")
                return videos
    except Exception as e:
        print(f"[WARNING] yt-dlp: {e}")

    print("[ERROR] No se pudo obtener la lista de videos de TikTok.")
    return []

# ==============================================================================
# DESCARGA SIN MARCA DE AGUA (100% via TikWM API - verificado que funciona)
# ==============================================================================

def download_video_via_tikwm(video_info: Dict) -> Tuple[str, str]:
    """
    Descarga el video sin marca de agua usando TikWM API.
    Devuelve (ruta_archivo_local, url_directa_mp4).
    """
    webpage_url = video_info.get("webpage_url", "")
    print(f"[TIKWM] Obteniendo .mp4 sin watermark para: {webpage_url}")

    res = requests.post(
        "https://www.tikwm.com/api/",
        data={"url": webpage_url},
        timeout=20
    ).json()

    if res.get("code") != 0:
        raise RuntimeError(f"TikWM error: {res.get('msg', 'unknown')}")

    data = res.get("data", {})
    direct_url = data.get("play", "")
    if not direct_url:
        raise RuntimeError("TikWM no retorno URL de descarga valida.")

    if not direct_url.startswith("http"):
        direct_url = f"https://www.tikwm.com{direct_url}"

    # Actualizar titulo si TikWM lo tiene y el original esta vacio
    if data.get("title") and not video_info.get("title", "").strip():
        video_info["title"] = data["title"]

    print(f"[TIKWM SUCCESS] URL de descarga obtenida.")

    # Descargar a archivo temporal
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "video.mp4")

    r = requests.get(direct_url, stream=True, timeout=60,
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    total = 0
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
            total += len(chunk)

    if total < 10000:
        raise RuntimeError(f"Archivo descargado demasiado pequeno ({total} bytes).")

    print(f"[DOWNLOAD SUCCESS] Video descargado: {output_path} ({total // 1024} KB)")
    return output_path, direct_url

# ==============================================================================
# PUBLICADORES POR RED SOCIAL
# ==============================================================================

def publish_to_youtube(video_path: str, caption: str, config: Dict) -> bool:
    refresh_token = config.get("YOUTUBE_REFRESH_TOKEN")
    client_id = config.get("YOUTUBE_CLIENT_ID")
    client_secret = config.get("YOUTUBE_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        print("[YOUTUBE] Omitido: Falta YOUTUBE_REFRESH_TOKEN en GitHub Secrets.")
        return False

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        youtube = build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title": caption[:90],
                "description": f"{caption}\n\n#Shorts #Viral #TikTok",
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        resp = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print(f"[YOUTUBE SUCCESS] Publicado! ID: {resp.get('id')}")
        return True
    except Exception as e:
        print(f"[YOUTUBE ERROR] {e}")
        return False

def publish_to_instagram(direct_mp4_url: str, caption: str, config: Dict) -> bool:
    ig_user_id = config.get("INSTAGRAM_USER_ID")
    access_token = config.get("INSTAGRAM_ACCESS_TOKEN")

    if not all([ig_user_id, access_token]):
        print("[INSTAGRAM] Omitido: Falta INSTAGRAM_USER_ID o INSTAGRAM_ACCESS_TOKEN.")
        return False

    try:
        print(f"[INSTAGRAM] Creando contenedor de Reel para usuario {ig_user_id}...")
        container_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": direct_mp4_url,
            "caption": caption,
            "access_token": access_token
        }
        res = requests.post(container_url, data=payload, timeout=30).json()

        creation_id = res.get("id")
        if not creation_id:
            err = res.get("error", {})
            print(f"[INSTAGRAM ERROR] No se creo contenedor: {err.get('message', str(res))}")
            return False

        print(f"[INSTAGRAM] Contenedor creado (ID: {creation_id}). Esperando procesamiento...")
        status_url = f"https://graph.facebook.com/v18.0/{creation_id}"
        for i in range(15):
            time.sleep(10)
            status = requests.get(
                status_url,
                params={"fields": "status_code,status", "access_token": access_token},
                timeout=15
            ).json()
            code = status.get("status_code")
            if code == "FINISHED":
                print("[INSTAGRAM] Video procesado. Publicando...")
                break
            elif code == "ERROR":
                print(f"[INSTAGRAM ERROR] Error en procesamiento: {status}")
                return False
            else:
                print(f"[INSTAGRAM] Estado ({i+1}/15): {code}...")

        pub_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
        pub_res = requests.post(
            pub_url,
            data={"creation_id": creation_id, "access_token": access_token},
            timeout=30
        ).json()

        if "id" in pub_res:
            print(f"[INSTAGRAM SUCCESS] Reel publicado! ID: {pub_res['id']}")
            return True
        else:
            print(f"[INSTAGRAM ERROR] Fallo al publicar: {pub_res}")
            return False
    except Exception as e:
        print(f"[INSTAGRAM ERROR] {e}")
        return False

def publish_to_x(video_path: str, caption: str, config: Dict) -> bool:
    consumer_key = config.get("X_API_KEY")
    consumer_secret = config.get("X_API_SECRET")
    access_token = config.get("X_ACCESS_TOKEN")
    access_token_secret = config.get("X_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("[X TWITTER] Omitido: Faltan credenciales de X (verifica X_ACCESS_TOKEN y X_ACCESS_TOKEN_SECRET).")
        return False

    try:
        import tweepy
        print("[X TWITTER] Subiendo video a X...")
        auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth)

        media = api_v1.media_upload(filename=video_path, media_category="tweet_video")

        client_v2 = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        resp = client_v2.create_tweet(text=caption[:270], media_ids=[media.media_id])
        print(f"[X SUCCESS] Tweet publicado! ID: {resp.data['id']}")
        return True
    except Exception as e:
        print(f"[X TWITTER ERROR] {e}")
        return False

def publish_to_reddit(video_path: str, caption: str, config: Dict) -> bool:
    client_id = config.get("REDDIT_CLIENT_ID")
    client_secret = config.get("REDDIT_CLIENT_SECRET")
    username = config.get("REDDIT_USERNAME")
    password = config.get("REDDIT_PASSWORD")
    subreddit_name = config.get("REDDIT_SUBREDDIT", "videos")

    if not all([client_id, client_secret, username, password]):
        print("[REDDIT] Omitido: Faltan credenciales de Reddit.")
        return False

    try:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent="TikTokCrossposter/1.0"
        )
        subreddit = reddit.subreddit(subreddit_name)
        submission = subreddit.submit(title=caption[:300], selftext=caption)
        print(f"[REDDIT SUCCESS] Publicado en r/{subreddit_name}: {submission.url}")
        return True
    except Exception as e:
        print(f"[REDDIT ERROR] {e}")
        return False

# ==============================================================================
# ORQUESTADOR PRINCIPAL
# ==============================================================================

def run_crosspost_workflow(config: Optional[Dict] = None) -> Dict:
    """Ejecuta el flujo completo: detectar -> descargar -> publicar en todas las redes."""
    if config is None:
        config = dict(os.environ)

    tiktok_username = config.get("TIKTOK_USERNAME", "").strip()
    if not tiktok_username:
        print("[ERROR] TIKTOK_USERNAME no configurado.")
        return {"status": "error", "message": "Falta TIKTOK_USERNAME en variables de entorno."}

    # 1. Obtener lista de videos recientes
    videos = fetch_latest_tiktok_videos(tiktok_username, count=10)
    if not videos:
        return {"status": "error", "message": f"No se encontraron videos para @{tiktok_username}."}

    # 2. Filtrar solo los NO procesados
    processed_ids = load_processed_ids()
    force_run = bool(config.get("FORCE_RUN"))

    new_videos = [v for v in videos if v["id"] not in processed_ids] if not force_run else videos[:1]

    if not new_videos:
        latest_id = videos[0]["id"] if videos else "N/A"
        print(f"[INFO] No hay videos nuevos. El ultimo ID detectado ({latest_id}) ya fue procesado.")
        return {"status": "skipped", "message": "No hay videos nuevos que procesar."}

    # 3. Procesar el video mas reciente nuevo
    video_info = new_videos[0]
    video_id = video_info["id"]
    print(f"\n[START] =====================================")
    print(f"[START] Video ID: {video_id}")
    print(f"[START] Titulo: {video_info['title'][:70]}")
    print(f"[START] =====================================\n")

    temp_video_file = None
    results = {}

    try:
        # 4. Generar captions con IA
        captions = generate_ai_captions(video_info["title"], config)
        print(f"[CAPTIONS] YouTube: {captions['youtube'][:60]}")
        print(f"[CAPTIONS] Instagram: {captions['instagram'][:60]}")
        print(f"[CAPTIONS] X: {captions['x'][:60]}\n")

        # 5. Descargar video sin watermark via TikWM
        temp_video_file, direct_mp4_url = download_video_via_tikwm(video_info)

        # 6. Publicar en todas las redes
        print("\n[PUBLISHING] Publicando en redes sociales...")
        results["youtube"] = publish_to_youtube(temp_video_file, captions["youtube"], config)
        results["instagram"] = publish_to_instagram(direct_mp4_url, captions["instagram"], config)
        results["x"] = publish_to_x(temp_video_file, captions["x"], config)
        results["reddit"] = publish_to_reddit(temp_video_file, captions["reddit"], config)

        # 7. Guardar como procesado solo si hubo al menos 1 exito
        success_count = sum(1 for v in results.values() if v)
        if success_count > 0:
            save_processed_id(video_id)
            print(f"\n[DONE] Video {video_id} marcado como procesado.")
        else:
            print(f"\n[WARNING] Ninguna red publico exitosamente. Video NO marcado como procesado para reintentar en proxima ejecucion.")

        print(f"\n[SUMMARY] =====================================")
        print(f"[SUMMARY] YouTube   : {'OK' if results.get('youtube') else 'FALLO/OMITIDO'}")
        print(f"[SUMMARY] Instagram : {'OK' if results.get('instagram') else 'FALLO/OMITIDO'}")
        print(f"[SUMMARY] X Twitter : {'OK' if results.get('x') else 'FALLO/OMITIDO'}")
        print(f"[SUMMARY] Reddit    : {'OK' if results.get('reddit') else 'FALLO/OMITIDO'}")
        print(f"[SUMMARY] Total: {success_count}/{len(results)} redes publicadas.")
        print(f"[SUMMARY] =====================================\n")

        return {
            "status": "success" if success_count > 0 else "all_failed",
            "video_id": video_id,
            "title": video_info["title"],
            "captions": captions,
            "results": results
        }

    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        return {"status": "error", "message": str(e)}

    finally:
        if temp_video_file and os.path.exists(temp_video_file):
            try:
                os.remove(temp_video_file)
            except Exception:
                pass

if __name__ == "__main__":
    print("[START] TikTok Crossposter con IA - Iniciando...")
    output = run_crosspost_workflow()
    print("\n[RESULT]", json.dumps(output, indent=2, ensure_ascii=False))
