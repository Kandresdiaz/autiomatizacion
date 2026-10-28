# 📖 Documentación Oficial del Proyecto: TikTok Multi-Platform Crossposter

Automatización gratuita en la nube para descargar automáticamente tus videos de TikTok sin marca de agua y resubirlos a **YouTube Shorts, Instagram Reels, X (Twitter) y Reddit**.

---

## 🛠️ Estructura del Proyecto

```
tiktok-crossposter/
├── app.py                      # Dashboard Web Frontend en Streamlit (Panel de Control, Programador y Asesor IA)
├── tiktok_crossposter.py       # Backend / Motor principal de descarga TikWM, captions IA y publicadores
├── ai_assistant.py             # Módulo opcional de IA: perfil del creador, analisis de metricas, plan semanal, monetizacion y guiones
├── processed_videos.json       # Historial de IDs de videos ya procesados
├── pending_queue.json          # Cola de videos programados para publicación progresiva
├── active_platforms.json       # Estado de activación de redes sociales (YouTube, IG, X, Reddit)
├── creator_profile.json        # Perfil del creador: nicho, oferta, seguidores y videos por semana (calibra toda la IA)
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

### 🧠 Pestaña 3: Asesor IA de Videos (Opcional)
- **100% Opcional:** Si no configuras ninguna clave de IA, el bot sigue publicando y funcionando con normalidad.
- **Sin Dependencias Extra:** Funciona mediante llamadas directas HTTP REST con `requests` (sin paquetes pesados que rompan el entorno).
- **Configuración en 30s:** Permite guardar `GEMINI_API_KEY` (gratis desde `aistudio.google.com`) directamente desde la interfaz en el `.env`. También acepta `GROQ_API_KEY` u `OPENAI_API_KEY`.

#### 🧬 Perfil del creador (se configura una vez y calibra TODO lo demás)
- **El problema que resuelve:** Sin perfil, la IA aconseja a un creador promedio. De ahí salían las dos quejas típicas: recomendaba "publica 1 video diario" sin saber cuántos puedes grabar, y proponía tácticas de cuenta grande (marcas, lives, colaboraciones) a una cuenta de 100 seguidores.
- **Qué se declara:** nicho concreto, a quién le hablas, **de dónde quieres que salga el dinero**, qué producto tienes y qué resuelve, herramientas que puedes mostrar en pantalla, **seguidores de hoy**, **videos que puedes publicar por semana** y **modo de trabajo** (volumen / sostenible / quirúrgico).
- **Modelo de negocio (`MODELOS_NEGOCIO`):** `apps_propias` (el producto es el negocio y las redes son el canal), `mixto` (apps como objetivo, servicios solo como caja puente) o `servicios`. No es un detalle de una sola pestaña: cambia qué significa "vender" para el análisis, para el plan semanal y para los ganchos. Con `apps_propias` la IA tiene **prohibido** proponer servicios, freelance, consultoría, cursos, mentorías o acuerdos con marcas como vía principal.
- **Dónde vive:** `creator_profile.json`, escrito por `save_creator_profile()` en `app.py` y normalizado por `normalize_creator_profile()` en `ai_assistant.py`.
- **Regla de cadencia:** `build_creator_profile_block()` inyecta en **todos** los prompts la capacidad declarada y le prohíbe explícitamente a la IA recomendar otra frecuencia o poner "sé constante" como acción. Todo plan se reparte en esos slots.
- **Etapa de la cuenta:** los seguidores se traducen a una etapa (arranque < 1.000, tracción 1.000-10.000, escala 10.000+) con la lista de tácticas que **no** aplican a ese tamaño. En arranque la IA no puede proponer lives, encuestas a la comunidad, colaboraciones, marcas ni fondo de creadores.
- **Modo volumen:** si lo eliges, la IA deja de buscar el video perfecto: cada video es un test, cada idea declara **qué variable prueba** y el avance se mide por cuántos superan tu mediana de vistas, no por la calidad de cada pieza.

#### 🔎 Sub-pestaña A: Análisis de Rendimiento (Asesor Viral)
- **Métricas reales, no suposiciones:** Lee de TikTok las vistas, likes, comentarios, compartidos y duración de los últimos 3 a 15 videos (`fetch_videos_with_stats()` en `tiktok_crossposter.py`), con `yt-dlp` como fuente principal y TikWM como respaldo.
- **Respaldo cuando TikTok bloquea el listado del perfil:** Si el scraper del perfil falla (pasa seguido desde IPs de datacenter), toma los videos del historial local `platform_status.json`, así el análisis nunca se queda sin fuente.
- **Cálculo local y determinístico:** `compute_performance_metrics()` en `ai_assistant.py` calcula el engagement por video ((likes+comentarios+compartidos)/vistas), promedios, mediana, mejores y peores videos, y comparativas por duración, franja horaria y día de la semana. La IA solo interpreta esos números: no los inventa.
- **Diagnóstico accionable:** El prompt del analista obliga a citar la cifra que sostiene cada afirmación, prohíbe los consejos de manual ("usa hashtags virales"), distingue problemas de **alcance** (pocas vistas = gancho/tema) de problemas de **conversión** (muchas vistas con poco engagement), y marca las conclusiones como hipótesis cuando hay menos de 5 videos.
- **Salida:** Diagnóstico, patrón de lo que sí funciona, lo que está costando vistas, tabla de 5 acciones (ninguna puede ser sobre cadencia ni constancia: eso lo fija el perfil), una idea lista para grabar **por cada slot de tu semana** con su gancho del segundo 0 y la variable que prueba, y las metas numéricas a superar en 7 días. Descargable en Markdown.
- **Objetivo configurable:** Más vistas, más interacción, más seguidores o vender; el asesor prioriza las recomendaciones según esa meta.
- **Puente al generador:** Botón para mandar el video con mejor rendimiento directo al generador de guiones.

#### 📅 Sub-pestaña B: Estructura de la semana
- **Una semana cerrada, no una lista de ideas:** `generate_weekly_plan()` reparte los videos que declaraste poder sostener entre los 7 días y entrega **una fila por slot** con tema concreto, gancho textual del segundo 0, duración, qué se ve en pantalla y qué variable prueba.
- **El reparto es local y determinístico:** `_reparto_semanal()` calcula cuántos videos caen en cada día (con menos de 7 prioriza lunes, miércoles, viernes y domingo). La IA solo rellena el contenido: no decide cuántos videos publicas ni cuándo.
- **Máximo 3 pilares:** la semana entera se sostiene en 3 tipos de video como máximo, para poder grabar en lote y para que el algoritmo entienda de qué es la cuenta. Prohibidas las categorías vacías tipo "tip del día" o "contenido de valor".
- **La semana responde una pregunta:** se declara arriba qué vas a saber el domingo que hoy no sabes, cada slot mueve una sola variable, y la salida incluye una regla de decisión explícita ("si pasa X, la semana que viene se hace Y").
- **Plan de grabación en lote:** agrupa qué slots salen de cada sesión de grabación, por lo que comparte montaje.
- **Apoyado en datos si los hay:** con el análisis corrido, `build_metrics_digest()` le pasa las cifras reales (mejor duración, mejor franja, mejor día, mejores y peores videos) y el pilar principal sale de ahí citando la cifra. Sin análisis lo dice y reparte los pilares para explorar.

#### 🚀 Sub-pestaña C: De las redes a mis apps
- **El producto es el negocio, el contenido es el canal:** `generate_monetization_plan()` no busca vías de ingreso sueltas. Parte de que el dinero sale del producto y trata el video corto como el canal que le trae usuarios.
- **La cuenta al revés:** desde la meta de ingresos hacia atrás — ingreso mensual objetivo → usuarios que pagan → registros o instalaciones → clics al enlace → vistas al mes → **videos al mes al promedio real de vistas de la cuenta**. Cada fila dice si el número es un dato real, un supuesto de la IA o un dato que falta y dónde se mide.
- **Responde si de verdad hay que "hacerse grande":** con las vistas reales calcula cuántos usuarios se pueden conseguir **este mes sin crecer nada** y qué porcentaje de la meta es. Si el alcance actual no alcanza, da el número exacto de vistas mensuales que sí alcanzaría y cuántos videos son a ese promedio. La respuesta la dan las cifras, no la intuición.
- **Entradas propias de la pestaña:** precio o modelo de cobro del producto y meta de ingresos mensual. Si se dejan vacíos la IA asume valores, los marca como supuestos y avisa de que confirmarlos cambia toda la cuenta.
- **Vistas no son usuarios:** tabla que separa qué tipo de video trae instalaciones de cuál solo trae vistas, y cómo se nota la diferencia en los datos.
- **Un solo producto al frente:** prohibido aconsejar construir otra app. Si hay varias, elige una y dice con qué criterio, más el problema que resuelve dicho **como lo diría el usuario**, no como lo diría el programador.
- **El camino del video a la app:** los pasos exactos desde ver el video hasta usar la app (dónde va el enlace, qué se ve al llegar, cuántos pasos hay) y en cuál se pierde más gente.
- **Y lo que NO deberías hacer todavía:** dice explícitamente si construir otra app, cambiar de nicho o esperar a tener más seguidores entran ahí, cada uno con el número que lo desbloquearía. Nada de métricas de vanidad: las metas a 30 días no pueden ser seguidores ni vistas totales.

#### 🎣 Sub-pestaña D: Ganchos & Guiones
- **Modo ganchos (lo principal):** Escribes de qué va el video y devuelve **10 aperturas distintas para los primeros 3 segundos**: la frase exacta que se dice, el visual que la acompaña y el ángulo usado (dolor, demostración, error, contraintuitivo, cifra, objeción...). Sin tabla, sin CTA, sin relleno: está pensado para el creador que no sigue un guion al pie de la letra pero necesita con qué abrir.
- **Calibrado con tus datos:** Si ya corriste el análisis, `build_account_context()` inyecta en el prompt las vistas promedio, el engagement, la duración que mejor funciona y los títulos actuales con la instrucción de **no repetir ese tono**. Sin análisis previo funciona igual, pero a ciegas.
- **Reglas del modo ganchos:** Máximo 12 palabras por frase, prohibidos los saludos y las presentaciones, prohibido el tono publicitario, un ángulo distinto por gancho y visuales grabables con un celular o una grabación de pantalla.
- **Reglas contra el gancho genérico (lo que hacía que no funcionaran):** cada gancho tiene que nombrar algo que se pueda ver, oír o medir (el error exacto, el nombre real de la herramienta, la cifra, el archivo, el resultado) y están prohibidos los sustantivos de coaching ("productividad", "potencial", "mentalidad", "éxito", "valor"). Si el mismo gancho serviría igual para un video de cocina y para uno de código, la IA lo descarta. Habla con las palabras del público que declaraste en el perfil, y cuando hay algo que mostrar el visual del segundo 0 arranca con esa pantalla ya en movimiento, no con tu cara presentando. Máximo 2 de los 10 pueden ser preguntas.
- **Guion completo (plegado):** El generador de guiones con microganchos cada 3-5s sigue disponible dentro del desplegable, y también recibe el contexto de la cuenta.
- **Exportación:** Ganchos y guion se descargan en Markdown.

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

