# app/main.py — API FastAPI del Sistema Experto IoT
#
# Responsabilidades:
# - Exponer endpoints HTML (panel, formulario, resultado, tablas, stats)
# - Exponer endpoints JSON (diagnosticar, stats API, etc.)
# - Persistir casos diagnosticados para métricas
# - Administrar la base de conocimiento (KB)
#
# IMPORTANTE: Uvicorn arranca esto como:
#   uvicorn app.main:app --reload

from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import Counter
from datetime import datetime
import json, os, tempfile, shutil

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.modelos import (
    DispositivoInput,
    Resultado,
    TipoDispositivo,
    Sintoma,
    NivelCriticidad,
)
from app.reglas import BaseConocimiento


# -------------------------------------------------------------------
# Rutas base (paths locales)
# -------------------------------------------------------------------
BASE_DIR     = Path(__file__).resolve().parent          # app/
TEMPLATE_DIR = BASE_DIR / "templates"                   # app/templates
STATIC_DIR   = BASE_DIR / "static"                      # app/static
DATA_DIR     = BASE_DIR / "data"                        # app/data

KB_PATH      = DATA_DIR / "base_conocimiento.json"      # matriz de reglas editable
CASES_PATH   = DATA_DIR / "casos_no_diagnosticados.json"  # historial de casos/diag


# -------------------------------------------------------------------
# Inicializar FastAPI, static y templates
# -------------------------------------------------------------------
app = FastAPI(
    title="SISTEMA EXPERTO IoT",
    description="API para diagnóstico inteligente de dispositivos IoT",
    version="2.0.0",
)

# servir CSS y assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# motor de plantillas HTML (Jinja2)
TEMPLATES = Jinja2Templates(directory=str(TEMPLATE_DIR))


# -------------------------------------------------------------------
# Utilidades internas de lectura/escritura JSON
# -------------------------------------------------------------------
def _read_json_safe(path: Path, default):
    """
    Lee un archivo JSON y devuelve su contenido.
    Si no existe o está corrupto, devuelve `default`.
    """
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_write_json(path: Path, payload: dict | list):
    """
    Escritura segura:
    1. Escribe en un archivo temporal.
    2. Mueve ese archivo temporal al destino.
    Evita archivos corruptos si la app se interrumpe en medio.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="kb_", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        shutil.move(tmp, path)
    finally:
        # cleanup por las dudas
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def read_kb() -> Dict[str, Any]:
    """
    Devuelve la KB en memoria con estructura garantizada.
    Estructura esperada:
    {
      "sintomas": {
        "CODIGO_SINTOMA": {
          "causas": [
            { "causa": "...", "categoria": "...", "prob": 0.7, "solucion": "..." },
            ...
          ]
        }
      },
      "dispositivos": {
        "TIPO_DISPOSITIVO": {
          "factores": { "factor_red": 1.1, ... },
          "sintomas_criticos": ["NO_RESPONDE", ...]
        }
      }
    }
    """
    kb = _read_json_safe(
        KB_PATH,
        default={"sintomas": {}, "dispositivos": {}}
    )
    kb.setdefault("sintomas", {})
    kb.setdefault("dispositivos", {})
    return kb


def write_kb(kb: Dict[str, Any]):
    """
    Guarda la KB en disco de forma atómica.
    """
    atomic_write_json(KB_PATH, kb)


def _append_case(payload: dict):
    """
    Agrega un caso diagnosticado al historial que usamos para:
    - /casos/diagnosticados
    - /api/stats
    """
    casos = _read_json_safe(CASES_PATH, default=[])
    casos.append(payload)
    atomic_write_json(CASES_PATH, casos)


# -------------------------------------------------------------------
# Motor del sistema experto
# -------------------------------------------------------------------
base_conocimiento = BaseConocimiento()


def obtener_descripcion_sintoma(sintoma: Sintoma) -> str:
    """
    Texto amigable para mostrar al usuario humano en el formulario.
    (Esto es puramente de presentación.)
    """
    descripciones = {
        Sintoma.NO_RESPONDE: "El dispositivo no reacciona a comandos ni muestra actividad.",
        Sintoma.ERROR_CONEXION: "Fallas recurrentes al conectar con WiFi o servidor cloud.",
        Sintoma.REINICIOS_FRECUENTES: "El dispositivo se apaga y enciende sin intervención.",
        Sintoma.CONSUMO_ANOMALO: "Consumo eléctrico fuera de especificaciones normales.",
        Sintoma.LATENCIA_ALTA: "Retardo superior a 2 segundos en responder comandos.",
        Sintoma.FALLA_AUTENTICACION: "Errores de login, tokens inválidos o acceso denegado.",
    }
    return descripciones.get(sintoma, "Sin descripción.")


# -------------------------------------------------------------------
# Rutas públicas (JSON / API técnica)
# -------------------------------------------------------------------

@app.post("/diagnosticar", response_model=Resultado)
def diagnosticar_dispositivo(dispositivo: DispositivoInput):
    """
    Endpoint técnico (JSON IN → JSON OUT)
    - Recibe un dispositivo con síntomas.
    - Ejecuta el motor experto.
    - Calcula criticidad y recomendación.
    - Loguea el caso para estadísticas.
    """
    if not dispositivo.sintomas:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos un síntoma."
        )

    diagnosticos = base_conocimiento.obtener_diagnosticos(dispositivo)
    if not diagnosticos:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron diagnósticos para los síntomas."
        )

    criticidad = base_conocimiento.calcular_criticidad(dispositivo, diagnosticos)
    requiere_alerta = (criticidad == NivelCriticidad.CRITICA)

    diag_principal = diagnosticos[0]
    recomendacion = f"[{diag_principal.categoria.value.upper()}] {diag_principal.solucion}"
    if requiere_alerta:
        recomendacion = f"⚠️ URGENTE: {recomendacion}"

    # Guardamos el caso para /stats y /casos
    try:
        _append_case({
            "nombre": dispositivo.nombre,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tipo_dispositivo": getattr(dispositivo.tipo, "value", str(dispositivo.tipo)),
            "sintomas": [getattr(s, "value", str(s)) for s in dispositivo.sintomas],
            "categoria_top": getattr(diagnosticos[0].categoria, "value", None) if diagnosticos else None,
            "criticidad": getattr(criticidad, "value", str(criticidad)),
        })
    except Exception:
        # si falla el log, seguimos igual (no rompemos el diagnóstico)
        pass

    return Resultado(
        dispositivo=dispositivo.nombre,
        tipo=dispositivo.tipo,
        criticidad=criticidad,
        diagnosticos=diagnosticos[:5],
        recomendacion_principal=recomendacion,
        requiere_alerta=requiere_alerta,
    )


@app.post("/diagnosticar/lote")
def diagnosticar_lote(items: List[DispositivoInput]):
    """
    Endpoint batch:
    - Recibe una lista de dispositivos.
    - Devuelve una lista de diagnósticos resumidos.
    - Loguea cada caso.
    """
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

        # log de caso
        try:
            _append_case({
                "tipo_dispositivo": getattr(dispositivo.tipo, "value", str(dispositivo.tipo)),
                "sintomas": [getattr(s, "value", str(s)) for s in dispositivo.sintomas],
                "categoria_top": getattr(diagnosticos[0].categoria, "value", None) if diagnosticos else None,
                "criticidad": getattr(criticidad, "value", str(criticidad)),
            })
        except Exception:
            pass

        resultados.append({
            "dispositivo": dispositivo.nombre,
            "tipo": dispositivo.tipo.value if hasattr(dispositivo.tipo, "value") else str(dispositivo.tipo),
            "criticidad": getattr(criticidad, "value", str(criticidad)),
            "recomendacion_principal": recomendacion,
            "requiere_alerta": requiere_alerta,
        })

    return {
        "procesados": len(resultados),
        "resultados": resultados,
    }


@app.get("/sintomas")
def listar_sintomas():
    """
    Devuelve lista de síntomas posibles (para usar en front, selects, etc.).
    """
    return {
        "sintomas": [
            {
                "valor": s.value,
                "nombre": s.name,
                "descripcion": obtener_descripcion_sintoma(s),
            }
            for s in Sintoma
        ]
    }


@app.get("/dispositivos")
def listar_dispositivos():
    """
    Devuelve lista de tipos de dispositivos posibles.
    """
    return {
        "dispositivos": [
            {"tipo": t.value, "nombre": t.name}
            for t in TipoDispositivo
        ]
    }


# -------------------------------------------------------------------
# API para métricas (la consume stats.html con fetch("/api/stats"))
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
        if td:
            by_device[td] += 1

        for s in c.get("sintomas", []):
            by_symptom[s] += 1

        cat = c.get("categoria_top")
        if cat:
            by_category[cat] += 1

        crit = c.get("criticidad")
        if crit:
            by_criticidad[crit] += 1

    return JSONResponse({
        "n_casos": len(casos),
        "by_device": dict(by_device.most_common(10)),
        "by_symptom": dict(by_symptom.most_common(15)),
        "by_category": dict(by_category.most_common()),
        "by_criticidad": dict(by_criticidad.most_common()),
    })


@app.get("/api/casos")
def api_listar_casos():
    """
    Devuelve el JSON crudo de casos guardados.
    Útil para debug sin UI.
    """
    return _read_json_safe(CASES_PATH, default=[])


@app.post("/reset-casos")
def reset_casos():
    """
    Borra TODOS los casos registrados.
    Se usa desde la UI cuando tocás "🗑️ Limpiar casos".
    """
    atomic_write_json(CASES_PATH, [])
    return {"mensaje": "Casos eliminados correctamente"}


@app.post("/delete-caso/{idx}")
def delete_caso(idx: int):
    """
    Elimina UN caso puntual por índice 1-based (el número que ves en la tabla).
    """
    try:
        casos = _read_json_safe(CASES_PATH, default=[])
        real_index = idx - 1  # porque en pantalla mostramos desde 1
        if real_index < 0 or real_index >= len(casos):
            raise HTTPException(status_code=404, detail="Caso no encontrado")

        casos.pop(real_index)
        atomic_write_json(CASES_PATH, casos)

        return {"ok": True, "msg": f"Caso {idx} eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo eliminar: {e}")


# -------------------------------------------------------------------
# Admin de la Base de Conocimiento (KB)
# -------------------------------------------------------------------
@app.get("/admin/kb", response_class=HTMLResponse)
def admin_kb(request: Request, mensaje: Optional[str] = None):
    """
    Render de la vista admin_kb.html para editar reglas/síntomas/dispositivos.
    """
    return TEMPLATES.TemplateResponse(
        "admin_kb.html",
        {
            "request": request,
            "mensaje": mensaje,
        },
    )


@app.post("/admin/sintoma/nuevo")
def admin_sintoma_nuevo(
    codigo: str = Form(...),
    causa: str = Form(...),
    categoria: str = Form(...),
    prob: float = Form(...),
    solucion: str = Form(...),
):
    """
    Agrega o actualiza una causa dentro de un síntoma en la KB.
    prob se espera en [0.0, 1.0]
    """
    codigo = codigo.strip().upper()
    categoria = categoria.strip().upper()

    if not (0.0 <= prob <= 1.0):
        return RedirectResponse(
            "/admin/kb?mensaje=Probabilidad%20inv%C3%A1lida",
            status_code=303,
        )

    kb = read_kb()
    kb["sintomas"].setdefault(codigo, {"causas": []})

    # Intentar ver si ya existe esa causa para ese síntoma
    existente = None
    for c in kb["sintomas"][codigo]["causas"]:
        if c.get("causa", "").strip().lower() == causa.strip().lower():
            existente = c
            break

    nueva = {
        "causa": causa.strip(),
        "categoria": categoria,
        "prob": prob,
        "solucion": solucion.strip(),
    }

    if existente:
        existente.update(nueva)
    else:
        kb["sintomas"][codigo]["causas"].append(nueva)

    write_kb(kb)
    return RedirectResponse(
        "/admin/kb?mensaje=S%C3%ADntoma%20guardado",
        status_code=303,
    )


@app.post("/admin/dispositivo/nuevo")
def admin_dispositivo_nuevo(
    tipo: str = Form(...),
    factores: str = Form(...),
    sintomas_criticos: Optional[str] = Form(None),
):
    """
    Actualiza/crea configuración por tipo de dispositivo:
    - factores de ajuste de probabilidad por categoría
    - lista de síntomas críticos
    """
    tipo = tipo.strip().upper()

    # factores viene como JSON en texto (ej: {"factor_red":1.2,"factor_hardware":1.5})
    try:
        factores_dict = json.loads(factores)
    except Exception:
        return RedirectResponse(
            "/admin/kb?mensaje=Factores%20JSON%20inv%C3%A1lido",
            status_code=303,
        )

    crit_list = []
    if sintomas_criticos:
        crit_list = [
            s.strip().upper()
            for s in sintomas_criticos.split(",")
            if s.strip()
        ]

    kb = read_kb()
    kb["dispositivos"][tipo] = {
        "factores": factores_dict,
        "sintomas_criticos": crit_list,
    }
    write_kb(kb)

    return RedirectResponse(
        "/admin/kb?mensaje=Dispositivo%20guardado",
        status_code=303,
    )


# -------------------------------------------------------------------
# Rutas HTML (interfaz humana)
# -------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root_redirect():
    """
    Redirige la raíz al panel principal.
    """
    return RedirectResponse(url="/panel", status_code=303)


@app.get("/panel", response_class=HTMLResponse)
def ver_panel(request: Request):
    """
    Pantalla principal tipo "dashboard" con las tres tarjetas:
    - Agregar diagnóstico
    - Ver estadísticas
    - Tabla de diagnósticos
    """
    return TEMPLATES.TemplateResponse(
        "panel.html",
        {
            "request": request,
        },
    )


@app.get("/nuevo", response_class=HTMLResponse)
def nuevo_diagnostico(request: Request):
    """
    Formulario HTML para cargar un nuevo diagnóstico manualmente.
    Este template usa 'dispositivos' y 'sintomas' para armar el <select>
    y los checkboxes.
    """
    try:
        return TEMPLATES.TemplateResponse(
            "index.html",
            {
                "request": request,
                "dispositivos": list(TipoDispositivo),
                "sintomas": list(Sintoma),
            },
        )
    except Exception as e:
        # fallback para debug
        return HTMLResponse(
            content=f"<pre>ERROR EN /nuevo:\n{e}</pre>",
            status_code=500,
        )


@app.post("/resultado", response_class=HTMLResponse)
def resultado_html(
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form(...),
    sintomas: Optional[List[str]] = Form(None),
    intensidad_wifi: Optional[str] = Form(None),      # actualmente no usamos pero se recibe
    tiempo_encendido: Optional[str] = Form(None),     # idem
):
    """
    Procesa el form de /nuevo:
    - Construye DispositivoInput con los datos del form.
    - Aplica las reglas.
    - Renderiza resultado.html (bonito para el humano).
    """
    dispositivo = DispositivoInput(
        nombre=nombre,
        tipo=TipoDispositivo(tipo),
        sintomas=[Sintoma(s) for s in (sintomas or [])],
    )

    diagnosticos = base_conocimiento.obtener_diagnosticos(dispositivo)
    if not diagnosticos:
        return TEMPLATES.TemplateResponse(
            "resultado.html",
            {
                "request": request,
                "error": "No se encontraron diagnósticos para los síntomas ingresados.",
            },
            status_code=404,
        )

    criticidad = base_conocimiento.calcular_criticidad(dispositivo, diagnosticos)
    requiere_alerta = (criticidad == NivelCriticidad.CRITICA)

    diag_principal = diagnosticos[0]
    recomendacion = f"[{diag_principal.categoria.value.upper()}] {diag_principal.solucion}"
    if requiere_alerta:
        recomendacion = f"⚠️ URGENTE: {recomendacion}"

    # Guardamos caso también desde el flujo HTML
    try:
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

    return TEMPLATES.TemplateResponse(
        "resultado.html",
        {
            "request": request,
            "resultado": resultado,
        },
    )


@app.get("/casos/diagnosticados", response_class=HTMLResponse)
def ver_casos(request: Request):
    """
    Página HTML con la tabla de casos ya diagnosticados.
    Usa casos.html.
    """
    casos = _read_json_safe(CASES_PATH, default=[])
    tabla = []
    for i, c in enumerate(casos, start=1):
        tabla.append({
            "n": i,
            "tipo_dispositivo": c.get("tipo_dispositivo") or "—",
            "sintomas": c.get("sintomas") or [],
            "categoria_top": c.get("categoria_top") or "—",
            "criticidad": c.get("criticidad") or "—",
            "nombre": c.get("nombre") or "",
            "fecha":  c.get("fecha")  or "",
        })

    return TEMPLATES.TemplateResponse(
        "casos.html",
        {
            "request": request,
            "casos": tabla,
        },
    )


@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request):
    """
    Página con los gráficos Chart.js (stats.html).
    Ese template luego hace fetch a /api/stats.
    """
    return TEMPLATES.TemplateResponse(
        "stats.html",
        {
            "request": request,
        },
    )


# -------------------------------------------------------------------
# Rutas utilitarias / debug opcionales
# -------------------------------------------------------------------

@app.get("/__routes")
def __routes():
    """
    Devuelve todas las rutas registradas (debug).
    """
    return JSONResponse([getattr(r, "path", None) for r in app.routes])


@app.get("/healthz")
def healthz():
    """
    Chequeo rápido de salud de la API.
    """
    return {"status": "ok"}


# -------------------------------------------------------------------
# Ejecutar con python app/main.py directamente (opcional)
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
