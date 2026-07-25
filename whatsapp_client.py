import requests
import os

# Intenta leer las variables de entorno; si no existen, asigna None
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", None)
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", None)

def enviar_mensaje_whatsapp(telefono_destino: str, texto_mensaje: str):
    """
    Envía una notificación por WhatsApp. Si no hay token de Meta configurado,
    imprime la simulación por consola.
    """
    # 🔴 SI NO HAY TOKEN, SIMULAR SALIDA POR CONSOLA
    if not WHATSAPP_TOKEN or WHATSAPP_TOKEN == "TU_TOKEN_DE_META_AQUI":
        print("\n" + "="*55)
        print(f"📱 [SIMULACIÓN WHATSAPP OUTBOUND] Para: {telefono_destino}")
        print(f"💬 Mensaje enviado:\n{texto_mensaje}")
        print("="*55 + "\n")
        return True

    # 🟢 SI HAY TOKEN REAL, ENVÍA A META GRAPH API
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telefono_destino.replace("+", ""),
        "type": "text",
        "text": {
            "preview_url": False,
            "body": texto_mensaje
        }
    }
 
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error al conectar con Meta API: {e}")
        return False