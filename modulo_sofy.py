import json
from crewai import Agent, Task, Crew, Process, LLM

# 1. Configurar el LLM Local
llm_local = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434",
    temperature=0.3
)

# 2. Definición del Agente Sofy
sofy_conversacional = Agent(
    role='SOFY - Asistente Virtual Empática y Diligente',
    goal='Atender a los empleados por WhatsApp con amabilidad, responder dudas sobre su historial de asistencia y estructurar solicitudes de permisos.',
    backstory="""Eres SOFY, una asistente virtual de la suite 'Aprovechamiento del Tiempo'.
    Te caracterizas por ser profundamente amable, empática, servicial y eficiente. Hablas un español 
    impecable, cálido y profesional.
    
    Tus funciones principales son:
    1. Si el usuario hace preguntas sobre sus registros (horarios, marcajes, geocercas), respondes de forma clara utilizando el CONTEXTO DE ASISTENCIA provisto.
    2. Si el usuario reporta una inasistencia, problema de salud o permiso, respondes empáticamente y extraes los datos en formato JSON.
    3. Si detectas una falla técnica grave que no puedes resolver, marcas 'escalar_soporte' como true.""",
    verbose=True,
    llm=llm_local
)

# 3. Función Principal para Procesar Mensajes Dinámicos
def procesar_mensaje_sofy(mensaje_usuario: str, contexto_empleado: dict = None) -> dict:
    """
    Recibe el mensaje del usuario y su contexto desde la BD para generar la respuesta.
    """
    
    # Formateamos el contexto si existe
    info_contexto = "No hay registros recientes disponibles."
    if contexto_empleado:
        info_contexto = f"""
        - Empleado: {contexto_empleado.get('nombre', 'Desconocido')}
        - Último Marcaje Hoy: {contexto_empleado.get('ultimo_marcaje', 'Sin marcaje hoy')}
        - Tipo Registro: {contexto_empleado.get('tipo_registro', 'N/A')}
        - Dentro de Geocerca: {contexto_empleado.get('dentro_geocerca', 'N/A')}
        - Sede Asignada: {contexto_empleado.get('sede', 'N/A')}
        """

    tarea_analisis = Task(
        description=f"""Analiza el siguiente mensaje enviado por un empleado en WhatsApp:
        "{mensaje_usuario}"
        
        Usa este CONTEXTO DE ASISTENCIA DEL EMPLEADO si hace preguntas sobre sus registros:
        {info_contexto}
        
        Debes redactar una respuesta de chat en español empática y clara. Luego, si detectas una solicitud de permiso o justificación, extrae los datos en JSON. De lo contrario, deja los campos de permiso vacíos o nulos.""",
        
        expected_output="""Un objeto JSON estricto con la siguiente estructura:
        {
           "respuesta_chat_sofy": "Texto amigable y respuesta dirigida al usuario...",
           "datos_permiso": {
              "es_solicitud_permiso": true/false,
              "razon": "Salud / Emergencia / Trámite / Consulta General",
              "fecha": "YYYY-MM-DD o vacio",
              "temporalidad": "Día Completo / Rango de Horas / N/A",
              "estatus": "Pendiente de Aprobación",
              "escalar_soporte": false
           }
        }
        Nota: Devuelve ÚNICAMENTE el bloque JSON válido, sin delimitadores ```json ni texto adicional.""",
        agent=sofy_conversacional
    )

    crew_sofy = Crew(
        agents=[sofy_conversacional],
        tasks=[tarea_analisis],
        process=Process.sequential,
        verbose=False
    )

    resultado = crew_sofy.kickoff()
    
    # Limpieza básica por si Ollama incluye comillas o etiquetas markdown
    raw_text = str(resultado).strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        
    try:
        return json.loads(raw_text)
    except Exception as e:
        # Fallback en caso de que el JSON no venga perfecto
        return {
            "respuesta_chat_sofy": raw_text,
            "datos_permiso": {"es_solicitud_permiso": False, "escalar_soporte": True}
        }

# Prueba local
if __name__ == "__main__":
    contexto_prueba = {
        "nombre": "Mery Cohen",
        "ultimo_marcaje": "2026-07-28 08:30 AM",
        "tipo_registro": "ENTRADA",
        "dentro_geocerca": True,
        "sede": "Sede Principal"
    }
    
    mensaje_prueba = "Hola Sofy, ¿a qué hora quedó registrada mi entrada hoy y si estuve dentro del rango?"
    
    print("\n🤖 SOFY Consultando datos...")
    respuesta = procesar_mensaje_sofy(mensaje_prueba, contexto_prueba)
    print("\n🎯 [RESPUESTA DE SOFY]:")
    print(json.dumps(respuesta, indent=2, ensure_ascii=False))