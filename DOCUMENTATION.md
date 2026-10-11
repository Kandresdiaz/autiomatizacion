# 📖 Documentación Oficial del Proyecto: TikTok Multi-Platform Crossposter

Automatización gratuita en la nube para descargar automáticamente tus videos de TikTok sin marca de agua y resubirlos a **YouTube Shorts, Instagram Reels, X (Twitter) y Reddit**.

---

## 🛠️ Estructura del Proyecto

```
tiktok-crossposter/
├── app.py                      # Dashboard Web Frontend en Streamlit (Panel de Control, Programador e Ideas IA)
├── tiktok_crossposter.py       # Backend / Motor principal de descarga TikWM, captions IA y publicadores
├── ai_assistant.py             # Módulo opcional de IA para análisis y generación de guiones con microganchos 3-5s
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
| `REDDIT_SUBREDDIT` | Reddit (Opcional) | Subreddit destino sin `r/`. Si lo dejas vacío publica en tu propio perfil (`u_tuusuario`), que siempre acepta video |
| `REDDIT_FLAIR_ID` | Reddit (Opcional) | ID de flair, obligatorio en subreddits que exigen flair |
| `REDDIT_FLAIR_TEXT` | Reddit (Opcional) | Texto del flair cuando el subreddit lo permite libre |
| `GEMINI_API_KEY` | IA (Opcional) | **Recomendada (Gratis)**. Clave de Google AI Studio (`aistudio.google.com`) para análisis y guiones con microganchos |
| `GROQ_API_KEY` | IA (Opcional) | Alternativa gratis para usar modelos Llama 3 en el asistente de guiones |
| `OPENAI_API_KEY` | IA (Opcional) | Alternativa si prefieres usar modelos GPT-4o-mini de OpenAI |

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
- **🔗 Publicar por Enlace Directo:** Sección desplegable para pegar cualquier enlace directo de TikTok y publicarlo de inmediato a todos los canales activos sin depender del escaneo periódico del perfil.
- Vista previa embebida del último video de TikTok con reproductor sin marcas de agua.
- Toggles para activar/desactivar plataformas individuales (YouTube, IG, X, Reddit).
- **🔬 Probar credenciales ahora:** valida en vivo YouTube, Instagram, X y Reddit *sin publicar nada*, y muestra el error exacto más la solución concreta cuando una llave ha caducado o ha sido revocada.

### 📅 Pestaña 2: Programador de Historial
- Recupera hasta 50 videos del perfil de TikTok mostrando miniatura (cover), título, ID, fecha de publicación y estado.
- Filtros por estado (*Todos*, *Solo pendientes*, *Solo ya publicados*), rango de fechas o búsqueda por texto.
- **Opción A (Publicación por Lotes en Vivo):** Permite elegir un tiempo de descanso entre videos (ej: 5 min, 15 min, 1 hora) con barra de progreso.
- **Opción B (Cola de Automatización):** Guarda los videos en `pending_queue.json` para que GitHub Actions publique 1 video cada ciclo.
- **Botón 🔓 Desmarcar:** Permite convertir cualquier video marcado como `✅ Ya Publicado` de vuelta a `⏳ Pendiente` para reintentar su publicación.
- **Botón 💡 Crear Guion IA:** Envía cualquier video del historial al asistente para desglosarlo y generar nuevos conceptos.

### 💡 Pestaña 3: Ideas & Guiones IA (Opcional)
- **100% Opcional:** Si no configuras ninguna clave de IA, el bot sigue publicando y funcionando con normalidad.
- **Sin Dependencias Extra:** Funciona mediante llamadas directas HTTP REST con `requests` (sin paquetes pesados que rompan el entorno).
- **Ingeniería Anti-Clichés y Retención:** Prohíbe frases genéricas corporativas y saludos vacíos; fuerza arrancar en el segundo cero y generar micro-estímulos (zooms, cortes, SFX, texto) cada 3 a 5 segundos.
- **Configuración en 30s:** Permite guardar `GEMINI_API_KEY` (gratis desde `aistudio.google.com`) directamente desde la interfaz en el `.env`.
- **Modos de Creación:** A partir del último video, de cualquier video del historial, pegando un enlace o escribiendo una idea libre.
- **Exportación:** Permite descargar el guion formateado en Markdown/TXT para teleprompter o guion de grabación.

---

## 📊 Estado de Redes y Recomendaciones de Distribución

| Red Social | Estado | Recomendación | Notas Técnicas |
| :--- | :--- | :--- | :--- |
| **YouTube Shorts** | ✅ **Operacional** | **Imprescindible** | Flujo OAuth 2.0 con scope `youtube.upload`, subida resumible por chunks con reintentos. El refresh token se canjea *antes* de subir, así un fallo de credenciales se reporta al instante y con la solución concreta. Cada subida gasta ~1600 de las 10.000 unidades diarias de cuota (~6 videos/día). |
| **Instagram Reels** | ✅ **Operacional** | **Imprescindible** | Meta Graph API profesional. Requiere Long-Lived Token (60 días). Carga directa del video MP4 en CDN de TikWM sin marcas de agua. |
| **X (Twitter)** | ⚠️ **Restringido por API** | Opcional / Desactivar | La API gratuita (Free Tier) de X solo permite texto. La subida de video (`media_upload`) suele requerir el plan Basic ($100/mes) o rechaza con 401/402. |
| **Reddit** | ✅ **Operacional** | Recomendado | Sube el **video nativo** a Reddit (mucho más alcance que un enlace). Si el subreddit no acepta video, cae automáticamente a post de enlace y, en última instancia, a post de texto. Se omite sin interrumpir el resto de redes si faltan credenciales. |

---

## 🔄 Renovación de Credenciales

### YouTube / Google OAuth

Errores típicos y qué significan exactamente:

| Error de Google | Causa real | Solución |
| :--- | :--- | :--- |
| `deleted_client` | El cliente OAuth fue **borrado** de Google Cloud Console | Crear credenciales nuevas y regenerar el refresh token |
| `invalid_client` | `YOUTUBE_CLIENT_ID` / `SECRET` no coinciden con ningún cliente | Copiarlos de nuevo desde Credenciales |
| `unauthorized_client` | El cliente no es de tipo *Aplicación de escritorio* | Recrear el cliente como **Desktop app** |
| `invalid_grant` | Refresh token revocado, caducado (app en modo *Testing* caduca a los 7 días) o generado con otro `client_id` | Regenerar el refresh token y **publicar** la app OAuth |
| `quotaExceeded` | Se agotaron las 10.000 unidades diarias de la API | Esperar el reset o solicitar más cuota |

Para regenerar las credenciales:

1. En [Google Cloud Console](https://console.cloud.google.com): **APIs y servicios ➔ Biblioteca ➔** activar **YouTube Data API v3**.
2. **Pantalla de consentimiento OAuth:** pulsar **Publicar app** (si queda en *Testing*, el refresh token caduca a los 7 días).
3. **Credenciales ➔ Crear credenciales ➔ ID de cliente de OAuth ➔ Aplicación de escritorio.**
4. En la terminal del proyecto:
   ```bash
   python generate_youtube_token.py
   ```
   El script abre el navegador, autorizas con la cuenta **dueña del canal**, verifica el token contra la API y lo guarda en `.env`.
5. Copiar `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` y `YOUTUBE_REFRESH_TOKEN` también a **GitHub Secrets**.

### Reddit

1. Ir a [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) ➔ **create another app...**
2. Tipo: **script** (obligatorio; cualquier otro tipo devuelve `403`). Redirect URI: `http://localhost:8080`.
3. Copiar el ID que aparece bajo el nombre de la app (`REDDIT_CLIENT_ID`) y el *secret* (`REDDIT_CLIENT_SECRET`).
4. `REDDIT_USERNAME` va **sin** `u/`. Si la cuenta tiene 2FA, `REDDIT_PASSWORD` debe ser `tupassword:123456` (con el código TOTP del momento) — lo práctico es desactivar 2FA en la cuenta del bot.
5. La app debe estar creada por **el mismo usuario** de `REDDIT_USERNAME`.

### Meta Graph API (Instagram 60 días)
1. Generar User Token con `instagram_basic`, `instagram_content_publish`, `pages_show_list` en Graph API Explorer.
2. Ingresar a `developers.facebook.com/tools/debug/accesstoken` y pulsar **Extend Access Token**.
3. Copiar el token de 60 días a `INSTAGRAM_ACCESS_TOKEN` en `.env` y en **GitHub Secrets**.

### X / Twitter
1. En Developer Console ➔ App Settings ➔ User authentication ➔ Configurar **Read and Write**.
2. En Keys and Tokens ➔ Regenerar `Access Token and Secret`. Copiar y actualizar en `.env` y en **GitHub Secrets**.

