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


def test_collect_values_filtra_none_de_kpi_opcional():
    """MEJ-2 v2: fill_rate_pct es None en modo estocastico (INIT-5) -- debe
    filtrarse, no tratarse como 0.0 (ensuciaria media/std con datos falsos)."""
    results = [
        {"fill_rate_pct": None, "total_workorders_completed": 10},
        {"fill_rate_pct": None, "total_workorders_completed": 12},
    ]
    assert experiment_runner._collect_values("fill_rate_pct", results) == []
    assert experiment_runner._collect_values("total_workorders_completed", results) == [10, 12]


def test_collect_values_disponible_en_modo_deterministico():
    results = [
        {"fill_rate_pct": 87.5},
        {"fill_rate_pct": 92.0},
    ]
    assert experiment_runner._collect_values("fill_rate_pct", results) == [87.5, 92.0]


def _fake_results(n, completed=30, sim_time=250.0):
    return [{
        "total_workorders_completed": completed + i,
        "total_workorders_failed": 0,
        "total_simulation_time_seconds": sim_time + i,
        "avg_completion_time_seconds": 8.0,
        "throughput_wo_per_s": 0.12,
        "fill_rate_pct": None,  # modo estocastico
    } for i in range(n)]


def test_build_compare_result_filas_serializables(tmp_path):
    """MEJ-EXP-WEB: el resultado de compare debe ser JSON-serializable y marcar
    los KPIs no disponibles (fill_rate_pct None en estocastico) como available=False."""
    import json as _json
    rows = experiment_runner.build_compare_result(_fake_results(3), _fake_results(3, completed=40))
    _json.dumps(rows)  # no debe explotar
    by_kpi = {r["kpi"]: r for r in rows}
    assert by_kpi["total_workorders_completed"]["available"] is True
    assert by_kpi["total_workorders_completed"]["mean_b"] > by_kpi["total_workorders_completed"]["mean_a"]
    assert by_kpi["fill_rate_pct"]["available"] is False


def test_progress_writer_ciclo_completo(tmp_path):
    """MEJ-EXP-WEB: running -> replicas acumuladas -> done con resultado."""
    import json as _json
    path = str(tmp_path / "progress.json")
    pw = experiment_runner.ProgressWriter(path, "compare", 6)

    with open(path, encoding="utf-8") as f:
        state = _json.load(f)
    assert state["status"] == "running"
    assert state["total_replicas"] == 6
    assert state["completed_replicas"] == 0

    pw.on_replica("A", 1, 3)
    pw.on_replica("A", 2, 3)
    with open(path, encoding="utf-8") as f:
        state = _json.load(f)
    assert state["completed_replicas"] == 2
    assert state["current_label"] == "A"

    pw.finish([{"kpi": "x", "available": True}])
    with open(path, encoding="utf-8") as f:
        state = _json.load(f)
    assert state["status"] == "done"
    assert state["result"][0]["kpi"] == "x"


def test_progress_writer_fail(tmp_path):
    import json as _json
    path = str(tmp_path / "progress.json")
    pw = experiment_runner.ProgressWriter(path, "run", 5)
    pw.fail(RuntimeError("replica exploto"))
    with open(path, encoding="utf-8") as f:
        state = _json.load(f)
    assert state["status"] == "error"
    assert "replica exploto" in state["error"]
