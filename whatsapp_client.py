import os
import requests

from dotenv import load_dotenv

# Cargar las variables del .env ANTES de que os.getenv las lea
load_dotenv()

def enviar_mensaje_whatsapp(telefono_destino: str, texto_mensaje: str):
    """
    Envía una notificación por WhatsApp Meta Graph API con logs de diagnóstico.
    """
    load_dotenv(override=True) # Forzar relectura del .env
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", None)
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", None)
    # ... enviar con requests ...
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


def enviar_saludo_interactivo_whatsapp(telefono: str, texto_saludo: str):
    """
    Envía el saludo matutino de Sofy acompañado de 3 botones interactivos
    para que el usuario interactúe a un solo toque.
    """
    
    load_dotenv(override=True)
    token = os.getenv("WHATSAPP_TOKEN")
    print(f"🔑 Token cargado: {token[:15]}...")
    phone_id = os.getenv("PHONE_NUMBER_ID")

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": texto_saludo
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "btn_marcar_asistencia",
                            "title": "📍 Registrar Marcaje"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "btn_reportar_permiso",
                            "title": "📝 Reportar Permiso"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "btn_consultar_dudas",
                            "title": "❓ Ayuda / Dudas"
                        }
                    }
                ]
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def enviar_respuesta_con_botones(telefono: str, texto_cuerpo: str, lista_botones: list):
    """
    Envía un mensaje interactivo con hasta 3 botones personalizados.
    lista_botones ejemplo: [
        {"id": "btn_menu", "title": "🔙 Menú Principal"},
        {"id": "btn_salir", "title": "👋 Finalizar"}
    ]
    """
    load_dotenv(override=True)
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("PHONE_NUMBER_ID")

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    buttons_payload = [
        {
            "type": "reply",
            "reply": {
                "id": btn["id"],
                "title": btn["title"]
            }
        } for btn in lista_botones[:3]  # Máximo 3 botones permitidos por Meta
    ]

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto_cuerpo},
            "action": {"buttons": buttons_payload}
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()
    