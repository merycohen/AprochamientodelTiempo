from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from conexion_db import Base

class Sede(Base):
    __tablename__ = "sedes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(255), nullable=True)
    
    # Campo espacial: Guarda la Latitud y Longitud como un PUNTO geométrico
    # SRID 4326 representa el sistema de coordenadas geográficas estándar (GPS)
    ubicacion = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    
    # Radio de tolerancia en metros configurado en el slider
    radio_metros = Column(Float, default=50.0)


class Empleado(Base):
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    cedula_id = Column(String(50), nullable=False, unique=True)
    
    # Teléfono cifrado con Fernet / AES-256
    telefono_cifrado = Column(String(255), nullable=False, unique=True, index=True)
    
    # Hash HMAC blindado con CLAVE_PEPPER para búsquedas exactas
    telefono_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    activo = Column(Boolean, default=True)
    
    # Nuevas columnas para la máquina de estados de Sofy en WhatsApp
    estado_wa = Column(String, default="IDLE")
    borrador_justificacion = Column(JSON, nullable=True, default=None)


class Asistencia(Base):
    __tablename__ = "asistencias"

    id = Column(Integer, primary_key=True, index=True)
    empleado_id = Column(Integer, nullable=False) # Vinculado al id del empleado
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    tipo_registro = Column(String(20), default="ENTRADA") # <--- NUEVA COLUMNA: 'ENTRADA' o 'SALIDA'
    hora_origen_whatsapp = Column(DateTime, nullable=True) # Hora enviada por el webhook
    hora_llegada_servidor = Column(DateTime, server_default=func.now(), nullable=False)
    coordenada_marca = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    dentro_geocerca = Column(Boolean, nullable=False)