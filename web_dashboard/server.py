"""
Web Dashboard Server for Digital Twin Warehouse
Serves the web dashboard and provides API endpoints for replay data
"""
import sys
import os
import json
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

app = FastAPI(title="Digital Twin Warehouse Dashboard")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== DATA LOADING ==========
# Using the same replay file as the web_prototype
REPLAY_FILE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 
    "..", 
    "output", 
    "simulation_20251120_224852", 
    "replay_20251120_224852.jsonl"
))

class ReplayData:
    def __init__(self):
        self.events = []
        self.max_time = 0
        self.load_data()

    def load_data(self):
        print(f"[Server] Loading replay data from {REPLAY_FILE}...")
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
                            initial_wos = event.get('initial_work_orders', [])
                            print(f"[Server] Found {len(initial_wos)} initial WOs in SIMULATION_START")
                            
                            # Create synthetic update events for initial WOs
                            timestamp = event.get('timestamp', 0.0)
                            for wo in initial_wos:
                                synthetic_event = wo.copy()
                                synthetic_event['type'] = 'work_order_update'
                                synthetic_event['timestamp'] = timestamp
                                if 'status' not in synthetic_event:
                                    synthetic_event['status'] = 'released'
                                self.events.append(synthetic_event)
                            
                            self.events.append(event)
                        else:
                            self.events.append(event)
                            
                    except json.JSONDecodeError:
                        continue
            
            # Sort events by timestamp
            self.events.sort(key=lambda x: x.get('timestamp', 0))
            
            if self.events:
                self.max_time = self.events[-1].get('timestamp', 0)
            print(f"[Server] Loaded {len(self.events)} events. Max time: {self.max_time:.2f}s")
        except Exception as e:
            print(f"[Server] Error loading replay data: {e}")
            import traceback
            traceback.print_exc()

replay_data = ReplayData()

# ========== API ENDPOINTS ==========

@app.get("/api/state")
def get_state(t: float):
    """Returns the state of all work orders at timestamp t."""
    current_state = {
        "work_orders": {}
    }
    
    # Filter events up to time t
    relevant_events = [e for e in replay_data.events if e.get('timestamp', 0) <= t]
    
    for event in relevant_events:
        etype = event.get('event_type') or event.get('tipo') or event.get('type')
        data = event.get('data', {})
        
        if etype == 'work_order_update':
            wo_id = data.get('id') or event.get('id')
            if wo_id:
                # Use event data directly if no nested 'data' key
                current_state['work_orders'][wo_id] = event if not data else data
    
    return {
        "timestamp": t,
        "max_time": replay_data.max_time,
        "work_orders": current_state['work_orders']
    }

@app.get("/api/metrics")
def get_metrics(t: float):
    """Returns comprehensive metrics at timestamp t."""
    state_data = get_state(t)
    work_orders = state_data['work_orders']
    
    # Helper to get status
    get_status = lambda wo: wo.get('status', 'released')
    
    is_released = lambda wo: get_status(wo) == 'released' or (get_status(wo) == 'assigned' and not wo.get('assigned_agent_id'))
    is_assigned = lambda wo: get_status(wo) == 'assigned' and wo.get('assigned_agent_id')
    
    wo_total = len(work_orders)
    wo_staged = sum(1 for wo in work_orders.values() if get_status(wo) == 'staged')
    wo_picked = sum(1 for wo in work_orders.values() if get_status(wo) == 'picked')
    wo_in_progress = sum(1 for wo in work_orders.values() if get_status(wo) == 'in_progress')
    wo_assigned = sum(1 for wo in work_orders.values() if is_assigned(wo))
    wo_released = sum(1 for wo in work_orders.values() if is_released(wo))
    
    # Calculate throughput
    if t > 0:
        throughput = (wo_staged / t) * 60.0
    else:
        throughput = 0.0
    
    return {
        "simulation_time": t,
        "work_orders": {
            "total": wo_total,
            "staged": wo_staged,
            "picked": wo_picked,
            "in_progress": wo_in_progress,
            "assigned": wo_assigned,
            "released": wo_released,
            "completion_rate": (wo_staged / wo_total * 100) if wo_total > 0 else 0
        },
        "performance": {
            "throughput_per_minute": round(throughput, 2),
            "avg_time_per_wo": round(t / wo_staged, 2) if wo_staged > 0 else 0
        }
    }

@app.get("/api/info")
def get_info():
    """Returns general information about the replay."""
    return {
        "total_events": len(replay_data.events),
        "max_time": replay_data.max_time,
        "replay_file": REPLAY_FILE,
        "status": "loaded" if replay_data.events else "error"
    }

@app.get("/")
def serve_index():
    """Serve the dashboard HTML."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "index.html")
    )

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory=os.path.dirname(__file__)), name="static")

# Also serve files directly from root for convenience
@app.get("/style.css")
def serve_css():
    return FileResponse(os.path.join(os.path.dirname(__file__), "style.css"))

@app.get("/app.js")
def serve_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "app.js"))

if __name__ == "__main__":
    print("=" * 60)
    print("DIGITAL TWIN WAREHOUSE - WEB DASHBOARD")
    print("Dashboard Server v1.0")
    print(f"Replay file: {REPLAY_FILE}")
    print("=" * 60)
    print()
    print("Dashboard will be available at:")
    print("  http://localhost:8001")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
