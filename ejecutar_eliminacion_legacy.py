#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE ELIMINACIÓN DE LEGACY - GENERADO AUTOMÁTICAMENTE
"""

from legacy_removal_plan import LegacyRemovalPlan

def main():
    print("ELIMINACIÓN DE CÓDIGO LEGACY")
    print("="*50)
    
    planner = LegacyRemovalPlan()
    
    # Primero hacer dry run
    print("\n1. DRY RUN - Simulación:")
    stats_dry = planner.execute_removal_plan(dry_run=True)
    
    if stats_dry['lines_removed'] > 0:
        print(f"\nSe eliminarían {stats_dry['lines_removed']:,} líneas")
        
        confirm = input("\n¿Proceder con eliminación real? (y/N): ").lower().strip()
        
        if confirm == 'y':
            print("\n2. ELIMINACIÓN REAL:")
            planner_real = LegacyRemovalPlan()
            stats_real = planner_real.execute_removal_plan(dry_run=False)
            
            print(f"\n✅ ELIMINACIÓN COMPLETADA")
            print(f"Archivos eliminados: {stats_real['files_removed']}")
            print(f"Líneas eliminadas: {stats_real['lines_removed']:,}")
        else:
            print("\nEliminación cancelada")
    else:
        print("\nNo hay archivos seguros para eliminar")

if __name__ == "__main__":
    main()
