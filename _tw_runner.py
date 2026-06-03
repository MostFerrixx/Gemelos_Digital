# -*- coding: utf-8 -*-
"""
Runner minimo para VALIDACION de Opcion C (Iniciativa #2). NO es codigo de produccion.
Hace crear_simulacion() + el lazo SimPy + volcar_replay_a_archivo() (SIN analytics,
que es lento e irrelevante para la no-regresion del .jsonl). Determinista.

Uso: python3 _tw_runner.py <config.json> <salida.jsonl> [wallclock_cap]
"""
import sys, os, time
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import simpy
from engines.event_generator import EventGenerator
from core.replay_utils import volcar_replay_a_archivo

cfg = sys.argv[1]
out = sys.argv[2]
CAP = float(sys.argv[3]) if len(sys.argv) > 3 else 300.0

gen = EventGenerator(headless_mode=True, config_path=cfg)
if not gen.crear_simulacion():
    print("RUNNER_ERROR: crear_simulacion fallo"); sys.exit(1)

t0 = time.time(); freeze = False
while not gen.almacen.simulacion_ha_terminado():
    try:
        gen.env.run(until=gen.env.now + 1.0)
    except simpy.core.EmptySchedule:
        break
    if time.time() - t0 > CAP:
        freeze = True; break

snap = getattr(gen.almacen.dispatcher, 'initial_work_orders_snapshot', [])
volcar_replay_a_archivo(gen.replay_buffer, out, gen.configuracion, gen.almacen, snap)

print(f"RUNNER_DONE cfg={cfg} out={out} sim_end_t={gen.env.now:.2f} "
      f"terminated={gen.almacen.simulacion_ha_terminado()} freeze={freeze} "
      f"events={len(gen.replay_buffer)} wall={time.time()-t0:.1f}s")

# Reporte de planner en sombra (Opcion C), si existe.
planner = getattr(gen.almacen, 'spacetime_planner', None)
table = getattr(gen.almacen, 'reservation_table', None)
if planner is not None and hasattr(planner, 'shadow_report'):
    import json as _json
    print("SHADOW_REPORT:" + _json.dumps(planner.shadow_report()))
if table is not None:
    print(f"SHADOW_TABLE reserve_calls={getattr(table,'reserve_calls',None)} "
          f"overlap_violations={getattr(table,'overlap_violations',None)} "
          f"cells={len(getattr(table,'reservations',{}))}")
