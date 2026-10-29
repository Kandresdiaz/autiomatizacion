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
# PERFIL DEL CREADOR: NICHO, OFERTA, TAMANO DE CUENTA Y CAPACIDAD DE PRODUCCION
# ==============================================================================
# Sin esto la IA aconseja a un creador promedio: cadencia de manual ("publica 1
# video diario"), ganchos que servirian para cualquier nicho y monetizacion de
# cuenta grande (marcas, fondo de creadores). El perfil la obliga a aconsejar a
# ESTE creador: su nicho, lo que construye, cuantos videos puede grabar de
# verdad y los seguidores que tiene hoy.

MODOS_PRODUCCION = {
    "volumen": (
        "VOLUMEN / APRENDIZAJE RAPIDO. Prioriza cantidad de intentos sobre pulido: cada video es un test "
        "para descubrir que tema y que formato enganchan. Produccion en lotes (varios videos en una sola "
        "sentada), edicion minima, se asume que la mayoria va a fracasar y eso no es un problema. El avance "
        "se mide por numero de tests publicados y por cuantos superan la mediana de vistas, no por la "
        "calidad de cada pieza suelta."
    ),
    "sostenible": (
        "SOSTENIBLE. Cadencia constante que el creador puede mantener semanas sin quemarse: se repite el "
        "formato que ya funciono y se testea una sola variable nueva por semana."
    ),
    "quirurgico": (
        "QUIRURGICO. Pocos videos, muy trabajados. Cada pieza apuesta a un tema ya validado por los datos; "
        "no se gastan slots en explorar a ciegas."
    ),
}

# De donde sale el dinero. No es un detalle de la pestana de monetizacion: cambia
# que es "vender" para el analisis, para la semana y para los ganchos. Si el
# creador vive de sus apps, el contenido es distribucion, no un escaparate de
# servicios.
MODELOS_NEGOCIO = {
    "apps_propias": (
        "PRODUCTO PROPIO. El negocio son SUS APPS: de ahi sale el dinero. El contenido no es la fuente de "
        "ingresos, es el canal de distribucion que lleva gente a usarlas. Queda PROHIBIDO proponerle vender "
        "servicios, freelance, consultoria, cursos, mentorias, plantillas o acuerdos con marcas como via "
        "principal. Si crees que necesita caja puente para sostenerse mientras el producto crece, lo dices en "
        "UNA linea marcada como 'no es el objetivo' y sigues trabajando el producto."
    ),
    "servicios": (
        "SERVICIOS. Vende su tiempo y su trabajo a medida (automatizaciones, desarrollo, consultoria). El "
        "contenido tiene que traer conversaciones con clientes potenciales."
    ),
    "mixto": (
        "MIXTO. Las apps son el objetivo real y los servicios son solo la caja de corto plazo. Prioriza "
        "siempre lo que acerque usuarios a las apps; los servicios aparecen unicamente como lo que financia "
        "el camino, nunca como el plan."
    ),
}

ETAPAS_CUENTA = [
    (0, 1000, "ARRANQUE (menos de 1.000 seguidores)",
     "Las vistas NO vienen de los seguidores, vienen del 'Para ti'. Queda PROHIBIDO aconsejar tacticas que "
     "necesitan una audiencia que todavia no existe: pedirle a los seguidores que comenten, lives, encuestas "
     "a la comunidad, colaboraciones con cuentas grandes, acuerdos con marcas o el fondo de creadores. En "
     "esta etapa el unico trabajo es encontrar el tema y el formato que el algoritmo empuja a desconocidos."),
    (1000, 10000, "TRACCION (1.000 a 10.000 seguidores)",
     "Ya hay audiencia minima: se puede serializar un formato y pedir una accion concreta, pero el grueso de "
     "las vistas sigue dependiendo del 'Para ti', no de los seguidores."),
    (10000, 10 ** 12, "ESCALA (mas de 10.000 seguidores)",
     "La audiencia propia ya mueve vistas por si sola: tiene sentido serializar, construir comunidad y "
     "monetizar por volumen."),
]


def _etapa_cuenta(followers: Optional[int]) -> Tuple[str, str]:
    """Etapa de la cuenta y que consejos SI aplican a ese tamano."""
    try:
        n = int(followers or 0)
    except (TypeError, ValueError):
        n = 0
    for minimo, maximo, etiqueta, regla in ETAPAS_CUENTA:
        if minimo <= n < maximo:
            return etiqueta, regla
    return ETAPAS_CUENTA[-1][2], ETAPAS_CUENTA[-1][3]


DEFAULT_CREATOR_PROFILE: Dict[str, Any] = {
    "nicho": "",
    "publico": "",
    "oferta": "",
    "herramientas": "",
    "followers": 0,
    "videos_por_semana": 7,
    "modo": "sostenible",
    "modelo_negocio": "apps_propias",
}


def normalize_creator_profile(profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Completa el perfil con los valores por defecto y normaliza los tipos."""
    datos = dict(DEFAULT_CREATOR_PROFILE)
    for clave, valor in (profile or {}).items():
        if clave in datos:
            datos[clave] = valor

    try:
        datos["followers"] = max(int(datos.get("followers") or 0), 0)
    except (TypeError, ValueError):
        datos["followers"] = 0

    try:
        datos["videos_por_semana"] = min(max(int(datos.get("videos_por_semana") or 1), 1), 70)
    except (TypeError, ValueError):
        datos["videos_por_semana"] = 7

    if datos.get("modo") not in MODOS_PRODUCCION:
        datos["modo"] = "sostenible"

    if datos.get("modelo_negocio") not in MODELOS_NEGOCIO:
        datos["modelo_negocio"] = "apps_propias"

    for clave in ("nicho", "publico", "oferta", "herramientas"):
        datos[clave] = str(datos.get(clave) or "").strip()

    return datos


def build_creator_profile_block(profile: Optional[Dict[str, Any]]) -> str:
    """
    Bloque de perfil que se inyecta en todos los prompts. Fija el nicho, el
    tamano real de la cuenta y la CADENCIA que el creador declaro poder sostener,
    para que la IA no invente una frecuencia de publicacion de manual.
    """
    datos = normalize_creator_profile(profile)
    declarado = bool(datos["nicho"] or datos["publico"] or datos["oferta"] or datos["followers"])

    etapa, regla_etapa = _etapa_cuenta(datos["followers"])
    por_semana = datos["videos_por_semana"]
    al_dia = round(por_semana / 7, 1)

    lineas = ["PERFIL DEL CREADOR (es obligatorio ajustar TODO el consejo a esto):"]

    if declarado:
        lineas += [
            f"- Nicho / de que habla: {datos['nicho'] or 'no declarado'}",
            f"- A quien le habla: {datos['publico'] or 'no declarado'}",
            f"- Que ofrece o quiere monetizar: {datos['oferta'] or 'no declarado'}",
        ]
        if datos["herramientas"]:
            lineas.append(
                f"- Herramientas / stack que usa y puede mostrar en pantalla: {datos['herramientas']}"
            )
        lineas.append(f"- Seguidores hoy: {datos['followers']} -> ETAPA {etapa}. {regla_etapa}")
    else:
        lineas.append("- El creador no declaro nicho ni oferta: no te lo inventes. Trabaja con el tema que "
                      "te den y marca en una linea que dato falta para afinar el consejo.")

    lineas += [
        f"- CAPACIDAD DE PRODUCCION DECLARADA: {por_semana} video(s) por semana ({al_dia} al dia en promedio).",
        f"- MODO DE TRABAJO ELEGIDO: {MODOS_PRODUCCION[datos['modo']]}",
        f"- DE DONDE SALE EL DINERO: {MODELOS_NEGOCIO[datos['modelo_negocio']]}",
        "",
        f"REGLA DE CADENCIA: todo plan que entregues se reparte exactamente en esos {por_semana} slots de la "
        "semana. Queda PROHIBIDO recomendar una frecuencia distinta a la declarada (nada de 'publica 1 video "
        "diario', 'sube 3 veces por semana' o 'se constante') y PROHIBIDO pedirle que publique mas o menos de "
        "lo que declaro. Si el volumen te parece insuficiente o excesivo para su objetivo, dilo en UNA linea "
        "con el numero que faltaria y despues planifica con el volumen declarado.",
    ]
    return "\n".join(lineas)


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
                      account_context: str = "", profile: Optional[Dict[str, Any]] = None) -> str:
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

{build_creator_profile_block(profile)}

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
    profile: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Genera un guion con microganchos a partir de un video o una idea.
    Con account_context (del analisis) calibra el guion a los numeros
    reales de la cuenta en vez de escribir a ciegas.
    """
    prompt = build_user_prompt(input_data, style=style, target_duration=target_duration,
                               account_context=account_context, profile=profile)
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
7. RESPETA LA CADENCIA DECLARADA: el perfil del creador trae cuantos videos por semana puede publicar de verdad y en que modo (volumen, sostenible o quirurgico). Todo plan se reparte en esos slots. Prohibido inventar una frecuencia ('publica 1 video diario') y prohibido poner 'se constante' o 'publica mas seguido' como accion.
8. AJUSTA AL TAMANO DE LA CUENTA: el perfil trae la etapa (arranque, traccion, escala) y que tacticas aplican a ese tamano. En arranque las vistas no vienen de los seguidores: prohibido proponer acciones que necesiten audiencia (pedir comentarios a los seguidores, lives, colaboraciones, marcas, fondo de creadores).
9. EN MODO VOLUMEN NO BUSQUES EL VIDEO PERFECTO: si el creador eligio volumen, el objetivo es cerrar la mayor cantidad de tests posibles y leer cual hipotesis gano. Cada idea que propongas dice QUE VARIABLE TESTEA (tema, formato, duracion, gancho) para que al final de la semana se pueda descartar con datos.
10. MONETIZACION SOLO LA DE SU ETAPA: si el creador quiere ganar dinero, parte de lo que YA ofrece (su producto, su app, su servicio) y habla en numeros absolutos de personas, no en porcentajes de conversion sobre vistas que todavia no tiene.
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

### 🛠️ 5 acciones para los proximos videos
Tabla de 5 filas: | Accion exacta | Por que (dato que lo justifica) | Como se mide si funciono |
Ninguna fila puede ser sobre cadencia ni sobre constancia: cuantos videos publica ya esta fijado en el perfil.

### 🎯 Ideas listas para grabar
Una idea por cada slot de la semana que declaro el creador, con un maximo de 10 filas. Si declaro mas slots que eso, di al final cuantas veces se reutiliza cada idea cambiando solo el gancho.
Tabla: | # | Tema concreto | Gancho del segundo 0 (frase exacta) | Dur. objetivo | Variable que testea |
Los temas salen de lo que ya funciono en ESTA cuenta y del nicho del perfil, no de ideas genericas.

### 📈 Que medir en los proximos 7 dias
2 o 3 numeros concretos con la meta a superar, calculada desde los promedios de arriba. Si el creador esta en modo volumen, uno de esos numeros es cuantos de los videos publicados superaron la mediana de vistas actual."""


def build_analysis_prompt(metrics: Dict[str, Any], account: str = "",
                          extra_context: str = "", goal: str = "mas_vistas",
                          profile: Optional[Dict[str, Any]] = None) -> str:
    """Arma el reporte de datos que recibe la IA: cifras, sin adjetivos."""
    resumen = metrics.get("resumen", {})
    filas = metrics.get("videos", [])

    objetivo = {
        "mas_vistas": "ALCANCE. Quiere que mas gente nueva vea los videos (vistas).",
        "mas_interaccion": "CONVERSION. Quiere mas comentarios, guardados y compartidos por vista.",
        "mas_seguidores": "SEGUIDORES. Quiere convertir espectadores sueltos en seguidores de la cuenta.",
        "vender": ("DISTRIBUCION. Quiere que el contenido traiga usuarios o clientes reales a lo que ofrece. "
                   "Mira 'DE DONDE SALE EL DINERO' en el perfil: si vive de sus apps, el objetivo son usuarios "
                   "de la app, no clientes de servicios."),
    }.get(goal, "ALCANCE. Quiere mas vistas.")

    lineas = [
        f"CUENTA ANALIZADA: {account or 'cuenta de TikTok del creador'}",
        f"OBJETIVO DEL CREADOR: {objetivo}",
        "",
        build_creator_profile_block(profile),
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
    profile: Optional[Dict[str, Any]] = None,
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

    prompt = build_analysis_prompt(metrics, account=account, extra_context=extra_context,
                                   goal=goal, profile=profile)
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
8. OBLIGATORIO SER CONCRETO: cada gancho nombra algo que se puede ver, oir o medir (el error exacto, el nombre real de la herramienta, la cifra, el archivo, la pantalla, el resultado, el tiempo que tardo). Prohibidos los sustantivos abstractos de coaching: 'productividad', 'potencial', 'mentalidad', 'exito', 'valor', 'habilidades', 'oportunidades'.
9. CERO GANCHOS REUSABLES: si el mismo gancho funcionaria igual para un video de cocina y para uno de codigo, esta mal y lo descartas. Tiene que ser imposible de usar fuera del tema y del publico que trae el perfil.
10. HABLA EL IDIOMA DEL PUBLICO DEL PERFIL: usa las palabras que esa gente ya usa (el nombre real del lenguaje, del framework, del error, de la herramienta) y no expliques lo que ya saben. Si el publico es tecnico, un gancho que suene a explicacion para principiantes esta mal.
11. SI HAY ALGO QUE MOSTRAR, SE MUESTRA: cuando el creador puede ensenar una pantalla, un resultado, un antes/despues o un objeto, el visual del segundo 0 arranca con eso ya en movimiento, no con su cara presentando.
12. NO TODOS LOS GANCHOS SON UNA PREGUNTA: maximo 2 de los que entregues pueden ser preguntas. El resto son afirmaciones, cifras o demostraciones.
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


def build_hooks_prompt(input_data: Dict[str, Any], n: int = 10, account_context: str = "",
                      profile: Optional[Dict[str, Any]] = None) -> str:
    """Prompt del modo ganchos: tema de entrada + perfil + contexto de la cuenta."""
    tema = (input_data.get("title") or input_data.get("user_idea") or "").strip()
    descripcion = (input_data.get("description") or "").strip()
    url = (input_data.get("url") or "").strip()

    partes = [f"Dame {n} ganchos distintos para los primeros 3 segundos de un video sobre:", f"TEMA: {tema}"]
    if descripcion and descripcion != tema:
        partes.append(f"CONTEXTO: {descripcion}")
    if url:
        partes.append(f"VIDEO DE REFERENCIA: {url}")
    partes.append("")
    partes.append(build_creator_profile_block(profile))
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
    profile: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Devuelve N aperturas para los primeros 3 segundos. Nada mas."""
    prompt = build_hooks_prompt(input_data, n=n, account_context=account_context, profile=profile)
    return run_ai_task(prompt, HOOKS_SYSTEM_PROMPT, config=config)


# ==============================================================================
# RESUMEN DE METRICAS REUTILIZABLE (plan semanal y monetizacion)
# ==============================================================================

def build_metrics_digest(metrics: Optional[Dict[str, Any]]) -> str:
    """
    Version compacta de las metricas, pensada para los prompts que no son el
    analisis completo. A diferencia de build_account_context, aqui SI se permite
    citar las cifras en la respuesta.
    """
    if not metrics or not metrics.get("videos"):
        return ("NUMEROS DE LA CUENTA: el creador todavia no corrio el analisis de rendimiento, asi que no "
                "tienes metricas. Dilo en la primera linea, no inventes cifras y marca tus propuestas como "
                "hipotesis a validar.")

    resumen = metrics.get("resumen", {})
    lineas = [
        f"NUMEROS REALES DE LA CUENTA (ultimos {resumen.get('n', 0)} videos, puedes citarlos):",
        f"- Vistas: promedio {resumen.get('views_promedio', 0)}, mediana {resumen.get('views_mediana', 0)}, "
        f"mejor {resumen.get('views_max', 0)}, peor {resumen.get('views_min', 0)}.",
        f"- Alcance total acumulado de esos videos: {resumen.get('views_total', 0)} vistas.",
        f"- Engagement promedio: {resumen.get('engagement_promedio', 0)}% "
        f"(comentarios {resumen.get('comment_rate_promedio', 0)}%, compartidos {resumen.get('share_rate_promedio', 0)}%).",
        f"- Duracion promedio actual: {resumen.get('duracion_promedio', 0)}s.",
    ]

    def mejor_de(datos: Dict[str, Dict[str, Any]], etiqueta: str) -> None:
        if datos:
            clave, valor = max(datos.items(), key=lambda kv: kv[1]["views_promedio"])
            lineas.append(f"- {etiqueta} con mas vistas promedio: {clave} ({valor['views_promedio']} vistas "
                          f"en {valor['n']} video(s)).")

    mejor_de(metrics.get("por_duracion") or {}, "Rango de duracion")
    mejor_de(metrics.get("por_franja") or {}, "Franja horaria")
    mejor_de(metrics.get("por_dia") or {}, "Dia de la semana")

    mejores = metrics.get("mejores") or []
    if mejores:
        lineas.append("- Los que mas funcionaron: " + " | ".join(
            f"\"{v['title'][:50]}\" ({v['views']} vistas, {v['duration']}s)" for v in mejores
        ))

    peores = metrics.get("peores") or []
    if peores:
        lineas.append("- Los que menos funcionaron: " + " | ".join(
            f"\"{v['title'][:50]}\" ({v['views']} vistas, {v['duration']}s)" for v in peores
        ))

    return "\n".join(lineas)


# ==============================================================================
# ESTRUCTURA DE LA SEMANA: QUE SE GRABA EN CADA SLOT Y QUE PRUEBA
# ==============================================================================

WEEKLY_PLAN_SYSTEM_PROMPT = """Eres un director de contenido que arma parrillas semanales de video corto (TikTok, Reels, Shorts) para un solo creador.
Tu entrega no es una lista de ideas: es un calendario cerrado donde cada slot ya tiene tema, gancho y duracion decididos, listo para grabar sin pensar mas.

REGLAS DE ORO OBLIGATORIAS:
1. EL VOLUMEN DECLARADO MANDA: el reparto de la semana te lo doy ya calculado. No cambias la cantidad de videos ni los dias, y no propones una cadencia distinta. Al final del prompt te digo cual de los dos formatos de entrega usar, porque depende de cuantos videos sean.
2. CADA VIDEO ES CONCRETO, NO UNA CATEGORIA: prohibido escribir 'tip del dia', 'behind the scenes', 'contenido de valor' o 'video motivacional'. Se escribe el tema exacto (que se explica, con que ejemplo, con que resultado). Esto vale igual para una variacion dentro de un formato repetible: 'otro caso de uso' no es una variacion, 'el cliente que escribio a las 11 de la noche un domingo' si lo es.
3. POCOS PILARES, SIEMPRE: con pocos videos la semana se sostiene en 3 pilares como maximo; en alto volumen, en 5 formatos repetibles como maximo. Nunca mas. Es lo que permite grabar en lote y lo que hace que el algoritmo entienda de que es la cuenta.
4. CADA SLOT TESTEA UNA SOLA VARIABLE Y LA SEMANA RESPONDE UNA PREGUNTA: la pregunta se declara arriba y cada fila dice que variable mueve (tema, formato, duracion, tipo de gancho). Si dos slots testean lo mismo, estas desperdiciando uno.
5. SE APOYA EN LO QUE YA FUNCIONO: si hay metricas, el pilar principal viene del tema, la duracion y la franja que mas vistas promedio dieron, y lo dices citando la cifra. Si no hay metricas, lo dices y reparte los pilares para explorar.
6. GRABABLE EN LOTE Y CON LO QUE YA TIENE: agrupa los videos que se graban de una sola sentada. Nada de produccion, equipo, invitados o locaciones que el creador no declaro tener.
7. NADA QUE NECESITE AUDIENCIA QUE NO EXISTE: respeta la etapa de la cuenta del perfil. En arranque no hay lives, ni colaboraciones, ni 'responde a tus comentarios' como slot.
8. CERO RELLENO: no escribes introduccion, ni cierre motivacional, ni explicaciones de por que el video corto funciona. Solo el plan.
9. ESPANOL NEUTRO, directo, en tablas.
"""

WEEKLY_PLAN_OUTPUT_SPEC = """ENTREGA TU RESPUESTA EXACTAMENTE CON ESTAS SECCIONES EN MARKDOWN:

### 🎯 La pregunta que responde esta semana
Una sola frase: que vas a saber el domingo que hoy no sabes. Mas una linea con el dato o la hipotesis de la que sale.

### 🧱 Pilares de la semana (maximo 3)
Tabla: | Pilar | Que videos entran ahi | Por que este pilar (dato o hipotesis) | Cuantos slots se lleva |

### 📅 El calendario cerrado
Tabla con EXACTAMENTE una fila por slot del reparto que te di:
| # | Dia | Pilar | Tema concreto del video | Gancho del segundo 0 (frase exacta que se dice) | Dur. | Que se ve en pantalla | Variable que testea |

### 🎥 Plan de grabacion en lote
Que dias se graba y que slots salen de cada sesion, con el tiempo estimado de cada sesion. Agrupa por lo que comparte montaje (misma pantalla, misma ropa, mismo encuadre).

### 📈 Como se lee la semana el domingo
2 o 3 numeros con su meta, calculados desde las cifras reales de la cuenta. Y una regla de decision explicita: 'si pasa X, la semana que viene se hace Y; si no pasa, se descarta Z'.

### ⛔ Lo que esta semana NO se hace
2 o 3 cosas que el creador podria tener ganas de hacer y que esta semana estorban, con el motivo en media linea."""


# A partir de aqui ya no se escriben videos uno por uno: nadie inventa 20 ideas
# originales en una semana y sostenerlo. Los creadores de volumen disenan pocos
# formatos y corren variaciones. La entrega cambia de forma, no de exigencia.
UMBRAL_ALTO_VOLUMEN = 15

WEEKLY_PLAN_OUTPUT_SPEC_VOLUMEN = """ENTREGA TU RESPUESTA EXACTAMENTE CON ESTAS SECCIONES EN MARKDOWN:

### 🎯 La pregunta que responde esta semana
Una sola frase: que vas a saber el domingo que hoy no sabes. Mas una linea con el dato o la hipotesis de la que sale.

### 🧱 Los formatos de la semana (maximo 5)
A este volumen no se inventan tantas ideas distintas: se disenan pocos formatos y se repiten cambiando una cosa. Tabla:
| Formato | Que pasa en el video, paso a paso | Repeticiones esta semana | Que cambia en cada repeticion | Minutos que toma grabar uno |
La suma de la columna de repeticiones tiene que dar EXACTAMENTE el total de videos que te di.

### 🔁 El banco de variaciones
Por cada formato, la lista concreta de sus variaciones de esta semana: el caso, el error, el cliente, la cifra o la pregunta exacta que cambia. Tantas lineas como repeticiones tenga ese formato, numeradas. Cada linea tiene que ser grabable tal cual, sin pensar mas. Aqui es donde se gana o se pierde la semana: si una linea es vaga, ese video no se va a grabar.

### 🪝 Los ganchos del segundo 0
Por cada formato, la plantilla de apertura y 3 ejemplos ya escritos con variaciones reales de arriba. La plantilla tiene que admitir las demas variaciones sin sonar repetida.

### 📅 Reparto por dia
Tabla: | Dia | Cuantos videos | Que formatos salen ese dia |
Respeta exactamente el reparto que te di.

### 🎥 Plan de grabacion en lote
A este volumen esta es la seccion mas importante: si no se graba en lote, el volumen no se sostiene y la semana se cae el miercoles. Di cuantas sesiones hay, que dia, que formatos salen de cada una, cuantos videos por sesion y el tiempo estimado. Agrupa por lo que comparte montaje (misma pantalla, misma ropa, mismo encuadre).

### 📈 Como se lee la semana el domingo
2 o 3 numeros con su meta, calculados desde las cifras reales de la cuenta. Compara FORMATOS entre si, no videos sueltos: a este volumen el video individual no dice nada, el formato si. Cierra con una regla de decision: 'el formato que haga X se queda y se duplica; el que no, se elimina'.

### ⛔ Lo que esta semana NO se hace
2 o 3 cosas que estorban a este volumen (editar de mas, buscar el video perfecto, abrir un formato nuevo a mitad de semana), con el motivo en media linea."""


def _reparto_semanal(videos_por_semana: int) -> List[Tuple[str, int]]:
    """
    Reparte los videos de la semana entre los 7 dias lo mas parejo posible.
    El calculo es local y deterministico: la IA solo rellena el contenido de
    cada slot, no decide cuantos videos se publican ni cuando.
    """
    total = max(int(videos_por_semana or 1), 1)
    base, resto = divmod(total, 7)

    # Con menos de 7 videos se priorizan los dias de mayor trafico habitual.
    orden_prioridad = [0, 2, 4, 6, 1, 3, 5]  # lunes, miercoles, viernes, domingo, martes, jueves, sabado
    por_dia = [base] * 7
    for i in range(resto):
        por_dia[orden_prioridad[i]] += 1

    return [(DIAS_SEMANA[i], por_dia[i]) for i in range(7) if por_dia[i] > 0]


def build_weekly_plan_prompt(metrics: Optional[Dict[str, Any]] = None,
                             profile: Optional[Dict[str, Any]] = None,
                             extra_context: str = "",
                             goal: str = "mas_vistas") -> str:
    """Arma el prompt de la parrilla semanal con el reparto ya calculado."""
    datos = normalize_creator_profile(profile)
    reparto = _reparto_semanal(datos["videos_por_semana"])
    total = sum(c for _, c in reparto)

    objetivo = {
        "mas_vistas": "ALCANCE: que mas gente nueva vea los videos.",
        "mas_interaccion": "CONVERSION: mas comentarios, guardados y compartidos por vista.",
        "mas_seguidores": "SEGUIDORES: convertir espectadores sueltos en seguidores.",
        "vender": ("DISTRIBUCION: que el contenido traiga usuarios a lo que ofrece. Si vive de sus apps, "
                   "la semana tiene que mover usuarios de la app, no pedidos de servicios."),
    }.get(goal, "ALCANCE: mas vistas.")

    partes = [
        f"Arma la parrilla de la proxima semana para esta cuenta. OBJETIVO: {objetivo}",
        "",
        build_creator_profile_block(datos),
        "",
        f"REPARTO EXACTO DE LA SEMANA ({total} videos en total, no lo modifiques):",
    ]
    for dia, cantidad in reparto:
        partes.append(f"- {dia}: {cantidad} video(s)")

    partes += ["", build_metrics_digest(metrics)]

    if extra_context.strip():
        partes += ["", f"CONTEXTO QUE DA EL CREADOR: {extra_context.strip()}"]

    if total > UMBRAL_ALTO_VOLUMEN:
        partes += [
            "",
            f"FORMATO DE ENTREGA: ALTO VOLUMEN. Son {total} videos en la semana. NO escribas {total} filas "
            "distintas: nadie sostiene esa cantidad de ideas originales, y una lista asi no se graba. Disena "
            "como maximo 5 formatos repetibles y entrega el banco de variaciones concretas que los llena.",
            "",
            WEEKLY_PLAN_OUTPUT_SPEC_VOLUMEN,
        ]
    else:
        partes += [
            "",
            f"FORMATO DE ENTREGA: CALENDARIO DETALLADO. Son {total} videos en la semana, asi que entregas "
            "una fila por video, cada uno decidido.",
            "",
            WEEKLY_PLAN_OUTPUT_SPEC,
        ]

    return "\n".join(partes)


def generate_weekly_plan(
    metrics: Optional[Dict[str, Any]] = None,
    profile: Optional[Dict[str, Any]] = None,
    extra_context: str = "",
    goal: str = "mas_vistas",
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Convierte el perfil (y el analisis, si existe) en una semana cerrada de
    videos: un slot por video, con tema, gancho y variable a testear.
    """
    prompt = build_weekly_plan_prompt(metrics, profile=profile,
                                      extra_context=extra_context, goal=goal)
    return run_ai_task(prompt, WEEKLY_PLAN_SYSTEM_PROMPT, config=config)


# ==============================================================================
# DE LAS REDES AL PRODUCTO: CUANTA GENTE HACE FALTA PARA VIVIR DE LAS APPS
# ==============================================================================

MONETIZATION_SYSTEM_PROMPT = """Eres un asesor de distribucion para creadores que construyen sus propios productos (apps, herramientas, automatizaciones) y usan el video corto como canal para conseguir usuarios.
Tu trabajo es decirle a ESTE creador cuanta gente necesita para vivir de su producto, cuanto de eso ya alcanza con los numeros que tiene hoy, y que contenido mueve ese numero.

REGLAS DE ORO OBLIGATORIAS:
1. EL PRODUCTO ES EL NEGOCIO, EL CONTENIDO ES EL CANAL: respeta el modelo de negocio declarado en el perfil ('DE DONDE SALE EL DINERO'). Si el creador eligio vivir de sus apps, toda tu salida habla de usuarios, instalaciones, registros y suscripciones; no de clientes de servicios ni de vender su tiempo.
2. HAZ LA CUENTA AL REVES, CON NUMEROS: parte de la meta de ingresos y del precio para sacar cuantos usuarios que pagan hacen falta; de ahi cuantos registros, de ahi cuantas vistas al mes, y de ahi cuantos videos al mes al promedio real de vistas que te doy. Si falta un dato para cerrar la cuenta (precio, tasa de registro, tasa de pago), asume un valor, dilo explicitamente, marca que es un supuesto y di donde se mide el real.
3. RESPONDE SI DE VERDAD TIENE QUE 'HACERSE GRANDE': con las vistas de hoy calcula cuantos usuarios puede conseguir este mes sin crecer nada, y que porcentaje de la meta es eso. Si su alcance actual no alcanza, di el numero exacto de vistas mensuales que si alcanzaria y cuantos videos son a su promedio. No le dejes la idea de que primero hay que ser grande si los numeros dicen otra cosa, ni al contrario: la respuesta la dan las cifras.
4. VISTAS NO SON USUARIOS: un video puede tener muchas vistas y traer cero instalaciones. Di que tipo de video trae usuarios, cual solo trae vistas, y como se nota la diferencia en los datos.
5. UN SOLO PRODUCTO AL FRENTE: queda PROHIBIDO aconsejarle construir otra app. Si tiene varias, eliges UNA para empujar y dices con que criterio.
6. CERO TACTICAS DE CUENTA GRANDE: respeta la etapa del perfil. Nada de marcas, fondo de creadores ni ingresos por vistas; si entran, solo como 'todavia no, se desbloquea en tal numero'.
7. EL CONTENIDO NO SE VUELVE CATALOGO: si una propuesta obliga a que los videos suenen a anuncio de la app, descartala. El producto aparece porque se esta usando en pantalla resolviendo algo, no porque se promocione.
8. NADA DE 'MARCA PERSONAL' SUELTO: si hablas de marca personal, dices exactamente que tiene que quedar demostrado en video para que alguien instale y despues pague.
9. HONESTIDAD CON LOS NUMEROS: no prometas resultados. Si un paso del embudo no se puede saber con los datos que hay, di donde se mide (TikTok Studio, las analiticas de la app, el panel de la tienda).
10. ESPANOL NEUTRO, directo, en tablas. Cero relleno motivacional.
"""

MONETIZATION_OUTPUT_SPEC = """ENTREGA TU RESPUESTA EXACTAMENTE CON ESTAS SECCIONES EN MARKDOWN:

### 🧮 La cuenta al reves: cuanta gente necesitas
Tabla con la cadena completa, desde la meta de ingresos hacia atras. Una fila por paso, y en cada una de donde sale el numero (dato real, supuesto tuyo o dato que falta):
| Paso | Numero que necesitas | De donde sale ese numero |
Filas obligatorias: ingreso mensual objetivo / usuarios que pagan / registros o instalaciones / clics al enlace / vistas al mes / videos al mes a tu promedio actual de vistas.

### 📍 Donde estas hoy, sin crecer nada
Con las vistas reales que te di: cuantos usuarios puede conseguir este mes tal como esta, y que porcentaje de la meta es. Cierra con UNA linea directa que responda si necesita 'hacerse grande' o si le falta otra cosa, con la cifra que lo sostiene.

### 🧨 El paso que te rompe el embudo
De los pasos de arriba, cual esta mas lejos de su objetivo y cual es el mas barato de mover. Que se hace esta semana para moverlo, concreto.

### 📱 Que app empujar y por que
Una sola, con el criterio por el que la eliges. Y una frase que diga que problema resuelve **como lo diria el usuario**, no como lo diria el programador.

### 🎥 Que videos traen usuarios y cuales solo traen vistas
Tabla: | Tipo de video | Que queda demostrado | Por que alguien instalaria despues de verlo | Si solo trae vistas, dilo aqui |

### 🚪 El camino del video a la app
Los pasos exactos desde que alguien ve el video hasta que usa la app: donde va el enlace, que ve al llegar, cuantos pasos hay. Di en cual se pierde mas gente y como se acorta.

### 📊 Que medir (nada de metricas de vanidad)
2 o 3 numeros con su meta a 30 dias. Ninguno puede ser seguidores ni vistas totales.

### ⛔ Lo que NO deberia hacer todavia
Di explicitamente si construir otra app, cambiar de nicho o esperar a tener mas seguidores entran aqui, cada uno con el numero que lo desbloquearia."""


def build_monetization_prompt(metrics: Optional[Dict[str, Any]] = None,
                              profile: Optional[Dict[str, Any]] = None,
                              extra_context: str = "",
                              precio: str = "",
                              meta_mensual: str = "") -> str:
    """
    Arma el prompt de distribucion: perfil + producto + numeros reales. El
    precio y la meta de ingresos son los que permiten hacer la cuenta al reves
    (cuantos usuarios, cuantas vistas, cuantos videos).
    """
    datos = normalize_creator_profile(profile)

    partes = [
        "Dime cuanta gente necesita este creador para vivir de su producto, cuanto de eso ya alcanza con los "
        "numeros que tiene HOY, y que contenido mueve ese numero.",
        "",
        build_creator_profile_block(datos),
        "",
        build_metrics_digest(metrics),
        "",
        "DATOS PARA HACER LA CUENTA AL REVES:",
    ]

    if precio.strip():
        partes.append(f"- Precio / modelo de cobro del producto: {precio.strip()}")
    else:
        partes.append("- Precio: no declarado. Asume uno razonable para su tipo de producto, dilo claramente "
                      "como supuesto y avisa que confirmarlo cambia toda la cuenta.")

    if meta_mensual.strip():
        partes.append(f"- Ingreso mensual que quiere alcanzar: {meta_mensual.strip()}")
    else:
        partes.append("- Meta de ingresos: no declarada. Usa un objetivo de referencia para 'vivir de esto', "
                      "dilo como supuesto y haz la cuenta igual.")

    if not datos["oferta"]:
        partes += ["", "AVISO: el creador no declaro que producto tiene. Antes de hacer la cuenta, deduce 2 o "
                       "3 productos posibles a partir de su nicho y de lo que muestra en sus videos, elige el "
                       "mas probable para los calculos y marca que falta confirmarlo."]

    if extra_context.strip():
        partes += ["", f"CONTEXTO QUE DA EL CREADOR: {extra_context.strip()}"]

    partes += ["", MONETIZATION_OUTPUT_SPEC]
    return "\n".join(partes)


def generate_monetization_plan(
    metrics: Optional[Dict[str, Any]] = None,
    profile: Optional[Dict[str, Any]] = None,
    extra_context: str = "",
    precio: str = "",
    meta_mensual: str = "",
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Cuanta gente hace falta para vivir del producto y cuanto de eso ya alcanza
    hoy. Hace la cuenta al reves (ingreso -> usuarios -> registros -> vistas ->
    videos) para responder si de verdad hace falta "hacerse grande" primero.
    """
    prompt = build_monetization_prompt(metrics, profile=profile, extra_context=extra_context,
                                       precio=precio, meta_mensual=meta_mensual)
    return run_ai_task(prompt, MONETIZATION_SYSTEM_PROMPT, config=config)
