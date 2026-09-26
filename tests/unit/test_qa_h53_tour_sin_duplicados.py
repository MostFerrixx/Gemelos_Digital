# -*- coding: utf-8 -*-
"""QA H-53: una WO no puede entrar dos veces al mismo tour.

BK-23 agrega las hermanas de la misma ubicacion junto con la primera WO; el
doble barrido las volvia a agregar porque solo marcaba como usada la primera.
Resultado: la misma linea se recogia, se dejaba y se despachaba dos veces.
"""


class _Op:
    def __init__(self, capacity=1000):
        self.capacity = capacity
        self.current_position = (0, 0)
        self.operator_id = "OP-TEST"

    def get_priority_for_work_area(self, area):
        return 1


def test_hermanas_de_la_ubicacion_no_se_repiten(make_dispatcher, make_wo):
    d = make_dispatcher({"tour_type": "Tour Mixto (Multi-Destino)"})
    assert d.consolidar_por_ubicacion
    primera = make_wo(pick_sequence=5, ubicacion=(3, 4))
    hermana = make_wo(pick_sequence=5, ubicacion=(3, 4))
    otra = make_wo(pick_sequence=7, ubicacion=(3, 8))
    for w in (primera, hermana, otra):
        w.staging_id = 1
    tour = d._construir_tour_por_secuencia(_Op(), primera, [primera, hermana, otra])
    ids = [w.id for w in tour]
    assert len(ids) == len(set(ids)), ids
    assert set(ids) == {primera.id, hermana.id, otra.id}


def test_hermana_con_secuencia_menor_tampoco_se_repite(make_dispatcher, make_wo):
    # barrido 2 (retroceso): la hermana con seq menor tampoco puede reentrar
    d = make_dispatcher({"tour_type": "Tour Simple (Un Destino)"})
    primera = make_wo(pick_sequence=9, ubicacion=(1, 1))
    hermana = make_wo(pick_sequence=2, ubicacion=(1, 1))
    for w in (primera, hermana):
        w.staging_id = 1
    tour = d._construir_tour_por_secuencia(_Op(), primera, [primera, hermana])
    assert [w.id for w in tour] == [primera.id, hermana.id]
