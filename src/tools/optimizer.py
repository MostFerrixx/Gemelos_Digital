# -*- coding: utf-8 -*-
"""
Simulation Optimizer - Optimización automática de configuración de warehouse usando Optuna.

Este módulo implementa el orquestador de optimización que ejecuta múltiples simulaciones
en paralelo, ajustando hiperparámetros (num_operarios_terrestres, num_montacargas, dispatch_strategy)
para maximizar la eficiencia operativa (throughput / costo).

Autor: Gemelos Digital
Versión: 1.0.0
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import optuna
from optuna.samplers import TPESampler


class SimulationOptimizer:
    """
    Optimizador automático de configuración de warehouse usando Optuna.
   
    Orquesta múltiples ejecuciones de simulación headless, ajustando hiperparámetros
    para maximizar eficiencia operativa definida como: Throughput / (Costo + Penalizaciones).
    
    Features:
    - Paralelización nativa con n_jobs
    - Almacenamiento persistente SQLite (estudios pausables/reanudables)
    - Manejo robusto de errores (simulaciones fallidas)
    - Limpieza automática de archivos temporales
    - Logging detallado de progreso
    """
    
    def __init__(
        self,
        base_config_path: str = "config.json",
        n_parallel_jobs: int = 4,
        cost_ground_operator: float = 15.0,
        cost_forklift: float = 50.0,
        penalty_failed_wo: float = 100.0
    ):
        """
        Inicializa el optimizador de simulación.
        
        Args:
            base_config_path: Path al config.json base que se usará como template
            n_parallel_jobs: Número de simulaciones en paralelo (recomendado: 2-4)
            cost_ground_operator: Costo operativo por operario terrestre ($/hora)
            cost_forklift: Costo operativo por montacargas ($/hora, incluye operador + equipo)
            penalty_failed_wo: Penalización por cada WorkOrder fallida ($)
        """
        self.base_config_path = base_config_path
        self.n_jobs = n_parallel_jobs
        
        # Parámetros de la función de costo
        self.COST_GROUND_OP = cost_ground_operator
        self.COST_FORKLIFT = cost_forklift
        self.PENALTY_FAILED_WO = penalty_failed_wo
        
        # Cargar configuración base
        if not os.path.exists(base_config_path):
            raise FileNotFoundError(f"Config file not found: {base_config_path}")
        
        with open(base_config_path, 'r', encoding='utf-8') as f:
            self.base_config = json.load(f)
        
        # Directorios temporales
        self.temp_configs_dir = "temp_configs"
        self.temp_metrics_dir = "temp_metrics"
        
        # Directorio para configs optimizados
        self.optimized_configs_dir = "optimized_configs"
        os.makedirs(self.optimized_configs_dir, exist_ok=True)
        
        # Timestamp para esta sesión de optimización
        self.optimization_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print(f"[OPTIMIZER] Inicializado")
        print(f"  Config base: {base_config_path}")
        print(f"  Jobs paralelos: {n_parallel_jobs}")
        print(f"  Costos: Ground=${self.COST_GROUND_OP}/h, Forklift=${self.COST_FORKLIFT}/h")
        print(f"  Penalización fallos: ${self.PENALTY_FAILED_WO}/WO")
    
    def objective(self, trial: optuna.Trial) -> float:
        """
        Función objetivo que Optuna optimizará.
        
        Flujo:
        1. Optuna sugiere parámetros (num_operarios, num_montacargas, dispatch_strategy)
        2. Genera config temporal con esos parámetros
        3. Ejecuta simulación headless como subprocess
        4. Lee metrics_output.json generado
        5. Calcula y retorna score
        
        Args:
            trial: Trial de Optuna con parámetros sugeridos
            
        Returns:
            float: Score a maximizar (throughput / costo)
        """
        # 1. Optuna sugiere parámetros
        n_ground = trial.suggest_int("num_operarios_terrestres", 1, 20)
        n_forklifts = trial.suggest_int("num_montacargas", 1, 10)
        
        # Dispatch strategies disponibles (ajustar según sistema)
        dispatch_strategy = trial.suggest_categorical(
            "dispatch_strategy",
            [
                "Ejecucion de Plan (Filtro por Prioridad)",
                "FIFO Simple",
                "Proximity-Based",
            ]
        )
        
        # 2. Generar config temporal
        trial_config = self.base_config.copy()
        trial_config["num_operarios_terrestres"] = n_ground
        trial_config["num_montacargas"] = n_forklifts
        trial_config["dispatch_strategy"] = dispatch_strategy
        
        # Ajustar num_operarios_total (suma de terrestres + montacargas)
        trial_config["num_operarios_total"] = n_ground + n_forklifts
        
        # Paths temporales
        os.makedirs(self.temp_configs_dir, exist_ok=True)
        os.makedirs(self.temp_metrics_dir, exist_ok=True)
        
        config_path = os.path.join(self.temp_configs_dir, f"trial_{trial.number}.json")
        metrics_path = os.path.join(self.temp_metrics_dir, f"trial_{trial.number}_metrics.json")
        
        # Guardar config temporal
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(trial_config, f, indent=2, ensure_ascii=False)
        
        # 3. Ejecutar simulación headless
        print(f"\n[OPTIMIZER] Trial {trial.number}: Ground={n_ground}, Forklifts={n_forklifts}, Strategy={dispatch_strategy}")
        
        cmd = [
            sys.executable,  # Usar el mismo intérprete Python
            "entry_points/run_generate_replay.py",
            "--config", config_path,
            "--output-metrics", metrics_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # Timeout de 10 minutos por simulación
            )
            
            if result.returncode != 0:
                print(f"[OPTIMIZER] Trial {trial.number} FAILED (returncode={result.returncode})")
                print(f"  stderr: {result.stderr[:500]}")  # Primeros 500 caracteres del error
                return 0.0  # Score mínimo para trials fallidos
            
        except subprocess.TimeoutExpired:
            print(f"[OPTIMIZER] Trial {trial.number} TIMEOUT (>10min)")
            return 0.0
        
        except Exception as e:
            print(f"[OPTIMIZER] Trial {trial.number} ERROR: {e}")
            return 0.0
        
        # 4. Leer métricas
        if not os.path.exists(metrics_path):
            print(f"[OPTIMIZER] Trial {trial.number} ERROR: Metrics file not found")
            return 0.0
        
        try:
            with open(metrics_path, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
        except Exception as e:
            print(f"[OPTIMIZER] Trial {trial.number} ERROR reading metrics: {e}")
            return 0.0
        
        # 5. Calcular score
        score = self.calculate_score(metrics)
        
        # 6. Log adicional para Optuna (user attributes)
        trial.set_user_attr("completed_wo", metrics["total_workorders_completed"])
        trial.set_user_attr("failed_wo", metrics["total_workorders_failed"])
        trial.set_user_attr("simulation_time", metrics["total_simulation_time_seconds"])
        trial.set_user_attr("total_cost_per_hour", n_ground * self.COST_GROUND_OP + n_forklifts * self.COST_FORKLIFT)
        
        print(f"[OPTIMIZER] Trial {trial.number} SCORE: {score:.4f}")
        print(f"  Completed: {metrics['total_workorders_completed']}/{metrics['total_workorders']}")
        print(f"  Sim time: {metrics['total_simulation_time_seconds']:.1f}s")
        
        return score
    
    def calculate_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calcula score de optimización según fórmula de negocio.
        
        Fórmula: Throughput (WO/hora) / (Costo Operativo Total/hora + Penalización Fallos)
        
        Objetivo: MAXIMIZAR el score (más WO completadas por dólar invertido).
        
        Args:
            metrics: Dict con métricas de la simulación
            
        Returns:
            float: Score positivo. Mayor = mejor configuración.
        """
        # Validar métricas
        if metrics["total_simulation_time_seconds"] == 0:
            return 0.0
        
        # Throughput (WO completadas por hora)
        throughput = (
            metrics["total_workorders_completed"] / 
            metrics["total_simulation_time_seconds"]
        ) * 3600  # Convertir a WO/hora
        
        # Costo operativo ($/hora)
        total_cost_per_hour = (
            metrics["resource_costs"]["ground_operators"] * self.COST_GROUND_OP +
            metrics["resource_costs"]["forklifts"] * self.COST_FORKLIFT
        )
        
        # Penalización por órdenes fallidas
        failure_penalty = metrics["total_workorders_failed"] * self.PENALTY_FAILED_WO
        
        # Score final
        denominator = total_cost_per_hour + failure_penalty
        if denominator <= 0:
            return 0.0
        
        score = throughput / denominator
        
        return score
    
    def optimize(
        self,
        n_trials: int = 100,
        study_name: str = "warehouse_optimization",
        storage: str = "sqlite:///optuna_study.db",
        load_if_exists: bool = True,
        cleanup: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta estudio de optimización con Optuna.
        
        Args:
            n_trials: Número de trials a ejecutar
            study_name: Nombre del estudio (para persistencia)
            storage: URL de almacenamiento (SQLite u otro backend)
            load_if_exists: Si True, carga estudio existente en vez de crear uno nuevo
            cleanup: Si True, limpia archivos temporales al finalizar
            
        Returns:
            Dict con resultados: best_params, best_score, study_name, n_trials
        """
        print("\n" + "="*60)
        print("OPTIMIZATION STUDY - GEMELO DIGITAL")
        print("="*60)
        print(f"Study name: {study_name}")
        print(f"Trials: {n_trials}")
        print(f"Parallel jobs: {self.n_jobs}")
        print(f"Storage: {storage}")
        print("="*60)
        
        try:
            # Crear/cargar estudio
            study = optuna.create_study(
                study_name=study_name,
                storage=storage,
                direction="maximize",  # Maximizar el score
                sampler=TPESampler(seed=42),
                load_if_exists=load_if_exists
            )
            
            # Warm-start: Sugerir config actual como primer trial
            if len(study.trials) == 0:
                print("\n[OPTIMIZER] Warm-start: Enqueuing current config as baseline...")
                study.enqueue_trial({
                    "num_operarios_terrestres": self.base_config.get("num_operarios_terrestres", 2),
                    "num_montacargas": self.base_config.get("num_montacargas", 1),
                    "dispatch_strategy": self.base_config.get("dispatch_strategy", "Ejecucion de Plan (Filtro por Prioridad)")
                })
            
            # Ejecutar optimización
            print(f"\n[OPTIMIZER] Starting optimization with {self.n_jobs} parallel jobs...")
            print("[OPTIMIZER] Press Ctrl+C to stop gracefully (progress will be saved)\n")
            
            study.optimize(
                self.objective,
                n_trials=n_trials,
                n_jobs=self.n_jobs,  # Paralelización
                show_progress_bar=True,
                catch=(Exception,)  # Continuar si un trial falla
            )
            
            # Resultados
            print("\n" + "="*60)
            print("OPTIMIZATION COMPLETED")
            print("="*60)
            print(f"Best score: {study.best_value:.4f}")
            print(f"Best params:")
            for key, value in study.best_params.items():
                print(f"  {key}: {value}")
            print(f"Total trials completed: {len(study.trials)}")
            print("="*60)
            
            result = {
                "best_params": study.best_params,
                "best_score": study.best_value,
                "best_trial_number": study.best_trial.number,
                "n_trials": len(study.trials),
                "study_name": study_name,
                "timestamp": self.optimization_timestamp
            }
            
            return result
        
        except KeyboardInterrupt:
            print("\n[OPTIMIZER] Interrupted by user. Progress saved to database.")
            print(f"[OPTIMIZER] Resume with: --study-name {study_name}")
            return {
                "interrupted": True,
                "study_name": study_name,
                "trials_completed": len(study.trials) if 'study' in locals() else 0
            }
        
        finally:
            # Cleanup archivos temporales
            if cleanup:
                self._cleanup_temp_files()
    
    def _cleanup_temp_files(self):
        """Limpia archivos temporales generados durante optimización."""
        dirs_to_clean = [self.temp_configs_dir, self.temp_metrics_dir]
        
        for dir_path in dirs_to_clean:
            if os.path.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                    print(f"[OPTIMIZER] Cleaned: {dir_path}/")
                except Exception as e:
                    print(f"[OPTIMIZER] Warning: Could not clean {dir_path}: {e}")


# Export
__all__ = ['SimulationOptimizer']
