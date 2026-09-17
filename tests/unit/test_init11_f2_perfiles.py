# -*- coding: utf-8 -*-
"""
INIT-11 F2: perfiles con prioridad, regla de cambio y estacionamientos.

Una persona puede tener varios perfiles (que tipo de tarea toma y con que
equipo). Al quedarse sin trabajo en el suyo, va a un estacionamiento, deja el
equipo y toma otro. La regla `cambio_de_perfil` decide cuando conviene hacerlo
(cambiar cuesta tiempo real).
"""
import copy
import os
import shutil

from core.config_schema import validate_config_schema
from core.fleet import (resolver_cambio_de_perfil, resolver_equipos,
                        resolver_perfiles, resolver_personas)
from subsystems.simulation.dispatcher import DispatcherV11
from subsystems.simulation.parking import GestorEstacionamientos

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

EQUIPOS = {
    "transpaleta": {"tipo_base": "GroundOperator", "cantidad": 2},
    "grua": {"tipo_base": "Forklift", "cantidad": 2, "tiempo_cambio_s": 45},
}
PERFILES = {
    "picker": {"tareas": ["pick"], "equipo": "transpaleta"},
    "gruero": {"tareas": ["pick"], "equipo": "grua"},
    "reponedor": {"tareas": ["putaway"], "equipo": "grua"},
}
BASE = {
    "work_area_equipment": {"Area_Ground": "GroundOperator", "Area_High": "Forklift"},
    "equipos": EQUIPOS,
    "perfiles": PERFILES,
    "estacionamientos": {"EST-1": {"x": 12, "y": 28, "capacidad": 3}},
}


def _config(**extra):
    c = copy.deepcopy(BASE)
    c.update(extra)
    return c


# ------------------------------------------------------------------ perfiles

def test_pf01_perfil_valido_y_tareas_desconocidas():
    perfiles, avisos = resolver_perfiles(_config(perfiles=dict(
        PERFILES, empacador={"tareas": ["actividad", "pick"]})))
    assert perfiles["picker"] == {"nombre": "picker", "tareas": ["pick"],
                                  "equipo": "transpaleta"}
    # 'actividad' llega en F4: se ignora, pero el perfil sobrevive por 'pick'
    assert perfiles["empacador"]["tareas"] == ["pick"]
    assert any("actividad" in a for a in avisos)


def test_pf02_perfil_sin_tareas_validas_o_con_equipo_inexistente_se_descarta():
    perfiles, avisos = resolver_perfiles(_config(perfiles={
        "fantasma": {"tareas": ["traslado"]},
        "sin_equipo": {"tareas": ["pick"], "equipo": "dron"},
    }))
    assert perfiles == {}
    assert len(avisos) >= 2


def test_pf03_la_persona_lleva_sus_perfiles_en_orden_de_prioridad():
    flota, avisos = resolver_personas(_config(personas=[
        {"grupo": "Poli", "equipo": "grua", "perfiles": ["gruero", "picker"],
         "habilitaciones": ["grua", "transpaleta"]}]))
    assert avisos == []
    assert [p["nombre"] for p in flota[0]["persona"]["perfiles"]] == ["gruero", "picker"]


def test_pf04_perfil_sin_habilitacion_no_se_asigna():
    flota, avisos = resolver_personas(_config(personas=[
        {"grupo": "Poli", "equipo": "grua", "perfiles": ["gruero", "picker"],
         "habilitaciones": ["grua"]}]))
    assert [p["nombre"] for p in flota[0]["persona"]["perfiles"]] == ["gruero"]
    assert any("no esta habilitado" in a for a in avisos)


def test_pf05_sin_equipo_declarado_lo_toma_del_perfil_mas_prioritario():
    flota, _ = resolver_personas(_config(personas=[
        {"grupo": "Poli", "perfiles": ["gruero", "picker"]}]))
    assert flota[0]["equipo"]["id"] == "grua"
    # y queda habilitada para los equipos de todos sus perfiles
    assert flota[0]["persona"]["habilitaciones"] == ["grua", "transpaleta"]


def test_pf06_perfil_inexistente_avisa():
    flota, avisos = resolver_personas(_config(personas=[
        {"grupo": "Poli", "equipo": "grua", "perfiles": ["gruero", "supervisor"]}]))
    assert [p["nombre"] for p in flota[0]["persona"]["perfiles"]] == ["gruero"]
    assert any("'supervisor'" in a for a in avisos)


def test_pf07_regla_de_cambio_por_defecto_y_modo_invalido():
    assert resolver_cambio_de_perfil({}) == {"modo": "umbral", "umbral": 3}
    assert resolver_cambio_de_perfil(
        {"cambio_de_perfil": {"modo": "agotar"}}) == {"modo": "agotar", "umbral": 3}
    assert resolver_cambio_de_perfil(
        {"cambio_de_perfil": {"modo": "cuando_quiera"}})["modo"] == "umbral"


# ----------------------------------------------------------- estacionamientos

def _gestor(config=None, en_uso=None):
    config = config or BASE
    equipos, _ = resolver_equipos(config)
    return GestorEstacionamientos(config, equipos, en_uso or {}, None)


def test_pf08_las_unidades_libres_arrancan_estacionadas():
    gestor = _gestor(en_uso={"grua": 1})
    guardados = sorted(gestor.puntos["EST-1"].guardados)
    assert guardados == ["grua", "transpaleta", "transpaleta"]
    assert gestor.hay_disponible("grua") and gestor.hay_disponible("transpaleta")


def test_pf09_sin_lugar_las_unidades_sobrantes_avisan():
    gestor = _gestor(_config(estacionamientos={"EST-1": {"x": 1, "y": 1, "capacidad": 1}}))
    assert len(gestor.puntos["EST-1"].guardados) == 1
    assert any("fuera de juego" in a for a in gestor.avisos)


def test_pf10_coordenada_fuera_del_mapa_descarta_el_punto():
    class MapaFalso:
        grid_width = grid_height = 30

        @staticmethod
        def is_walkable(x, y):
            return y < 29

    equipos, _ = resolver_equipos(BASE)
    gestor = GestorEstacionamientos(
        _config(estacionamientos={"FUERA": {"x": 99, "y": 2},
                                  "PARED": {"x": 3, "y": 29},
                                  "OK": {"x": 3, "y": 2, "capacidad": 4}}),
        equipos, {}, MapaFalso())
    assert list(gestor.puntos) == ["OK"]
    assert len([a for a in gestor.avisos if "no es una celda transitable" in a]) == 2


def test_pf11_el_punto_de_cambio_necesita_unidad_libre_y_lugar():
    gestor = _gestor(en_uso={"grua": 2, "transpaleta": 2})  # nada libre
    assert gestor.punto_para_cambio("transpaleta", "grua") is None
    gestor = _gestor(en_uso={"grua": 1, "transpaleta": 2})  # 1 grua libre
    punto = gestor.punto_para_cambio("transpaleta", "grua")
    assert punto is not None and punto.id == "EST-1"
    gestor.ejecutar_cambio(punto, "transpaleta", "grua")
    assert sorted(punto.guardados) == ["transpaleta"]
    assert gestor.tiempo_de_cambio("transpaleta", "grua") == 75.0  # 30 + 45


def test_pf12_un_punto_que_no_admite_el_equipo_no_sirve_para_dejarlo():
    gestor = _gestor(_config(estacionamientos={
        "SOLO_GRUAS": {"x": 1, "y": 1, "capacidad": 3, "admite": ["grua"]}}),
        en_uso={"grua": 1, "transpaleta": 2})
    assert gestor.punto_para_cambio("transpaleta", "grua") is None
    assert gestor.punto_para_cambio(None, "grua") is not None


# ------------------------------------------------------- reparto por perfiles

class _WO:
    def __init__(self, work_area, listo=None):
        self.work_area = work_area
        self.pallet_ready = listo is not None
        self.tiempo_pallet_listo = listo
        self.wave_id = None


class _Operario:
    """Lo minimo que mira el dispatcher para repartir por perfiles."""

    def __init__(self, perfiles, equipo):
        self.perfiles = perfiles
        self.perfil_actual = None
        self.equipo = self.equipo_fisico = equipo
        self.equipos = {e["id"]: e for e in (equipo,)}

    def equipo_de_perfil(self, perfil):
        equipos, _ = resolver_equipos(BASE)
        return equipos.get(perfil["equipo"], self.equipo_fisico)

    def prioridades_de_equipo(self, equipo_id):
        equipos, _ = resolver_equipos(BASE)
        tipo = equipos[equipo_id]["tipo_base"]
        return ({"Area_Ground": 1} if tipo == "GroundOperator"
                else {"Area_High": 1})


def _dispatcher(modo, umbral=3):
    d = object.__new__(DispatcherV11)
    d.cambio_de_perfil = {"modo": modo, "umbral": umbral}
    d.work_orders_pendientes = []
    d.putaway_pendientes = []
    d._wo_elegible_por_ola = lambda wo: True
    return d


def _operario():
    perfiles, _ = resolver_perfiles(BASE)
    equipos, _ = resolver_equipos(BASE)
    return _Operario([perfiles["gruero"], perfiles["picker"]], equipos["grua"])


def test_pf13_modo_inmediato_siempre_prueba_primero_el_mas_prioritario():
    d = _dispatcher("inmediato")
    op = _operario()
    op.perfil_actual = op.perfiles[1]          # esta de picker
    d.work_orders_pendientes = [_WO("Area_High")]
    assert [p["nombre"] for p in d._orden_de_perfiles(op)] == ["gruero", "picker"]


def test_pf14_modo_agotar_se_queda_mientras_tenga_trabajo():
    d = _dispatcher("agotar")
    op = _operario()
    op.perfil_actual = op.perfiles[1]          # picker
    d.work_orders_pendientes = [_WO("Area_Ground"), _WO("Area_High")]
    assert [p["nombre"] for p in d._orden_de_perfiles(op)] == ["picker", "gruero"]
    d.work_orders_pendientes = [_WO("Area_High")]   # se le acabo lo suyo
    assert [p["nombre"] for p in d._orden_de_perfiles(op)] == ["gruero", "picker"]


def test_pf15_modo_umbral_solo_sube_si_se_acumulo_trabajo():
    d = _dispatcher("umbral", umbral=3)
    op = _operario()
    op.perfil_actual = op.perfiles[1]          # picker
    d.work_orders_pendientes = [_WO("Area_High"), _WO("Area_High")]
    assert [p["nombre"] for p in d._orden_de_perfiles(op)] == ["picker", "gruero"]
    d.work_orders_pendientes.append(_WO("Area_High"))   # llega a 3
    assert [p["nombre"] for p in d._orden_de_perfiles(op)] == ["gruero", "picker"]


def test_pf16_las_pendientes_cuentan_picks_y_putaway_del_perfil():
    d = _dispatcher("umbral")
    op = _operario()
    perfiles, _ = resolver_perfiles(BASE)
    d.work_orders_pendientes = [_WO("Area_High"), _WO("Area_Ground")]
    d.putaway_pendientes = [_WO("Area_High", listo=1.0), _WO("Area_High")]
    assert d._pendientes_de_perfil(op, perfiles["gruero"]) == 1     # solo el pick
    assert d._pendientes_de_perfil(op, perfiles["picker"]) == 1
    # el reponedor toma putaway: solo cuenta el pallet YA aterrizado
    assert d._pendientes_de_perfil(op, perfiles["reponedor"]) == 1


# --------------------------------------------------------------- esquema y web

def test_pf17_esquema_registra_perfiles_cambio_y_estacionamientos():
    errores, avisos = validate_config_schema(_config(
        perfiles={"picker": {"tareas": ["pick"], "color": "azul"}},
        cambio_de_perfil={"modo": "agotar", "cada_cuanto": 5},
        estacionamientos={"EST-1": {"x": 1, "y": 1, "techado": True}}))
    assert errores == []
    assert "clave DESCONOCIDA: 'perfiles.picker.color'" in avisos
    assert "clave DESCONOCIDA: 'cambio_de_perfil.cada_cuanto'" in avisos
    assert "clave DESCONOCIDA: 'estacionamientos.EST-1.techado'" in avisos
    assert not any("'perfiles'" in a or "'estacionamientos'" in a for a in avisos)


def _config_web(**cambios):
    import json
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["equipos"] = {"transpaleta": {"tipo_base": "GroundOperator"},
                      "grua": {"tipo_base": "Forklift", "cantidad": 2}}
    cfg["perfiles"] = {"picker": {"tareas": ["pick"], "equipo": "transpaleta"},
                       "gruero": {"tareas": ["pick"], "equipo": "grua"}}
    cfg["personas"] = [
        {"grupo": "P", "equipo": "transpaleta", "perfiles": ["picker", "gruero"],
         "habilitaciones": ["transpaleta", "grua"],
         "work_area_priorities": {"Area_Ground": 1}},
        {"grupo": "G", "equipo": "grua", "perfiles": ["gruero"],
         "work_area_priorities": {"Area_High": 1, "Area_Special": 2}}]
    cfg["estacionamientos"] = {"EST-1": {"x": 12, "y": 28, "capacidad": 4}}
    cfg.update(cambios)
    return cfg


def _manager(tmp_path):
    from web_prototype.config_manager import WebConfigurationManager
    (tmp_path / "layouts").mkdir()
    for nombre in ("Warehouse_Logic.xlsx", "WH1.tmx"):
        origen = os.path.join(PROJECT_ROOT, "layouts", nombre)
        if os.path.exists(origen):
            shutil.copy2(origen, tmp_path / "layouts" / nombre)
    return WebConfigurationManager(str(tmp_path))


def test_pf18_web_acepta_perfiles_con_estacionamiento(tmp_path):
    ok, errores = _manager(tmp_path).validate_config(_config_web())
    assert ok, errores


def test_pf19_web_bloquea_perfiles_sin_donde_cambiar_de_equipo(tmp_path):
    cfg = _config_web()
    del cfg["estacionamientos"]
    ok, errores = _manager(tmp_path).validate_config(cfg)
    assert not ok
    assert any("no hay ningun estacionamiento" in e for e in errores)


def test_pf20_web_valida_las_coordenadas_del_estacionamiento_contra_el_mapa(tmp_path):
    cfg = _config_web(estacionamientos={"EST-1": {"x": 3, "y": 26, "capacidad": 2}})
    ok, errores = _manager(tmp_path).validate_config(cfg)
    assert not ok  # (3, 26) es rack, no pasillo
    assert any("transitable" in e for e in errores)
