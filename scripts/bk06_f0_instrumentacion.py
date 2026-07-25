# -*- coding: utf-8 -*-
"""
BK-06 / F0 -- Instrumentacion pura (NO cambia el comportamiento del motor).

Objetivo: cuantificar el upside del fix ANTES de tocar la logica.

Monta la simulacion canonica con el MISMO setup que el headless
(EventGenerator.crear_simulacion) pero NO la ejecuta: solo inspecciona las
WorkOrders ya generadas y la flota instanciada, y responde:

  1. Que capacidad usa HOY el dimensionado de WOs por area (la via ciega).
  2. Que capacidad CORRESPONDERIA segun work_area_equipment + la flota real.
  3. Cuantas WOs se generarian con la capacidad correcta (upside en WOs/viajes).
  4. Cuantas de esas WOs serian irrecogibles por un agente del tipo equivocado
     (el riesgo que hay que neutralizar en F1 con el filtro por el mapa).

Uso:
    python scripts/bk06_f0_instrumentacion.py

Salida: tabla ASCII por consola. No escribe nada en el repo.
Ver docs/PLAN_BK06_CAPACIDAD_AREA.md
"""

import os
import sys
import io
import math
import contextlib
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# El motor usa imports tipo `subsystems.simulation...` => src/ debe estar en
# el path (mismo criterio que entry_points/run_generate_replay.py).
for _p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Determinismo: mismo seed que el gate.
os.environ.setdefault("WAREHOUSE_SEED", "42")


def _expected_equipment_for_area(configuracion, area):
    """Replica exacta de event_generator._expected_equipment_for_area (QA-3
    Opcion B). Se duplica a proposito: F0 NO debe importar logica nueva ni
    modificar el motor. En F1 esto pasa a ser un helper unico compartido."""
    wae = (configuracion or {}).get('work_area_equipment', {})
    if isinstance(wae, dict):
        t = wae.get(area)
        if t:
            return t
    import re
    if re.search(r'ground|piso|floor|suelo|terrestre|level[_-]?0|l0', str(area), re.I):
        return 'GroundOperator'
    return 'Forklift'


def _wos_necesarias(volumen_unidad, cantidad, capacidad):
    """Cuantas WOs hacen falta para mover `cantidad` unidades de un SKU dado
    un limite de capacidad. Replica la intencion de
    warehouse._validar_y_ajustar_cantidad (division por viajes)."""
    if volumen_unidad <= 0:
        return 1
    if volumen_unidad > capacidad:
        return 0  # irrecogible: se descarta (backorder implicito)
    unidades_por_viaje = int(capacidad // volumen_unidad)
    if unidades_por_viaje <= 0:
        return 0
    return int(math.ceil(cantidad / unidades_por_viaje))


def main():
    from src.engines.event_generator import EventGenerator

    print("=" * 78)
    print("BK-06 / F0 -- INSTRUMENTACION (canonico, WAREHOUSE_SEED=%s)"
          % os.environ.get("WAREHOUSE_SEED"))
    print("=" * 78)

    # El setup del motor es ruidoso; lo silenciamos para que la tabla se lea.
    gen = EventGenerator(headless_mode=True)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = gen.crear_simulacion()
    if not ok:
        print("[ERROR] crear_simulacion() devolvio False. Abortado.")
        return 1

    setup_log = buf.getvalue()
    almacen = gen.almacen
    config = gen.configuracion
    wos = list(almacen.dispatcher.lista_maestra_work_orders)
    operarios = gen.operarios

    # ---------------------------------------------------------------- FLOTA
    print("\n--- FLOTA INSTANCIADA (capacidad fisica real) ---")
    cap_por_tipo = {}
    conteo_tipo = defaultdict(int)
    for op in operarios:
        cap_por_tipo[op.type] = op.capacity
        conteo_tipo[op.type] += 1
    for tipo, n in sorted(conteo_tipo.items()):
        print("  %-16s x%d  capacidad=%s" % (tipo, n, cap_por_tipo[tipo]))

    # ------------------------------------------------- CAPACIDAD: HOY vs REAL
    print("\n--- CAPACIDAD DE DIMENSIONADO POR AREA ---")
    print("  operator_capacities (derivado de agent_types) = %s"
          % almacen.operator_capacities)
    print("  max_operator_capacity (fallback global)       = %s"
          % almacen.max_operator_capacity)

    areas = sorted({wo.work_area for wo in wos})
    cap_hoy = {}
    cap_correcta = {}
    equipo_area = {}
    for area in areas:
        cap_hoy[area] = almacen.operator_capacities.get(
            area, almacen.max_operator_capacity)
        tipo = _expected_equipment_for_area(config, area)
        equipo_area[area] = tipo
        cap_correcta[area] = cap_por_tipo.get(tipo, cap_hoy[area])

    print("")
    print("  %-14s %-16s %12s %12s %10s" % (
        "AREA", "EQUIPO (mapa)", "CAP HOY", "CAP REAL", "FACTOR"))
    print("  " + "-" * 68)
    for area in areas:
        factor = (cap_correcta[area] / cap_hoy[area]) if cap_hoy[area] else 0
        print("  %-14s %-16s %12s %12s %9.1fx" % (
            area, equipo_area[area], cap_hoy[area], cap_correcta[area], factor))

    # ------------------------------------------------ WOs ACTUALES POR AREA
    print("\n--- WORKORDERS GENERADAS HOY (canonico) ---")
    wos_por_area = defaultdict(int)
    vol_por_area = defaultdict(float)
    for wo in wos:
        vol = (wo.sku.volumen if wo.sku else 0) * wo.cantidad_inicial
        wos_por_area[wo.work_area] += 1
        vol_por_area[wo.work_area] += vol
    print("  %-14s %10s %14s" % ("AREA", "WOs", "VOLUMEN"))
    print("  " + "-" * 42)
    for area in areas:
        print("  %-14s %10d %14.1f" % (area, wos_por_area[area], vol_por_area[area]))
    print("  %-14s %10d %14.1f" % ("TOTAL", len(wos), sum(vol_por_area.values())))

    # ------------------------------------- RE-DIMENSIONADO CON CAP CORRECTA
    # Reconstruimos la demanda original agrupando las WOs que fueron divididas
    # (misma orden + mismo SKU + misma area) y recalculamos cuantas WOs
    # harian falta con la capacidad que corresponde al equipo del area.
    demanda = defaultdict(lambda: {"cantidad": 0, "volumen_unidad": 0.0})
    for wo in wos:
        clave = (wo.order_id, wo.sku.id if wo.sku else "N/A", wo.work_area)
        demanda[clave]["cantidad"] += wo.cantidad_inicial
        demanda[clave]["volumen_unidad"] = wo.sku.volumen if wo.sku else 0

    wos_hoy_recalc = defaultdict(int)
    wos_fix = defaultdict(int)
    irrecogibles_por_ground = 0
    vol_max_por_area = defaultdict(float)

    for (order_id, sku_id, area), d in demanda.items():
        cant = d["cantidad"]
        vol_u = d["volumen_unidad"]
        wos_hoy_recalc[area] += _wos_necesarias(vol_u, cant, cap_hoy[area])
        n_fix = _wos_necesarias(vol_u, cant, cap_correcta[area])
        wos_fix[area] += n_fix
        # Volumen de la WO mas grande que existiria tras el fix
        if n_fix > 0:
            unidades_por_viaje = int(cap_correcta[area] // vol_u) if vol_u > 0 else cant
            vol_wo = min(cant, unidades_por_viaje) * vol_u
            vol_max_por_area[area] = max(vol_max_por_area[area], vol_wo)
            # Riesgo: WO que un GroundOperator (cap 150) no podria levantar
            cap_ground = cap_por_tipo.get("GroundOperator", 150)
            if vol_wo > cap_ground:
                irrecogibles_por_ground += n_fix

    print("\n--- UPSIDE ESTIMADO (re-dimensionado con la capacidad correcta) ---")
    print("  %-14s %12s %12s %12s" % ("AREA", "WOs HOY", "WOs FIX", "DELTA"))
    print("  " + "-" * 54)
    tot_hoy = tot_fix = 0
    for area in areas:
        h, f = wos_hoy_recalc[area], wos_fix[area]
        tot_hoy += h
        tot_fix += f
        print("  %-14s %12d %12d %12d" % (area, h, f, f - h))
    print("  %-14s %12d %12d %12d" % ("TOTAL", tot_hoy, tot_fix, tot_fix - tot_hoy))
    if tot_hoy:
        print("\n  Reduccion de WorkOrders: %.1f%% (%d -> %d)"
              % (100.0 * (tot_hoy - tot_fix) / tot_hoy, tot_hoy, tot_fix))

    # ------------------------------------------------------------- RIESGOS
    print("\n--- RIESGO A NEUTRALIZAR EN F1 ---")
    print("  WO mas grande por area tras el fix:")
    for area in areas:
        print("    %-14s volumen_max=%.1f (equipo=%s)"
              % (area, vol_max_por_area[area], equipo_area[area]))
    cap_ground = cap_por_tipo.get("GroundOperator", 150)
    print("  WOs que un GroundOperator (cap %s) NO podria levantar: %d"
          % (cap_ground, irrecogibles_por_ground))
    print("  -> Estas son las que hoy generan el bucle de [DISPATCHER ERROR].")
    print("     F1 debe impedir que se le ofrezcan (filtro por work_area_equipment).")

    # ------------------------------------------------- CHEQUEO DE COHERENCIA
    print("\n--- COHERENCIA work_area_equipment vs work_area_priorities ---")
    for op in operarios:
        incoherentes = []
        for area in op.work_area_priorities.keys():
            if area in equipo_area and equipo_area[area] != op.type:
                incoherentes.append("%s(->%s)" % (area, equipo_area[area]))
        if incoherentes:
            print("  [WARN] %-14s (%s) se declara apto para: %s"
                  % (op.id, op.type, ", ".join(incoherentes)))
    print("  -> Cada [WARN] es una via por la que el motor puede asignar mal.")

    divididas = [l for l in setup_log.splitlines() if "WO DIVIDIDA" in l]
    print("\n--- CONTROL ---")
    print("  Lineas 'WO DIVIDIDA' en el setup: %d" % len(divididas))
    print("  WorkOrders totales generadas:     %d" % len(wos))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
