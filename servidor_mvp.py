from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import math

app = FastAPI(title="Suite Aprovechamiento del Tiempo - MVP Core")

# Coordenadas de la Sede de la Empresa Configurada por el Administrador (Ejemplo: Centro de Caracas)
SEDE_LAT = 10.4806
SEDE_LON = -66.9036
RADIO_TOLERANCIA_METROS = 50.0

# 1. Definición del objeto JSON exacto que nos envía Evolution API / Baileys desde WhatsApp
class WebhookWhatsApp(BaseModel):
    phone: str
    message_text: str
    latitude: float
    longitude: float
    messageTimestamp: int  # Unix timestamp enviado por el celular del usuario

def calcular_distancia_metros(lat1, lon1, lat2, lon2):
    """
    Fórmula matemática de Haversine. Es el equivalente exacto a la función 
    ST_DWithin de PostGIS que usaremos en la base de datos final.
    """
    R = 6371000  # Radio de la Tierra en metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 2. El "Enchufe" (Endpoint) de Entrada donde llega la marca de asistencia
@app.post("/webhook/asistencia")
def procesar_asistencia(payload: WebhookWhatsApp):
    # --- LÓGICA DE RESILIENCIA ANTE FALLAS DE INTERNET ---
    # Convertimos el timestamp original del celular (congelado cuando no había internet) a hora legible
    hora_real_envio = datetime.fromtimestamp(payload.messageTimestamp)
    hora_llegada_servidor = datetime.now()
    
    # --- LÓGICA DE GEOFENCING ---
    distancia = calcular_distancia_metros(payload.latitude, payload.longitude, SEDE_LAT, SEDE_LON)
    esta_dentro = distancia <= RADIO_TOLERANCIA_METROS

    print(f"\n📡 --- NUEVO EVENTO RECIBIDO DESDE WHATSAPP ---")
    print(f"📱 Teléfono: {payload.phone}")
    print(f"🕒 Hora en que el empleado le dio ENVIAR: {hora_real_envio.strftime('%I:%M:%S %p')}")
    print(f"🖥️ Hora en que LLEGÓ al servidor: {hora_llegada_servidor.strftime('%I:%M:%S %p')}")
    print(f"📍 Distancia calculada a la sede: {distancia:.2f} metros")

    if not esta_dentro:
        print("❌ RECHAZADO: Fuera de la geocerca.")
        raise HTTPException(
            status_code=400, 
            detail=f"Marca rechazada. Te encuentras a {distancia:.1f} metros de la sede. El límite son {RADIO_TOLERANCIA_METROS}m."
        )

    print("✅ VALIDADO: Dentro de la geocerca. Registrando marca...")
    
    # Aquí es donde el sistema guardaría los datos cifrados con AES-256 en PostgreSQL
    return {
        "status": "success",
        "mensaje": "Asistencia registrada exitosamente",
        "datos_registro": {
            "hora_computada": hora_real_envio.strftime('%Y-%m-%d %H:%M:%S'),
            "nota": "Procesado utilizando el timestamp original de origen (Resiliencia de Red activa)."
        }
    }