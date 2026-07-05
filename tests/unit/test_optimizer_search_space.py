# -*- coding: utf-8 -*-
"""
INIT-3: espacio de busqueda ampliado del optimizador (max_wos_por_tour +
radio_cercania condicional a la estrategia "Cercania").

Usa optuna.trial.FixedTrial para fijar los parametros sugeridos sin correr un
estudio real, y mockea subprocess.run para no ejecutar la simulacion real
(esto es un test de la CONSTRUCCION del trial_config, no del motor).
"""
import json
import os

import pytest
from optuna.trial import FixedTrial

from tools.optimizer import SimulationOptimizer


@pytest.fixture
def optimizer(tmp_path):
    config_path = tmp_path / "base_config.json"
    config_path.write_text(json.dumps({
        "dispatch_strategy": "Ejecucion de Plan",
        "num_operarios_terrestres": 2,
        "num_montacargas": 2,
    }), encoding="utf-8")

    opt = SimulationOptimizer(base_config_path=str(config_path), n_parallel_jobs=1)
    opt.temp_configs_dir = str(tmp_path / "temp_configs")
    opt.temp_metrics_dir = str(tmp_path / "temp_metrics")
    return opt


def _fake_run_ok(monkeypatch, metrics_dir, metrics_payload):
    """Mockea subprocess.run para no correr la sim real; escribe el metrics.json
    esperado en el path que objective() va a pasar via --output-metrics."""
    import subprocess as _subprocess

    class _FakeCompletedProcess:
        returncode = 0

    def _fake_run(cmd, **kwargs):
        # cmd = [python, entry_point, "--config", config_path, "--output-metrics", metrics_path]
        metrics_path = cmd[cmd.index("--output-metrics") + 1]
        os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics_payload, f)
        return _FakeCompletedProcess()

    monkeypatch.setattr(_subprocess, "run", _fake_run)


def _written_trial_config(optimizer_instance, trial_number):
    path = os.path.join(optimizer_instance.temp_configs_dir, f"trial_{trial_number}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_max_wos_por_tour_siempre_presente(optimizer, monkeypatch):
    fake_metrics = {
        "total_workorders_completed": 10, "total_workorders_failed": 0,
        "total_workorders": 10, "total_simulation_time_seconds": 100.0,
        "resource_costs": {"ground_operators": 2, "forklifts": 2},
    }
    _fake_run_ok(monkeypatch, optimizer.temp_metrics_dir, fake_metrics)

    trial = FixedTrial({
        "num_operarios_terrestres": 2, "num_montacargas": 2,
        "dispatch_strategy": "Ejecucion de Plan", "max_wos_por_tour": 15,
    })
    optimizer.objective(trial)

    written = _written_trial_config(optimizer, trial.number)
    assert written["max_wos_por_tour"] == 15
    assert "radio_cercania" not in written


def test_radio_cercania_solo_con_estrategia_cercania(optimizer, monkeypatch):
    fake_metrics = {
        "total_workorders_completed": 10, "total_workorders_failed": 0,
        "total_workorders": 10, "total_simulation_time_seconds": 100.0,
        "resource_costs": {"ground_operators": 2, "forklifts": 2},
    }
    _fake_run_ok(monkeypatch, optimizer.temp_metrics_dir, fake_metrics)

    trial = FixedTrial({
        "num_operarios_terrestres": 3, "num_montacargas": 1,
        "dispatch_strategy": "Cercania", "max_wos_por_tour": 20,
        "radio_cercania": 75,
    })
    optimizer.objective(trial)

    written = _written_trial_config(optimizer, trial.number)
    assert written["dispatch_strategy"] == "Cercania"
    assert written["radio_cercania"] == 75


def test_radio_cercania_ausente_en_otras_estrategias(optimizer, monkeypatch):
    fake_metrics = {
        "total_workorders_completed": 10, "total_workorders_failed": 0,
        "total_workorders": 10, "total_simulation_time_seconds": 100.0,
        "resource_costs": {"ground_operators": 1, "forklifts": 1},
    }
    _fake_run_ok(monkeypatch, optimizer.temp_metrics_dir, fake_metrics)

    trial = FixedTrial({
        "num_operarios_terrestres": 1, "num_montacargas": 1,
        "dispatch_strategy": "FIFO Estricto", "max_wos_por_tour": 8,
    })
    optimizer.objective(trial)

    written = _written_trial_config(optimizer, trial.number)
    assert written["dispatch_strategy"] == "FIFO Estricto"
    assert "radio_cercania" not in written
