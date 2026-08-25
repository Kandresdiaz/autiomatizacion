import os
import json
import streamlit as st
from tiktok_crossposter import run_crosspost_workflow, fetch_latest_tiktok_videos, load_processed_ids

st.set_page_config(
    page_title="Dark Command Center",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo Dark Command Center (Opción 1) - CSS personalizado
st.markdown("""
    <style>
    /* Fondo principal y barra lateral */
    .stApp {
        background-color: #050505 !important;
        color: #ffffff !important;
    }
    
    /* Remover elementos innecesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Contenedor principal */
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }
    
    /* Botón PUBLICAR AHORA */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #8a2be2 0%, #ff007f 100%) !important;
        color: white !important;
        font-weight: 800 !important;
        border: none !important;
        padding: 16px 32px !important;
        border-radius: 50px !important;
        font-size: 20px !important;
        letter-spacing: 2px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(138, 43, 226, 0.4) !important;
        text-transform: uppercase;
        margin-bottom: 20px;
    }
    .stButton>button:hover {
        opacity: 0.95 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 0, 127, 0.6) !important;
    }
    
    /* Card de vista previa de TikTok */
    .preview-card {
        background-color: #0c0c0e;
        border: 1px solid #1a1a1e;
        border-radius: 20px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    /* Panel de controles */
    .controls-panel {
        background-color: #0c0c0e;
        border: 1px solid #1a1a1e;
        border-radius: 20px;
        padding: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        height: 100%;
    }
    
    /* Título de secciones */
    .section-title {
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #66666e;
        margin-bottom: 20px;
    }
    
    /* Toggles */
    .stCheckbox>label {
        font-size: 16px !important;
        font-weight: 500 !important;
        color: #ffffff !important;
    }
    
    /* Barra de estado */
    .status-bar {
        background-color: #0c0c0e;
        border-top: 1px solid #1a1a1e;
        padding: 12px 24px;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        color: #88888e;
        z-index: 999;
    }
    .status-dot {
        height: 8px;
        width: 8px;
        background-color: #00ff88;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
        box-shadow: 0 0 8px #00ff88;
    }
    </style>
""", unsafe_allow_html=True)

# Helper para cargar/guardar configuración de plataformas activas
def load_active() -> dict:
    path = "active_platforms.json"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"youtube": True, "instagram": True, "x": True, "reddit": True}

def save_active(data: dict):
    with open("active_platforms.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

active_platforms = load_active()

# Cargar configuración del .env para el usuario
tiktok_user = os.getenv("TIKTOK_USERNAME", "@b00kevin")

# Contenedor principal
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# 1. BOTÓN GRANDE DE PUBLICACIÓN (Arriba del todo)
st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
if st.button("⚡ PUBLICAR AHORA"):
    with st.spinner("Procesando último video de TikTok y publicando..."):
        config = dict(os.environ)
        config["FORCE_RUN"] = "1"  # Forzar ejecución para publicar el último video actual
        res = run_crosspost_workflow(config)
        
        if res.get("status") in ["success", "partial_failure"]:
            st.balloons()
            st.success(f"¡Publicado exitosamente! Video: {res.get('title')}")
            # Mostrar resultados por red
            for net, ok in res.get("results", {}).items():
                if ok:
                    st.markdown(f"✅ **{net.capitalize()}**: Publicado con éxito.")
                else:
                    st.markdown(f"❌ **{net.capitalize()}**: Falló o no configurado.")
        elif res.get("status") == "skipped":
            st.warning("El último video ya fue publicado en tus redes sociales previamente.")
        else:
            st.error(f"Error: {res.get('message')}")
st.markdown('</div>', unsafe_allow_html=True)

# 2. COLUMNAS PRINCIPALES (Vista previa izquierda, Toggles derecha)
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.markdown('<div class="preview-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Vista Previa de TikTok</div>', unsafe_allow_html=True)
    
    with st.spinner("Buscando último video..."):
        videos = fetch_latest_tiktok_videos(tiktok_user, count=1)
        if videos:
            latest = videos[0]
            st.markdown(f"### {latest['title'] or 'Video sin título'}")
            st.caption(f"TikTok ID: {latest['id']}")
            
            # Buscamos miniatura / reproductor
            st.video(latest['webpage_url'])
        else:
            st.warning(f"No se detectaron videos para el usuario {tiktok_user}. Verifica tu configuración.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="controls-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Canales de Publicación</div>', unsafe_allow_html=True)
    st.write("Elige en qué redes sociales quieres que el robot publique de forma automática:")
    
    # Checkboxes estilizados como Toggles
    yt_active = st.checkbox("YouTube Shorts", value=active_platforms.get("youtube", True), key="yt_toggle")
    ig_active = st.checkbox("Instagram Reels", value=active_platforms.get("instagram", True), key="ig_toggle")
    x_active = st.checkbox("X (Twitter)", value=active_platforms.get("x", True), key="x_toggle")
    rd_active = st.checkbox("Reddit", value=active_platforms.get("reddit", True), key="rd_toggle")
    
    # Guardar cambios si hay modificación
    new_active = {
        "youtube": yt_active,
        "instagram": ig_active,
        "x": x_active,
        "reddit": rd_active
    }
    if new_active != active_platforms:
        save_active(new_active)
        st.toast("Configuración de canales actualizada.", icon="💾")
        
    st.divider()
    st.markdown('<div class="section-title">Ajustes Rápidos</div>', unsafe_allow_html=True)
    new_user = st.text_input("Usuario de TikTok:", value=tiktok_user)
    if new_user != tiktok_user:
        # Guardar en .env
        with open(".env", "w", encoding="utf-8") as f:
            f.write(f"TIKTOK_USERNAME={new_user}\n")
        st.toast("Usuario de TikTok actualizado.", icon="👤")
        
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# 3. BARRA DE ESTADO (Fijada abajo)
processed = load_processed_ids()
last_post = processed[-1] if processed else "Ninguno"
st.markdown(f"""
    <div class="status-bar">
        <span class="status-dot"></span>
        Robot Activo &nbsp;|&nbsp; Cuenta: {tiktok_user} &nbsp;|&nbsp; Último procesado: ID {last_post} &nbsp;|&nbsp; Frecuencia: Cada 2 horas
    </div>
""", unsafe_allow_html=True)
