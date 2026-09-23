# -*- coding: utf-8 -*-
"""
BK-29: donde empieza el turno cada operario.

Cadena (decision del Director 2026-09-23): zonas de inicio del cliente >
estacionamiento de su equipo > celdas de espera. Ninguna celda de inicio puede
ser carril, salida, acceso ni boca de pasillo, y dos operarios nunca comparten
celda.
"""
import os

from subsystems.simulation.idle_zones import GestorZonasEspera
from subsystems.simulation.inicio_turno import GestorInicioTurno
from subsystems.simulation.parking import Estacionamiento

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Mini mapa 12x12, todo transitable: picks arriba, carril de descarga 2x4 abajo.
ANCHO = ALTO = 12
PICKS = [(5, 1), (6, 1)]
CARRIL = [(x, y) for x in (3, 4) for y in range(8, 12)]


def _transitable(x, y):
    return 0 <= x < ANCHO and 0 <= y < ALTO


def _ze(config=None, n=4):
    return GestorZonasEspera(config or {}, _transitable, ANCHO, ALTO,
                             picks=PICKS, descargas=CARRIL, muelles=[], n_agentes=n)


class _Parking:
    def __init__(self, puntos):
        self.puntos = puntos


def test_sin_configuracion_nacen_en_las_celdas_de_espera():
    ze = _ze()
    g = GestorInicioTurno({}, ze)
    celdas = [g.celda_para('A%d' % i, None, (3, 8)) for i in range(4)]
    assert len(set(celdas)) == 4                               # una por operario
    assert all(c in ze.celdas for c in celdas)
    assert set(g.origen.values()) == {'espera'}
    assert all(ze.motivo_invalida(c) is None for c in celdas)


def test_la_zona_del_cliente_manda_y_descarta_celdas_invalidas():
    ze = _ze()
    cfg = {'inicio_turno': {'zonas': {'INI': {'x': 8, 'y': 5, 'ancho': 2, 'alto': 1}},
                            'usar_estacionamientos': True}}
    g = GestorInicioTurno(cfg, ze)
    assert g.celda_para('A', None, (3, 8)) == (8, 5)
    assert g.celda_para('B', None, (3, 8)) == (9, 5)
    assert g.origen == {'A': 'inicio_turno', 'B': 'inicio_turno'}
    # la zona se lleno: el tercero cae al respaldo, no se encima
    c = g.celda_para('C', None, (3, 8))
    assert c not in ((8, 5), (9, 5)) and g.origen['C'] == 'espera'

    malo = GestorInicioTurno({'inicio_turno': {'zonas': {'X': {'x': 3, 'y': 8}}}}, _ze())
    assert malo.celdas_zonas == []                             # es carril
    assert any('se descartan' in a for a in malo.avisos)


def test_el_montacargas_arranca_junto_a_su_estacionamiento():
    ze = _ze()
    parking = _Parking({'EST-1': Estacionamiento('EST-1', (10, 10), 4, ['grua'])})
    g = GestorInicioTurno({}, ze, parking)
    c = g.celda_para('M1', 'grua', (3, 8))
    assert g.origen['M1'] == 'estacionamiento'
    assert abs(c[0] - 10) + abs(c[1] - 10) <= 6
    # un equipo que ese estacionamiento no admite va al respaldo
    g.celda_para('T1', 'a_pie', (3, 8))
    assert g.origen['T1'] == 'espera'
    # apagado por config: tambien al respaldo
    g2 = GestorInicioTurno({'inicio_turno': {'usar_estacionamientos': False}}, _ze(), parking)
    g2.celda_para('M1', 'grua', (3, 8))
    assert g2.origen['M1'] == 'espera'


def test_nunca_dos_en_la_misma_celda_aunque_sean_muchos():
    ze = _ze(n=4)                                              # 6 celdas de espera
    g = GestorInicioTurno({}, ze)
    celdas = [g.celda_para('A%d' % i, None, (3, 8)) for i in range(15)]
    validas = [c for c in celdas if c is not None]
    assert len(validas) == len(set(validas))
    assert all(ze.motivo_invalida(c) is None for c in validas)
    assert 'cercana' in g.origen.values()                      # se agoto la espera


def test_siempre_la_misma_celda_para_el_mismo_operario():
    g = GestorInicioTurno({}, _ze())
    assert g.celda_para('A', None, (3, 8)) == g.celda_para('A', None, (3, 8))


def test_mapa_real_v3_nadie_nace_en_la_estacion():
    """Canonico WH1 v3 con 16 operarios: nadie en un carril, salida ni entrada."""
    import contextlib, copy, io, json, tempfile
    from engines.event_generator import EventGenerator
    ruta_cfg = os.path.join(PROJECT_ROOT, 'config.json')
    cfg = json.load(open(ruta_cfg, encoding='utf-8'))
    if 'WH1 v3' not in cfg.get('layout_file', ''):
        return
    g = [a for a in cfg['agent_types'] if a['type'] == 'GroundOperator'][0]
    f = [a for a in cfg['agent_types'] if a['type'] == 'Forklift'][0]
    cfg['agent_types'] = [copy.deepcopy(g) for _ in range(8)] + [copy.deepcopy(f) for _ in range(8)]
    tmp = os.path.join(tempfile.mkdtemp(), 'c.json')
    json.dump(cfg, open(tmp, 'w'))
    cwd = os.getcwd()
    try:
        os.chdir(PROJECT_ROOT)
        with contextlib.redirect_stdout(io.StringIO()):
            gen = EventGenerator(headless_mode=True, config_path=tmp)
            gen.crear_simulacion()
    finally:
        os.chdir(cwd)
    a = gen.almacen
    est = a.estaciones
    prohibidas = set(est.todas_las_salidas().keys())
    for e in est.estaciones.values():
        prohibidas |= set(e.celdas) | set(e.entradas.values())
    celdas = [a.inicio_turno.celda_para('OP%d' % i, None, (3, 30)) for i in range(16)]
    assert None not in celdas and len(set(celdas)) == 16
    assert not (set(celdas) & prohibidas)
