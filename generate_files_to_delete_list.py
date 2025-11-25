#!/usr/bin/env python3
"""
Script para generar la lista detallada de archivos temporales a eliminar.
Este script NO elimina archivos, solo genera la lista para revisión.
"""
import os
from pathlib import Path

# Directorio base del proyecto
BASE_DIR = Path(__file__).parent

# Categorías de archivos a eliminar
FILES_TO_DELETE = {
    "1. Scripts de Debug (Root)": [
        "debug_assigned_status.py",
        "debug_config_loading.py",
        "debug_config_loading_detailed.py",
        "debug_config_passing.py",
        "debug_dispatcher_config.py",
        "debug_dispatcher_init.py",
        "debug_estrategia.py",
        "debug_event_types.py",
        "debug_execution_flow.py",
        "debug_flujo_estrategia.py",
        "debug_inicializacion_dispatcher.py",
        "debug_initial_state.py",
        "debug_missing_status.py",
        "debug_t40.py",
        "debug_wo_asignadas.py",
        "debug_wo_assignments.py",
        "debug_wo_lifecycle.py",
        "debug_wo_status.py",
    ],
    "2. Scripts de Debug (debug/)": [
        "debug/debug_O_key_press.py",
        "debug/debug_dashboard_state.py",
        "debug/debug_workorder_loading.py",
    ],
    "3. Scripts de Debug (tools/debug/)": [
        "tools/debug/debug_activity_times.py",
        "tools/debug/debug_analytics.py",
        "tools/debug/debug_analytics_detailed.py",
        "tools/debug/debug_analytics_engine.py",
        "tools/debug/debug_calculations.py",
        "tools/debug/debug_event_structure.py",
        "tools/debug/debug_excel_generation.py",
        "tools/debug/debug_exporter.py",
        "tools/debug/debug_exporter_problem.py",
        "tools/debug/debug_normalization.py",
        "tools/debug/debug_null_agent.py",
    ],
    "4. Scripts de Inspección": [
        "inspect_excel.py",
        "inspect_start_event.py",
        "inspect_tmx.py",
    ],
    "5. Scripts de Validación Temporal": [
        "validacion_comportamiento_especifico.py",
        "validacion_estrategia_ejecucion_plan.py",
        "validacion_simple.py",
        "validate_fix_tours.py",
        "validate_multi_staging_discharge.py",
    ],
    "6. Scripts de Test Temporales (Root)": [
        "test_volumen_visual.py",
        "test_wo_decrease.py",
        "reproduce_seek_bug.py",
    ],
    "7. Scripts de Aplicación de Cambios": [
        "apply_all_fixes.py",
        "apply_css_changes.py",
        "apply_fullscreen_changes.py",
    ],
    "8. Scripts de Fix/Remove/Make/Verify": [
        "fix_top_section.py",
        "remove_canvas_borders.py",
        "remove_canvas_margins.py",
        "make_resize_visible.py",
        "verify_replay_loading.py",
    ],
    "9. Archivos de Log": [
        "debug_dispatcher_1760587745.log",
        "final_test.log",
        "og_run.log",
        "og_selector.log",
        "plan_run.log",
        "plan_run_2.log",
        "plan_run_confirm.log",
        "plan_selector.log",
        "replay_test.log",
        "server.log",
        "temp_output.log",
        "temp_output2.log",
        "test_final_run.log",
        "test_output.log",
        "test_output_debug.log",
        "test_output_headless.log",
        "validacion_estrategia.log",
        "validacion_estrategia_completa.log",
    ],
    "10. Archivos de Backup": [
        "config.json.backup",
        "config.json.backup_debug",
        "configurator.py.backup",
        "web_prototype/static/style.css.backup",
    ],
    "11. Archivos de Texto Temporal": [
        "diagnostico_tecla_o.txt",
        "refactored_test.txt",
        "replay_dashboard_test.txt",
    ],
    "12. Documentos Markdown Temporales": [
        "ACTIVE_SESSION_STATE.md",
        "ANALISIS_PROBLEMA_DIVISION_WOS.md",
        "ANALISIS_PROBLEMA_TOURS_CORTOS.md",
        "ANALISIS_VOLUMEN_DASHBOARD.md",
        "AUDITORIA_DASHBOARD_KPIS.md",
        "BUGFIX_DASHBOARD_CARGO_VOLUME.md",
        "HANDOFF.md",
        "INSTRUCCIONES_PARA_SIGUIENTE_CHAT.md",
        "PLAN_DESCARGA_MULTIPLE_STAGINGS.md",
        "PLAN_TRABAJO_TOURS_CORTOS.md",
        "PROBLEMA_DIVISION_WORK_ORDERS.md",
        "PROBLEMA_VOLUMEN_ENCONTRADO.md",
        "RESUMEN_CORRECCION_DASHBOARD_KPIS.md",
        "RESUMEN_FINAL_DASHBOARD_FIX.md",
        "RESUMEN_SESION_ANALISIS_TOURS.md",
        "RESUMEN_SOLUCION_DIVISION_WOS.md",
        "RESUMEN_SOLUCION_VOLUMEN.md",
        "RESUMEN_VALIDACION_IMPLEMENTACION.md",
        "SOLUCION_VOLUMEN_IMPLEMENTADA.md",
        "VALIDACION_VISUAL_DIVISION_WOS.md",
        "test_visual_validation.md",
    ],
    "13. Archivos JSON Temporal": [
        "raw_events_20250826_005756.json",
        "reporte_validacion_estrategia_20251016_005357.json",
    ],
    "14. Archivos Excel de Prueba": [
        "test_after_cache_clear.xlsx",
        "test_excel_output.xlsx",
        "test_final_fix.xlsx",
        "test_fix_excel_output.xlsx",
        "test_fix_excel_output_v2.xlsx",
        "test_simulation_230010.xlsx",
    ],
}

def main():
    """Genera lista de archivos a eliminar y muestra estadísticas."""
    output_file = BASE_DIR / "files_to_delete.txt"
    
    total_files = 0
    existing_files = 0
    missing_files = []
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Lista de Archivos Temporales a Eliminar\n")
        f.write(f"# Generado: {Path(__file__).name}\n")
        f.write(f"# Base directory: {BASE_DIR}\n")
        f.write("#\n")
        f.write("# Esta lista contiene archivos relativos al directorio base.\n")
        f.write("# Los archivos marcados con [MISSING] no existen actualmente.\n")
        f.write("#\n\n")
        
        for category, files in FILES_TO_DELETE.items():
            f.write(f"# {category}\n")
            f.write(f"# Total en categoría: {len(files)}\n")
            
            for file_path in files:
                full_path = BASE_DIR / file_path
                total_files += 1
                
                if full_path.exists():
                    f.write(f"{file_path}\n")
                    existing_files += 1
                else:
                    f.write(f"{file_path} [MISSING]\n")
                    missing_files.append(file_path)
            
            f.write("\n")
        
        # Estadísticas al final
        f.write("#" + "=" * 70 + "\n")
        f.write(f"# ESTADÍSTICAS\n")
        f.write(f"# Total de archivos en lista: {total_files}\n")
        f.write(f"# Archivos existentes: {existing_files}\n")
        f.write(f"# Archivos faltantes: {len(missing_files)}\n")
        f.write("#" + "=" * 70 + "\n")
        
        if missing_files:
            f.write("\n# Archivos que no existen (ya eliminados o nunca creados):\n")
            for missing in missing_files:
                f.write(f"# - {missing}\n")
    
    # Imprimir resumen en consola
    print("=" * 70)
    print("Lista de archivos temporales generada exitosamente")
    print("=" * 70)
    print(f"Archivo de salida: {output_file}")
    print()
    print("ESTADÍSTICAS:")
    print(f"  Total de archivos en lista: {total_files}")
    print(f"  Archivos existentes:        {existing_files}")
    print(f"  Archivos faltantes:         {len(missing_files)}")
    print()
    
    if missing_files:
        print(f"⚠️  {len(missing_files)} archivos de la lista no existen actualmente.")
        print("   Esto podría significar que ya fueron eliminados o nunca se crearon.")
        print()
        print("Archivos faltantes:")
        for missing in missing_files[:10]:  # Mostrar primeros 10
            print(f"  - {missing}")
        if len(missing_files) > 10:
            print(f"  ... y {len(missing_files) - 10} más")
    else:
        print("✅ Todos los archivos en la lista existen actualmente.")
    
    print()
    print("=" * 70)
    print("PRÓXIMOS PASOS:")
    print("1. Revisar el archivo 'files_to_delete.txt'")
    print("2. Verificar que la lista es correcta")
    print("3. Crear backup del proyecto antes de eliminar")
    print("4. Seguir el plan de verificación del implementation_plan.md")
    print("=" * 70)

if __name__ == "__main__":
    main()
