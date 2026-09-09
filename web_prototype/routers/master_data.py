# -*- coding: utf-8 -*-
"""Endpoints de DATOS MAESTROS (Excel maestro, mapa TMX, tablas de la BD).

Por que existe este router
--------------------------
Los datos maestros del almacen (ubicaciones, catalogo de SKU, zonas de staging,
muelles) viven en `layouts/Warehouse_Logic.xlsx`, pero el motor NO los lee de
ahi: los lee de `warehouse.db`. El Excel solo se usa si la base no existe.

Consecuencia que este router viene a resolver: **editar el Excel no tenia
ningun efecto** hasta que alguien corriera `run_migration.py` por consola, y la
UI no avisaba de eso en ninguna parte. Los botones "Examinar" de la pestana
Layout y Datos, ademas, no hacian nada.

Flujo que se expone:
    subir  ->  validar (sin aplicar)  ->  aplicar (migrar a la BD)  ->  ver

Ver `docs/PLAN_DATOS_MAESTROS_WEB.md`.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from web_prototype.app_state import PROJECT_ROOT

router = APIRouter()

DB_PATH = os.path.join(PROJECT_ROOT, "warehouse.db")
UPLOADS_DIR = os.path.join(PROJECT_ROOT, "uploads")

# Hojas que el motor necesita, con sus columnas obligatorias.
# Espejo de lo que consume data_manager._load_excel_data / el importador.
HOJAS_REQUERIDAS: Dict[str, List[str]] = {
    "PickingLocations": ["x", "y", "pick_sequence", "WorkArea"],
}
HOJAS_OPCIONALES: Dict[str, List[str]] = {
    "SkuCatalog": ["sku_code", "volumen_m3", "peso_kg", "clase_manejo"],
    "OutboundStaging": ["staging_id", "x", "y"],
    "InboundDocks": ["dock_id", "x", "y"],
}

# Tablas de la BD que se pueden consultar, y la hoja de la que provienen.
TABLAS = {
    "locations": "PickingLocations",
    "sku_catalog": "SkuCatalog",
    "staging_areas": "OutboundStaging",
    "inbound_docks": "InboundDocks",
}


class AplicarRequest(BaseModel):
    """Aplica un Excel ya subido (o el vigente si no se pasa ninguno)."""
    excel_path: Optional[str] = None


def _conn():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404,
                            detail="No existe warehouse.db. Subi y aplica el Excel maestro.")
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _ruta_segura(rel: str) -> str:
    """Resuelve una ruta relativa al proyecto y bloquea path traversal."""
    resuelto = os.path.realpath(os.path.join(PROJECT_ROOT, rel))
    raiz = os.path.realpath(PROJECT_ROOT)
    if not resuelto.startswith(raiz + os.sep):
        raise HTTPException(status_code=400, detail="Ruta fuera del proyecto.")
    return resuelto


def _validar_excel(path: str) -> Dict[str, Any]:
    """Abre el Excel y comprueba hojas y columnas. NO aplica nada."""
    import openpyxl

    errores: List[str] = []
    avisos: List[str] = []
    resumen: Dict[str, int] = {}

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        return {"valido": False, "errores": ["No se pudo abrir el archivo: %s" % e],
                "avisos": [], "resumen": {}}

    def _columnas(hoja):
        fila = next(hoja.iter_rows(min_row=1, max_row=1, values_only=True), ())
        return [str(c).strip() for c in fila if c is not None]

    for hoja, requeridas in HOJAS_REQUERIDAS.items():
        if hoja not in wb.sheetnames:
            errores.append("Falta la hoja obligatoria '%s'." % hoja)
            continue
        ws = wb[hoja]
        cols = _columnas(ws)
        faltantes = [c for c in requeridas if c not in cols]
        if faltantes:
            errores.append("La hoja '%s' no tiene la(s) columna(s): %s."
                           % (hoja, ", ".join(faltantes)))
        resumen[hoja] = max(ws.max_row - 1, 0)

    for hoja, requeridas in HOJAS_OPCIONALES.items():
        if hoja not in wb.sheetnames:
            avisos.append("Sin la hoja '%s' (opcional): se usaran los valores por defecto."
                          % hoja)
            resumen[hoja] = 0
            continue
        ws = wb[hoja]
        cols = _columnas(ws)
        faltantes = [c for c in requeridas if c not in cols]
        if faltantes:
            errores.append("La hoja '%s' no tiene la(s) columna(s): %s."
                           % (hoja, ", ".join(faltantes)))
        resumen[hoja] = max(ws.max_row - 1, 0)

    wb.close()
    return {"valido": not errores, "errores": errores, "avisos": avisos, "resumen": resumen}


@router.post("/api/master-data/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    """Sube el Excel maestro y lo VALIDA. No toca la base todavia."""
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .xlsx")

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    destino = os.path.join(UPLOADS_DIR, "master_%s" % os.path.basename(file.filename))
    with open(destino, "wb") as f:
        f.write(await file.read())

    reporte = _validar_excel(destino)
    reporte["excel_path"] = os.path.relpath(destino, PROJECT_ROOT)
    reporte["nombre"] = os.path.basename(file.filename)
    return reporte


@router.post("/api/master-data/upload-tmx")
async def upload_tmx(file: UploadFile = File(...)):
    """Sube un mapa .tmx y comprueba que se pueda abrir."""
    if not file.filename.lower().endswith(".tmx"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .tmx")

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    destino = os.path.join(UPLOADS_DIR, "map_%s" % os.path.basename(file.filename))
    with open(destino, "wb") as f:
        f.write(await file.read())

    # Validacion minima sin cargar pygame: el TMX es XML con <map> y capas.
    try:
        import xml.etree.ElementTree as ET
        raiz = ET.parse(destino).getroot()
        if raiz.tag != "map":
            raise ValueError("el archivo no tiene un elemento <map> raiz")
        capas = [c.get("name") for c in raiz.findall("layer")]
        info = {
            "valido": True, "errores": [], "avisos": [],
            "resumen": {
                "ancho": int(raiz.get("width", 0)),
                "alto": int(raiz.get("height", 0)),
                "capas": len(capas),
            },
            "capas": capas,
        }
    except Exception as e:
        info = {"valido": False, "errores": ["TMX invalido: %s" % e],
                "avisos": [], "resumen": {}}

    info["tmx_path"] = os.path.relpath(destino, PROJECT_ROOT)
    info["nombre"] = os.path.basename(file.filename)
    return info


@router.post("/api/master-data/apply")
def aplicar_excel(request: AplicarRequest):
    """Importa el Excel a `warehouse.db` (el origen que SI lee el motor).

    Hace BACKUP de la base antes de tocarla. La importacion RECONSTRUYE las
    tablas: cualquier edicion hecha desde la web se reemplaza por lo que traiga
    el Excel, y el stock inicial vuelve al del archivo (decision del Director,
    2026-09-08).
    """
    from web_prototype.app_state import config_manager

    if request.excel_path:
        excel = _ruta_segura(request.excel_path)
    else:
        cfg = config_manager.load_config()
        excel = _ruta_segura(cfg.get("sequence_file", "layouts/Warehouse_Logic.xlsx"))

    if not os.path.exists(excel):
        raise HTTPException(status_code=404, detail="No se encontro el Excel: %s" % excel)

    reporte = _validar_excel(excel)
    if not reporte["valido"]:
        return {"success": False, "errors": reporte["errores"]}

    backup = None
    if os.path.exists(DB_PATH):
        backup = DB_PATH + ".bak"
        shutil.copy2(DB_PATH, backup)

    proc = subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "run_migration.py"), "--excel", excel],
        cwd=PROJECT_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=600,
    )

    if proc.returncode != 0:
        # Restaurar la base: mejor quedarse como estaba que a medio migrar.
        if backup and os.path.exists(backup):
            shutil.copy2(backup, DB_PATH)
        cola = "\n".join((proc.stdout or "").splitlines()[-15:])
        return {"success": False,
                "errors": ["La importacion fallo (se restauro la base anterior)."],
                "log": cola}

    return {
        "success": True,
        "excel": os.path.relpath(excel, PROJECT_ROOT),
        "backup": os.path.relpath(backup, PROJECT_ROOT) if backup else None,
        "resumen": _resumen_bd(),
        "log": "\n".join((proc.stdout or "").splitlines()[-15:]),
    }


def _resumen_bd() -> Dict[str, Any]:
    if not os.path.exists(DB_PATH):
        return {"disponible": False}
    conn = sqlite3.connect(DB_PATH)
    try:
        datos = {}
        for tabla in TABLAS:
            try:
                datos[tabla] = conn.execute("SELECT COUNT(*) FROM %s" % tabla).fetchone()[0]
            except sqlite3.Error:
                datos[tabla] = None
        return {"disponible": True, "conteos": datos,
                "actualizada": os.path.getmtime(DB_PATH)}
    finally:
        conn.close()


@router.get("/api/master-data/summary")
def resumen():
    """Que datos maestros esta usando el motor, y si el Excel quedo mas nuevo.

    El aviso de desactualizacion es la parte importante: sin el, alguien edita
    el Excel, no ve ningun cambio en los resultados y no entiende por que.
    """
    from web_prototype.app_state import config_manager

    info = _resumen_bd()
    try:
        cfg = config_manager.load_config()
        excel = _ruta_segura(cfg.get("sequence_file", "layouts/Warehouse_Logic.xlsx"))
        info["excel"] = os.path.relpath(excel, PROJECT_ROOT)
        if os.path.exists(excel):
            info["excel_actualizado"] = os.path.getmtime(excel)
            info["excel_mas_nuevo"] = (
                info.get("disponible", False)
                and info["excel_actualizado"] > info.get("actualizada", 0)
            )
        else:
            info["excel_existe"] = False
    except Exception as e:
        info["excel_error"] = str(e)
    return info


class Coordenada(BaseModel):
    """Una fila de las tablas chicas editables (zona de staging o muelle)."""
    id: int
    x: int
    y: int


class CoordenadasRequest(BaseModel):
    filas: List[Coordenada]


# Tablas chicas editables desde la web: (tabla, columna id, col x, col y).
# Solo estas: las grandes (ubicaciones, catalogo) se editan en el Excel, que es
# mejor herramienta para eso, y se traen con "Aplicar Excel".
EDITABLES = {
    "staging_areas": ("staging_id", "legacy_x", "legacy_y"),
    "inbound_docks": ("dock_id", "x", "y"),
}


def _mapa_para_validar():
    """(ancho, alto, es_transitable) del mapa TMX vigente, o (None, None, None).

    Se usa el LayoutManager REAL del motor en vez de reinterpretar el TMX aca:
    es la misma fuente de verdad que valida las coordenadas al correr. Si no se
    puede cargar (falta el archivo, falta una dependencia), se degrada a no
    validar geometria en vez de bloquear el guardado.
    """
    try:
        src_dir = os.path.join(PROJECT_ROOT, "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from web_prototype.app_state import config_manager
        from subsystems.simulation.layout_manager import LayoutManager

        tmx = config_manager.load_config().get("layout_file", "layouts/WH1.tmx")
        lm = LayoutManager(_ruta_segura(tmx), headless=True)
        return lm.grid_width, lm.grid_height, lm.is_walkable
    except Exception as e:
        print("[MASTER-DATA][WARN] No se pudo cargar el mapa para validar: %s" % e)
        return None, None, None


def _guardar_coordenadas(tabla: str, filas: List[Coordenada]) -> Dict[str, Any]:
    col_id, col_x, col_y = EDITABLES[tabla]

    ids = [f.id for f in filas]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=400, detail="Hay identificadores repetidos.")
    for f in filas:
        if f.x < 0 or f.y < 0:
            raise HTTPException(status_code=400,
                                detail="Coordenadas negativas en el id %s." % f.id)

    # Contra el MAPA: el motor exige que estas coordenadas caigan dentro de la
    # grilla del TMX y aborta la corrida si no (DataManagerError). Sin este
    # chequeo, la web aceptaba un valor invalido y el error recien aparecia al
    # simular, lejos de donde se cometio.
    ancho, alto, transitable = _mapa_para_validar()
    if ancho is not None:
        fuera = [f for f in filas if not (0 <= f.x < ancho and 0 <= f.y < alto)]
        if fuera:
            raise HTTPException(
                status_code=400,
                detail=("Fuera del mapa (%d x %d): %s. Corregi las coordenadas."
                        % (ancho, alto,
                           ", ".join("id %s -> (%s, %s)" % (f.id, f.x, f.y) for f in fuera))))

        if transitable is not None:
            bloqueadas = []
            for f in filas:
                try:
                    if not transitable(f.x, f.y):
                        bloqueadas.append(f)
                except Exception:
                    pass  # ante la duda, no bloquear el guardado
            if bloqueadas:
                raise HTTPException(
                    status_code=400,
                    detail=("Estas celdas no son transitables en el mapa (hay un rack o "
                            "una pared): %s. Los agentes no podrian llegar."
                            % ", ".join("id %s -> (%s, %s)" % (f.id, f.x, f.y)
                                        for f in bloqueadas)))

    conn = _conn()
    try:
        existentes = {r[col_id] for r in conn.execute(
            "SELECT %s FROM %s" % (col_id, tabla))}
        desconocidos = [i for i in ids if i not in existentes]
        if desconocidos:
            raise HTTPException(
                status_code=400,
                detail=("Estos identificadores no existen: %s. Para agregar o quitar "
                        "filas, editalos en el Excel y usa 'Aplicar Excel'."
                        % ", ".join(str(d) for d in desconocidos)))

        for f in filas:
            conn.execute("UPDATE %s SET %s = ?, %s = ? WHERE %s = ?"
                         % (tabla, col_x, col_y, col_id), (f.x, f.y, f.id))
        conn.commit()
        return {"success": True, "actualizadas": len(filas)}
    finally:
        conn.close()


@router.put("/api/master-data/staging-areas")
def guardar_staging(request: CoordenadasRequest):
    """Actualiza las coordenadas de las zonas de salida.

    OJO: escribe en `warehouse.db`, no en el Excel. Un "Aplicar Excel" posterior
    reemplaza estos valores por los del archivo (decision del Director,
    2026-09-08: el Excel manda, avisando antes).
    """
    return _guardar_coordenadas("staging_areas", request.filas)


@router.put("/api/master-data/inbound-docks")
def guardar_docks(request: CoordenadasRequest):
    """Actualiza las coordenadas de los muelles de recepcion. Ver nota de arriba."""
    return _guardar_coordenadas("inbound_docks", request.filas)


@router.get("/api/master-data/table/{nombre}")
def leer_tabla(nombre: str, limit: int = 50, offset: int = 0, q: str = ""):
    """Contenido paginado de una tabla de datos maestros (solo lectura)."""
    if nombre not in TABLAS:
        raise HTTPException(status_code=404,
                            detail="Tabla desconocida. Validas: %s" % ", ".join(TABLAS))
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    conn = _conn()
    try:
        columnas = [r["name"] for r in conn.execute("PRAGMA table_info(%s)" % nombre)]
        where, params = "", []
        if q:
            # Busqueda simple sobre las columnas de texto.
            textos = [c for c in columnas if c.lower().endswith(("code", "class", "area", "group", "name"))]
            if textos:
                where = " WHERE " + " OR ".join("CAST(%s AS TEXT) LIKE ?" % c for c in textos)
                params = ["%%%s%%" % q] * len(textos)

        total = conn.execute("SELECT COUNT(*) FROM %s%s" % (nombre, where), params).fetchone()[0]
        filas = conn.execute(
            "SELECT * FROM %s%s LIMIT ? OFFSET ?" % (nombre, where), params + [limit, offset]
        ).fetchall()
        return {
            "tabla": nombre,
            "hoja": TABLAS[nombre],
            "columnas": columnas,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filas": [dict(f) for f in filas],
        }
    finally:
        conn.close()
