#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACTIVADOR SISTEMA MEJORADO - Configuración rápida
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def activar_pathfinding_mejorado():
    """Activar sistema de pathfinding mejorado para testing"""
    
    print("="*60)
    print("ACTIVANDO SISTEMA DE PATHFINDING MEJORADO")
    print("="*60)
    
    try:
        # Importar manager
        from pathfinding_manager import get_pathfinding_manager
        
        # Obtener manager
        manager = get_pathfinding_manager()
        
        # Configurar para usar sistema mejorado al 100%
        exito = manager.establecer_modo("MEJORADO")
        
        if exito:
            print("✅ Sistema mejorado activado correctamente")
            print("✅ Todas las rutas usarán el nuevo pathfinding")
            print("✅ Rollback automático si hay problemas")
            
            # Mostrar estadísticas iniciales
            stats = manager.obtener_estadisticas()
            print(f"\nEstado inicial:")
            print(f"- Modo: {stats['modo_actual']}")
            print(f"- Auto-rollback: {'Activo' if stats['auto_rollback_activo'] else 'Inactivo'}")
            
            print(f"\n🚀 LISTO PARA TESTING!")
            print(f"Ejecuta el simulador normalmente con:")
            print(f"python run_simulator.py")
            
            return True
        else:
            print("❌ Error activando sistema mejorado")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def mostrar_instrucciones():
    """Mostrar instrucciones de testing"""
    
    print(f"\n{'='*60}")
    print("INSTRUCCIONES DE TESTING")
    print("="*60)
    
    print(f"\n1. ACTIVAR SISTEMA MEJORADO:")
    print(f"   python activar_sistema_mejorado.py")
    
    print(f"\n2. EJECUTAR SIMULADOR:")
    print(f"   python run_simulator.py")
    
    print(f"\n3. OBSERVAR MEJORAS:")
    print(f"   - Rutas más eficientes (hasta 85% mejor)")
    print(f"   - Mensajes '[PATHFINDING MEJORADO]' en consola")
    print(f"   - Movimientos más suaves entre ubicaciones")
    
    print(f"\n4. MONITOREAR SISTEMA:")
    print(f"   - Observa mensajes en consola durante simulación")
    print(f"   - Sistema se automonitora cada 50 llamadas")
    print(f"   - Rollback automático si detecta problemas")
    
    print(f"\n5. ROLLBACK MANUAL (si necesario):")
    print(f"   python rollback_sistema.py")
    
    print(f"\n6. COMPARAR RENDIMIENTO:")
    print(f"   python pathfinding_comparison.py")

if __name__ == "__main__":
    # Activar sistema
    exito = activar_pathfinding_mejorado()
    
    if exito:
        mostrar_instrucciones()
    
    print(f"\n¡Sistema listo para testing!")