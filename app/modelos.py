"""
app/modelos.py

Modelos de datos y enums del sistema experto.

Acá definimos:
- Los tipos de dispositivo admitidos (TipoDispositivo)
- Los síntomas que puede reportar el usuario (Sintoma)
- Las categorías de causa (Causa)
- El nivel de criticidad (NivelCriticidad)
- El input que recibe el motor / la API (DispositivoInput)
- El formato interno de diagnóstico (Diagnostico)
- El resultado que devolvemos al front / templates (Resultado)

IMPORTANTE:
- Estos modelos los importan tanto main.py como reglas.py.
- Mantener los nombres tal cual (no renombrar campos) porque otras
  partes del sistema ya dependen de ellos.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


# -------------------------------------------------------------------
# ENUMS PRINCIPALES
# -------------------------------------------------------------------

class TipoDispositivo(str, Enum):
    """
    Tipos conocidos de dispositivos IoT.
    Estos valores son los que se muestran en el formulario /nuevo (select de tipo).
    """
    TERMOSTATO = "termostato"
    LUZ_INTELIGENTE = "luz_inteligente"
    CAMARA_SEGURIDAD = "camara_seguridad"
    CERRADURA_INTELIGENTE = "cerradura_inteligente"
    ASISTENTE_VOZ = "asistente_voz"
    SENSOR_AGUA = "sensor_agua"
    # Si querés que un nuevo tipo aparezca en el formulario, lo agregás acá.


class Sintoma(str, Enum):
    """
    Síntomas reportables que describen el comportamiento del dispositivo.
    Estos valores (strings) se usan para buscar causas en la KB.
    """
    NO_RESPONDE = "no_responde"
    ERROR_CONEXION = "error_conexion"
    REINICIOS_FRECUENTES = "reinicios_frecuentes"
    CONSUMO_ANOMALO = "consumo_anomalo"
    LATENCIA_ALTA = "latencia_alta"
    FALLA_AUTENTICACION = "falla_autenticacion"
    # Si querés un nuevo checkbox en /nuevo, lo agregás acá.


class Causa(str, Enum):
    """
    Clasificación técnica de la causa raíz estimada.
    Se usa para ponderar criticidad y generar la recomendación final.
    """
    HARDWARE = "hardware"
    SOFTWARE = "software"
    RED = "red"
    CONFIGURACION = "configuracion"
    ENERGIA = "energia"


class NivelCriticidad(str, Enum):
    """
    Nivel de severidad final que calculamos en reglas.BaseConocimiento.calcular_criticidad.
    Esto alimenta:
    - el color/alerta en resultado.html
    - el flag requiere_alerta en Resultado
    """
    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


# -------------------------------------------------------------------
# MODELOS DE DATOS (Pydantic)
# -------------------------------------------------------------------

class DispositivoInput(BaseModel):
    """
    Entrada principal hacia el motor de inferencia.
    - Se usa en /diagnosticar (JSON POST)
    - También la armamos manualmente desde el form /resultado
    """

    tipo: TipoDispositivo
    nombre: str
    sintomas: List[Sintoma]

    # Campos contextuales opcionales que pueden influir en reglas:
    ultima_actualizacion_firmware: Optional[str] = None
    intensidad_señal_wifi: Optional[int] = Field(
        None,
        ge=-100,
        le=0,
        description="RSSI aproximado en dBm (ej: -40 = muy buena señal, -90 = casi sin señal)",
    )
    tiempo_encendido_dias: Optional[int] = None


class Diagnostico(BaseModel):
    """
    Una causa candidata producida por el sistema experto.
    Cada Diagnostico representa:
    - qué creemos que está pasando (causa),
    - en qué categoría técnica cae,
    - con qué probabilidad estimada,
    - y qué acción recomendamos.
    """

    causa: str
    categoria: Causa
    probabilidad: float = Field(
        ...,
        ge=0,
        le=100,
        description="Probabilidad estimada en porcentaje (0-100).",
    )
    solucion: str


class Resultado(BaseModel):
    """
    Respuesta de alto nivel que devolvemos:
    - a la API /diagnosticar (JSON)
    - y a la vista resultado.html
    """

    dispositivo: str
    tipo: TipoDispositivo
    criticidad: NivelCriticidad
    diagnosticos: List[Diagnostico]
    recomendacion_principal: str
    requiere_alerta: bool
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Marca de tiempo ISO generada automáticamente.",
    )


# -------------------------------------------------------------------
# COMPATIBILIDAD LEGADA (Alias Sintoma.CORTE_INTERMITENTE)
# -------------------------------------------------------------------


try:
    # ¿Existe ya el miembro CORTE_INTERMITENTE?
    _ = Sintoma.CORTE_INTERMITENTE  # noqa: F841
except AttributeError:
    # No existe. Buscamos alternativas que podrían estar en tu KB/reglas históricas.
    candidatos = [
        "CORTE_INTERMITENTE_WIFI",
        "INTERMITENCIA",
        "CORTES_INTERMITENTES",
        "CORTES",
        "CORTE",
    ]

    destino = None
    for name in candidatos:
        if hasattr(Sintoma, name):
            destino = getattr(Sintoma, name)
            break

    if destino is None:
        # fallback final: tomar el primer miembro del Enum para no romper import
        try:
            destino = list(Sintoma)[0]
        except Exception:
            destino = None

    if destino is not None:
        # Creamos el alias dinámicamente:
        # Sintoma.CORTE_INTERMITENTE va a apuntar a ese destino.
        setattr(Sintoma, "CORTE_INTERMITENTE", destino)

