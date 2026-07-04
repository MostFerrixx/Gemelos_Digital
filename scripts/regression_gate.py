# -*- coding: utf-8 -*-
"""
MEJ-1: Gate de regresion byte-identico en un comando.

Corre la simulacion canonica (config.json de la raiz) con WAREHOUSE_SEED fijo,
computa el SHA256 del .jsonl generado y lo compara contra tests/baseline.json.

Uso:
    python scripts/regression_gate.py                  -> PASS/FAIL (exit 0/1)
    python scripts/regression_gate.py --keep-output    -> conserva la corrida
    python scripts/regression_gate.py --update-baseline --yes
        -> SOLO para cambios de comportamiento INTENCIONALES: regenera el
           baseline con el resultado de esta corrida y lo escribe al JSON.

Regla: solo ASCII en la salida (consola Windows cp1252).
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASELINE_PATH = os.path.join(PROJECT_ROOT, "tests", "baseline.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
ENTRY_POINT = os.path.join(PROJECT_ROOT, "entry_points", "run_generate_replay.py")
TIMEOUT_SECONDS = 600


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_simulation(seed):
    """Corre la sim canonica; devuelve la carpeta output/simulation_* NUEVA."""
    before = set()
    if os.path.isdir(OUTPUT_DIR):
        before = {d for d in os.listdir(OUTPUT_DIR) if d.startswith("simulation_")}

    env = os.environ.copy()
    env["WAREHOUSE_SEED"] = str(seed)
    env["PYTHONUNBUFFERED"] = "1"

    print("[GATE] Corriendo simulacion canonica (WAREHOUSE_SEED=%s)..." % seed)
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, ENTRY_POINT],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=TIMEOUT_SECONDS,
    )
    elapsed = time.time() - t0
    if proc.returncode != 0:
        tail = proc.stdout.decode("utf-8", errors="replace").splitlines()[-15:]
        print("[FAIL] La simulacion termino con exit code %d. Ultimas lineas:" % proc.returncode)
        for line in tail:
            print("       " + line)
        return None, elapsed

    after = {d for d in os.listdir(OUTPUT_DIR) if d.startswith("simulation_")}
    new_dirs = sorted(after - before)
    if not new_dirs:
        print("[FAIL] La simulacion no creo ninguna carpeta output/simulation_*.")
        return None, elapsed
    # Si hubiera mas de una (no deberia), tomar la mas reciente de ESTA corrida.
    return os.path.join(OUTPUT_DIR, new_dirs[-1]), elapsed


def find_jsonl(sim_dir):
    for name in sorted(os.listdir(sim_dir)):
        if name.startswith("replay_") and name.endswith(".jsonl"):
            return os.path.join(sim_dir, name)
    return None


def main():
    parser = argparse.ArgumentParser(description="Gate de regresion byte-identico (MEJ-1)")
    parser.add_argument("--keep-output", action="store_true",
                        help="No borrar la carpeta output/ generada por el gate")
    parser.add_argument("--update-baseline", action="store_true",
                        help="Regenerar tests/baseline.json con esta corrida (requiere --yes)")
    parser.add_argument("--yes", action="store_true",
                        help="Confirma --update-baseline sin prompt")
    args = parser.parse_args()

    if args.update_baseline and not args.yes:
        print("[FAIL] --update-baseline requiere --yes explicito (es un cambio de contrato).")
        return 1

    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    local_py = platform.python_version()
    if local_py != baseline.get("python_version"):
        print("[WARN] Python local %s != %s del baseline: un FAIL podria deberse a la "
              "version del interprete, no al codigo." % (local_py, baseline.get("python_version")))

    sim_dir, elapsed = run_simulation(baseline["seed"])
    if sim_dir is None:
        return 1

    jsonl = find_jsonl(sim_dir)
    if jsonl is None:
        print("[FAIL] No se encontro replay_*.jsonl en %s" % sim_dir)
        return 1

    sha = sha256_of(jsonl)
    size = os.path.getsize(jsonl)
    print("[GATE] Corrida: %.1f s | %s | %d bytes" % (elapsed, os.path.basename(jsonl), size))

    if args.update_baseline:
        baseline.update({
            "sha256": sha,
            "size_bytes": size,
            "python_version": local_py,
            "updated": time.strftime("%Y-%m-%d"),
        })
        with open(BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=4, ensure_ascii=True)
            f.write("\n")
        print("[OK] BASELINE ACTUALIZADO: sha256=%s size=%d" % (sha, size))
        print("     Commitea tests/baseline.json JUNTO con el cambio de comportamiento.")
        result = 0
    elif sha == baseline["sha256"] and size == baseline["size_bytes"]:
        print("[OK] GATE PASS: byte-identico al baseline (sha256=%s...)" % sha[:16])
        result = 0
    else:
        print("[FAIL] GATE FAIL: el comportamiento del motor CAMBIO.")
        print("       esperado: sha256=%s size=%d" % (baseline["sha256"], baseline["size_bytes"]))
        print("       obtenido: sha256=%s size=%d" % (sha, size))
        print("       Si el cambio es intencional: --update-baseline --yes")
        result = 1

    if args.keep_output or (result != 0 and not args.update_baseline):
        # En FAIL se conserva la evidencia para diff/diagnostico.
        print("[GATE] Corrida conservada en: %s" % sim_dir)
    else:
        shutil.rmtree(sim_dir, ignore_errors=True)
        print("[GATE] Corrida temporal eliminada (usa --keep-output para conservarla).")

    return result


if __name__ == "__main__":
    sys.exit(main())
