# 📜 Historial de Cambios (CHANGELOG)

Todos los cambios notables realizados en este proyecto se registrarán en este archivo.

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
