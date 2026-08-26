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

import datetime

PROCESSED_FILE = "processed_videos.json"
QUEUE_FILE = "pending_queue.json"

# ==============================================================================
# UTILIDADES
# ==============================================================================

def get_config() -> Dict[str, str]:
    """Obtiene la configuración combinando os.environ, .env y st.secrets de Streamlit."""
    config = dict(os.environ)

    # Cargar .env local si existe
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        config[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass

    # Cargar st.secrets si se está ejecutando dentro de Streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            for k, v in st.secrets.items():
                if isinstance(v, str):
                    config[k] = v
                elif isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        if isinstance(sub_v, str):
                            config[sub_k] = sub_v
    except Exception:
        pass

    return config

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

def remove_processed_id(video_id: str) -> bool:
    """Remueve un video de la lista de procesados para permitir volver a publicarlo."""
    processed = load_processed_ids()
    if video_id in processed:
        processed.remove(video_id)
        with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
            json.dump(processed, f, indent=2)
        return True
    return False

def load_pending_queue() -> List[Dict]:
    """Carga la lista de videos pendientes en cola."""
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_pending_queue(queue: List[Dict]):
    """Guarda la lista de videos en cola pendiente."""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

def add_to_pending_queue(videos: List[Dict]) -> int:
    """Agrega videos a la cola pendiente omitiendo duplicados."""
    queue = load_pending_queue()
    processed = load_processed_ids()
    existing_ids = {v["id"] for v in queue} | set(processed)
    
    added_count = 0
    for video in videos:
        if video["id"] not in existing_ids:
            queue.append(video)
            existing_ids.add(video["id"])
            added_count += 1
            
    if added_count > 0:
        save_pending_queue(queue)
    return added_count

def pop_from_pending_queue() -> Optional[Dict]:
    """Toma y remueve el primer video de la cola pendiente."""
    queue = load_pending_queue()
    if not queue:
        return None
    video_info = queue.pop(0)
    save_pending_queue(queue)
    return video_info

def remove_from_pending_queue(video_id: str) -> bool:
    """Elimina un video específico de la cola por su ID."""
    queue = load_pending_queue()
    initial_len = len(queue)
    queue = [v for v in queue if v.get("id") != video_id]
    if len(queue) != initial_len:
        save_pending_queue(queue)
        return True
    return False

def load_active_platforms() -> Dict[str, bool]:
    path = "active_platforms.json"
    default = {"youtube": True, "instagram": True, "x": True, "reddit": True}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {k: bool(data.get(k, True)) for k in default}
        except Exception:
            return default
    return default


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
    Obtiene los últimos videos del perfil de TikTok usando yt-dlp.
    Devuelve lista de dicts con id, title, webpage_url, upload_date, timestamp, thumbnail, duration.
    """
    clean_username = username.strip().replace("@", "")
    profile_url = f"https://www.tiktok.com/@{clean_username}"
    print(f"[SEARCH] Buscando los últimos {count} videos en TikTok @{clean_username}...")

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
                
                # Extraer miniatura (cover)
                thumbnail_url = ""
                thumbnails = e.get('thumbnails') or []
                if thumbnails and isinstance(thumbnails, list):
                    thumbnail_url = thumbnails[0].get('url', '')
                
                # Extraer timestamp y formato de fecha
                ts = e.get('timestamp')
                upload_date_str = ""
                if ts:
                    try:
                        dt = datetime.datetime.fromtimestamp(ts)
                        upload_date_str = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                
                duration = e.get('duration') or 0

                videos.append({
                    "id": video_id,
                    "title": title,
                    "webpage_url": webpage_url,
                    "timestamp": ts or 0,
                    "upload_date": upload_date_str,
                    "thumbnail": thumbnail_url,
                    "duration": duration
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

def publish_to_youtube(video_path: str, caption: str, config: Dict) -> Tuple[bool, str]:
    refresh_token = config.get("YOUTUBE_REFRESH_TOKEN")
    client_id = config.get("YOUTUBE_CLIENT_ID")
    client_secret = config.get("YOUTUBE_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        msg = "Falta YOUTUBE_REFRESH_TOKEN o credenciales de Google."
        print(f"[YOUTUBE] Omitido: {msg}")
        return False, msg

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
        v_id = resp.get("id", "")
        print(f"[YOUTUBE SUCCESS] Publicado! ID: {v_id}")
        return True, f"Publicado con éxito (ID: {v_id})"
    except Exception as e:
        msg = str(e)
        print(f"[YOUTUBE ERROR] {msg}")
        return False, f"Error: {msg}"

def publish_to_instagram(direct_mp4_url: str, caption: str, config: Dict) -> Tuple[bool, str]:
    ig_user_id = config.get("INSTAGRAM_USER_ID")
    access_token = config.get("INSTAGRAM_ACCESS_TOKEN")

    if not all([ig_user_id, access_token]):
        msg = "Falta INSTAGRAM_USER_ID o INSTAGRAM_ACCESS_TOKEN."
        print(f"[INSTAGRAM] Omitido: {msg}")
        return False, msg

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
            err_msg = err.get("message", str(res))
            print(f"[INSTAGRAM ERROR] No se creó contenedor: {err_msg}")
            return False, f"Meta API Error: {err_msg}"

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
                err_msg = str(status)
                print(f"[INSTAGRAM ERROR] Error en procesamiento: {err_msg}")
                return False, f"Error procesamiento Meta: {err_msg}"
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
            return True, f"Reel publicado (ID: {pub_res['id']})"
        else:
            err_msg = str(pub_res)
            print(f"[INSTAGRAM ERROR] Falló al publicar: {err_msg}")
            return False, f"Fallo al publicar Reel: {err_msg}"
    except Exception as e:
        print(f"[INSTAGRAM ERROR] {e}")
        return False, f"Error: {e}"

def publish_to_x(video_path: str, caption: str, config: Dict) -> Tuple[bool, str]:
    consumer_key = config.get("X_API_KEY")
    consumer_secret = config.get("X_API_SECRET")
    access_token = config.get("X_ACCESS_TOKEN")
    access_token_secret = config.get("X_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        msg = "Faltan credenciales de X (X_ACCESS_TOKEN y X_ACCESS_TOKEN_SECRET)."
        print(f"[X TWITTER] Omitido: {msg}")
        return False, msg

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
        tw_id = resp.data["id"]
        print(f"[X SUCCESS] Tweet publicado! ID: {tw_id}")
        return True, f"Tweet publicado (ID: {tw_id})"
    except Exception as e:
        msg = str(e)
        print(f"[X TWITTER ERROR] {msg}")
        return False, f"Error X API: {msg}"

def publish_to_reddit(video_path: str, caption: str, config: Dict) -> Tuple[bool, str]:
    client_id = config.get("REDDIT_CLIENT_ID")
    client_secret = config.get("REDDIT_CLIENT_SECRET")
    username = config.get("REDDIT_USERNAME")
    password = config.get("REDDIT_PASSWORD")
    subreddit_name = config.get("REDDIT_SUBREDDIT", "videos")

    if not all([client_id, client_secret, username, password]):
        msg = "Faltan credenciales de Reddit."
        print(f"[REDDIT] Omitido: {msg}")
        return False, msg

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
        return True, f"Publicado en Reddit: {submission.url}"
    except Exception as e:
        msg = str(e)
        print(f"[REDDIT ERROR] {msg}")
        return False, f"Error Reddit API: {msg}"

# ==============================================================================
# ORQUESTADOR PRINCIPAL
# ==============================================================================

def crosspost_single_video(video_info: Dict, config: Optional[Dict] = None) -> Dict:
    """Procesa y publica un único video específico en todas las redes configuradas."""
    if config is None:
        config = get_config()

    video_id = video_info.get("id", "")
    title = video_info.get("title", "Video de TikTok")
    print(f"\n[START] =====================================")
    print(f"[START] Video ID: {video_id}")
    print(f"[START] Título: {title[:70]}")
    print(f"[START] =====================================\n")

    temp_video_file = None
    results = {}

    try:
        # 1. Generar captions con IA
        captions = generate_ai_captions(title, config)
        print(f"[CAPTIONS] YouTube: {captions['youtube'][:60]}")
        print(f"[CAPTIONS] Instagram: {captions['instagram'][:60]}")
        print(f"[CAPTIONS] X: {captions['x'][:60]}\n")

        # 2. Descargar video sin watermark via TikWM
        temp_video_file, direct_mp4_url = download_video_via_tikwm(video_info)

        # 3. Publicar en todas las redes
        print("\n[PUBLISHING] Publicando en redes sociales...")
        active = load_active_platforms()

        results["youtube"] = publish_to_youtube(temp_video_file, captions["youtube"], config) if active.get("youtube", True) else (False, "Desactivado en canales")
        results["instagram"] = publish_to_instagram(direct_mp4_url, captions["instagram"], config) if active.get("instagram", True) else (False, "Desactivado en canales")
        results["x"] = publish_to_x(temp_video_file, captions["x"], config) if active.get("x", True) else (False, "Desactivado en canales")
        results["reddit"] = publish_to_reddit(temp_video_file, captions["reddit"], config) if active.get("reddit", True) else (False, "Desactivado en canales")

        # 4. Guardar como procesado si al menos 1 tuvo éxito
        success_count = sum(1 for (ok, _) in results.values() if ok)
        if success_count > 0:
            save_processed_id(video_id)
            print(f"\n[DONE] Video {video_id} marcado como procesado.")
        else:
            print(f"\n[WARNING] Ninguna red publicó exitosamente. Video NO marcado como procesado.")

        print(f"\n[SUMMARY] =====================================")
        for net, (ok, msg) in results.items():
            print(f"[SUMMARY] {net.capitalize():10}: {'OK' if ok else 'FALLO/OMITIDO'} ({msg})")
        print(f"[SUMMARY] Total: {success_count}/{len(results)} redes publicadas.")
        print(f"[SUMMARY] =====================================\n")

        return {
            "status": "success" if success_count > 0 else "all_failed",
            "video_id": video_id,
            "title": title,
            "captions": captions,
            "results": {k: ok for k, (ok, _) in results.items()},
            "details": {k: msg for k, (_, msg) in results.items()}
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

def run_crosspost_workflow(config: Optional[Dict] = None) -> Dict:
    """
    Ejecuta el flujo completo:
    1. Si FORCE_RUN=1, procesa el video más reciente.
    2. Si hay videos nuevos en TikTok, procesa el más reciente.
    3. Si no hay videos nuevos pero hay cola pendiente (pending_queue.json), procesa 1 video de la cola.
    """
    if config is None:
        config = get_config()

    tiktok_username = config.get("TIKTOK_USERNAME", "").strip()
    if not tiktok_username:
        print("[ERROR] TIKTOK_USERNAME no configurado.")
        return {"status": "error", "message": "Falta TIKTOK_USERNAME en variables de entorno."}

    force_run = bool(config.get("FORCE_RUN"))

    # 1. Buscar videos recientes en TikTok
    videos = fetch_latest_tiktok_videos(tiktok_username, count=10)

    if force_run and videos:
        print("[WORKFLOW] Ejecución forzada: procesando último video detectado.")
        return crosspost_single_video(videos[0], config)

    processed_ids = load_processed_ids()
    new_videos = [v for v in videos if v["id"] not in processed_ids]

    if new_videos:
        print(f"[WORKFLOW] Nuevo video detectado en el perfil: {new_videos[0]['id']}")
        return crosspost_single_video(new_videos[0], config)

    # 2. Revisar cola de videos pendientes
    pending_video = pop_from_pending_queue()
    if pending_video:
        print(f"[WORKFLOW] Procesando video guardado en la cola pendiente: {pending_video['id']}")
        return crosspost_single_video(pending_video, config)

    print("[INFO] No hay videos nuevos ni pendientes en la cola.")
    return {"status": "skipped", "message": "No hay videos nuevos ni pendientes en cola que procesar."}

if __name__ == "__main__":
    print("[START] TikTok Crossposter con IA - Iniciando...")
    output = run_crosspost_workflow()
    print("\n[RESULT]", json.dumps(output, indent=2, ensure_ascii=False))
