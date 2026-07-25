import json
from crewai import Agent, Task, Crew, Process, LLM

# 1. Configurar el "Cerebro" Local con un toque de creatividad controlada
llm_local = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434",
    temperature=0.3  # Un poco más alto para que su lenguaje natural sea fluido y empático
)

# ==========================================================
# 👥 DEFINICIÓN DE LA IDENTIDAD DE SOFY
# ==========================================================
sofy_conversacional = Agent(
    role='SOFY - Asistente Virtual Empática y Diligente',
    goal='Procesar mensajes de empleados con absoluta amabilidad, resolver dudas de asistencia y estructurar solicitudes de permisos.',
    backstory="""Eres SOFY, una asistente virtual de género femenino. Te caracterizas por ser 
    profundamente amable, empática, servicial y muy rápida para resolver problemas. Hablas un español 
    impecable, cálido y profesional. 
    Cuando un empleado te escribe porque tiene una duda, un problema técnico o necesita faltar, tú 
    siempre respondes primero con empatía (ej. "Lamento escuchar eso", "Con gusto te ayudo"). 
    Tu objetivo principal en este caso es analizar el mensaje del usuario y extraer TRES datos clave en formato JSON:
    1. razon: El motivo (Salud, Trámite Personal, Emergencia, Dudas, Falla Técnica).
    2. fecha: La fecha del evento o la solicitud.
    3. temporalidad: Si es "Día Completo" o un rango de horas específico (ej: "09:00 AM a 01:00 PM").
    
    Si el caso es una falla técnica grave que no puedes resolver, marcas el campo 'escalar_soporte' como true.""",
    verbose=True,
    llm=llm_local
)

# ==========================================================
# 📋 DEFINICIÓN DE LA TAREA DE PROCESAMIENTO
# ==========================================================
# Simulamos un mensaje real que un empleado enviaría por WhatsApp en una mañana difícil
mensaje_empleado_whatsapp = """
Hola Sofy, buenos días. Mira, me siento muy mal del estómago hoy, tengo fiebre y dolor de cabeza. 
No voy a poder ir a la oficina hoy 18 de julio. Voy a ir al médico en la tarde a ver qué me dice. 
Por favor ayúdame a reportar esto. Gracias.
"""

tarea_analisis_mensaje = Task(
    description=f"""Analiza el siguiente mensaje enviado por un empleado en WhatsApp:
    "{mensaje_empleado_whatsapp}"
    
    Debes redactar una respuesta de chat en español que sea sumamente empática, amable y diligente, confirmando 
    que procesarás su solicitud. Luego, extrae los datos del permiso estrictamente en una estructura JSON.""",
    expected_output="""Un objeto JSON con la siguiente estructura exacta:
    {
       "respuesta_chat_sofy": "Texto empático dirigido al usuario...",
       "datos_permiso": {
          "razon": "Salud / Emergencia / etc",
          "fecha": "Fecha detectada",
          "temporalidad": "Día Completo o Horario",
          "estatus": "Pendiente de Aprobación",
          "escalar_soporte": false
       }
    }
    Nota: Devuelve ÚNICAMENTE el bloque JSON válido, sin textos introductorios antes o después.""",
    agent=sofy_conversacional
)

# ==========================================================
# 🚀 ORQUESTACIÓN DE LA INTERACCIÓN
# ==========================================================
crew_sofy = Crew(
    agents=[sofy_conversacional],
    tasks=[tarea_analisis_mensaje],
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("\n🤖 SOFY iniciando procesamiento de lenguaje natural en WhatsApp...")
    
    resultado = crew_sofy.kickoff()
    
    print("\n🎯 [PROCESAMIENTO DE SOFY COMPLETADO]")
    print(resultado)