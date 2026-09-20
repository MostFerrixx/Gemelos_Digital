# -*- coding: utf-8 -*-
"""
BK-25 capa 3: pasillos del mapa y zonas de picking (una zona por pasillo).

Como en un WMS estandar: la zona sale del mapa (SAP EWM la llama "activity
area"; Dynamics, "zone" de la ubicacion) y la asignacion de operarios a zonas
es configuracion de operacion, no dato maestro.
"""
import types

from subsystems.simulation.aisles import MapaDePasillos

# Mini mapa 12x8: racks en x=0,3,4,7,8,11; pasillos en x=1-2, 5-6, 9-10
PICKS = [(x, y) for x in (1, 2, 5, 6, 9, 10) for y in range(2, 6)]


def _transitable(x, y):
    return 0 <= x < 12 and 0 <= y < 8 and x not in (0, 3, 4, 7, 8, 11)


def _mapa():
    return MapaDePasillos(PICKS, _transitable, 12, 8)


def test_pasillos_numerados_de_izquierda_a_derecha():
    m = _mapa()
    assert m.numeros == [1, 2, 3]
    assert m.pasillo(1).columnas == [1, 2]
    assert m.pasillo(3).columnas == [9, 10]
    assert m.numero_de((5, 3)) == 2
    assert m.numero_de((0, 0)) is None          # no es celda de picking


def test_ancho_y_capacidad_sugerida():
    m = _mapa()
    assert m.pasillo(1).ancho == 2               # dos celdas de ancho
    assert m.capacidad_sugerida(1) == 2          # un operario por celda de ancho


def test_bocas_del_pasillo():
    m = _mapa()
    bocas = m.pasillo(1).bocas
    assert (1, 2) in bocas and (1, 5) in bocas   # arriba y abajo
    assert (1, 3) not in bocas                   # el medio no es boca


def _despachador(zonas):
    from subsystems.simulation.dispatcher import DispatcherV11
    d = DispatcherV11.__new__(DispatcherV11)
    d.zonas_activas = bool(zonas.get('enabled', False))
    d.zonas_por_agente = {str(k): [int(z) for z in v] for k, v in (zonas.get('asignacion') or {}).items()}
    d.robo_de_trabajo = bool(zonas.get('robo_de_trabajo', True))
    d.tareas_robadas = 0
    d.almacen = types.SimpleNamespace(pasillos=_mapa())
    return d


class _WO:
    def __init__(self, id_, celda):
        self.id = id_
        self.ubicacion = celda


def test_cada_operario_trabaja_en_sus_zonas():
    d = _despachador({'enabled': True, 'asignacion': {'GroundOp-01': [1], 'GroundOp-02': [2, 3]}})
    a = types.SimpleNamespace(id='GroundOp-01', type='GroundOperator')
    b = types.SimpleNamespace(id='GroundOp-02', type='GroundOperator')
    wos = [_WO('W1', (1, 3)), _WO('W2', (5, 3)), _WO('W3', (9, 4))]
    assert [w.id for w in d._candidatos_de_mi_zona(a, wos)] == ['W1']
    assert [w.id for w in d._candidatos_de_mi_zona(b, wos)] == ['W2', 'W3']


def test_si_su_zona_se_vacia_ayuda_en_otra():
    d = _despachador({'enabled': True, 'asignacion': {'GroundOp-01': [1]}, 'robo_de_trabajo': True})
    a = types.SimpleNamespace(id='GroundOp-01', type='GroundOperator')
    wos = [_WO('W2', (5, 3))]                    # no queda nada en su zona
    assert [w.id for w in d._candidatos_de_mi_zona(a, wos)] == ['W2']
    assert d.tareas_robadas == 1


def test_sin_robo_de_trabajo_espera():
    d = _despachador({'enabled': True, 'asignacion': {'GroundOp-01': [1]}, 'robo_de_trabajo': False})
    a = types.SimpleNamespace(id='GroundOp-01', type='GroundOperator')
    assert d._candidatos_de_mi_zona(a, [_WO('W2', (5, 3))]) == []


def test_apagado_no_filtra_nada():
    d = _despachador({'enabled': False, 'asignacion': {'GroundOp-01': [1]}})
    a = types.SimpleNamespace(id='GroundOp-01', type='GroundOperator')
    wos = [_WO('W1', (1, 3)), _WO('W2', (5, 3))]
    assert d._candidatos_de_mi_zona(a, wos) == wos


def _despachador_staging(reparto=True, en_curso=None):
    from subsystems.simulation.dispatcher import DispatcherV11
    d = DispatcherV11.__new__(DispatcherV11)
    d.repartir_por_staging = reparto
    d.stagings_en_curso = dict(en_curso or {})
    return d


class _WOStaging:
    def __init__(self, id_, staging_id):
        self.id = id_
        self.staging_id = staging_id


def test_los_pickers_van_a_muelles_distintos():
    """BK-25 (idea del Director): si varios trabajan pedidos del mismo carril,
    se encolan todos ahi a descargar."""
    d = _despachador_staging(en_curso={1: 2, 2: 0, 3: 1})
    wos = [_WOStaging('A', 1), _WOStaging('B', 2), _WOStaging('C', 3)]
    assert [w.id for w in d._candidatos_repartiendo_staging(wos)] == ['B']   # el muelle mas libre


def test_si_todos_los_muelles_estan_igual_no_filtra():
    d = _despachador_staging(en_curso={1: 1, 2: 1})
    wos = [_WOStaging('A', 1), _WOStaging('B', 2)]
    assert len(d._candidatos_repartiendo_staging(wos)) == 2


def test_reparto_apagado_no_filtra():
    d = _despachador_staging(reparto=False, en_curso={1: 5, 2: 0})
    wos = [_WOStaging('A', 1), _WOStaging('B', 2)]
    assert len(d._candidatos_repartiendo_staging(wos)) == 2
