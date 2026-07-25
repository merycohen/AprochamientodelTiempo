import requests
import json

URL_WEBHOOK = "http://127.0.0.1:8005/webhook"

# ⚠️ Importante: Usa el teléfono EXACTO con el que registraste al empleado en Swagger
TELEFONO_EMPLEADO = "4166074603"

LATITUD_SIMULADA = 100
LONGITUD_SIMULADA = 100

payload_whatsapp = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WHATSAPP_ENTRY_ID",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550555555",
                            "phone_number_id": "123456789"
                        },
                        "contacts": [
                            {
                                "profile": {"name": "Empleado Prueba"},
                                "wa_id": TELEFONO_EMPLEADO.replace("+", "")
                            }
                        ],
                        "messages": [
                            {
                                "from": TELEFONO_EMPLEADO,
                                "id": "wamid.HBgLMTIzNDU2Nzg5MzA=",
                                "timestamp": "1721584800",
                                "type": "location",
                                "location": {
                                    "latitude": LATITUD_SIMULADA,
                                    "longitude": LONGITUD_SIMULADA,
                                    "name": "Ubicación Compartida",
                                    "address": "Sede Principal"
                                }
                            }
                        ]
                    },
                    "field": "messages"
                }
            ]
        }
    ]
}

print("🚀 Enviando simulación de mensaje de ubicación desde WhatsApp...")

try:
    response = requests.post(URL_WEBHOOK, json=payload_whatsapp)
    print(f"\n📡 Código de respuesta HTTP: {response.status_code}")
    print("📊 Respuesta JSON del servidor:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ Error al conectar con el servidor: {e}")