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



from fastapi import Request, status, Response, Depends
from sqlalchemy.orm import Session

# Mantén tus imports locales según tu proyecto:
# from database import get_db
# from models import Empleado
# from utils import generar_hash_busqueda, procesar_fichaje_inteligente, enviar_mensaje_whatsapp

@app.post("/webhook", status_code=status.HTTP_200_OK, tags=["WhatsApp Webhook"])
async def recibir_evento_whatsapp(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        
        print("\n================ [PAYLOAD RECIBIDO] ================")
        print(data)
        print("===================================================\n")
        
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                raw_messages = value.get("messages", [])
                if not raw_messages:
                    continue

                for msg_raw in raw_messages:
                    # Extraer teléfono del remitente de forma directa
                    telefono_crudo = msg_raw.get("from")
                    tipo_msg = msg_raw.get("type")
                    
                    if not telefono_crudo:
                        continue

                    print(f"📩 Mensaje recibido de tipo '{tipo_msg}' desde teléfono: {telefono_crudo}")

                    # -------------------------------------------------------------
                    # 1. UBICACIÓN (Check-In / Check-Out con Geocerca)
                    # -------------------------------------------------------------
                    if tipo_msg == "location" and "location" in msg_raw:
                        loc_data = msg_raw.get("location", {})
                        lat = loc_data.get("latitude")
                        lon = loc_data.get("longitude")
                        timestamp_wa = int(msg_raw.get("timestamp", 0))
                        
                        hash_entrante = generar_hash_busqueda(telefono_crudo)
                        empleado = db.query(Empleado).filter(Empleado.telefono_hash == hash_entrante).first()
                        
                        if not empleado:
                            print(f"⚠️ Empleado no registrado para teléfono {telefono_crudo}")
                            continue

                        db_raw = db.connection().connection
                        resultado = procesar_fichaje_inteligente(
                            empleado_id=empleado.id,
                            latitud=lat,
                            longitud=lon,
                            timestamp_wa=timestamp_wa,
                            db_connection=db_raw
                        )
                        
                        if resultado.get("mensaje"):
                            enviar_mensaje_whatsapp(telefono_crudo, resultado["mensaje"])

                    # -------------------------------------------------------------
                    # 2. TEXTO O AUDIO (JUSTIFICACIONES)
                    # -------------------------------------------------------------
                    elif tipo_msg in ["text", "audio"]:
                        print(f"📝 Procesando justificación para teléfono {telefono_crudo}...")
                        
                        hash_entrante = generar_hash_busqueda(telefono_crudo)
                        empleado = db.query(Empleado).filter(Empleado.telefono_hash == hash_entrante).first()

                        if not empleado:
                            print("⚠️ Empleado no encontrado para el hash registrado.")
                            continue

                        tipo_just = "TEXTO"
                        contenido_justificacion = ""

                        # --- CASO A: MENSAJE DE TEXTO ---
                        if tipo_msg == "text":
                            tipo_just = "TEXTO"
                            text_data = msg_raw.get("text", {})
                            if isinstance(text_data, dict):
                                contenido_justificacion = text_data.get("body", "Sin texto en body")
                            else:
                                contenido_justificacion = str(text_data)

                        # --- CASO B: NOTA DE VOZ / AUDIO ---
                        elif tipo_msg == "audio":
                            tipo_just = "AUDIO"
                            audio_data = msg_raw.get("audio", {})
                            audio_id = audio_data.get("id", "desconocido") if isinstance(audio_data, dict) else "desconocido"
                            contenido_justificacion = f"Audio Media ID: {audio_id}"

                        print(f"💾 Guardando en DB: Empleado ID={empleado.id}, Tipo={tipo_just}, Contenido='{contenido_justificacion}'")

                        db_raw = db.connection().connection
                        cursor = db_raw.cursor()
                        
                        cursor.execute("""
                            INSERT INTO justificaciones (empleado_id, tipo, contenido, estatus)
                            VALUES (%s, %s, %s, 'PENDIENTE');
                        """, (empleado.id, tipo_just, contenido_justificacion))
                        
                        db_raw.commit()
                        cursor.close()

                        mensaje_sofy = (
                            "📝 *Justificación Recibida*\n\n"
                            "Tu explicación ha sido registrada y enviada a tu supervisor para su revisión.\n\n"
                            "¡Muchas gracias!"
                        )
                        enviar_mensaje_whatsapp(telefono_crudo, mensaje_sofy)

        # Responder a Meta inmediatamente
        return Response(content="EVENT_RECEIVED", status_code=status.HTTP_200_OK)

    except Exception as e:
        db.rollback()
        print(f"\n🔥 [ERROR CRÍTICO EN WEBHOOK]: {str(e)}\n")
        return Response(content="EVENT_RECEIVED", status_code=status.HTTP_200_OK)

from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor

def procesar_fichaje_inteligente(
    empleado_id: int,
    latitud: float,
    longitud: float,
    timestamp_wa: int,
    db_connection
):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    # Convertimos a datetime en UTC (o timezone local) para evitar conflictos de restar horas
    hora_evento = datetime.fromtimestamp(timestamp_wa, tz=timezone.utc)

    # 1. Buscar si el empleado tiene alguna entrada ABIERTA (incluimos hora_origen_whatsapp y hora_llegada_servidor)
    query_bloque_abierto = """
        SELECT a.id, a.sede_id, a.hora_origen_whatsapp, a.hora_llegada_servidor, s.nombre AS nombre_sede, s.radio_metros
        FROM asistencias a
        JOIN sedes s ON a.sede_id = s.id
        WHERE a.empleado_id = %s AND a.hora_salida IS NULL AND a.estatus != 'Rechazado'
        ORDER BY a.id DESC LIMIT 1;
    """
    cursor.execute(query_bloque_abierto, (empleado_id,))
    bloque_abierto = cursor.fetchone()

    # ==========================================
    # CASO A: CHECK-OUT (Cerrar bloque activo)
    # ==========================================
    if bloque_abierto:
        asistencia_id = bloque_abierto['id']
        sede_id = bloque_abierto['sede_id']
        nombre_sede = bloque_abierto['nombre_sede']
        
        # Usamos hora_origen_whatsapp si existe, o en su defecto hora_llegada_servidor
        hora_entrada = bloque_abierto.get("hora_origen_whatsapp") or bloque_abierto["hora_llegada_servidor"]

        # Validar geocerca de salida en PostGIS
        query_geocerca_salida = """
            SELECT 
                ST_Distance(
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
                    s.ubicacion::geography
                ) <= s.radio_metros AS esta_dentro,
                ROUND(ST_Distance(
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
                    s.ubicacion::geography
                )::numeric, 2) AS distancia
            FROM sedes s WHERE s.id = %s;
        """
        cursor.execute(query_geocerca_salida, (longitud, latitud, longitud, latitud, sede_id))
        eval_salida = cursor.fetchone()

        dentro_salida = eval_salida['esta_dentro']
        distancia_m = eval_salida['distancia']

        if not dentro_salida:
            cursor.close()
            return {
                "status": "rejected",
                "mensaje": f"❌ *Salida no permitida:* Te encuentras a {distancia_m}m de la sede '{nombre_sede}'. Debes estar dentro del radio de la sede para cerrar tu jornada."
            }

        # Asegurar compatibilidad de timezones para el cálculo
        if hora_entrada.tzinfo is None and hora_evento.tzinfo is not None:
            hora_entrada = hora_entrada.replace(tzinfo=timezone.utc)
            
        # Calcular duración exacta de la jornada
        diferencia_segundos = max(0, (hora_evento - hora_entrada).total_seconds())
        horas_jornada = round(diferencia_segundos / 3600.0, 2)

        # Formato legible para el usuario (ej: "2h 15m" o "45 min")
        horas_enteras = int(diferencia_segundos // 3600)
        minutos_restantes = int((diferencia_segundos % 3600) // 60)
        if horas_enteras > 0:
            tiempo_str = f"{horas_enteras}h {minutos_restantes}m"
        else:
            tiempo_str = f"{minutos_restantes} min"

        # Actualizar la salida Y guardar las horas trabajadas en la DB
        query_update_salida = """
            UPDATE asistencias 
            SET 
                hora_salida = %s,
                coordenada_salida = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                dentro_geocerca_salida = %s,
                horas_trabajadas = %s
            WHERE id = %s;
        """
        cursor.execute(query_update_salida, (hora_evento, longitud, latitud, dentro_salida, horas_jornada, asistencia_id))
        
        # Obtener estadísticas semanales acumuladas
        stats = obtener_stats_semanales(empleado_id, cursor)
        db_connection.commit()
        cursor.close()

        mensaje_sofy = (
            f"👋 *Check-Out Exitoso en {nombre_sede}*\n\n"
            f"⏱️ *Tiempo de este bloque:* {tiempo_str} ({horas_jornada} hrs)\n"
            f"📍 *Ubicación verificada:* A {distancia_m}m de la sede.\n\n"
            f"📊 *Acumulado Semanal (Semana en curso):*\n"
            f"• *Horas totales laboradas:* {stats['total_horas']} hrs\n"
            f"• *Días con registros:* {stats['dias_asistidos']}\n"
            f"• *Sedes visitadas:* {stats['sedes_visitadas']}\n\n"
            f"¡Excelente jornada!"
        )

        return {"tipo": "CHECK_OUT", "mensaje": mensaje_sofy}

    # ==========================================
    # CASO B: CHECK-IN (Abrir nuevo bloque)
    # ==========================================
    else:
        # Identificar la sede más cercana
        query_sede_cercana = """
            SELECT id, nombre, radio_metros,
                   ST_Distance(
                       ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
                       ubicacion::geography
                   ) AS distancia
            FROM sedes
            ORDER BY distancia ASC LIMIT 1;
        """
        cursor.execute(query_sede_cercana, (longitud, latitud))
        sede_cercana = cursor.fetchone()

        if not sede_cercana:
            cursor.close()
            return {"status": "error", "mensaje": "⚠️ No hay sedes configuradas en el sistema."}

        dentro_entrada = sede_cercana['distancia'] <= sede_cercana['radio_metros']

        if not dentro_entrada:
            cursor.close()
            return {
                "status": "rejected",
                "mensaje": f"❌ *Entrada no válida:* Te encuentras a {round(sede_cercana['distancia'], 2)}m de la sede '{sede_cercana['nombre']}'. Fuera de la geocerca de 50m."
            }

        # Registrar la entrada
        query_insert_entrada = """
            INSERT INTO asistencias (
                empleado_id, sede_id, hora_origen_whatsapp, hora_llegada_servidor, 
                coordenada_marca, dentro_geocerca, estatus
            ) VALUES (
                %s, %s, %s, NOW(), 
                ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, 'Aprobado'
            ) RETURNING id;
        """
        cursor.execute(query_insert_entrada, (
            empleado_id, sede_cercana['id'], hora_evento, longitud, latitud, dentro_entrada
        ))
        
        db_connection.commit()
        cursor.close()

        mensaje_sofy = (
            f"✨ *Check-In Registrado en {sede_cercana['nombre']}*\n\n"
            f"📅 *Hora de llegada:* {hora_evento.strftime('%I:%M %p')}\n"
            f"📍 *Geocerca:* Validada (Dentro del perímetro)\n\n"
            f"¡Que tengas un turno muy productivo!"
        )

        return {"tipo": "CHECK_IN", "mensaje": mensaje_sofy}


def obtener_stats_semanales(empleado_id: int, cursor):
    """Consulta auxiliar para calcular el acumulado semanal de horas y días."""
    query = """
        WITH bloques_semana AS (
            SELECT 
                hora_llegada_servidor::date AS fecha,
                sede_id,
                EXTRACT(EPOCH FROM (COALESCE(hora_salida, NOW()) - hora_llegada_servidor))/3600.0 AS horas
            FROM asistencias
            WHERE empleado_id = %s 
              AND hora_llegada_servidor >= DATE_TRUNC('week', CURRENT_DATE)
              AND estatus IN ('Aprobado', 'Ajustado_Supervisor')
        )
        SELECT 
            COUNT(DISTINCT fecha) AS dias_asistidos,
            COUNT(DISTINCT sede_id) AS sedes_visitadas,
            ROUND(COALESCE(SUM(horas), 0)::numeric, 2) AS total_horas
        FROM bloques_semana;
    """
    cursor.execute(query, (empleado_id,))
    return cursor.fetchone()