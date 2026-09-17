# 📜 Historial de Cambios (CHANGELOG)

Todos los cambios notables realizados en este proyecto se registrarán en este archivo.

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
