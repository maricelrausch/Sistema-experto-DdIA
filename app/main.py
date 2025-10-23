# app/main.py — Archivo principal de FastAPI con todos los endpoints.

from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import Counter
import json, os, tempfile, shutil

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.modelos import DispositivoInput, Resultado, TipoDispositivo, Sintoma, NivelCriticidad
from app.reglas import BaseConocimiento




# -------------------------------------------------------------------
# Paths (ajustados a la nueva estructura: app/static, app/templates, app/data)
# -------------------------------------------------------------------
BASE_DIR     = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR   = BASE_DIR / "static"
DATA_DIR     = BASE_DIR / "data"

KB_PATH      = DATA_DIR / "base_conocimiento.json"
CASES_PATH   = DATA_DIR / "casos_no_diagnosticados.json"

# -------------------------------------------------------------------
# App + Static + Templates
# -------------------------------------------------------------------
app = FastAPI(
    title="SISTEMA EXPERTO IoT",
    description="API PARA DIAGNOSTICO INTELIGENTE DE DISPOSITIVOS INTELIGENTES DEL HOGAR",
    version="2.0.0"
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
TEMPLATES = Jinja2Templates(directory=str(TEMPLATE_DIR))

# -------------------------------------------------------------------
# Utilidades JSON (lectura/escritura segura)
# -------------------------------------------------------------------
def _read_json_safe(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def atomic_write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="kb_", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        shutil.move(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def read_kb() -> Dict[str, Any]:
    kb = _read_json_safe(KB_PATH, default={"sintomas": {}, "dispositivos": {}})
    kb.setdefault("sintomas", {})
    kb.setdefault("dispositivos", {})
    return kb

def write_kb(kb: Dict[str, Any]):
    atomic_write_json(KB_PATH, kb)

def _append_case(payload: dict):
    casos = _read_json_safe(CASES_PATH, default=[])
    casos.append(payload)
    CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CASES_PATH.write_text(json.dumps(casos, ensure_ascii=False, indent=2), encoding="utf-8")

# -------------------------------------------------------------------
# Motor del sistema experto
# -------------------------------------------------------------------
base_conocimiento = BaseConocimiento()

def obtener_descripcion_sintoma(sintoma: Sintoma) -> str:
    descripciones = {
        Sintoma.NO_RESPONDE: "El dispositivo no reacciona a comandos ni muestra actividad.",
        Sintoma.ERROR_CONEXION: "Fallas recurrentes al conectar con WiFi o servidor cloud.",
        Sintoma.REINICIOS_FRECUENTES: "El dispositivo se apaga y enciende sin intervención.",
        Sintoma.CONSUMO_ANOMALO: "Consumo eléctrico fuera de especificaciones normales.",
        Sintoma.LATENCIA_ALTA: "Retardo superior a 2 segundos en responder comandos.",
        Sintoma.FALLA_AUTENTICACION: "Errores de login, tokens inválidos o acceso denegado."
    }
    return descripciones.get(sintoma, "Sin descripción.")

# -------------------------------------------------------------------
# Endpoints públicos
# -------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse(url="/panel", status_code=303)


@app.post("/diagnosticar", response_model=Resultado)
def diagnosticar_dispositivo(dispositivo: DispositivoInput):
    if not dispositivo.sintomas:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un síntoma.")

    diagnosticos = base_conocimiento.obtener_diagnosticos(dispositivo)
    if not diagnosticos:
        raise HTTPException(status_code=404, detail="No se encontraron diagnósticos para los síntomas.")

    criticidad = base_conocimiento.calcular_criticidad(dispositivo, diagnosticos)
    requiere_alerta = (criticidad == NivelCriticidad.CRITICA)

    diag_principal = diagnosticos[0]
    recomendacion = f"[{diag_principal.categoria.value.upper()}] {diag_principal.solucion}"
    if requiere_alerta:
        recomendacion = f"⚠️ URGENTE: {recomendacion}"

    # Guarda caso para /stats (best-effort)
    try:
        from datetime import datetime

        _append_case({
            "nombre": dispositivo.nombre,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tipo_dispositivo": getattr(dispositivo.tipo, "value", str(dispositivo.tipo)),
            "sintomas": [getattr(s, "value", str(s)) for s in dispositivo.sintomas],
            "categoria_top": getattr(diagnosticos[0].categoria, "value", None) if diagnosticos else None,
            "criticidad": getattr(criticidad, "value", str(criticidad))
        })

    except Exception as e:
        print(f"[LOG] No se pudo guardar el caso: {e}")

    return Resultado(
        dispositivo=dispositivo.nombre,
        tipo=dispositivo.tipo,
        criticidad=criticidad,
        diagnosticos=diagnosticos[:5],
        recomendacion_principal=recomendacion,
        requiere_alerta=requiere_alerta,
    )

@app.get("/sintomas")
def listar_sintomas():
    return {
        "sintomas": [
            {"valor": s.value, "nombre": s.name, "descripcion": obtener_descripcion_sintoma(s)}
            for s in Sintoma
        ]
    }

@app.get("/dispositivos")
def listar_dispositivos():
    return {
        "dispositivos": [{"tipo": t.value, "nombre": t.name} for t in TipoDispositivo]
    }

# -------------------------------------------------------------------
# API JSON para gráficos
# -------------------------------------------------------------------
@app.get("/api/stats")
def api_stats():
    casos = _read_json_safe(CASES_PATH, default=[])
    by_device = Counter()
    by_symptom = Counter()
    by_category = Counter()
    by_criticidad = Counter()

    for c in casos:
        td = c.get("tipo_dispositivo")
        if td: by_device[td] += 1

        for s in c.get("sintomas", []):
            by_symptom[s] += 1

        cat = c.get("categoria_top")
        if cat: by_category[cat] += 1

        crit = c.get("criticidad")
        if crit: by_criticidad[crit] += 1

    return JSONResponse({
        "n_casos": len(casos),
        "by_device": dict(by_device.most_common(10)),
        "by_symptom": dict(by_symptom.most_common(15)),
        "by_category": dict(by_category.most_common()),
        "by_criticidad": dict(by_criticidad.most_common()),
    })


# -------------------------------------------------------------------
# Página de gráficos (Chart.js inline)
# -------------------------------------------------------------------
@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request):
    return TEMPLATES.TemplateResponse("stats.html", {"request": request})

# raíz única
@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse(url="/panel", status_code=303)

# panel
@app.get("/panel", response_class=HTMLResponse)
def ver_panel(request: Request):
    return TEMPLATES.TemplateResponse("panel.html", {"request": request})

# tabla de casos
@app.get("/casos/diagnosticados", response_class=HTMLResponse)
def ver_casos(request: Request):
    casos = _read_json_safe(CASES_PATH, default=[])
    norm = []
    for i, c in enumerate(casos, start=1):
        norm.append({
            "n": i,
            "tipo_dispositivo": c.get("tipo_dispositivo") or "—",
            "sintomas": c.get("sintomas") or [],
            "categoria_top": c.get("categoria_top") or "—",
            "criticidad": c.get("criticidad") or "—",
            "nombre": c.get("nombre") or "",
            "fecha":  c.get("fecha")  or "",
        })
    return TEMPLATES.TemplateResponse("casos.html", {"request": request, "casos": norm})

# -------------------------------------------------------------------
# Administración de KB
# -------------------------------------------------------------------
@app.get("/admin/kb", response_class=HTMLResponse)
def admin_kb(request: Request, mensaje: Optional[str] = None):
    return TEMPLATES.TemplateResponse("admin_kb.html", {"request": request, "mensaje": mensaje})

@app.post("/admin/sintoma/nuevo")
def admin_sintoma_nuevo(
    codigo: str = Form(...),
    causa: str = Form(...),
    categoria: str = Form(...),
    prob: float = Form(...),
    solucion: str = Form(...)
):
    codigo = codigo.strip().upper()
    categoria = categoria.strip().upper()
    if not (0.0 <= prob <= 1.0):
        return RedirectResponse("/admin/kb?mensaje=Probabilidad%20inv%C3%A1lida", status_code=303)

    kb = read_kb()
    kb["sintomas"].setdefault(codigo, {"causas": []})

    existente = None
    for c in kb["sintomas"][codigo]["causas"]:
        if c.get("causa","").strip().lower() == causa.strip().lower():
            existente = c
            break

    nueva = {"causa": causa.strip(), "categoria": categoria, "prob": prob, "solucion": solucion.strip()}
    if existente:
        existente.update(nueva)
    else:
        kb["sintomas"][codigo]["causas"].append(nueva)

    write_kb(kb)
    return RedirectResponse("/admin/kb?mensaje=S%C3%ADntoma%20guardado", status_code=303)

@app.post("/admin/dispositivo/nuevo")
def admin_dispositivo_nuevo(
    tipo: str = Form(...),
    factores: str = Form(...),
    sintomas_criticos: Optional[str] = Form(None)
):
    tipo = tipo.strip().upper()
    try:
        factores_dict = json.loads(factores)
    except Exception:
        return RedirectResponse("/admin/kb?mensaje=Factores%20JSON%20inv%C3%A1lido", status_code=303)

    crit_list = []
    if sintomas_criticos:
        crit_list = [s.strip().upper() for s in sintomas_criticos.split(",") if s.strip()]

    kb = read_kb()
    kb["dispositivos"][tipo] = {"factores": factores_dict, "sintomas_criticos": crit_list}
    write_kb(kb)
    return RedirectResponse("/admin/kb?mensaje=Dispositivo%20guardado", status_code=303)

# -------------------------------------------------------------------
# Carga por lote (array de diagnósticos)
# -------------------------------------------------------------------
@app.post("/diagnosticar/lote")
def diagnosticar_lote(items: List[DispositivoInput]):
    resultados = []
    for dispositivo in items:
        diagnosticos = base_conocimiento.obtener_diagnosticos(dispositivo)
        if not diagnosticos:
            continue

        criticidad = base_conocimiento.calcular_criticidad(dispositivo, diagnosticos)
        requiere_alerta = (criticidad == NivelCriticidad.CRITICA)

        diag_principal = diagnosticos[0]
        recomendacion = f"[{diag_principal.categoria.value.upper()}] {diag_principal.solucion}"
        if requiere_alerta:
            recomendacion = f"⚠️ URGENTE: {recomendacion}"

        try:
            _append_case({
                "tipo_dispositivo": getattr(dispositivo.tipo, "value", str(dispositivo.tipo)),
                "sintomas": [getattr(s, "value", str(s)) for s in dispositivo.sintomas],
                "categoria_top": getattr(diagnosticos[0].categoria, "value", None) if diagnosticos else None,
                "criticidad": getattr(criticidad, "value", str(criticidad))
            })
        except Exception:
            pass

        resultados.append({
            "dispositivo": dispositivo.nombre,
            "tipo": dispositivo.tipo.value if hasattr(dispositivo.tipo, "value") else str(dispositivo.tipo),
            "criticidad": getattr(criticidad, "value", str(criticidad)),
            "recomendacion_principal": recomendacion,
            "requiere_alerta": requiere_alerta
        })
    return {"procesados": len(resultados), "resultados": resultados}



@app.get("/casos/diagnosticados", response_class=HTMLResponse)
def ver_casos(request: Request):
    casos = _read_json_safe(CASES_PATH, default=[])
    norm = []
    for i, c in enumerate(casos, start=1):
        norm.append({
            "n": i,
            "tipo_dispositivo": c.get("tipo_dispositivo") or "—",
            "sintomas": c.get("sintomas") or [],
            "categoria_top": c.get("categoria_top") or "—",
            "criticidad": c.get("criticidad") or "—",
            "nombre": c.get("nombre") or "",
            "fecha":  c.get("fecha")  or "",
        })
    return TEMPLATES.TemplateResponse("casos.html", {"request": request, "casos": norm})

@app.get("/panel", response_class=HTMLResponse)
def ver_panel(request: Request):
    return TEMPLATES.TemplateResponse("panel.html", {"request": request})

from fastapi.responses import JSONResponse

@app.get("/__routes")
def __routes():
    return JSONResponse([getattr(r, "path", None) for r in app.routes])

@app.get("/api/casos")
def api_listar_casos():
    return _read_json_safe(CASES_PATH, default=[])

@app.get("/__casos_test", response_class=HTMLResponse)
def __casos_test(request: Request):
    fake = [{
        "n": 1,
        "tipo_dispositivo": "ROUTER",
        "sintomas": ["ERROR_CONEXION","LATENCIA_ALTA"],
        "categoria_top": "RED",
        "criticidad": "MEDIA",
        "nombre": "Demo",
        "fecha": "2025-10-23 16:45"
    }]
    return TEMPLATES.TemplateResponse("casos.html", {"request": request, "casos": fake})

@app.get("/form", response_class=HTMLResponse)
def ver_formulario(request: Request):
    dispositivos = list(TipoDispositivo)
    sintomas = list(Sintoma)
    return TEMPLATES.TemplateResponse(
        "index.html",
        {"request": request, "dispositivos": dispositivos, "sintomas": sintomas}
    )


@app.post("/resultado", response_class=HTMLResponse)
def resultado_html(
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form(...),
    sintomas: Optional[List[str]] = Form(None),
    intensidad_wifi: Optional[str] = Form(None),
    tiempo_encendido: Optional[str] = Form(None),
):
    # construir el dispositivo desde el form
    dispositivo = DispositivoInput(
        nombre=nombre,
        tipo=TipoDispositivo(tipo),
        sintomas=[Sintoma(s) for s in (sintomas or [])],
    )

    diagnosticos = base_conocimiento.obtener_diagnosticos(dispositivo)
    if not diagnosticos:
        return TEMPLATES.TemplateResponse(
            "resultado.html",
            {"request": request, "error": "No se encontraron diagnósticos para los síntomas ingresados."},
            status_code=404,
        )

    criticidad = base_conocimiento.calcular_criticidad(dispositivo, diagnosticos)
    requiere_alerta = (criticidad == NivelCriticidad.CRITICA)
    diag_principal = diagnosticos[0]
    recomendacion = f"[{diag_principal.categoria.value.upper()}] {diag_principal.solucion}"
    if requiere_alerta:
        recomendacion = f"⚠️ URGENTE: {recomendacion}"

    # guardar caso para la tabla/estadísticas
    try:
        from datetime import datetime
        _append_case({
            "nombre": dispositivo.nombre,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tipo_dispositivo": dispositivo.tipo.value,
            "sintomas": [s.value for s in dispositivo.sintomas],
            "categoria_top": diag_principal.categoria.value,
            "criticidad": criticidad.value,
        })
    except Exception:
        pass

    resultado = Resultado(
        dispositivo=dispositivo.nombre,
        tipo=dispositivo.tipo,
        criticidad=criticidad,
        diagnosticos=diagnosticos[:5],
        recomendacion_principal=recomendacion,
        requiere_alerta=requiere_alerta,
    )
    return TEMPLATES.TemplateResponse("resultado.html", {"request": request, "resultado": resultado})
from typing import Optional, List
from fastapi import Form

@app.post("/resultado", response_class=HTMLResponse)
def resultado_html(
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form(...),
    sintomas: Optional[List[str]] = Form(None),
    intensidad_wifi: Optional[str] = Form(None),
    tiempo_encendido: Optional[str] = Form(None),
):
    dispositivo = DispositivoInput(
        nombre=nombre,
        tipo=TipoDispositivo(tipo),
        sintomas=[Sintoma(s) for s in (sintomas or [])],
    )

    diagnosticos = base_conocimiento.obtener_diagnosticos(dispositivo)
    if not diagnosticos:
        return TEMPLATES.TemplateResponse(
            "resultado.html",
            {"request": request, "error": "No se encontraron diagnósticos para los síntomas ingresados."},
            status_code=404,
        )

    criticidad = base_conocimiento.calcular_criticidad(dispositivo, diagnosticos)
    requiere_alerta = (criticidad == NivelCriticidad.CRITICA)
    diag_principal = diagnosticos[0]
    recomendacion = f"[{diag_principal.categoria.value.upper()}] {diag_principal.solucion}"
    if requiere_alerta:
        recomendacion = f"⚠️ URGENTE: {recomendacion}"

    # guardar caso para tabla/estadísticas
    try:
        from datetime import datetime
        _append_case({
            "nombre": dispositivo.nombre,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tipo_dispositivo": dispositivo.tipo.value,
            "sintomas": [s.value for s in dispositivo.sintomas],
            "categoria_top": diag_principal.categoria.value,
            "criticidad": criticidad.value,
        })
    except Exception:
        pass

    resultado = Resultado(
        dispositivo=dispositivo.nombre,
        tipo=dispositivo.tipo,
        criticidad=criticidad,
        diagnosticos=diagnosticos[:5],
        recomendacion_principal=recomendacion,
        requiere_alerta=requiere_alerta,
    )
    return TEMPLATES.TemplateResponse("resultado.html", {"request": request, "resultado": resultado})

# -------------------------------------------------------------------
# Uvicorn (para ejecución directa) → usar app.main:app
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
