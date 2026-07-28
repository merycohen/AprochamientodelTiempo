import os
import requests

from dotenv import load_dotenv

# Cargar las variables del .env ANTES de que os.getenv las lea
load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", None)
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", None)

def enviar_mensaje_whatsapp(telefono_destino: str, texto_mensaje: str):
    """
    Envía una notificación por WhatsApp Meta Graph API con logs de diagnóstico.
    """
    # 1. Validar variables de entorno
    if not WHATSAPP_TOKEN or WHATSAPP_TOKEN == "TU_TOKEN_DE_META_AQUI":
        print("\n" + "="*55)
        print(f"⚠️ [AVISO]: WHATSAPP_TOKEN no está cargado o es por defecto.")
        print(f"📱 [SIMULACIÓN OUTBOUND] Para: {telefono_destino}")
        print(f"💬 Mensaje:\n{texto_mensaje}")
        print("="*55 + "\n")
        return False

    if not PHONE_NUMBER_ID:
        print("❌ [ERROR]: PHONE_NUMBER_ID no está configurado en las variables de entorno.")
        return False

    # 2. Preparar endpoint y cabeceras
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 3. Limpiar número destinatario
    telefono_limpio = str(telefono_destino).replace("+", "").strip()
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telefono_limpio,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": texto_mensaje
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n📤 [RESPUESTA META API] Status: {response.status_code}")
        print(f"📄 [RESPUESTA META API] Body: {response.text}\n")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error crítico al conectar con Meta API: {e}")
        return False