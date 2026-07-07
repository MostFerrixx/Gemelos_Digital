import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, Optional

import optuna
from optuna.trial import TrialState


class OptimizationRunner:
    """
    Lanza entry_points/run_optimization.py como subprocess en background
    (fire-and-forget) y expone el progreso leyendo directamente el storage
    SQLite de Optuna -- funciona incluso si el servidor se reinicio mientras
    el estudio corria, porque el progreso vive en la BD, no en memoria.

    Un estudio de optimizacion (N trials x minutos cada uno) puede tardar
    mucho mas que el timeout de 600s de SimulationRunner: por eso NO se corre
    de forma sincrona ni streameada, se lanza y se consulta por polling.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OptimizationRunner, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._process: Optional[subprocess.Popen] = None
        self._study_name: Optional[str] = None
        self._storage: Optional[str] = None
        self.PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.PYTHON_EXECUTABLE = sys.executable

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self, config_path: str = "config.json", n_trials: int = 50,
              n_jobs: int = 2, study_name: Optional[str] = None,
              cost_ground: float = 15.0, cost_forklift: float = 50.0,
              penalty_failed: float = 100.0,
              penalty_late: float = 50.0) -> Dict[str, Any]:
        if self.is_running():
            raise RuntimeError(
                "Ya hay una optimizacion en curso ('%s'). Espera a que "
                "termine o cancelala primero." % self._study_name
            )

        study_name = study_name or ("web_opt_%s" % time.strftime("%Y%m%d_%H%M%S"))
        storage = "sqlite:///optuna_study.db"

        cmd = [
            self.PYTHON_EXECUTABLE,
            os.path.join(self.PROJECT_ROOT, "entry_points", "run_optimization.py"),
            "--config", config_path,
            "--n-trials", str(n_trials),
            "--n-jobs", str(n_jobs),
            "--study-name", study_name,
            "--storage", storage,
            "--cost-ground", str(cost_ground),
            "--cost-forklift", str(cost_forklift),
            "--penalty-failed", str(penalty_failed),
            "--penalty-late", str(penalty_late),
        ]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        self._process = subprocess.Popen(
            cmd, cwd=self.PROJECT_ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self._study_name = study_name
        self._storage = storage

        return {"study_name": study_name, "storage": storage, "pid": self._process.pid}

    def stop(self) -> bool:
        if not self.is_running():
            return False
        self._process.terminate()
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.kill()
        return True

    def status(self, study_name: Optional[str] = None,
               storage: Optional[str] = None) -> Dict[str, Any]:
        """Progreso del estudio leido directamente de la BD de Optuna.

        Acepta study_name/storage explicitos para poder consultar un estudio
        aunque el servidor se haya reiniciado (no depende de memoria del
        proceso actual).
        """
        study_name = study_name or self._study_name
        storage = storage or self._storage or "sqlite:///optuna_study.db"

        if not study_name:
            return {"running": self.is_running(), "study_name": None, "n_trials_completed": 0}

        try:
            study = optuna.load_study(study_name=study_name, storage=storage)
        except Exception:
            # BUGFIX concurrencia: justo despues de start(), el subprocess
            # recien esta creando/migrando el esquema SQLite (Alembic). Una
            # consulta de status que llega en ese instante puede chocar con
            # esa migracion (visto en la practica: IntegrityError de
            # sqlalchemy en alembic_version, no solo el KeyError esperado de
            # "estudio no existe"). Cualquier excepcion aca es transitoria --
            # se resuelve solo en el proximo poll.
            return {
                "running": self.is_running(),
                "study_name": study_name,
                "storage": storage,
                "n_trials_completed": 0,
                "note": "Estudio aun no existe o esta inicializando la BD (reintentar en unos segundos).",
            }

        trials = study.trials
        completed = [t for t in trials if t.state == TrialState.COMPLETE]

        result: Dict[str, Any] = {
            "running": self.is_running(),
            "study_name": study_name,
            "storage": storage,
            "n_trials_total": len(trials),
            "n_trials_completed": len(completed),
        }
        if completed:
            best = study.best_trial
            result["best_score"] = best.value
            result["best_params"] = best.params
            result["best_trial_number"] = best.number
        return result
