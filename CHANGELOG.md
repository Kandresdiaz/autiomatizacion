# 📜 Historial de Cambios (CHANGELOG)

Todos los cambios notables realizados en este proyecto se registrarán en este archivo.

---

## [2.3.0] - 2026-09-08
### ✨ Añadido
- **Verificación en Vivo de YouTube Shorts:** Flujo OAuth 2.0 de Google completado y verificado en producción con canal oficial. Subida exitosa comprobada de Shorts verticales en vivo.
- **Verificación en Vivo de Instagram Reels:** Integración con Meta Graph API (`instagram_content_publish`) verificada en producción publicando videos limpios descargados desde TikTok.

### 🛠️ Modificado
- **Diagnóstico de Plataformas en Streamlit:** Actualización de estados y mensajes de error específicos (ej: detección de HTTP 402 en la API de Twitter/X por política de cobro de subida de video).
- **Documentación y Guía de Secrets:** Actualizada la guía paso a paso para la configuración de secretos tanto en **Streamlit Cloud** como en **GitHub Actions**.

### 🐛 Corregido
- Renovación de credenciales OAuth de Google Cloud (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`) resolviendo el error de permisos insuficientes y tokens expirados.

---

## [2.2.0] - 2026-09-08
### ✨ Añadido
- **Reproductor de Video Nativo en Directo (`get_preview_play_url`):** Integración con la API de streaming de TikWM para reproducir videos MP4 sin marca de agua con controles y audio directamente dentro del dashboard de Streamlit.
- **Enlace Directo a TikTok:** Acceso rápido para abrir el video original en la plataforma.

### 🛠️ Modificado
- Corrección de formato del nombre de usuario de TikTok (`@usuario` sin duplicación de arrobas).
- Limpieza y optimización de la previsualización del último video en la pestaña principal de `app.py`.

### 🐛 Corregido
- Resuelto problema del reproductor negro con `0:00` en Streamlit que impedía visualizar el video de TikTok.
- Actualizadas y verificadas las credenciales de API para Instagram Graph API, YouTube Data API v3 y X (Twitter) v2.

---

## [2.1.0] - 2026-08-26
### ✨ Añadido
- **Skill de Autodocumentación (`.agents/skills/auto-docs-updater/SKILL.md`):** Skill para Antigravity que verifica cambios en Git y actualiza la documentación automáticamente en cada commit.
- **Pestaña `📅 Programador de Historial`:** Permite explorar hasta 50 videos antiguos de TikTok con miniatura, fecha y estado.
- **Modos de Publicación Programada:**
  - Publicación por lotes en vivo con intervalos de pausa configurables (1 min, 5 min, 15 min, 1 hora).
  - Cola persistente (`pending_queue.json`) integrada con GitHub Actions para publicar 1 video cada 2 horas.
- **Botón `🔓 Desmarcar`:** Permite cambiar el estado de un video de `✅ Ya Publicado` a `⏳ Pendiente` para reintentar su publicación.
- **Diagnóstico en Vivo de Redes Sociales:** Muestra el motivo exacto de omisión o fallo por cada red social en la interfaz de Streamlit.

### 🛠️ Modificado
- Refactorización de `tiktok_crossposter.py` con función modular `crosspost_single_video`.
- Extracción extendida de metadatos de TikTok con `yt-dlp` (miniaturas, timestamp, fechas formateadas).
- Actualización del workflow `.github/workflows/crosspost.yml` para sincronizar `pending_queue.json`.

---

## [1.0.0] - 2026-08-01
### ✨ Lanzamiento Inicial
- Descarga de videos de TikTok sin marca de agua via TikWM API.
- Generación de captions personalizados por red social con Gemini AI.
- Publicadores automáticos para YouTube Shorts, Instagram Reels, X (Twitter) y Reddit.
- Dashboard web inicial en Streamlit (`app.py`).
