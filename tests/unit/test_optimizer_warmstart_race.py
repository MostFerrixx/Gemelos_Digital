# -*- coding: utf-8 -*-
"""
INIT-3 v2: regresion del bug de concurrencia warm-start + n_jobs>1.

`study.enqueue_trial()` (warm-start del config actual) seguido de
`study.optimize(..., n_jobs>1)` provoca una carrera real de Optuna: dos
workers toman el mismo trial encolado y le asignan el mismo `trial.number`,
perdiendo un trial silenciosamente (reproducido y confirmado 2026-07-05 --
ver docs/CHANGELOG.md). Fix: `SimulationOptimizer.optimize()` consume el
warm-start en serie (n_jobs=1) ANTES de arrancar el resto en paralelo.

Este test reemplaza objective() por una funcion rapida (sin subprocess, sin
simulacion real) para verificar la orquestacion de Optuna en si misma, no el
motor.
"""
import json

import optuna

from tools.optimizer import SimulationOptimizer


def _optimizer(tmp_path, n_jobs):
    config_path = tmp_path / "base_config.json"
    config_path.write_text(json.dumps({
        "dispatch_strategy": "Ejecucion de Plan",
        "num_operarios_terrestres": 2,
        "num_montacargas": 2,
    }), encoding="utf-8")
    opt = SimulationOptimizer(base_config_path=str(config_path), n_parallel_jobs=n_jobs)
    opt.temp_configs_dir = str(tmp_path / "temp_configs")
    opt.temp_metrics_dir = str(tmp_path / "temp_metrics")
    return opt


def test_warmstart_mas_n_jobs_no_pierde_trials(tmp_path, monkeypatch):
    optimizer = _optimizer(tmp_path, n_jobs=3)

    def fake_objective(trial):
        trial.suggest_int("num_operarios_terrestres", 1, 20)
        trial.suggest_int("num_montacargas", 1, 10)
        trial.suggest_categorical("dispatch_strategy", ["Ejecucion de Plan", "Cercania"])
        trial.suggest_int("max_wos_por_tour", 5, 40)
        return 1.0

    monkeypatch.setattr(optimizer, "objective", fake_objective)

    storage = "sqlite:///%s" % (tmp_path / "warmstart_race.db").as_posix()
    result = optimizer.optimize(n_trials=6, study_name="warmstart_race_test",
                                 storage=storage, load_if_exists=False, cleanup=False)

    assert result["n_trials"] == 6

    study = optuna.load_study(study_name="warmstart_race_test", storage=storage)
    numbers = sorted(t.number for t in study.trials)
    assert numbers == list(range(6)), (
        "Se esperaban 6 trials con numeros unicos 0..5, se obtuvo: %s "
        "(si hay numeros repetidos, volvio la carrera warm-start + n_jobs>1)"
        % numbers
    )


def test_warmstart_con_n_jobs_uno_no_serializa_de_mas(tmp_path, monkeypatch):
    """Con n_jobs=1 no hay carrera posible; el fix no debe alterar el conteo."""
    optimizer = _optimizer(tmp_path, n_jobs=1)

    def fake_objective(trial):
        trial.suggest_int("num_operarios_terrestres", 1, 20)
        trial.suggest_int("num_montacargas", 1, 10)
        trial.suggest_categorical("dispatch_strategy", ["Ejecucion de Plan"])
        trial.suggest_int("max_wos_por_tour", 5, 40)
        return 1.0

    monkeypatch.setattr(optimizer, "objective", fake_objective)

    storage = "sqlite:///%s" % (tmp_path / "no_race.db").as_posix()
    result = optimizer.optimize(n_trials=3, study_name="no_race_test",
                                 storage=storage, load_if_exists=False, cleanup=False)

    assert result["n_trials"] == 3
