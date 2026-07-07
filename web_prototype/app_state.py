# -*- coding: utf-8 -*-
"""
Estado compartido del servidor web (REFACTOR 2026-07-07: extraido del
monolito server.py, ver docs/CHANGELOG.md). Aca viven las instancias unicas
que comparten los routers: config_manager y replay_data (+ constantes de
paths). Los endpoints viven en web_prototype/routers/.
"""
import json
import os

from web_prototype.config_manager import WebConfigurationManager

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
config_manager = WebConfigurationManager(PROJECT_ROOT)

# Ruta historica del TMX (arbol data/ muerto); solo queda como candidato de
# compatibilidad en la cadena de fallbacks de /api/layout.
TMX_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "layouts", "layout_v2.tmx"))

# REFACTOR 2026-07-07 (arranque limpio): antes apuntaba hardcodeado a un
# replay de nov-2025 inexistente -> cada arranque imprimia un error y quedaba
# vacio "por accidente". Ahora arranca vacio A PROPOSITO; se setea al cargar
# un replay (Importar en el visor o POST /api/load_replay).
REPLAY_FILE = None

class ReplayData:
    def __init__(self):
        self.events = []
        self.max_time = 0
        self.snapshots = {}  # {timestamp: state_dict}
        self.snapshot_interval = 60.0  # Create a snapshot every 60 seconds
        self.service_level = None  # INIT-5: resumen de nivel de servicio (backorders)
        self.sla_summary = None  # INIT-4b: resumen de cumplimiento de SLA (due_time)
        self.bottleneck_summary = None  # MEJ-BOTTLENECK: cuellos de botella de la corrida
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

        # F2.c: handlers de eventos de camion (outbound). Acumulan contadores en
        # state['outbound'] para que los snapshots y /api/snapshot los expongan.
        # Con outbound.enabled=false nunca se emiten estos tipos -> contadores = 0.
        elif etype == 'truck_arrived':
            ob = state.setdefault('outbound', {
                'trucks_dispatched': 0, 'pallets_shipped': 0, 'backlog': 0})
            ob['last_truck_id'] = event.get('truck_id')

        elif etype == 'truck_departed':
            ob = state.setdefault('outbound', {
                'trucks_dispatched': 0, 'pallets_shipped': 0, 'backlog': 0})
            if event.get('pallets_loaded', 0) > 0:
                ob['trucks_dispatched'] = ob.get('trucks_dispatched', 0) + 1
            ob['backlog'] = event.get('backlog', 0)

        elif etype == 'pallet_shipped':
            ob = state.setdefault('outbound', {
                'trucks_dispatched': 0, 'pallets_shipped': 0, 'backlog': 0})
            ob['pallets_shipped'] = ob.get('pallets_shipped', 0) + 1

    def load_data(self):
        if not REPLAY_FILE:
            print("[REPLAY] Arranque sin replay cargado (usa Importar en el visor "
                  "o POST /api/load_replay).")
            return
        print(f"Loading replay data from {REPLAY_FILE}...")
        try:
            self.events = []
            self.service_level = None
            self.sla_summary = None
            self.bottleneck_summary = None
            with open(REPLAY_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        
                        # Handle SIMULATION_START to extract initial WOs
                        if event.get('type') == 'SIMULATION_START' or event.get('event_type') == 'SIMULATION_START':
                            # INIT-5: resumen de nivel de servicio (backorders) desde la metadata.
                            self.service_level = event.get('service_level')
                            # INIT-4b: resumen de cumplimiento de SLA desde la metadata.
                            self.sla_summary = event.get('sla_summary')
                            # MEJ-BOTTLENECK: cuellos de botella desde la metadata.
                            self.bottleneck_summary = event.get('bottleneck_summary')
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

    def reload_data(self, new_file_path: str):
        """
        Reload replay data from a new JSONL file.
        Clears existing events and snapshots, then loads new data.
        """
        print(f"Reloading data from {new_file_path}...")
        
        # Clear existing data
        self.events = []
        self.snapshots = {}
        self.max_time = 0
        
        # Update file path
        global REPLAY_FILE
        REPLAY_FILE = new_file_path
        
        # Load new data
        self.load_data()
        self.precompute_snapshots()
        
        print(f"Reload complete. Loaded {len(self.events)} events, max time: {self.max_time}")

replay_data = ReplayData()
