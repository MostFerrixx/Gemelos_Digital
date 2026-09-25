# -*- coding: utf-8 -*-
"""
Replica de una configuracion guardada (BK-36, decision del Director 2026-09-25).

Guardar una configuracion copia TODO lo necesario para volver a usarla tal
cual estaba: el mapa (con sus dependencias: tileset y su imagen), la base de
datos en uso (datos maestros + stock; puede diferir del Excel si se edito desde
la web), el Excel maestro (referencia), el archivo de pedidos y el ASN.

    data/config_presets/<id>.json          metadata + configuracion (original)
    data/config_presets/<id>/              la replica
        mapa/<mapa>.tmx (+ tileset/imagenes)
        datos/warehouse.db
        datos/<excel>.xlsx
        archivos/<pedidos>, archivos/<asn>

Cargar la configuracion restaura esa base como la base en uso (con respaldo)
y devuelve la configuracion apuntando a las copias.

Modulo sin FastAPI: lo usan config_manager y los routers.
"""
import hashlib
import os
import shutil
import sqlite3
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

VERSION = 1
# (ruta dentro de la config, subcarpeta de la replica)
ARCHIVOS = (
    (("layout_file",), "mapa"),
    (("sequence_file",), "datos"),
    (("order_file_path",), "archivos"),
    (("inbound", "asn_file_path"), "archivos"),
)


def _sha(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 16), b""):
            h.update(bloque)
    return h.hexdigest()


def _abs(raiz: str, ruta: str) -> str:
    return ruta if os.path.isabs(ruta) else os.path.join(raiz, ruta)


def _rel(raiz: str, ruta: str) -> str:
    return os.path.relpath(ruta, raiz).replace(os.sep, "/")


def _leer(config: Dict, clave) -> Optional[str]:
    valor = config
    for k in clave:
        if not isinstance(valor, dict):
            return None
        valor = valor.get(k)
    return valor if isinstance(valor, str) and valor.strip() else None


def _escribir(config: Dict, clave, valor: str) -> None:
    destino = config
    for k in clave[:-1]:
        destino = destino.setdefault(k, {})
    destino[clave[-1]] = valor


def dependencias_tmx(ruta_tmx: str) -> List[str]:
    """Archivos de los que depende un mapa de Tiled (tilesets externos .tsx y
    las imagenes), como rutas RELATIVAS a la carpeta del .tmx."""
    base = os.path.dirname(ruta_tmx)
    deps: List[str] = []

    def _imagenes(nodo, carpeta_rel):
        for img in nodo.iter("image"):
            src = img.get("source")
            if src:
                deps.append(os.path.normpath(os.path.join(carpeta_rel, src)))

    raiz = ET.parse(ruta_tmx).getroot()
    _imagenes(raiz, "")
    for ts in raiz.findall("tileset"):
        src = ts.get("source")
        if src:
            deps.append(os.path.normpath(src))
            tsx = os.path.join(base, src)
            if os.path.exists(tsx):
                _imagenes(ET.parse(tsx).getroot(), os.path.dirname(src))
    return sorted(set(deps))


def _copiar_base(origen: str, destino: str) -> None:
    """Copia consistente de SQLite (API de backup, aunque este en uso)."""
    src = sqlite3.connect(origen)
    dst = sqlite3.connect(destino)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def crear_replica(raiz: str, carpeta: str, config: Dict) -> Tuple[Dict, List[str]]:
    """Copia los archivos de `config` a `carpeta`. Devuelve (manifiesto, avisos)."""
    avisos: List[str] = []
    os.makedirs(carpeta, exist_ok=True)
    archivos: Dict[str, Dict] = {}
    for clave, sub in ARCHIVOS:
        ruta = _leer(config, clave)
        if not ruta:
            continue
        origen = _abs(raiz, ruta)
        if not os.path.exists(origen):
            avisos.append("No existe %s (%s): no se replica." % (".".join(clave), ruta))
            continue
        destino = os.path.join(carpeta, sub, os.path.basename(origen))
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copy2(origen, destino)
        if clave == ("layout_file",):
            for dep in dependencias_tmx(origen):
                if dep.startswith(".."):
                    avisos.append("El mapa usa %s fuera de su carpeta: no se replica." % dep)
                    continue
                o = os.path.join(os.path.dirname(origen), dep)
                if os.path.exists(o):
                    d = os.path.join(os.path.dirname(destino), dep)
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    shutil.copy2(o, d)
                else:
                    avisos.append("Falta %s (lo usa el mapa)." % dep)
        archivos[".".join(clave)] = {"original": ruta, "copia": _rel(raiz, destino),
                                     "sha256": _sha(destino)}

    base_origen = _abs(raiz, config.get("database_file") or "warehouse.db")
    base = None
    if os.path.exists(base_origen):
        destino = os.path.join(carpeta, "datos", "warehouse.db")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        _copiar_base(base_origen, destino)
        base = {"original": _rel(raiz, base_origen), "copia": _rel(raiz, destino)}
    else:
        avisos.append("No hay base de datos en uso (%s): no se replica." % base_origen)
    return {"version": VERSION, "carpeta": _rel(raiz, carpeta),
            "archivos": archivos, "base": base}, avisos


def config_con_copias(config: Dict, manifiesto: Optional[Dict]) -> Dict:
    """La configuracion apuntando a las copias de la replica."""
    import copy
    salida = copy.deepcopy(config)
    for clave_txt, info in ((manifiesto or {}).get("archivos") or {}).items():
        _escribir(salida, tuple(clave_txt.split(".")), info["copia"])
    return salida


def verificar(raiz: str, manifiesto: Optional[Dict]) -> List[str]:
    """Avisos si alguna copia falta o fue modificada despues de guardarse."""
    avisos = []
    for clave, info in ((manifiesto or {}).get("archivos") or {}).items():
        ruta = _abs(raiz, info["copia"])
        if not os.path.exists(ruta):
            avisos.append("Falta la copia de %s (%s)." % (clave, info["copia"]))
        elif _sha(ruta) != info.get("sha256"):
            avisos.append("La copia de %s cambio desde que se guardo." % clave)
    base = (manifiesto or {}).get("base")
    if base and not os.path.exists(_abs(raiz, base["copia"])):
        avisos.append("Falta la copia de la base de datos.")
    return avisos


def restaurar_base(raiz: str, manifiesto: Optional[Dict], destino_rel: str = "warehouse.db") -> Optional[str]:
    """Pone la base de la replica como base en uso. Respaldo previo en
    <base>.bak. Devuelve la ruta del respaldo (o None si no habia base)."""
    base = (manifiesto or {}).get("base")
    if not base:
        return None
    origen = _abs(raiz, base["copia"])
    destino = _abs(raiz, destino_rel)
    respaldo = None
    if os.path.exists(destino):
        # API de backup de SQLite, NO copia de archivo: la base usa WAL y los
        # cambios recientes viven en el -wal hasta el checkpoint.
        respaldo = destino + ".bak"
        _copiar_base(destino, respaldo)
    _copiar_base(origen, destino)
    return _rel(raiz, respaldo) if respaldo else None


def copia_temporal_de_base(raiz: str, manifiesto: Optional[Dict], carpeta_temp: str) -> Optional[str]:
    """Para experimentos A/B: una copia descartable de la base de la replica
    (cada corrida escribe en su base; la replica no se toca)."""
    import tempfile
    base = (manifiesto or {}).get("base")
    if not base:
        return None
    os.makedirs(carpeta_temp, exist_ok=True)
    fd, ruta = tempfile.mkstemp(prefix="replica_", suffix=".db", dir=carpeta_temp)
    os.close(fd)
    _copiar_base(_abs(raiz, base["copia"]), ruta)
    return _rel(raiz, ruta)
