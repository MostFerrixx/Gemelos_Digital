import json
import os

REPLAY_FILE = os.path.abspath(os.path.join("output", "simulation_20251120_224852", "replay_20251120_224852.jsonl"))

with open(REPLAY_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        event = json.loads(line)
        if event.get('type') == 'SIMULATION_START' or event.get('event_type') == 'SIMULATION_START':
            print("Event keys:", event.keys())
            if 'data' in event:
                print("Data keys:", event['data'].keys())
                if 'work_orders' in event['data']:
                    wos = event['data']['work_orders']
                    print(f"Type of work_orders: {type(wos)}")
                    print(f"Length of work_orders: {len(wos)}")
            break
