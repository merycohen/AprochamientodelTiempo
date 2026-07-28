ALTER TABLE asistencias 
-- 1. Campos para la marcación de salida
ADD COLUMN IF NOT EXISTS hora_salida TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS coordenada_salida GEOMETRY(Point, 4326),
ADD COLUMN IF NOT EXISTS dentro_geocerca_salida BOOLEAN DEFAULT FALSE,

-- 2. Campos para el flujo de regularización / aprobación (Sofy + Supervisor)
ADD COLUMN IF NOT EXISTS estatus VARCHAR(30) DEFAULT 'Aprobado',
ADD COLUMN IF NOT EXISTS justificacion_regularizacion TEXT,
ADD COLUMN IF NOT EXISTS ajustado_por_supervisor_id INTEGER,
ADD COLUMN IF NOT EXISTS observaciones_supervisor TEXT;