import os
import json
import time
import requests
import tempfile
from typing import Dict, List, Optional

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
    Obtiene el último video de TikTok sin marca de agua usando la API gratuita de TikWM.
    """
    clean_username = username.strip().replace("@", "")
    url = f"https://www.tikwm.com/api/user/posts?unique_id={clean_username}&count=5"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if data.get("code") == 0 and "data" in data and "videos" in data["data"]:
            videos = data["data"]["videos"]
            if videos:
                latest = videos[0]
                video_id = str(latest.get("video_id") or latest.get("id"))
                title = latest.get("title", "Nuevo Video")
                # URL sin marca de agua
                play_url = latest.get("play")
                if play_url and not play_url.startswith("http"):
                    play_url = f"https://www.tikwm.com{play_url}"
                
                return {
                    "id": video_id,
                    "title": title,
                    "download_url": play_url,
                    "cover": latest.get("cover")
                }
    except Exception as e:
        print(f"⚠️ Error consultando TikTok de @{clean_username}: {e}")
    return None

def download_video_file(url: str) -> str:
    """Descarga el video temporalmente en el sistema de archivos."""
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    for chunk in response.iter_content(chunk_size=8192):
        temp_file.write(chunk)
    temp_file.close()
    return temp_file.name

# ==============================================================================
# MÓDULOS DE PUBLICACIÓN POR RED SOCIAL
# ==============================================================================

def publish_to_youtube(video_path: str, title: str, config: Dict) -> bool:
    """Publica el video en YouTube Shorts vía YouTube Data API v3."""
    refresh_token = config.get("YOUTUBE_REFRESH_TOKEN")
    client_id = config.get("YOUTUBE_CLIENT_ID")
    client_secret = config.get("YOUTUBE_CLIENT_SECRET")
    
    if not (refresh_token and client_id and client_secret):
        print("⏭️ YouTube ignorado (Faltan credenciales).")
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
        print(f"✅ Publicado con éxito en YouTube Shorts ID: {response.get('id')}")
        return True
    except Exception as e:
        print(f"❌ Error publicando en YouTube: {e}")
        return False

def publish_to_instagram(video_url: str, title: str, config: Dict) -> bool:
    """Publica el video como Reel en Instagram usando la Graph API de Meta."""
    ig_user_id = config.get("INSTAGRAM_USER_ID")
    access_token = config.get("INSTAGRAM_ACCESS_TOKEN")
    
    if not (ig_user_id and access_token):
        print("⏭️ Instagram ignorado (Faltan credenciales).")
        return False
        
    try:
        # Paso 1: Crear el contenedor de Reel
        container_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": title,
            "access_token": access_token
        }
        res = requests.post(container_url, data=payload, timeout=20)
        res_data = res.json()
        
        creation_id = res_data.get("id")
        if not creation_id:
            print(f"❌ Error al crear contenedor de Instagram: {res_data}")
            return False
            
        # Esperar procesamiento del video
        print("⏳ Procesando video en servidores de Instagram...")
        status_url = f"https://graph.facebook.com/v18.0/{creation_id}"
        for _ in range(12):
            time.sleep(10)
            status_res = requests.get(status_url, params={"fields": "status_code", "access_token": access_token}).json()
            status = status_res.get("status_code")
            if status == "FINISHED":
                break
            elif status == "ERROR":
                print("❌ Fallo en el procesamiento del video en Instagram.")
                return False
                
        # Paso 2: Publicar el contenedor
        publish_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
        pub_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": access_token}, timeout=20)
        pub_data = pub_res.json()
        
        if "id" in pub_data:
            print(f"✅ Publicado con éxito en Instagram Reel ID: {pub_data['id']}")
            return True
        else:
            print(f"❌ Error publicando contenedor en Instagram: {pub_data}")
            return False
    except Exception as e:
        print(f"❌ Error publicando en Instagram: {e}")
        return False

def publish_to_x(video_path: str, title: str, config: Dict) -> bool:
    """Publica el tweet con video usando Tweepy (X API v2 Free)."""
    consumer_key = config.get("X_API_KEY")
    consumer_secret = config.get("X_API_SECRET")
    access_token = config.get("X_ACCESS_TOKEN")
    access_token_secret = config.get("X_ACCESS_TOKEN_SECRET")
    
    if not (consumer_key and consumer_secret and access_token and access_token_secret):
        print("⏭️ X (Twitter) ignorado (Faltan credenciales).")
        return False
        
    try:
        import tweepy
        
        # v1.1 Client para Subida de Multimedia
        auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth)
        
        media = api_v1.media_upload(filename=video_path, media_category="tweet_video")
        
        # v2 Client para Publicar Tweet
        client_v2 = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        tweet_text = title[:270]
        response = client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
        print(f"✅ Publicado con éxito en X (Twitter) Tweet ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"❌ Error publicando en X (Twitter): {e}")
        return False

def publish_to_reddit(video_path: str, title: str, config: Dict) -> bool:
    """Publica el video en un Subreddit usando PRAW."""
    client_id = config.get("REDDIT_CLIENT_ID")
    client_secret = config.get("REDDIT_CLIENT_SECRET")
    username = config.get("REDDIT_USERNAME")
    password = config.get("REDDIT_PASSWORD")
    subreddit_name = config.get("REDDIT_SUBREDDIT", "videos")
    
    if not (client_id and client_secret and username and password):
        print("⏭️ Reddit ignorado (Faltan credenciales).")
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
        # Nota: Reddit API soporta envíos vía link o video nativo mediante praw
        submission = subreddit.submit(title=title[:300], selftext=f"Nuevo video: {title}")
        print(f"✅ Publicado con éxito en Reddit Subreddit r/{subreddit_name}: {submission.url}")
        return True
    except Exception as e:
        print(f"❌ Error publicando en Reddit: {e}")
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
        return {"status": "error", "message": "Por favor ingresa un nombre de usuario de TikTok."}
        
    video_info = fetch_latest_tiktok_video(tiktok_username)
    if not video_info:
        return {"status": "error", "message": f"No se encontraron videos para @{tiktok_username}."}
        
    video_id = video_info["id"]
    processed_ids = load_processed_ids()
    
    if video_id in processed_ids and not config.get("FORCE_RUN"):
        return {"status": "skipped", "message": f"El video ID {video_id} ya fue procesado previamente."}
        
    print(f"🎥 Procesando nuevo video: '{video_info['title']}' (ID: {video_id})")
    
    temp_video_file = None
    results = {}
    try:
        temp_video_file = download_video_file(video_info["download_url"])
        
        # 1. YouTube Shorts
        results["youtube"] = publish_to_youtube(temp_video_file, video_info["title"], config)
        
        # 2. Instagram Reels
        results["instagram"] = publish_to_instagram(video_info["download_url"], video_info["title"], config)
        
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
    finally:
        if temp_video_file and os.path.exists(temp_video_file):
            os.remove(temp_video_file)

if __name__ == "__main__":
    print("🚀 Ejecutando TikTok Crossposter...")
    output = run_crosspost_workflow()
    print(json.dumps(output, indent=2, ensure_ascii=False))
