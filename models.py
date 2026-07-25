
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
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
    # Aquí almacenamos el teléfono previamente encriptado con Fernet / AES-256
    telefono_cifrado = Column(String(255), nullable=False, unique=True, index=True)
    telefono_hash = Column(String(64), nullable=False, unique=True, index=True)  # <--- NUEVA COLUMNA PARA BÚSQUEDAS Un hash HMAC blindado con tu CLAVE_PEPPER
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    activo = Column(Boolean, default=True)

class Asistencia(Base):
    __tablename__ = "asistencias"

    id = Column(Integer, primary_key=True, index=True)
    empleado_id = Column(Integer, nullable=False) # Vinculado al id del empleado
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    hora_origen_whatsapp = Column(DateTime, nullable=True) # Hora opcional enviada por el webhook
    hora_llegada_servidor = Column(DateTime, server_default=func.now(), nullable=False) # Timestamp automático de Postgres
    coordenada_marca = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    dentro_geocerca = Column(Boolean, nullable=False)