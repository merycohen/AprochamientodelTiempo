import os
from cryptography.fernet import Fernet

# 🔑 CLAVE DE DESARROLLO: Fija para que los datos en la DB se puedan recuperar siempre.
# En producción, esto se lee desde un archivo .env externo.
CLAVE_MAESTRA = b'_RZYPnURoLwBzshRrndY3u8zMF4Sc8N2aTCfM9WcEso='


def generar_y_guardar_clave():
    """
    Genera una clave maestra para AES-256 y la muestra en pantalla.
    En un entorno de producción, esta clave se guarda estrictamente 
    en las variables de entorno (.env) fuera de la base de datos.
    """
    clave = Fernet.generate_key()
    print(# Guardar con cuidado
    f"🔑 CLAVE MAESTRA GENERADA (Cópiala y guárdala): {clave.decode()}")
    return clave

def cifrar_dato_sensible(texto_plano: str, clave: bytes) -> str:
    """
    Toma un dato sensible (como el teléfono o la coordenada de ubicación)
    y lo encripta usando AES-256 (Fernet). Devuelve una cadena de texto cifrada.
    """
    f = Fernet(clave)
    texto_bytes = texto_plano.encode('utf-8')
    texto_cifrado_bytes = f.encrypt(texto_bytes)
    return texto_cifrado_bytes.decode('utf-8')

def descifrar_dato_sensible(texto_cifrado: str, clave: bytes) -> str:
    """
    Toma el bloque de texto cifrado de la base de datos y, usando la clave maestra,
    lo devuelve a su estado original legible.
    """
    f = Fernet(clave)
    texto_cifrado_bytes = texto_cifrado.encode('utf-8')
    texto_desencriptado_bytes = f.decrypt(texto_cifrado_bytes)
    return texto_desencriptado_bytes.decode('utf-8')

if __name__ == "__main__":
    print("🔐 --- PRUEBA UNITARIA DEL MÓDULO DE CIBERSEGURIDAD ---")
    
    # 1. Simulamos la generación de la llave de seguridad
    mi_clave_secreta = generar_y_guardar_clave()
    
    # 2. Datos reales de una marca de asistencia simulada
    telefono_empleado = "+584121234567"
    ubicacion_real = "Lat: 10.4806, Lon: -66.9036" # Coordenadas en Caracas
    
    print(f"\n📝 Datos originales en texto plano:")
    print(f"   Teléfono: {telefono_empleado}")
    print(f"   Ubicación: {ubicacion_real}")
    
    # 3. Aplicamos Encriptación en Reposo (AES-256)
    telefono_protegido = cifrar_dato_sensible(telefono_empleado, mi_clave_secreta)
    ubicacion_protegida = cifrar_dato_sensible(ubicacion_real, mi_clave_secreta)
    
    print(f"\n🔒 Datos encriptados (Así se guardarán en PostgreSQL):")
    print(f"   Teléfono en DB: {telefono_protegido}")
    print(f"   Ubicación en DB: {ubicacion_protegida}")
    
    # 4. Probamos la desencriptación para cuando el Supervisor necesite consultar
    print(f"\n🔓 Desencriptando datos para auditoría autorizada...")
    print(f"   Teléfono recuperado: {descifrar_dato_sensible(telefono_protegido, mi_clave_secreta)}")
    print(f"   Ubicación recuperada: {descifrar_dato_sensible(ubicacion_protegida, mi_clave_secreta)}")

import hmac
import hashlib

# Clave secreta dedicada exclusivamente para generar los índices de búsqueda
CLAVE_PEPPER = "MiClaveSecretaParaHashes2026_NoCompartir"

def generar_hash_busqueda(dato: str) -> str:
    """
    Genera un HMAC-SHA256 determinista para búsquedas eficientes.
    Incluso si un atacante conoce el número de teléfono, no puede generar 
    el hash correspondiente sin la CLAVE_PEPPER.
    """
    dato_limpio = dato.strip().replace(" ", "").replace("+", "")
    return hmac.new(
        CLAVE_PEPPER.encode('utf-8'),
        dato_limpio.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()