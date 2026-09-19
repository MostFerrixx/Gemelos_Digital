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


def _termina_con_fin(ruta):
    """True si la ultima linea del .jsonl es el evento SIMULATION_END."""
    try:
        with open(ruta, 'rb') as f:
            f.seek(0, os.SEEK_END)
            tam = f.tell()
            f.seek(max(0, tam - 400))
            cola = f.read().decode('utf-8', 'replace').strip().splitlines()
        return bool(cola) and 'SIMULATION_END' in cola[-1]
    except OSError:
        return False


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
            jsonl = glob.glob(os.path.join(carpeta, 'replay_*.jsonl'))
            # El Excel se escribe ANTES de que termine el .jsonl: la corrida
            # recien esta completa cuando el .jsonl cierra con SIMULATION_END
            # (leccion del bloque 4: se analizo un .jsonl a medio escribir).
            if jsonl and glob.glob(os.path.join(carpeta, '*.xlsx')) and \
                    _termina_con_fin(jsonl[0]):
                print(os.path.relpath(carpeta, RAIZ), os.path.relpath(temporal, RAIZ))
                return 0
        time.sleep(3)
    raise SystemExit('[TIMEOUT] la corrida no termino en %.0f s' % args.timeout)


if __name__ == '__main__':
    sys.exit(main())
