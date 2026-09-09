# 📖 Documentación Oficial del Proyecto: TikTok Multi-Platform Crossposter

Automatización gratuita en la nube para descargar automáticamente tus videos de TikTok sin marca de agua y resubirlos a **YouTube Shorts, Instagram Reels, X (Twitter) y Reddit**.

---

## 🛠️ Estructura del Proyecto

```
tiktok-crossposter/
├── app.py                      # Dashboard Web Frontend en Streamlit (Panel de Control y Programador)
├── tiktok_crossposter.py       # Backend / Motor principal de descarga TikWM, captions IA y publicadores
├── processed_videos.json       # Historial de IDs de videos ya procesados
├── pending_queue.json          # Cola de videos programados para publicación progresiva
├── active_platforms.json       # Estado de activación de redes sociales (YouTube, IG, X, Reddit)
├── .env                        # Variables de entorno locales
├── requirements.txt            # Dependencias de Python
├── .agents/
│   └── skills/
│       └── auto-docs-updater/ # Skill personalizada para actualizar documentación en cada commit
└── .github/
    └── workflows/
        └── crosspost.yml       # Tarea automatizada en GitHub Actions (Corre cada 2 horas)
```

---

## 🔑 Configuración de Variables de Entorno y Llaves de API

Para que el robot publique correctamente en tus redes sociales, debes configurar las siguientes variables en tus secretos:

| Variable | Requerido Para | Descripción / Ejemplo |
| :--- | :--- | :--- |
| `TIKTOK_USERNAME` | TikTok | Usuario de TikTok (ej. `@b00kevin`) |
| `YOUTUBE_CLIENT_ID` | YouTube | Client ID OAuth de Google Cloud |
| `YOUTUBE_CLIENT_SECRET` | YouTube | Client Secret OAuth de Google Cloud |
| `YOUTUBE_REFRESH_TOKEN` | YouTube | **(¡Crucial!)** Refresh Token generado para autorizar subidas a tu canal |
| `INSTAGRAM_USER_ID` | Instagram | ID de cuenta Profesional / Creador de Instagram |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram | Token de acceso de Meta Graph API con permisos `instagram_content_publish` |
| `X_API_KEY` | X (Twitter) | API Key de X Developer Portal |
| `X_API_SECRET` | X (Twitter) | API Secret de X Developer Portal |
| `X_ACCESS_TOKEN` | X (Twitter) | Access Token de tu cuenta de X |
| `X_ACCESS_TOKEN_SECRET` | X (Twitter) | Access Token Secret de tu cuenta de X |
| `REDDIT_CLIENT_ID` | Reddit | Client ID de app tipo Script en Reddit |
| `REDDIT_CLIENT_SECRET` | Reddit | Client Secret de app de Reddit |
| `REDDIT_USERNAME` | Reddit | Usuario de tu cuenta de Reddit |
| `REDDIT_PASSWORD` | Reddit | Contraseña de tu cuenta de Reddit |

---

## ⚠️ Diferencia Importante: GitHub Secrets vs Streamlit Cloud Secrets

Existen 2 entornos independientes donde debes configurar tus llaves según cómo uses el robot:

1. **Para la Automatización Silenciosa en la Nube (GitHub Actions):**
   - Configura las variables en **GitHub** ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions**.
   - Se ejecuta automáticamente cada 2 horas buscando videos nuevos o procesando la cola `pending_queue.json`.

2. **Para la Interfaz Web en la Nube (Streamlit Cloud):**
   - Si usas la app web en `streamlit.app`, debes ingresar a **share.streamlit.io** ➔ **App Settings** ➔ **Secrets** y pegar allí las llaves en formato TOML:
   ```toml
   TIKTOK_USERNAME = "@b00kevin"
   INSTAGRAM_USER_ID = "..."
   INSTAGRAM_ACCESS_TOKEN = "..."
   YOUTUBE_CLIENT_ID = "..."
   YOUTUBE_CLIENT_SECRET = "..."
   YOUTUBE_REFRESH_TOKEN = "..."
   X_API_KEY = "..."
   X_API_SECRET = "..."
   X_ACCESS_TOKEN = "..."
   X_ACCESS_TOKEN_SECRET = "..."
   ```

---

## 🚀 Funcionalidades de la Interfaz Web (`app.py`)

### ⚡ Pestaña 1: Panel Principal
- Botón **⚡ PUBLICAR ÚLTIMO VIDEO AHORA** para publicar el video más reciente en vivo.
- Vista previa embebida del último video de TikTok.
- Toggles para activar/desactivar plataformas individuales (YouTube, IG, X, Reddit).

### 📅 Pestaña 2: Programador de Historial
- Recupera hasta 50 videos del perfil de TikTok mostrando miniatura (cover), título, ID, fecha de publicación y estado.
- Filtros por estado (*Todos*, *Solo pendientes*, *Solo ya publicados*), rango de fechas o búsqueda por texto.
- **Opción A (Publicación por Lotes en Vivo):** Permite elegir un tiempo de descanso entre videos (ej: 5 min, 15 min, 1 hora) con barra de progreso.
- **Opción B (Cola de Automatización):** Guarda los videos en `pending_queue.json` para que GitHub Actions publique 1 video cada 2 horas.
- **Botón 🔓 Desmarcar:** Permite convertir cualquier video marcado como `✅ Ya Publicado` de vuelta a `⏳ Pendiente` para reintentar su publicación.

---

## 📊 Estado de Redes y Recomendaciones de Distribución

| Red Social | Estado | Recomendación | Notas Técnicas |
| :--- | :--- | :--- | :--- |
| **YouTube Shorts** | ✅ **Operacional** | **Imprescindible** | Flujo OAuth 2.0 con scope `youtube.upload`. Los videos se publican como Shorts públicos con SEO optimizado. |
| **Instagram Reels** | ✅ **Operacional** | **Imprescindible** | Meta Graph API profesional. Carga directa del video MP4 en CDN de TikWM sin marcas de agua. |
| **X (Twitter)** | ⚠️ **De Pago (API)** | Opcional / Desactivar | La API gratuita de X solo permite texto. Para subir videos MP4 por API, X exige suscripción Basic ($100/mes) o da error `402 Pago requerido`. |
| **Reddit** | ⚠️ **Desactivar** | No recomendado | Reddit no es una red de video corto personal. Los moderadores de subreddits penalizan o banean publicaciones automatizadas. |

