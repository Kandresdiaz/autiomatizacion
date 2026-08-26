import os
import json
import time
import datetime
import streamlit as st
from tiktok_crossposter import (
    run_crosspost_workflow,
    crosspost_single_video,
    fetch_latest_tiktok_videos,
    load_processed_ids,
    remove_processed_id,
    load_pending_queue,
    save_pending_queue,
    add_to_pending_queue,
    remove_from_pending_queue
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
tiktok_user = os.getenv("TIKTOK_USERNAME", "@b00kevin")

st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.title("🤖 TikTok Multi-Platform Command Center")

tab1, tab2 = st.tabs(["⚡ Panel Principal", "📅 Programador de Historial"])

# ==============================================================================
# TAB 1: PANEL PRINCIPAL
# ==============================================================================
with tab1:
    st.markdown('<div style="text-align: center; margin-bottom: 20px;">', unsafe_allow_html=True)
    if st.button("⚡ PUBLICAR ÚLTIMO VIDEO AHORA", key="btn_publish_now"):
        with st.spinner("Procesando último video de TikTok y publicando..."):
            config = dict(os.environ)
            config["FORCE_RUN"] = "1"
            res = run_crosspost_workflow(config)
            
            if res.get("status") in ["success", "partial_failure"]:
                st.balloons()
                st.success(f"¡Publicado exitosamente! Video: {res.get('title')}")
                for net, ok in res.get("results", {}).items():
                    if ok:
                        st.markdown(f"✅ **{net.capitalize()}**: Publicado con éxito.")
                    else:
                        st.markdown(f"❌ **{net.capitalize()}**: Falló o no configurado.")
            elif res.get("status") == "skipped":
                st.warning("El último video ya fue publicado previamente.")
            else:
                st.error(f"Error: {res.get('message')}")
    st.markdown('</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Último Video de TikTok</div>', unsafe_allow_html=True)
        with st.spinner("Buscando último video..."):
            videos = fetch_latest_tiktok_videos(tiktok_user, count=1)
            if videos:
                latest = videos[0]
                st.markdown(f"### {latest['title'] or 'Video sin título'}")
                st.caption(f"TikTok ID: {latest['id']} | Fecha: {latest.get('upload_date', 'N/A')}")
                st.video(latest['webpage_url'])
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
        st.markdown('<div class="section-title">Ajustes Rápidos</div>', unsafe_allow_html=True)
        new_user = st.text_input("Usuario de TikTok:", value=tiktok_user, key="t1_user")
        if new_user != tiktok_user:
            with open(".env", "w", encoding="utf-8") as f:
                f.write(f"TIKTOK_USERNAME={new_user}\n")
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
                is_selected = st.checkbox("", value=st.session_state.get(f"select_{v['id']}", False), key=f"select_{v['id']}")
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
