import os
import json
import time
import datetime
import streamlit as st
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
    get_preview_play_url
)
from ai_assistant import (
    detect_ai_provider,
    save_ai_key_to_env,
    generate_video_script
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

tab1, tab2, tab3 = st.tabs(["⚡ Panel Principal", "📅 Programador de Historial", "💡 Ideas & Guiones IA (Opcional)"])

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
                    st.toast("¡Video enviado al Asistente de Guiones IA! Ve a la pestaña '💡 Ideas & Guiones IA'.", icon="💡")
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
                if st.button("💡 Crear Guion IA", key=f"ai_seed_{v['id']}"):
                    st.session_state["ai_selected_video"] = v
                    st.session_state["ai_source_type"] = f"Video: {v.get('title', v['id'])[:30]}"
                    st.toast(f"¡Video {v['id']} cargado en 'Ideas & Guiones IA'!", icon="💡")
                
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
# TAB 3: IDEAS & GUIONES IA (OPCIONAL)
# ==============================================================================
with tab3:
    st.markdown('<div class="controls-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💡 Generador de Guiones de Alta Retención (Microganchos 3-5s)</div>', unsafe_allow_html=True)
    st.write("Crea guiones cinematográficos y dinámicos para Shorts/Reels/TikTok a partir de tus videos o ideas nuevas, sin frases clichés ni rodeos.")
    
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
        st.success(f"🟢 **Asistente de IA Activo:** Proveedor detectado (`{ai_provider.upper()}`). Listo para generar.")
        
        col_ai1, col_ai2 = st.columns([1.2, 1])
        
        with col_ai1:
            st.markdown("#### 1. ¿En qué video o idea nos basamos?")
            
            preloaded_video = st.session_state.get("ai_selected_video")
            preloaded_title = preloaded_video.get("title", "") if preloaded_video else ""
            preloaded_url = preloaded_video.get("webpage_url", "") if preloaded_video else ""
            
            source_choice = st.radio(
                "Origen del contenido:",
                ["Video seleccionado / precargado", "Escribir idea o tema libre", "Pegar URL o título manual"],
                index=0 if preloaded_video else 1
            )
            
            video_payload = {}
            if source_choice == "Video seleccionado / precargado":
                if preloaded_video:
                    st.info(f"📌 **Video cargado:** {preloaded_title or 'Sin título'} (`ID: {preloaded_video.get('id')}`)")
                    video_payload = {
                        "title": preloaded_title,
                        "description": preloaded_title,
                        "url": preloaded_url
                    }
                else:
                    st.warning("No has seleccionado ningún video aún. Puedes ir a 'Panel Principal' o 'Programador de Historial' y pulsar '💡 Crear Guion IA', o elegir 'Escribir idea o tema libre'.")
            elif source_choice == "Escribir idea o tema libre":
                user_idea = st.text_area(
                    "¿De qué quieres que hable el video?",
                    placeholder="Ejemplo: Por qué los programadores no deberían usar loops infinitos / Cómo ganar clientes...",
                    height=100
                )
                video_payload = {"user_idea": user_idea}
            else:
                manual_title = st.text_input("Título o tema del video:", placeholder="Ej: Las 3 herramientas que uso a diario...")
                manual_url = st.text_input("Link de referencia (opcional):", placeholder="https://www.tiktok.com/@...")
                video_payload = {"title": manual_title, "url": manual_url}
                
        with col_ai2:
            st.markdown("#### 2. Configuración de Retención")
            style_opt = st.selectbox(
                "Ángulo psicológico del guion:",
                [
                    ("disruptive", "🔥 Polémico / Disruptivo (Rompe mitos / Ataca un error)"),
                    ("quick_tutorial", "⚡ Tutorial Express (Paso a paso sin relleno)"),
                    ("storytelling", "📖 Historia / Conflicto Rápido (Storytelling de 30s)"),
                    ("top3_errors", "⚠️ Top 3 Errores Críticos (Alta curiosidad)")
                ],
                format_func=lambda x: x[1]
            )[0]
            
            duration_opt = st.select_slider(
                "Duración estimada del video:",
                options=[15, 30, 45, 60],
                value=30,
                format_func=lambda x: f"{x} segundos"
            )
            
        st.divider()
        if st.button("⚡ GENERAR GUION DE ALTO IMPACTO (MICROGANCHOS CADA 3-5s)", key="btn_run_ai_gen"):
            if not video_payload.get("title") and not video_payload.get("user_idea"):
                st.error("Por favor define un tema o selecciona un video para que la IA sepa de qué escribir.")
            else:
                with st.spinner("Creando estructura de microganchos y guion de alta retención..."):
                    result = generate_video_script(video_payload, style=style_opt, target_duration=duration_opt)
                    if result.get("success"):
                        st.session_state["ai_generated_result"] = result.get("content")
                        st.toast("¡Guion generado con éxito!", icon="✨")
                    else:
                        st.error(f"Error al generar: {result.get('message')}")
                        
        if "ai_generated_result" in st.session_state:
            st.markdown("### 📝 Guion y Estrategia Generada")
            st.markdown(st.session_state["ai_generated_result"])
            
            st.download_button(
                label="📥 Descargar Guion (.txt / .md)",
                data=st.session_state["ai_generated_result"],
                file_name="guion_tiktok_microganchos.md",
                mime="text/markdown"
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
