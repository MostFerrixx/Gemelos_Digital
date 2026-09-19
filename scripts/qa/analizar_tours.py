# -*- coding: utf-8 -*-
"""
Verificacion del despacho (plan de QA, bloque 2).

Reconstruye cada recorrido (tour) de una corrida y verifica la regla con la que
se eligio su tarea ANCLA segun la estrategia configurada:

  * Ejecucion de Plan: el tour contiene la tarea pendiente de MENOR
    pick_sequence del area de la tarea ancla.
  * Optimizacion Global: el tour contiene la tarea pendiente MAS CERCANA (por
    camino real, con el mismo buscador de rutas del motor) del area.
  * Cercania: distancia en linea recta del operario a la tarea mas cercana
    del tour (para comparar contra el radio configurado).

Tambien informa cuantas zonas de descarga mezcla cada tour (Tour Simple vs
Mixto) y la distancia media al primer pick.

Uso: python scripts/qa/analizar_tours.py <replay.jsonl | carpeta> [--json salida]
"""
import argparse
import collections
import contextlib
import io
import json
import math
import os
import statistics
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(RAIZ, 'src'))
import analizar_replay as ar  # noqa: E402


def buscador_de_rutas(config):
    from subsystems.simulation.layout_manager import LayoutManager
    from subsystems.simulation.pathfinder import Pathfinder
    lm = LayoutManager(os.path.join(RAIZ, config.get('layout_file', 'layouts/WH1.tmx')),
                       headless=True)
    return Pathfinder(lm.collision_matrix)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('replay')
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    meta, eventos = ar.cargar(args.replay)
    config = meta.get('config', {})
    estrategia = config.get('dispatch_strategy')
    wo = {w['id']: dict(w) for w in meta.get('initial_work_orders', [])}

    asignada = {}                      # wo -> t de asignacion
    staging = {}
    tours = collections.defaultdict(list)
    for e in eventos:
        if ar.tipo_de(e) != 'work_order_update':
            continue
        staging[e['id']] = e.get('staging')
        if e.get('status') == 'assigned' and e['id'] not in asignada:
            asignada[e['id']] = e['timestamp']
            tours[(e.get('assigned_agent_id'), e['timestamp'])].append(e['id'])
            wo.setdefault(e['id'], {'id': e['id'], 'ubicacion': e.get('location'),
                                    'work_area': e.get('work_area'),
                                    'pick_sequence': e.get('pick_sequence')})

    pick_t = {}
    for e in eventos:
        if ar.tipo_de(e) == 'operation_completed':
            pick_t.setdefault(e['data'].get('work_order_id'), e['timestamp'])

    linea = ar.linea_de_tiempo(eventos)
    with contextlib.redirect_stdout(io.StringIO()):
        pf = buscador_de_rutas(config)
    cache = {}

    def camino(a, b):
        clave = (tuple(a), tuple(b))
        if clave not in cache:
            with contextlib.redirect_stdout(io.StringIO()):
                p = pf.find_path(tuple(a), tuple(b))
            cache[clave] = float(len(p)) if p else float('inf')
        return cache[clave]

    filas = []
    for (agente_evt, t), ids in sorted(tours.items(), key=lambda kv: kv[0][1]):
        agente = agente_evt.split('_', 1)[-1] if agente_evt else agente_evt
        pos = ar.posicion_al_pedir(linea, agente, t)
        if pos is None:
            continue
        primera = min(ids, key=lambda w: pick_t.get(w, float('inf')))
        area = wo[primera].get('work_area')
        pendientes = [w for w, ta in asignada.items()
                      if ta >= t and wo.get(w, {}).get('work_area') == area]
        min_seq = min(wo[w]['pick_sequence'] for w in pendientes)
        seq_ok = any(wo[w]['pick_sequence'] == min_seq for w in ids)
        d_tour = min(camino(pos, wo[w]['ubicacion']) for w in ids)
        d_min = min(camino(pos, wo[w]['ubicacion']) for w in pendientes)
        eu_tour = min(math.dist(pos, wo[w]['ubicacion']) for w in ids)
        filas.append({
            'agente': agente, 't': round(t, 2), 'n_wos': len(ids), 'area': area,
            'contiene_menor_secuencia': seq_ok,
            'contiene_mas_cercana': d_tour <= d_min + 1e-9,
            'camino_a_la_mas_cercana_del_tour': d_tour,
            'camino_minimo_posible': d_min,
            'linea_recta_a_la_mas_cercana_del_tour': round(eu_tour, 2),
            'zonas': len({staging.get(w) for w in ids}),
        })

    n = len(filas) or 1
    resumen = {
        'estrategia': estrategia,
        'tour_type': config.get('tour_type'),
        'radio': [config.get('radio_cercania'), config.get('radio_expansion_paso'),
                  config.get('radio_max_expansiones')],
        'tours': len(filas),
        'pct_contiene_menor_secuencia': round(100 * sum(f['contiene_menor_secuencia'] for f in filas) / n, 1),
        'pct_contiene_mas_cercana': round(100 * sum(f['contiene_mas_cercana'] for f in filas) / n, 1),
        'camino_medio_a_la_mas_cercana_del_tour': round(statistics.mean(
            f['camino_a_la_mas_cercana_del_tour'] for f in filas), 2) if filas else None,
        'linea_recta_max': max((f['linea_recta_a_la_mas_cercana_del_tour'] for f in filas), default=None),
        'tours_con_mas_de_una_zona': sum(1 for f in filas if f['zonas'] > 1),
        'wos_por_tour_medio': round(statistics.mean(f['n_wos'] for f in filas), 2) if filas else None,
    }
    salida = {'resumen': resumen, 'tours': filas}
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(salida, f, indent=1)
    print(json.dumps(resumen, indent=1))


if __name__ == '__main__':
    sys.exit(main())
