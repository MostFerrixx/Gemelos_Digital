# -*- coding: utf-8 -*-
"""
MEJ-2: Experiment runner -- N replicas con semillas distintas + comparacion A/B.

Convierte corridas-anecdota (N=1, estocasticas) en decisiones con rigor
estadistico. Reusa el patron de scripts/regression_gate.py: cada replica
corre en un subprocess aislado via entry_points/run_generate_replay.py,
con WAREHOUSE_SEED distinto y --output-metrics para leer los KPIs ya
exportados por el motor (sin tocarlo).

Modos:
    python scripts/experiment_runner.py run --config config.json --replicas 5
        -> corre N replicas de UNA config, agrega KPIs (media, desv, IC 95%).

    python scripts/experiment_runner.py compare --config-a A.json --config-b B.json --replicas 5
        -> corre N replicas pareadas (mismas semillas) de DOS configs y da un
           veredicto estadistico por KPI (t-test pareado): diferencia real o ruido.

Opciones comunes:
    --base-seed N       Primera semilla (default 1000); las siguientes son N+1, N+2, ...
    --output PATH.xlsx  Exporta resultado crudo + resumen a Excel.
    --keep-output       No borra las carpetas output/simulation_* de cada replica.

Regla: solo ASCII en la salida (consola Windows cp1252).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from scipy import stats as _stats

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
ENTRY_POINT = os.path.join(PROJECT_ROOT, "entry_points", "run_generate_replay.py")
TIMEOUT_SECONDS = 600

# KPIs leidos directamente de export_optimization_metrics() (event_generator.py).
# "throughput_wo_per_s" es derivado (completadas / tiempo de sim).
RAW_KPI_KEYS = [
    "total_workorders_completed",
    "total_workorders_failed",
    "total_simulation_time_seconds",
    "avg_completion_time_seconds",
]
ALL_KPI_KEYS = RAW_KPI_KEYS + ["throughput_wo_per_s"]


def _find_new_output_dir(before):
    if not os.path.isdir(OUTPUT_DIR):
        return None
    after = {d for d in os.listdir(OUTPUT_DIR) if d.startswith("simulation_")}
    new_dirs = sorted(after - before)
    if not new_dirs:
        return None
    return os.path.join(OUTPUT_DIR, new_dirs[-1])


def run_one_replica(config_path, seed, keep_output=False):
    """Corre una replica aislada; devuelve (metrics_dict, elapsed_seconds)."""
    before = set()
    if os.path.isdir(OUTPUT_DIR):
        before = {d for d in os.listdir(OUTPUT_DIR) if d.startswith("simulation_")}

    env = os.environ.copy()
    env["WAREHOUSE_SEED"] = str(seed)
    env["PYTHONUNBUFFERED"] = "1"

    fd, metrics_path = tempfile.mkstemp(prefix="experiment_metrics_", suffix=".json")
    os.close(fd)
    os.remove(metrics_path)  # el motor lo crea; solo reservamos el nombre

    cmd = [sys.executable, ENTRY_POINT, "--config", config_path, "--output-metrics", metrics_path]

    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=PROJECT_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=TIMEOUT_SECONDS,
    )
    elapsed = time.time() - t0

    if proc.returncode != 0:
        tail = proc.stdout.decode("utf-8", errors="replace").splitlines()[-15:]
        raise RuntimeError(
            "Replica seed=%s termino con exit code %d. Ultimas lineas:\n  %s"
            % (seed, proc.returncode, "\n  ".join(tail))
        )

    if not os.path.exists(metrics_path):
        raise RuntimeError("Replica seed=%s: no se genero el archivo de metricas." % seed)

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    os.remove(metrics_path)

    sim_dir = _find_new_output_dir(before)
    if sim_dir and not keep_output:
        shutil.rmtree(sim_dir, ignore_errors=True)
    elif sim_dir:
        metrics["_output_dir"] = sim_dir

    completed = metrics.get("total_workorders_completed", 0)
    sim_time = metrics.get("total_simulation_time_seconds", 0)
    metrics["throughput_wo_per_s"] = (completed / sim_time) if sim_time else 0.0
    metrics["_seed"] = seed
    metrics["_elapsed_wallclock_s"] = elapsed
    return metrics


def run_replicas(config_path, n, base_seed, keep_output=False, label=""):
    results = []
    for i in range(n):
        seed = base_seed + i
        print("[EXPERIMENT] %sReplica %d/%d (seed=%d)..." % (label, i + 1, n, seed))
        metrics = run_one_replica(config_path, seed, keep_output=keep_output)
        print("  -> completadas=%s fallidas=%s tiempo_sim=%.1fs (%.1fs wall)" % (
            metrics.get("total_workorders_completed"),
            metrics.get("total_workorders_failed"),
            metrics.get("total_simulation_time_seconds", 0.0),
            metrics.get("_elapsed_wallclock_s", 0.0),
        ))
        results.append(metrics)
    return results


def summarize(values):
    """Media, desviacion estandar muestral e IC 95% (t-Student) de una lista de floats."""
    n = len(values)
    mean = sum(values) / n
    if n > 1:
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        std = variance ** 0.5
        se = std / (n ** 0.5)
        t_crit = _stats.t.ppf(0.975, df=n - 1)
        margin = t_crit * se
    else:
        std = 0.0
        margin = 0.0
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "ci95_low": mean - margin,
        "ci95_high": mean + margin,
    }


def paired_verdict(values_a, values_b, alpha=0.05):
    """t-test pareado (mismas semillas en A y B). Devuelve dict con veredicto."""
    if len(values_a) != len(values_b) or len(values_a) < 2:
        return {"statistic": None, "pvalue": None, "verdict": "N/A (necesita >=2 replicas pareadas)"}
    diffs = [b - a for a, b in zip(values_a, values_b)]
    if all(d == diffs[0] for d in diffs):
        # Varianza cero en las diferencias: el t-test da 0/0 (nan). Caso real, no ruido.
        if diffs[0] == 0:
            return {"statistic": None, "pvalue": None, "verdict": "IDENTICO (sin diferencia en ninguna replica)"}
        return {"statistic": None, "pvalue": 0.0,
                 "verdict": "DIFERENCIA SIGNIFICATIVA (constante en todas las replicas)"}
    statistic, pvalue = _stats.ttest_rel(values_a, values_b)
    verdict = "DIFERENCIA SIGNIFICATIVA (p<%.2f)" % alpha if pvalue < alpha else "RUIDO (no significativo)"
    return {"statistic": statistic, "pvalue": pvalue, "verdict": verdict}


def _print_run_summary(results):
    print("\n" + "=" * 70)
    print("RESUMEN -- %d replicas" % len(results))
    print("=" * 70)
    for key in ALL_KPI_KEYS:
        values = [r.get(key, 0.0) for r in results]
        s = summarize(values)
        print("%-32s media=%.2f  std=%.2f  IC95=[%.2f, %.2f]" % (
            key, s["mean"], s["std"], s["ci95_low"], s["ci95_high"]))
    print("=" * 70)


def _print_compare_summary(results_a, results_b):
    print("\n" + "=" * 90)
    print("COMPARACION A/B -- %d replicas pareadas por semilla" % len(results_a))
    print("=" * 90)
    for key in ALL_KPI_KEYS:
        values_a = [r.get(key, 0.0) for r in results_a]
        values_b = [r.get(key, 0.0) for r in results_b]
        sa, sb = summarize(values_a), summarize(values_b)
        v = paired_verdict(values_a, values_b)
        delta_pct = ((sb["mean"] - sa["mean"]) / sa["mean"] * 100.0) if sa["mean"] else float("nan")
        pvalue_str = ("%.4f" % v["pvalue"]) if v["pvalue"] is not None else "N/A"
        print("%-32s A=%.2f  B=%.2f  delta=%+.1f%%  p=%s  -> %s" % (
            key, sa["mean"], sb["mean"], delta_pct, pvalue_str, v["verdict"]))
    print("=" * 90)


def _export_excel(path, results, results_b=None):
    import pandas as pd

    df_a = pd.DataFrame(results)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_a.to_excel(writer, sheet_name="Replicas_A", index=False)
        summary_rows = [{"kpi": k, **summarize([r.get(k, 0.0) for r in results])} for k in ALL_KPI_KEYS]
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Resumen_A", index=False)

        if results_b is not None:
            df_b = pd.DataFrame(results_b)
            df_b.to_excel(writer, sheet_name="Replicas_B", index=False)
            compare_rows = []
            for k in ALL_KPI_KEYS:
                values_a = [r.get(k, 0.0) for r in results]
                values_b = [r.get(k, 0.0) for r in results_b]
                v = paired_verdict(values_a, values_b)
                compare_rows.append({
                    "kpi": k,
                    "mean_a": summarize(values_a)["mean"],
                    "mean_b": summarize(values_b)["mean"],
                    "pvalue": v["pvalue"],
                    "verdict": v["verdict"],
                })
            pd.DataFrame(compare_rows).to_excel(writer, sheet_name="Comparacion_AB", index=False)
    print("[EXPERIMENT] Excel exportado: %s" % path)


def cmd_run(args):
    if not os.path.isfile(args.config):
        print("[FAIL] No existe el config: %s" % args.config)
        return 1
    results = run_replicas(args.config, args.replicas, args.base_seed, keep_output=args.keep_output)
    _print_run_summary(results)
    if args.output:
        _export_excel(args.output, results)
    return 0


def cmd_compare(args):
    for path in (args.config_a, args.config_b):
        if not os.path.isfile(path):
            print("[FAIL] No existe el config: %s" % path)
            return 1
    results_a = run_replicas(args.config_a, args.replicas, args.base_seed, keep_output=args.keep_output, label="[A] ")
    results_b = run_replicas(args.config_b, args.replicas, args.base_seed, keep_output=args.keep_output, label="[B] ")
    _print_compare_summary(results_a, results_b)
    if args.output:
        _export_excel(args.output, results_a, results_b=results_b)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="MEJ-2: Experiment runner -- replicas con rigor estadistico y comparacion A/B.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    p_run = sub.add_parser("run", help="N replicas de una config, KPIs agregados (media/std/IC95)")
    p_run.add_argument("--config", required=True, help="Path al config.json a correr")
    p_run.add_argument("--replicas", type=int, default=5, help="Numero de replicas (default 5)")
    p_run.add_argument("--base-seed", type=int, default=1000, help="Primera semilla (default 1000)")
    p_run.add_argument("--output", type=str, default=None, help="Path .xlsx para exportar resultados")
    p_run.add_argument("--keep-output", action="store_true", help="No borrar output/simulation_* de cada replica")
    p_run.set_defaults(func=cmd_run)

    p_cmp = sub.add_parser("compare", help="Compara dos configs con semillas pareadas + veredicto estadistico")
    p_cmp.add_argument("--config-a", required=True, help="Path al config.json A (baseline)")
    p_cmp.add_argument("--config-b", required=True, help="Path al config.json B (variante)")
    p_cmp.add_argument("--replicas", type=int, default=5, help="Numero de replicas pareadas (default 5)")
    p_cmp.add_argument("--base-seed", type=int, default=1000, help="Primera semilla (default 1000)")
    p_cmp.add_argument("--output", type=str, default=None, help="Path .xlsx para exportar resultados")
    p_cmp.add_argument("--keep-output", action="store_true", help="No borrar output/simulation_* de cada replica")
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as e:
        print("[FAIL] %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
