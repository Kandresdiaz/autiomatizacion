# ⚡ TikTok Multi-Platform Crossposter

Automatización **100% gratuita y en la nube** para descargar automáticamente tus videos de TikTok sin marca de agua y resubirlos a **YouTube Shorts, Instagram Reels, X (Twitter) y Reddit**.

---

## 🎨 Características

- **Dashboard Web de Control (Frontend):** Interfaz construida en Python con Streamlit para configurar credenciales, probar publicaciones y ver logs en tiempo real.
- **Sin Marcas de Agua:** Utiliza la API gratuita de TikWM para obtener el archivo `.mp4` limpio.
- **100% en la Nube:** Corre de fondo en **GitHub Actions** cada 2 horas o a través de **Streamlit Cloud** sin ocupar espacio en tu computadora.
- **Memoria de Duplicados:** Guarda los IDs de videos procesados en `processed_videos.json` para no repetir publicaciones.

---

## 🛠️ Estructura del Proyecto

```
tiktok-crossposter/
├── app.py                      # Interfaz Web Frontend (Streamlit Dashboard)
├── tiktok_crossposter.py       # Backend / Motor de automatización en Python
├── requirements.txt            # Dependencias
├── processed_videos.json       # Historial de videos procesados
└── .github/
    └── workflows/
        └── crosspost.yml       # Programador automático en la nube
```

---

## 🚀 Cómo ejecutar la Interfaz Web Localmente

1. Abre tu terminal en la carpeta del proyecto:
   ```bash
   pip install -r requirements.txt
   ```
2. Inicia el Dashboard Web:
   ```bash
   streamlit run app.py
   ```
3. Se abrirá automáticamente tu navegador en `http://localhost:8501`.

---

## ☁️ Despliegue en la Nube 100% Gratis

### Opción A: Automatización Silenciosa (GitHub Actions)
1. Crea un nuevo repositorio **privado** en tu cuenta de GitHub.
2. Sube todos estos archivos a tu repositorio.
3. Ve a la pestaña **Settings** ➔ **Secrets and variables** ➔ **Actions**.
4. Haz clic en **New repository secret** e ingresa cada una de tus llaves de API:

| Secret Name | Valor / Descripción |
| :--- | :--- |
| `TIKTOK_USERNAME` | Tu usuario de TikTok (ej. `@tu_usuario`) |
| `YOUTUBE_CLIENT_ID` | Client ID de Google Cloud Console |
| `YOUTUBE_CLIENT_SECRET` | Client Secret de Google Cloud Console |
| `YOUTUBE_REFRESH_TOKEN` | Refresh token generado de YouTube |
| `INSTAGRAM_USER_ID` | ID de usuario de Instagram Business/Creador |
| `INSTAGRAM_ACCESS_TOKEN` | Token de acceso de Meta Graph API |
| `X_API_KEY` | API Key de X Developer Portal |
| `X_API_SECRET` | API Secret Key de X Developer Portal |
| `X_ACCESS_TOKEN` | Access Token de X Developer Portal |
| `X_ACCESS_TOKEN_SECRET` | Access Token Secret de X Developer Portal |
| `REDDIT_CLIENT_ID` | Client ID de Reddit App |
| `REDDIT_CLIENT_SECRET` | Client Secret de Reddit App |
| `REDDIT_USERNAME` | Tu usuario de Reddit |
| `REDDIT_PASSWORD` | Tu contraseña de Reddit |

¡Listo! El servidor de GitHub revisará automáticamente tu TikTok cada 2 horas y resubirá tus nuevos videos sin costo.

---

### Opción B: Dashboard Web en la Nube (Streamlit Community Cloud)
1. Entra a [share.streamlit.io](https://share.streamlit.io/).
2. Conecta tu cuenta de GitHub.
3. Selecciona este repositorio y pon `app.py` como archivo principal.
4. ¡Tendrás tu propia aplicación web pública o privada funcionando gratis en la nube!

---

## ⚡ Lista Rápida para Obtener tus LLaves de API Gratis

- **YouTube:** [Google Cloud Console](https://console.cloud.google.com/) (Gratis - 10,000 unidades diarias).
- **Instagram:** [Meta for Developers](https://developers.facebook.com/) (Gratis via Instagram Graph API).
- **X (Twitter):** [X Developer Portal](https://developer.x.com/) (Gratis v2 Free Tier - 1,500 tweets/mes).
- **Reddit:** [Reddit Apps](https://www.reddit.com/prefs/apps) (Gratis - opción script).
