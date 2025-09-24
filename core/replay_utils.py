# -*- coding: utf-8 -*-
"""
Utilidades para el sistema de replay.
Modulo extraido de run_simulator.py para modularizacion incremental.
"""

import json


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