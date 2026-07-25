import os
import requests
from dotenv import load_dotenv

# Cargar las variables desde el archivo .env
load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")

# 🚨 PON AQUÍ TU NÚMERO PERSONAL EN FORMATO INTERNACIONAL SIN EL "+"
# Ejemplo para Venezuela: "584121234567"
TELEFONO_DESTINO = "584166074603"


def probar_envio_whatsapp():
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": TELEFONO_DESTINO.replace("+", "").strip(),
        "type": "text",
        "text": {
            "preview_url": False,
            "body": "🚀 *Prueba Exitosa desde Aprovechamiento del Tiempo*\n\n¡Hola Mery! Tu servidor FastAPI acaba de conectarse correctamente con la API de Meta WhatsApp.",
        },
    }

    print("Enviando mensaje de prueba a Meta...")
    response = requests.post(url, json=payload, headers=headers)

    print(f"Estado HTTP: {response.status_code}")
    print(f"Respuesta de Meta: {response.json()}")


if __name__ == "__main__":
    probar_envio_whatsapp()