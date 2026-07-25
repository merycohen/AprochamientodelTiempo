import sys
import os

# Aseguramos que Python encuentre los archivos locales
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Cambiamos "database" por "fabrica_db_mvp"
from conexion_db import engine, Base
import models

def inicializar_base_de_datos():
    print("⏳ Conectando con PostgreSQL y creando tablas...")
    try:
        #borra la base de datos completa 
        Base.metadata.drop_all(bind=engine)
        # Este comando busca todas las clases que heredan de Base (como Sede)
        # y crea las tablas físicamente en la base de datos si no existen.
        Base.metadata.create_all(bind=engine)
        print("✅ ¡Tablas creadas con éxito en la base de datos 'suite_tiempo'!")
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        sys.exit(1)

if __name__ == "__main__":
    inicializar_base_de_datos()