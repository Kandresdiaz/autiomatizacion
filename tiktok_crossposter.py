import os
import sys
import json
import time
import requests
import tempfile
import yt_dlp
from typing import Dict, List, Optional

# Forzar codificación UTF-8 en la salida de la consola
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

def fetch_latest_tiktok_video(username: str) -> Optional[Dict]:
    """
    Obtiene el último video de TikTok usando yt-dlp y TikWM como respaldo.
    """
    clean_username = username.strip().replace("@", "")
    profile_url = f"https://www.tiktok.com/@{clean_username}"
    
    print(f"[SEARCH] Consultando perfil de TikTok: @{clean_username}...")
    
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'playlistend': 5,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(profile_url, download=False)
            entries = info.get('entries', [])
            if entries:
                latest = entries[0]
                video_id = str(latest.get('id'))
                video_url = latest.get('url') or f"https://www.tiktok.com/@{clean_username}/video/{video_id}"
                title = latest.get('title') or latest.get('description') or f"Nuevo Video de TikTok {video_id}"
                
                thumbnails = latest.get('thumbnails', [])
                cover = thumbnails[0]['url'] if thumbnails else None
                
                print(f"[FOUND] Video más reciente encontrado: ID {video_id} ('{title[:50]}...')")
                
                return {
                    "id": video_id,
                    "title": title,
                    "webpage_url": video_url,
                    "cover": cover
                }
    except Exception as e:
        print(f"[WARNING] Aviso yt-dlp: {e}")
        
    # Fallback TikWM API
    try:
        url = f"https://www.tikwm.com/api/user/posts?unique_id={clean_username}&count=5"
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=h, timeout=15)
        data = response.json()
        if data.get("code") == 0 and "data" in data and "videos" in data["data"]:
            videos = data["data"]["videos"]
            if videos:
                latest = videos[0]
                video_id = str(latest.get("video_id") or latest.get("id"))
                title = latest.get("title", "Nuevo Video")
                play_url = latest.get("play")
                if play_url and not play_url.startswith("http"):
                    play_url = f"https://www.tikwm.com{play_url}"
                return {
                    "id": video_id,
                    "title": title,
                    "download_url": play_url,
                    "webpage_url": f"https://www.tiktok.com/@{clean_username}/video/{video_id}",
                    "cover": latest.get("cover")
                }
    except Exception as e:
        print(f"[ERROR] Error en fallback TikWM: {e}")
        
    return None

def download_tiktok_video(video_info: Dict) -> tuple[str, str]:
    """Descarga el video usando yt-dlp y devuelve la ruta local y la URL directa .mp4 si está disponible."""
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "video.mp4")
    direct_mp4_url = ""
    
    if "webpage_url" in video_info:
        ydl_opts = {
            'outtmpl': output_template,
            'format': 'mp4/bestvideo+bestaudio/best',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            extracted = ydl.extract_info(video_info["webpage_url"], download=True)
            direct_mp4_url = extracted.get("url", "")
            
        if os.path.exists(output_template):
            return output_template, direct_mp4_url
            
    if "download_url" in video_info:
        direct_mp4_url = video_info["download_url"]
        response = requests.get(direct_mp4_url, stream=True, timeout=30)
        response.raise_for_status()
        with open(output_template, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return output_template, direct_mp4_url
        
    raise RuntimeError("No se pudo descargar el archivo mp4 del video.")

# ==============================================================================
# MÓDULOS DE PUBLICACIÓN POR RED SOCIAL
# ==============================================================================

def publish_to_youtube(video_path: str, title: str, config: Dict) -> bool:
    """Publica el video en YouTube Shorts vía YouTube Data API v3."""
    refresh_token = config.get("YOUTUBE_REFRESH_TOKEN")
    client_id = config.get("YOUTUBE_CLIENT_ID")
    client_secret = config.get("YOUTUBE_CLIENT_SECRET")
    
    if not (refresh_token and client_id and client_secret):
        print("[YOUTUBE] Omitido: Faltan credenciales (YOUTUBE_REFRESH_TOKEN, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET).")
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
                "title": f"{title[:90]} #Shorts",
                "description": f"{title}\n\n#Shorts #Viral #TikTok",
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        print(f"[YOUTUBE SUCCESS] Publicado con exito en YouTube Shorts ID: {response.get('id')}")
        return True
    except Exception as e:
        print(f"[YOUTUBE ERROR] Error publicando en YouTube Shorts: {e}")
        return False

def publish_to_instagram(direct_mp4_url: str, title: str, config: Dict) -> bool:
    """Publica el video como Reel en Instagram usando la Graph API de Meta."""
    ig_user_id = config.get("INSTAGRAM_USER_ID")
    access_token = config.get("INSTAGRAM_ACCESS_TOKEN")
    
    if not (ig_user_id and access_token):
        print("[INSTAGRAM] Omitido: Faltan credenciales (INSTAGRAM_USER_ID o INSTAGRAM_ACCESS_TOKEN).")
        return False
        
    if not direct_mp4_url:
        print("[INSTAGRAM] Omitido: Se requiere una URL .mp4 accesible para Meta Graph API.")
        return False
        
    try:
        print(f"[INSTAGRAM] Enviando contenedor de Reel a Instagram para usuario {ig_user_id}...")
        container_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": direct_mp4_url,
            "caption": title[:2000] if title else "Nuevo Reel",
            "access_token": access_token
        }
        res = requests.post(container_url, data=payload, timeout=25)
        res_data = res.json()
        
        creation_id = res_data.get("id")
        if not creation_id:
            print(f"[INSTAGRAM ERROR] Error creando contenedor en Instagram: {res_data}")
            return False
            
        print(f"[INSTAGRAM] Contenedor creado (ID: {creation_id}). Esperando procesamiento en Meta...")
        status_url = f"https://graph.facebook.com/v18.0/{creation_id}"
        for attempt in range(12):
            time.sleep(10)
            status_res = requests.get(status_url, params={"fields": "status_code", "access_token": access_token}, timeout=15).json()
            status = status_res.get("status_code")
            if status == "FINISHED":
                print("[INSTAGRAM] Video procesado exitosamente por Instagram.")
                break
            elif status == "ERROR":
                print(f"[INSTAGRAM ERROR] Error en procesamiento de video por Instagram: {status_res}")
                return False
                
        # Publicar contenedor
        publish_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
        pub_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": access_token}, timeout=25)
        pub_data = pub_res.json()
        
        if "id" in pub_data:
            print(f"[INSTAGRAM SUCCESS] Publicado con exito en Instagram Reels ID: {pub_data['id']}")
            return True
        else:
            print(f"[INSTAGRAM ERROR] Error final al publicar en Instagram: {pub_data}")
            return False
    except Exception as e:
        print(f"[INSTAGRAM ERROR] Error publicando en Instagram Reels: {e}")
        return False

def publish_to_x(video_path: str, title: str, config: Dict) -> bool:
    """Publica el tweet con video usando Tweepy (X API v2 Free)."""
    consumer_key = config.get("X_API_KEY")
    consumer_secret = config.get("X_API_SECRET")
    access_token = config.get("X_ACCESS_TOKEN")
    access_token_secret = config.get("X_ACCESS_TOKEN_SECRET")
    
    if not (consumer_key and consumer_secret):
        print("[X TWITTER] Omitido: Faltan credenciales principales (X_API_KEY, X_API_SECRET).")
        return False
        
    if not (access_token and access_token_secret):
        print("[X TWITTER] Omitido: Se requieren X_ACCESS_TOKEN y X_ACCESS_TOKEN_SECRET con permisos de Escritura.")
        return False
        
    try:
        import tweepy
        print("[X TWITTER] Subiendo video a X (Twitter)...")
        auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth)
        
        media = api_v1.media_upload(filename=video_path, media_category="tweet_video")
        
        client_v2 = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        tweet_text = title[:270] if title else "Nuevo video de TikTok"
        response = client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
        print(f"[X TWITTER SUCCESS] Publicado con exito en X (Twitter) Tweet ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"[X TWITTER ERROR] Error publicando en X (Twitter): {e}")
        return False

def publish_to_reddit(video_path: str, title: str, config: Dict) -> bool:
    """Publica el video en un Subreddit usando PRAW."""
    client_id = config.get("REDDIT_CLIENT_ID")
    client_secret = config.get("REDDIT_CLIENT_SECRET")
    username = config.get("REDDIT_USERNAME")
    password = config.get("REDDIT_PASSWORD")
    subreddit_name = config.get("REDDIT_SUBREDDIT", "videos")
    
    if not (client_id and client_secret and username and password):
        print("[REDDIT] Omitido: Faltan credenciales (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD).")
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
        submission = subreddit.submit(title=title[:300] or "Nuevo video", selftext=f"Nuevo video: {title}")
        print(f"[REDDIT SUCCESS] Publicado con exito en Reddit r/{subreddit_name}: {submission.url}")
        return True
    except Exception as e:
        print(f"[REDDIT ERROR] Error publicando en Reddit: {e}")
        return False

# ==============================================================================
# ORQUESTADOR PRINCIPAL
# ==============================================================================

def run_crosspost_workflow(config: Optional[Dict] = None) -> Dict:
    """Ejecuta el ciclo de automatización completo."""
    if config is None:
        config = os.environ
        
    tiktok_username = config.get("TIKTOK_USERNAME", "")
    if not tiktok_username:
        print("[ERROR] TIKTOK_USERNAME no esta configurado.")
        return {"status": "error", "message": "Por favor ingresa un nombre de usuario de TikTok."}
        
    video_info = fetch_latest_tiktok_video(tiktok_username)
    if not video_info:
        print(f"[ERROR] No se pudieron encontrar videos publicos para @{tiktok_username}.")
        return {"status": "error", "message": f"No se encontraron videos para @{tiktok_username}."}
        
    video_id = video_info["id"]
    processed_ids = load_processed_ids()
    
    if video_id in processed_ids and not config.get("FORCE_RUN"):
        print(f"[INFO] El video ID {video_id} ya se encuentra registrado como procesado en processed_videos.json. Omitiendo.")
        return {"status": "skipped", "message": f"El video ID {video_id} ya fue procesado previamente."}
        
    print(f"[START] Iniciando republicacion de nuevo video ID: {video_id} ('{video_info['title'][:60]}')")
    
    temp_video_file = None
    results = {}
    try:
        temp_video_file, direct_mp4_url = download_tiktok_video(video_info)
        print(f"[DOWNLOAD] Video descargado correctamente en disco local: {temp_video_file}")
        
        # 1. YouTube Shorts
        results["youtube"] = publish_to_youtube(temp_video_file, video_info["title"], config)
        
        # 2. Instagram Reels
        results["instagram"] = publish_to_instagram(direct_mp4_url, video_info["title"], config)
        
        # 3. X (Twitter)
        results["x"] = publish_to_x(temp_video_file, video_info["title"], config)
        
        # 4. Reddit
        results["reddit"] = publish_to_reddit(temp_video_file, video_info["title"], config)
        
        # Guardar como procesado
        save_processed_id(video_id)
        
        return {
            "status": "success",
            "video_id": video_id,
            "title": video_info["title"],
            "results": results
        }
    except Exception as e:
        print(f"[ERROR] Error durante el flujo de publicacion: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if temp_video_file and os.path.exists(temp_video_file):
            try:
                os.remove(temp_video_file)
            except Exception:
                pass

if __name__ == "__main__":
    print("[START] Ejecutando TikTok Crossposter...")
    output = run_crosspost_workflow()
    print(json.dumps(output, indent=2, ensure_ascii=False))
