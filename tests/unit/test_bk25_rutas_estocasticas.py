# -*- coding: utf-8 -*-
"""
BK-25: rutas en modo aleatorio (idea del Director).

En modo aleatorio no hay tiendas reales, pero el cliente si sabe cuantas rutas
piquea. Cada ruta queda atada a un muelle y el reparto por muelle decide
cuantas rutas le tocan a cada uno; los pedidos de una ruta salen todos por el
mismo muelle, como con `destino_staging_map` en modo determinista.
"""
import types

from subsystems.simulation.warehouse import AlmacenMejorado


def _almacen(rutas, distribucion):
    a = AlmacenMejorado.__new__(AlmacenMejorado)     # sin SimPy: solo el reparto
    a.configuracion = {'rutas_estocasticas': rutas}
    a.outbound_staging_distribution = distribucion
    a._preparar_rutas_estocasticas()
    return a


def test_las_rutas_se_reparten_segun_el_porcentaje_de_cada_muelle():
    a = _almacen({'enabled': True, 'cantidad': 10},
                 {'1': 40, '2': 20, '3': 20, '4': 20, '5': 0})
    por_muelle = {}
    for _, sid in a.rutas_estocasticas.items():
        por_muelle[sid] = por_muelle.get(sid, 0) + 1
    assert sum(por_muelle.values()) == 10
    assert por_muelle == {1: 4, 2: 2, 3: 2, 4: 2}    # 40/20/20/20
    assert 5 not in por_muelle                       # muelle cerrado (0%)


def test_cada_ruta_sale_siempre_por_su_muelle():
    a = _almacen({'enabled': True, 'cantidad': 4}, {'1': 50, '2': 50})
    vistos = {}
    for _ in range(50):
        ruta, sid = a._seleccionar_ruta()
        assert ruta is not None
        vistos.setdefault(ruta, sid)
        assert vistos[ruta] == sid                   # la ruta no cambia de muelle


def test_apagado_no_hay_rutas():
    a = _almacen({}, {'1': 100})
    assert a.rutas_estocasticas is None
    assert a._seleccionar_ruta() == (None, None)


def test_un_muelle_abierto_se_lleva_todas():
    a = _almacen({'enabled': True, 'cantidad': 5}, {'1': 100, '2': 0})
    assert sorted(set(a.rutas_estocasticas.values())) == [1]
    assert len(a.rutas_estocasticas) == 5
