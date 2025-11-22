import json
import os

REPLAY_FILE = os.path.abspath(os.path.join("output", "simulation_20251120_224852", "replay_20251120_224852.jsonl"))

class ReplayData:
    def __init__(self):
        self.events = []
        self.max_time = 0
        self.load_data()

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
                        
                        if event.get('type') == 'SIMULATION_START' or event.get('event_type') == 'SIMULATION_START':
                            # Extract initial WOs directly from event
                            initial_wos = event.get('initial_work_orders', [])
                            print(f"Found {len(initial_wos)} initial WOs in SIMULATION_START")
                            
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
            
            self.events.sort(key=lambda x: x.get('timestamp', 0))
            
            if self.events:
                self.max_time = self.events[-1].get('timestamp', 0)
            print(f"Loaded {len(self.events)} events. Max time: {self.max_time}")
            
            # Check metrics at t=0
            self.check_metrics(0)
            
        except Exception as e:
            print(f"Error loading replay data: {e}")
            import traceback
            traceback.print_exc()

    def check_metrics(self, t):
        current_state = {"work_orders": {}}
        relevant_events = [e for e in self.events if e.get('timestamp', 0) <= t]
        
        for event in relevant_events:
            etype = event.get('event_type') or event.get('tipo') or event.get('type')
            data = event.get('data', {})
            
            if etype == 'work_order_update':
                wo_id = data.get('id') or event.get('id')
                if wo_id:
                    current_state['work_orders'][wo_id] = event if not data else data
        
        work_orders = current_state['work_orders']
        released_count = sum(1 for wo in work_orders.values() if wo.get('status') == 'released')
        print(f"At t={t}: Total WOs: {len(work_orders)}, Released: {released_count}")

replay = ReplayData()
