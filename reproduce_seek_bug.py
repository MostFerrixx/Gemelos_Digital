import sys
import os
import json
from copy import deepcopy

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Mock pygame to avoid display issues in headless environment
import unittest.mock
sys.modules['pygame'] = unittest.mock.MagicMock()
sys.modules['pygame_gui'] = unittest.mock.MagicMock()

# Import ReplayViewerEngine
from src.engines.replay_engine import ReplayViewerEngine, estado_visual

def verify_seek_logic(replay_file):
    print(f"Loading replay file: {replay_file}")
    
    engine = ReplayViewerEngine()
    
    # Manually load events since we can't run the full engine loop
    events = []
    with open(replay_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    event = json.loads(line)
                    if event.get('event_type') != 'SIMULATION_START':
                        events.append(event)
                    else:
                         # Initialize config if needed
                         engine.configuracion = event.get('config', {})
                except:
                    continue
    
    engine.eventos = events
    engine.max_time = events[-1].get('timestamp', 0.0) if events else 0.0
    
    # Monkey patch _compute_snapshot_from_events to trace GroundOp-02
    original_compute = engine._compute_snapshot_from_events
    
    def traced_compute(events, target_time):
        print("Starting traced compute...")
        
        # Filter for WO-0052 events
        wo52_events = [e for e in events if e.get('id') == 'WO-0052']
        print(f"Found {len(wo52_events)} events for WO-0052")
        
        prev_agent = None
        for i, e in enumerate(wo52_events):
            agent = e.get('assigned_agent_id')
            if i < 5 or agent != prev_agent:
                print(f"WO-0052 EVENT ({i}): {e}")
            prev_agent = agent

        return original_compute(events, target_time)
    
    engine._compute_snapshot_from_events = traced_compute

    # Initialize state
    engine.initial_estado_visual = {'work_orders': {}, 'operarios': {}, 'metricas': {}}
    
    # Find a time where operators have tours
    target_time = 107.90 # Specific time from previous run
    print(f"Seeking to {target_time:.2f}s...")
    
    # Perform seek
    engine.seek_to_time(target_time)
    
    # Check global state
    print("\n--- Verification Results ---")
    operators = estado_visual.get('operarios', {})
    work_orders = estado_visual.get('work_orders', {})
    
    print(f"Operators found: {len(operators)}")
    print(f"Work Orders found: {len(work_orders)}")
    
    operators_with_tours = 0
    total_assigned_wos = 0
    
    for op_id, op_data in operators.items():
        assigned_wos = op_data.get('work_orders_asignadas', [])
        if assigned_wos:
            operators_with_tours += 1
            total_assigned_wos += len(assigned_wos)
            print(f"Operator {op_id} has {len(assigned_wos)} assigned WOs: {assigned_wos}")
            
            # Verify WOs exist in work_orders dict
            missing_wos = [wo for wo in assigned_wos if wo not in work_orders]
            if missing_wos:
                print(f"  WARNING: WOs missing from main dict: {missing_wos}")
            else:
                print(f"  OK: All assigned WOs exist in main dict.")
        else:
             # Check if they SHOULD have WOs based on current_task
             current_task = op_data.get('current_task')
             if current_task:
                 print(f"Operator {op_id} has current_task {current_task} but NO work_orders_asignadas list.")
    
    if operators_with_tours > 0:
        print("\nSUCCESS: Found operators with reconstructed tours after seek.")
    else:
        print("\nFAILURE: No operators have tours after seek. The bug persists.")

if __name__ == "__main__":
    # Use one of the found replay files
    replay_path = r"c:\Users\ferri\OneDrive\Escritorio\Gemelos Digital\output\simulation_20251013_220606\replay_20251013_220606.jsonl"
    verify_seek_logic(replay_path)
