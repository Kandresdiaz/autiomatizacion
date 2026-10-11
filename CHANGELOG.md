# 📜 Historial de Cambios (CHANGELOG)

Todos los cambios notables realizados en este proyecto se registrarán en este archivo.

## [2.7.0] - 2026-10-11
### 🐛 Corregido
- **Reintento atascado que dejaba videos fuera de YouTube (causa raíz en producción):** `find_incomplete_video()` devolvía el primer video con cualquier red pendiente. Como al video `7689625193223949569` solo le faltaban X (401 permanente en el plan gratuito) y Reddit (sin credenciales), **cada corrida de GitHub Actions gastaba el reintento en ese mismo video**, y los 4 videos a los que de verdad les faltaba YouTube (`7691351448658988340`, `7692165172504431924`, `7692180380907998516`, `7692197163060743425`, publicados entre el 30-sep y el 2-oct con las credenciales viejas) nunca se volvieron a intentar. Ahora solo cuentan como pendientes las redes cuyas credenciales son válidas **en ese momento**, así el reintento va directo a los huecos que sí se pueden llenar.
- **Diagnóstico real del fallo de YouTube:** La subida fallaba porque el cliente OAuth de Google Cloud había sido **eliminado** (`deleted_client`), por lo que ni el refresh token ni ningún token nuevo podían canjearse. `publish_to_youtube` ahora canjea el refresh token **antes** de subir el MP4 y traduce `deleted_client`, `invalid_client`, `unauthorized_client`, `invalid_grant`, `quotaExceeded`, `uploadLimitExceeded` y `accessNotConfigured` a una instrucción concreta de qué hacer, en vez de devolver el error crudo de Google.
- **Pérdida de credenciales al cambiar el usuario de TikTok:** En `app.py`, guardar un usuario nuevo abría `.env` en modo `"w"` y escribía una sola línea, **borrando todos los tokens** de YouTube, Meta, X y Reddit. Ahora `update_env_key()` reescribe únicamente esa clave y conserva el resto del archivo.
- **Subida de YouTube resiliente:** Carga resumible en chunks de 4 MB con reintentos y backoff exponencial ante errores transitorios (500/502/503/504, cortes de conexión) y reporte de progreso.

### ✨ Añadido
- **`generate_youtube_token.py`:** Generador asistido de `YOUTUBE_REFRESH_TOKEN`. Acepta `client_secret.json` o Client ID/Secret pegados a mano, fuerza `access_type=offline` + `prompt=consent`, verifica el token contra la YouTube Data API y lo guarda en `.env` sin tocar las demás llaves.
- **Reddit con video nativo:** `publish_to_reddit` ahora sube el MP4 directamente a Reddit (mucho más alcance que un enlace), con miniatura extraída del propio video si hay `ffmpeg` disponible. Cadena de respaldo automática: video nativo ➔ post de enlace ➔ post de texto. Compatible con `praw` 7.x (`submit_video`) y 8.x (`submit(video=PostMedia(...))`).
- **Autenticación de Reddit verificada antes de subir** y traducción de sus errores típicos (`401`, `403` por app que no es de tipo *script*, `SUBREDDIT_NOTALLOWED`, flair obligatorio, `RATELIMIT`).
- **Variables opcionales de Reddit:** `REDDIT_FLAIR_ID` y `REDDIT_FLAIR_TEXT` para subreddits que exigen flair, añadidas también al workflow de GitHub Actions.
- **Diagnóstico de credenciales en vivo:** `check_all_credentials()` (y los `check_*_credentials()` por red) validan YouTube, Instagram, X y Reddit **sin publicar nada**, expuesto en el dashboard con el botón **🔬 Probar credenciales ahora**.

### 🛠️ Modificado
- `DOCUMENTATION.md`: Tabla de errores de Google OAuth, guía paso a paso para regenerar el token de YouTube, guía de creación de la app de Reddit (tipo *script*, 2FA, usuario sin `u/`) y estado de Reddit actualizado a **Operacional**.

---

## [2.6.0] - 2026-09-17
### 🐛 Corregido
- **Protección contra Re-publicación de Histórico Antiguo:** Limitada la detección automática en `run_crosspost_workflow` exclusivamente a los 3 videos más recientes del perfil de TikTok. Se evita que el scraper excave en el backlog histórico de videos viejos que el creador ya había publicado manualmente en Instagram u otras redes.
- **Sincronización Total del Historial TikTok:** Registrados en `processed_videos.json` todos los videos existentes en la cuenta `@b00kevin` (40 videos) para prevenir publicaciones retroactivas duplicadas.

### ✨ Añadido
- **Soporte `share_to_feed` en Instagram Reels:** Inclusión del parámetro `share_to_feed: true` en el contenedor de Meta Graph API para asegurar que los Reels aparezcan en el feed principal y se compartan sin fricción en Facebook.
- **Integración Reddit con Enlace Original y Fallback a Perfil de Usuario:** Mejora en `publish_to_reddit` para adjuntar el enlace original del video y utilizar automáticamente el perfil de usuario (`u/{username}`) si no se define un subreddit específico.
- **Secretos en GitHub Actions:** Añadidos `REDDIT_SUBREDDIT` y `GEMINI_API_KEY` al workflow `.github/workflows/crosspost.yml`.
### ✨ Añadido
- **Publicación por Enlace Directo (`crosspost_from_url`):** Permite procesar y publicar cualquier video pegando su enlace directo en `app.py` o pasándolo como argumento CLI (`python tiktok_crossposter.py <URL>`), sin depender del escaneo del perfil.
- **Tolerancia a Fallos Multicanal:** El sistema publica de forma independiente en cada red; si alguna plataforma falla por tokens expirados (ej: Meta Graph API o X), las plataformas activas y funcionales (como YouTube Shorts) completan la subida y el video se marca como procesado sin abortar.
- **Cabeceras de Navegador Real Anti-Bot:** Adición de cabeceras HTTP de navegador en `yt-dlp` para evitar bloqueos por parte de TikTok en entornos cloud (GitHub Actions).

### 🛠️ Modificado
- `app.py`: Añadido acordeón de publicación rápida por URL directa en la pestaña principal.
- `DOCUMENTATION.md`: Actualizada guía de resolución de tokens (Meta 60 días, X OAuth 1.0a) y resumen de operatividad.

### 🚀 Verificado en Producción
- Subida exitosa y comprobada en vivo de videos de TikTok a YouTube Shorts (IDs: `hC6OeBdDTVU` y `avL-dt7Sax0`).

---

## [2.4.0] - 2026-09-09
### ✨ Añadido
- **Módulo `ai_assistant.py` (100% Opcional):** Motor de generación de guiones de alta retención para Reels, TikTok y YouTube Shorts con microganchos cada 3 a 5 segundos.
- **Detección Multi-Proveedor:** Soporta Google Gemini (`GEMINI_API_KEY`, recomendado y gratuito), Groq (`GROQ_API_KEY`) y OpenAI (`OPENAI_API_KEY`) sin dependencias pesadas adicionales (usa llamadas REST directas con `requests`).
- **Pestaña `💡 Ideas & Guiones IA (Opcional)` en `app.py`:** Dashboard interactivo para generar guiones a partir del último video, videos del historial, URLs o ideas desde cero.
- **Acceso Directo desde Videos:** Botones de inspiración en el Panel Principal y en el Programador de Historial para enviar cualquier video al asistente con un solo clic.
- **Exportación de Guiones:** Descarga de guiones formateados con tabla de tiempos, audio, indicaciones visuales y 3 ganchos A/B testing.

### 🛠️ Modificado
- `DOCUMENTATION.md`: Documentada la arquitectura del módulo de IA, variables de entorno opcionales y guía de configuración gratuita en 30 segundos vía Google AI Studio.

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
