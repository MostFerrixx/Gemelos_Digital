# -*- coding: utf-8 -*-
"""
MEJ-1 / ES-xx: caracterizacion del router de estrategias y helpers.

ES-01 defaults del constructor; ES-02 FIFO (orden de llegada + area + capacidad);
ES-03 router con alias H-5; ES-04 radio blando H-6 (expansion gradual + fallback).
"""


def test_es01a_constructor_passthrough_del_config(make_dispatcher):
    disp = make_dispatcher()
    assert disp.estrategia == "Optimizacion Global"
    assert disp.max_wos_por_tour == 20
    assert disp.radio_cercania == 100
    assert disp.radio_expansion_paso == 50
    assert disp.radio_max_expansiones == 5
    assert disp.cercania_tour_mode == "cost"
    assert disp.priority_dispatch_enabled is False
    assert disp.waves_enabled is False


def test_es01b_defaults_con_config_vacio(fake_env):
    """Los DEFAULTS del motor son contrato (pinneado por esta suite; esquema
    en src/core/config_schema.py): config vacio debe reproducir el
    comportamiento historico documentado."""
    from subsystems.simulation.dispatcher import DispatcherV11
    disp = DispatcherV11(env=fake_env, almacen=None, assignment_calculator=None,
                         route_calculator=None, data_manager=None, configuracion={})
    assert disp.estrategia == "Optimizacion Global"
    assert disp.tour_type == "Tour Mixto (Multi-Destino)"
    assert disp.max_wos_por_tour == 20
    assert disp.radio_cercania == 100
    assert disp.radio_expansion_paso == 50
    assert disp.radio_max_expansiones == 5
    assert disp.cercania_tour_mode == "cost"
    assert disp.priority_dispatch_enabled is False
    assert disp.waves_enabled is False
    assert disp.wave_release_times == {}


def test_es02_fifo_respeta_orden_area_y_capacidad(make_dispatcher, make_wo, make_operator):
    disp = make_dispatcher({"dispatch_strategy": "FIFO Estricto"})
    op = make_operator(areas=("Area_Ground",), capacity=100)
    wo1 = make_wo(work_area="Area_Ground", volumen=40)
    wo_ajena = make_wo(work_area="Area_High", volumen=10)  # area no compatible
    wo2 = make_wo(work_area="Area_Ground", volumen=40)
    wo3 = make_wo(work_area="Area_Ground", volumen=40)  # ya no cabe (120 > 100)
    disp.work_orders_pendientes = [wo1, wo_ajena, wo2, wo3]
    resultado = disp._estrategia_fifo(op)
    assert resultado == [wo1, wo2]  # orden de llegada, sin area ajena, corta por capacidad


def test_es03_router_reconoce_alias_h5(make_dispatcher, make_operator):
    """H-5: alias corto y largo de 'Ejecucion de Plan' van a la misma estrategia."""
    sentinel = {"fifo": ["F"], "og": ["G"], "plan": ["P"], "cerca": ["C"]}
    nombres = {
        "FIFO Estricto": sentinel["fifo"],
        "Optimizacion Global": sentinel["og"],
        "Ejecucion de Plan": sentinel["plan"],
        "Ejecucion de Plan (Filtro por Prioridad)": sentinel["plan"],
        "Cercania": sentinel["cerca"],
        "EstrategiaInventada": sentinel["og"],  # desconocida -> default OG
    }
    op = make_operator()
    for nombre, esperado in nombres.items():
        disp = make_dispatcher({"dispatch_strategy": nombre})
        disp._estrategia_fifo = lambda o: sentinel["fifo"]
        disp._estrategia_optimizacion_global = lambda o: sentinel["og"]
        disp._estrategia_ejecucion_plan = lambda o: sentinel["plan"]
        disp._estrategia_cercania = lambda o: sentinel["cerca"]
        assert disp._seleccionar_work_orders_candidatos(op) is esperado, nombre


def test_es04a_cercania_radio_inicial_suficiente(make_dispatcher, make_wo, make_operator):
    disp = make_dispatcher({"dispatch_strategy": "Cercania", "radio_cercania": 10})
    op = make_operator(areas=("Area_Ground",), current_position=(0, 0))
    cerca = make_wo(work_area="Area_Ground", ubicacion=(3, 4))    # dist 5
    lejos = make_wo(work_area="Area_Ground", ubicacion=(30, 40))  # dist 50
    disp.work_orders_pendientes = [cerca, lejos]
    resultado = disp._estrategia_cercania(op)
    assert resultado == [cerca]
    assert disp.total_expansiones_radio == 0


def test_es04b_cercania_expande_radio_h6(make_dispatcher, make_wo, make_operator):
    # radio 10; WO a dist 50 -> paso 25: intento 1 radio 35 (no), intento 2 radio 60 (si)
    disp = make_dispatcher({"dispatch_strategy": "Cercania", "radio_cercania": 10,
                            "radio_expansion_paso": 25, "radio_max_expansiones": 5})
    op = make_operator(areas=("Area_Ground",), current_position=(0, 0))
    lejos = make_wo(work_area="Area_Ground", ubicacion=(30, 40))  # dist 50
    disp.work_orders_pendientes = [lejos]
    resultado = disp._estrategia_cercania(op)
    assert resultado == [lejos]
    assert disp.total_expansiones_radio == 1


def test_es04c_cercania_fallback_final_todas_las_compatibles(make_dispatcher, make_wo, make_operator):
    # WO fuera incluso del radio maximo expandido -> fallback: compatibles del almacen
    disp = make_dispatcher({"dispatch_strategy": "Cercania", "radio_cercania": 10,
                            "radio_expansion_paso": 10, "radio_max_expansiones": 2})
    op = make_operator(areas=("Area_Ground",), current_position=(0, 0))
    muy_lejos = make_wo(work_area="Area_Ground", ubicacion=(300, 400))  # dist 500
    ajena = make_wo(work_area="Area_High", ubicacion=(1, 1))
    disp.work_orders_pendientes = [muy_lejos, ajena]
    resultado = disp._estrategia_cercania(op)
    assert resultado == [muy_lejos]  # la ajena nunca entra
    assert disp.total_expansiones_radio == 1


def test_es04d_cercania_sin_posicion_cae_a_fifo(make_dispatcher, make_wo, make_operator):
    disp = make_dispatcher({"dispatch_strategy": "Cercania"})
    op = make_operator(areas=("Area_Ground",), current_position=None, capacity=1000)
    wo = make_wo(work_area="Area_Ground", volumen=10)
    disp.work_orders_pendientes = [wo]
    assert disp._estrategia_cercania(op) == [wo]
