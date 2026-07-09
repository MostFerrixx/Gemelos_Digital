# -*- coding: utf-8 -*-
"""Endpoints del VISOR de replay (layout TMX, snapshot/state/metrics,
carga/subida de replays, event markers).
REFACTOR 2026-07-07: extraido verbatim del monolito server.py."""
import os
import shutil

import pytmx
from fastapi import APIRouter, File, HTTPException, UploadFile

from web_prototype.app_state import PROJECT_ROOT, TMX_PATH, config_manager, replay_data

router = APIRouter()


@router.get("/api/layout")
def get_layout():
    """Parses TMX file and returns geometry for rendering.

    FIX: resuelve el mapa desde la CONFIGURACION (config.json -> layout_file), que es
    el MISMO mapa que usa la simulacion. Antes usaba una ruta fija
    (data/layouts/layout_v2.tmx) que no existe -> caia al mapa viejo (30x30) y no
    coincidia con la simulacion (el v2 es 30x42), por eso el visor "no se veia bien".
    Orden: layout_file del config -> ruta historica -> WH1.tmx.
    """
    candidates = []
    try:
        cfg = config_manager.load_config()
        layout_rel = cfg.get('layout_file')
        if layout_rel:
            candidates.append(os.path.join(PROJECT_ROOT, layout_rel))
    except Exception as e:
        print(f"[API/LAYOUT] No se pudo leer layout_file del config: {e}")
    candidates.append(TMX_PATH)  # ruta historica (compat)
    candidates.append(os.path.join(PROJECT_ROOT, "layouts", "WH1.tmx"))  # fallback final
    tmx_file = next((p for p in candidates if p and os.path.exists(p)), None)
    if tmx_file is None:
        raise HTTPException(status_code=404, detail=f"TMX no encontrado. Probados: {candidates}")
    print(f"[API/LAYOUT] Sirviendo mapa: {tmx_file}")
    tm = pytmx.TiledMap(tmx_file)

    try:
        layers = []
        
        # Extract walls and zones
        for layer in tm.layers:
            if hasattr(layer, 'data'):
                layer_data = []
                for y, row in enumerate(layer.data):
                    for x, gid in enumerate(row):
                        if gid != 0:
                            # Simple mapping for prototype
                            # In real app, we'd map GID to properties
                            layer_data.append({"x": x, "y": y, "gid": gid})
                layers.append({"name": layer.name, "tiles": layer_data})
        
        return {
            "width": tm.width,
            "height": tm.height,
            "tile_width": tm.tilewidth,
            "tile_height": tm.tileheight,
            "layers": layers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/snapshot")
def get_snapshot(t: float):
    """
    UNIFIED ENDPOINT: Returns both state and metrics in a single request.
    This reduces HTTP traffic by 50% compared to separate /api/state + /api/metrics calls.
    """
    # OPTIMIZATION: Use nearest snapshot
    snapshot_times = [st for st in replay_data.snapshots.keys() if st <= t]
    
    if snapshot_times:
        base_time = max(snapshot_times)
        # Deep copy to avoid modifying the snapshot
        import copy
        current_state = copy.deepcopy(replay_data.snapshots[base_time])
        # Only process events AFTER the snapshot
        relevant_events = [e for e in replay_data.events if base_time < e.get('timestamp', 0) <= t]
    else:
        current_state = {
            "agents": {},
            "work_orders": {}
        }
        relevant_events = [e for e in replay_data.events if e.get('timestamp', 0) <= t]
    
    for event in relevant_events:
        replay_data._apply_event_to_state(event, current_state)
    
    # Compute work_orders_asignadas for each agent
    # Based on desktop implementation in replay_engine.py
    for agent_id in current_state['agents']:
        assigned_wos = []
        for wo_id, wo in current_state['work_orders'].items():
            # Check if WO is assigned to this agent
            wo_agent = wo.get('assigned_agent_id') or wo.get('agent_id')
            wo_status = wo.get('status', 'released')
            
            # Normalize agent ID matching - WO agents are like "Forklift_Forklift-01" 
            # but state agents are "Forklift-01"
            # Extract the last part after underscore if present
            if wo_agent:
                if '_' in wo_agent:
                    wo_agent_short = wo_agent.split('_')[-1]
                else:
                    wo_agent_short = wo_agent
            else:
                wo_agent_short = None
            
            # Only include WOs that are PENDING (not picked or staged)
            # picked = completed picking, staged = delivered to staging
            pending_statuses = ['assigned', 'in_progress']
            if wo_agent_short == agent_id and wo_status in pending_statuses:
                assigned_wos.append({
                    'id': wo_id,
                    'location': wo.get('location') or wo.get('ubicacion', [0, 0]),
                    'status': wo_status,
                    'pick_sequence': wo.get('pick_sequence', 0)
                })
        
        # Sort by pick_sequence to maintain tour order
        assigned_wos.sort(key=lambda x: x['pick_sequence'])
        current_state['agents'][agent_id]['work_orders_asignadas'] = assigned_wos

    # Compute metrics (integrated from get_metrics)
    work_orders = current_state['work_orders']
    agents = current_state['agents']
    
    # Helper lambdas for status checks
    get_status = lambda wo: wo.get('status', 'released')
    is_released = lambda wo: get_status(wo) == 'released' or (get_status(wo) == 'assigned' and not wo.get('assigned_agent_id'))
    is_assigned = lambda wo: get_status(wo) == 'assigned' and wo.get('assigned_agent_id')
    
    # Count work orders by status
    wo_total = len(work_orders)
    wo_completed = sum(1 for wo in work_orders.values() if wo.get('status') == 'staged')
    
    # Count agents by status
    agent_total = len(agents)
    agent_active = sum(1 for agent in agents.values() if agent.get('status') in ['moving', 'picking', 'unloading'])
    agent_idle = sum(1 for agent in agents.values() if agent.get('status') == 'idle')
    
    # Calculate throughput (WOs per minute)
    if t > 0:
        throughput = (wo_completed / t) * 60.0
    else:
        throughput = 0.0
    
    # Count by agent type
    ground_operators = sum(1 for agent in agents.values() if 'Ground' in agent.get('type', ''))
    forklifts = sum(1 for agent in agents.values() if 'Forklift' in agent.get('type', ''))
    
    # === NEW: Dashboard de Agentes Metrics ===
    # Calculate utilizacion_promedio (% of agents not idle)
    operarios_working = sum(1 for agent in agents.values() if agent.get('status') in ['working', 'picking', 'lifting', 'unloading'])
    operarios_traveling = sum(1 for agent in agents.values() if agent.get('status') in ['moving', 'traveling'])
    operarios_idle = sum(1 for agent in agents.values() if agent.get('status') in ['idle', 'Esperando tour'])
    
    if agent_total > 0:
        utilizacion_promedio = ((operarios_working + operarios_traveling) / agent_total) * 100.0
    else:
        utilizacion_promedio = 0.0
    
    # Calculate WIP (Work In Progress = total - completed)
    wip = max(wo_total - wo_completed, 0)
    
    # Calculate tareas_completadas (tasks completed = wo_completed * 3)
    # Each WorkOrder has 3 tasks in the desktop version
    tareas_completadas = wo_completed * 3
    
    # Add cargo_volume to each agent for load bar visualization
    # Note: This would normally come from the event data, but we'll set a placeholder
    for agent_id, agent_data in agents.items():
        # If cargo_volume not already in agent data, initialize it
        if 'cargo_volume' not in agent_data:
            agent_data['cargo_volume'] = 0
        # capacidad would also come from agent config, set default
        if 'capacidad' not in agent_data:
            # Default capacity: GroundOperator = 100, Forklift = 200
            agent_type = agent_data.get('type', '')
            agent_data['capacidad'] = 200 if 'Forklift' in agent_type else 100

    # Return unified response with both state and metrics
    return {
        "timestamp": t,
        "max_time": replay_data.max_time,
        "service_level": replay_data.service_level,  # INIT-5: nivel de servicio (backorders)
        "sla_summary": replay_data.sla_summary,  # INIT-4b: cumplimiento de SLA (due_time)
        "bottleneck_summary": replay_data.bottleneck_summary,  # MEJ-BOTTLENECK: cuellos de botella
        "state": {
            "agents": agents,  # Now includes cargo_volume and capacidad
            "work_orders": current_state['work_orders']
        },
        "metricas": {
            # Core metrics (matching desktop estado_visual["metricas"])
            "tiempo": t,
            "workorders_completadas": wo_completed,
            "total_wos": wo_total,
            "tareas_completadas": tareas_completadas,
            "operarios_idle": operarios_idle,
            "operarios_working": operarios_working,
            "operarios_traveling": operarios_traveling,
            "utilizacion_promedio": round(utilizacion_promedio, 1),
            "wip": wip,
            # Throughput (WOs per minute) - CRITICAL: Division by zero protection
            "throughput_min": round(throughput, 2) if t > 0 else 0.0,
        },
        # Legacy metrics structure (keep for backward compatibility)
        "metrics": {
            "simulation_time": t,
            "work_orders": {
                "total": wo_total,
                "staged": wo_completed,
                "picked": sum(1 for wo in work_orders.values() if get_status(wo) == 'picked'),
                "in_progress": sum(1 for wo in work_orders.values() if get_status(wo) == 'in_progress'),
                "assigned": sum(1 for wo in work_orders.values() if is_assigned(wo)),
                "released": sum(1 for wo in work_orders.values() if is_released(wo)),
                "completion_rate": (wo_completed / wo_total * 100) if wo_total > 0 else 0
            },
            "agents": {
                "total": agent_total,
                "active": agent_active,
                "idle": agent_idle,
                "ground_operators": ground_operators,
                "forklifts": forklifts
            },
            "performance": {
                "throughput_per_minute": round(throughput, 2),
                "avg_time_per_wo": round(t / wo_completed, 2) if wo_completed > 0 else 0
            },
            # F2.c: contadores de camion acumulados hasta t (0 si outbound off)
            "outbound": {
                "trucks_dispatched": current_state.get('outbound', {}).get('trucks_dispatched', 0),
                "pallets_shipped": current_state.get('outbound', {}).get('pallets_shipped', 0),
                "backlog": current_state.get('outbound', {}).get('backlog', 0),
            },
            "service_level": replay_data.service_level,  # INIT-5: nivel de servicio (backorders)
            "sla_summary": replay_data.sla_summary,  # INIT-4b: cumplimiento de SLA (due_time)
            "bottleneck_summary": replay_data.bottleneck_summary  # MEJ-BOTTLENECK: cuellos de botella
        }
    }


@router.get("/api/state")
def get_state(t: float):
    """Returns the state of the world at timestamp t."""
    # Naive implementation: Replay all events from 0 to t
    # In production, we would use snapshots/keyframes for performance
    
    # OPTIMIZATION: Use nearest snapshot
    snapshot_times = [st for st in replay_data.snapshots.keys() if st <= t]
    
    if snapshot_times:
        base_time = max(snapshot_times)
        # Deep copy to avoid modifying the snapshot
        import copy
        current_state = copy.deepcopy(replay_data.snapshots[base_time])
        # Only process events AFTER the snapshot
        relevant_events = [e for e in replay_data.events if base_time < e.get('timestamp', 0) <= t]
    else:
        current_state = {
            "agents": {},
            "work_orders": {}
        }
        relevant_events = [e for e in replay_data.events if e.get('timestamp', 0) <= t]
    
    for event in relevant_events:
        replay_data._apply_event_to_state(event, current_state)
    
    # Compute work_orders_asignadas for each agent
    # Based on desktop implementation in replay_engine.py
    for agent_id in current_state['agents']:
        assigned_wos = []
        for wo_id, wo in current_state['work_orders'].items():
            # Check if WO is assigned to this agent
            wo_agent = wo.get('assigned_agent_id') or wo.get('agent_id')
            wo_status = wo.get('status', 'released')
            
            # Normalize agent ID matching - WO agents are like "Forklift_Forklift-01" 
            # but state agents are "Forklift-01"
            # Extract the last part after underscore if present
            if wo_agent:
                if '_' in wo_agent:
                    wo_agent_short = wo_agent.split('_')[-1]
                else:
                    wo_agent_short = wo_agent
            else:
                wo_agent_short = None
            
            # Only include WOs that are PENDING (not picked or staged)
            # picked = completed picking, staged = delivered to staging
            pending_statuses = ['assigned', 'in_progress']
            if wo_agent_short == agent_id and wo_status in pending_statuses:
                assigned_wos.append({
                    'id': wo_id,
                    'location': wo.get('location') or wo.get('ubicacion', [0, 0]),
                    'status': wo_status,
                    'pick_sequence': wo.get('pick_sequence', 0)
                })
        
        # Sort by pick_sequence to maintain tour order
        assigned_wos.sort(key=lambda x: x['pick_sequence'])
        current_state['agents'][agent_id]['work_orders_asignadas'] = assigned_wos

    return {
        "timestamp": t,
        "max_time": replay_data.max_time,
        "service_level": replay_data.service_level,  # INIT-5: nivel de servicio (backorders)
        "sla_summary": replay_data.sla_summary,  # INIT-4b: cumplimiento de SLA (due_time)
        "bottleneck_summary": replay_data.bottleneck_summary,  # MEJ-BOTTLENECK: cuellos de botella
        "agents": current_state['agents'],
        "work_orders": current_state['work_orders']
    }


@router.get("/api/metrics")
def get_metrics(t: float):
    """Returns comprehensive metrics at timestamp t."""
    # Reuse state calculation
    state_data = get_state(t)
    
    work_orders = state_data['work_orders']
    agents = state_data['agents']
    
    # Count work orders by status
    # ACTUAL statuses in log: 'assigned', 'in_progress', 'picked', 'staged'
    # 'staged' = completed (tiempo_fin is set)
    # 'picked' = picking done, awaiting staging
    # 'in_progress' = actively being picked
    # 'assigned' = pending
    wo_total = len(work_orders)
    wo_completed = sum(1 for wo in work_orders.values() if wo.get('status') == 'staged')
    wo_in_progress = sum(1 for wo in work_orders.values() if wo.get('status') in ['in_progress', 'picked'])
    wo_pending = sum(1 for wo in work_orders.values() if wo.get('status') == 'assigned')
    
    # Count agents by status
    agent_total = len(agents)
    agent_active = sum(1 for agent in agents.values() if agent.get('status') in ['moving', 'picking', 'unloading'])
    agent_idle = sum(1 for agent in agents.values() if agent.get('status') == 'idle')
    
    # Calculate throughput (WOs per minute)
    if t > 0:
        throughput = (wo_completed / t) * 60.0
    else:
        throughput = 0.0
    
    # Count by agent type
    ground_operators = sum(1 for agent in agents.values() if 'Ground' in agent.get('type', ''))
    forklifts = sum(1 for agent in agents.values() if 'Forklift' in agent.get('type', ''))
    
    # Helper lambdas for status checks
    # MATCH PYTHON DASHBOARD LOGIC: Status defaults to 'released' if missing
    get_status = lambda wo: wo.get('status', 'released')
    
    is_released = lambda wo: get_status(wo) == 'released' or (get_status(wo) == 'assigned' and not wo.get('assigned_agent_id'))
    is_assigned = lambda wo: get_status(wo) == 'assigned' and wo.get('assigned_agent_id')

    return {
        "simulation_time": t,
        "service_level": replay_data.service_level,  # INIT-5: nivel de servicio (backorders)
        "sla_summary": replay_data.sla_summary,  # INIT-4b: cumplimiento de SLA (due_time)
        "bottleneck_summary": replay_data.bottleneck_summary,  # MEJ-BOTTLENECK: cuellos de botella
        "work_orders": {
            "total": wo_total,
            "staged": wo_completed,
            "picked": sum(1 for wo in work_orders.values() if get_status(wo) == 'picked'),
            "in_progress": sum(1 for wo in work_orders.values() if get_status(wo) == 'in_progress'),
            "assigned": sum(1 for wo in work_orders.values() if is_assigned(wo)),
            "released": sum(1 for wo in work_orders.values() if is_released(wo)),
            "completion_rate": (wo_completed / wo_total * 100) if wo_total > 0 else 0
        },
        "agents": {
            "total": agent_total,
            "active": agent_active,
            "idle": agent_idle,
            "ground_operators": ground_operators,
            "forklifts": forklifts
        },
        "performance": {
            "throughput_per_minute": round(throughput, 2),
            "avg_time_per_wo": round(t / wo_completed, 2) if wo_completed > 0 else 0
        }
    }


@router.post("/api/upload_replay")
async def upload_replay_file(file: UploadFile = File(...)):
    """
    Upload a new JSONL replay file and reload the simulation.
    
    Returns:
        - success: bool
        - message: str
        - max_time: float (if successful)
    """
    try:
        # Validate file extension
        if not file.filename.endswith('.jsonl'):
            raise HTTPException(
                status_code=400, 
                detail="Solo se permiten archivos .jsonl"
            )
        
        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join(PROJECT_ROOT, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Save file to uploads directory
        # REVIEW 2026-07-07: basename() -- un filename artesanal con
        # separadores (a/../../x.jsonl) escapaba de uploads/.
        file_path = os.path.join(uploads_dir, f"uploaded_{os.path.basename(file.filename)}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"File saved to: {file_path}")
        
        # Reload replay data with new file
        replay_data.reload_data(file_path)
        
        return {
            "success": True,
            "message": f"Archivo '{file.filename}' cargado exitosamente",
            "max_time": replay_data.max_time,
            "event_count": len(replay_data.events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading file: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



# ========================================================================
# SIMULATION RUNNER ENDPOINTS


@router.get("/api/validate-replay")
def validate_replay_file(file: str):
    """Validate that a replay file exists and is readable"""
    # REVIEW 2026-07-07: mismo `pass` muerto que tenia load_replay ->
    # validacion real del path resuelto contra PROJECT_ROOT.
    file_path = os.path.realpath(os.path.join(PROJECT_ROOT, file))
    root = os.path.realpath(PROJECT_ROOT)
    if not file_path.startswith(root + os.sep):
        raise HTTPException(status_code=400,
                            detail="Path fuera del proyecto (path traversal bloqueado)")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Replay file not found")
    
    if not file.endswith('.jsonl'):
        raise HTTPException(status_code=400, detail="Invalid file format")
    
    return {"valid": True, "path": file}


@router.post("/api/load_replay")
def load_replay_file(file: str):
    """Load an existing replay file from the server"""
    # REVIEW 2026-07-07: el chequeo de path traversal anterior era un `pass`
    # (codigo muerto que aparentaba validar). Validacion real: el path
    # RESUELTO debe quedar dentro de PROJECT_ROOT.
    file_path = os.path.realpath(os.path.join(PROJECT_ROOT, file))
    root = os.path.realpath(PROJECT_ROOT)
    if not file_path.startswith(root + os.sep):
        raise HTTPException(status_code=400,
                            detail="Path fuera del proyecto (path traversal bloqueado)")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Replay file not found")

    if not file.endswith('.jsonl'):
        raise HTTPException(status_code=400, detail="Invalid file format")
        
    try:
        print(f"Loading replay file: {file_path}")
        replay_data.reload_data(file_path)
        
        return {
            "success": True,
            "message": f"Archivo '{file}' cargado exitosamente",
            "max_time": replay_data.max_time,
            "event_count": len(replay_data.events)
        }
    except Exception as e:
        print(f"Error loading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/event-markers")
def get_event_markers():
    """D-15: tiempos de eventos notables del replay para marcar en la barra de tiempo.
    Hitos: salidas de camion outbound (truck_departed) y, desde INIT-7 F1,
    descargas de camion inbound (inbound_truck_departed). Devuelve [] si no hay
    (p.ej. ambos subsistemas apagados)."""
    markers = []
    try:
        for e in replay_data.events:
            etype = e.get('type') or e.get('event_type')
            if etype == 'truck_departed':
                t = e.get('timestamp', 0)
                loaded = e.get('pallets_loaded', 0)
                markers.append({
                    "t": t,
                    "type": "truck",
                    "label": f"Camion {e.get('truck_id', '')} ({loaded} pallets)".strip()
                })
            elif etype == 'inbound_truck_departed':
                t = e.get('timestamp', 0)
                unloaded = e.get('pallets_unloaded', 0)
                markers.append({
                    "t": t,
                    "type": "truck_in",
                    "label": (f"Recepcion {e.get('truck_id', '')} "
                              f"({unloaded} pallets, muelle {e.get('dock_id', '?')})").strip()
                })
    except Exception as ex:
        print(f"[EVENT-MARKERS] WARN: {ex}")
    return {"markers": markers, "max_time": replay_data.max_time}

