# app/reglas.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Importes ABSOLUTOS (sirven en -m y en script si se ejecuta desde la raíz del proyecto)
from app.modelos import (
    DispositivoInput,
    Diagnostico,
    TipoDispositivo,
    Sintoma,
    Causa,
    NivelCriticidad,
)


class BaseConocimiento:
    def __init__(self, ruta_json: str | Path | None = None) -> None:
        """Inicializa la base de conocimiento desde un archivo JSON."""
        self.reglas: Dict[str, list] = {}
        self.reglas_dispositivo: Dict[str, dict] = {}

        try:
            if ruta_json is None:
                ruta_json = Path(__file__).resolve().parent / "data" / "base_conocimiento.json"
            ruta_json = Path(ruta_json)

            with ruta_json.open("r", encoding="utf-8") as f:
                conocimiento: Dict[str, Any] = json.load(f)

            self.reglas = conocimiento.get("reglas_por_sintoma", {}) or {}
            self.reglas_dispositivo = conocimiento.get("reglas_por_dispositivo", {}) or {}

            print(f"✅ Base de conocimiento cargada desde {ruta_json}")
        except Exception as e:
            print(f"❌ ERROR al cargar la base de conocimiento: {e}")
            self.reglas = {}
            self.reglas_dispositivo = {}

    # ------------------------------------------------------------------
    # Motor de inferencia
    # ------------------------------------------------------------------
    def obtener_diagnosticos(self, dispositivo: DispositivoInput) -> List[Diagnostico]:
        """Genera una lista de diagnósticos basados en los síntomas del dispositivo."""
        diagnosticos_raw: List[Diagnostico] = []

        # Soporte con/sin ñ
        intensidad_wifi: Optional[float] = getattr(dispositivo, "intensidad_señal_wifi", None)
        if intensidad_wifi is None:
            intensidad_wifi = getattr(dispositivo, "intensidad_senal_wifi", None)

        reglas_disp: Dict[str, Any] = self.reglas_dispositivo.get(dispositivo.tipo.value, {}) or {}

        for sintoma_enum in dispositivo.sintomas:
            sintoma_str = getattr(sintoma_enum, "value", str(sintoma_enum))
            reglas_sintoma = self.reglas.get(sintoma_str, [])

            for regla in reglas_sintoma:
                try:
                    prob_base = float(regla.get("probabilidad_base", 0))
                except Exception:
                    prob_base = 0.0

                try:
                    categoria = Causa(regla.get("categoria", ""))
                except Exception:
                    # Categoría desconocida: se ignora la regla
                    continue

                probabilidad_ajustada = prob_base

                # Factores por tipo de dispositivo
                if categoria == Causa.HARDWARE and "factor_hardware" in reglas_disp:
                    probabilidad_ajustada *= float(reglas_disp["factor_hardware"])
                elif categoria == Causa.RED and "factor_red" in reglas_disp:
                    probabilidad_ajustada *= float(reglas_disp["factor_red"])
                elif categoria == Causa.ENERGIA and "factor_energia" in reglas_disp:
                    probabilidad_ajustada *= float(reglas_disp["factor_energia"])
                elif categoria == Causa.SOFTWARE and "factor_software" in reglas_disp:
                    probabilidad_ajustada *= float(reglas_disp["factor_software"])

                # Señal WiFi (solo afecta a RED)
                if categoria == Causa.RED and intensidad_wifi is not None:
                    if intensidad_wifi < -80:
                        probabilidad_ajustada *= 1.3
                    elif intensidad_wifi > -60:
                        probabilidad_ajustada *= 0.7

                # Firmware actualizado reduce probabilidad de SOFTWARE
                fw = getattr(dispositivo, "ultima_actualizacion_firmware", None)
                if categoria == Causa.SOFTWARE and isinstance(fw, str) and fw.strip():
                    probabilidad_ajustada *= 0.9



                # Mucho tiempo encendido aumenta HARDWARE
                dias_on = getattr(dispositivo, "tiempo_encendido_dias", None)
                if categoria == Causa.HARDWARE and dias_on and dias_on > 90:
                    probabilidad_ajustada *= 1.2

                diagnosticos_raw.append(
                    Diagnostico(
                        causa=str(regla.get("causa", "desconocida")),
                        categoria=categoria,
                        probabilidad=min(max(round(probabilidad_ajustada, 2), 0.0), 100.0),
                        solucion=str(regla.get("solucion", "")),
                    )
                )

        # Deduplicar por causa: conservar la MAYOR probabilidad
        mejores_por_causa: Dict[str, Diagnostico] = {}
        for d in diagnosticos_raw:
            previo = mejores_por_causa.get(d.causa)
            if previo is None or d.probabilidad > previo.probabilidad:
                mejores_por_causa[d.causa] = d

        # Ordenar descendente por probabilidad
        return sorted(mejores_por_causa.values(), key=lambda x: x.probabilidad, reverse=True)

    # ------------------------------------------------------------------
    # Cálculo de criticidad
    # ------------------------------------------------------------------
    def calcular_criticidad(
        self, dispositivo: DispositivoInput, diagnosticos: List[Diagnostico]
    ) -> NivelCriticidad:
        """Determina el nivel de criticidad de un diagnóstico."""
        reglas_disp = self.reglas_dispositivo.get(dispositivo.tipo.value, {}) or {}
        sintomas_criticos = reglas_disp.get("sintomas_criticos", []) or []

        # 1) Síntomas críticos por tipo de dispositivo
        if any(getattr(s, "value", str(s)) in sintomas_criticos for s in dispositivo.sintomas):
            if dispositivo.tipo in [
                TipoDispositivo.CERRADURA_INTELIGENTE,
                TipoDispositivo.CAMARA_SEGURIDAD,
                TipoDispositivo.SENSOR_AGUA,
            ]:
                return NivelCriticidad.CRITICA
            return NivelCriticidad.ALTA

        # 2) Máxima probabilidad prioriza energía/hardware
        if diagnosticos:
            top = diagnosticos[0]
            if top.probabilidad > 80:
                if top.categoria in (Causa.ENERGIA, Causa.HARDWARE):
                    return NivelCriticidad.ALTA
                return NivelCriticidad.MEDIA

        # 3) Heurística por cantidad de síntomas
        if len(dispositivo.sintomas) >= 3:
            return NivelCriticidad.ALTA
        if len(dispositivo.sintomas) >= 2:
            return NivelCriticidad.MEDIA

        return NivelCriticidad.BAJA


# ----------------------------------------------------------------------
# Smoke test: ejecutar desde la RAÍZ del proyecto
#   - python -m app.reglas     (recomendado)
#   - python app\reglas.py     (también OK)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    base = BaseConocimiento()

    try:
        # 1) Enums reales (sin nombres hardcodeados)
        sintomas_all = list(Sintoma)
        tipos_all = list(TipoDispositivo)
        if not sintomas_all or not tipos_all:
            raise RuntimeError("Verificá que Sintoma y TipoDispositivo tengan miembros.")

        sintomas_demo = sintomas_all[:2] if len(sintomas_all) >= 2 else sintomas_all[:1]
        tipo_demo = tipos_all[0]

        # 2) Construir kwargs SOLO con campos válidos y necesarios
        kwargs: Dict[str, Any] = {
            "nombre": "Dispositivo Demo",
            "tipo": tipo_demo,
            "sintomas": sintomas_demo,
            # NO pasamos ultima_actualizacion_firmware (deja default None)
            "tiempo_encendido_dias": 120,
        }

        # Señal WiFi (tu modelo usa el campo con ñ)
        try:
            if hasattr(DispositivoInput, "model_fields"):
                if "intensidad_señal_wifi" in DispositivoInput.model_fields:  # pydantic v2
                    kwargs["intensidad_señal_wifi"] = -85
            elif hasattr(DispositivoInput, "__annotations__"):
                if "intensidad_señal_wifi" in DispositivoInput.__annotations__:
                    kwargs["intensidad_señal_wifi"] = -85
        except Exception:
            pass

        # 3) Instanciar y ejecutar
        dispositivo_demo = DispositivoInput(**kwargs)

        diags = base.obtener_diagnosticos(dispositivo_demo)
        print("🔎 Diagnósticos (top 5):")
        for d in diags[:5]:
            cat = getattr(d.categoria, "value", d.categoria)
            print(f" - {d.causa} | {cat} | {d.probabilidad}%")

        crit = base.calcular_criticidad(dispositivo_demo, diags)
        print(f"📶 Criticidad: {getattr(crit, 'value', crit)}")

    except Exception as e:
        # Apoyo: mostrar miembros reales y campos del modelo
        try:
            print("📚 Sintomas disponibles:", [s.name for s in Sintoma])
        except Exception:
            pass
        try:
            print("🧩 Tipos de dispositivo disponibles:", [t.name for t in TipoDispositivo])
        except Exception:
            pass
        try:
            if hasattr(DispositivoInput, "model_fields"):
                print("🧱 Campos del modelo (v2):", list(DispositivoInput.model_fields.keys()))
            elif hasattr(DispositivoInput, "__fields__"):
                print("🧱 Campos del modelo (v1):", list(DispositivoInput.__fields__.keys()))
            elif hasattr(DispositivoInput, "__annotations__"):
                print("🧱 Campos del modelo (ann):", list(DispositivoInput.__annotations__.keys()))
        except Exception:
            pass
        print(f"⚠️ Error en smoke test: {e}")
