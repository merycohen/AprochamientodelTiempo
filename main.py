from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware  # Importar el control de acceso
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import base64  # Para simular la estructura del cifrado en el JSON de salida
from typing import List

app = FastAPI(title="Suite Aprovechamiento del Tiempo - API")

# Activar el puente de comunicación entre el puerto 5500 y el 8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite que tu mapa local se conecte sin bloqueos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1.1 Definimos el modelo de datos que espera recibir el Frontend
class SedeCreate(BaseModel):
    nombre: str = Field(..., example="Sede Principal Chacao")
    direccion: str = Field(..., example="Avenida Francisco de Miranda, Caracas")
    latitud: float = Field(..., ge=-90, le=90, example=10.4906)
    longitud: float = Field(..., ge=-180, le=180, example=-66.8536)
    radio_metros: int = Field(50, ge=30, le=150, example=50)

# 1.2 Creamos la ruta de conexión para el mapa del Administrador
@app.post("/api/sedes", status_code=status.HTTP_201_CREATED)
async def crear_sede(sede: SedeCreate):
    try:
        # A) Aquí se recibe el JSON del mapa interactivo
        print(f"Recibiendo datos desde el frontend para: {sede.nombre}")
        
        # B) Preparación para PostGIS: Transformamos lat/lng en formato WKT (Well-Known Text)
        # Recuerda que PostGIS lee primero Longitud y luego Latitud: POINT(Lng Lat)
        punto_postgis = f"POINT({sede.longitud} {sede.latitud})"
        
        # C) TODO: Aquí se conectará tu sesión de Base de Datos (SQLAlchemy) para hacer el INSERT:
        # sql = "INSERT INTO sedes (nombre, direccion, posicion, radio) VALUES (:nom, :dir, ST_GeomFromText(:pos, 4326), :rad)"
        
        return {
            "status": "success",
            "message": f"Sede '{sede.nombre}' registrada exitosamente con su geocerca.",
            "data_procesada": {
                "wkt_geometria": punto_postgis,
                "radio_aplicado": f"{sede.radio_metros} metros"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al procesar la geocerca: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


# 2.1 Definimos el modelo para el formulario del Paso 2
class UsuarioCreate(BaseModel):
    nombre_completo: str = Field(..., example="Pedro Pérez")
    correo: str = Field(..., example="pedro.perez@email.com")
    telefono: str = Field(..., example="+584121234567")
    rol: str = Field(..., example="Supervisor de Sede")
    sede_asignada: Optional[str] = Field(None, example="Sede Principal Chacao")
    autoriza_uso_datos: bool = Field(..., example=True) # El checkbox de privacidad

# 2.2 Creamos la ruta para el Onboarding y Cifrado
@app.post("/api/usuarios", status_code=status.HTTP_201_CREATED)
async def crear_usuario(usuario: UsuarioCreate):
    # Regla de Negocio Crítica: Si no aceptó los términos de privacidad, no procesamos nada
    if not usuario.autoriza_uso_datos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de Cumplimiento: Es obligatorio el consentimiento explícito del usuario para almacenar sus datos."
        )
    
    try:
        print(f"Procesando alta segura para: {usuario.nombre_completo}")
        
        # Simulación del Escudo de Ciberseguridad (AES-256 en producción)
        # Aquí convertimos el teléfono a una cadena protegida para que veas el efecto en la base de datos
        telefono_bytes = usuario.telefono.encode("utf-8")
        telefono_cifrado_simulado = base64.b64encode(telefono_bytes).decode("utf-8")
        
        # Simulación del Token Efímero de 24 horas para el enlace de contraseña
        token_activacion = "tok_efimero_" + base64.b32encode(telefono_bytes).decode("utf-8")[:10].lower()
        enlace_onboarding = f"https://suite-tiempo.com/activar?token={token_activacion}"
        
        return {
            "status": "success",
            "message": f"Usuario '{usuario.nombre_completo}' registrado. Invitación de Onboarding generada.",
            "seguridad_base_datos": {
                "telefono_guardado_en_bd": f"ENCRYPTED_DATA::{telefono_cifrado_simulado}",
                "privacidad_estatus": "Consentimiento firmado y registrado en auditoría"
            },
            "disparadores_notificacion": {
                "canal_correo": f"Enviando enlace expeirables a {usuario.correo}",
                "canal_whatsapp_sofy": f"SOFY despachando token a {usuario.telefono}",
                "enlace_generado": enlace_onboarding
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el proceso de Onboarding: {str(e)}"
        )

# 3.1 Definimos el modelo para un empleado individual dentro de la lista
class EmpleadoItem(BaseModel):
    nombre_completo: str = Field(..., example="Carlos Mendoza")
    correo: str = Field(..., example="carlos.mendoza@email.com")
    telefono: str = Field(..., example="+584149876543")
    sede_asignada: str = Field(..., example="Sede Principal Chacao")
    autoriza_uso_datos: bool = Field(..., example=True) # Checkbox individual de privacidad
    

# 3.2 Creamos la ruta para la carga masiva (recibe una lista de empleados)
@app.post("/api/empleados/cargar", status_code=status.HTTP_201_CREATED)
async def cargar_empleados_masivo(empleados: List[EmpleadoItem]):
    registrados_exito = 0
    errores_cumplimiento = 0
    lista_procesada_bd = []
    cola_mensajeria_sofy = []
    
    for emp in empleados:
        # Validación legal: si un empleado en la lista no tiene el consentimiento marcado, se rechaza ese registro
        if not emp.autoriza_uso_datos:
            errores_cumplimiento += 1
            continue
            
        # Cifrado de Privacidad en memoria (Simulación AES-256)
        tel_bytes = emp.telefono.encode("utf-8")
        tel_cifrado = base64.b64encode(tel_bytes).decode("utf-8")
        cor_bytes = emp.correo.encode("utf-8")
        correo_cifrado = base64.b64encode(cor_bytes).decode("utf-8")
        
        # Guardamos la estructura protegida que irá a la base de datos
        lista_procesada_bd.append({
            "nombre": emp.nombre_completo,
            "sede": emp.sede_asignada,
            "telefono_secure": f"ENCRYPTED_DATA::{tel_cifrado}",
            "correo_secure": f"ENCRYPTED_DATA::{correo_cifrado}"
        })
        
        # Preparamos la cola de mensajes interactivos que SOFY disparará por WhatsApp
        # Enmascaramos visualmente el correo en el mensaje de bienvenida para mayor privacidad (c***@email.com)
        partes_correo = emp.correo.split("@")
        correo_ofuscado = f"{partes_correo[0][0]}***@{partes_correo[1]}"
        
        cola_mensajeria_sofy.append({
            "destinatario_telefono": emp.telefono,
            "mensaje_onboarding": f"¡Hola {emp.nombre_completo}! Bienvenido a la Suite. Para activar tu cuenta y autorizar el uso seguro de tu teléfono y tu correo {correo_ofuscado} exclusivamente para el control de asistencias, por favor responde SÍ o presiona el botón Aceptar."
        })
        
        registrados_exito += 1

    return {
        "status": "completed",
        "resumen_operacion": {
            "total_recibidos": len(empleados),
            "cargados_exitosamente": registrados_exito,
            "rechazados_por_privacidad": errores_cumplimiento
        },
        "vista_previa_base_datos": lista_procesada_bd if registrados_exito > 0 else "Sin registros válidos",
        "accion_inmediata_sofy": {
            "estado_cola": f"Disparando {len(cola_mensajeria_sofy)} mensajes de Double Opt-In por WhatsApp...",
            "ejemplo_primer_envio": cola_mensajeria_sofy[0] if cola_mensajeria_sofy else None
        }
    }