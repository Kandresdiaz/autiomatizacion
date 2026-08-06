import os
import json
import streamlit as st
from tiktok_crossposter import run_crosspost_workflow, fetch_latest_tiktok_video, load_processed_ids

st.set_page_config(
    page_title="TikTok Multi-Platform Crossposter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS Modernos
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #ff0050 0%, #00f2fe 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 16px;
    }
    .stButton>button:hover {
        opacity: 0.9;
        transform: scale(1.01);
    }
    .metric-card {
        background-color: #1e222d;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #2e3440;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ TikTok Crossposter Dashboard")
st.caption("Automatiza la republicación de TikTok a YouTube Shorts, Instagram Reels, X y Reddit de forma 100% gratuita.")

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/tiktok.png", width=64)
    st.header("Configuración Rápida")
    
    tiktok_username = st.text_input("Usuario de TikTok", value="@kevindiaz", help="Tu usuario público de TikTok con o sin @")
    
    st.divider()
    st.subheader("Estado de Conexiones")
    
    # Indicadores de credenciales configuradas
    yt_ok = bool(os.getenv("YOUTUBE_CLIENT_ID"))
    ig_ok = bool(os.getenv("INSTAGRAM_ACCESS_TOKEN"))
    x_ok = bool(os.getenv("X_API_KEY"))
    rd_ok = bool(os.getenv("REDDIT_CLIENT_ID"))
    
    st.markdown(f"🔴 YouTube Shorts: **{'✅ Configurado' if yt_ok else '⚠️ Sin Llaves'}**")
    st.markdown(f"🔴 Instagram Reels: **{'✅ Configurado' if ig_ok else '⚠️ Sin Llaves'}**")
    st.markdown(f"🔴 X (Twitter): **{'✅ Configurado' if x_ok else '⚠️ Sin Llaves'}**")
    st.markdown(f"🔴 Reddit: **{'✅ Configurado' if rd_ok else '⚠️ Sin Llaves'}**")
    
    st.divider()
    st.info("💡 **Tip:** Puedes configurar tus llaves en la pestaña de 'Configuración de Credenciales' o mediante GitHub Secrets.")

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Panel de Control", "🔑 Credenciales y APIs", "📋 Historial", "📖 Guía Rápida"])

# TAB 1: PANEL DE CONTROL
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Vista Previa de TikTok")
        if tiktok_username:
            with st.spinner("Buscando último video..."):
                video_info = fetch_latest_tiktok_video(tiktok_username)
                if video_info:
                    st.success("✅ ¡Último video detectado!")
                    st.markdown(f"**Título:** {video_info['title']}")
                    st.markdown(f"**ID de Video:** `{video_info['id']}`")
                    if video_info.get("cover"):
                        st.image(video_info["cover"], width=280, caption="Portada del Video")
                else:
                    st.warning(f"No se pudo obtener el último video para {tiktok_username}. Verifica el nombre de usuario.")
        else:
            st.info("Por favor ingresa un nombre de usuario de TikTok en la barra lateral.")

    with col2:
        st.subheader("2. Lanzar Automatización")
        st.write("Haz clic para procesar manualmente el último video y resubirlo a tus redes configuradas.")
        
        force_run = st.checkbox("Forzar publicación (ignorar si ya fue procesado antes)")
        
        if st.button("🚀 PUBLICAR AHORA"):
            if not tiktok_username:
                st.error("Debes especificar un usuario de TikTok primero.")
            else:
                config = dict(os.environ)
                config["TIKTOK_USERNAME"] = tiktok_username
                if force_run:
                    config["FORCE_RUN"] = "1"
                    
                with st.spinner("Descargando video sin marca de agua y resubiendo a redes..."):
                    res = run_crosspost_workflow(config)
                    
                if res.get("status") == "success":
                    st.balloons()
                    st.success(f"🎉 ¡Publicación completada para: {res.get('title')}!")
                    
                    results = res.get("results", {})
                    st.json(results)
                elif res.get("status") == "skipped":
                    st.warning(f"ℹ️ {res.get('message')}")
                else:
                    st.error(f"❌ Error: {res.get('message')}")

# TAB 2: CONFIGURACIÓN DE CREDENCIALES
with tab2:
    st.subheader("🔑 Configuración de Llaves de API Gratis")
    st.write("Ingresa tus credenciales aquí para probar localmente o copiarlas a tus GitHub Secrets.")
    
    with st.form("credentials_form"):
        st.markdown("### 🔴 YouTube Shorts API")
        yt_client_id = st.text_input("YouTube Client ID", value=os.getenv("YOUTUBE_CLIENT_ID", ""))
        yt_client_secret = st.text_input("YouTube Client Secret", value=os.getenv("YOUTUBE_CLIENT_SECRET", ""), type="password")
        yt_refresh_token = st.text_input("YouTube Refresh Token", value=os.getenv("YOUTUBE_REFRESH_TOKEN", ""), type="password")
        
        st.markdown("### 🔴 Instagram Graph API")
        ig_user_id = st.text_input("Instagram User ID", value=os.getenv("INSTAGRAM_USER_ID", ""))
        ig_access_token = st.text_input("Instagram Access Token", value=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""), type="password")
        
        st.markdown("### 🔴 X (Twitter) API v2 Free")
        x_api_key = st.text_input("X API Key", value=os.getenv("X_API_KEY", ""))
        x_api_secret = st.text_input("X API Secret", value=os.getenv("X_API_SECRET", ""), type="password")
        x_access_token = st.text_input("X Access Token", value=os.getenv("X_ACCESS_TOKEN", ""))
        x_access_secret = st.text_input("X Access Token Secret", value=os.getenv("X_ACCESS_TOKEN_SECRET", ""), type="password")
        
        st.markdown("### 🔴 Reddit API")
        rd_client_id = st.text_input("Reddit Client ID", value=os.getenv("REDDIT_CLIENT_ID", ""))
        rd_client_secret = st.text_input("Reddit Client Secret", value=os.getenv("REDDIT_CLIENT_SECRET", ""), type="password")
        rd_username = st.text_input("Reddit Username", value=os.getenv("REDDIT_USERNAME", ""))
        rd_password = st.text_input("Reddit Password", value=os.getenv("REDDIT_PASSWORD", ""), type="password")
        
        save_btn = st.form_submit_button("💾 Guardar Cambios")
        
        if save_btn:
            # Guardar en archivo .env
            env_content = f"""TIKTOK_USERNAME={tiktok_username}
YOUTUBE_CLIENT_ID={yt_client_id}
YOUTUBE_CLIENT_SECRET={yt_client_secret}
YOUTUBE_REFRESH_TOKEN={yt_refresh_token}
INSTAGRAM_USER_ID={ig_user_id}
INSTAGRAM_ACCESS_TOKEN={ig_access_token}
X_API_KEY={x_api_key}
X_API_SECRET={x_api_secret}
X_ACCESS_TOKEN={x_access_token}
X_ACCESS_TOKEN_SECRET={x_access_secret}
REDDIT_CLIENT_ID={rd_client_id}
REDDIT_CLIENT_SECRET={rd_client_secret}
REDDIT_USERNAME={rd_username}
REDDIT_PASSWORD={rd_password}
"""
            with open(".env", "w", encoding="utf-8") as f:
                f.write(env_content)
            st.success("✅ Credenciales guardadas con éxito en `.env`!")

# TAB 3: HISTORIAL
with tab3:
    st.subheader("📋 Historial de Videos Procesados")
    processed_ids = load_processed_ids()
    st.write(f"Total de videos registrados como procesados: **{len(processed_ids)}**")
    
    if processed_ids:
        st.json(processed_ids)
    else:
        st.info("Aún no hay registros de videos procesados.")

# TAB 4: GUÍA RÁPIDA DE APIS
with tab4:
    st.subheader("⚡ Dónde sacar cada API gratis en 2 minutos")
    
    st.markdown("""
    #### 1️⃣ YouTube Shorts (Google Cloud Console)
    1. Entra a [Google Cloud Console](https://console.cloud.google.com/).
    2. Crea un proyecto gratis y busca **YouTube Data API v3** ➔ Hacer clic en **Habilitar**.
    3. En **Credenciales**, crea un **OAuth 2.0 Client ID**.
    
    #### 2️⃣ Instagram Reels (Meta for Developers)
    1. Entra a [Meta Developers](https://developers.facebook.com/).
    2. Crea una app de tipo **Business**.
    3. Agrega el producto **Instagram Graph API** y genera un *User Access Token* de larga duración.
    
    #### 3️⃣ X (Twitter) API v2 Free
    1. Entra a [X Developer Portal](https://developer.x.com/).
    2. En tu proyecto, entra a **Keys and Tokens**.
    3. Genera tus **API Key, API Key Secret, Access Token** y **Access Token Secret** (asegúrate de que los permisos estén en *Read and Write*).
    
    #### 4️⃣ Reddit API
    1. Entra a [Reddit App Preferences](https://www.reddit.com/prefs/apps).
    2. Haz clic en **create another app...** abajo.
    3. Selecciona la opción **script**, ponle de nombre `TikTokCrossposter` y obtén tu `Client ID` y `Client Secret`.
    """)
