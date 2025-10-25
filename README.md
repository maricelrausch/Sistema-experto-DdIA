<!-- 
========================================================
README - Sistema Experto IoT
Proyecto final - Desarrollo de Sistemas de Inteligencia Artificial (2025)
Autores: Maricel Rausch, Eduardo Saldivia, Facundo Isa
Institución: Politécnico Malvinas Argentinas
========================================================
-->

# 🧠 Sistema Experto para Diagnóstico de Dispositivos IoT  
**Proyecto Final – Desarrollo de Sistemas de Inteligencia Artificial (2025)**  

📚 *Carrera:* Ciencias de Datos e Inteligencia Artificial  
🏫 *Institución:* Politécnico Malvinas Argentinas  
👩‍💻 *Autores:* **Maricel Rausch**, **Eduardo Saldivia**, **Facundo Isa**  

---

## 🚀 Descripción General

Este proyecto implementa un **Sistema Experto** en **FastAPI** para el diagnóstico inteligente de fallas en dispositivos **IoT (Internet of Things)**.  
El sistema aplica una **base de conocimiento configurable (JSON)** y un **motor de inferencia** que evalúa síntomas, calcula probabilidades y determina la criticidad del problema, ofreciendo una **recomendación automática** al usuario.

Además, cuenta con una **interfaz web completa** para:
- Registrar casos y ver resultados en tiempo real.
- Consultar estadísticas de diagnósticos.
- Editar la base de conocimiento sin tocar código.

---

## 🧩 Arquitectura del Proyecto

proyecto-sistema-experto-main/
│
├─ app/
│ ├─ main.py # API principal y rutas FastAPI
│ ├─ modelos.py # Modelos de datos (Pydantic + Enums)
│ ├─ reglas.py # Motor de inferencia (BaseConocimiento)
│ ├─ static/ # Archivos CSS y recursos estáticos
│ ├─ templates/ # Interfaz web (HTML + Jinja2)
│ └─ data/ # Archivos JSON (Base de conocimiento + Casos)
│
├─ requirements.txt # Dependencias del entorno
├─ README.md # Documentación del proyecto
└─ venv/ # Entorno virtual (local)

yaml
Copiar código

---

## ⚙️ Instalación y Ejecución

> **💡 Requisitos previos:**  
> Tener instalado **Python 3.11+** y **Git**.  

### 1️⃣ Clonar el repositorio
```bash
git clone https://github.com/<usuario>/proyecto-sistema-experto-main.git
cd proyecto-sistema-experto-main
2️⃣ Crear y activar entorno virtual
bash
Copiar código
python -m venv venv
En Windows:

bash
Copiar código
venv\Scripts\activate
En Linux/Mac:

bash
Copiar código
source venv/bin/activate
3️⃣ Instalar dependencias
bash
Copiar código
pip install -r requirements.txt
4️⃣ Ejecutar la aplicación
bash
Copiar código
uvicorn app.main:app --reload
🔗 Por defecto, la aplicación estará disponible en:
http://127.0.0.1:8000

🖥️ Interfaz Web (Rutas Principales)
Ruta	Descripción
/panel	Panel principal con accesos a todas las secciones.
/nuevo	Formulario para cargar un nuevo diagnóstico.
/resultado	Página que muestra el resultado del diagnóstico.
/casos/diagnosticados	Historial de casos registrados.
/stats	Visualización de estadísticas y gráficos (Chart.js).
/admin/kb	Editor de base de conocimiento (agregar/editar síntomas y dispositivos).

🧠 Motor de Inferencia (app/reglas.py)
El motor BaseConocimiento:

Carga las reglas desde app/data/base_conocimiento.json.

Evalúa los síntomas reportados y busca causas posibles.

Ajusta probabilidades según:

Tipo de dispositivo.

Factores definidos (factor_hardware, factor_red, etc.).

Señal WiFi, firmware y tiempo encendido.

Determina el nivel de criticidad (BAJA, MEDIA, ALTA, CRITICA).

Devuelve un listado de causas probables con su recomendación.

Ejemplo de flujo:
text
Copiar código
1️⃣ Usuario ingresa: "Cámara de seguridad" + "No responde" + "Error de conexión".
2️⃣ El sistema consulta las reglas relacionadas en la base de conocimiento.
3️⃣ Ajusta las probabilidades considerando factores y contexto.
4️⃣ Devuelve diagnóstico + recomendación.
📂 Base de Conocimiento (JSON)
Ubicación: app/data/base_conocimiento.json

json
Copiar código
{
  "reglas_por_sintoma": {
    "no_responde": [
      {
        "causa": "Falla total de firmware",
        "categoria": "hardware",
        "probabilidad_base": 85,
        "solucion": "Reinstalar firmware original"
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
El archivo puede editarse manualmente o desde la interfaz /admin/kb.

🧮 Casos y Estadísticas
Los diagnósticos realizados se guardan automáticamente en
app/data/casos_no_diagnosticados.json, con estructura tipo:

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
La sección /stats analiza este archivo y genera gráficos automáticos con Chart.js:

Distribución de casos por tipo de dispositivo.

Frecuencia de síntomas.

Categorías más comunes.

Niveles de criticidad.

🔬 Prueba Rápida (Smoke Test)
Para probar el motor sin levantar la API:

bash
Copiar código
python -m app.reglas
Esto carga la base de conocimiento, crea un dispositivo de prueba y muestra:

css
Copiar código
🔎 Diagnósticos (top 5):
 - Falla total de firmware | hardware | 82.0%
📶 Criticidad: alta
🧰 Requerimientos Técnicos
Herramienta	Versión recomendada
Python	3.11+
FastAPI	0.110+
Uvicorn	0.30+
Jinja2	3.1+
Pydantic	2.x
Chart.js	4.x (para los gráficos en /stats)

👩‍💻 Autores
Nombre	Rol	Contacto
Maricel Rausch	Desarrollo Frontend, integración FastAPI, documentación	
Eduardo Saldivia	Motor de inferencia, base de conocimiento	
Facundo Isa	Diseño de interfaz, visualización y testing	

🧭 Conclusión
Este sistema experto demuestra cómo combinar lógica simbólica (reglas) con una API moderna (FastAPI) para resolver problemas reales de diagnóstico.
Su arquitectura modular permite escalar fácilmente a otros contextos:

mantenimiento predictivo,

monitoreo remoto,

o integración con sensores IoT reales.

🌟 Ejecución Rápida (resumen)
bash
Copiar código
git clone https://github.com/<usuario>/proyecto-sistema-experto-main.git
cd proyecto-sistema-experto-main
python -m venv venv
venv\Scripts\activate        # o source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
📍Abrir en navegador: http://127.0.0.1:8000/panel

🏁 Licencia y Uso
Proyecto académico – uso educativo y demostrativo.
Puedes reutilizarlo con fines formativos, citando a sus autores originales.