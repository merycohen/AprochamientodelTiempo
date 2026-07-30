# ==========================================
# 1. IMPORTACIONES
# ==========================================
import os
import sys
import logging
from typing import List, Optional
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from psycopg2.extras import RealDictCursor
import logging

# Importaciones locales
from conexion_db import get_db
from models import Sede, Asistencia, Empleado
from modulo_seguridad import cifrar_dato_sensible, descifrar_dato_sensible, generar_hash_busqueda, CLAVE_MAESTRA
from whatsapp_client import enviar_mensaje_whatsapp, enviar_respuesta_con_botones
from modulo_sofy import procesar_mensaje_sofy

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Carga de tokens desde el .env
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "mi_token_secreto")

print("\n" + "="*40)
print(f"DEBUG TOKEN CARGADO: '{WHATSAPP_VERIFY_TOKEN}'")
print("="*40 + "\n")

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# ==========================================
# 2. INICIALIZACIÓN DE LA APLICACIÓN
# ==========================================
app = FastAPI(
    title="Suite de Tiempo - MVP Asistencia",
    description="API de control de asistencia automatizada mediante WhatsApp, geolocalización y PostGIS.",
    version="1.0.0"
)

# Configurar carpetas auxiliares (plantillas HTML)
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router para panel administrativo
router = APIRouter(prefix="/admin", tags=["Panel de Administración"])

# ==========================================
# 4. Obtener la información más reciente del empleado usando su número de teléfono
# ==========================================
def obtener_stats_semanales(empleado_id: int, cursor) -> dict:
    """Calcula las estadísticas semanales acumuladas del empleado."""
    query = """
        SELECT 
            COALESCE(SUM(horas_trabajadas), 0) AS total_horas,
            COUNT(DISTINCT DATE(hora_llegada_servidor)) AS dias_asistidos,
            COUNT(DISTINCT sede_id) AS sedes_visitadas
        FROM asistencias
        WHERE empleado_id = %s 
          AND hora_llegada_servidor >= DATE_TRUNC('week', CURRENT_DATE);
    """
    cursor.execute(query, (empleado_id,))
    res = cursor.fetchone() or {}
    return {
        "total_horas": round(res.get("total_horas", 0), 2),
        "dias_asistidos": res.get("dias_asistidos", 0),
        "sedes_visitadas": res.get("sedes_visitadas", 0)
    }

def obtener_contexto_empleado(telefono: str, db: Session):
    query = text("""
        SELECT 
            e.nombre,
            s.nombre AS sede,
            a.hora_llegada_servidor AS ultimo_marcaje,
            a.tipo_registro,
            a.dentro_geocerca
        FROM empleados e
        LEFT JOIN sedes s ON e.sede_id = s.id
        LEFT JOIN asistencias a ON a.empleado_id = e.id
        WHERE e.telefono = :telefono
        ORDER BY a.id DESC 
        LIMIT 1;
    """)
    res = db.execute(query, {"telefono": telefono}).fetchone()
    
    if res:
        return {
            "nombre": res.nombre,
            "sede": res.sede or "Sede Principal",
            "ultimo_marcaje": str(res.ultimo_marcaje) if res.ultimo_marcaje else "Sin registros hoy",
            "tipo_registro": res.tipo_registro or "N/A",
            "dentro_geocerca": res.dentro_geocerca if res.dentro_geocerca is not None else True
        }
    return None

# ==========================================
# 4. ENDPOINTS ADMIN ROUTER & RUTAS PRINCIPALES
# ==========================================
@app.get("/admin", response_class=HTMLResponse, tags=["Panel Admin"])
async def ver_panel_admin(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin.html"
    )
@router.get("/api/marcajes-hoy")
def obtener_marcajes_mapa(db: Session = Depends(get_db)):
    # Trae los registros sin restringir estrictamente a CURRENT_DATE 
    # para que las pruebas guardadas se visualicen de inmediato en el mapa
    query = text("""
        SELECT 
            a.id,
            COALESCE(e.nombre, 'Empleado #' || a.empleado_id::text) AS empleado_nombre,
            COALESCE(s.nombre, 'Sede Principal') AS sede_nombre,
            a.tipo_registro,
            a.hora_origen_whatsapp,
            a.dentro_geocerca,
            ST_X(a.coordenada_marca::geometry) AS longitud,
            ST_Y(a.coordenada_marca::geometry) AS latitud,
            COALESCE(s.radio_metros, 50) AS radio_metros,
            CASE WHEN s.ubicacion IS NOT NULL THEN ST_X(s.ubicacion::geometry) ELSE NULL END AS sede_longitud,
            CASE WHEN s.ubicacion IS NOT NULL THEN ST_Y(s.ubicacion::geometry) ELSE NULL END AS sede_latitud
        FROM asistencias a
        LEFT JOIN empleados e ON a.empleado_id = e.id
        LEFT JOIN sedes s ON a.sede_id = s.id
        ORDER BY a.id DESC 
        LIMIT 100;
    """)
    result = db.execute(query).fetchall()
    return [dict(row._mapping) for row in result]

@router.get("/api/marcajes-hoy")
def obtener_marcajes_mapa(db: Session = Depends(get_db)):
    query = text("""
        SELECT 
            a.id,
            COALESCE(e.nombre, 'Empleado Desconocido') AS empleado_nombre,
            COALESCE(s.nombre, 'Sin Sede Asignada') AS sede_nombre,
            a.tipo_registro,
            a.hora_origen_whatsapp,
            a.dentro_geocerca,
            ST_X(a.coordenada_marca::geometry) AS longitud,
            ST_Y(a.coordenada_marca::geometry) AS latitud,
            COALESCE(s.radio_metros, 50) AS radio_metros,
            ST_X(s.ubicacion::geometry) AS sede_longitud,
            ST_Y(s.ubicacion::geometry) AS sede_latitud
        FROM asistencias a
        LEFT JOIN empleados e ON a.empleado_id = e.id
        LEFT JOIN sedes s ON a.sede_id = s.id
        ORDER BY a.id DESC 
        LIMIT 50;
    """)
    result = db.execute(query).fetchall()
    return [dict(row._mapping) for row in result]

@router.post("/api/justificaciones/{justificacion_id}/estatus")
def cambiar_estatus_justificacion(justificacion_id: int, datos: dict, db: Session = Depends(get_db)):
    nuevo_estatus = datos.get("estatus")
    if nuevo_estatus not in ["APROBADO", "RECHAZADO"]:
        raise HTTPException(status_code=400, detail="Estatus no válido")

    query = text("""
        UPDATE justificaciones 
        SET estatus = :estatus, fecha_revision = NOW() 
        WHERE id = :id 
        RETURNING id;
    """)
    res = db.execute(query, {"estatus": nuevo_estatus, "id": justificacion_id}).fetchone()
    db.commit()

    if not res:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    return {"status": "success", "mensaje": f"Solicitud {nuevo_estatus.lower()} exitosamente"}

# Incluir Router Admin
app.include_router(router)

# ==========================================
# 5. DIAGNÓSTICO Y ENTIDADES
# ==========================================
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
# 6. MODELOS PYDANTIC PARA WHATSAPP
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
# 7. WEBHOOK DE WHATSAPP
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

logger = logging.getLogger(__name__)

# Definición de menús repetitivos como constantes para limpiar el código
BOTONES_MENU_PRINCIPAL = [
    {"id": "btn_marcar_asistencia", "title": "📍 Registrar Marcaje"},
    {"id": "btn_reportar_permiso", "title": "📝 Reportar Permiso"},
    {"id": "btn_consultar_dudas", "title": "❓ Ayuda / Dudas"}
]

BOTONES_CIERRE = [
    {"id": "btn_volver_menu", "title": "🔙 Ir al Menú"},
    {"id": "btn_finalizar_sesion", "title": "👋 Finalizar"}
]

@app.post("/webhook", status_code=status.HTTP_200_OK, tags=["WhatsApp Webhook"])
async def recibir_evento_whatsapp(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                raw_messages = value.get("messages", [])
                if not raw_messages:
                    continue

                for msg_raw in raw_messages:
                    telefono_crudo = msg_raw.get("from")
                    tipo_msg = msg_raw.get("type")
                    
                    if not telefono_crudo:
                        continue

                    # Identificar Empleado por Hash
                    hash_entrante = generar_hash_busqueda(telefono_crudo)
                    empleado = db.query(Empleado).filter(Empleado.telefono_hash == hash_entrante).first()

                    if not empleado:
                        logger.warning(f"⚠️ Teléfono {telefono_crudo} no registrado en el sistema.")
                        continue

                    # ---------------------------------------------------------
                    # 1. BOTONES INTERACTIVOS
                    # ---------------------------------------------------------
                    if tipo_msg == "interactive":
                        button_reply = msg_raw.get("interactive", {}).get("button_reply", {})
                        btn_id = button_reply.get("id")

                        if btn_id in ["btn_menu_principal", "btn_volver_menu", "btn_cancelar_justificacion"]:
                            empleado.estado_wa = "IDLE"
                            empleado.borrador_justificacion = None
                            db.commit()

                            nombre = empleado.nombre.split()[0]
                            mensaje = f"¡Hola, {nombre}! 👋 ¿Qué deseas gestionar el día de hoy?"
                            enviar_respuesta_con_botones(telefono_crudo, mensaje, BOTONES_MENU_PRINCIPAL)

                        elif btn_id == "btn_marcar_asistencia":
                            mensaje = "📍 *Registro de Marcaje*\n\n¿Qué acción deseas registrar en este momento?"
                            botones = [
                                {"id": "btn_marca_entrada", "title": "🟢 Entrar"},
                                {"id": "btn_marca_salida", "title": "🔴 Salir"},
                                {"id": "btn_volver_menu", "title": "🔙 Cancelar"}
                            ]
                            enviar_respuesta_con_botones(telefono_crudo, mensaje, botones)

                        elif btn_id in ["btn_marca_entrada", "btn_marca_salida"]:
                            es_entrada = (btn_id == "btn_marca_entrada")
                            empleado.estado_wa = "ESPERANDO_MARCA_ENTRADA" if es_entrada else "ESPERANDO_MARCA_SALIDA"
                            db.commit()

                            accion_txt = "ENTRADA" if es_entrada else "SALIDA"
                            emoji = "🟢" if es_entrada else "🔴"
                            
                            mensaje = (
                                f"{emoji} *Marcaje de {accion_txt}*\n\n"
                                "Por favor, presiona el icono de adjuntar **(📎)** o **(+)**, "
                                "selecciona **Ubicación** ➔ **Enviar mi ubicación actual**.\n\n"
                                "_(Asegúrate de tener el GPS activado en tu teléfono)._"
                            )
                            botones = [{"id": "btn_volver_menu", "title": "🔙 Cancelar / Menú"}]
                            enviar_respuesta_con_botones(telefono_crudo, mensaje, botones)

                        elif btn_id == "btn_reportar_permiso":
                            empleado.estado_wa = "ESPERANDO_JUSTIFICACION"
                            db.commit()

                            mensaje = (
                                "📝 *Solicitud de Permiso / Justificación*\n\n"
                                "Por favor, envíame en **un solo mensaje (texto o nota de voz)** "
                                "los detalles de tu permiso indicando:\n\n"
                                "• **Fecha(s) y Horario:** *(Ej: Mañana todo el día, o de 8:00 AM a 12:00 PM)*\n"
                                "• **Motivo:** *(Ej: Cita médica, trámite personal, etc.)*"
                            )
                            botones = [{"id": "btn_volver_menu", "title": "🔙 Cancelar / Menú"}]
                            enviar_respuesta_con_botones(telefono_crudo, mensaje, botones)

                        elif btn_id == "btn_confirmar_justificacion":
                            borrador = empleado.borrador_justificacion or {}
                            tipo_just = borrador.get("tipo", "TEXTO")
                            contenido = borrador.get("contenido", "Sin detalle")

                            # Inserción limpia a través de la sesión activa de SQLAlchemy
                            db.execute(
                                text("""
                                    INSERT INTO justificaciones (empleado_id, tipo, contenido, estatus)
                                    VALUES (:empleado_id, :tipo, :contenido, 'PENDIENTE')
                                """),
                                {"empleado_id": empleado.id, "tipo": tipo_just, "contenido": contenido}
                            )

                            empleado.estado_wa = "IDLE"
                            empleado.borrador_justificacion = None
                            db.commit()

                            mensaje_exito = "✅ *¡Solicitud Enviada con Éxito!*\n\nLa ficha ha sido registrada y enviada a tu supervisor."
                            enviar_respuesta_con_botones(telefono_crudo, mensaje_exito, BOTONES_CIERRE)

                        elif btn_id == "btn_consultar_dudas":
                            mensaje = (
                                "❓ *Centro de Ayuda - Sofy*\n\n"
                                "1️⃣ **Marcaje:** Selecciona Entrar o Salir y comparte tu ubicación.\n"
                                "2️⃣ **Permisos:** Envía texto o nota de voz para solicitar justificativos.\n"
                                "3️⃣ **Ubicación:** Activa el GPS de tu celular para validar la sede."
                            )
                            enviar_respuesta_con_botones(telefono_crudo, mensaje, BOTONES_CIERRE)

                        elif btn_id == "btn_finalizar_sesion":
                            empleado.estado_wa = "IDLE"
                            db.commit()
                            mensaje = "¡Listo! Que tengas un excelente día. Escribe 'Hola' cuando quieras volver al menú. 👋"
                            enviar_mensaje_whatsapp(telefono_crudo, mensaje)

                    # ---------------------------------------------------------
                    # 2. RECEPCIÓN DE UBICACIÓN GPS
                    # ---------------------------------------------------------
                    elif tipo_msg == "location" and "location" in msg_raw:
                        loc_data = msg_raw.get("location", {})
                        lat, lon = loc_data.get("latitude"), loc_data.get("longitude")
                        timestamp_wa = int(msg_raw.get("timestamp", 0))

                        tipo_registro = "SALIDA" if empleado.estado_wa == "ESPERANDO_MARCA_SALIDA" else "ENTRADA"

                        # Pasar la sesión de SQLAlchemy si procesar_fichaje_inteligente lo admite,
                        # o utilizar db.connection() sin abrir un cursor directo inconsistente.
                        # Extrae la conexión nativa de psycopg2 desde SQLAlchemy:
                        # Obtenemos la conexión directa de DBAPI (psycopg2)
                        raw_conn = db.connection()._dbapi_connection

                        resultado = procesar_fichaje_inteligente(
                            empleado_id=empleado.id,
                            latitud=lat,
                            longitud=lon,
                            timestamp_wa=timestamp_wa,
                            tipo_registro=tipo_registro,
                            db_connection=raw_conn  # <--- Pasas la conexión nativa con soporte para .cursor()
                        )

                        empleado.estado_wa = "IDLE"
                        db.commit()

                        texto_confirmacion = resultado.get("mensaje", "Marcaje procesado.")
                        enviar_respuesta_con_botones(telefono_crudo, texto_confirmacion, BOTONES_CIERRE)

                    # ---------------------------------------------------------
                    # 3. TEXTO O AUDIO
                    # ---------------------------------------------------------
                    elif tipo_msg in ["text", "audio"]:
                        if empleado.estado_wa == "ESPERANDO_JUSTIFICACION":
                            contenido = msg_raw.get("text", {}).get("body") if tipo_msg == "text" else "Nota de voz recibida"
                            empleado.borrador_justificacion = {"tipo": tipo_msg.upper(), "contenido": contenido}
                            db.commit()

                            mensaje_confirmacion = (
                                f"📝 *Justificación Recibida*\n\n"
                                f"Tipo: {tipo_msg.upper()}\n"
                                f"Contenido: {contenido[:100]}...\n\n"
                                "¿Deseas enviar esta solicitud a tu supervisor?"
                            )
                            botones_confirmar = [
                                {"id": "btn_confirmar_justificacion", "title": "✅ Enviar Solicitud"},
                                {"id": "btn_cancelar_justificacion", "title": "❌ Cancelar"}
                            ]
                            enviar_respuesta_con_botones(telefono_crudo, mensaje_confirmacion, botones_confirmar)
                        else:
                            mensaje_default = (
                                "👋 Hola! Para registrar marcajes o permisos, utiliza el menú interactivo.\n"
                                "Escribe 'Hola' para ver las opciones disponibles."
                            )
                            enviar_respuesta_con_botones(telefono_crudo, mensaje_default, BOTONES_MENU_PRINCIPAL)
        return Response(content="EVENT_RECEIVED", status_code=status.HTTP_200_OK)

    except Exception as e:
        db.rollback()
        logger.error(f"🔥 [ERROR CRÍTICO EN WEBHOOK]: {str(e)}", exc_info=True)
        return Response(content="EVENT_RECEIVED", status_code=status.HTTP_200_OK)

# ==========================================
# 8. LÓGICA DE FICHAJE INTELIGENTE (POSTGIS)
# ==========================================
def procesar_fichaje_inteligente(
    empleado_id: int,
    latitud: float,
    longitud: float,
    timestamp_wa: int,
    tipo_registro: str = "ENTRADA",
    db_connection = None
):
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    hora_evento = datetime.fromtimestamp(timestamp_wa, tz=timezone.utc)

    if tipo_registro.upper() == "SALIDA":
        query_bloque_abierto = """
            SELECT a.id, a.sede_id, a.hora_origen_whatsapp, a.hora_llegada_servidor, s.nombre AS nombre_sede, s.radio_metros
            FROM asistencias a
            JOIN sedes s ON a.sede_id = s.id
            WHERE a.empleado_id = %s AND a.hora_salida IS NULL AND a.estatus != 'Rechazado'
            ORDER BY a.id DESC LIMIT 1;
        """
        cursor.execute(query_bloque_abierto, (empleado_id,))
        bloque_abierto = cursor.fetchone()

        if not bloque_abierto:
            cursor.close()
            return {
                "status": "error",
                "mensaje": "⚠️ *No tienes una entrada activa:* No registras un marcaje de entrada previo para poder cerrar la salida."
            }

        asistencia_id = bloque_abierto['id']
        sede_id = bloque_abierto['sede_id']
        nombre_sede = bloque_abierto['nombre_sede']
        
        hora_entrada = bloque_abierto.get("hora_origen_whatsapp") or bloque_abierto["hora_llegada_servidor"]

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

        if hora_entrada.tzinfo is None and hora_evento.tzinfo is not None:
            hora_entrada = hora_entrada.replace(tzinfo=timezone.utc)
            
        diferencia_segundos = max(0, (hora_evento - hora_entrada).total_seconds())
        horas_jornada = round(diferencia_segundos / 3600.0, 2)

        horas_enteras = int(diferencia_segundos // 3600)
        minutos_restantes = int((diferencia_segundos % 3600) // 60)
        tiempo_str = f"{horas_enteras}h {minutos_restantes}m" if horas_enteras > 0 else f"{minutos_restantes} min"

        query_update_salida = """
            UPDATE asistencias 
            SET 
                hora_salida = TO_TIMESTAMP(%s),
                coordenada_salida = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                dentro_geocerca_salida = %s,
                horas_trabajadas = %s
            WHERE id = %s;
        """
        cursor.execute(query_update_salida, (timestamp_wa, longitud, latitud, dentro_salida, horas_jornada, asistencia_id))
        
        stats = obtener_stats_semanales(empleado_id, cursor)
        db_connection.commit()
        cursor.close()

        mensaje_sofy = (
            f"👋 *Check-Out Exitoso en {nombre_sede}*\n\n"
            f"⏱️ *Tiempo de este bloque:* {tiempo_str} ({horas_jornada} hrs)\n"
            f"📍 *Ubicación verificada:* A {distancia_m}m de la sede.\n\n"
            f"📊 *Acumulado Semanal:*\n"
            f"• *Horas totales laboradas:* {stats['total_horas']} hrs\n"
            f"• *Días con registros:* {stats['dias_asistidos']}\n"
            f"• *Sedes visitadas:* {stats['sedes_visitadas']}\n\n"
            f"¡Excelente jornada!"
        )

        return {"tipo": "CHECK_OUT", "mensaje": mensaje_sofy}

    # Bloque default/fallback si es ENTRADA
    cursor.close()
    return {"tipo": "ENTRADA", "mensaje": "Marcaje de Entrada recibido correctamente."}

@app.get("/api/debug-asistencias", tags=["Diagnóstico"])
def debug_asistencias(db: Session = Depends(get_db)):
    query = text("""
        SELECT 
            id, 
            empleado_id, 
            sede_id, 
            tipo_registro, 
            hora_llegada_servidor,
            hora_origen_whatsapp,
            dentro_geocerca
        FROM asistencias 
        ORDER BY id DESC 
        LIMIT 10;
    """)
    result = db.execute(query).fetchall()
    return [dict(row._mapping) for row in result]