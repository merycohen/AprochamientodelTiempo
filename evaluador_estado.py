import os
import random
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(override=True)

# Importar la función desde tu módulo existente de WhatsApp
from whatsapp_client import enviar_saludo_interactivo_whatsapp  # <--- Cambia 'tu_modulo_whatsapp' por el nombre real de tu archivo .py

# Lista de saludos dinámicos para días normales (para variar la conversación diario)
SALUDOS_DIARIOS = [
    "¡Hola, {nombre}! ☀️ Espero que tengas un día excelente y súper productivo.",
    "¡Buenos días, {nombre}! 👋 Listos para iniciar la jornada con la mejor energía.",
    "¡Feliz día, {nombre}! ✨ Recuerda que estoy aquí para ayudarte con tu registro de hoy.",
    "¡Hola, {nombre}! 🚀 Que tengas una jornada extraordinaria."
]

def obtener_conexion():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=RealDictCursor
    )

def evaluar_estado_empleado_hoy(empleado_id: int, fecha_hoy: date = None) -> dict:
    """
    Determina la condición operativa del empleado para la fecha dada (por defecto hoy).
    Retorna un diccionario con el estado, si requiere fichaje y el saludo preparado.
    """
    if not fecha_hoy:
        fecha_hoy = date.today()

    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        # 1. Consultar datos básicos del empleado
        cursor.execute("SELECT id, nombre, fecha_nacimiento, activo FROM empleados WHERE id = %s", (empleado_id,))
        empleado = cursor.fetchone()

        if not empleado or not empleado['activo']:
            return {"estado": "INACTIVO", "requiere_fichaje": False, "mensaje": None}

        nombre = empleado['nombre'].split()[0]  # Primer nombre para trato cercano

        # 2. Revisar si hoy es FERIADO o DÍA NO LABORABLE (Calendario Institucional)
        cursor.execute("SELECT descripcion, es_laborable, mensaje_saludo FROM calendario_institucional WHERE fecha = %s", (fecha_hoy,))
        feriado = cursor.fetchone()

        if feriado and not feriado['es_laborable']:
            mensaje = feriado['mensaje_saludo'] or f"¡Hola {nombre}! Hoy es {feriado['descripcion']}. ¡Disfruta tu día de descanso!"
            return {
                "estado": "FERIADO",
                "descripcion": feriado['descripcion'],
                "requiere_fichaje": False,
                "mensaje": mensaje
            }

        # 3. Revisar NOVEDADES del empleado (Vacaciones, Reposos, Permisos)
        cursor.execute("""
            SELECT tipo_novedad, motivo_detalle 
            FROM novedades_empleado 
            WHERE empleado_id = %s 
              AND %s BETWEEN fecha_inicio AND fecha_fin
              AND estatus = 'APROBADO'
        """, (empleado_id, fecha_hoy))
        novedad = cursor.fetchone()

        if novedad:
            tipo = novedad['tipo_novedad']
            if tipo == 'VACACIONES':
                mensaje = f"¡Hola {nombre}! 🏖️ Te recordamos que estás en tu periodo de vacaciones. ¡Sigue disfrutando tu descanso!"
            elif tipo == 'REPOSO_MEDICO':
                mensaje = f"¡Hola {nombre}! 🏥 Esperamos que te recuperes pronto. Estás registrado en reposo médico para el día de hoy."
            else:
                mensaje = f"¡Hola {nombre}! Tienes registrado un evento de {tipo.lower()} para hoy."

            return {
                "estado": tipo,
                "requiere_fichaje": False,
                "mensaje": mensaje
            }

        # 4. Revisar si hoy es CUMPLEAÑOS del empleado
        es_cumpleanos = False
        if empleado['fecha_nacimiento']:
            fn = empleado['fecha_nacimiento']
            if fn.day == fecha_hoy.day and fn.month == fecha_hoy.month:
                es_cumpleanos = True

        # 5. Si es DÍA NORMAL DE TRABAJO
        saludo_base = random.choice(SALUDOS_DIARIOS).format(nombre=nombre)
        
        if es_cumpleanos:
            saludo_base = f"🎉 ¡¡FELIZ CUMPLEAÑOS, {nombre}!! 🎂🎈 De parte de todo el equipo te deseamos un día genial. " + saludo_base

        return {
            "estado": "CUMPLEAÑOS" if es_cumpleanos else "ACTIVO_NORMAL",
            "es_cumpleanos": es_cumpleanos,
            "requiere_fichaje": True,
            "mensaje": saludo_base
        }

    finally:
        cursor.close()
        conn.close()
if __name__ == "__main__":
    import json
    
    # Reemplaza '1' por el ID de un empleado que exista en tu BD
    ID_EMPLEADO_PRUEBA = 2
    
    print(f"\n🔍 Evaluando estado para el Empleado ID={ID_EMPLEADO_PRUEBA}...")
    evaluacion = evaluar_estado_empleado_hoy(empleado_id=ID_EMPLEADO_PRUEBA)
    
    print("\n📋 [RESULTADO DE EVALUACIÓN DE SOFY]:")
    print(json.dumps(evaluacion, indent=2, ensure_ascii=False))

    # Si requiere fichaje, probamos el envío de botones a WhatsApp
    if evaluacion.get("requiere_fichaje"):
        # Reemplaza por tu número de teléfono de pruebas en formato internacional (sin +)
        TELEFONO_PRUEBA = "584166074603" 
        
        print(f"\n📤 Enviando mensaje interactivo con botones a {TELEFONO_PRUEBA}...")
        respuesta_meta = enviar_saludo_interactivo_whatsapp(TELEFONO_PRUEBA, evaluacion["mensaje"])
        print("\n📩 Respuesta de la API de Meta:")
        print(respuesta_meta)
