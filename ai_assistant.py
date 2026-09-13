import os
import json
import requests
from typing import Dict, Any, Optional, Tuple

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

def build_user_prompt(input_data: Dict[str, Any], style: str = "disruptive", target_duration: int = 30) -> str:
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

def call_gemini(api_key: str, prompt: str) -> str:
    """Llama a Google Gemini API usando REST (modelo gemini-2.5-flash o gemini-1.5-flash)."""
    models = ["gemini-2.5-flash", "gemini-1.5-flash"]
    last_err = ""
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048
            }
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            else:
                last_err = f"Error {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = str(e)
            
    raise RuntimeError(f"Fallo al contactar Gemini: {last_err}")

def call_openai_compatible(api_key: str, prompt: str, base_url: str, model: str) -> str:
    """Llama a OpenAI o Groq usando REST."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    resp = requests.post(base_url, headers=headers, json=payload, timeout=45)
    if resp.status_code == 200:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    else:
        raise RuntimeError(f"Error {resp.status_code}: {resp.text}")

def generate_video_script(
    input_data: Dict[str, Any],
    style: str = "disruptive",
    target_duration: int = 30,
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Funcion principal para generar un guion con microganchos.
    Detecta automaticamente que proveedor de IA esta disponible.
    """
    provider, api_key = detect_ai_provider(config)
    
    if not provider or not api_key:
        return {
            "success": False,
            "provider": None,
            "message": "No hay ninguna API Key de IA configurada (GEMINI_API_KEY, GROQ_API_KEY u OPENAI_API_KEY).",
            "content": None
        }
        
    prompt = build_user_prompt(input_data, style=style, target_duration=target_duration)
    
    try:
        if provider == "gemini":
            content = call_gemini(api_key, prompt)
        elif provider == "groq":
            content = call_openai_compatible(
                api_key=api_key,
                prompt=prompt,
                base_url="https://api.groq.com/openai/v1/chat/completions",
                model="llama-3.3-70b-versatile"
            )
        elif provider == "openai":
            content = call_openai_compatible(
                api_key=api_key,
                prompt=prompt,
                base_url="https://api.openai.com/v1/chat/completions",
                model="gpt-4o-mini"
            )
        else:
            return {"success": False, "provider": provider, "message": f"Proveedor no reconocido: {provider}"}
            
        return {
            "success": True,
            "provider": provider,
            "content": content
        }
    except Exception as e:
        return {
            "success": False,
            "provider": provider,
            "message": f"Error al generar con {provider}: {str(e)}",
            "content": None
        }
