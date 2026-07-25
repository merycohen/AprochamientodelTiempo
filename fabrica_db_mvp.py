from crewai import Agent, Task, Crew, Process, LLM

# Configurar el cerebro local con temperatura baja para máxima precisión de código
llm_local = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434",
    temperature=0.1
)

# AGENTE: Arquitecto DevSecOps y Especialista en Base de Datos
arquitecto_db = Agent(
    role='Arquitecto de Base de Datos Senior y Experto en PostGIS',
    goal='Diseñar el esquema DDL de PostgreSQL altamente optimizado y seguro para el MVP de Asistencia.',
    backstory="""Eres un DBA Senior y experto en seguridad de datos. Dominas PostgreSQL y su extensión 
    geoespacial PostGIS. Diseñas estructuras relacionales limpias, aplicando integridad referencial, 
    índices eficientes y encapsulamiento de lógica matemática compleja directamente en el motor de datos.""",
    verbose=True,
    llm=llm_local
)

# TAREA: Generar el script SQL con PostGIS y encriptación conceptual
tarea_diseño_sql = Task(
    description="""Diseña el script SQL de creación de tablas (DDL) para PostgreSQL. El diseño debe incluir:
    1. Habilitación de la extensión postgis.
    2. Tabla 'sedes': id, nombre, coordenada_centro (tipo GEOMETRY(Point, 4326)).
    3. Tabla 'empleados': id, telefono_cifrado (VARCHAR por AES-256), nombre_completo, sede_id.
    4. Tabla 'asistencias': id, empleado_id, hora_origen_whatsapp (TIMESTAMP), hora_llegada_servidor, coordenada_marca (GEOMETRY), dentro_geocerca (BOOLEAN).
    5. Tabla 'permisos': id, empleado_id, razon, fecha, temporalidad, JSON_crudo_sofy (JSONB), estatus.
    6. Una función o query de ejemplo comentada que use 'ST_DWithin' para validar si la coordenada_marca está a menos de 50 metros de la coordenada_centro de su sede.""",
    expected_output="Un archivo SQL estructurado y limpio con comentarios técnicos explicativos de cada tabla y restricción.",
    agent=arquitecto_db,
    output_file='estructura_base_datos.sql' # <--- Se guardará automáticamente aquí
)

crew_db = Crew(
    agents=[arquitecto_db],
    tasks=[tarea_diseño_sql],
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("\n🗄️ El Arquitecto de Software está diseñando el plano de base de datos geoespacial...")
    crew_db.kickoff()
    print("\n🎯 [PLANO DE BASE DE DATOS GENERADO CON ÉXITO]")
    print("Revisa el archivo 'estructura_base_datos.sql' en tu carpeta de proyecto.")