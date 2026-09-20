# -*- coding: utf-8 -*-
"""
BK-23 (capa 1): una ubicacion, un operario a la vez + consolidar por ubicacion.

El despacho mandaba varias tareas del MISMO hueco a operarios distintos. Una
vez ahi se tapaban las salidas entre ellos: en la corrida de 16 operarios,
cinco terminaron en (10,18) y uno quedo 12.111 s sin poder moverse.
"""
import types


class _WO:
    """WorkOrder de mentira: lo justo para la logica del despacho.

    Cualquier atributo que el despachador pida y no este aca vale 1 (los usa
    solo para armar el evento de asignacion, que en el test no se mira).
    """

    def __init__(self, id_, celda, volumen=10, area='Area_Ground', seq=1):
        self.id = id_
        self.ubicacion = celda
        self.work_area = area
        self.pick_sequence = seq
        self._v = volumen
        self.status = 'released'
        self.assigned_agent_id = None

    def __getattr__(self, nombre):
        if nombre.startswith('_'):
            raise AttributeError(nombre)
        return 1

    def calcular_volumen_restante(self):
        return self._v


def _despachador(configuracion=None):
    from subsystems.simulation.dispatcher import DispatcherV11
    d = DispatcherV11.__new__(DispatcherV11)          # sin SimPy: solo la logica
    d.ubicaciones_comprometidas = {}
    d.work_orders_asignados = {}
    d.work_orders_pendientes = []
    _desp = (configuracion or {}).get('despacho', {})
    d.una_ubicacion_un_operario = bool(_desp.get('una_ubicacion_un_operario', True))
    d.consolidar_por_ubicacion = bool(_desp.get('consolidar_por_ubicacion', True))
    d.max_wos_por_tour = 20
    d.repartir_por_staging = False        # BK-25: se prueba aparte
    d.stagings_en_curso = {}
    d.zonas_activas = False
    d.env = types.SimpleNamespace(now=0.0)
    d.almacen = types.SimpleNamespace(registrar_evento=lambda *a, **k: None)
    d.operadores_activos = {}
    d.operadores_disponibles = []
    return d


def _operario(nombre='GroundOp-01'):
    return types.SimpleNamespace(id=nombre, type='GroundOperator', capacity=100)


def test_bk23_el_segundo_operario_no_recibe_el_hueco_tomado():
    d = _despachador()
    a, b = _operario('GroundOp-01'), _operario('GroundOp-02')
    wos = [_WO('W1', (10, 18)), _WO('W2', (10, 18)), _WO('W3', (5, 7))]
    d._marcar_asignados(a, [wos[0]])
    libres = d._candidatos_sin_ubicacion_ajena(b, wos)
    assert [w.id for w in libres] == ['W3']                 # (10,18) es de A
    assert [w.id for w in d._candidatos_sin_ubicacion_ajena(a, wos)] == ['W1', 'W2', 'W3']


def test_bk23_la_ubicacion_se_libera_al_terminar():
    d = _despachador()
    a, b = _operario('GroundOp-01'), _operario('GroundOp-02')
    w1, w2 = _WO('W1', (10, 18)), _WO('W2', (10, 18))
    d._marcar_asignados(a, [w1, w2])
    d.finalizar_tour(a)                                 # la limpieza del cierre de tour
    assert d.ubicaciones_comprometidas == {}
    assert len(d._candidatos_sin_ubicacion_ajena(b, [w1, w2])) == 2


def test_bk23_consolidar_se_lleva_las_lineas_del_mismo_hueco():
    d = _despachador()
    w1, w2, w3 = _WO('W1', (10, 18)), _WO('W2', (10, 18)), _WO('W3', (5, 7))
    hermanas = d._wos_de_la_misma_ubicacion(w1, [w1, w2, w3])
    assert [w.id for w in hermanas] == ['W2']


def test_bk23_apagado_se_comporta_como_antes():
    d = _despachador({'despacho': {'una_ubicacion_un_operario': False,
                                   'consolidar_por_ubicacion': False}})
    a, b = _operario('GroundOp-01'), _operario('GroundOp-02')
    wos = [_WO('W1', (10, 18)), _WO('W2', (10, 18))]
    d._marcar_asignados(a, [wos[0]])
    assert len(d._candidatos_sin_ubicacion_ajena(b, wos)) == 2    # sin filtro
    assert d._wos_de_la_misma_ubicacion(wos[0], wos) == []        # sin consolidar
