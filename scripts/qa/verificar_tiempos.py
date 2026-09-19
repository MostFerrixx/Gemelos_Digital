# -*- coding: utf-8 -*-
"""
Verificacion de los tiempos (plan de QA, bloque 4).

Para una corrida, recalcula con la configuracion QUE USO ESA CORRIDA (la de la
metadata) y los datos maestros (warehouse.db):

  * cada PICK: t = (base + u*qty + v*vol + kg*peso) * mult_clase + recargo,
    acotado por el minimo; con horquilla se suman 2 x tiempo_horquilla.
    Se compara con la duracion registrada (operation_completed).
  * cada PASO: tiempo entre dos celdas vecinas consecutivas de un agente en
    movimiento; se esperan time_per_cell (a pie) y time_per_cell x factor
    (montacargas), mas lento si "velocidad segun carga" esta activa.
  * cada DESCARGA: tiempo entre tareas depositadas seguidas en la zona de
    salida = descarga + pack de la clase.

Uso: python scripts/qa/verificar_tiempos.py <replay | carpeta> [--detalle]
"""
import collections
import os
import sqlite3
import statistics
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, AQUI)
import analizar_replay as ar  # noqa: E402


def catalogo():
    con = sqlite3.connect(os.path.join(RAIZ, 'warehouse.db'))
    try:
        return {c: {'vol': max(1, int((v or 0.01) * 100)), 'kg': float(k or 0.0),
                    'clase': str(cl or 'GENERAL')}
                for c, v, k, cl in con.execute(
                    'select sku_code, volume_m3, weight_kg, category from sku_catalog')}
    finally:
        con.close()


def moda(valores):
    c = collections.Counter(round(v, 4) for v in valores)
    return c.most_common(1)[0] if c else (None, 0)


def main():
    carpeta = sys.argv[1]
    detalle = '--detalle' in sys.argv
    meta, ev = ar.cargar(carpeta)
    cfg = meta.get('config', {})
    tiempos = cfg.get('tiempos', {}) or {}
    ptm = tiempos.get('pick_time_model', {}) or {}
    clases = tiempos.get('clases_manejo', {}) or {}
    lift = float(tiempos.get('tiempo_horquilla', 2.0))
    tpc = float(tiempos.get('time_per_cell', 0.1))
    f_ground = float(tiempos.get('speed_factor_ground', 1.0))
    f_fork = float(tiempos.get('speed_factor_forklift', 0.8))
    var_on = bool((tiempos.get('variabilidad') or {}).get('enabled', False))
    sku = catalogo()
    wo = {w['id']: w for w in meta.get('initial_work_orders', [])}

    linea = ar.linea_de_tiempo(ev)
    con_horquilla = {a for _, a, _, s in linea if s == 'lifting'}

    # ---------------------------------------------------------------- picks
    base = ptm.get('base')
    errores, ratios_por_grupo, filas = [], collections.defaultdict(list), []
    for e in ev:
        if ar.tipo_de(e) != 'operation_completed':
            continue
        w = wo.get(e['data'].get('work_order_id'))
        if not w:
            continue
        s = sku.get(w['sku_id'], {'vol': 1, 'kg': 0.0, 'clase': 'GENERAL'})
        q = w['cantidad_inicial']
        c = clases.get(s['clase']) or {}
        mult, recargo = float(c.get('mult', 1.0)), float(c.get('recargo', 0.0))
        t = ((float(base) if base is not None else 5.0)
             + float(ptm.get('por_unidad', 0)) * q
             + float(ptm.get('por_volumen', 0)) * q * s['vol']
             + float(ptm.get('por_kg', 0)) * q * s['kg'])
        t = max(t * mult + recargo, float(ptm.get('minimo', 0) or 0))
        agente = e.get('agent_id')
        esperado = t + (2 * lift if agente in con_horquilla else 0.0)
        real = float(e['data']['duration'])
        errores.append(abs(real - esperado))
        ratios_por_grupo[(w['sku_id'], q)].append(real / esperado if esperado else 1.0)
        filas.append((agente, w['id'], s['clase'], q, round(esperado, 4), round(real, 4)))
    exactos = sum(1 for x in errores if x < 1e-6)
    print('PICKS: %d | exactos (error < 1e-6): %d | error max: %.6f'
          % (len(errores), exactos, max(errores) if errores else 0))
    if var_on:
        ratios = [r for g in ratios_por_grupo.values() for r in g]
        print('   variabilidad ON: CV de real/esperado = %.3f (media %.3f, n=%d)'
              % (statistics.pstdev(ratios) / statistics.mean(ratios), statistics.mean(ratios), len(ratios)))
    if detalle:
        for f in filas[:8]:
            print('   ', f)

    # ---------------------------------------------------------------- pasos
    pasos = collections.defaultdict(list)
    ultimo = {}
    for ts, a, c, s in linea:
        p = ultimo.get(a)
        if p and c and p[1] and s == 'moving' and \
                abs(c[0] - p[1][0]) + abs(c[1] - p[1][1]) == 1 and ts > p[0]:
            pasos[a].append(ts - p[0])
        if c != (p[1] if p else None):
            ultimo[a] = (ts, c)
    for a, v in sorted(pasos.items()):
        esperado = tpc * (f_fork if a in con_horquilla else f_ground)
        m, n = moda(v)
        print('PASOS %-12s n=%5d  moda=%s (%d)  esperado=%.4f  mediana=%.4f'
              % (a, len(v), m, n, esperado, statistics.median(v)))

    # ------------------------------------------------------------- descargas
    staged = []
    for e in ev:
        if ar.tipo_de(e) == 'work_order_update' and e.get('status') == 'staged':
            staged.append((e['timestamp'], e.get('assigned_agent_id'), e['id']))
    staged.sort()
    por_agente = collections.defaultdict(list)
    for t, a, w in staged:
        por_agente[a].append((t, w))
    durs = collections.defaultdict(list)
    for a, lst in por_agente.items():
        for (t0, _w0), (t1, w1) in zip(lst, lst[1:]):
            if t1 - t0 < 120:
                durs[sku.get(wo[w1]['sku_id'], {}).get('clase')].append(round(t1 - t0, 4))
    for clase, v in sorted(durs.items(), key=lambda kv: str(kv[0])):
        print('DESCARGA clase=%-12s n=%4d  moda=%s' % (clase, len(v), moda(v)))


if __name__ == '__main__':
    sys.exit(main())
