from crewai import Agent, Task, Crew, Process, LLM

# 1. Configurar el "Cerebro" Local Optimizado
llm_local = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434",
    temperature=0.1  # Temperatura muy baja para máxima precisión en reglas de negocio y seguridad
)

# ==========================================================
# 👥 SECCIÓN 1: DEFINICIÓN DE AGENTES (Incorporando a SOFY)
# ==========================================================

# AGENTE 1: SOFY (Tu Asistente Virtual y Gestora de Permisos)
sofy_agent = Agent(
    role='SOFY - Asistente Virtual Diligente de Soporte y Gestión de Tiempos',
    goal='Guiar amablemente a los empleados, resolver dudas operativas y estructurar solicitudes de permisos en JSON limpios.',
    backstory="""Eres SOFY, una asistente virtual de género femenino. Te caracterizas por ser 
    profundamente amable, empática, diligente y muy clara en tu comunicación. Hablas español de forma profesional y cordial.
    Tu objetivo es facilitar la vida al empleado. Si reportan una inasistencia o permiso, tú los guías para extraer de forma 
    estructurada tres datos clave: Razón (Enfermedad, Permiso Remunerado/No Remunerado), Temporalidad (Todo el día o rango de horas) 
    y la Fecha. Si un usuario experimenta un problema técnico complejo, eres capaz de estructurar un ticket formal para Soporte Humano.""",
    verbose=True,
    llm=llm_local
)

# AGENTE 2: El Arquitecto DevSecOps y Base de Datos (Especialista en Seguridad y PostGIS)
arquitecto_seguridad = Agent(
    role='Arquitecto de Software Senior y Especialista en Ciberseguridad/PostGIS',
    goal='Diseñar la estructura lógica de la base de datos, el mecanismo de geofencing de 50 metros y blindar la seguridad de la app.',
    backstory="""Eres un experto en ciberseguridad, bases de datos relacionales y diseño de APIs robustas.
    Tu enfoque es el diseño seguro (Security by Design). Sabes encriptar datos en reposo usando AES-256, gestionar accesos mediante
    roles estrictos (RBAC) con tokens JWT y resolver la validación geográfica nativa en la base de datos utilizando la extensión PostGIS.""",
    verbose=True,
    llm=llm_local
)

# ==========================================================
# 📋 SECCIÓN 2: DEFINICIÓN DE TAREAS (Lógica de Resiliencia y Flujos)
# ==========================================================

# TAREA 1: Diseñar el flujo de SOFY para captura de datos y permisos
tarea_flujo_sofy = Task(
    description="""Diseña el flujo conversacional y la especificación técnica para el agente SOFY en WhatsApp. 
    Debe abordar dos escenarios:
    1. Guía paso a paso en lenguaje natural para que el usuario solicite un permiso, asegurando que se capturen de forma estructurada los campos: Razón, Temporalidad (todo el día o rango horario) y Fecha, marcándolo como 'Pendiente de Aprobación'.
    2. El protocolo de escalado a Soporte Humano por correo electrónico si la app de geofencing presenta fallas técnicos.""",
    expected_output="Un documento conceptual con el diseño de diálogos de SOFY y la estructura JSON exacta que generará para el módulo de permisos.",
    agent=sofy_agent
)

# TAREA 2: Diseñar el módulo de Resiliencia de Red y Ciberseguridad (Fallas de Internet e Inyección PostGIS)
tarea_arquitectura_tecnica = Task(
    description="""Basándote en los requerimientos del negocio, diseña la especificación técnica de la infraestructura:
    1. MECANISMO DE RESILIENCIA: Explica cómo la API de FastAPI procesará el objeto JSON nativo de WhatsApp, extrayendo el 'messageTimestamp' (la hora real en que la persona le dio enviar en su cel sin internet) en lugar de la hora de llegada al servidor, detallando la respuesta de espera para el usuario.
    2. SEGURIDAD AUTOMATIZADA: Define el esquema de la base de datos PostgreSQL + PostGIS. Incluye la consulta SQL nativa usando 'ST_DWithin' para validar el radio de 50 metros de geocerca. Especifica qué columnas (teléfono, nombres, coordenadas) se encriptarán en reposo usando AES-256 y cómo se protegerá la llave de cifrado fuera de la base de datos.""",
    expected_output="Un manual de arquitectura técnica detallado que cubra el geofencing PostGIS, el manejo de resiliencia del timestamp de WhatsApp y las políticas de encriptación AES-256.",
    agent=arquitecto_seguridad,
    output_file='arquitectura_mvp_asistencia.md'  # <--- ¡MIRA! Se guardará automáticamente aquí en Markdown
)

# ==========================================================
# 🚀 SECCIÓN 3: ORQUESTACIÓN Y LANZAMIENTO DE LA FÁBRICA
# ==========================================================

crew_asistencia = Crew(
    agents=[sofy_agent, arquitecto_seguridad],
    tasks=[tarea_flujo_sofy, tarea_arquitectura_tecnica],
    process=Process.sequential,  # Primero se define la lógica de interacción de SOFY, luego la arquitectura técnica
    verbose=True
)

if __name__ == "__main__":
    print("\n🎬 Inicializando Fábrica para el MVP Suite 'Aprovechamiento del Tiempo'...")
    print("🤖 Procesando flujos de SOFY, Resiliencia de Red y Seguridad...\n")
    
    resultado = crew_asistencia.kickoff()
    
    print("\n🎯 [PROCESO COMPLETADO EXITOSAMENTE]")
    print("El informe técnico completo ha sido generado y guardado en tu disco duro.")