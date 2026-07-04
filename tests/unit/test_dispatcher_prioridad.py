# -*- coding: utf-8 -*-
"""
MEJ-1 / PR-xx: caracterizacion de INIT-4 C2 (prioridad de pedido, Opcion C).

_aplicar_prioridad_pedido: flag off -> lista intacta; flag on -> solo la mejor
priority, desempate por due_time ascendente (None al final), orden estable.
_pool_para_barrido: flag off o ancla no urgente -> todos; ancla urgente -> solo
WOs de la misma priority.
"""


def test_pr01_flag_off_devuelve_lista_intacta(make_dispatcher, make_wo):
    disp = make_dispatcher({"priority_dispatch_enabled": False})
    wos = [make_wo(priority=5), make_wo(priority=1), make_wo(priority=99)]
    resultado = disp._aplicar_prioridad_pedido(list(wos))
    assert resultado == wos  # mismo orden, mismos objetos


def test_pr01b_lista_vacia_no_rompe(make_dispatcher):
    disp = make_dispatcher({"priority_dispatch_enabled": True})
    assert disp._aplicar_prioridad_pedido([]) == []


def test_pr02_flag_on_conserva_solo_mejor_priority(make_dispatcher, make_wo):
    disp = make_dispatcher({"priority_dispatch_enabled": True})
    urgente_a = make_wo(priority=1)
    urgente_b = make_wo(priority=1)
    normal = make_wo(priority=99)
    medio = make_wo(priority=5)
    resultado = disp._aplicar_prioridad_pedido([normal, urgente_a, medio, urgente_b])
    assert set(resultado) == {urgente_a, urgente_b}


def test_pr03_empate_ordena_por_due_time_none_al_final(make_dispatcher, make_wo):
    disp = make_dispatcher({"priority_dispatch_enabled": True})
    sin_sla = make_wo(priority=1, due_time=None)
    sla_tarde = make_wo(priority=1, due_time=500.0)
    sla_pronto = make_wo(priority=1, due_time=100.0)
    resultado = disp._aplicar_prioridad_pedido([sin_sla, sla_tarde, sla_pronto])
    assert resultado == [sla_pronto, sla_tarde, sin_sla]


def test_pr04_pool_flag_off_devuelve_todo(make_dispatcher, make_wo):
    disp = make_dispatcher({"priority_dispatch_enabled": False})
    wos = [make_wo(priority=1), make_wo(priority=99)]
    ancla = wos[0]
    assert disp._pool_para_barrido(list(wos), ancla) == wos


def test_pr05_pool_ancla_no_urgente_no_filtra(make_dispatcher, make_wo):
    disp = make_dispatcher({"priority_dispatch_enabled": True})
    wos = [make_wo(priority=99), make_wo(priority=99), make_wo(priority=100)]
    ancla = wos[0]  # priority >= 99 -> sin filtro
    assert disp._pool_para_barrido(list(wos), ancla) == wos


def test_pr06_pool_ancla_urgente_filtra_misma_priority(make_dispatcher, make_wo):
    disp = make_dispatcher({"priority_dispatch_enabled": True})
    u1 = make_wo(priority=1)
    u2 = make_wo(priority=1)
    normal = make_wo(priority=99)
    otro_nivel = make_wo(priority=2)
    resultado = disp._pool_para_barrido([u1, normal, u2, otro_nivel], ancla=u1)
    assert resultado == [u1, u2]


def test_pr07_pool_ancla_none_devuelve_todo(make_dispatcher, make_wo):
    disp = make_dispatcher({"priority_dispatch_enabled": True})
    wos = [make_wo(priority=1)]
    assert disp._pool_para_barrido(list(wos), ancla=None) == wos
