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

```

# ⚙️ Instalación y Ejecución

Requisitos previos:
Tener instalado Python 3.11+ y Git.

# 🚀 Instrucciones de instalación y ejecución

### 1. Clonar el repositorio

git clone https://github.com/maricelrausch/Sistema-experto-DdIA.git
cd Sistema-experto-DdIA

### 2. Crear y activar el entorno virtual
bash
python -m venv venv

En Windows (PowerShell / CMD):
bash
venv\Scripts\activate

En Linux / macOS:
bash
source venv/bin/activate


### 3. Instalar dependencias
bash
pip install -r requirements.txt

### 4. Ejecutar la aplicación FastAPI
bash
uvicorn app.main:app --reload

### 5. Luego abrí en tu navegador:

App: http://127.0.0.1:8000/panel

# Requerimientos Técnicos

Herramienta	Versión recomendada
Python	3.11+
FastAPI	0.110+
Uvicorn	0.30+
Pydantic	2.x
Jinja2	3.1+
Chart.js	4.x (gráficos en /stats)

Las dependencias exactas están en requirements.txt.

# Autores

Maricel Rausch – Integración FastAPI, frontend, documentación.
Eduardo Saldivia – Motor de inferencia, base de conocimiento.
Facundo Isa – Interfaz, visualización, testing funcional.

# Licencia y Uso
Proyecto académico con fines educativos.
Se permite reutilizar el código con fines de aprendizaje, mencionando a los autores.

