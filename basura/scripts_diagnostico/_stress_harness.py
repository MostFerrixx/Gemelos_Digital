# -*- coding: utf-8 -*-
"""
Harness de PRUEBA DE ESTRES (Iniciativa #2 / Fase 2).
Reusa EventGenerator.crear_simulacion() pero corre SOLO el loop SimPy
(sin analytics/heatmap, que es lento e irrelevante para el test) y vuelca
el resumen de co-ocupacion del CongestionManager.

Mide: tiempo final de sim, si TERMINO, si hubo FREEZE (cap de wallclock),
y las co-ocupaciones (totales y en ventana de arranque t<=5).

Uso: python3 _stress_harness.py <config.json> [wallclock_cap_seg]
"""
import sys, os, json, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import simpy
from engines.event_generator import EventGenerator

cfg = sys.argv[1]
CAP = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0

gen = EventGenerator(headless_mode=True, config_path=cfg)
if not gen.crear_simulacion():
    print("HARNESS_ERROR: crear_simulacion fallo")
    sys.exit(1)

t0 = time.time()
freeze = False
while not gen.almacen.simulacion_ha_terminado():
    try:
        gen.env.run(until=gen.env.now + 1.0)
    except simpy.core.EmptySchedule:
        break
    if time.time() - t0 > CAP:
        freeze = True
        break

cm = gen.almacen.congestion_manager
resumen = cm.resumen() if cm is not None else {}

# Posiciones iniciales de spawn (para verificar dispersion: ningun par igual)
spawn_positions = {}
collisions_spawn = 0
seen = {}
for op in gen.operarios:
    # tras el run, current_position ya no es la inicial; pero spawn_index sirve para
    # reconstruir el anden esperado. Reportamos solo el conteo de la instrumentacion.
    pass

print("=" * 70)
print("RESULTADO PRUEBA DE ESTRES")
print("=" * 70)
print(f"  Config: {cfg}")
print(f"  Agentes: {len(gen.operarios)}")
print(f"  staggered_start: {gen.almacen.congestion_config.get('staggered_start')}")
print(f"  spawn_offset: {gen.almacen.congestion_config.get('spawn_offset')}")
print(f"  SIM_END_T: {gen.env.now:.2f}")
print(f"  TERMINO: {gen.almacen.simulacion_ha_terminado()}")
print(f"  FREEZE (cap {CAP}s): {freeze}")
print(f"  wallclock_sim: {time.time()-t0:.1f}s")
print("  --- co-ocupacion (instrumentacion) ---")
print(f"  cooccup_total: {resumen.get('cooccupation_events_total')}")
print(f"  cooccup_startup(t<=5): {resumen.get('cooccupation_events_startup_window')}")
print(f"  celdas_distintas: {resumen.get('distinct_cells_with_cooccupation')}")
print(f"  max_concurrent_celda: {resumen.get('max_concurrent_any_cell')}")
print(f"  top_hotspots: {resumen.get('top_hotspots')}")
print("=" * 70)
# JSON para parseo
print("JSON_RESUMEN:" + json.dumps({
    "config": cfg,
    "agents": len(gen.operarios),
    "staggered_start": gen.almacen.congestion_config.get('staggered_start'),
    "sim_end_t": round(gen.env.now, 2),
    "terminated": gen.almacen.simulacion_ha_terminado(),
    "freeze": freeze,
    "cooccup_total": resumen.get('cooccupation_events_total'),
    "cooccup_startup": resumen.get('cooccupation_events_startup_window'),
    "max_concurrent": resumen.get('max_concurrent_any_cell'),
}))
