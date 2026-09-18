# -*- coding: utf-8 -*-
"""
Espera a que termine la corrida lanzada con "Run Simulation" desde la web.

Toma la copia temporal mas reciente de temp_web/ (la crea el boton Run) y
espera la carpeta output/simulation_* creada despues, con el replay y el Excel.
Imprime: <carpeta> <config temporal>.

Uso: python scripts/qa/esperar_corrida.py [--timeout 600]
"""
import argparse
import glob
import os
import sys
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--timeout', type=float, default=600)
    args = ap.parse_args()

    temporales = glob.glob(os.path.join(RAIZ, 'temp_web', 'run_config_*.json'))
    if not temporales:
        raise SystemExit('[ERROR] no hay copias temporales en temp_web/')
    temporal = max(temporales, key=os.path.getmtime)
    desde = os.path.getmtime(temporal) - 2

    inicio = time.time()
    while time.time() - inicio < args.timeout:
        for carpeta in glob.glob(os.path.join(RAIZ, 'output', 'simulation_*')):
            if os.path.getmtime(carpeta) < desde:
                continue
            if glob.glob(os.path.join(carpeta, 'replay_*.jsonl')) and \
                    glob.glob(os.path.join(carpeta, '*.xlsx')):
                print(os.path.relpath(carpeta, RAIZ), os.path.relpath(temporal, RAIZ))
                return 0
        time.sleep(3)
    raise SystemExit('[TIMEOUT] la corrida no termino en %.0f s' % args.timeout)


if __name__ == '__main__':
    sys.exit(main())
