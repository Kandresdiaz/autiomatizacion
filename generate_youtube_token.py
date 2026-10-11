"""
Generador de YOUTUBE_REFRESH_TOKEN
==================================

Usalo cuando YouTube falle con deleted_client, invalid_client o invalid_grant.

Pasos previos en Google Cloud Console (https://console.cloud.google.com):
  1. Crea (o selecciona) un proyecto.
  2. APIs y servicios > Biblioteca > activa "YouTube Data API v3".
  3. APIs y servicios > Pantalla de consentimiento OAuth:
       - Tipo "Externo", publica la app o agregate como usuario de prueba.
       - IMPORTANTE: si la dejas en modo "Testing", el refresh token caduca a los 7 dias.
         Pulsa "Publicar app" para que no caduque.
  4. APIs y servicios > Credenciales > Crear credenciales > ID de cliente de OAuth
       - Tipo de aplicacion: "Aplicacion de escritorio" (Desktop app).
       - Copia el Client ID y el Client Secret.

Luego ejecuta:
    python generate_youtube_token.py

Se abrira el navegador, inicias sesion con la cuenta DUENA del canal de YouTube,
y el script imprime (y opcionalmente guarda en .env) el refresh token.
"""

import os
import sys

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
ENV_FILE = ".env"


def leer_env() -> dict:
    datos = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    k, v = linea.split("=", 1)
                    datos[k.strip()] = v.strip().strip("'\"")
    return datos


def guardar_en_env(valores: dict):
    """Actualiza las claves indicadas en .env sin tocar el resto del archivo."""
    lineas = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lineas = f.read().splitlines()

    pendientes = dict(valores)
    for i, linea in enumerate(lineas):
        if "=" in linea and not linea.strip().startswith("#"):
            clave = linea.split("=", 1)[0].strip()
            if clave in pendientes:
                lineas[i] = f"{clave}={pendientes.pop(clave)}"
    for clave, valor in pendientes.items():
        lineas.append(f"{clave}={valor}")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def main() -> int:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Falta google-auth-oauthlib. Ejecuta:  pip install -r requirements.txt")
        return 1

    env = leer_env()

    # Opcion A: client_secret.json descargado de Google Cloud Console.
    archivo_json = next(
        (n for n in ("client_secret.json", "credentials.json") if os.path.exists(n)),
        None,
    )

    if archivo_json:
        print(f"[1/3] Usando {archivo_json}")
        flow = InstalledAppFlow.from_client_secrets_file(archivo_json, SCOPES)
    else:
        # Opcion B: pegar Client ID y Secret a mano (o tomarlos del .env).
        client_id = (env.get("YOUTUBE_CLIENT_ID") or "").strip()
        client_secret = (env.get("YOUTUBE_CLIENT_SECRET") or "").strip()

        print("[1/3] No encontre client_secret.json.")
        if client_id:
            print(f"      En .env hay YOUTUBE_CLIENT_ID = ...{client_id[-24:]}")
            usar = input("      Usar ese Client ID? [S/n]: ").strip().lower()
            if usar in ("n", "no"):
                client_id = client_secret = ""

        if not client_id:
            client_id = input("      Pega el Client ID nuevo: ").strip()
        if not client_secret:
            client_secret = input("      Pega el Client Secret nuevo: ").strip()

        if not client_id or not client_secret:
            print("ERROR: hacen falta Client ID y Client Secret.")
            return 1

        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            },
            SCOPES,
        )

    print("[2/3] Abriendo el navegador. Inicia sesion con la cuenta DUENA del canal de YouTube.")
    print("      (Si ves 'Google no ha verificado esta app' > Configuracion avanzada > Continuar)")
    try:
        creds = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="consent",
            open_browser=True,
        )
    except Exception as e:
        print(f"ERROR en el flujo OAuth: {e}")
        print("Si el navegador no abrio, copia la URL que se imprimio arriba y pegala a mano.")
        return 1

    if not creds.refresh_token:
        print("ERROR: Google no devolvio refresh_token. Vuelve a ejecutar el script "
              "(se fuerza prompt=consent) o revoca el acceso en "
              "https://myaccount.google.com/permissions y reintenta.")
        return 1

    # Verificacion real: que el token pueda hablar con la API.
    print("[3/3] Verificando contra la YouTube Data API...")
    try:
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        canal = yt.channels().list(part="snippet", mine=True).execute()
        items = canal.get("items", [])
        if items:
            print(f"      OK. Canal autorizado: {items[0]['snippet']['title']}")
        else:
            print("      ATENCION: la cuenta no tiene canal de YouTube. Crea el canal primero.")
    except Exception as e:
        # El scope youtube.upload no siempre permite leer channels; no es bloqueante.
        print(f"      Aviso: no pude leer el canal ({str(e)[:120]}). El token de subida igual sirve.")

    print("\n" + "=" * 70)
    print("YOUTUBE_CLIENT_ID     =", flow.client_config["client_id"])
    print("YOUTUBE_CLIENT_SECRET =", flow.client_config["client_secret"])
    print("YOUTUBE_REFRESH_TOKEN =", creds.refresh_token)
    print("=" * 70)

    resp = input("\nGuardar estos 3 valores en .env ahora? [S/n]: ").strip().lower()
    if resp in ("", "s", "si", "y", "yes"):
        guardar_en_env({
            "YOUTUBE_CLIENT_ID": flow.client_config["client_id"],
            "YOUTUBE_CLIENT_SECRET": flow.client_config["client_secret"],
            "YOUTUBE_REFRESH_TOKEN": creds.refresh_token,
        })
        print(f"Guardado en {ENV_FILE}.")
    else:
        print("No se guardo nada. Copia los valores a mano.")

    print("\nRecuerda actualizar tambien los Secrets de GitHub Actions:")
    print("  Settings > Secrets and variables > Actions >")
    print("  YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
