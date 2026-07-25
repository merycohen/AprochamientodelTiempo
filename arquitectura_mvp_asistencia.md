**Manual de Arquitectura Técnica para el Agente SOFY en WhatsApp**

**Introducción**

El objetivo de este manual es proporcionar una visión general de la arquitectura técnica del agente SOFY en WhatsApp, incluyendo el diseño del flujo conversacional y la especificación técnica para el agente. El manual se divide en dos escenarios: Guía paso a paso para solicitar un permiso y Protocolo de escalado a Soporte Humano por correo electrónico.

**Escenario 1: Guía paso a paso para solicitar un permiso**

### Flujo Conversacional

El flujo conversacional del agente SOFY en WhatsApp se presenta a continuación:

1. **Bienvenida**
```
Hola, gracias por contactar con nosotros. ¿En qué puedo ayudarte hoy?
```

2. **Solicitud de Permiso**
```
¿Necesitas solicitar un permiso? (sí/no)
```

3. **Razón del Permiso**
```
Si es así, ¿por qué necesitas un permiso? (Escribe una breve descripción)
```

4. **Temporalidad del Permiso**
```
¿Cuál es la fecha de inicio y fin del permiso? (Todo el día o rango horario)
```

5. **Fecha del Permiso**
```
¿Cuál es la fecha del permiso?
```

6. **Aprobación Pendiente**
```
¡Excelente! Tu solicitud de permiso ha sido registrada como pendiente de aprobación. Nuestro equipo se pondrá en contacto contigo pronto.
```

### Estructura JSON

La estructura JSON del mensaje de WhatsApp se presenta a continuación:
```json
{
  "razon": "",
  "temporalidad": {
    "fecha_inicio": "",
    "fecha_fin": ""
  },
  "fecha": ""
}
```
**Escenario 2: Protocolo de escalado a Soporte Humano por correo electrónico**

### Flujo Conversacional

El flujo conversacional del agente SOFY en WhatsApp se presenta a continuación:

1. **Problema con Geofencing**
```
¿Estás experimentando algún problema con nuestra app de geofencing?
```

2. **Descripción del Problema**
```
¿Puedes describir el problema que estás experimentando? (Escribe una breve descripción)
```

3. **Escalado a Soporte Humano**
```
Si el problema persiste, necesitamos escalarte a nuestro equipo de soporte humano para ayudarte. Te enviaremos un correo electrónico con más información.
```

### Estructura del Correo Electrónico

La estructura del correo electrónico se presenta a continuación:
```json
{
  "asunto": "Escalado a Soporte Humano",
  "corpo": {
    "mensaje": "",
    "enlace": ""
  }
}
```
**Mecanismo de Resiliencia**

El agente SOFY en WhatsApp implementará un mecanismo de resiliencia para procesar el objeto JSON nativo de WhatsApp, extrayendo el 'messageTimestamp' (la hora real en que la persona le dio enviar en su celular sin internet) en lugar de la hora de llegada al servidor. El agente utilizará una biblioteca de programación como FastAPI para procesar el objeto JSON y extraer el timestamp.

El agente también implementará un mecanismo de espera para el usuario, que se activará si el agente no puede procesar el objeto JSON en un plazo determinado. En este caso, el agente enviará una respuesta al usuario con un mensaje de espera, indicando que el sistema está trabajando en su solicitud.

**Seguridad Automatizada**

El agente SOFY en WhatsApp implementará una política de seguridad automatizada para proteger la información del usuario. La política se basará en las siguientes reglas:

* **Encriptación de datos**: El agente utilizará AES-256 para encriptar los datos del usuario, incluyendo el mensaje de texto y la fecha del permiso.
* **Autenticación**: El agente utilizará tokens JWT para autenticar al usuario y verificar su identidad.
* **Validación geográfica**: El agente utilizará PostGIS para validar la ubicación del usuario y determinar si se encuentra dentro del radio de 50 metros.

La política de seguridad también incluirá una consulta SQL nativa utilizando 'ST_DWithin' para validar el radio de 50 metros. La consulta se presentará a continuación:
```sql
SELECT * FROM usuarios WHERE ST_DWithin(geom, ST_GeomFromText('POINT(-122.084051 37.385348)')) = 500;
```
**Protección de la llave de cifrado**

La política de seguridad también incluirá una protección para la llave de cifrado fuera de la base de datos. La llave se almacenará en un archivo seguro y se utilizará con un token de autenticación para acceder a la base de datos.

**Conclusión**

El agente SOFY en WhatsApp implementará un sistema de seguridad automatizada para proteger la información del usuario. El sistema incluirá una política de encriptación de datos, autenticación y validación geográfica utilizando PostGIS. La política también incluirá una consulta SQL nativa utilizando 'ST_DWithin' para validar el radio de 50 metros.

**Recomendaciones**

* Asegurarse de que el agente SOFY esté configurado correctamente con las credenciales de acceso a los sistemas y aplicaciones relevantes.
* Realizar pruebas exhaustivas del flujo conversacional y la estructura JSON para asegurarse de que se capturen los datos necesarios de forma precisa y estructurada.
* Establecer un proceso claro para escalar la ayuda al usuario cuando se presentan fallas técnicas, como en el segundo escenario.