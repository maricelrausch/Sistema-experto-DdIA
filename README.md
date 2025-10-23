# Sistema Experto para Diagnóstico de Dispositivos IoT

Este proyecto está construido con FastAPI que sirve como un sistema experto para diagnosticar problemas en dispositivos inteligentes del hogar.

## Estructura del Proyecto

-   `main.py`: El servidor FastAPI y todos los endpoints.
-   `modelos.py`: Contiene los modelos de datos Pydantic y las enumeraciones.
-   `reglas.py`: Define la base de conocimiento y el motor de inferencia.
-   `requirements.txt`: Las dependencias de Python del proyecto.

## Instalación

1.  Clona este repositorio.
2.  Crea un entorno virtual (recomendado):
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```
3.  Instala las dependencias:
    ```bash
    pip install -r requirements.txt
    ```

## Ejecución

Para iniciar el servidor de la API, ejecuta el siguiente comando en la raíz del proyecto:

```bash
uvicorn main:app --reload
