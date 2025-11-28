# -*- coding: utf-8 -*-
"""
Run Optimization - Entry point para optimización automática de warehouse.

Ejecuta estudios de optimización usando Optuna para encontrar la configuración
óptima de recursos (operarios terrestres, montacargas) y estrategias de despacho
que maximizan eficiencia operativa (throughput / costo).

Uso:
    python entry_points/run_optimization.py --config config.json --n-trials 100
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add project root and src/ to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(1, os.path.join(project_root, 'src'))

# Import optimizer
from src.tools.optimizer import SimulationOptimizer


def main():
    """Función principal - Lanza estudio de optimización."""
    
    parser = argparse.ArgumentParser(
        description="Warehouse Configuration Optimizer - Automated Parameter Tuning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Optimización básica con 100 trials y 4 jobs paralelos
  python run_optimization.py --config config.json --n-trials 100 --n-jobs 4
  
  # Optimización con estudio nombrado (pausable/reanudable)
  python run_optimization.py --study-name warehouse_opt_v1 --n-trials 50
  
  # Continuar estudio existente
  python run_optimization.py --study-name warehouse_opt_v1 --n-trials 50
  
  # Optimización serial (sin paralelización, para debugging)
  python run_optimization.py --n-trials 20 --n-jobs 1
  
  # Con costos personalizados
  python run_optimization.py --cost-ground 20 --cost-forklift 60 --n-trials 100
        """
    )
    
    # Config de simulación
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path al config.json base usado como template (default: config.json)'
    )
    
    # Parámetros de optimización
    parser.add_argument(
        '--n-trials',
        type=int,
        default=100,
        help='Número de trials a ejecutar (default: 100)'
    )
    
    parser.add_argument(
        '--n-jobs',
        type=int,
        default=4,
        help='Número de simulaciones en paralelo (default: 4, usar 1 para serial)'
    )
    
    parser.add_argument(
        '--study-name',
        type=str,
        default='warehouse_optimization',
        help='Nombre del estudio Optuna (default: warehouse_optimization)'
    )
    
    parser.add_argument(
        '--storage',
        type=str,
        default='sqlite:///optuna_study.db',
        help='URL de storage Optuna (default: sqlite:///optuna_study.db)'
    )
    
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='No limpiar archivos temporales al finalizar (útil para debugging)'
    )
    
    # Parámetros de función de costo
    parser.add_argument(
        '--cost-ground',
        type=float,
        default=15.0,
        help='Costo operativo por operario terrestre ($/hora, default: 15.0)'
    )
    
    parser.add_argument(
        '--cost-forklift',
        type=float,
        default=50.0,
        help='Costo operativo por montacargas ($/hora, default: 50.0)'
    )
    
    parser.add_argument(
        '--penalty-failed',
        type=float,
        default=100.0,
        help='Penalización por WorkOrder fallida ($, default: 100.0)'
    )
    
    args = parser.parse_args()
    
    # Banner
    print("\n" + "="*70)
    print("   WAREHOUSE CONFIGURATION OPTIMIZER - GEMELO DIGITAL")
    print("="*70)
    print(f"  Config base:      {args.config}")
    print(f"  Study name:       {args.study_name}")
    print(f"  Trials:           {args.n_trials}")
    print(f"  Parallel jobs:    {args.n_jobs}")
    print(f"  Storage:          {args.storage}")
    print(f"  Cleanup:          {not args.no_cleanup}")
    print(f"  Cost config:      Ground=${args.cost_ground}/h, Forklift=${args.cost_forklift}/h")
    print(f"  Penalty failed:   ${args.penalty_failed}/WO")
    print("="*70)
    
    # Validar que config existe
    if not os.path.exists(args.config):
        print(f"\n[ERROR] Config file not found: {args.config}")
        print("Please specify a valid config file with --config")
        return 1
    
    try:
        # Crear optimizador
        optimizer = SimulationOptimizer(
            base_config_path=args.config,
            n_parallel_jobs=args.n_jobs,
            cost_ground_operator=args.cost_ground,
            cost_forklift=args.cost_forklift,
            penalty_failed_wo=args.penalty_failed
        )
        
        # Ejecutar optimización
        result = optimizer.optimize(
            n_trials=args.n_trials,
            study_name=args.study_name,
            storage=args.storage,
            load_if_exists=True,
            cleanup=not args.no_cleanup
        )
        
        # Si fue interrumpido
        if result.get('interrupted'):
            print(f"\n[INFO] Optimization interrupted. Resume with:")
            print(f"  python run_optimization.py --study-name {args.study_name} --n-trials {args.n_trials}")
            return 0
        
        # Guardar mejor configuración
        os.makedirs("optimized_configs", exist_ok=True)
        timestamp = result.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        best_config_filename = os.path.join("optimized_configs", f"config_optimized_{timestamp}.json")
        
        # Cargar config base y aplicar best params
        with open(args.config, 'r', encoding='utf-8') as f:
            base_config = json.load(f)
        
        optimized_config = base_config.copy()
        optimized_config.update(result['best_params'])
        
        # Ajustar num_operarios_total
        optimized_config['num_operarios_total'] = (
            result['best_params']['num_operarios_terrestres'] +
            result['best_params']['num_montacargas']
        )
        
        # Guardar config optimizado
        with open(best_config_filename, 'w', encoding='utf-8') as f:
            json.dump(optimized_config, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*70)
        print("   OPTIMIZATION SUMMARY")
        print("="*70)
        print(f"  Best score:       {result['best_score']:.4f}")
        print(f"  Best trial:       #{result['best_trial_number']}")
        print(f"  Total trials:     {result['n_trials']}")
        print(f"\n  Best Parameters:")
        for key, value in result['best_params'].items():
            print(f"    {key}: {value}")
        print(f"\n  Optimized config saved to: {best_config_filename}")
        print(f"  Study database: {args.storage.replace('sqlite:///', '')}")
        print("="*70)
        
        # Sugerencias finales
        print("\n[TIP] View study with Optuna Dashboard:")
        print(f"  pip install optuna-dashboard")
        print(f"  optuna-dashboard {args.storage.replace('sqlite:///', '')}")
        print(f"\n[TIP] Test optimized config:")
        print(f"  python entry_points/run_generate_replay.py --config {best_config_filename}")
        
        return 0
    
    except KeyboardInterrupt:
        print("\n[INFO] Optimization interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n[ERROR] Optimization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
