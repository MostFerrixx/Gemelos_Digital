# -*- coding: utf-8 -*-
"""
Utilidades para el sistema de replay.
Modulo extraido de run_simulator.py para modularizacion incremental.
"""

import json


def build_service_level_summary(almacen):
    """INIT-5: resumen de nivel de servicio (backorders) a partir del resultado de
    validacion del allocation layer. Devuelve un dict serializable (plomeria: NO calcula
    nada nuevo, solo transporta lo que el motor ya calculo en allocation_summary /
    unfilled_demand). En modo estocastico (sin validacion de stock) -> available=False
    (la UI muestra N/A). Fuente unica usada por el .jsonl y por el reporte Excel."""
    vr = None
    try:
        if almacen is not None and hasattr(almacen, 'get_order_validation_result'):
            vr = almacen.get_order_validation_result()
    except Exception:
        vr = None
    if not vr:
        return {
            'available': False,
            'mode': 'stochastic',
            'fill_rate_pct': None,
            'total_requested': 0,
            'total_served': 0,
            'total_unfilled': 0,
            'orders_short': 0,
            'backorder_items': 0,
            'unfilled': [],
        }
    summ = getattr(vr, 'allocation_summary', {}) or {}
    unfilled = list(getattr(vr, 'unfilled_demand', []) or [])
    orders_short = len({u.get('order_id') for u in unfilled if u.get('order_id') is not None})
    out = {
        'available': True,
        'mode': 'deterministic',
        'fill_rate_pct': summ.get('allocation_rate', 100.0),
        'total_requested': summ.get('total_qty_requested', 0),
        'total_served': summ.get('total_qty_allocated', 0),
        'total_unfilled': summ.get('total_qty_unfilled', 0),
        'orders_short': orders_short,
        'backorder_items': summ.get('backorder_items_count', 0),
        'unfilled': unfilled,
    }
    # INIT-7 F5b: el cross-dock rescata backorders DURANTE la corrida con el
    # stock que llego ese dia. fill_rate_pct sigue siendo la foto de la
    # allocation t=0 (contrato historico intacto); fill_rate_effective_pct
    # suma lo rescatado. Las claves solo aparecen si hubo rescates: con
    # cross-dock off la metadata es identica a la historica (gate intacto).
    im = getattr(almacen, 'inbound_metrics', None) or {}
    rescued = im.get('cross_dock_units_rescued', 0)
    if rescued:
        total_req = out['total_requested']
        served_eff = out['total_served'] + rescued
        out['units_rescued_cross_dock'] = rescued
        out['fill_rate_effective_pct'] = (
            round(served_eff / total_req * 100, 1) if total_req else 100.0)
    return out


def build_sla_summary(almacen):
    """INIT-4b: resumen de cumplimiento de SLA (due_time) por pedido, a partir
    de las WorkOrders completadas (dispatcher.work_orders_completados).
    Mismo patron/plomeria que build_service_level_summary: NO calcula SLA
    nuevo, solo agrega lo que ya trae cada WO (due_time viene de INIT-4 C2,
    opt-in). Un pedido cuenta como "a tiempo" si TODAS sus WOs terminaron
    (tiempo_fin) antes o en su due_time -- se usa el MAX tiempo_fin del
    pedido, porque el pedido no esta completo hasta que lo estan todas sus WOs.
    Si ninguna WO completada trae due_time (INIT-4 C2 desactivado, o modo
    Stochastic que no lo asigna), available=False (la UI muestra N/A)."""
    dispatcher = getattr(almacen, 'dispatcher', None)
    completadas = getattr(dispatcher, 'work_orders_completados', None) if dispatcher else None

    orders = {}
    for wo in (completadas or []):
        due = getattr(wo, 'due_time', None)
        if due is None:
            continue
        order_id = getattr(wo, 'order_id', None)
        tiempo_fin = getattr(wo, 'tiempo_fin', None) or 0.0
        entry = orders.setdefault(order_id, {'due_time': due, 'completion_time': tiempo_fin})
        if tiempo_fin > entry['completion_time']:
            entry['completion_time'] = tiempo_fin

    if not orders:
        return {
            'available': False,
            'total_orders_with_sla': 0,
            'orders_on_time': 0,
            'orders_late': 0,
            'on_time_pct': None,
            'late_orders': [],
        }

    late_orders = []
    on_time = 0
    for order_id, data in orders.items():
        if data['completion_time'] <= data['due_time']:
            on_time += 1
        else:
            late_orders.append({
                'order_id': order_id,
                'due_time': data['due_time'],
                'completion_time': data['completion_time'],
                'delay_seconds': data['completion_time'] - data['due_time'],
            })

    total = len(orders)
    return {
        'available': True,
        'total_orders_with_sla': total,
        'orders_on_time': on_time,
        'orders_late': len(late_orders),
        'on_time_pct': round(on_time / total * 100.0, 1) if total else None,
        'late_orders': late_orders,
    }


def build_bottleneck_summary(almacen):
    """MEJ-BOTTLENECK: consolida en UN dict serializable los indicadores de
    cuellos de botella que el motor YA calcula pero quedaban enterrados en
    JSONs sueltos por corrida (congestion_report, timewindow_shadow_report)
    o solo en memoria (outbound_metrics). Misma plomeria que INIT-5/INIT-4b:
    NO calcula nada nuevo, solo transporta. Fuente unica para la metadata del
    .jsonl, la API del visor y la hoja Excel 'Cuellos de Botella'.

    Cada bloque es None si su subsistema no esta activo en la corrida
    (congestion off / outbound off) -- available=False solo si NINGUNO lo esta."""
    congestion = None
    cm = getattr(almacen, 'congestion_manager', None)
    if cm is not None and getattr(cm, 'active', False):
        try:
            s = cm.resumen()
            congestion = {
                'cooccupation_events_total': s.get('cooccupation_events_total', 0),
                'distinct_cells_with_cooccupation': s.get('distinct_cells_with_cooccupation', 0),
                'max_concurrent_any_cell': s.get('max_concurrent_any_cell', 0),
                'top_hotspots': (s.get('top_hotspots') or [])[:8],
            }
        except Exception:
            congestion = None

    planner = None
    sp = getattr(almacen, 'spacetime_planner', None)
    if sp is not None and hasattr(sp, 'shadow_report'):
        try:
            rep = sp.shadow_report()
            # OJO: NO incluir avg_plan_ms/max_plan_ms aca -- son WALL-CLOCK
            # (time.perf_counter), varian entre corridas identicas y romperian
            # el gate byte-identico del .jsonl. El coste de CPU del planner
            # sigue disponible en timewindow_shadow_report_*.json (no hasheado).
            planner = {
                'segments_planned': rep.get('segments_planned', 0),
                'plans_found': rep.get('plans_found', 0),
                'plans_failed': rep.get('plans_failed', 0),
                'avg_waits_per_plan': rep.get('avg_waits_per_plan'),
                'table_overlap_violations': rep.get('table_overlap_violations', 0),
            }
        except Exception:
            planner = None

    outbound = None
    om = getattr(almacen, 'outbound_metrics', None)
    if om:
        outbound = {
            'pallets_staged': om.get('pallets_staged', 0),
            'pallets_shipped': om.get('pallets_shipped', 0),
            'slot_wait_events': om.get('slot_wait_events', 0),
            'slot_wait_time': om.get('slot_wait_time', 0.0),
            'max_slot_wait': om.get('max_slot_wait', 0.0),
            'lane_full_wait_events': om.get('lane_full_wait_events', 0),
            'lane_full_wait_time': om.get('lane_full_wait_time', 0.0),
            # {staging_id: ocupacion pico} -- claves a str para JSON estable
            'peak_occupancy': {str(k): v for k, v in (om.get('peak_occupancy') or {}).items()},
        }

    return {
        'available': any(b is not None for b in (congestion, planner, outbound)),
        'congestion': congestion,
        'planner': planner,
        'outbound': outbound,
    }


def build_inbound_summary(almacen):
    """INIT-7 F4: consolida en UN dict serializable los KPIs de recepcion /
    putaway que el motor YA acumula en almacen.inbound_metrics durante la
    corrida. Misma plomeria que build_bottleneck_summary: NO calcula nada
    nuevo, solo transporta y deriva promedios. Fuente unica para la metadata
    del .jsonl, la API del visor y la hoja Excel 'Inbound'.

    available=False si inbound no corrio en esta simulacion.

    REGLA BN-05: todo lo que entra aca es tiempo de SIMULACION (dock_to_stock
    = env.now - t_unloaded) o distancia de grilla -- ambos DETERMINISTAS. NADA
    wall-clock (rompe el gate byte-identico del .jsonl)."""
    im = getattr(almacen, 'inbound_metrics', None)
    if not im:
        return {'available': False}

    stored = im.get('pallets_stored', 0)
    d2s_total = im.get('dock_to_stock_total', 0.0)
    dist_total = im.get('putaway_distance_total', 0.0)
    avg_d2s = round(d2s_total / stored, 2) if stored else None
    avg_dist = round(dist_total / stored, 2) if stored else None
    # F5a: contencion cruzada (pallet listo esperando que un agente lo tome).
    waits = im.get('putaway_wait_events', 0)
    avg_wait = (round(im.get('putaway_wait_total', 0.0) / waits, 2)
                if waits else None)

    return {
        'available': True,
        # F5a: quien manda en la flota compartida (picks_first | putaway_first)
        'putaway_priority': getattr(
            getattr(almacen, 'dispatcher', None), 'putaway_priority',
            'picks_first'),
        # F5a: espera del pallet listo -> asignacion (la contencion cruzada).
        'avg_putaway_wait': avg_wait,
        'max_putaway_wait': round(im.get('max_putaway_wait', 0.0), 2),
        # F5b: cross-docking (0/False si apagado).
        'cross_dock_enabled': bool(getattr(almacen, 'cross_dock_enabled', False)),
        'cross_dock_picks_created': im.get('cross_dock_picks_created', 0),
        'cross_dock_units_rescued': im.get('cross_dock_units_rescued', 0),
        # estrategia de esta corrida: la clave que el A/B compara entre A y B.
        'slotting_strategy': getattr(almacen, 'inbound_slotting', 'fija_por_sku'),
        'docks_count': len(getattr(almacen, 'inbound_docks', {}) or {}),
        'trucks_received': im.get('trucks_received', 0),
        'pallets_unloaded': im.get('pallets_unloaded', 0),
        'pallets_stored': stored,
        'units_received': im.get('units_received', 0),
        # dock-to-stock: cuanto tarda un pallet de bajar del camion a quedar
        # guardado (segundos de simulacion).
        'avg_dock_to_stock': avg_d2s,
        'max_dock_to_stock': round(im.get('max_dock_to_stock', 0.0), 2),
        # distancia de guardado (celdas): la palanca directa del slotting.
        'avg_putaway_distance': avg_dist,
        'max_putaway_distance': round(im.get('max_putaway_distance', 0.0), 2),
        'putaway_distance_total': round(dist_total, 2),
        # contencion de muelles.
        'dock_wait_events': im.get('dock_wait_events', 0),
        'dock_wait_time': round(im.get('dock_wait_time', 0.0), 2),
        'max_dock_wait': round(im.get('max_dock_wait', 0.0), 2),
        'buffer_peak': im.get('buffer_peak', 0),
    }


def agregar_evento_replay(buffer, evento):
    """Agrega un evento al bufer de replay"""
    buffer.add_event(evento)


def volcar_replay_a_archivo(buffer, archivo_salida, configuracion, almacen=None, initial_work_orders_snapshot=None):
    """Vuelca el bufer completo a un archivo .jsonl"""

    # REFACTOR: Usar la instancia de ReplayBuffer recibida como parametro
    eventos_a_volcar = buffer.get_events()
    print(f"[VOLCADO-REFACTOR] Usando ReplayBuffer con {len(eventos_a_volcar)} eventos")

    # Contar eventos para volcado (logging minimo)
    wo_events = [e for e in eventos_a_volcar if e.get('type') == 'work_order_update']
    estado_events = [e for e in eventos_a_volcar if e.get('type') == 'estado_agente']
    print(f"[REPLAY-EXPORT] Volcando {len(wo_events)} work_order_update + {len(estado_events)} estado_agente de {len(eventos_a_volcar)} total")

    # ELIMINADO: Sistema de respaldo artificial que causaba replay erratico
    # Los eventos reales del headless son de alta fidelidad y ya no necesitan respaldo sintetico

    try:
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            # Escribir metadata de la simulacion primero
            metadata = {
                'event_type': 'SIMULATION_START',
                'timestamp': 0,
                'config': configuracion,
                'total_events_captured': len(eventos_a_volcar)
            }

            # BUGFIX: Anadir total de WorkOrders al evento SIMULATION_START
            if almacen and hasattr(almacen, 'dispatcher') and hasattr(almacen.dispatcher, 'work_orders_total_inicial'):
                total_work_orders = almacen.dispatcher.work_orders_total_inicial
                metadata['total_work_orders'] = total_work_orders
                print(f"[REPLAY-METADATA] Anadido total_work_orders: {total_work_orders} al evento SIMULATION_START")
            else:
                print(f"[REPLAY-METADATA] WARNING: No se pudo obtener total de WorkOrders del almacen")

            # REFACTOR: Usar instantanea capturada en t=0 en lugar de estado al final
            if initial_work_orders_snapshot and len(initial_work_orders_snapshot) > 0:
                metadata['initial_work_orders'] = initial_work_orders_snapshot
                print(f"[REPLAY-METADATA] Anadidas {len(initial_work_orders_snapshot)} initial_work_orders desde instantanea t=0")
            else:
                print(f"[REPLAY-METADATA] WARNING: No se recibio instantanea inicial de WorkOrders")

            # INIT-5: resumen de nivel de servicio (backorders) en la metadata del replay.
            service = build_service_level_summary(almacen)
            metadata['service_level'] = service
            if service.get('available'):
                print(f"[REPLAY-METADATA] Nivel de servicio: {service['fill_rate_pct']}% "
                      f"(deuda {service['total_unfilled']} u / {service['orders_short']} pedidos)")

            # INIT-4b: resumen de cumplimiento de SLA (due_time) en la metadata del replay.
            sla = build_sla_summary(almacen)
            metadata['sla_summary'] = sla
            if sla.get('available'):
                print(f"[REPLAY-METADATA] SLA: {sla['on_time_pct']}% a tiempo "
                      f"({sla['orders_late']} de {sla['total_orders_with_sla']} pedidos vencidos)")

            # MEJ-BOTTLENECK: resumen de cuellos de botella en la metadata del replay.
            bottleneck = build_bottleneck_summary(almacen)
            metadata['bottleneck_summary'] = bottleneck
            if bottleneck.get('available') and bottleneck.get('congestion'):
                c = bottleneck['congestion']
                print(f"[REPLAY-METADATA] Cuellos de botella: {c['cooccupation_events_total']} "
                      f"co-ocupaciones en {c['distinct_cells_with_cooccupation']} celdas")

            # INIT-7 F4: resumen de recepcion/putaway (inbound) en la metadata.
            inbound = build_inbound_summary(almacen)
            metadata['inbound_summary'] = inbound
            if inbound.get('available'):
                print(f"[REPLAY-METADATA] Inbound ({inbound['slotting_strategy']}): "
                      f"{inbound['pallets_stored']} pallets guardados, "
                      f"dock-to-stock avg {inbound['avg_dock_to_stock']}s, "
                      f"distancia putaway avg {inbound['avg_putaway_distance']} celdas")

            f.write(json.dumps(metadata, ensure_ascii=False) + '\n')

            # Escribir todos los eventos
            for evento in eventos_a_volcar:
                f.write(json.dumps(evento, ensure_ascii=False) + '\n')

            # Escribir evento final
            final_event = {
                'event_type': 'SIMULATION_END',
                'timestamp': eventos_a_volcar[-1]['timestamp'] if eventos_a_volcar else 0
            }
            f.write(json.dumps(final_event, ensure_ascii=False) + '\n')

        print(f"[REPLAY-BUFFER] {len(eventos_a_volcar)} eventos guardados en {archivo_salida}")
        return True

    except Exception as e:
        print(f"[REPLAY-BUFFER] ERROR al escribir archivo: {e}")
        return False