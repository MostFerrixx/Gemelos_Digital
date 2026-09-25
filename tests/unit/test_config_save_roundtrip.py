# -*- coding: utf-8 -*-
"""
Guardar el config canonico SIN cambios debe ser un no-op exacto.

Revision de UI del 2026-09-16: guardar desde el configurador alteraba el
archivo aunque nadie tocara nada:
  - lo reindentaba entero (indent=4 contra el indent=2 versionado);
  - le quitaba el salto de linea final;
  - le volvia a agregar `tiempo_picking_por_linea: null` (clave eliminada);
  - le agregaba `destino_staging_map: {}`.
Las dos ultimas cambiaban la metadata del replay y rompian el gate.

Las dos primeras las cubre este test (backend). Las dos ultimas son del
frontend (serializeConfig) y se verificaron en el navegador.

Se trabaja sobre una COPIA en un directorio temporal: nunca se escribe el
config.json real del proyecto.
"""
import json
import os
import shutil

from web_prototype.config_manager import WebConfigurationManager

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _proyecto_temporal(tmp_path):
    """Copia lo minimo para que el validador funcione: config + Excel + mapa."""
    shutil.copy2(os.path.join(PROJECT_ROOT, "config.json"), tmp_path / "config.json")
    (tmp_path / "layouts").mkdir()
    # Los archivos que nombra la config (antes copiaba WH1.tmx y el Excel
    # viejo aunque el canonico usa otros) + la imagen del mapa.
    cfg = json.load(open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8"))
    nombres = {os.path.basename(cfg["layout_file"]), os.path.basename(cfg["sequence_file"]),
               "custom_warehouse_tileset.png", "custom_warehouse_tileset.tsx"}
    for nombre in nombres:
        origen = os.path.join(PROJECT_ROOT, "layouts", nombre)
        if os.path.exists(origen):
            shutil.copy2(origen, tmp_path / "layouts" / nombre)
    return WebConfigurationManager(str(tmp_path))


def _normalizar_eol(datos: bytes) -> bytes:
    """En Windows, con core.autocrlf=true, git entrega el archivo con CRLF y el
    guardado escribe LF. Git (y el regression gate) normalizan a LF, asi que esa
    diferencia no llega al repositorio: se compara con los finales normalizados."""
    return datos.replace(b"\r\n", b"\n")


def test_rt01_guardar_sin_cambios_no_altera_el_archivo(tmp_path):
    manager = _proyecto_temporal(tmp_path)
    ruta = tmp_path / "config.json"
    antes = ruta.read_bytes()

    config = json.loads(antes.decode("utf-8"))
    ok, errores = manager.save_config(config)
    assert ok, errores

    despues = ruta.read_bytes()
    assert _normalizar_eol(despues) == _normalizar_eol(antes), \
        "guardar el canonico sin cambios modifico el archivo"


def test_rt02_usa_la_indentacion_del_archivo_versionado(tmp_path):
    manager = _proyecto_temporal(tmp_path)
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    manager.save_config(config)

    lineas = (tmp_path / "config.json").read_text(encoding="utf-8").splitlines()
    segunda = next(l for l in lineas[1:] if l.strip())
    sangria = len(segunda) - len(segunda.lstrip(" "))
    assert sangria == 2, "se esperaba indent=2, se encontro %d" % sangria


def test_rt03_termina_con_salto_de_linea(tmp_path):
    manager = _proyecto_temporal(tmp_path)
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    manager.save_config(config)
    assert (tmp_path / "config.json").read_bytes().endswith(b"\n")


def test_rt04_canonico_no_tiene_claves_eliminadas():
    """Guardas contra la reintroduccion de claves que el motor ya no lee."""
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        config = json.load(f)
    assert "tiempo_picking_por_linea" not in config.get("tiempos", {})
