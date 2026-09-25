# -*- coding: utf-8 -*-
"""
Validacion de un mapa TMX contra datos maestros (QA H-43, BK-36).

Modulo liviano (sin FastAPI ni estado del servidor): lo usan el router de
datos maestros y la validacion de configuraciones de config_manager. Misma
regla de transitabilidad que el motor (layout_manager).
"""
import os
import sqlite3
from typing import Any, Dict, List, Optional


def _celdas_bloqueadas(ruta: str, ancho: int, alto: int):
    """Misma regla que el motor (layout_manager): toda celda es transitable
    salvo que algun tile de una capa visible diga walkable=false."""
    import pytmx
    tmx = pytmx.TiledMap(ruta)
    bloqueadas = set()
    for idx, capa in enumerate(tmx.visible_layers):
        if not hasattr(capa, "data"):
            continue
        for y in range(alto):
            for x in range(ancho):
                try:
                    props = tmx.get_tile_properties(x, y, idx)
                except (AttributeError, IndexError, KeyError):
                    continue
                if not props:
                    continue
                w = props.get("walkable", "true")
                ok = w.lower() == "true" if isinstance(w, str) else bool(w)
                if not ok:
                    bloqueadas.add((x, y))
    return bloqueadas


def _n_puntos(lista) -> str:
    return "1 punto" if len(lista) == 1 else "%d puntos" % len(lista)


def _ejemplos(lista, n=5):
    return ", ".join(lista[:n]) + (" y %d mas" % (len(lista) - n) if len(lista) > n else "")


def _cruzar_puntos(puntos, ancho: int, alto: int, bloqueadas, origen: str) -> List[str]:
    """Errores si algun punto (etiqueta, id, x, y) cae fuera del mapa o sobre
    una celda bloqueada. `origen` dice de donde vienen los puntos."""
    errores = []
    fuera = ["%s %s (%d, %d)" % p for p in puntos
             if not (0 <= p[2] < ancho and 0 <= p[3] < alto)]
    tapados = ["%s %s (%d, %d)" % p for p in puntos
               if 0 <= p[2] < ancho and 0 <= p[3] < alto and (p[2], p[3]) in bloqueadas]
    if fuera:
        errores.append("%s de %s %s FUERA del mapa de %d x %d: %s."
                       % (_n_puntos(fuera), origen, "queda" if len(fuera) == 1 else "quedan",
                          ancho, alto, _ejemplos(fuera)))
    if tapados:
        errores.append("%s de %s %s sobre celdas bloqueadas (racks o paredes): %s. "
                       "Los operarios no podrian llegar."
                       % (_n_puntos(tapados), origen, "cae" if len(tapados) == 1 else "caen",
                          _ejemplos(tapados)))
    return errores


def _leer_mapa(ruta: str):
    """(ancho, alto, celdas bloqueadas) con la misma regla que el motor."""
    import xml.etree.ElementTree as ET
    raiz = ET.parse(ruta).getroot()
    ancho, alto = int(raiz.get("width", 0)), int(raiz.get("height", 0))
    return ancho, alto, _celdas_bloqueadas(ruta, ancho, alto)


def validar_tmx(ruta: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """QA-6.6: un mapa se acepta solo si el simulador puede usarlo CON los
    datos maestros en uso. Antes bastaba un <map> (se aceptaba un mapa vacio
    de 10x10 aunque las ubicaciones llegan a x=31, y=39)."""
    import xml.etree.ElementTree as ET
    errores: List[str] = []
    avisos: List[str] = []
    try:
        raiz = ET.parse(ruta).getroot()
    except Exception as e:
        return {"valido": False, "errores": ["No es un archivo TMX valido (XML ilegible: %s)." % e],
                "avisos": [], "resumen": {}}
    if raiz.tag != "map":
        return {"valido": False, "errores": ["No es un mapa de Tiled: falta el elemento <map>."],
                "avisos": [], "resumen": {}}
    try:
        ancho, alto = int(raiz.get("width", 0)), int(raiz.get("height", 0))
    except ValueError:
        ancho = alto = 0
    capas = [c.get("name") for c in raiz.findall("layer")]
    if ancho <= 0 or alto <= 0:
        errores.append("El mapa no tiene tamanio (ancho x alto = %d x %d)." % (ancho, alto))
    if not capas:
        errores.append("El mapa no tiene capas de tiles: el simulador no sabria donde hay "
                       "racks, pasillos ni muelles.")
    resumen = {"ancho": ancho, "alto": alto, "capas": len(capas)}
    if errores:
        return {"valido": False, "errores": errores, "avisos": avisos,
                "resumen": resumen, "capas": capas}

    try:
        bloqueadas = _celdas_bloqueadas(ruta, ancho, alto)
    except Exception as e:
        return {"valido": False, "errores": ["El mapa esta danado o incompleto y el simulador tampoco "
                                        "puede abrirlo (%s). Revisalo en Tiled." % e],
                "avisos": avisos, "resumen": resumen, "capas": capas}
    resumen["celdas_bloqueadas"] = len(bloqueadas)
    if not bloqueadas:
        avisos.append("Ninguna celda esta bloqueada: el mapa no tiene racks ni paredes.")

    # Cruce con los datos maestros que usa el motor (warehouse.db).
    if db_path and os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        try:
            puntos = []
            for sql, etiqueta in (
                    ("SELECT location_id, legacy_x, legacy_y FROM locations", "ubicacion"),
                    ("SELECT staging_id, legacy_x, legacy_y FROM staging_areas", "zona de salida"),
                    ("SELECT dock_id, x, y FROM inbound_docks", "muelle")):
                try:
                    puntos += [(etiqueta, str(i), int(x), int(y))
                               for i, x, y in conn.execute(sql).fetchall()
                               if x is not None and y is not None]
                except sqlite3.Error:
                    continue
        finally:
            conn.close()
        errores += _cruzar_puntos(puntos, ancho, alto, bloqueadas, "los datos maestros en uso")
        if errores:
            errores.append("Usa un mapa que los contenga o aplica un Excel hecho para este mapa.")
        resumen["puntos_verificados"] = len(puntos)
    return {"valido": not errores, "errores": errores, "avisos": avisos,
            "resumen": resumen, "capas": capas}
