# -*- coding: utf-8 -*-
"""
Analizador de corridas para el plan de QA (docs/PLAN_QA_CONFIGURACION_WEB.md).

Resume un replay (.jsonl) en las "firmas observables" que usa el nivel 2 del
plan, y propone instantes para el nivel 3 (comparar con el visor).

Uso:
    python scripts/qa/analizar_replay.py <replay.jsonl | carpeta>
    python scripts/qa/analizar_replay.py <replay> --muestras 5 --semilla 7
    python scripts/qa/analizar_replay.py <replay> --json resumen.json
    python scripts/qa/analizar_replay.py <replay> --posiciones 1234.5

Es determinista: el mismo replay da siempre el mismo resumen.
"""
import argparse
import collections
import json
import os
import random
import statistics
import sys

ESTADOS_ACTIVOS = {'moving', 'picking', 'lifting', 'unloading', 'working',
                   'discharging', 'cambiando_equipo'}


def encontrar_jsonl(ruta):
    if os.path.isdir(ruta):
        for nombre in sorted(os.listdir(ruta)):
            if nombre.startswith('replay_') and nombre.endswith('.jsonl'):
                return os.path.join(ruta, nombre)
        raise SystemExit('[ERROR] no hay replay_*.jsonl en %s' % ruta)
    return ruta


def cargar(ruta):
    with open(encontrar_jsonl(ruta), encoding='utf-8') as f:
        lineas = f.read().splitlines()
    meta = json.loads(lineas[0])
    eventos = [json.loads(l) for l in lineas[1:] if l.strip()]
    return meta, eventos


def clases_de_sku(raiz=None):
    """{sku: clase_manejo} desde warehouse.db (lo que usa el motor)."""
    import sqlite3
    raiz = raiz or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    ruta = os.path.join(raiz, 'warehouse.db')
    if not os.path.exists(ruta):
        return {}
    con = sqlite3.connect(ruta)
    try:
        return dict(con.execute('select sku_code, category from sku_catalog'))
    finally:
        con.close()


def tipo_de(evento):
    return evento.get('type') or evento.get('event_type')


def linea_de_tiempo(eventos):
    """[(t, agente, celda, estado)] de los eventos estado_agente, en orden."""
    salida = []
    for e in eventos:
        if tipo_de(e) != 'estado_agente':
            continue
        d = e.get('data', {})
        pos = d.get('position')
        salida.append((e['timestamp'], e['agent_id'],
                       tuple(pos) if pos else None, d.get('status')))
    return salida


def posiciones_en(linea, t):
    """Estado de cada agente en el instante t (ultimo evento <= t)."""
    estado = {}
    for ts, agente, celda, status in linea:
        if ts > t:
            break
        estado[agente] = {'celda': celda, 'status': status, 'desde': ts}
    return estado


def posicion_al_pedir(linea, agente, t):
    """Celda donde estaba `agente` cuando PIDIO trabajo en el instante t.

    En un mismo instante el agente puede pedir trabajo (estado idle) y dar el
    primer paso del recorrido; la posicion util para verificar el despacho es
    la del pedido, no la de despues del paso (QA bloque 2)."""
    celda = None
    for ts, a, c, s in linea:
        if ts > t:
            break
        if a != agente:
            continue
        if ts < t or s == 'idle':
            celda = c
    return celda


def resumir(meta, eventos):
    config = meta.get('config', {})
    iniciales = meta.get('initial_work_orders', []) or []
    wo_info = {w['id']: w for w in iniciales}

    tipos = collections.Counter(tipo_de(e) for e in eventos)
    fin = max((e.get('timestamp', 0) for e in eventos), default=0)

    # WOs: estado final y datos del ultimo update (incluye staging/work_area)
    wo_update = {}
    asignaciones = collections.defaultdict(list)  # (agente, t) -> [wo]
    for e in eventos:
        if tipo_de(e) != 'work_order_update':
            continue
        wo_update[e['id']] = e
        if e.get('status') == 'assigned':
            asignaciones[(e.get('assigned_agent_id'), e['timestamp'])].append(e['id'])
    for wid, e in wo_update.items():
        info = wo_info.setdefault(wid, {'id': wid})
        info.setdefault('order_id', e.get('order_id'))
        info.setdefault('work_area', e.get('work_area'))
        info['staging'] = e.get('staging')
        info['estado_final'] = e.get('status')
        info['agente'] = e.get('assigned_agent_id')
        info['sku_id'] = info.get('sku_id') or e.get('sku_id')

    # Tours = WOs asignadas al mismo agente en el mismo instante.
    tours = [wos for wos in asignaciones.values()]
    zonas_por_tour = [len({wo_info.get(w, {}).get('staging') for w in t}) for t in tours]

    # Picks: operation_completed trae la duracion real del pick por WO.
    picks = []
    for e in eventos:
        if tipo_de(e) == 'operation_completed':
            d = e.get('data', {})
            wid = d.get('work_order_id')
            picks.append({'wo': wid, 'agente': e.get('agent_id'),
                          'duracion': d.get('duration'), 't': e['timestamp'],
                          'area': wo_info.get(wid, {}).get('work_area')})

    agentes = collections.OrderedDict()
    carga_max = collections.defaultdict(float)
    capacidad = {}
    for e in eventos:
        if tipo_de(e) != 'estado_agente':
            continue
        d = e.get('data', {})
        a = e['agent_id']
        agentes.setdefault(a, d.get('agent_type') or e.get('agent_type'))
        carga_max[a] = max(carga_max[a], float(d.get('cargo_volume') or 0))
        capacidad[a] = d.get('capacidad')

    picks_por_agente_area = collections.defaultdict(collections.Counter)
    for p in picks:
        picks_por_agente_area[p['agente']][p['area']] += 1

    # Co-ocupacion: dos agentes en la misma celda al cerrar un instante.
    linea = linea_de_tiempo(eventos)
    pos = {}
    coocupaciones = []
    i = 0
    while i < len(linea):
        t = linea[i][0]
        while i < len(linea) and linea[i][0] == t:
            _, a, celda, status = linea[i]
            pos[a] = celda
            i += 1
        celdas = collections.Counter(c for c in pos.values() if c)
        for celda, n in celdas.items():
            if n > 1:
                coocupaciones.append((t, celda, n))

    clases = clases_de_sku()
    wos_por_clase = collections.Counter(
        clases.get(w.get('sku_id'), 'SIN_CLASE') for w in wo_info.values())

    staging = collections.Counter(
        str(w.get('staging')) for w in wo_info.values() if w.get('staging') is not None)
    duraciones = [p['duracion'] for p in picks if p['duracion'] is not None]

    return {
        'config_clave': {k: config.get(k) for k in (
            'order_generation_mode', 'total_ordenes', 'dispatch_strategy',
            'tour_type', 'outbound_staging_distribution')},
        'fin_s': round(fin, 3),
        'eventos': dict(tipos),
        'ordenes_distintas': len({w.get('order_id') for w in wo_info.values()
                                  if w.get('order_id')}),
        'wos_totales': len(wo_info),
        'wos_por_estado_final': dict(collections.Counter(
            w.get('estado_final') for w in wo_info.values())),
        'wos_por_area': dict(collections.Counter(
            w.get('work_area') for w in wo_info.values())),
        'wos_por_staging': dict(staging),
        'wos_por_clase': dict(wos_por_clase),
        'agentes': dict(agentes),
        'capacidad_por_agente': capacidad,
        'carga_max_por_agente': {a: round(v, 2) for a, v in carga_max.items()},
        'picks_por_agente_area': {a: dict(c) for a, c in picks_por_agente_area.items()},
        'tours': len(tours),
        'tours_con_mas_de_una_zona': sum(1 for z in zonas_por_tour if z > 1),
        'wos_por_tour_max': max((len(t) for t in tours), default=0),
        'pick_duracion': {
            'n': len(duraciones),
            'min': round(min(duraciones), 3) if duraciones else None,
            'media': round(statistics.mean(duraciones), 3) if duraciones else None,
            'max': round(max(duraciones), 3) if duraciones else None,
        },
        'coocupaciones': {'instantes': len(coocupaciones),
                          'ejemplos': coocupaciones[:5]},
        'bottleneck_summary': meta.get('bottleneck_summary'),
    }


def muestras(eventos, n=5, semilla=7):
    """n instantes al azar con al menos 2 agentes activos (no ociosos)."""
    linea = linea_de_tiempo(eventos)
    candidatos = []
    estado = {}
    for ts, a, celda, status in linea:
        estado[a] = status
        if sum(1 for s in estado.values() if s in ESTADOS_ACTIVOS) >= 2:
            candidatos.append(ts)
    candidatos = sorted(set(candidatos))
    rng = random.Random(semilla)
    elegidos = sorted(rng.sample(candidatos, min(n, len(candidatos))))
    return [{'t': t, 'agentes': posiciones_en(linea, t)} for t in elegidos]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('replay')
    ap.add_argument('--muestras', type=int, default=0)
    ap.add_argument('--semilla', type=int, default=7)
    ap.add_argument('--posiciones', type=float, default=None)
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    meta, eventos = cargar(args.replay)
    resumen = resumir(meta, eventos)
    if args.muestras:
        resumen['muestras'] = muestras(eventos, args.muestras, args.semilla)
    if args.posiciones is not None:
        resumen['posiciones'] = posiciones_en(linea_de_tiempo(eventos), args.posiciones)

    texto = json.dumps(resumen, indent=2, ensure_ascii=True, default=str)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            f.write(texto)
    print(texto)


if __name__ == '__main__':
    sys.exit(main())
