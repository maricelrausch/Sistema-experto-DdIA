import json
from datetime import datetime
import os

# Cambiamos el nombre del archivo de salida.
NOMBRE_ARCHIVO = 'casos_no_diagnosticados.json'

def guardar_nuevo_caso(dispositivo: str, problema: str):
    """
    Registra un nuevo dispositivo y su problema en un archivo JSON.
    El archivo contendrá una lista de objetos (casos).
    """
    datos_nuevos = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dispositivo': dispositivo,
        'descripcion_problema': problema
    }
    
    lista_casos = []
    
    # Si el archivo ya existe y no está vacío, leemos los datos que ya contiene.
    if os.path.exists(NOMBRE_ARCHIVO) and os.path.getsize(NOMBRE_ARCHIVO) > 0:
        with open(NOMBRE_ARCHIVO, mode='r', encoding='utf-8') as archivo_json:
            try:
                lista_casos = json.load(archivo_json)
            except json.JSONDecodeError:
                # El archivo existe pero está corrupto o vacío, empezamos de nuevo.
                lista_casos = []
    
    # Añadimos el nuevo caso a nuestra lista de Python.
    lista_casos.append(datos_nuevos)
    
    # Escribimos la lista completa de vuelta en el archivo.
    # Usamos 'w' para 'write' (sobrescribir) y 'indent=4' para que sea legible.
    with open(NOMBRE_ARCHIVO, mode='w', encoding='utf-8') as archivo_json:
        json.dump(lista_casos, archivo_json, indent=4, ensure_ascii=False)

    print(f"✅ Nuevo caso registrado en '{NOMBRE_ARCHIVO}'")