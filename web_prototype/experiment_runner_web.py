import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, Optional


class ExperimentWebRunner:
    """
    MEJ-EXP-WEB: lanza scripts/experiment_runner.py (compare A/B) como
    subprocess fire-and-forget y expone el progreso leyendo el JSON que el
    runner escribe via --progress-json (escritura atomica en el runner, asi
    el polling nunca lee un archivo a medio escribir).

    Mismo patron que OptimizationRunner: una comparacion de 2xN replicas
    (cada una ~10-15s de sim real) excede largamente el timeout de 600s del
    SimulationRunner interactivo, por eso NO es sincrono ni streameado.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ExperimentWebRunner, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._process: Optional[subprocess.Popen] = None
        self._progress_path: Optional[str] = None
        self._labels: Dict[str, str] = {}
        self.PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.PYTHON_EXECUTABLE = sys.executable

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self, config_a_path: str, config_b_path: str,
              label_a: str, label_b: str,
              replicas: int = 5, base_seed: int = 1000) -> Dict[str, Any]:
        if self.is_running():
            raise RuntimeError(
                "Ya hay un experimento en curso. Espera a que termine o cancelalo primero.")

        # DISK 2026-07-07: temp del PROYECTO (D), no %TEMP% (C); y borrar el
        # progress del experimento anterior (antes se acumulaban para siempre).
        temp_dir = os.path.join(self.PROJECT_ROOT, "temp_web")
        os.makedirs(temp_dir, exist_ok=True)
        if self._progress_path and os.path.exists(self._progress_path):
            try:
                os.remove(self._progress_path)
            except OSError:
                pass
        fd, progress_path = tempfile.mkstemp(prefix="experiment_web_", suffix=".json",
                                             dir=temp_dir)
        os.close(fd)

        cmd = [
            self.PYTHON_EXECUTABLE,
            os.path.join(self.PROJECT_ROOT, "scripts", "experiment_runner.py"),
            "compare",
            "--config-a", config_a_path,
            "--config-b", config_b_path,
            "--replicas", str(replicas),
            "--base-seed", str(base_seed),
            "--progress-json", progress_path,
        ]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        self._process = subprocess.Popen(
            cmd, cwd=self.PROJECT_ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self._progress_path = progress_path
        self._labels = {"a": label_a, "b": label_b}

        return {"pid": self._process.pid, "replicas": replicas, "base_seed": base_seed,
                "label_a": label_a, "label_b": label_b}

    def stop(self) -> bool:
        if not self.is_running():
            return False
        # REVIEW 2026-07-06: matar el ARBOL de procesos, no solo el padre
        # (mismo bug que OptimizationRunner: terminate() dejaba huerfano al
        # motor de la replica en curso, que seguia corriendo y dejaba su
        # carpeta output/ sin limpiar).
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(self._process.pid), "/T", "/F"],
                           capture_output=True)
        else:
            self._process.terminate()
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.kill()
        return True

    def status(self) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "running": self.is_running(),
            "labels": self._labels,
        }
        if not self._progress_path or not os.path.exists(self._progress_path):
            base.update({"status": "idle", "completed_replicas": 0, "total_replicas": 0})
            return base
        try:
            with open(self._progress_path, "r", encoding="utf-8") as f:
                progress = json.load(f)
        except Exception:
            # Lectura en el instante exacto del os.replace: transitorio, reintentar.
            base.update({"status": "initializing", "completed_replicas": 0, "total_replicas": 0})
            return base
        base.update(progress)
        # Proceso muerto sin status final en el JSON = detenido manualmente
        # (stop) o crasheo antes de escribir el resultado.
        if not base["running"] and progress.get("status") == "running":
            base["status"] = "error"
            base["error"] = ("El experimento termino sin reportar resultado "
                             "(detenido manualmente o crasheo -- revisar logs "
                             "del servidor si no fue un stop).")
        return base
