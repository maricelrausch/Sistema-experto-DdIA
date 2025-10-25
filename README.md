<!--
========================================================
Sistema Experto IoT
Proyecto final - Desarrollo de Sistemas de IA (2025)
Autores: Maricel Rausch, Eduardo Saldivia, Facundo Isa
Institución: Politécnico Malvinas Argentinas
========================================================
-->

# Sistema Experto para Diagnóstico de Dispositivos IoT  
Proyecto Final – Desarrollo de Sistemas de Inteligencia Artificial (2025)

**Carrera:** Ciencias de Datos e Inteligencia Artificial  
**Institución:** Politécnico Malvinas Argentinas  
**Autores:** Maricel Rausch, Eduardo Saldivia, Facundo Isa  

---

## Descripción General

Este proyecto implementa un **Sistema Experto** en **FastAPI** para el diagnóstico inteligente de fallas en dispositivos IoT (Internet of Things).

El sistema:
- Recibe síntomas observados en un dispositivo.
- Consulta una base de conocimiento configurable almacenada en JSON.
- Calcula probabilidad de posibles causas.
- Determina el nivel de criticidad del problema.
- Genera una recomendación automática para el usuario.

Además incluye una **interfaz web completa** para:
- Cargar un nuevo caso y ver el resultado.
- Consultar el historial de diagnósticos.
- Visualizar métricas y gráficos.
- Administrar la base de conocimiento sin editar el código.

---

## Arquitectura del Proyecto

```text
proyecto-sistema-experto-main/
│
├─ app/
│  ├─ main.py                # API principal y rutas FastAPI
│  ├─ modelos.py             # Modelos de datos (Pydantic + Enums)
│  ├─ reglas.py              # Motor de inferencia (BaseConocimiento)
│  ├─ static/                # Archivos CSS / assets
│  ├─ templates/             # Interfaz web (HTML + Jinja2)
│  └─ data/
│      ├─ base_conocimiento.json        # Reglas del sistema experto
│      └─ casos_no_diagnosticados.json  # Historial de diagnósticos
│
├─ requirements.txt          # Dependencias del entorno
└─ README.md                 # Documentación del proyecto
Instalación y Ejecución
Requisitos previos:

Python 3.11 o superior

Git

1. Clonar el repositorio
bash
Copiar código
git clone https://github.com/maricelrausch/Sistema-experto-DdIA.git
cd Sistema-experto-DdIA
2. Crear y activar el entorno virtual
bash
Copiar código
python -m venv venv
En Windows (PowerShell / CMD):

bash
Copiar código
venv\Scripts\activate
En Linux / macOS:

bash
Copiar código
source venv/bin/activate
3. Instalar dependencias
bash
Copiar código
pip install -r requirements.txt
4. Ejecutar la aplicación FastAPI
bash
Copiar código
uvicorn app.main:app --reload
Luego abrí en tu navegador:

App: http://127.0.0.1:8000/panel

Docs interactivas (Swagger): http://127.0.0.1:8000/docs

Interfaz Web (rutas principales)
Ruta	Descripción
/panel	Panel principal con accesos rápidos.
/nuevo	Formulario para ingresar un dispositivo y sus síntomas.
/resultado	Vista con el diagnóstico generado.
/casos/diagnosticados	Historial de diagnósticos registrados.
/stats	Gráficos y métricas de uso del sistema.
/admin/kb	Editor de la base de conocimiento (síntomas, causas, factores por equipo).

Motor de Inferencia (app/reglas.py)
El motor BaseConocimiento es el corazón del sistema experto.

Responsabilidades:

Carga las reglas desde app/data/base_conocimiento.json.

Busca qué causas se asocian a los síntomas reportados.

Ajusta la probabilidad de cada causa según:

Tipo de dispositivo.

Factores definidos para ese tipo (factor_hardware, factor_red, etc.).

Intensidad de la señal WiFi.

Estado del firmware.

Tiempo encendido del dispositivo.

Determina el nivel de criticidad (baja, media, alta, critica).

Ejemplo de flujo conceptual:

El usuario reporta:

Dispositivo: "cámara de seguridad"

Síntomas: "no responde", "error de conexión"

El sistema consulta reglas asociadas a cada síntoma.

Ajusta probabilidades según contexto (por ejemplo, mala WiFi aumenta problemas de red).

Devuelve:

causas más probables,

recomendación prioritaria,

criticidad total.

Base de Conocimiento
La base de conocimiento vive en:
app/data/base_conocimiento.json

Ejemplo (resumido):

json
Copiar código
{
  "reglas_por_sintoma": {
    "no_responde": [
      {
        "causa": "Falla total de firmware",
        "categoria": "hardware",
        "probabilidad_base": 85,
        "solucion": "Reinstalar firmware oficial"
      }
    ]
  },

  "reglas_por_dispositivo": {
    "termostato": {
      "factor_hardware": 1.3,
      "factor_red": 1.1,
      "factor_energia": 1.2,
      "factor_software": 0.9,
      "sintomas_criticos": ["no_responde", "reinicios_frecuentes"]
    }
  }
}
Notas:

reglas_por_sintoma define, por cada síntoma, cuáles son las posibles causas y cómo diagnosticarlas.

reglas_por_dispositivo define modificadores de probabilidad y qué síntomas son críticos para ese tipo de equipo.

Esta información se puede editar:

A mano (editando el JSON).

Desde la interfaz /admin/kb (sin tocar el código).

Casos y Estadísticas
Cada vez que se hace un diagnóstico, se guarda un registro en:
app/data/casos_no_diagnosticados.json

Ejemplo:

json
Copiar código
[
  {
    "nombre": "Sensor Cocina",
    "fecha": "2025-10-25 12:30",
    "tipo_dispositivo": "termostato",
    "sintomas": ["no_responde", "reinicios_frecuentes"],
    "categoria_top": "hardware",
    "criticidad": "alta"
  }
]
Ese archivo alimenta:

La tabla en /casos/diagnosticados

Los gráficos en /stats (por ejemplo distribución por tipo, síntomas más frecuentes, niveles de criticidad, etc.)

Prueba rápida del motor (sin levantar la API)
Podés probar el motor de reglas directamente desde consola:

bash
Copiar código
python -m app.reglas
Esto:

Crea un dispositivo de ejemplo.

Corre la inferencia.

Muestra por consola las causas más probables y la criticidad estimada.

Sirve para testear que la base de conocimiento JSON está bien formada.

Requerimientos Técnicos
Herramienta	Versión recomendada
Python	3.11+
FastAPI	0.110+
Uvicorn	0.30+
Pydantic	2.x
Jinja2	3.1+
Chart.js	4.x (gráficos en /stats)

Las dependencias exactas están en requirements.txt.

Autores
Maricel Rausch – Integración FastAPI, frontend, documentación.

Eduardo Saldivia – Motor de inferencia, base de conocimiento.

Facundo Isa – Interfaz, visualización, testing funcional.

Licencia y Uso
Proyecto académico con fines educativos.
Se permite reutilizar el código con fines de aprendizaje, mencionando a los autores.

