# -*- coding: utf-8 -*-
"""
MEJ-2: tests de la agregacion estadistica de scripts/experiment_runner.py.

Solo cubre summarize() y paired_verdict() con datos sinteticos -- no corre
la simulacion real (eso es un smoke manual, no una unit test). No toca el
motor ni el gate de regresion.
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

experiment_runner = pytest.importorskip("experiment_runner")


def test_summarize_media_basica():
    s = experiment_runner.summarize([10.0, 20.0, 30.0])
    assert s["n"] == 3
    assert s["mean"] == 20.0
    assert s["std"] > 0
    assert s["ci95_low"] < s["mean"] < s["ci95_high"]


def test_summarize_n_uno_sin_intervalo():
    s = experiment_runner.summarize([42.0])
    assert s["n"] == 1
    assert s["mean"] == 42.0
    assert s["std"] == 0.0
    assert s["ci95_low"] == s["ci95_high"] == 42.0


def test_paired_verdict_identico():
    v = experiment_runner.paired_verdict([5.0, 5.0, 5.0], [5.0, 5.0, 5.0])
    assert v["pvalue"] is None
    assert "IDENTICO" in v["verdict"]


def test_paired_verdict_diferencia_constante():
    v = experiment_runner.paired_verdict([5.0, 5.0, 5.0], [8.0, 8.0, 8.0])
    assert v["pvalue"] == 0.0
    assert "SIGNIFICATIVA" in v["verdict"]


def test_paired_verdict_diferencia_clara():
    values_a = [10.0, 11.0, 9.0, 10.5, 10.2]
    values_b = [20.0, 21.5, 19.0, 20.5, 20.1]
    v = experiment_runner.paired_verdict(values_a, values_b)
    assert v["pvalue"] < 0.05
    assert "SIGNIFICATIVA" in v["verdict"]


def test_paired_verdict_ruido_con_pocas_replicas():
    v = experiment_runner.paired_verdict([10.0, 15.0], [11.0, 14.0])
    assert v["verdict"] is not None  # no debe explotar con N=2


def test_paired_verdict_requiere_misma_longitud():
    v = experiment_runner.paired_verdict([1.0, 2.0], [1.0])
    assert v["pvalue"] is None
    assert "N/A" in v["verdict"]
