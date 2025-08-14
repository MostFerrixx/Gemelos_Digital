#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLAN DE ELIMINACIÓN DE CÓDIGO LEGACY - Específico y Seguro
"""

import os
import shutil
from datetime import datetime

class LegacyRemovalPlan:
    """Plan de eliminación de código legacy específico y seguro"""
    
    def __init__(self):
        self.base_path = "git"
        self.backup_path = "backup_legacy"
        self.removal_candidates = []
        self.stats = {'lines_removed': 0, 'files_removed': 0}
        
    def analyze_specific_legacy_files(self):
        """Analizar archivos específicos que sabemos son legacy"""
        
        print("ANÁLISIS ESPECÍFICO DE ARCHIVOS LEGACY")
        print("="*50)
        
        # Lista específica de archivos que sabemos contienen código legacy
        legacy_files = [
            {
                'path': 'git/utils/pathfinding.py',
                'reason': 'Sistema A* original reemplazado por enhanced_calibrator',
                'lines_estimate': 909,
                'priority': 'HIGH',
                'safe_to_remove': True,
                'replacement': 'enhanced_calibrator.py + pathfinding_manager.py'
            },
            {
                'path': 'git/utils/strict_lane_system.py', 
                'reason': 'Sistema de carriles complejo, parcialmente reemplazado',
                'lines_estimate': 1610,
                'priority': 'MEDIUM',
                'safe_to_remove': False,  # Todavía usado por operarios
                'replacement': 'Revisar uso actual antes de eliminar'
            },
            {
                'path': 'git/utils/collision.py',
                'reason': 'Sistema de colisiones legacy',
                'lines_estimate': 547,
                'priority': 'LOW', 
                'safe_to_remove': False,  # Verificar si se usa
                'replacement': 'Incorporado en pathfinding mejorado'
            },
            {
                'path': 'git/config/window_config.py',
                'reason': 'Configuración ventanas, parcialmente legacy',
                'lines_estimate': 698,
                'priority': 'LOW',
                'safe_to_remove': False,  # Configuración puede ser necesaria
                'replacement': 'Mantener partes necesarias'
            }
        ]
        
        print(f"Archivos candidatos para eliminación:")
        print("-" * 40)
        
        total_removable = 0
        immediate_removal = []
        
        for i, file_info in enumerate(legacy_files, 1):
            path = file_info['path']
            exists = os.path.exists(path)
            status = "EXISTE" if exists else "NO ENCONTRADO"
            
            print(f"{i}. {os.path.basename(path)}")
            print(f"   Ruta: {path}")
            print(f"   Estado: {status}")
            print(f"   Líneas estimadas: {file_info['lines_estimate']}")
            print(f"   Prioridad: {file_info['priority']}")
            print(f"   Seguro eliminar: {'SÍ' if file_info['safe_to_remove'] else 'NO'}")
            print(f"   Razón: {file_info['reason']}")
            print(f"   Reemplazo: {file_info['replacement']}")
            
            if exists and file_info['safe_to_remove']:
                immediate_removal.append(file_info)
                total_removable += file_info['lines_estimate']
            
            print()
        
        print(f"RESUMEN:")
        print(f"- Archivos eliminables inmediatamente: {len(immediate_removal)}")
        print(f"- Líneas eliminables: {total_removable:,}")
        
        return immediate_removal
    
    def create_backup(self, file_path):
        """Crear backup de archivo antes de eliminación"""
        
        if not os.path.exists(self.backup_path):
            os.makedirs(self.backup_path)
        
        if os.path.exists(file_path):
            backup_name = os.path.basename(file_path) + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_full_path = os.path.join(self.backup_path, backup_name)
            
            shutil.copy2(file_path, backup_full_path)
            print(f"   Backup creado: {backup_full_path}")
            return backup_full_path
        
        return None
    
    def remove_legacy_file_safe(self, file_info, dry_run=True):
        """Eliminar archivo legacy de forma segura"""
        
        file_path = file_info['path']
        
        if not os.path.exists(file_path):
            print(f"   SKIP: {file_path} no existe")
            return False
        
        # Contar líneas reales
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
        except:
            lines = file_info['lines_estimate']
        
        print(f"   Procesando: {os.path.basename(file_path)} ({lines} líneas)")
        
        if not dry_run:
            # Crear backup
            backup_path = self.create_backup(file_path)
            
            if backup_path:
                # Eliminar archivo
                os.remove(file_path)
                print(f"   ELIMINADO: {file_path}")
                
                self.stats['files_removed'] += 1
                self.stats['lines_removed'] += lines
                return True
        else:
            print(f"   DRY RUN: {file_path} sería eliminado ({lines} líneas)")
            self.stats['lines_removed'] += lines
        
        return True
    
    def execute_removal_plan(self, dry_run=True):
        """Ejecutar plan de eliminación"""
        
        print("="*60)
        print(f"EJECUCIÓN PLAN DE ELIMINACIÓN {'(DRY RUN)' if dry_run else '(REAL)'}")
        print("="*60)
        
        # Obtener archivos eliminables
        immediate_removal = self.analyze_specific_legacy_files()
        
        if not immediate_removal:
            print("No hay archivos seguros para eliminar inmediatamente")
            return
        
        print(f"\nPROCESANDO {len(immediate_removal)} ARCHIVOS:")
        print("-" * 30)
        
        for file_info in immediate_removal:
            success = self.remove_legacy_file_safe(file_info, dry_run)
            if success:
                print(f"   ✅ {os.path.basename(file_info['path'])}")
            else:
                print(f"   ❌ {os.path.basename(file_info['path'])}")
        
        print(f"\n{'='*60}")
        print("RESUMEN DE ELIMINACIÓN")
        print("="*60)
        print(f"Archivos {'que serían' if dry_run else ''} eliminados: {len(immediate_removal)}")
        print(f"Líneas {'que serían' if dry_run else ''} eliminadas: {self.stats['lines_removed']:,}")
        
        if not dry_run:
            print(f"Backups creados en: {self.backup_path}")
        
        return self.stats
    
    def create_removal_script(self):
        """Crear script de eliminación ejecutable"""
        
        script_content = '''#!/usr/bin/env python3
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
    print("\\n1. DRY RUN - Simulación:")
    stats_dry = planner.execute_removal_plan(dry_run=True)
    
    if stats_dry['lines_removed'] > 0:
        print(f"\\nSe eliminarían {stats_dry['lines_removed']:,} líneas")
        
        confirm = input("\\n¿Proceder con eliminación real? (y/N): ").lower().strip()
        
        if confirm == 'y':
            print("\\n2. ELIMINACIÓN REAL:")
            planner_real = LegacyRemovalPlan()
            stats_real = planner_real.execute_removal_plan(dry_run=False)
            
            print(f"\\n✅ ELIMINACIÓN COMPLETADA")
            print(f"Archivos eliminados: {stats_real['files_removed']}")
            print(f"Líneas eliminadas: {stats_real['lines_removed']:,}")
        else:
            print("\\nEliminación cancelada")
    else:
        print("\\nNo hay archivos seguros para eliminar")

if __name__ == "__main__":
    main()
'''
        
        with open('ejecutar_eliminacion_legacy.py', 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print("Script de eliminación creado: ejecutar_eliminacion_legacy.py")

def main():
    """Crear plan de eliminación completo"""
    print("="*60)
    print("PLANIFICADOR DE ELIMINACIÓN LEGACY")
    print("="*60)
    
    planner = LegacyRemovalPlan()
    
    # Analizar archivos
    print("\n1. Analizando archivos legacy específicos...")
    immediate_removal = planner.analyze_specific_legacy_files()
    
    # Crear script ejecutable
    print("\n2. Creando script de eliminación...")
    planner.create_removal_script()
    
    # Hacer dry run
    print("\n3. Ejecutando simulación (dry run)...")
    stats = planner.execute_removal_plan(dry_run=True)
    
    print(f"\n✅ PLAN DE ELIMINACIÓN COMPLETADO")
    print(f"Archivos identificados: {len(immediate_removal)}")
    print(f"Líneas eliminables: {stats['lines_removed']:,}")
    
    print(f"\nPara ejecutar eliminación real:")
    print(f"python ejecutar_eliminacion_legacy.py")
    
    return planner

if __name__ == "__main__":
    planner = main()