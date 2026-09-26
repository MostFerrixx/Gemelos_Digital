# -*- coding: utf-8 -*-
"""QA H-57: al arrancar, el servidor borraba uploads/ entero, incluido el
archivo de pedidos (o mapa / Excel subido) que usa config.json."""
import json

from web_prototype.server import limpiar_uploads


def test_arranque_conserva_lo_que_usa_config_json(tmp_path):
    up = tmp_path / "uploads" / "sub"
    up.mkdir(parents=True)
    (up / "pedidos.csv").write_text("order_id,sku_id,quantity\n")
    (tmp_path / "uploads" / "viejo.xlsx").write_text("x")
    json.dump({"order_file_path": "uploads\sub\pedidos.csv"},
              open(tmp_path / "config.json", "w", encoding="utf-8"))
    borrados = limpiar_uploads(str(tmp_path))
    assert borrados == ["uploads/viejo.xlsx"]
    assert (up / "pedidos.csv").exists()


def test_sin_config_json_limpia_todo_y_deja_la_carpeta(tmp_path):
    (tmp_path / "uploads").mkdir()
    (tmp_path / "uploads" / "a.csv").write_text("x")
    assert limpiar_uploads(str(tmp_path)) == ["uploads/a.csv"]
    assert (tmp_path / "uploads").is_dir()
