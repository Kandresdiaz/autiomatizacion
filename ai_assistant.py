import os
import re
import json
import datetime
import requests
from typing import Dict, Any, List, Optional, Tuple

# ==============================================================================
# CONFIGURACION Y DETECCION DE PROVEEDORES
# ==============================================================================

def get_env_config() -> Dict[str, str]:
    """Obtiene variables de entorno y del archivo .env."""
    config = dict(os.environ)
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        config[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass
    return config

def detect_ai_provider(config: Optional[Dict[str, str]] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Detecta si hay alguna API Key configurada.
    Prioridad:
      1. Gemini (Gratis, rapido, recomendado) -> GEMINI_API_KEY
      2. Groq (Ultra-rapido, gratis) -> GROQ_API_KEY
      3. OpenAI -> OPENAI_API_KEY
    """
    cfg = config or get_env_config()
    
    if cfg.get("GEMINI_API_KEY"):
        return "gemini", cfg.get("GEMINI_API_KEY")
    if cfg.get("GROQ_API_KEY"):
        return "groq", cfg.get("GROQ_API_KEY")
    if cfg.get("OPENAI_API_KEY"):
        return "openai", cfg.get("OPENAI_API_KEY")
        
    return None, None

def save_ai_key_to_env(provider_key_name: str, key_value: str) -> bool:
    """Guarda o actualiza la clave en el archivo .env de forma segura."""
    key_value = key_value.strip()
    if not key_value:
        return False
        
    lines = []
    found = False
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{provider_key_name}="):
            new_lines.append(f"{provider_key_name}={key_value}\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{provider_key_name}={key_value}\n")
        
    with open(".env", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    os.environ[provider_key_name] = key_value
    return True

# ==============================================================================
# PROMPT ENGINE: REGLAS ESTRICTAS ANTI-CLICHE Y MICROGANCHOS
# ==============================================================================

SYSTEM_PROMPT = """Eres un director creativo y experto de elite en retencion de video para TikTok, Instagram Reels y YouTube Shorts.
Tu trabajo es escribir guiones de ALTO IMPACTO y RITMO FRENETICO.

REGLAS DE ORO OBLIGATORIAS (PROHIBIDO EL CONTENIDO GENERICO / 'HABLAR TONTERIAS'):
1. CERO CLICHES: Queda terminantemente PROHIBIDO usar saludos como '¡Hola a todos!', 'Bienvenidos a mi canal', '¿Alguna vez te has preguntado...?', 'Hoy te voy a ensenar...', 'Quedate hasta el final'.
2. SEGUNDO CERO (00:00): El video DEBE arrancar inmediatamente en el primer segundo con conflicto, un error grave, un dato inesperado, una frase que rompa una creencia o una demostracion visual inmediata.
3. MICROGANCHOS CADA 3 A 5 SEGUNDOS:
   - En formato corto, si no ocurre un estimulo cada 3-5 segundos, el usuario hace scroll.
   - Cada segmento debe incluir:
     a) AUDIO: Frase corta, directa, conversacional (maximo 8-12 palabras por rafaga).
     b) VISUAL / ESTIMULO: Indicacion precisa para el creador (zoom in/out rapido, texto clave en pantalla, sonido 'pop'/'whoosh', corte de plano, B-roll o expresion facial).
4. TONO: Humano, crudo, seguro, sin rodeos corporativos ni palabras rimbombantes.
5. FORMATO DE RESPUESTA: Siempre responde en espanol neutro y entrega el guion estructurado como tabla o bloques temporales listos para produccion.
"""

def build_user_prompt(input_data: Dict[str, Any], style: str = "disruptive", target_duration: int = 30,
                      account_context: str = "") -> str:
    title = input_data.get("title", "")
    description = input_data.get("description", "")
    url = input_data.get("url", "")
    user_idea = input_data.get("user_idea", "")
    
    style_guidance = {
        "disruptive": "Enfoque Polemico / Disruptivo (desmonta un mito comun o ataca un error que la gente comete sin saberlo).",
        "quick_tutorial": "Enfoque Tutorial Express (metodo paso a paso sin relleno, resultado tangible en pocos segundos).",
        "storytelling": "Enfoque Historia / Conflicto Rapido ('Me paso esto y cambio todo...').",
        "top3_errors": "Enfoque Lista de Errores Criticos ('3 cosas que arruinan X y tu estas haciendo la numero 2')."
    }.get(style, "Enfoque Disruptivo de alta retencion.")

    prompt = f"""
Crea un nuevo guion para un video corto (Shorts / Reels / TikTok) con una duracion objetivo de aprox. {target_duration} segundos.

ESTILO SELECCIONADO: {style_guidance}

INFORMACION DE ENTRADA / INSPIRACION:
- Titulo/Idea original: {title or user_idea}
- Contexto o descripcion: {description or 'N/A'}
{f'- Link del video de referencia: {url}' if url else ''}

{account_context}

INSTRUCCIONES DE SALIDA:
Entrega tu respuesta estructurada exactamente con las siguientes secciones en Markdown:

### 🎯 3 Ganchos Alternativos para los Primeros 3 Segundos (A/B Testing)
- **Gancho 1 (Curiosidad agresiva):** ...
- **Gancho 2 (Miedo a perderse algo / Error):** ...
- **Gancho 3 (Resultado contraintuitivo):** ...

### 🎬 Guion de Produccion Paso a Paso (Microganchos cada 3-5s)
Presenta una tabla clara con las siguientes columnas:
| Tiempo (Segundos) | Lo que dices (Audio / Voz) | Lo que pasa en pantalla (Visual & Microgancho) |
(Asegurate de que cubra desde el segundo 0 hasta el final con cortes y micro-estimulos cada 3 a 5 segundos).

### ⚡ Llamado a la Accion (CTA) de 2 Segundos
(Un cierre veloz que no suene a 'por favor sigueme', sino que invite al debate o a guardar el video).

### 💡 Consejo Pro de Edicion
(1 o 2 trucos para este video: que musica de fondo usar, que SFX poner en el segundo clave, etc.).
"""
    return prompt

# ==============================================================================
# LLAMADAS A APIS (SIN DEPENDENCIAS EXTRA, SOLO REQUESTS)
# ==============================================================================

GEMINI_API_BASE = "https://generativelanguage.googleapis.com"

# Orden de preferencia entre los modelos que la clave REALMENTE tiene. Las
# familias 2.5 ya no se sirven a claves nuevas (404 "no longer available to new
# users"), asi que las 3.x van primero y las 2.5 quedan de ultimo recurso.
GEMINI_MODELOS_PREFERIDOS = [
    "gemini-3.8-flash",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

# El catalogo de la clave incluye modelos que NO generan texto: voz (tts),
# imagen, embeddings. Pedirles texto devuelve 400 y gasta un intento.
GEMINI_NO_TEXTO = ("tts", "image", "embedding", "aqa", "vision", "audio", "live")

# Cache por proceso: el catalogo no cambia entre llamadas.
_GEMINI_MODELOS_CACHE: Dict[str, List[Tuple[str, str]]] = {}


def _sirve_para_texto(modelo: str) -> bool:
    return not any(marca in modelo for marca in GEMINI_NO_TEXTO)


def _modelos_sugeridos(texto_error: str, modelo_fallido: str) -> List[str]:
    """
    Cuando Google retira un modelo, el propio 404 dice cual lo reemplaza
    ("Please update your code to use models/gemini-3.8-flash"). Se aprovecha
    esa pista en vez de adivinar.
    """
    sugeridos = []
    for nombre in re.findall(r"models/([A-Za-z0-9.\-_]+)", texto_error or ""):
        if nombre != modelo_fallido and _sirve_para_texto(nombre) and nombre not in sugeridos:
            sugeridos.append(nombre)
    return sugeridos


def listar_modelos_gemini(api_key: str) -> List[Tuple[str, str]]:
    """
    Modelos que esta clave puede usar con generateContent, como (version, modelo).

    Los nombres de Google caducan y no todas las claves ven el mismo catalogo,
    asi que se pregunta en vez de asumir.
    """
    if api_key in _GEMINI_MODELOS_CACHE:
        return _GEMINI_MODELOS_CACHE[api_key]

    encontrados: List[Tuple[str, str]] = []
    for version in ("v1beta", "v1"):
        try:
            resp = requests.get(
                f"{GEMINI_API_BASE}/{version}/models",
                params={"key": api_key, "pageSize": 100},
                timeout=20,
            )
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        try:
            datos = resp.json()
        except ValueError:
            continue
        for m in datos.get("models", []):
            if "generateContent" not in (m.get("supportedGenerationMethods") or []):
                continue
            modelo = str(m.get("name", "")).replace("models/", "")
            if _sirve_para_texto(modelo):
                encontrados.append((version, modelo))
        if encontrados:
            break

    def prioridad(item: Tuple[str, str]) -> Tuple[int, int]:
        _version, modelo = item
        for i, preferido in enumerate(GEMINI_MODELOS_PREFERIDOS):
            if modelo == preferido:
                return (0, i)
        # Entre los no listados, los 'flash' son los rapidos y de cuota generosa.
        return (1, 0 if "flash" in modelo else 1)

    encontrados.sort(key=prioridad)
    _GEMINI_MODELOS_CACHE[api_key] = encontrados
    return encontrados


def call_gemini(api_key: str, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """
    Llama a Gemini probando los modelos que la clave tiene disponibles.

    Si un modelo responde 404 porque fue retirado, Google indica el reemplazo en
    el propio mensaje; ese reemplazo se encola como siguiente intento. Asi la
    proxima retirada de modelos no vuelve a tumbar la funcion.
    """
    payload = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
        # El diagnostico del asesor son 6 secciones con tablas y los ganchos son
        # 10 bloques: 2048 se quedaba corto. Ademas los modelos nuevos gastan
        # parte del presupuesto de salida razonando.
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192},
    }
    headers = {"Content-Type": "application/json"}

    pendientes = list(listar_modelos_gemini(api_key))
    if not pendientes:
        # Sin catalogo (clave sin permiso de listar, red caida): a ciegas.
        pendientes = [("v1beta", m) for m in GEMINI_MODELOS_PREFERIDOS]

    errores: List[str] = []
    intentados: set = set()
    sobrecargado = False

    while pendientes and len(intentados) < 6:
        version, model = pendientes.pop(0)
        if model in intentados:
            continue
        intentados.add(model)

        url = f"{GEMINI_API_BASE}/{version}/models/{model}:generateContent"
        try:
            resp = requests.post(url, params={"key": api_key}, headers=headers,
                                 json=payload, timeout=60)
        except Exception as e:
            errores.append(f"{model}: {type(e).__name__}: {e}")
            continue

        if resp.status_code == 200:
            try:
                candidates = resp.json().get("candidates", [])
            except ValueError:
                errores.append(f"{model}: respuesta no-JSON")
                continue
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                texto = "".join(p.get("text", "") for p in parts)
                if texto.strip():
                    return texto
                motivo = candidates[0].get("finishReason", "sin texto")
                errores.append(f"{model}: respuesta vacia ({motivo})")
                continue
            errores.append(f"{model}: la API no devolvio candidatos")
            continue

        cuerpo = resp.text[:200]
        errores.append(f"{model}: HTTP {resp.status_code} {cuerpo}")
        if resp.status_code == 503:
            sobrecargado = True
        if resp.status_code == 404:
            # Google nombra el reemplazo en el error: probarlo a continuacion.
            for sugerido in _modelos_sugeridos(resp.text, model):
                if sugerido not in intentados:
                    pendientes.insert(0, (version, sugerido))

    pista = ""
    if sobrecargado:
        pista = " Alguno respondio 503 (demanda alta, temporal): reintenta en un minuto."

    raise RuntimeError(
        "Fallo al contactar Gemini. Intentos: " + " | ".join(errores) + "." + pista
    )

def call_openai_compatible(api_key: str, prompt: str, base_url: str, model: str,
                           system_prompt: str = SYSTEM_PROMPT) -> str:
    """Llama a OpenAI o Groq usando REST."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    resp = requests.post(base_url, headers=headers, json=payload, timeout=45)
    if resp.status_code == 200:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    else:
        raise RuntimeError(f"Error {resp.status_code}: {resp.text}")

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
    "openai": ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
}


def call_provider(provider: str, api_key: str, prompt: str, system_prompt: str) -> str:
    """Unico punto de salida hacia el proveedor detectado."""
    if provider == "gemini":
        return call_gemini(api_key, prompt, system_prompt)
    if provider in PROVIDERS:
        base_url, model = PROVIDERS[provider]
        return call_openai_compatible(api_key, prompt, base_url, model, system_prompt)
    raise RuntimeError(f"Proveedor no reconocido: {provider}")


def run_ai_task(prompt: str, system_prompt: str,
                config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Detecta el proveedor disponible y ejecuta la tarea. Todas las funciones de
    IA del proyecto devuelven este mismo contrato.
    """
    provider, api_key = detect_ai_provider(config)

    if not provider or not api_key:
        return {
            "success": False,
            "provider": None,
            "message": "No hay ninguna API Key de IA configurada (GEMINI_API_KEY, GROQ_API_KEY u OPENAI_API_KEY).",
            "content": None
        }

    try:
        return {
            "success": True,
            "provider": provider,
            "content": call_provider(provider, api_key, prompt, system_prompt)
        }
    except Exception as e:
        return {
            "success": False,
            "provider": provider,
            "message": f"Error al generar con {provider}: {str(e)}",
            "content": None
        }


def generate_video_script(
    input_data: Dict[str, Any],
    style: str = "disruptive",
    target_duration: int = 30,
    account_context: str = "",
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Genera un guion con microganchos a partir de un video o una idea.
    Con account_context (del analisis) calibra el guion a los numeros
    reales de la cuenta en vez de escribir a ciegas.
    """
    prompt = build_user_prompt(input_data, style=style, target_duration=target_duration,
                               account_context=account_context)
    return run_ai_task(prompt, SYSTEM_PROMPT, config=config)

# ==============================================================================
# ASESOR VIRAL: ANALISIS DE RENDIMIENTO REAL ANTES DE DAR CONSEJOS
# ==============================================================================

ANALYST_SYSTEM_PROMPT = """Eres un analista de crecimiento y asesor de contenido viral para video corto (TikTok, Reels, Shorts).
Recibes las METRICAS REALES de la cuenta de un creador y tu trabajo es decirle, con evidencia, por que un video funciono y otro no, y que hacer en el siguiente.

REGLAS DE ORO OBLIGATORIAS:
1. CERO CONSEJOS DE MANUAL: Queda prohibido decir 'usa hashtags virales', 'publica con constancia', 'engancha al espectador' o 'haz contenido de valor' si no van atados a un numero del reporte y a un COMO exacto y ejecutable.
2. TODA AFIRMACION LLEVA SU DATO: Cada conclusion cita la cifra que la sostiene (vistas, engagement %, duracion en segundos, hora de publicacion, titulo del video). Si no hay dato que la sostenga, no la digas.
3. DISTINGUE EL TIPO DE PROBLEMA:
   - Pocas vistas = problema de ALCANCE: el gancho de los primeros 3 segundos, el tema o el formato no retienen.
   - Muchas vistas con engagement bajo = problema de CONVERSION: falta provocar comentario, guardado o compartido.
   - Vistas muy irregulares = el tema o el formato no es consistente; no es 'el algoritmo'.
4. NO INVENTES METRICAS: solo existen las que te entregan. Si para concluir algo necesitas retencion por segundo, seguidores ganados o fuente de trafico, dilo explicitamente y di donde se ve (TikTok Studio > Analiticas).
5. MUESTRA PEQUENA = HIPOTESIS: si hay menos de 5 videos con datos o las vistas son muy bajas, avisalo en la primera linea y presenta las conclusiones como hipotesis a testear, no como verdades.
6. TONO: espanol neutro, directo, crudo, sin relleno corporativo. Prioriza tablas y listas accionables sobre parrafos.
"""


DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

FRANJAS_HORARIAS = [
    (0, 6, "00-06h (madrugada)"),
    (6, 12, "06-12h (manana)"),
    (12, 18, "12-18h (tarde)"),
    (18, 24, "18-24h (noche)"),
]


def _porcentaje(parte: int, total: int) -> float:
    return round(parte / total * 100, 2) if total else 0.0


def _franja_horaria(hora: Optional[int]) -> str:
    if hora is None:
        return "sin fecha"
    for inicio, fin, etiqueta in FRANJAS_HORARIAS:
        if inicio <= hora < fin:
            return etiqueta
    return "sin fecha"


def _rango_duracion(segundos: int) -> str:
    if not segundos:
        return "sin duracion"
    if segundos <= 15:
        return "0-15s"
    if segundos <= 30:
        return "16-30s"
    if segundos <= 45:
        return "31-45s"
    return "46s+"


def _agrupar(filas: List[Dict[str, Any]], clave: str) -> Dict[str, Dict[str, Any]]:
    """Promedio de vistas y engagement por grupo (franja horaria, duracion, dia)."""
    grupos: Dict[str, Dict[str, Any]] = {}
    for fila in filas:
        etiqueta = fila.get(clave) or "sin dato"
        g = grupos.setdefault(etiqueta, {"n": 0, "vistas": [], "engagement": []})
        g["n"] += 1
        g["vistas"].append(fila["views"])
        g["engagement"].append(fila["engagement"])
    return {
        etiqueta: {
            "n": g["n"],
            "views_promedio": round(sum(g["vistas"]) / g["n"]),
            "engagement_promedio": round(sum(g["engagement"]) / g["n"], 2),
        }
        for etiqueta, g in grupos.items()
    }


def compute_performance_metrics(videos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcula la evidencia numerica (engagement por video, promedios, mejores y
    peores, comparativas por duracion / horario / dia) que la IA usara como base.
    Todo el calculo es local y deterministico: la IA interpreta, no inventa.
    """
    filas: List[Dict[str, Any]] = []

    for v in videos:
        views = max(int(v.get("views") or 0), 0)
        likes = max(int(v.get("likes") or 0), 0)
        comments = max(int(v.get("comments") or 0), 0)
        shares = max(int(v.get("shares") or 0), 0)
        duration = max(int(v.get("duration") or 0), 0)

        hora = None
        dia = "sin fecha"
        fecha = "sin fecha"
        ts = int(v.get("timestamp") or 0)
        if ts:
            try:
                dt = datetime.datetime.fromtimestamp(ts)
                hora = dt.hour
                dia = DIAS_SEMANA[dt.weekday()]
                fecha = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        titulo = (v.get("title") or "").strip() or "(sin titulo)"
        filas.append({
            "id": str(v.get("id") or ""),
            "title": titulo,
            "webpage_url": v.get("webpage_url", ""),
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "duration": duration,
            "engagement": _porcentaje(likes + comments + shares, views),
            "like_rate": _porcentaje(likes, views),
            "comment_rate": _porcentaje(comments, views),
            "share_rate": _porcentaje(shares, views),
            "fecha": fecha,
            "hora": hora,
            "franja": _franja_horaria(hora),
            "dia": dia,
            "rango_duracion": _rango_duracion(duration),
            "largo_titulo": len(titulo),
        })

    if not filas:
        return {"videos": [], "resumen": {}, "mejores": [], "peores": [],
                "por_franja": {}, "por_duracion": {}, "por_dia": {}}

    vistas = sorted(f["views"] for f in filas)
    n = len(filas)
    mediana = vistas[n // 2] if n % 2 else round((vistas[n // 2 - 1] + vistas[n // 2]) / 2)
    por_vistas = sorted(filas, key=lambda f: f["views"], reverse=True)

    resumen = {
        "n": n,
        "views_total": sum(vistas),
        "views_promedio": round(sum(vistas) / n),
        "views_mediana": mediana,
        "views_max": vistas[-1],
        "views_min": vistas[0],
        "engagement_promedio": round(sum(f["engagement"] for f in filas) / n, 2),
        "comment_rate_promedio": round(sum(f["comment_rate"] for f in filas) / n, 2),
        "share_rate_promedio": round(sum(f["share_rate"] for f in filas) / n, 2),
        "duracion_promedio": round(sum(f["duration"] for f in filas) / n),
    }

    return {
        "videos": filas,
        "resumen": resumen,
        "mejores": por_vistas[:3],
        "peores": list(reversed(por_vistas[-3:])),
        "por_franja": _agrupar(filas, "franja"),
        "por_duracion": _agrupar(filas, "rango_duracion"),
        "por_dia": _agrupar(filas, "dia"),
    }


ANALYSIS_OUTPUT_SPEC = """ENTREGA TU RESPUESTA EXACTAMENTE CON ESTAS SECCIONES EN MARKDOWN:

### 📊 Diagnostico (maximo 3 lineas)
Di sin rodeos si el problema es de ALCANCE o de CONVERSION y con que cifra lo sostienes. Si la muestra es pequena, avisalo aqui.

### 🏆 Patron de lo que SI funciona
Compara los videos de arriba contra los de abajo, nombrandolos por su titulo. Que tienen en comun los mejores: tema, duracion, tipo de titulo, horario. Solo patrones que se vean en los numeros.

### 🧨 Lo que te esta costando vistas
Errores concretos detectados en los datos (duracion fuera del rango que te funciona, titulos que no abren curiosidad, cero compartidos, etc.). Cada punto con su cifra.

### 🛠️ 5 acciones para el proximo video
Tabla de 5 filas: | Accion exacta | Por que (dato que lo justifica) | Como se mide si funciono |

### 🎯 3 ideas listas para grabar
Por cada idea: tema + el gancho textual del segundo 0 (la frase exacta que se dice) + duracion objetivo en segundos. Basadas en lo que ya funciono en ESTA cuenta.

### 📈 Que medir en los proximos 7 dias
2 o 3 numeros concretos con la meta a superar, calculada desde los promedios de arriba."""


def build_analysis_prompt(metrics: Dict[str, Any], account: str = "",
                          extra_context: str = "", goal: str = "mas_vistas") -> str:
    """Arma el reporte de datos que recibe la IA: cifras, sin adjetivos."""
    resumen = metrics.get("resumen", {})
    filas = metrics.get("videos", [])

    objetivo = {
        "mas_vistas": "ALCANCE. Quiere que mas gente nueva vea los videos (vistas).",
        "mas_interaccion": "CONVERSION. Quiere mas comentarios, guardados y compartidos por vista.",
        "mas_seguidores": "SEGUIDORES. Quiere convertir espectadores sueltos en seguidores de la cuenta.",
        "vender": "VENTA. Quiere que el contenido traiga interesados reales en lo que ofrece.",
    }.get(goal, "ALCANCE. Quiere mas vistas.")

    lineas = [
        f"CUENTA ANALIZADA: {account or 'cuenta de TikTok del creador'}",
        f"OBJETIVO DEL CREADOR: {objetivo}",
        "",
        f"RESUMEN DE LOS ULTIMOS {resumen.get('n', 0)} VIDEOS CON DATOS:",
        f"- Vistas totales: {resumen.get('views_total', 0)}",
        f"- Vistas promedio: {resumen.get('views_promedio', 0)} | mediana: {resumen.get('views_mediana', 0)}",
        f"- Mejor video: {resumen.get('views_max', 0)} vistas | peor video: {resumen.get('views_min', 0)} vistas",
        f"- Engagement promedio ((likes+comentarios+compartidos) / vistas): {resumen.get('engagement_promedio', 0)}%",
        f"- Tasa de comentarios promedio: {resumen.get('comment_rate_promedio', 0)}% | tasa de compartidos: {resumen.get('share_rate_promedio', 0)}%",
        f"- Duracion promedio: {resumen.get('duracion_promedio', 0)}s",
        "",
        "DETALLE VIDEO POR VIDEO (del mas reciente al mas antiguo):",
        "| # | Titulo / texto del video | Dur. | Publicado | Vistas | Likes | Coment. | Comp. | Engagement |",
        "| - | - | - | - | - | - | - | - | - |",
    ]

    for i, f in enumerate(filas, start=1):
        titulo = f["title"].replace("|", "/")[:70]
        lineas.append(
            f"| {i} | {titulo} | {f['duration']}s | {f['fecha']} ({f['dia']}) | "
            f"{f['views']} | {f['likes']} | {f['comments']} | {f['shares']} | {f['engagement']}% |"
        )

    def bloque_grupo(titulo: str, datos: Dict[str, Dict[str, Any]]) -> None:
        if not datos:
            return
        lineas.append("")
        lineas.append(titulo)
        for etiqueta, d in sorted(datos.items(), key=lambda kv: kv[1]["views_promedio"], reverse=True):
            lineas.append(
                f"- {etiqueta}: {d['n']} video(s), {d['views_promedio']} vistas promedio, "
                f"{d['engagement_promedio']}% de engagement promedio"
            )

    bloque_grupo("COMPARATIVA POR DURACION DEL VIDEO:", metrics.get("por_duracion", {}))
    bloque_grupo("COMPARATIVA POR FRANJA HORARIA DE PUBLICACION:", metrics.get("por_franja", {}))
    bloque_grupo("COMPARATIVA POR DIA DE LA SEMANA:", metrics.get("por_dia", {}))

    if extra_context.strip():
        lineas.append("")
        lineas.append(f"CONTEXTO QUE DA EL CREADOR (nicho, publico, que vende): {extra_context.strip()}")

    lineas.append("")
    lineas.append(ANALYSIS_OUTPUT_SPEC)

    return "\n".join(lineas)


def analyze_account_performance(
    videos: List[Dict[str, Any]],
    account: str = "",
    extra_context: str = "",
    goal: str = "mas_vistas",
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Asesor viral: analiza las metricas reales de los ultimos videos y devuelve un
    diagnostico accionable. Las metricas calculadas se devuelven siempre, incluso
    si la llamada a la IA falla, para que el dashboard pueda mostrarlas igual.
    """
    metrics = compute_performance_metrics(videos)

    if not metrics["videos"]:
        return {
            "success": False,
            "provider": None,
            "message": ("No hay videos con metricas para analizar. Revisa el usuario de TikTok "
                        "o intenta de nuevo (TikTok bloquea las consultas por rachas)."),
            "content": None,
            "metrics": metrics,
        }

    prompt = build_analysis_prompt(metrics, account=account, extra_context=extra_context, goal=goal)
    resultado = run_ai_task(prompt, ANALYST_SYSTEM_PROMPT, config=config)
    resultado["metrics"] = metrics
    return resultado
# ==============================================================================
# MODO GANCHOS: SOLO LAS APERTURAS DE LOS PRIMEROS 3 SEGUNDOS
# ==============================================================================

HOOKS_SYSTEM_PROMPT = """Eres un especialista en ganchos de apertura para video corto (TikTok, Reels, Shorts).
Tu unico trabajo son los PRIMEROS 3 SEGUNDOS: la frase exacta que se dice en voz alta y lo que se ve en pantalla mientras se dice.

REGLAS DE ORO OBLIGATORIAS:
1. SOLO EL GANCHO: no escribes el guion, ni el desarrollo, ni el cierre, ni el CTA. Nada de lo que pasa despues del segundo 3.
2. PROHIBIDO: saludos ('hola', 'que tal'), presentaciones ('en este video', 'hoy te voy a ensenar'), rellenos ('quedate hasta el final', 'alguna vez te has preguntado').
3. PROHIBIDO EL TONO PUBLICITARIO: nada que suene a eslogan o a promesa de venta. Si el gancho se pudiera poner en un banner de anuncio, no sirve.
4. MAXIMO 12 PALABRAS por frase. Se dice en 3 segundos o menos, en voz natural.
5. UN ANGULO DISTINTO POR GANCHO: no entregues 10 variaciones de la misma idea.
6. GRABABLE: el visual tiene que poder hacerse con un celular, una grabacion de pantalla o lo que el creador ya tiene a mano. Nada de produccion imposible.
7. ESPANOL NEUTRO, hablado, directo. Como se lo dirias a un amigo, no a un cliente.
"""


HOOKS_OUTPUT_SPEC = """FORMATO DE SALIDA (respetalo exactamente, sin nada antes ni despues de la lista):

**1.** "la frase exacta que se dice en voz alta"
📹 lo que se ve en pantalla mientras la dices
🎯 angulo

**2.** "..."
📹 ...
🎯 ...

El angulo de cada uno debe ser uno de estos, y no se repite: dolor, demostracion, error, contraintuitivo, curiosidad, conflicto, cifra, confesion, comparacion, objecion.
Nada de introduccion. Nada de cierre. Nada de explicaciones. Solo la lista."""


def build_account_context(metrics: Optional[Dict[str, Any]]) -> str:
    """
    Convierte las metricas del analisis en un contexto corto para calibrar lo
    que la IA propone. Sin analisis previo devuelve cadena vacia y la IA
    trabaja a ciegas, como antes.
    """
    if not metrics or not metrics.get("videos"):
        return ""

    resumen = metrics.get("resumen", {})
    lineas = [
        "DATOS REALES DE ESTA CUENTA (para calibrar tus propuestas; NO los menciones en tu respuesta):",
        f"- Ultimos {resumen.get('n', 0)} videos: {resumen.get('views_promedio', 0)} vistas promedio "
        f"(mediana {resumen.get('views_mediana', 0)}, mejor {resumen.get('views_max', 0)}).",
        f"- Engagement promedio: {resumen.get('engagement_promedio', 0)}%. "
        f"Duracion promedio actual: {resumen.get('duracion_promedio', 0)}s.",
    ]

    por_duracion = metrics.get("por_duracion") or {}
    if por_duracion:
        mejor = max(por_duracion.items(), key=lambda kv: kv[1]["views_promedio"])
        lineas.append(f"- Rango de duracion con mas vistas hasta ahora: {mejor[0]}.")

    if resumen.get("comment_rate_promedio", 0) == 0:
        lineas.append("- La cuenta NO esta generando comentarios: prioriza ganchos que obliguen a responder.")

    titulos = [v["title"] for v in metrics["videos"][:5] if v.get("title")]
    if titulos:
        lineas.append("- Asi abren sus videos actuales (NO repitas este tono ni estas formulas): "
                      + " / ".join(t[:45] for t in titulos))

    return "\n".join(lineas)


def build_hooks_prompt(input_data: Dict[str, Any], n: int = 10, account_context: str = "") -> str:
    """Prompt del modo ganchos: tema de entrada + contexto de la cuenta."""
    tema = (input_data.get("title") or input_data.get("user_idea") or "").strip()
    descripcion = (input_data.get("description") or "").strip()
    url = (input_data.get("url") or "").strip()

    partes = [f"Dame {n} ganchos distintos para los primeros 3 segundos de un video sobre:", f"TEMA: {tema}"]
    if descripcion and descripcion != tema:
        partes.append(f"CONTEXTO: {descripcion}")
    if url:
        partes.append(f"VIDEO DE REFERENCIA: {url}")
    if account_context:
        partes.append("")
        partes.append(account_context)
    partes.append("")
    partes.append(HOOKS_OUTPUT_SPEC)

    return "\n".join(partes)


def generate_hooks(
    input_data: Dict[str, Any],
    n: int = 10,
    account_context: str = "",
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Devuelve N aperturas para los primeros 3 segundos. Nada mas."""
    prompt = build_hooks_prompt(input_data, n=n, account_context=account_context)
    return run_ai_task(prompt, HOOKS_SYSTEM_PROMPT, config=config)
