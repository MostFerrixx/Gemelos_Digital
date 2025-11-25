import sys
import os
import json
import math
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pytmx

# Add project root to path to import existing modules if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

app = FastAPI()

# CORS for development convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA LOADING ---
TMX_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "layouts", "layout_v2.tmx"))
# Using the replay JSONL file which contains the full simulation state including initial released WOs
REPLAY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "simulation_20251120_224852", "replay_20251120_224852.jsonl"))

class ReplayData:
    def __init__(self):
        self.events = []
        self.max_time = 0
        self.snapshots = {}  # {timestamp: state_dict}
        self.snapshot_interval = 60.0  # Create a snapshot every 60 seconds
        self.load_data()
        self.precompute_snapshots()

    def precompute_snapshots(self):
        """
        Pre-computes state snapshots at PROGRESSIVE intervals to speed up seeking.
        Intervals decrease as simulation progresses to handle more events efficiently:
        - 0-5min: 60s intervals
        - 5-30min: 30s intervals  
        - 30min+: 15s intervals
        """
        print(f"Pre-computing progressive snapshots...")
        if not self.events:
            return

        # Initial state
        current_state = {
            "agents": {},
            "work_orders": {}
        }
        
        # Helper to determine next snapshot time based on current time
        def get_next_snapshot_time(current_t):
            if current_t < 300:  # 0-5 minutes
                return 60.0
            elif current_t < 1800:  # 5-30 minutes
                return 30.0
            else:  # 30+ minutes
                return 15.0
        
        # Process all events in order and save snapshots
        next_snapshot_time = 60.0  # First snapshot at 60s
        prev_time = None
        
        # We need to process events sequentially to build state
        for event in self.events:
            t = event.get('timestamp', 0)
            
            # Apply event to current_state
            self._apply_event_to_state(event, current_state)
            
            # Check if we just finished processing all t=0 events
            if prev_time == 0 and t > 0 and 0.0 not in self.snapshots:
                import copy
                self.snapshots[0.0] = copy.deepcopy(current_state)
            
            # If we passed a snapshot boundary, save current state
            while t >= next_snapshot_time and next_snapshot_time <= self.max_time:
                # Deep copy current state for the snapshot
                import copy
                self.snapshots[next_snapshot_time] = copy.deepcopy(current_state)
                print(f"  Snapshot at t={next_snapshot_time}s")
                
                # Calculate next interval based on current position
                interval = get_next_snapshot_time(next_snapshot_time)
                next_snapshot_time += interval
            
            prev_time = t
        
        # Save t=0 snapshot if we never exceeded t=0 (all events at t=0)
        if 0.0 not in self.snapshots:
            import copy
            self.snapshots[0.0] = copy.deepcopy(current_state)
            
        print(f"Created {len(self.snapshots)} progressive snapshots.")


    def _apply_event_to_state(self, event, state):
        """Helper to apply a single event to a state dict."""
        etype = event.get('event_type') or event.get('tipo') or event.get('type')
        data = event.get('data', {})
        agent_id = event.get('agent_id') or data.get('agent_id')
        
        if etype == 'agent_moved':
            if agent_id:
                if agent_id not in state['agents']:
                    state['agents'][agent_id] = {}
                pos = data.get('position') or [data.get('x', 0), data.get('y', 0)]
                state['agents'][agent_id]['position'] = pos
                state['agents'][agent_id]['type'] = data.get('agent_type', 'Unknown')
                state['agents'][agent_id]['status'] = data.get('status', 'idle')
                
        elif etype == 'estado_agente':
            if agent_id:
                if agent_id not in state['agents']:
                    state['agents'][agent_id] = {}
                pos = event.get('position') or data.get('position') or [0, 0]
                state['agents'][agent_id]['position'] = pos
                state['agents'][agent_id]['type'] = event.get('agent_type') or data.get('agent_type', 'Unknown')
                state['agents'][agent_id]['status'] = event.get('status') or data.get('status', 'idle')
                
        elif etype == 'work_order_update':
            wo_id = data.get('id') or event.get('id')
            if wo_id:
                # Use data if it has content, otherwise use the entire event (for synthetic events)
                state['work_orders'][wo_id] = data if data else event

    def load_data(self):
        print(f"Loading replay data from {REPLAY_FILE}...")
        try:
            self.events = []
            with open(REPLAY_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        
                        # Handle SIMULATION_START to extract initial WOs
                        if event.get('type') == 'SIMULATION_START' or event.get('event_type') == 'SIMULATION_START':
                            # Extract initial WOs directly from event
                            initial_wos = event.get('initial_work_orders', [])
                            print(f"Found {len(initial_wos)} initial WOs in SIMULATION_START")
                            
                            # Create synthetic update events for these initial WOs so they appear in the timeline
                            timestamp = event.get('timestamp', 0.0)
                            for wo in initial_wos:
                                # Create a synthetic update event
                                synthetic_event = wo.copy()
                                synthetic_event['type'] = 'work_order_update'
                                synthetic_event['timestamp'] = timestamp
                                # Ensure status defaults to 'released' if missing
                                if 'status' not in synthetic_event:
                                    synthetic_event['status'] = 'released'
                                self.events.append(synthetic_event)
                            
                            # Also add the start event itself just in case
                            self.events.append(event)
                        else:
                            # Normal event
                            self.events.append(event)
                            
                    except json.JSONDecodeError:
                        continue
            
            # Sort events by timestamp
            self.events.sort(key=lambda x: x.get('timestamp', 0))
            
            if self.events:
                self.max_time = self.events[-1].get('timestamp', 0)
            print(f"Loaded {len(self.events)} events. Max time: {self.max_time}")
        except Exception as e:
            print(f"Error loading replay data: {e}")
            import traceback
            traceback.print_exc()

replay_data = ReplayData()

# --- API ENDPOINTS ---

@app.get("/api/layout")
def get_layout():
    """Parses TMX file and returns geometry for rendering."""
    if not os.path.exists(TMX_PATH):
        # Fallback to old path if v2 doesn't exist, just in case
        fallback_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "layouts", "WH1.tmx"))
        if os.path.exists(fallback_path):
             tm = pytmx.TiledMap(fallback_path)
        else:
             raise HTTPException(status_code=404, detail=f"TMX file not found at {TMX_PATH}")
    else:
        tm = pytmx.TiledMap(TMX_PATH)

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


@app.get("/api/snapshot")
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

    # Return unified response with both state and metrics
    return {
        "timestamp": t,
        "max_time": replay_data.max_time,
        "state": {
            "agents": current_state['agents'],
            "work_orders": current_state['work_orders']
        },
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
            }
        }
    }

@app.get("/api/state")
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
        "agents": current_state['agents'],
        "work_orders": current_state['work_orders']
    }


@app.get("/api/metrics")
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




# Serve static files (Frontend)
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
