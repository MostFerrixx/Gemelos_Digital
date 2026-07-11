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
ENTRY_POINT = os.path.join(PROJECT_ROOT, "entry_points", "run_generate_replay.py")
TIMEOUT_SECONDS = 600

# DISK 2026-07-07: los temporales van a una carpeta del PROYECTO (disco D,
# gitignoreada), NO a %TEMP% (disco C) -- el Director reporto saturacion de C
# y estos archivos quedaban huerfanos ante crash/stop (taskkill). purge_stale
# borra los que tengan mas de 1 dia al arrancar cualquier corrida.
TEMP_WEB_DIR = os.path.join(PROJECT_ROOT, "temp_web")


def purge_stale_temp(max_age_hours=24):
    """Borra archivos de temp_web/ con mas de max_age_hours (huerfanos de
    corridas crasheadas/detenidas). Silencioso e inofensivo si no existe."""
    try:
        if not os.path.isdir(TEMP_WEB_DIR):
            return
        cutoff = time.time() - max_age_hours * 3600
        for name in os.listdir(TEMP_WEB_DIR):
            p = os.path.join(TEMP_WEB_DIR, name)
            try:
                if os.path.isfile(p) and os.path.getmtime(p) < cutoff:
                    os.remove(p)
            except OSError:
                pass
    except OSError:
        pass

# KPIs leidos directamente de export_optimization_metrics() (event_generator.py).
# "throughput_wo_per_s" es derivado (completadas / tiempo de sim).
# "throughput_picks_per_s" (AUDIT 2026-07-10): SOLO picks exitosos -- con
# inbound activo, throughput_wo_per_s mezcla picks+putaway con el tiempo
# extendido de la recepcion; este es el comparable limpio entre configs
# con/sin inbound.
RAW_KPI_KEYS = [
    "total_workorders_completed",
    "total_workorders_failed",
    "total_simulation_time_seconds",
    "avg_completion_time_seconds",
]
ALL_KPI_KEYS = RAW_KPI_KEYS + ["throughput_wo_per_s", "throughput_picks_per_s"]

# MEJ-2 v2: nivel de servicio (fill_rate_pct). Puede ser None en modo
# estocastico (sin validacion de stock, mismo comportamiento que INIT-5 en el
# visor/API/Excel) -- se agrega y agrega por separado porque summarize()/
# paired_verdict() necesitan filtrar los None antes de operar.
# INIT-7 F4/F5: KPIs de inbound (None cuando inbound off, mismo trato que
# fill_rate_pct) -> el A/B compara estrategias de slotting, prioridad de
# flota (avg_putaway_wait) y el efecto del cross-dock (fill_rate_effective).
OPTIONAL_KPI_KEYS = ["fill_rate_pct", "avg_dock_to_stock",
                     "avg_putaway_distance", "avg_putaway_wait",
                     "fill_rate_effective_pct"]


def run_one_replica(config_path, seed, keep_output=False):
    """Corre una replica aislada; devuelve (metrics_dict, elapsed_seconds)."""
    env = os.environ.copy()
    env["WAREHOUSE_SEED"] = str(seed)
    env["PYTHONUNBUFFERED"] = "1"

    os.makedirs(TEMP_WEB_DIR, exist_ok=True)
    purge_stale_temp()
    fd, metrics_path = tempfile.mkstemp(prefix="experiment_metrics_", suffix=".json",
                                        dir=TEMP_WEB_DIR)
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

    # REVIEW 2026-07-06: la carpeta a limpiar sale de las metricas de ESTA
    # replica (el motor reporta su propio session_output_dir), no de un diff
    # antes/despues del directorio output/ -- el diff tenia una carrera real
    # si un estudio del optimizador corria a la vez (podia borrar la carpeta
    # de OTRO proceso y dejar la propia). Mismo patron que el fix de auditoria
    # en optimizer.py.
    sim_dir = metrics.get("session_output_dir")
    if sim_dir and not os.path.isabs(sim_dir):
        sim_dir = os.path.join(PROJECT_ROOT, sim_dir)
    if sim_dir and os.path.basename(os.path.normpath(sim_dir)).startswith("simulation_"):
        if not keep_output:
            shutil.rmtree(sim_dir, ignore_errors=True)
        else:
            metrics["_output_dir"] = sim_dir

    completed = metrics.get("total_workorders_completed", 0)
    sim_time = metrics.get("total_simulation_time_seconds", 0)
    metrics["throughput_wo_per_s"] = (completed / sim_time) if sim_time else 0.0
    # AUDIT menores: picks-only (fallback = completadas para metrics viejos).
    picks = metrics.get("total_picks_completed", completed)
    metrics["throughput_picks_per_s"] = (picks / sim_time) if sim_time else 0.0
    metrics["_seed"] = seed
    metrics["_elapsed_wallclock_s"] = elapsed
    return metrics


def run_replicas(config_path, n, base_seed, keep_output=False, label="", progress_cb=None):
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
        if progress_cb is not None:
            progress_cb(label.strip("[] "), i + 1, n)
    return results


class ProgressWriter:
    """MEJ-EXP-WEB: escribe el progreso del experimento a un JSON (escritura
    atomica: tmp + os.replace) para que la web pueda hacer polling sin leer
    archivos a medio escribir. Sin --progress-json no se instancia -- el CLI
    puro queda identico."""

    def __init__(self, path, mode, total_replicas):
        self.path = path
        self.state = {
            "mode": mode,
            "status": "running",
            "total_replicas": total_replicas,
            "completed_replicas": 0,
            "current_label": "",
            "error": None,
            "result": None,
        }
        self._flush()

    def _flush(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=True, indent=2)
        os.replace(tmp, self.path)

    def on_replica(self, label, done_in_label, n_label):
        # En compare, B corre despues de A: el acumulado global avanza de a 1.
        self.state["completed_replicas"] += 1
        self.state["current_label"] = label
        self._flush()

    def finish(self, result_rows):
        self.state["status"] = "done"
        self.state["result"] = result_rows
        self._flush()

    def fail(self, error_msg):
        self.state["status"] = "error"
        self.state["error"] = str(error_msg)
        self._flush()


def build_run_result(results):
    """Filas serializables del resumen de un run (para --progress-json y Excel)."""
    rows = []
    for key in ALL_KPI_KEYS + OPTIONAL_KPI_KEYS:
        values = _collect_values(key, results)
        if not values:
            rows.append({"kpi": key, "available": False})
            continue
        s = summarize(values)
        rows.append({"kpi": key, "available": True, **s})
    return rows


def _collect_paired_values(key, results_a, results_b):
    """AUDIT 2026-07-10: pares (a, b) de la MISMA replica (mismo indice =
    misma semilla), descartando el par completo si CUALQUIER lado es None.

    Antes se filtraban los None por lado ANTES de parear (_collect_values
    independiente): si los None caian en semillas distintas entre A y B, el
    t-test pareado comparaba replicas desalineadas como si fueran pares.
    Con los KPIs opcionales (fill_rate_pct, avg_dock_to_stock,
    fill_rate_effective_pct...) el riesgo es real. Media y veredicto se
    calculan sobre los MISMOS pares (consistencia estadistica)."""
    pares_a, pares_b = [], []
    for ra, rb in zip(results_a, results_b):
        va, vb = ra.get(key), rb.get(key)
        if va is not None and vb is not None:
            pares_a.append(va)
            pares_b.append(vb)
    return pares_a, pares_b


def build_compare_result(results_a, results_b):
    """Filas serializables de la comparacion A/B (para --progress-json y Excel)."""
    rows = []
    for key in ALL_KPI_KEYS + OPTIONAL_KPI_KEYS:
        values_a, values_b = _collect_paired_values(key, results_a, results_b)
        if not values_a or not values_b:
            rows.append({"kpi": key, "available": False})
            continue
        sa, sb = summarize(values_a), summarize(values_b)
        v = paired_verdict(values_a, values_b)
        delta_pct = ((sb["mean"] - sa["mean"]) / sa["mean"] * 100.0) if sa["mean"] else None
        rows.append({
            "kpi": key, "available": True,
            "mean_a": sa["mean"], "mean_b": sb["mean"],
            "delta_pct": delta_pct,
            "pvalue": v["pvalue"], "verdict": v["verdict"],
        })
    return rows


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


def _collect_values(key, results):
    """Valores no-None de un KPI. Los KPIs opcionales (ej. fill_rate_pct) son
    None en modo estocastico (INIT-5); se filtran en vez de tratarlos como 0.0
    para no ensuciar media/std con un cero que no paso en la realidad."""
    return [r[key] for r in results if r.get(key) is not None]


def _print_run_summary(results):
    print("\n" + "=" * 70)
    print("RESUMEN -- %d replicas" % len(results))
    print("=" * 70)
    for key in ALL_KPI_KEYS + OPTIONAL_KPI_KEYS:
        values = _collect_values(key, results)
        if not values:
            print("%-32s N/A (no disponible en este modo)" % key)
            continue
        s = summarize(values)
        print("%-32s media=%.2f  std=%.2f  IC95=[%.2f, %.2f]" % (
            key, s["mean"], s["std"], s["ci95_low"], s["ci95_high"]))
    print("=" * 70)


def _print_compare_summary(results_a, results_b):
    print("\n" + "=" * 90)
    print("COMPARACION A/B -- %d replicas pareadas por semilla" % len(results_a))
    print("=" * 90)
    for key in ALL_KPI_KEYS + OPTIONAL_KPI_KEYS:
        # AUDIT 2026-07-10: parear por semilla ANTES de filtrar None.
        values_a, values_b = _collect_paired_values(key, results_a, results_b)
        if not values_a or not values_b:
            print("%-32s N/A (no disponible en este modo)" % key)
            continue
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
        summary_rows = []
        for k in ALL_KPI_KEYS + OPTIONAL_KPI_KEYS:
            values = _collect_values(k, results)
            row = {"kpi": k}
            row.update(summarize(values) if values else {"n": 0, "mean": None, "std": None,
                                                           "ci95_low": None, "ci95_high": None})
            summary_rows.append(row)
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Resumen_A", index=False)

        if results_b is not None:
            df_b = pd.DataFrame(results_b)
            df_b.to_excel(writer, sheet_name="Replicas_B", index=False)
            compare_rows = []
            for k in ALL_KPI_KEYS + OPTIONAL_KPI_KEYS:
                # AUDIT 2026-07-10: parear por semilla ANTES de filtrar None.
                values_a, values_b = _collect_paired_values(k, results, results_b)
                if not values_a or not values_b:
                    compare_rows.append({"kpi": k, "mean_a": None, "mean_b": None,
                                          "pvalue": None, "verdict": "N/A (no disponible en este modo)"})
                    continue
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
    pw = ProgressWriter(args.progress_json, "run", args.replicas) if args.progress_json else None
    try:
        results = run_replicas(args.config, args.replicas, args.base_seed,
                                keep_output=args.keep_output,
                                progress_cb=pw.on_replica if pw else None)
    except Exception as e:
        if pw:
            pw.fail(e)
        raise
    _print_run_summary(results)
    if pw:
        pw.finish(build_run_result(results))
    if args.output:
        _export_excel(args.output, results)
    return 0


def cmd_compare(args):
    for path in (args.config_a, args.config_b):
        if not os.path.isfile(path):
            print("[FAIL] No existe el config: %s" % path)
            return 1
    pw = ProgressWriter(args.progress_json, "compare", args.replicas * 2) if args.progress_json else None
    try:
        results_a = run_replicas(args.config_a, args.replicas, args.base_seed,
                                  keep_output=args.keep_output, label="[A] ",
                                  progress_cb=pw.on_replica if pw else None)
        results_b = run_replicas(args.config_b, args.replicas, args.base_seed,
                                  keep_output=args.keep_output, label="[B] ",
                                  progress_cb=pw.on_replica if pw else None)
    except Exception as e:
        if pw:
            pw.fail(e)
        raise
    _print_compare_summary(results_a, results_b)
    if pw:
        pw.finish(build_compare_result(results_a, results_b))
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
    p_run.add_argument("--progress-json", type=str, default=None,
                       help="Path a un JSON de progreso/resultado (para polling desde la web)")
    p_run.set_defaults(func=cmd_run)

    p_cmp = sub.add_parser("compare", help="Compara dos configs con semillas pareadas + veredicto estadistico")
    p_cmp.add_argument("--config-a", required=True, help="Path al config.json A (baseline)")
    p_cmp.add_argument("--config-b", required=True, help="Path al config.json B (variante)")
    p_cmp.add_argument("--replicas", type=int, default=5, help="Numero de replicas pareadas (default 5)")
    p_cmp.add_argument("--base-seed", type=int, default=1000, help="Primera semilla (default 1000)")
    p_cmp.add_argument("--output", type=str, default=None, help="Path .xlsx para exportar resultados")
    p_cmp.add_argument("--keep-output", action="store_true", help="No borrar output/simulation_* de cada replica")
    p_cmp.add_argument("--progress-json", type=str, default=None,
                       help="Path a un JSON de progreso/resultado (para polling desde la web)")
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as e:
        print("[FAIL] %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
