import os
import sys
import json
import time
import datetime
import importlib
import streamlit as st

# Streamlit Cloud deja los modulos ya importados en memoria cuando hace pull del
# codigo nuevo: sin este reload, app.py nuevo pide funciones que el modulo viejo
# todavia no tiene y la app arranca con ImportError.
import tiktok_crossposter
importlib.reload(tiktok_crossposter)

import ai_assistant
importlib.reload(ai_assistant)

from tiktok_crossposter import (
    run_crosspost_workflow,
    crosspost_single_video,
    crosspost_from_url,
    fetch_latest_tiktok_videos,
    load_processed_ids,
    remove_processed_id,
    load_pending_queue,
    save_pending_queue,
    add_to_pending_queue,
    remove_from_pending_queue,
    get_config,
    get_preview_play_url,
    fetch_videos_with_stats,
    check_all_credentials
)
from ai_assistant import (
    detect_ai_provider,
    save_ai_key_to_env,
    generate_video_script,
    generate_hooks,
    generate_weekly_plan,
    generate_monetization_plan,
    build_account_context,
    analyze_account_performance,
    normalize_creator_profile
)

st.set_page_config(
    page_title="TikTok Crossposter Command Center",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo Dark Command Center - CSS personalizado
st.markdown("""
    <style>
    .stApp {
        background-color: #050505 !important;
        color: #ffffff !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 10px 20px 80px 20px;
    }
    
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #8a2be2 0%, #ff007f 100%) !important;
        color: white !important;
        font-weight: 800 !important;
        border: none !important;
        padding: 14px 28px !important;
        border-radius: 50px !important;
        font-size: 18px !important;
        letter-spacing: 1.5px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(138, 43, 226, 0.4) !important;
        text-transform: uppercase;
    }
    .stButton>button:hover {
        opacity: 0.95 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 0, 127, 0.6) !important;
    }
    
    .preview-card {
        background-color: #0c0c0e;
        border: 1px solid #1a1a1e;
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    .controls-panel {
        background-color: #0c0c0e;
        border: 1px solid #1a1a1e;
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    .video-item-card {
        background-color: #121216;
        border: 1px solid #22222a;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
    }
    
    .section-title {
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #88889e;
        margin-bottom: 15px;
    }
    
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
    .badge-published {
        background-color: #1b4332;
        color: #52b788;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-pending {
        background-color: #3d2600;
        color: #ffb703;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Helper para cargar/guardar configuración de plataformas activas
def update_env_key(key: str, value: str):
    """Actualiza una sola clave del .env conservando el resto del archivo.

    Antes esto se hacia con open(".env", "w") + un unico write, lo que borraba
    TODAS las credenciales guardadas (tokens de YouTube, Meta, X y Reddit).
    """
    lineas = []
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            lineas = f.read().splitlines()

    reemplazado = False
    for i, linea in enumerate(lineas):
        if "=" in linea and not linea.strip().startswith("#"):
            if linea.split("=", 1)[0].strip() == key:
                lineas[i] = f"{key}={value}"
                reemplazado = True
                break
    if not reemplazado:
        lineas.append(f"{key}={value}")

    with open(".env", "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


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

CREATOR_PROFILE_FILE = "creator_profile.json"


def load_creator_profile() -> dict:
    """
    Perfil del creador: nicho, oferta, seguidores y cuantos videos puede grabar
    de verdad. Sin esto la IA aconseja a un creador promedio (cadencia de
    manual, ganchos genericos, monetizacion de cuenta grande).
    """
    if os.path.exists(CREATOR_PROFILE_FILE):
        try:
            with open(CREATOR_PROFILE_FILE, "r", encoding="utf-8") as f:
                return normalize_creator_profile(json.load(f))
        except Exception:
            pass
    return normalize_creator_profile(None)


def save_creator_profile(data: dict) -> dict:
    limpio = normalize_creator_profile(data)
    with open(CREATOR_PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(limpio, f, indent=2, ensure_ascii=False)
    return limpio


active_platforms = load_active()
tiktok_user = os.getenv("TIKTOK_USERNAME", "@b00kevin")

st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.title("🤖 TikTok Multi-Platform Command Center")

tab1, tab2, tab3 = st.tabs(["⚡ Panel Principal", "📅 Programador de Historial", "🧠 Asesor IA de Videos (Opcional)"])

# ==============================================================================
# TAB 1: PANEL PRINCIPAL
# ==============================================================================
with tab1:
    st.markdown('<div style="text-align: center; margin-bottom: 20px;">', unsafe_allow_html=True)
    if st.button("⚡ PUBLICAR ÚLTIMO VIDEO AHORA", key="btn_publish_now"):
        with st.spinner("Procesando último video de TikTok y publicando..."):
            config = get_config()
            config["FORCE_RUN"] = "1"
            res = run_crosspost_workflow(config)
            
            if res.get("status") in ["success", "partial_failure", "all_failed"]:
                results = res.get("results", {})
                details = res.get("details", {})
                
                if res.get("status") == "success":
                    st.balloons()
                    st.success(f"¡Publicado exitosamente! Video: {res.get('title')}")
                else:
                    st.warning(f"Procesado: {res.get('title')}")
                    
                for net, ok in results.items():
                    msg = details.get(net, "Sin detalles")
                    if ok:
                        st.markdown(f"✅ **{net.capitalize()}**: {msg}")
                    else:
                        st.markdown(f"❌ **{net.capitalize()}**: {msg}")
            elif res.get("status") == "skipped":
                st.warning("El último video ya fue publicado previamente.")
            else:
                st.error(f"Error: {res.get('message')}")
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("🔗 Publicar por Enlace Directo (Pega cualquier link de TikTok)", expanded=False):
        st.write("¿Tienes un enlace específico o no quieres esperar a que el escáner lo detecte? Pégalo aquí:")
        col_url1, col_url2 = st.columns([3, 1])
        with col_url1:
            direct_url_input = st.text_input(
                "Enlace del video:",
                placeholder="https://www.tiktok.com/@b00kevin/video/...",
                key="input_direct_url_app",
                label_visibility="collapsed"
            )
        with col_url2:
            btn_publish_direct = st.button("🚀 Publicar Link", key="btn_publish_direct_link")

        if btn_publish_direct:
            if direct_url_input.strip():
                with st.spinner("Descargando video sin marca de agua y publicando a los canales activos..."):
                    res_dir = crosspost_from_url(direct_url_input.strip())
                    if res_dir.get("status") in ["success", "partial_failure", "all_failed"]:
                        results_dir = res_dir.get("results", {})
                        details_dir = res_dir.get("details", {})
                        if res_dir.get("status") == "success":
                            st.balloons()
                            st.success(f"¡Publicado exitosamente! {res_dir.get('title', '')}")
                        else:
                            st.warning(f"Finalizado con detalles: {res_dir.get('title', '')}")
                        for net_d, ok_d in results_dir.items():
                            msg_d = details_dir.get(net_d, "Sin detalles")
                            if ok_d:
                                st.markdown(f"✅ **{net_d.capitalize()}**: {msg_d}")
                            else:
                                st.markdown(f"❌ **{net_d.capitalize()}**: {msg_d}")
                    else:
                        st.error(f"Error: {res_dir.get('message')}")
            else:
                st.warning("Por favor pega un enlace de TikTok válido.")

    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Último Video de TikTok</div>', unsafe_allow_html=True)
        with st.spinner("Buscando último video..."):
            videos = fetch_latest_tiktok_videos(tiktok_user, count=1)
            if videos:
                latest = videos[0]
                st.markdown(f"### {latest['title'] or 'Video sin título'}")
                st.caption(f"TikTok ID: `{latest['id']}` | Fecha: {latest.get('upload_date', 'N/A')}")
                
                # Obtener preview directo de video MP4 sin marca de agua
                play_url = get_preview_play_url(latest['webpage_url'])
                if play_url:
                    st.video(play_url)
                elif latest.get('thumbnail'):
                    st.image(latest['thumbnail'], use_container_width=True)
                
                st.markdown(f"🔗 [Abrir video en TikTok]({latest['webpage_url']})")
                if st.button("💡 Usar este video para crear nuevos guiones con IA", key="btn_ai_seed_latest"):
                    st.session_state["ai_selected_video"] = latest
                    st.session_state["ai_source_type"] = "Último video de TikTok"
                    st.toast("¡Video enviado al Asesor IA! Ve a la pestaña '🧠 Asesor IA de Videos' > '🎣 Ganchos & Guiones'.", icon="💡")
            else:
                st.warning(f"No se detectaron videos para @{tiktok_user}.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="controls-panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Canales de Publicación</div>', unsafe_allow_html=True)
        st.write("Selecciona las redes sociales donde publicar automáticamente:")
        
        yt_active = st.checkbox("YouTube Shorts", value=active_platforms.get("youtube", True), key="t1_yt")
        ig_active = st.checkbox("Instagram Reels", value=active_platforms.get("instagram", True), key="t1_ig")
        x_active = st.checkbox("X (Twitter)", value=active_platforms.get("x", True), key="t1_x")
        rd_active = st.checkbox("Reddit", value=active_platforms.get("reddit", True), key="t1_rd")
        
        new_active = {"youtube": yt_active, "instagram": ig_active, "x": x_active, "reddit": rd_active}
        if new_active != active_platforms:
            save_active(new_active)
            st.toast("Canales actualizados.", icon="💾")
            
        st.divider()
        st.markdown('<div class="section-title">🔑 Estado de Credenciales / Tokens</div>', unsafe_allow_html=True)
        
        cfg = get_config()
        clean_user = cfg.get('TIKTOK_USERNAME', tiktok_user).strip().lstrip('@')
        st.markdown(f"**TikTok:** `@{clean_user}`")
        st.markdown(f"**Instagram:** {'✅ Token detectado' if cfg.get('INSTAGRAM_ACCESS_TOKEN') else '❌ Falta INSTAGRAM_ACCESS_TOKEN'}")
        st.markdown(f"**YouTube:** {'✅ Token detectado' if cfg.get('YOUTUBE_REFRESH_TOKEN') else '❌ Falta YOUTUBE_REFRESH_TOKEN'}")
        st.markdown(f"**X (Twitter):** {'✅ Tokens detectados' if (cfg.get('X_ACCESS_TOKEN') and cfg.get('X_ACCESS_TOKEN_SECRET')) else '❌ Falta X_ACCESS_TOKEN o Secret'}")
        st.markdown(f"**Reddit:** {'✅ Credenciales detectadas' if cfg.get('REDDIT_CLIENT_ID') else '❌ Faltan credenciales Reddit'}")

        st.caption("Tener la llave guardada no significa que siga siendo valida. Compruebalo en vivo:")
        if st.button("🔬 Probar credenciales ahora", key="t1_check_creds", use_container_width=True):
            with st.spinner("Consultando cada API (no publica nada)..."):
                st.session_state["cred_check"] = check_all_credentials(cfg)

        if st.session_state.get("cred_check"):
            NOMBRES_RED = {"youtube": "YouTube", "instagram": "Instagram", "x": "X (Twitter)", "reddit": "Reddit"}
            for red, (ok, detalle) in st.session_state["cred_check"].items():
                if ok:
                    st.success(f"**{NOMBRES_RED[red]}:** {detalle}")
                else:
                    st.error(f"**{NOMBRES_RED[red]}:** {detalle}")
            if not st.session_state["cred_check"].get("youtube", (True, ""))[0]:
                st.info("Para regenerar el token de YouTube, ejecuta en la terminal: "
                        "`python generate_youtube_token.py`")
        
        st.divider()
        st.markdown('<div class="section-title">Ajustes Rápidos</div>', unsafe_allow_html=True)
        new_user = st.text_input("Usuario de TikTok:", value=tiktok_user, key="t1_user")
        if new_user != tiktok_user:
            update_env_key("TIKTOK_USERNAME", new_user)
            st.toast("Usuario de TikTok actualizado.", icon="👤")
        st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# TAB 2: PROGRAMADOR DE HISTORIAL
# ==============================================================================
with tab2:
    st.markdown('<div class="controls-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📅 Seleccionar y Programar Videos Antiguos</div>', unsafe_allow_html=True)
    st.write("Inspecciona los videos de tu perfil, selecciona cuáles quieres publicar y prográmalos con pausas o guárdalos en cola.")
    
    col_c1, col_c2, col_c3 = st.columns([1, 1, 1])
    with col_c1:
        fetch_count = st.number_input("Cantidad de videos a recuperar:", min_value=5, max_value=50, value=20, step=5)
    with col_c2:
        filter_status = st.selectbox("Filtrar por estado:", ["Todos", "Solo pendientes", "Solo ya publicados"])
    with col_c3:
        search_query = st.text_input("🔍 Buscar título / ID:", "")
        
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        enable_date_filter = st.checkbox("Filtrar por rango de fechas")
    with col_f2:
        if enable_date_filter:
            date_range = st.date_input("Rango de fechas (Desde - Hasta):", [datetime.date.today() - datetime.timedelta(days=30), datetime.date.today()])
        else:
            date_range = None

    # Carga automática inicial si aún no se han consultado los videos
    if "history_videos" not in st.session_state:
        with st.spinner(f"Obteniendo los últimos {fetch_count} videos de TikTok @{tiktok_user}..."):
            st.session_state["history_videos"] = fetch_latest_tiktok_videos(tiktok_user, count=fetch_count)

    if st.button("🔄 Cargar / Actualizar Lista de Videos", key="btn_load_history"):
        with st.spinner(f"Obteniendo los últimos {fetch_count} videos de TikTok @{tiktok_user}..."):
            st.session_state["history_videos"] = fetch_latest_tiktok_videos(tiktok_user, count=fetch_count)
            st.toast(f"Cargados {len(st.session_state.get('history_videos', []))} videos.", icon="✅")

    videos_list = st.session_state.get("history_videos", [])
    processed_ids = set(load_processed_ids())

    if not videos_list:
        st.info("Haz clic en **'Cargar / Actualizar Lista de Videos'** para obtener tus publicaciones de TikTok.")
    else:
        # Filtrado de videos
        filtered_videos = []
        for v in videos_list:
            is_proc = v["id"] in processed_ids
            
            # Filtro de estado
            if filter_status == "Solo pendientes" and is_proc:
                continue
            if filter_status == "Solo ya publicados" and not is_proc:
                continue
                
            # Filtro de búsqueda
            if search_query:
                q = search_query.lower()
                if q not in v["title"].lower() and q not in v["id"]:
                    continue
                    
            # Filtro de fecha
            if enable_date_filter and date_range and len(date_range) == 2 and v.get("timestamp"):
                v_date = datetime.date.fromtimestamp(v["timestamp"])
                if not (date_range[0] <= v_date <= date_range[1]):
                    continue
                    
            filtered_videos.append(v)

        st.subheader(f"Videos Encontrados ({len(filtered_videos)})")
        
        # Botones de selección rápida
        col_s1, col_s2 = st.columns([1, 1])
        with col_s1:
            if st.button("☑️ Seleccionar Todos los Pendientes", key="btn_select_pending"):
                for v in filtered_videos:
                    if v["id"] not in processed_ids:
                        st.session_state[f"select_{v['id']}"] = True
        with col_s2:
            if st.button("🔲 Desmarcar Todos", key="btn_unselect_all"):
                for v in filtered_videos:
                    st.session_state[f"select_{v['id']}"] = False

        st.divider()

        # Lista / Tabla interactiva de videos
        selected_videos = []
        for v in filtered_videos:
            is_proc = v["id"] in processed_ids
            c_check, c_thumb, c_info, c_status = st.columns([0.4, 1.2, 3.5, 1.5])
            
            with c_check:
                is_selected = st.checkbox("Seleccionar", value=st.session_state.get(f"select_{v['id']}", False), key=f"select_{v['id']}", label_visibility="collapsed")
                if is_selected:
                    selected_videos.append(v)
                    
            with c_thumb:
                if v.get("thumbnail"):
                    st.image(v["thumbnail"], use_container_width=True)
                else:
                    st.markdown("🎥 Video")
                    
            with c_info:
                st.markdown(f"**{v['title'] or 'Sin título'}**")
                st.caption(f"ID: `{v['id']}` | Fecha TikTok: {v.get('upload_date', 'N/A')}")
                st.markdown(f"[Ver en TikTok]({v['webpage_url']})")
                if st.button("💡 Crear Guion IA", key=f"ai_seed_{v['id']}"):
                    st.session_state["ai_selected_video"] = v
                    st.session_state["ai_source_type"] = f"Video: {v.get('title', v['id'])[:30]}"
                    st.toast(f"¡Video {v['id']} cargado en el Asesor IA (Ganchos & Guiones)!", icon="💡")
                
            with c_status:
                if is_proc:
                    st.markdown('<span class="badge-published">✅ Ya Publicado</span>', unsafe_allow_html=True)
                    if st.button("🔓 Desmarcar", key=f"unproc_{v['id']}"):
                        remove_processed_id(v['id'])
                        st.toast(f"Video {v['id']} desmarcado.", icon="🔓")
                        st.rerun()
                else:
                    st.markdown('<span class="badge-pending">⏳ Pendiente</span>', unsafe_allow_html=True)
            st.divider()

        # PANEL DE ACCIONES SOBRE SELECCIÓN
        st.markdown(f"### ⚙️ Acciones sobre la Selección ({len(selected_videos)} videos seleccionados)")
        
        col_act1, col_act2 = st.columns(2)
        
        with col_act1:
            st.markdown("#### ⚡ Opción A: Publicar Lote Ahora (con pausas)")
            delay_minutes = st.selectbox(
                "Pausa entre publicaciones:",
                options=[0, 1, 2, 5, 10, 15, 30, 60],
                format_func=lambda x: "Sin pausa (inmediato)" if x == 0 else f"{x} minuto(s)"
            )
            
            if st.button("🚀 INICIAR PUBLICACIÓN POR LOTES", key="btn_run_batch"):
                if not selected_videos:
                    st.warning("Selecciona al menos un video para publicar.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    total = len(selected_videos)
                    
                    for idx, vid in enumerate(selected_videos):
                        status_text.markdown(f"⏳ **[{idx+1}/{total}] Publicando:** {vid['title'][:50]}...")
                        config = dict(os.environ)
                        res = crosspost_single_video(vid, config)
                        
                        if res.get("status") in ["success", "partial_failure"]:
                            st.success(f"✅ Video {vid['id']} publicado.")
                        else:
                            st.error(f"❌ Falló video {vid['id']}: {res.get('message')}")
                            
                        progress_bar.progress((idx + 1) / total)
                        
                        if delay_minutes > 0 and idx < total - 1:
                            status_text.info(f"⏸️ Pausa programada: esperando {delay_minutes} minuto(s) antes del siguiente video...")
                            time.sleep(delay_minutes * 60)
                            
                    status_text.success("🎉 ¡Lote finalizado con éxito!")
                    st.balloons()

        with col_act2:
            st.markdown("#### 📅 Opción B: Añadir a la Cola Automática")
            st.write("Los videos se guardarán en `pending_queue.json` y GitHub Actions / Bot publicará 1 video cada 2 horas.")
            
            if st.button("📥 GUARDAR SELECCIÓN EN LA COLA", key="btn_add_queue"):
                if not selected_videos:
                    st.warning("Selecciona al menos un video para añadir a la cola.")
                else:
                    added = add_to_pending_queue(selected_videos)
                    st.success(f"¡Se añadieron {added} videos a la cola pendiente!")
                    st.toast(f"{added} videos encolados.", icon="📥")

        # GESTIÓN DE LA COLA ACTUAL
        st.divider()
        st.markdown("### 📋 Cola Pendiente Actual (`pending_queue.json`)")
        queue_items = load_pending_queue()
        
        if not queue_items:
            st.info("La cola está vacía en este momento.")
        else:
            st.write(f"Hay **{len(queue_items)}** videos programados en cola para publicarse progresivamente:")
            for idx, qv in enumerate(queue_items):
                col_q1, col_q2 = st.columns([4, 1])
                with col_q1:
                    st.markdown(f"**#{idx+1}** - {qv.get('title', 'Sin título')} (`ID: {qv.get('id')}`)")
                with col_q2:
                    if st.button("❌ Quitar", key=f"remove_q_{qv.get('id')}"):
                        remove_from_pending_queue(qv.get('id'))
                        st.rerun()
                        
            if st.button("🗑️ Vaciar Cola Pendiente", key="btn_clear_queue"):
                save_pending_queue([])
                st.toast("Cola vaciada.", icon="🗑️")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# TAB 3: ASESOR IA (ANALISIS DE RENDIMIENTO + GUIONES)
# ==============================================================================
with tab3:
    st.markdown('<div class="controls-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🧠 Asesor IA de Videos Virales</div>', unsafe_allow_html=True)
    st.write("Analiza el rendimiento **real** de tus últimos TikToks (vistas, likes, comentarios y compartidos), te dice con datos qué está funcionando y convierte ese diagnóstico en guiones de alta retención.")

    ai_provider, ai_key = detect_ai_provider()

    if not ai_provider:
        st.info("ℹ️ **Esta función es 100% opcional.** Si quieres usarla, solo necesitas una API Key de IA gratuita.")

        with st.expander("🔑 Configuración Rápida en 30 segundos (Recomendado: Google Gemini GRATIS)", expanded=True):
            st.markdown("""
            **¿Cómo obtener tu clave de Google Gemini sin pagar nada y sin tarjeta de crédito?**
            1. Entra a **[Google AI Studio (aistudio.google.com)](https://aistudio.google.com/)** con tu cuenta de Gmail.
            2. Haz clic en **'Get API key'** y luego en **'Create API key'**.
            3. Cópiala y pégala aquí abajo:
            """)

            c_key1, c_key2 = st.columns([3, 1])
            with c_key1:
                gemini_input = st.text_input("Ingresa tu GEMINI_API_KEY:", type="password", placeholder="AIzaSy...")
            with c_key2:
                st.write("")
                st.write("")
                if st.button("💾 Guardar Clave", key="btn_save_gemini_key"):
                    if gemini_input.strip():
                        if save_ai_key_to_env("GEMINI_API_KEY", gemini_input.strip()):
                            st.success("¡Clave Gemini guardada con éxito en .env!")
                            st.rerun()
                    else:
                        st.warning("Por favor escribe o pega una clave válida.")

            st.caption("Nota: También puedes usar `GROQ_API_KEY` u `OPENAI_API_KEY` en tu archivo `.env` si prefieres Llama 3 o ChatGPT.")
    else:
        # Proveedor detectado
        st.success(f"🟢 **Asistente de IA Activo:** Proveedor detectado (`{ai_provider.upper()}`). Listo para analizar y generar.")

        # ======================================================================
        # 3.0 - PERFIL: SIN ESTO LA IA ACONSEJA A UN CREADOR PROMEDIO
        # ======================================================================
        perfil = st.session_state.get("creator_profile") or load_creator_profile()
        st.session_state["creator_profile"] = perfil

        perfil_completo = bool(perfil.get("nicho") and perfil.get("oferta"))
        etiqueta_perfil = (
            "🧬 Tu marca personal y tu capacidad real de producción"
            if perfil_completo else
            "🧬 ⚠️ Configura tu perfil primero (sin esto los consejos salen genéricos)"
        )

        with st.expander(etiqueta_perfil, expanded=not perfil_completo):
            st.caption(
                "Esto es lo que hace que el asesor te hable **a ti** y no a un creador promedio: "
                "con tus seguidores reales no te va a proponer tácticas de cuenta grande, y con los videos "
                "por semana que declares aquí el plan se reparte en **esos** slots (nunca más \"publica 1 diario\")."
            )

            with st.form("form_creator_profile"):
                col_p1, col_p2 = st.columns([3, 2])

                with col_p1:
                    f_nicho = st.text_input(
                        "¿De qué hablas? (tu nicho, concreto)",
                        value=perfil.get("nicho", ""),
                        placeholder="Ej: programación y vibecoding: construyo apps con IA y muestro el proceso"
                    )
                    f_publico = st.text_input(
                        "¿A quién le hablas?",
                        value=perfil.get("publico", ""),
                        placeholder="Ej: devs junior y gente no técnica que quiere construir su primera app con IA"
                    )
                    f_modelo = st.radio(
                        "¿De dónde quieres que salga el dinero?",
                        options=["apps_propias", "mixto", "servicios"],
                        index=["apps_propias", "mixto", "servicios"].index(
                            perfil.get("modelo_negocio", "apps_propias")
                        ),
                        horizontal=True,
                        format_func=lambda m: {
                            "apps_propias": "📱 De mis apps (las redes son el canal)",
                            "mixto": "🔀 Apps, con servicios como caja puente",
                            "servicios": "🛠️ Servicios / trabajo a medida"
                        }[m],
                        help="Si eliges tus apps, el asesor tiene prohibido proponerte vender servicios, "
                             "cursos o mentorías: todo se mide en usuarios del producto, no en clientes."
                    )
                    f_oferta = st.text_input(
                        "¿Qué producto tienes y qué resuelve?",
                        value=perfil.get("oferta", ""),
                        placeholder="Ej: una app que automatiza la facturación de negocios pequeños"
                    )
                    f_tools = st.text_input(
                        "Herramientas / stack que puedes mostrar en pantalla (opcional)",
                        value=perfil.get("herramientas", ""),
                        placeholder="Ej: Claude Code, Cursor, Python, n8n, Supabase"
                    )

                with col_p2:
                    f_followers = st.number_input(
                        "Seguidores que tienes hoy",
                        min_value=0, step=10,
                        value=int(perfil.get("followers", 0)),
                        help="Define qué tácticas aplican. Con menos de 1.000 las vistas vienen del 'Para ti', "
                             "no de tus seguidores: el asesor dejará de proponerte lives, colaboraciones o marcas."
                    )
                    f_por_semana = st.slider(
                        "Videos que puedes publicar por semana",
                        min_value=1, max_value=70,
                        value=int(perfil.get("videos_por_semana", 7)),
                        help="Sé honesto con lo que puedes sostener: todo el plan se reparte exactamente en "
                             "este número de slots. A partir de 15 el plan deja de darte un video por fila y "
                             "pasa a darte formatos repetibles con su banco de variaciones, que es como se "
                             "sostiene el volumen de verdad."
                    )
                    st.caption(f"≈ **{round(f_por_semana / 7, 1)} videos al día**."
                               + (" Modo alto volumen: el plan vendrá por formatos, no video por video."
                                  if f_por_semana > 15 else ""))
                    f_modo = st.radio(
                        "Modo de trabajo",
                        options=["volumen", "sostenible", "quirurgico"],
                        index=["volumen", "sostenible", "quirurgico"].index(perfil.get("modo", "sostenible")),
                        format_func=lambda m: {
                            "volumen": "🔁 Volumen / aprendizaje rápido",
                            "sostenible": "⚖️ Sostenible",
                            "quirurgico": "🎯 Quirúrgico (pocos y muy trabajados)"
                        }[m],
                        help="Volumen: muchos intentos, edición mínima, la mayoría va a fracasar y da igual; "
                             "lo que importa es cuántos superan tu mediana. Quirúrgico: pocos videos sobre "
                             "temas ya validados por tus datos."
                    )

                if st.form_submit_button("💾 Guardar perfil"):
                    perfil = save_creator_profile({
                        "nicho": f_nicho,
                        "publico": f_publico,
                        "oferta": f_oferta,
                        "herramientas": f_tools,
                        "followers": f_followers,
                        "videos_por_semana": f_por_semana,
                        "modo": f_modo,
                        "modelo_negocio": f_modelo
                    })
                    st.session_state["creator_profile"] = perfil
                    st.success("Perfil guardado. Todo lo que genere el asesor queda calibrado a esto.")
                    st.rerun()

            if perfil_completo:
                st.caption(
                    f"Ahora mismo: **{perfil['followers']} seguidores**, "
                    f"**{perfil['videos_por_semana']} videos/semana** en modo **{perfil['modo']}**."
                )

        if not perfil_completo:
            st.warning(
                "⚠️ Sin nicho ni oferta declarados, la IA no sabe a quién le hablas: los ganchos van a servir "
                "para cualquier tema y la monetización va a sonar a cuenta grande. Llena el perfil de arriba."
            )

        tab_analisis, tab_semana, tab_dinero, tab_guion = st.tabs([
            "🔎 Análisis de Rendimiento (Asesor Viral)",
            "📅 Estructura de la semana",
            "🚀 De las redes a mis apps",
            "🎣 Ganchos & Guiones"
        ])

        # ======================================================================
        # 3.A - ASESOR VIRAL: DIAGNOSTICO CON METRICAS REALES
        # ======================================================================
        with tab_analisis:
            st.markdown("#### 1. ¿Qué analizamos?")
            col_an1, col_an2 = st.columns([1, 1])

            with col_an1:
                n_videos = st.slider(
                    "Cantidad de videos recientes a analizar:",
                    min_value=3, max_value=15, value=8,
                    help="Mientras más videos, más confiable el patrón. Con menos de 5 el asesor te lo advertirá."
                )
                goal_opt = st.selectbox(
                    "¿Cuál es tu objetivo ahora mismo?",
                    [
                        ("mas_vistas", "👀 Más vistas / alcance nuevo"),
                        ("mas_interaccion", "💬 Más comentarios y compartidos"),
                        ("mas_seguidores", "➕ Convertir espectadores en seguidores"),
                        ("vender", "📱 Llevar usuarios a mi producto")
                    ],
                    format_func=lambda x: x[1],
                    key="goal_opt_analisis"
                )[0]

            with col_an2:
                extra_ctx = st.text_area(
                    "Contexto de tu cuenta (opcional, mejora mucho el análisis):",
                    placeholder="Ej: hablo de automatización con IA, mi público son emprendedores y vendo bots de WhatsApp...",
                    height=150
                )

            st.caption("Las métricas se leen directo de TikTok. Si TikTok bloquea la consulta (pasa por rachas desde la nube), espera unos minutos y reintenta.")

            if st.button("🔎 ANALIZAR MIS VIDEOS Y DARME EL DIAGNÓSTICO", key="btn_run_ai_analysis"):
                barra = st.progress(0.0, text="Leyendo métricas de TikTok...")

                def _avance(i, total, titulo):
                    barra.progress(
                        min(i / max(total, 1), 1.0),
                        text=f"Leyendo métricas {i}/{total}: {titulo[:45]}"
                    )

                datos = fetch_videos_with_stats(tiktok_user, count=n_videos, on_progress=_avance)
                barra.empty()

                videos_stats = datos.get("videos", [])
                fallidos = datos.get("failed", [])

                if not videos_stats:
                    st.error("No se pudieron leer las métricas de ningún video. TikTok bloquea las consultas por rachas: espera unos minutos y vuelve a intentarlo.")
                else:
                    with st.spinner("Cruzando tus números y armando el diagnóstico..."):
                        res_an = analyze_account_performance(
                            videos_stats,
                            account=tiktok_user,
                            extra_context=extra_ctx,
                            goal=goal_opt,
                            profile=perfil
                        )

                    st.session_state["ai_analysis_metrics"] = res_an.get("metrics")
                    if res_an.get("success"):
                        st.session_state["ai_analysis_result"] = res_an.get("content")
                        st.toast("¡Diagnóstico listo!", icon="📊")
                    else:
                        st.session_state.pop("ai_analysis_result", None)
                        st.error(f"Se leyeron las métricas, pero la IA falló: {res_an.get('message')}")

                if fallidos:
                    nombres = ", ".join((f.get("title") or f.get("id", "?"))[:35] for f in fallidos[:5])
                    st.warning(f"⚠️ Sin métricas para {len(fallidos)} video(s): {nombres}")

            metrics_state = st.session_state.get("ai_analysis_metrics")
            if metrics_state and metrics_state.get("videos"):
                resumen = metrics_state.get("resumen", {})
                st.divider()
                st.markdown("#### 📊 Tus números reales")

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Videos analizados", resumen.get("n", 0))
                m2.metric("Vistas promedio", f"{resumen.get('views_promedio', 0):,}".replace(",", "."))
                m3.metric("Engagement promedio", f"{resumen.get('engagement_promedio', 0)}%")
                m4.metric("Mejor video", f"{resumen.get('views_max', 0):,}".replace(",", ".") + " vistas")

                st.dataframe(
                    [
                        {
                            "Video": (f["title"] or "(sin título)")[:60],
                            "Dur.": f"{f['duration']}s",
                            "Publicado": f["fecha"],
                            "Vistas": f["views"],
                            "Likes": f["likes"],
                            "Coment.": f["comments"],
                            "Comp.": f["shares"],
                            "Engagement": f"{f['engagement']}%"
                        }
                        for f in metrics_state["videos"]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

                mejores = metrics_state.get("mejores") or []
                if mejores:
                    mejor = mejores[0]
                    if st.button(
                        f"💡 Crear un guion nuevo basado en mi mejor video ({mejor.get('views', 0)} vistas)",
                        key="btn_ai_seed_best"
                    ):
                        st.session_state["ai_selected_video"] = {
                            "id": mejor.get("id", ""),
                            "title": mejor.get("title", ""),
                            "webpage_url": mejor.get("webpage_url", "")
                        }
                        st.session_state["ai_source_type"] = "Mejor video por vistas"
                        st.toast("Video cargado en '🎣 Ganchos & Guiones'.", icon="💡")

            if st.session_state.get("ai_analysis_result"):
                st.divider()
                st.markdown("#### 🧠 Diagnóstico y plan de acción")
                st.markdown(st.session_state["ai_analysis_result"])

                st.download_button(
                    label="📥 Descargar diagnóstico (.md)",
                    data=st.session_state["ai_analysis_result"],
                    file_name="analisis_viral_tiktok.md",
                    mime="text/markdown",
                    key="btn_dl_analysis"
                )


        # ======================================================================
        # 3.C - ESTRUCTURA DE LA SEMANA: UN SLOT POR VIDEO, YA DECIDIDO
        # ======================================================================
        with tab_semana:
            st.markdown("#### Tu semana cerrada, no una lista de ideas")
            _alto_volumen = perfil["videos_por_semana"] > 15
            st.caption(
                f"Reparte **{perfil['videos_por_semana']} videos** (los que declaraste poder sostener) en los "
                "7 días. "
                + ("A tu volumen el plan no viene video por video: viene como **formatos repetibles** con su "
                   "banco de variaciones concretas y el plan de grabación en lote, que es como se sostiene. "
                   if _alto_volumen else
                   "Cada slot trae tema, gancho del segundo 0, duración y **qué variable prueba**. ")
                + "Si ya corriste el análisis, se apoya en lo que tus números dicen que funciona."
            )

            metrics_semana = st.session_state.get("ai_analysis_metrics")
            if metrics_semana and metrics_semana.get("videos"):
                st.success("✅ Calibrado con tus métricas reales del análisis.")
            else:
                st.info("ℹ️ Todavía sin métricas: corre primero el análisis y la semana saldrá apoyada en datos "
                        "en vez de hipótesis.")

            col_s1, col_s2 = st.columns([1, 2])
            with col_s1:
                goal_semana = st.selectbox(
                    "Objetivo de esta semana:",
                    [
                        ("mas_vistas", "👀 Más vistas / alcance nuevo"),
                        ("mas_interaccion", "💬 Más comentarios y compartidos"),
                        ("mas_seguidores", "➕ Convertir espectadores en seguidores"),
                        ("vender", "📱 Llevar usuarios a mi producto")
                    ],
                    format_func=lambda x: x[1],
                    key="goal_opt_semana"
                )[0]
            with col_s2:
                ctx_semana = st.text_input(
                    "¿Algo puntual de esta semana? (opcional)",
                    placeholder="Ej: acabo de terminar una app de facturación y quiero mostrarla",
                    key="ctx_semana"
                )

            if st.button("📅 ARMARME LA SEMANA", key="btn_run_weekly"):
                with st.spinner("Repartiendo tus slots y decidiendo qué prueba cada video..."):
                    res_w = generate_weekly_plan(
                        metrics=metrics_semana,
                        profile=perfil,
                        extra_context=ctx_semana,
                        goal=goal_semana
                    )
                if res_w.get("success"):
                    st.session_state["ai_weekly_result"] = res_w.get("content")
                    st.toast("¡Semana lista!", icon="📅")
                else:
                    st.error(res_w.get("message"))

            if st.session_state.get("ai_weekly_result"):
                st.divider()
                st.markdown(st.session_state["ai_weekly_result"])
                st.download_button(
                    "📥 Descargar la semana (.md)",
                    data=st.session_state["ai_weekly_result"],
                    file_name="plan_semanal.md",
                    mime="text/markdown",
                    key="btn_dl_weekly"
                )

        # ======================================================================
        # 3.D - CUANTA GENTE HACE FALTA PARA VIVIR DEL PRODUCTO
        # ======================================================================
        with tab_dinero:
            st.markdown("#### Cuánta gente necesitas para vivir de tus apps")
            st.caption(
                "El producto es el negocio y las redes son el canal. Esto hace la cuenta **al revés**: "
                "del ingreso que quieres → usuarios que pagan → registros → vistas al mes → **videos al mes "
                "a tu promedio real**. Y te responde con cifras si de verdad tienes que hacerte grande "
                "primero, o si con el alcance que ya tienes alcanza para arrancar."
            )

            metrics_dinero = st.session_state.get("ai_analysis_metrics")
            if not (metrics_dinero and metrics_dinero.get("videos")):
                st.info("ℹ️ Corre el análisis primero: sin tus vistas reales la cuenta sale con supuestos.")

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                precio_app = st.text_input(
                    "¿Cuánto cobras (o cobrarías) por tu app?",
                    placeholder="Ej: 5 USD al mes por usuario / pago único de 20 USD",
                    key="precio_app",
                    help="Es el dato que permite hacer la cuenta. Si lo dejas vacío, la IA asume un precio y "
                         "lo marca como supuesto."
                )
            with col_d2:
                meta_mes = st.text_input(
                    "¿Cuánto quieres ganar al mes con tus apps?",
                    placeholder="Ej: 2.000 USD al mes",
                    key="meta_mes",
                    help="La meta desde la que se cuenta hacia atrás."
                )

            ctx_dinero = st.text_area(
                "¿Qué apps tienes ya, y qué no quieres hacer? (opcional)",
                placeholder="Ej: tengo 2 apps publicadas y una que automatiza facturación; no quiero vender "
                            "cursos ni trabajar para clientes; puedo dedicarle 10 horas por semana",
                height=100,
                key="ctx_dinero"
            )

            if st.button("🚀 HAZME LA CUENTA", key="btn_run_money"):
                if not perfil.get("oferta"):
                    st.warning("Llena primero '¿Qué producto tienes y qué resuelve?' en tu perfil: sin eso "
                               "la cuenta sale a ciegas.")
                with st.spinner("Contando hacia atrás desde tu meta..."):
                    res_m = generate_monetization_plan(
                        metrics=metrics_dinero,
                        profile=perfil,
                        extra_context=ctx_dinero,
                        precio=precio_app,
                        meta_mensual=meta_mes
                    )
                if res_m.get("success"):
                    st.session_state["ai_money_result"] = res_m.get("content")
                    st.toast("¡Cuenta lista!", icon="🚀")
                else:
                    st.error(res_m.get("message"))

            if st.session_state.get("ai_money_result"):
                st.divider()
                st.markdown(st.session_state["ai_money_result"])
                st.download_button(
                    "📥 Descargar la cuenta (.md)",
                    data=st.session_state["ai_money_result"],
                    file_name="camino_a_mis_apps.md",
                    mime="text/markdown",
                    key="btn_dl_money"
                )

        # ======================================================================
        # 3.B - GENERADOR DE GUIONES CON MICROGANCHOS
        # ======================================================================
        with tab_guion:
            # El analisis, si ya se corrio, calibra lo que la IA propone.
            account_context = build_account_context(st.session_state.get("ai_analysis_metrics"))

            preloaded_video = st.session_state.get("ai_selected_video")
            if preloaded_video and st.session_state.get("hooks_seed_id") != preloaded_video.get("id"):
                st.session_state["hooks_tema"] = preloaded_video.get("title", "")
                st.session_state["hooks_seed_id"] = preloaded_video.get("id")

            st.text_input(
                "¿De qué va el video?",
                key="hooks_tema",
                placeholder="Ej: el bot le contestó a un cliente a las 2 de la madrugada"
            )
            tema = st.session_state.get("hooks_tema", "")

            if account_context:
                st.caption("✅ Calibrado con los números de tu último análisis.")
            else:
                st.caption("💡 Corre primero el análisis y los ganchos saldrán calibrados a tus números.")

            if st.button("🎣 DAME 10 GANCHOS PARA LOS PRIMEROS 3 SEGUNDOS", key="btn_run_hooks"):
                if not tema.strip():
                    st.warning("Escribe de qué va el video.")
                else:
                    with st.spinner("Escribiendo aperturas..."):
                        res_h = generate_hooks(
                            {
                                "title": tema.strip(),
                                "url": preloaded_video.get("webpage_url", "") if preloaded_video else ""
                            },
                            n=10,
                            account_context=account_context,
                            profile=perfil
                        )
                    if res_h.get("success"):
                        st.session_state["ai_hooks_result"] = res_h.get("content")
                    else:
                        st.error(res_h.get("message"))

            if st.session_state.get("ai_hooks_result"):
                st.divider()
                st.markdown(st.session_state["ai_hooks_result"])
                st.download_button(
                    "📥 Descargar ganchos (.md)",
                    data=st.session_state["ai_hooks_result"],
                    file_name="ganchos.md",
                    mime="text/markdown",
                    key="btn_dl_hooks"
                )

            with st.expander("¿Necesitas el guion completo? (tabla de tiempos, visuales y CTA)"):
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    style_opt = st.selectbox(
                        "Ángulo:",
                        [
                            ("disruptive", "🔥 Polémico / Rompe mitos"),
                            ("quick_tutorial", "⚡ Tutorial express"),
                            ("storytelling", "📖 Historia / conflicto"),
                            ("top3_errors", "⚠️ Top 3 errores")
                        ],
                        format_func=lambda x: x[1]
                    )[0]
                with col_g2:
                    duration_opt = st.select_slider(
                        "Duración:",
                        options=[15, 30, 45, 60],
                        value=30,
                        format_func=lambda x: f"{x}s"
                    )

                if st.button("⚡ Generar guion completo", key="btn_run_ai_gen"):
                    if not tema.strip():
                        st.warning("Escribe de qué va el video.")
                    else:
                        with st.spinner("Escribiendo el guion..."):
                            result = generate_video_script(
                                {
                                    "title": tema.strip(),
                                    "url": preloaded_video.get("webpage_url", "") if preloaded_video else ""
                                },
                                style=style_opt,
                                target_duration=duration_opt,
                                account_context=account_context,
                                profile=perfil
                            )
                        if result.get("success"):
                            st.session_state["ai_generated_result"] = result.get("content")
                        else:
                            st.error(result.get("message"))

                if st.session_state.get("ai_generated_result"):
                    st.markdown(st.session_state["ai_generated_result"])
                    st.download_button(
                        "📥 Descargar guion (.md)",
                        data=st.session_state["ai_generated_result"],
                        file_name="guion.md",
                        mime="text/markdown",
                        key="btn_dl_guion"
                    )

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# BARRA DE ESTADO INFERIOR
processed = load_processed_ids()
last_post = processed[-1] if processed else "Ninguno"
st.markdown(f"""
    <div class="status-bar">
        <span class="status-dot"></span>
        Robot Activo &nbsp;|&nbsp; Cuenta: {tiktok_user} &nbsp;|&nbsp; Último procesado: ID {last_post} &nbsp;|&nbsp; Frecuencia: Cada 2 horas
    </div>
""", unsafe_allow_html=True)
