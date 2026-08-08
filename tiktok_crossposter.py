import os
import sys
import json
import time
import requests
import tempfile
import yt_dlp
from typing import Dict, List, Optional

# Forzar codificación UTF-8 en la consola
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

# ==============================================================================
# GENERADOR DE CONTENIDO CON IA (GEMINI API)
# ==============================================================================

def generate_ai_captions(original_title: str, config: Dict) -> Dict[str, str]:
    """Genera textos adaptados por IA para cada red social."""
    gemini_api_key = config.get("GEMINI_API_KEY")
    
    # Textos adaptados por defecto
    default_captions = {
        "youtube": f"{original_title[:80]} #Shorts",
        "instagram": f"✨ {original_title}\n\n#Reels #Viral #ContentCreator #Trending",
        "x": f"🔥 {original_title[:240]} #Trending",
        "reddit": original_title[:250] if original_title else "Nuevo contenido"
    }
    
    if not gemini_api_key:
        print("[AI] Omitiendo IA personalizada (No se proporcionó GEMINI_API_KEY). Usando formato optimizado.")
        return default_captions
        
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
        prompt = f"""Dado este título/idea de video de TikTok: '{original_title}', genera 4 adaptaciones en JSON para publicar en redes sociales:
1. "youtube": Título muy llamativo para YouTube Shorts (máximo 90 caracteres, incluye #Shorts).
2. "instagram": Caption divertido y visual para Instagram Reels con emojis y 5 hashtags relevantes.
3. "x": Tweet corto e impactante (máximo 250 caracteres) con enganche inicial.
4. "reddit": Título neutro y natural para Reddit.

Devuelve ÚNICAMENTE un objeto JSON válido con esas 4 llaves."""

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=10).json()
        
        text_response = res['candidates'][0]['content']['parts'][0]['text']
        # Limpiar bloques markdown
        clean_json = text_response.replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(clean_json)
        print("[AI SUCCESS] Textos personalizados generados con IA para cada red social.")
        return ai_data
    except Exception as e:
        print(f"[AI WARNING] Fallo al generar con IA, usando formato por defecto: {e}")
        return default_captions

# ==============================================================================
# DESCARGA Y PARSER DE TIKTOK
# ==============================================================================

def fetch_latest_tiktok_video(username: str) -> Optional[Dict]:
    """Obtiene la información del último video de TikTok."""
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
                title = latest.get('title') or latest.get('description') or f"Nuevo Video {video_id}"
                
                return {
                    "id": video_id,
                    "title": title,
                    "webpage_url": video_url
                }
    except Exception as e:
        print(f"[WARNING] Aviso extractor yt-dlp: {e}")
        
    return None

def download_tiktok_video(video_info: Dict) -> tuple[str, str]:
    """Descarga el video sin marca de agua usando la API oficial de TikWM."""
    video_url = video_info.get("webpage_url", "")
    print(f"[TIKWM] Solicitando enlace .mp4 sin marca de agua para: {video_url}...")
    
    tikwm_res = requests.post("https://www.tikwm.com/api/", data={"url": video_url}, timeout=20).json()
    
    if tikwm_res.get("code") == 0 and "data" in tikwm_res and "play" in tikwm_res["data"]:
        direct_mp4_url = tikwm_res["data"]["play"]
        if not direct_mp4_url.startswith("http"):
            direct_mp4_url = f"https://www.tikwm.com{direct_mp4_url}"
            
        print(f"[TIKWM SUCCESS] Enlace .mp4 sin marca de agua obtenido.")
        
        # Descargar archivo local
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, "video.mp4")
        
        r = requests.get(direct_mp4_url, stream=True, timeout=30)
        r.raise_for_status()
        with open(output_template, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return output_template, direct_mp4_url
    else:
        raise RuntimeError(f"Fallo al obtener enlace .mp4 de TikWM: {tikwm_res.get('msg')}")

# ==============================================================================
# PUBLICACIÓN EN REDES SOCIALES
# ==============================================================================

def publish_to_youtube(video_path: str, caption: str, config: Dict) -> bool:
    refresh_token = config.get("YOUTUBE_REFRESH_TOKEN")
    client_id = config.get("YOUTUBE_CLIENT_ID")
    client_secret = config.get("YOUTUBE_CLIENT_SECRET")
    
    if not (refresh_token and client_id and client_secret):
        print("[YOUTUBE] Omitido: Faltan credenciales en GitHub Secrets (YOUTUBE_REFRESH_TOKEN).")
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
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        print(f"[YOUTUBE SUCCESS] ¡Publicado con éxito en YouTube Shorts! ID: {response.get('id')}")
        return True
    except Exception as e:
        print(f"[YOUTUBE ERROR] Error publicando en YouTube: {e}")
        return False

def publish_to_instagram(direct_mp4_url: str, caption: str, config: Dict) -> bool:
    ig_user_id = config.get("INSTAGRAM_USER_ID")
    access_token = config.get("INSTAGRAM_ACCESS_TOKEN")
    
    if not (ig_user_id and access_token):
        print("[INSTAGRAM] Omitido: Faltan credenciales (INSTAGRAM_USER_ID o INSTAGRAM_ACCESS_TOKEN).")
        return False
        
    try:
        print(f"[INSTAGRAM] Enviando contenedor de Reel a Instagram para usuario {ig_user_id}...")
        container_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": direct_mp4_url,
            "caption": caption,
            "access_token": access_token
        }
        res = requests.post(container_url, data=payload, timeout=25).json()
        
        creation_id = res.get("id")
        if not creation_id:
            print(f"[INSTAGRAM ERROR] Error creando contenedor en Instagram: {res}")
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
        pub_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": access_token}, timeout=25).json()
        
        if "id" in pub_res:
            print(f"[INSTAGRAM SUCCESS] ¡Publicado con éxito en Instagram Reels! ID: {pub_res['id']}")
            return True
        else:
            print(f"[INSTAGRAM ERROR] Error final al publicar en Instagram: {pub_res}")
            return False
    except Exception as e:
        print(f"[INSTAGRAM ERROR] Error publicando en Instagram: {e}")
        return False

def publish_to_x(video_path: str, caption: str, config: Dict) -> bool:
    consumer_key = config.get("X_API_KEY")
    consumer_secret = config.get("X_API_SECRET")
    access_token = config.get("X_ACCESS_TOKEN")
    access_token_secret = config.get("X_ACCESS_TOKEN_SECRET")
    
    if not (consumer_key and consumer_secret and access_token and access_token_secret):
        print("[X TWITTER] Omitido: Faltan credenciales (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET).")
        return False
        
    try:
        import tweepy
        print("[X TWITTER] Subiendo video multimedia a X...")
        auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth)
        
        media = api_v1.media_upload(filename=video_path, media_category="tweet_video")
        
        client_v2 = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        response = client_v2.create_tweet(text=caption[:270], media_ids=[media.media_id])
        print(f"[X TWITTER SUCCESS] ¡Publicado con éxito en X (Twitter)! Tweet ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"[X TWITTER ERROR] Error publicando en X: {e}")
        return False

def publish_to_reddit(video_path: str, caption: str, config: Dict) -> bool:
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
        submission = subreddit.submit(title=caption[:300], selftext=f"Nuevo video: {caption}")
        print(f"[REDDIT SUCCESS] ¡Publicado con éxito en Reddit r/{subreddit_name}! URL: {submission.url}")
        return True
    except Exception as e:
        print(f"[REDDIT ERROR] Error publicando en Reddit: {e}")
        return False

# ==============================================================================
# ORQUESTADOR PRINCIPAL
# ==============================================================================

def run_crosspost_workflow(config: Optional[Dict] = None) -> Dict:
    if config is None:
        config = os.environ
        
    tiktok_username = config.get("TIKTOK_USERNAME", "")
    if not tiktok_username:
        print("[ERROR] TIKTOK_USERNAME no está configurado.")
        return {"status": "error", "message": "Por favor ingresa un nombre de usuario de TikTok."}
        
    video_info = fetch_latest_tiktok_video(tiktok_username)
    if not video_info:
        print(f"[ERROR] No se encontraron videos para @{tiktok_username}.")
        return {"status": "error", "message": f"No se encontraron videos para @{tiktok_username}."}
        
    video_id = video_info["id"]
    processed_ids = load_processed_ids()
    
    if video_id in processed_ids and not config.get("FORCE_RUN"):
        print(f"[INFO] El video ID {video_id} ya fue procesado previamente. Omitiendo.")
        return {"status": "skipped", "message": f"El video ID {video_id} ya fue procesado previamente."}
        
    print(f"[START] Procesando video ID: {video_id} ('{video_info['title'][:50]}')")
    
    temp_video_file = None
    results = {}
    try:
        # 1. Obtener descripciones adaptadas con IA
        ai_captions = generate_ai_captions(video_info["title"], config)
        
        # 2. Descargar video .mp4 sin marca de agua
        temp_video_file, direct_mp4_url = download_tiktok_video(video_info)
        print(f"[DOWNLOAD SUCCESS] Video listo en disco local: {temp_video_file}")
        
        # 3. Publicaciones paralelas en redes
        results["youtube"] = publish_to_youtube(temp_video_file, ai_captions["youtube"], config)
        results["instagram"] = publish_to_instagram(direct_mp4_url, ai_captions["instagram"], config)
        results["x"] = publish_to_x(temp_video_file, ai_captions["x"], config)
        results["reddit"] = publish_to_reddit(temp_video_file, ai_captions["reddit"], config)
        
        # Guardar en base de datos
        save_processed_id(video_id)
        
        return {
            "status": "success",
            "video_id": video_id,
            "title": video_info["title"],
            "ai_captions": ai_captions,
            "results": results
        }
    except Exception as e:
        print(f"[ERROR] Fallo en el flujo de publicación: {e}")
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
