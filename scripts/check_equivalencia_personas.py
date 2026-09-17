# -*- coding: utf-8 -*-
"""
Prueba de equivalencia de INIT-11 F1 (personas y equipos separados).

Toma el config canonico, expresa su flota como `personas` + `equipos` (mismos
nombres de agente, mismas capacidades, velocidades y horquilla) y corre las
dos variantes con la misma semilla. Los EVENTOS (lineas 2..n del .jsonl)
deben ser identicos; la linea 1 (metadata) difiere solo porque lleva el
config.

Uso:
    python scripts/check_equivalencia_personas.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from core.fleet import resolver_flota  # noqa: E402

ENTRY_POINT = os.path.join(PROJECT_ROOT, "entry_points", "run_generate_replay.py")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
SEED = "42"


def config_con_personas(config):
    """La misma flota, escrita con el modelo persona + equipo."""
    nuevo = json.loads(json.dumps(config))
    personas, equipos, contador = [], {}, {}
    prefijos = {"GroundOperator": "GroundOp", "Forklift": "Forklift"}
    for agente in resolver_flota(config):
        tipo = agente["type"]
        equipo = agente["equipo"]
        nombre_equipo = "equipo_" + tipo
        equipos[nombre_equipo] = {
            "tipo_base": tipo,
            "capacidad": equipo["capacidad"],
            "velocidad": equipo["velocidad"],
            "horquilla_s": equipo["horquilla_s"],
        }
        contador[tipo] = contador.get(tipo, 0) + 1
        personas.append({
            "grupo": "G_" + tipo,
            "nombres": ["%s-%02d" % (prefijos[tipo], contador[tipo])],
            "cantidad": 1,
            "equipo": nombre_equipo,
            "discharge_time": agente["discharge_time"],
            "work_area_priorities": agente["work_area_priorities"],
        })
    nuevo.pop("agent_types", None)
    nuevo["equipos"] = equipos
    nuevo["personas"] = personas
    return nuevo


def correr(config_path):
    antes = set(os.listdir(OUTPUT_DIR)) if os.path.isdir(OUTPUT_DIR) else set()
    env = dict(os.environ, WAREHOUSE_SEED=SEED, PYTHONUNBUFFERED="1")
    args = [sys.executable, ENTRY_POINT]
    if config_path:
        args += ["--config", config_path]
    proc = subprocess.run(args, cwd=PROJECT_ROOT, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        print(proc.stdout.decode("utf-8", "replace")[-2000:])
        raise SystemExit("[FAIL] la simulacion termino con error")
    nuevas = sorted(d for d in set(os.listdir(OUTPUT_DIR)) - antes
                    if d.startswith("simulation_"))
    carpeta = os.path.join(OUTPUT_DIR, nuevas[-1])
    jsonl = [f for f in os.listdir(carpeta) if f.endswith(".jsonl")][0]
    with open(os.path.join(carpeta, jsonl), encoding="utf-8") as f:
        lineas = f.read().splitlines()
    shutil.rmtree(carpeta, ignore_errors=True)
    return lineas


def main():
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        config = json.load(f)
    variante = config_con_personas(config)

    tmp = tempfile.mkdtemp(prefix="equiv_f1_")
    ruta = os.path.join(tmp, "config_personas.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(variante, f, indent=2)

    print("[EQUIV] Flota como personas + equipos:")
    for p in variante["personas"]:
        print("   %s -> %s" % (p["nombres"][0], p["equipo"]))

    try:
        print("[EQUIV] Corriendo config canonico...")
        a = correr(None)
        print("[EQUIV] Corriendo config con personas...")
        b = correr(ruta)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    eventos_a, eventos_b = a[1:], b[1:]
    if eventos_a == eventos_b:
        print("[OK] EQUIVALENTE: %d eventos identicos." % len(eventos_a))
        return 0
    distintos = sum(1 for x, y in zip(eventos_a, eventos_b) if x != y)
    print("[FAIL] NO equivalente: %d vs %d eventos, %d lineas distintas."
          % (len(eventos_a), len(eventos_b), distintos))
    for x, y in zip(eventos_a, eventos_b):
        if x != y:
            print("   canonico: " + x[:200])
            print("   personas: " + y[:200])
            break
    return 1


if __name__ == "__main__":
    sys.exit(main())
