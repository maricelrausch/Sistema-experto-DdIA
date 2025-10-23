# app/interfaz/visual.py
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Tu motor y modelos
from app.modelos import DispositivoInput, TipoDispositivo, Sintoma, NivelCriticidad
from app.reglas import BaseConocimiento

# --- Rutas absolutas para que no dependan del cwd ---
INTERFAZ_DIR = Path(__file__).resolve().parent              # .../app/interfaz
TEMPLATES_DIR = INTERFAZ_DIR / "templates"                  # app/interfaz/templates
STATIC_DIR = INTERFAZ_DIR / "static"                        # app/interfaz/static

app = FastAPI(title="Interfaz IoT")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Instancia única del motor
BC = BaseConocimiento()

# ---------- Helpers ----------
def _parse_float(s: Optional[str]) -> Optional[float]:
    if s is None or str(s).strip() == "":
        return None
    try:
        return float(str(s).replace(",", "."))
    except Exception:
        return None

def _parse_int(s: Optional[str]) -> Optional[int]:
    if s is None or str(s).strip() == "":
        return None
    try:
        return int(str(s))
    except Exception:
        return None

# ---------- Rutas ----------
@app.get("/healthz")
def healthz():
    return {"status": "ok", "templates": str(TEMPLATES_DIR), "static": str(STATIC_DIR)}

from fastapi.responses import HTMLResponse, PlainTextResponse

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # Probar en este orden
    candidatos = ["index.html", "admin.kb.html"]
    contexto_base = {
        "request": request,
        # pasamos con TODOS los nombres típicos por compatibilidad
        "tipos": list(TipoDispositivo),
        "device_types": list(TipoDispositivo),   # alias
        "sintomas": list(Sintoma),
        "symptoms": list(Sintoma),               # alias
    }
    for tpl in candidatos:
        if (TEMPLATES_DIR / tpl).exists():
            try:
                return templates.TemplateResponse(tpl, contexto_base)
            except Exception as e:
                # Mostrar error de Jinja claramente en el navegador
                return PlainTextResponse(
                    f"Error renderizando {tpl}:\n{type(e).__name__}: {e}",
                    status_code=500,
                )

    archivos = [p.name for p in TEMPLATES_DIR.glob('*.html')]
    return HTMLResponse(
        f"<h3>No encontré ninguno de {candidatos} en {TEMPLATES_DIR}</h3>"
        f"<p>Encontré: {archivos}</p>",
        status_code=404,
    )


@app.post("/diagnosticar", response_class=HTMLResponse)
async def diagnosticar(
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form(...),
    # checkboxes o multiselect de síntomas
    sintomas: List[str] = Form(default=[]),
    # opcionales
    intensidad_senal_wifi: Optional[str] = Form(default=None),  # por si el form usa 'senal' sin ñ
    intensidad_señal_wifi: Optional[str] = Form(default=None),  # por si el form usa 'señal' con ñ
    tiempo_encendido_dias: Optional[str] = Form(default=None),
    ultima_actualizacion_firmware: Optional[str] = Form(default=None),
):
    # Resolver campo de señal (con/sin ñ)
    wifi_txt = intensidad_señal_wifi if intensidad_señal_wifi not in (None, "") else intensidad_senal_wifi
    wifi = _parse_float(wifi_txt)
    dias_on = _parse_int(tiempo_encendido_dias)

    # Mapear enums desde valores string del form
    try:
        tipo_enum = TipoDispositivo(tipo)
    except Exception:
        # fallback al primero si viene mal
        tipo_enum = list(TipoDispositivo)[0]

    sintomas_enum: List[Sintoma] = []
    for s in sintomas:
        try:
            sintomas_enum.append(Sintoma(s))
        except Exception:
            # ignorar síntomas desconocidos
            pass
    if not sintomas_enum:
        # al menos uno para que el motor tenga con qué trabajar
        sintomas_enum = [list(Sintoma)[0]]

    # Construir el dispositivo respetando tu modelo
    kwargs: Dict[str, Any] = dict(
        nombre=nombre.strip() or "Dispositivo",
        tipo=tipo_enum,
        sintomas=sintomas_enum,
    )

    # Campo firmware es Optional[str] en tu modelo -> pasar string o None
    if ultima_actualizacion_firmware and ultima_actualizacion_firmware.strip():
        kwargs["ultima_actualizacion_firmware"] = ultima_actualizacion_firmware.strip()

    # Señal WiFi (tu modelo usa 'intensidad_señal_wifi' con ñ)
    if wifi is not None:
        kwargs["intensidad_señal_wifi"] = wifi

    if dias_on is not None:
        kwargs["tiempo_encendido_dias"] = dias_on

    dispositivo = DispositivoInput(**kwargs)

    diags = BC.obtener_diagnosticos(dispositivo)
    crit = BC.calcular_criticidad(dispositivo, diags)

    return templates.TemplateResponse(
        "resultado.html",
        {
            "request": request,
            "dispositivo": dispositivo,
            "diagnosticos": diags,
            "criticidad": crit,
        },
    )
