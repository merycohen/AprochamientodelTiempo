import os
import sys
import logging
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from conexion_db import get_db
from models import Sede, Asistencia, Empleado
from modulo_seguridad import cifrar_dato_sensible, descifrar_dato_sensible, generar_hash_busqueda, CLAVE_MAESTRA
from whatsapp_client import enviar_mensaje_whatsapp

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Carga de tokens desde el .env
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "mi_token_secreto")
# --- AGREGA ESTAS LÍNEAS TEMPORALES DE DIAGNÓSTICO ---
print("\n" + "="*40)
print(f"DEBUG TOKEN CARGADO: '{WHATSAPP_VERIFY_TOKEN}'")
print("="*40 + "\n")

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

app = FastAPI(
    title="Suite de Tiempo - MVP Asistencia",
    description="API de control de asistencia automatizada mediante WhatsApp, geolocalización y PostGIS.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINTS ---

@app.get("/", tags=["Diagnóstico"])
def ruta_raiz():
    return {
        "status": "online",
        "proyecto": "Aprovechamiento del Tiempo",
        "mensaje": "Servidor FastAPI corriendo con éxito"
    }

@app.get("/api/v1/sedes", tags=["Sedes"])
def listar_sedes(db: Session = Depends(get_db)):
    try:
        query = db.execute(text("SELECT id, nombre, direccion, ST_AsText(ubicacion) as coordenadas_wkt, radio_metros FROM sedes")).mappings().all()
        return {"total_sedes": len(query), "sedes": query}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar las sedes: {str(e)}"
        )

@app.post("/api/v1/sedes", status_code=status.HTTP_201_CREATED, tags=["Sedes"])
def registrar_sede(nombre: str, latitud: float, longitud: float, radio_metros: float = 50.0, direccion: str = None, db: Session = Depends(get_db)):
    try:
        punto_wkt = f"POINT({longitud} {latitud})"
        nueva_sede = Sede(
            nombre=nombre,
            direccion=direccion,
            ubicacion=text(f"ST_GeomFromText('{punto_wkt}', 4326)"),
            radio_metros=radio_metros
        )
        db.add(nueva_sede)
        db.commit()
        db.refresh(nueva_sede)
        return {
            "mensaje": "✅ Sede registrada con éxito",
            "sede_id": nueva_sede.id,
            "nombre": nueva_sede.nombre
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo registrar la sede: {str(e)}"
        )

@app.post("/api/v1/empleados", status_code=status.HTTP_201_CREATED, tags=["Empleados"])
def registrar_empleado(
    nombre: str,
    cedula_id: str,
    telefono: str,
    sede_id: int,
    db: Session = Depends(get_db)
):
    try:
        sede = db.query(Sede).filter(Sede.id == sede_id).first()
        if not sede:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"❌ La sede con ID {sede_id} no existe."
            )

        telefono_encriptado = cifrar_dato_sensible(telefono, CLAVE_MAESTRA)
        hash_busqueda = generar_hash_busqueda(telefono)

        nuevo_empleado = Empleado(
            nombre=nombre,
            cedula_id=cedula_id,
            telefono_cifrado=telefono_encriptado,
            telefono_hash=hash_busqueda,
            sede_id=sede_id,
            activo=True
        )

        db.add(nuevo_empleado)
        db.commit()
        db.refresh(nuevo_empleado)

        return {
            "mensaje": "✅ Empleado registrado exitosamente con teléfono cifrado",
            "empleado_id": nuevo_empleado.id,
            "nombre": nuevo_empleado.nombre,
            "sede_asignada": sede.nombre,
            "identificador_protegido": telefono_encriptado[:20] + "..."
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo registrar al empleado: {str(e)}"
        )

# ==========================================
# MODELOS PYDANTIC PARA WHATSAPP CLOUD API
# ==========================================

class LocationPayload(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None

class MessageMetadata(BaseModel):
    from_id: str = Field(..., alias="from")
    id: str
    timestamp: str
    type: str
    location: Optional[LocationPayload] = None

class ContactMetadata(BaseModel):
    profile: dict
    wa_id: str

class ValuePayload(BaseModel):
    messaging_product: str
    metadata: dict
    contacts: Optional[List[ContactMetadata]] = None
    messages: Optional[List[MessageMetadata]] = None

class ChangePayload(BaseModel):
    value: ValuePayload
    field: str

class EntryPayload(BaseModel):
    id: str
    changes: List[ChangePayload]

class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: List[EntryPayload]

# ==========================================
# ENDPOINTS DEL WEBHOOK DE WHATSAPP
# ==========================================

@app.get("/webhook", tags=["WhatsApp Webhook"])
async def verificar_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print(f"\n🔍 [WEBHOOK VERIFICACIÓN] Modo: {mode}, Token recibido: '{token}', Challenge: {challenge}")
    print(f"🔑 Token esperado (desde .env): '{WHATSAPP_VERIFY_TOKEN}'")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        print("--> ¡Validación de Meta realizada con éxito! 🎉")
        return Response(content=str(challenge), media_type="text/plain", status_code=200)
    else:
        print("--> ❌ Error: Los tokens no coinciden o el modo no es 'subscribe'.")
        raise HTTPException(status_code=403, detail="Error de validación: Token o modo incorrecto.")


@app.post("/webhook", status_code=status.HTTP_200_OK, tags=["WhatsApp Webhook"])
async def recibir_evento_whatsapp(payload: WhatsAppWebhookPayload, db: Session = Depends(get_db)):
    try:
        print("\n================ [PAYLOAD RECIBIDO] ================")
        print(payload.model_dump_json(indent=2))
        print("===================================================\n")
        
        for entry in payload.entry:
            for change in entry.changes:
                value = change.value
                
                if value.messages:
                    for msg in value.messages:
                        if msg.type == "location" and msg.location:
                            telefono_crudo = msg.from_id
                            lat = msg.location.latitude
                            lon = msg.location.longitude
                            
                            print(f"📍 Ubicación recibida de {telefono_crudo}: ({lat}, {lon})")
                            
                            hash_entrante = generar_hash_busqueda(telefono_crudo)
                            empleado = db.query(Empleado).filter(Empleado.telefono_hash == hash_entrante).first()
                            
                            if not empleado:
                                print(f"⚠️ Teléfono {telefono_crudo} NO está registrado.")
                                return {
                                    "status": "rejected", 
                                    "reason": "Empleado no registrado",
                                    "telefono_evaluado": telefono_crudo
                                }
                            
                            punto_empleado_wkt = f"POINT({lon} {lat})"
                            
                            sql_query = text("""
                                SELECT ST_DWithin(
                                    ubicacion, 
                                    ST_GeomFromText(:punto_wkt, 4326), 
                                    radio_metros, 
                                    true
                                ) AS dentro_de_geocerca
                                FROM sedes
                                WHERE id = :sede_id
                            """)
                            
                            es_valido = db.execute(
                                sql_query, 
                                {
                                    "punto_wkt": punto_empleado_wkt, 
                                    "sede_id": empleado.sede_id
                                }
                            ).scalar()
                            
                            nueva_asistencia = Asistencia(
                                empleado_id=empleado.id,
                                sede_id=empleado.sede_id,
                                coordenada_marca=text(f"ST_GeomFromText('{punto_empleado_wkt}', 4326)"),
                                dentro_geocerca=bool(es_valido)
                            )
                            
                            db.add(nueva_asistencia)
                            db.commit()
                            db.refresh(nueva_asistencia)
                            
                            if es_valido:
                                txt_alerta = (
                                    f"📍 *Asistencia Registrada Exitosamente*\n\n"
                                    f"Hola *{empleado.nombre}*, hemos confirmado tu ubicación en la sede.\n"
                                    f"⏱️ *Marca ID:* #{nueva_asistencia.id}\n"
                                    f"✅ *Estado:* DENTRO DE GEOCERCA"
                                )
                            else:
                                txt_alerta = (
                                    f"⚠️ *Alerta Fuera de Rango*\n\n"
                                    f"Hola *{empleado.nombre}*, la ubicación enviada se encuentra fuera de la sede.\n"
                                    f"⏱️ *Marca ID:* #{nueva_asistencia.id}\n"
                                    f"❌ *Estado:* FUERA DE RANGO"
                                )
                            
                            enviar_mensaje_whatsapp(telefono_crudo, txt_alerta)
                            
                            return {
                                "status": "processed",
                                "asistencia_id": nueva_asistencia.id,
                                "empleado": empleado.nombre,
                                "dentro_geocerca": bool(es_valido),
                                "mensaje": f"Marca registrada para {empleado.nombre}."
                            }

    except Exception as e:
        db.rollback()
        print(f"\n🔥 [ERROR CRÍTICO EN WEBHOOK]: {str(e)}\n")
        return {"status": "error", "detalle": str(e)}

    return {"status": "received"}