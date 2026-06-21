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
    return {
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