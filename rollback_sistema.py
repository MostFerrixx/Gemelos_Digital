#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROLLBACK SISTEMA - Volver al pathfinding original
"""

import sys
import os
import shutil

def rollback_sistema():
    """Volver al sistema original"""
    
    print("="*60)
    print("ROLLBACK AL SISTEMA ORIGINAL")
    print("="*60)
    
    try:
        backup_path = "git/simulation/operators_backup.py"
        operators_path = "git/simulation/operators.py"
        
        if os.path.exists(backup_path):
            # Restaurar archivo original
            shutil.copy2(backup_path, operators_path)
            print("✅ operators.py restaurado desde backup")
            
            # Mostrar qué cambió
            print(f"\nCambio revertido:")
            print(f"- from mover_por_ruta_mejorado import mover_por_ruta_realista")
            print(f"+ from utils.pathfinding import mover_por_ruta_realista")
            
            print(f"\n✅ ROLLBACK COMPLETADO")
            print(f"El simulador usará el sistema original")
            
            return True
        else:
            print("❌ No se encontró backup - operators_backup.py")
            print("Verifica que el archivo exista en git/simulation/")
            return False
            
    except Exception as e:
        print(f"❌ Error en rollback: {e}")
        return False

if __name__ == "__main__":
    rollback_sistema()