# -*- coding: utf-8 -*-
"""Endpoints de los RUNNERS (simulacion via websocket, optimizador Optuna,
experimentos A/B). REFACTOR 2026-07-07: extraido verbatim del monolito
server.py."""
import json
import os
import tempfile as _tempfile
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from web_prototype.app_state import PROJECT_ROOT, config_manager
from web_prototype.experiment_runner_web import ExperimentWebRunner
from web_prototype.optimization_runner import OptimizationRunner
from web_prototype.simulation_runner import SimulationRunner

router = APIRouter()


class StartOptimizationRequest(BaseModel):
    """INIT-3: parametros para lanzar un estudio de optimizacion Optuna"""
    n_trials: int = 50
    n_jobs: int = 2
    study_name: Optional[str] = None
    cost_ground: float = 15.0
    cost_forklift: float = 50.0
    penalty_failed: float = 100.0
    penalty_late: float = 50.0  # MEJ-SLA-OPT: $ por pedido con SLA vencido


class StartExperimentRequest(BaseModel):
    """MEJ-EXP-WEB: parametros para lanzar una comparacion A/B de configs.
    config_a/config_b: "current" (config.json canonico) o el id de un preset."""
    config_a: str = "current"
    config_b: str = "current"
    replicas: int = 5
    base_seed: int = 1000


@router.websocket("/ws/simulation-runner")
async def websocket_simulation_runner(websocket: WebSocket):
    await websocket.accept()
    runner = SimulationRunner()
    
    try:
        # Check if simulation is already running
        if runner.is_running():
            await websocket.send_json({
                "type": "error",
                "message": "System busy: A simulation is already running"
            })
            return
        
        # Wait for START command
        data = await websocket.receive_json()
        if data.get("command") != "START":
            await websocket.send_json({
                "type": "error", 
                "message": "Invalid command. Expected START."
            })
            return
        
        # Run simulation and stream events.
        # BK-11: el cliente manda el config temporal preparado con
        # /api/simulation/stage-config; sin el se usa el canonico.
        async for event in runner.run_simulation_async(config_path=data.get("config_path")):
            await websocket.send_json(event)
            
    except WebSocketDisconnect:
        print("Client disconnected, cancelling simulation...")
        runner.cancel_current_simulation()
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Internal server error: {str(e)}"
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


class StageConfigRequest(BaseModel):
    """Config a usar en una corrida, SIN escribir el canonico. (BK-11)"""
    config: Dict[str, Any]


@router.post("/api/simulation/stage-config")
def stage_simulation_config(request: StageConfigRequest):
    """Prepara un config TEMPORAL para correr, sin tocar el config.json.  (BK-11)

    Antes, "Run Simulation" hacia POST /api/configurator/config: escribia el
    canonico con lo que tuviera el formulario y recien despues corria. Nadie
    pedia guardar, asi que una pestana con un estado viejo podia alterar en
    silencio la configuracion del proyecto (incidente real: dejo la congestion
    apagada en el canonico, 626 -> 614 WorkOrders).

    Ahora la corrida usa una copia temporal en `temp_web/` y el canonico solo
    cambia con "Aplicar Configuracion", que es explicito.

    El config se VALIDA igual (mismas reglas que al guardar): si no es valido se
    devuelve el error y no se corre, que es el comportamiento util de antes.
    """
    try:
        valido, errores = config_manager.validate_config(request.config)
        if not valido:
            return {"success": False, "errors": errores}

        temp_dir = os.path.join(PROJECT_ROOT, "temp_web")
        os.makedirs(temp_dir, exist_ok=True)
        fd, path = _tempfile.mkstemp(prefix="run_config_", suffix=".json", dir=temp_dir)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(request.config, f, indent=2, ensure_ascii=False)

        # Se devuelve relativo al proyecto: el runner lo resuelve y asi no se
        # expone una ruta absoluta del servidor al navegador.
        return {"success": True, "config_path": os.path.relpath(path, PROJECT_ROOT)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/simulation-status")
def get_simulation_status():
    """Check if a simulation is currently running"""
    runner = SimulationRunner()
    return {
        "running": runner.is_running()
    }


@router.post("/api/optimization/start")
def start_optimization(request: StartOptimizationRequest):
    """
    INIT-3: lanza un estudio de optimizacion Optuna en background (subprocess
    fire-and-forget) usando el config.json canonico como template. Un estudio
    de N trials puede tardar mucho mas que el timeout de 600s de una
    simulacion individual, por eso NO es sincrono: se lanza y se consulta el
    progreso via /api/optimization/status.
    """
    runner = OptimizationRunner()
    try:
        result = runner.start(
            config_path=os.path.join(PROJECT_ROOT, "config.json"),
            n_trials=request.n_trials,
            n_jobs=request.n_jobs,
            study_name=request.study_name,
            cost_ground=request.cost_ground,
            cost_forklift=request.cost_forklift,
            penalty_failed=request.penalty_failed,
            penalty_late=request.penalty_late,
        )
        return {"started": True, **result}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/api/optimization/status")
def get_optimization_status(study_name: Optional[str] = None, storage: Optional[str] = None):
    """
    Progreso del estudio (trials completados, mejor score/params hasta ahora).
    Lee directamente la BD SQLite de Optuna -- funciona aunque el servidor se
    haya reiniciado desde que se lanzo el estudio, pasando study_name/storage.
    """
    runner = OptimizationRunner()
    return runner.status(study_name=study_name, storage=storage)


@router.post("/api/optimization/stop")
def stop_optimization():
    """Cancela el estudio de optimizacion en curso (si lo hay)."""
    runner = OptimizationRunner()
    stopped = runner.stop()
    if not stopped:
        raise HTTPException(status_code=409, detail="No hay ninguna optimizacion en curso.")
    return {"stopped": True}


def _materialize_experiment_config(selector: str) -> tuple:
    """MEJ-EXP-WEB: resuelve el selector de config ("current" o id de preset) a
    un path de archivo legible por experiment_runner.py y una etiqueta humana.
    Los presets se validan (misma barrera que el guardado) y se escriben a un
    temp file; "current" usa el config.json canonico directamente."""
    import tempfile as _tempfile
    if selector == "current":
        return os.path.join(PROJECT_ROOT, "config.json"), "Actual (config.json)"

    # BK-36: el preset corre con SU replica (mapa, datos, archivos) y una copia
    # descartable de su base.
    config = config_manager.config_para_experimento(
        selector, os.path.join(PROJECT_ROOT, "temp_web"))
    if config is None:
        raise HTTPException(status_code=404, detail=f"Preset '{selector}' no encontrado.")
    is_valid, errors = config_manager.validate_config(config)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"El preset '{selector}' no pasa la validacion del motor: {errors}")

    name = selector
    for meta in config_manager.list_configurations():
        if meta.get("id") == selector:
            name = meta.get("name", selector)
            break

    # DISK 2026-07-07: temp del PROYECTO (D), no %TEMP% (C). La purga de
    # viejos la hace experiment_runner.purge_stale_temp en cada corrida.
    temp_dir = os.path.join(PROJECT_ROOT, "temp_web")
    os.makedirs(temp_dir, exist_ok=True)
    fd, path = _tempfile.mkstemp(prefix="experiment_config_", suffix=".json", dir=temp_dir)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return path, name


@router.post("/api/experiment/start")
def start_experiment(request: StartExperimentRequest):
    """
    MEJ-EXP-WEB: lanza una comparacion A/B (scripts/experiment_runner.py compare)
    en background. 2xN replicas con semillas pareadas y veredicto estadistico
    por KPI. Progreso via GET /api/experiment/status (polling).
    """
    if request.config_a == request.config_b:
        raise HTTPException(status_code=400,
                            detail="Config A y Config B son la misma: no hay nada que comparar.")
    if not (1 <= request.replicas <= 50):
        raise HTTPException(status_code=400, detail="replicas debe estar entre 1 y 50.")

    path_a, label_a = _materialize_experiment_config(request.config_a)
    path_b, label_b = _materialize_experiment_config(request.config_b)

    runner = ExperimentWebRunner()
    try:
        result = runner.start(path_a, path_b, label_a, label_b,
                              replicas=request.replicas, base_seed=request.base_seed)
        return {"started": True, **result}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/api/experiment/status")
def get_experiment_status():
    """Progreso del experimento A/B (replicas completadas, resultado al final)."""
    runner = ExperimentWebRunner()
    return runner.status()


@router.post("/api/experiment/stop")
def stop_experiment():
    """Cancela el experimento A/B en curso (si lo hay)."""
    runner = ExperimentWebRunner()
    stopped = runner.stop()
    if not stopped:
        raise HTTPException(status_code=409, detail="No hay ningun experimento en curso.")
    return {"stopped": True}

