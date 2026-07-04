# -*- coding: utf-8 -*-
"""
MEJ-1 / OL-xx: caracterizacion de INIT-4 C3 (olas / release diferido).

_wo_elegible_por_ola: con waves off, sin wave_id o sin release definido ->
siempre elegible; con release, elegible solo cuando env.now >= release.
Normalizacion de release_times: claves a str, valores no numericos ignorados.
"""


def test_ol01_waves_off_siempre_elegible(make_dispatcher, make_wo):
    disp = make_dispatcher({"waves": {"enabled": False,
                                      "release_times": {"1": 1000}}})
    wo = make_wo(wave_id="1")
    assert disp._wo_elegible_por_ola(wo) is True


def test_ol02_wo_sin_wave_id_elegible(make_dispatcher, make_wo):
    disp = make_dispatcher({"waves": {"enabled": True,
                                      "release_times": {"1": 1000}}})
    wo = make_wo(wave_id=None)
    assert disp._wo_elegible_por_ola(wo) is True


def test_ol03_ola_sin_release_definido_elegible(make_dispatcher, make_wo):
    disp = make_dispatcher({"waves": {"enabled": True,
                                      "release_times": {"1": 1000}}})
    wo = make_wo(wave_id="99")  # ola sin release -> defensivo, elegible
    assert disp._wo_elegible_por_ola(wo) is True


def test_ol04_release_futuro_bloquea_y_pasado_libera(make_dispatcher, make_wo, fake_env):
    disp = make_dispatcher({"waves": {"enabled": True,
                                      "release_times": {"2": 300}}},
                           env=fake_env)
    wo = make_wo(wave_id="2")
    fake_env.now = 299.9
    assert disp._wo_elegible_por_ola(wo) is False
    fake_env.now = 300.0
    assert disp._wo_elegible_por_ola(wo) is True


def test_ol05_normalizacion_claves_int_y_valores_basura(make_dispatcher, make_wo, fake_env):
    # Claves int del JSON -> lookup por str; valores no numericos se descartan.
    disp = make_dispatcher({"waves": {"enabled": True,
                                      "release_times": {1: 100, "2": "abc"}}},
                           env=fake_env)
    assert disp.wave_release_times == {"1": 100.0}
    wo_ola1 = make_wo(wave_id=1)  # wave_id int -> lookup str(1)
    fake_env.now = 50.0
    assert disp._wo_elegible_por_ola(wo_ola1) is False
    fake_env.now = 100.0
    assert disp._wo_elegible_por_ola(wo_ola1) is True
    # Ola "2" quedo sin release valido -> elegible (defensivo)
    assert disp._wo_elegible_por_ola(make_wo(wave_id="2")) is True


def test_ol06_bloque_waves_malformado_desactiva(make_dispatcher):
    disp = make_dispatcher({"waves": "no-soy-un-dict"})
    assert disp.waves_enabled is False
    assert disp.wave_release_times == {}
