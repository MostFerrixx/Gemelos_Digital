# -*- coding: utf-8 -*-
"""
Verificacion de la estrategia Cercania (plan de QA, bloque 2).

Para cada recorrido: desde la posicion donde el operario PIDIO trabajo, busca
el primer escalon de radio (radio, radio+paso, ... hasta max_expansiones) con
alguna tarea pendiente compatible (linea recta, igual que el motor). Si existe,
el recorrido debe contener una tarea dentro de ese escalon; si no existe
ninguno, el motor cae al almacen completo (correcto).

Uso: python scripts/qa/verificar_radio.py <replay | carpeta>
"""
import collections
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analizar_replay as ar  # noqa: E402


def main():
    meta, ev = ar.cargar(sys.argv[1])
    cfg = meta['config']
    r0 = float(cfg.get('radio_cercania', 100))
    paso = float(cfg.get('radio_expansion_paso', 50))
    n_exp = int(cfg.get('radio_max_expansiones', 5))
    escalones = [r0 + i * paso for i in range(n_exp + 1)]
    wo = {w['id']: w for w in meta['initial_work_orders']}
    asignada, tours = {}, collections.defaultdict(list)
    areas = collections.defaultdict(set)
    for e in ev:
        if ar.tipo_de(e) == 'work_order_update' and e.get('status') == 'assigned' \
                and e['id'] not in asignada:
            agente = e['assigned_agent_id'].split('_', 1)[-1]
            asignada[e['id']] = e['timestamp']
            tours[(agente, e['timestamp'])].append(e['id'])
            areas[agente].add(wo[e['id']]['work_area'])
    linea = ar.linea_de_tiempo(ev)
    por_escalon = collections.Counter()
    violaciones = []
    for (agente, t), ids in sorted(tours.items(), key=lambda kv: kv[0][1]):
        pos = ar.posicion_al_pedir(linea, agente, t)
        pend = [w for w, ta in asignada.items() if ta >= t and wo[w]['work_area'] in areas[agente]]
        d_pend = min(math.dist(pos, wo[w]['ubicacion']) for w in pend)
        d_tour = min(math.dist(pos, wo[w]['ubicacion']) for w in ids)
        escalon = next((r for r in escalones if d_pend <= r), None)
        por_escalon[escalon if escalon is not None else 'almacen'] += 1
        if escalon is not None and d_tour > escalon:
            violaciones.append((agente, round(t, 1), pos, escalon, round(d_tour, 2)))
    print('escalones:', escalones)
    print('recorridos por escalon usado:', dict(por_escalon))
    print('violaciones (habia tarea en el escalon y no se uso):', len(violaciones), violaciones[:3])


if __name__ == '__main__':
    main()
