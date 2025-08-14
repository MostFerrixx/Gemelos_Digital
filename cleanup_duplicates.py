# -*- coding: utf-8 -*-
"""
Script de limpieza de archivos duplicados identificados en el análisis de optimización.
USAR CON PRECAUCIÓN - Hace backup antes de eliminar.
"""

import os
import shutil
import datetime
from pathlib import Path

class DuplicateCleanup:
    """Limpiador seguro de archivos duplicados"""
    
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.backup_dir = self.base_path / "backup_duplicates"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Archivos identificados como duplicados o legacy
        self.files_to_remove = [
            # Pathfinding duplicados
            "pathfinding_enhanced.py",  # Solo 24 líneas, funcionalidad en pathfinding.py
            "pathfinding_replacement.py",  # Solo 24 líneas, obsoleto
            "debug_pathfinding.py",  # Script de debug temporal
            "pathfinding_comparison.py",  # Script de análisis temporal
            "safe_pathfinding_replacement.py",  # Implementación duplicada
            
            # Mover por ruta duplicados
            "mover_por_ruta_mejorado.py",  # Duplicado, existe en git/simulation/
            
            # Operators backup
            "git/simulation/operators_backup.py",  # Backup innecesario
            
            # Pathfinding managers duplicados
            "pathfinding_manager.py",  # Duplicado, existe en git/simulation/
            
            # Test files obsoletos (mantener solo algunos principales)
            "test_enhanced_window.py",  # Test temporal
            "quick_visual_test.py",  # Test temporal
            
            # Calibrators duplicados (mantener solo enhanced_calibrator.py)
            "improved_calibrator.py",
            "coordinate_calibrator.py",
            
            # Análisis temporales
            "analyze_failed_cases.py",
            "simple_analysis.py",
            "legacy_analysis.py",
            
            # Scripts de migración completados
            "activar_sistema_mejorado.py",
            "ejecutar_eliminacion_legacy.py",
            "rollback_sistema.py",
            "legacy_removal_plan.py",
        ]
        
        # Archivos a consolidar (no eliminar, pero documentar)
        self.files_to_consolidate = [
            "operators_integration.py",  # Consolidar con git/simulation/operators.py
            "dynamic_pathfinding_integration.py",  # Revisar si se puede simplificar
            "validate_tmx_pathfinding.py",  # Mover a carpeta de tests
            "visual_pathfinding_demo.py",  # Mover a carpeta de demos
        ]
    
    def create_backup(self, file_path):
        """Crea backup de un archivo antes de eliminarlo"""
        try:
            rel_path = file_path.relative_to(self.base_path)
            backup_path = self.backup_dir / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(file_path, backup_path)
            print(f"Backup creado: {backup_path}")
            return True
        except Exception as e:
            print(f"✗ Error creando backup para {file_path}: {e}")
            return False
    
    def remove_duplicate_files(self, dry_run=True):
        """Elimina archivos duplicados (con opción de dry-run)"""
        print(f"{'=== DRY RUN ===' if dry_run else '=== ELIMINACIÓN REAL ==='}")
        print(f"Directorio base: {self.base_path}")
        print(f"Directorio backup: {self.backup_dir}")
        print()
        
        removed_count = 0
        failed_count = 0
        total_size_saved = 0
        
        for file_rel in self.files_to_remove:
            file_path = self.base_path / file_rel
            
            if file_path.exists():
                file_size = file_path.stat().st_size
                total_size_saved += file_size
                
                print(f"📁 Procesando: {file_rel} ({file_size} bytes)")
                
                if not dry_run:
                    # Crear backup primero
                    if self.create_backup(file_path):
                        try:
                            file_path.unlink()
                            print(f"✓ Eliminado: {file_rel}")
                            removed_count += 1
                        except Exception as e:
                            print(f"✗ Error eliminando {file_rel}: {e}")
                            failed_count += 1
                    else:
                        print(f"✗ No se pudo crear backup para {file_rel}, omitiendo eliminación")
                        failed_count += 1
                else:
                    print(f"  → Se eliminaría: {file_rel}")
                    removed_count += 1
            else:
                print(f"⚠️  No encontrado: {file_rel}")
        
        print(f"\n{'=' * 50}")
        print(f"Resumen:")
        print(f"  Archivos procesados: {removed_count}")
        print(f"  Errores: {failed_count}")
        print(f"  Espacio liberado: {total_size_saved / 1024:.1f} KB")
        
        if dry_run:
            print(f"\n🔍 Esto fue un DRY RUN. Para eliminar realmente, ejecuta:")
            print(f"   cleanup.remove_duplicate_files(dry_run=False)")
    
    def analyze_consolidation_candidates(self):
        """Analiza archivos candidatos para consolidación"""
        print("🔍 ANÁLISIS DE CONSOLIDACIÓN")
        print("=" * 50)
        
        for file_rel in self.files_to_consolidate:
            file_path = self.base_path / file_rel
            
            if file_path.exists():
                file_size = file_path.stat().st_size
                lines = self._count_lines(file_path)
                
                print(f"\n📄 {file_rel}")
                print(f"   Tamaño: {file_size} bytes")
                print(f"   Líneas: {lines}")
                print(f"   Recomendación: Revisar para consolidación")
            else:
                print(f"⚠️  No encontrado: {file_rel}")
    
    def _count_lines(self, file_path):
        """Cuenta líneas en un archivo"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except:
            return "Error"
    
    def generate_cleanup_report(self):
        """Genera reporte detallado de limpieza"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.base_path / f"cleanup_report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Reporte de Limpieza de Archivos Duplicados\n\n")
            f.write(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Archivos Eliminados\n\n")
            for file_rel in self.files_to_remove:
                file_path = self.base_path / file_rel
                status = "✓ Existe" if file_path.exists() else "⚠️ No encontrado"
                f.write(f"- `{file_rel}` - {status}\n")
            
            f.write("\n## Archivos para Consolidación\n\n")
            for file_rel in self.files_to_consolidate:
                file_path = self.base_path / file_rel
                status = "✓ Existe" if file_path.exists() else "⚠️ No encontrado"
                f.write(f"- `{file_rel}` - {status}\n")
            
            f.write("\n## Beneficios Esperados\n\n")
            f.write("- Reducción del número de archivos duplicados\n")
            f.write("- Menor confusión en el mantenimiento del código\n")
            f.write("- Estructura de proyecto más limpia\n")
            f.write("- Reducción del tiempo de indexación en IDEs\n")
        
        print(f"📋 Reporte generado: {report_path}")
        return report_path

def main():
    """Función principal del script de limpieza"""
    base_path = Path(__file__).parent
    cleanup = DuplicateCleanup(base_path)
    
    print("LIMPIEZA DE ARCHIVOS DUPLICADOS")
    print("=" * 50)
    print()
    
    # Generar reporte
    cleanup.generate_cleanup_report()
    print()
    
    # Análisis de consolidación
    cleanup.analyze_consolidation_candidates()
    print()
    
    # Dry run de eliminación
    cleanup.remove_duplicate_files(dry_run=True)
    print()
    
    print("💡 Próximos pasos:")
    print("   1. Revisar archivos en backup_duplicates/")
    print("   2. Ejecutar cleanup.remove_duplicate_files(dry_run=False) si está de acuerdo")
    print("   3. Consolidar archivos listados en files_to_consolidate")

if __name__ == "__main__":
    main()