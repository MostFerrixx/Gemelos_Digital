#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE REEMPLAZO SEGURO - Pathfinding
Drop-in replacement con rollback automático y monitoreo
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

# Importar manager
from pathfinding_manager import get_pathfinding_manager, PathfindingManager

class SafePathfindingReplacement:
    """Sistema de reemplazo seguro para funciones de pathfinding"""
    
    def __init__(self):
        self.manager = get_pathfinding_manager()
        self.modo_backup = "ACTUAL"  # Modo de seguridad
        self.activado = False
        
        # Log de eventos críticos
        self.eventos = []
        
        print("Safe Pathfinding Replacement inicializado")
    
    def activar_sistema_mejorado(self, modo="AB_TEST", porcentaje=50):
        """Activar sistema mejorado de forma segura"""
        print(f"\n🚀 ACTIVANDO SISTEMA MEJORADO")
        print(f"Modo: {modo}")
        
        if modo == "AB_TEST":
            self.manager.porcentaje_mejorado = porcentaje
            print(f"A/B Testing: {porcentaje}% usará sistema mejorado")
        
        # Intentar cambiar modo
        exito = self.manager.establecer_modo(modo)
        
        if exito:
            self.activado = True
            self.log_evento("ACTIVACION", f"Sistema mejorado activado en modo {modo}")
            print("✅ Sistema mejorado activado correctamente")
            return True
        else:
            self.log_evento("ERROR_ACTIVACION", f"Falló activación en modo {modo}")
            print("❌ Error activando sistema mejorado")
            return False
    
    def desactivar_sistema_mejorado(self, razon="Manual"):
        """Desactivar sistema mejorado (rollback)"""
        print(f"\n🔄 ROLLBACK A SISTEMA ACTUAL")
        print(f"Razón: {razon}")
        
        exito = self.manager.establecer_modo("ACTUAL")
        
        if exito:
            self.activado = False
            self.log_evento("ROLLBACK", f"Rollback ejecutado - {razon}")
            print("✅ Rollback completado")
            return True
        else:
            self.log_evento("ERROR_ROLLBACK", f"Falló rollback - {razon}")
            print("❌ Error en rollback")
            return False
    
    def log_evento(self, tipo, descripcion):
        """Log de eventos importantes"""
        evento = {
            "timestamp": datetime.now().isoformat(),
            "tipo": tipo,
            "descripcion": descripcion,
            "estadisticas": self.manager.obtener_estadisticas()
        }
        self.eventos.append(evento)
        
        # Mantener solo últimos 100 eventos
        if len(self.eventos) > 100:
            self.eventos = self.eventos[-100:]
    
    def monitorear_salud_sistema(self):
        """Monitorear salud del sistema y ejecutar rollback si es necesario"""
        stats = self.manager.obtener_estadisticas()
        
        # Criterios de rollback automático
        rollback_necesario = False
        razon_rollback = ""
        
        # 1. Tasa de error muy alta en sistema mejorado
        if (stats["llamadas_mejorado"] > 20 and 
            stats["tasa_error_mejorado"] > 15):
            rollback_necesario = True
            razon_rollback = f"Tasa de error alta: {stats['tasa_error_mejorado']:.1f}%"
        
        # 2. Sistema mejorado consistentemente más lento
        if (stats["llamadas_mejorado"] > 10 and stats["llamadas_actual"] > 10 and
            stats["tiempo_promedio_mejorado"] > stats["tiempo_promedio_actual"] * 2):
            rollback_necesario = True
            razon_rollback = "Sistema mejorado demasiado lento"
        
        if rollback_necesario and self.activado:
            print(f"🚨 ROLLBACK AUTOMÁTICO DETECTADO: {razon_rollback}")
            self.desactivar_sistema_mejorado(f"Auto: {razon_rollback}")
            return True
        
        return False
    
    def calcular_ruta_realista_safe(self, pos_actual, pos_destino, operario_id=None):
        """Función de reemplazo segura para calcular_ruta_realista"""
        
        # Monitorear salud antes de cada llamada importante
        if self.manager.estadisticas["llamadas_total"] % 50 == 0:
            self.monitorear_salud_sistema()
        
        try:
            resultado = self.manager.calcular_ruta_con_fallback(pos_actual, pos_destino, operario_id)
            return resultado
        
        except Exception as e:
            self.log_evento("ERROR_CRITICO", f"Error en pathfinding: {e}")
            print(f"🚨 ERROR CRÍTICO EN PATHFINDING: {e}")
            
            # En caso de error crítico, fallback inmediato
            if self.activado:
                self.desactivar_sistema_mejorado(f"Error crítico: {e}")
            
            # Retornar ruta de emergencia
            return [pos_actual, pos_destino]
    
    def generar_reporte_completo(self):
        """Generar reporte completo del sistema"""
        stats = self.manager.obtener_estadisticas()
        
        reporte = {
            "sistema": {
                "modo_actual": stats["modo_actual"],
                "activado": self.activado,
                "auto_rollback": stats["auto_rollback_activo"]
            },
            "rendimiento": {
                "llamadas_totales": stats["llamadas_total"],
                "distribucion": {
                    "actual": stats["llamadas_actual"],
                    "mejorado": stats["llamadas_mejorado"]
                },
                "errores": {
                    "actual": f"{stats['tasa_error_actual']:.1f}%",
                    "mejorado": f"{stats['tasa_error_mejorado']:.1f}%"
                },
                "tiempos_promedio": {
                    "actual": f"{stats['tiempo_promedio_actual']*1000:.1f}ms",
                    "mejorado": f"{stats['tiempo_promedio_mejorado']*1000:.1f}ms"
                }
            },
            "eventos_recientes": self.eventos[-10:],  # Últimos 10 eventos
            "timestamp": datetime.now().isoformat()
        }
        
        return reporte
    
    def exportar_reporte(self, archivo=None):
        """Exportar reporte completo a archivo"""
        if archivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo = f"pathfinding_reporte_{timestamp}.json"
        
        reporte = self.generar_reporte_completo()
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
        
        print(f"Reporte exportado: {archivo}")
        return archivo

# Instancia global del sistema de reemplazo
_safe_replacement = None

def get_safe_replacement():
    """Obtener instancia global del sistema seguro"""
    global _safe_replacement
    if _safe_replacement is None:
        _safe_replacement = SafePathfindingReplacement()
    return _safe_replacement

# Funciones públicas para uso en el código
def activar_pathfinding_mejorado(modo="AB_TEST", porcentaje=50):
    """Activar sistema de pathfinding mejorado"""
    replacement = get_safe_replacement()
    return replacement.activar_sistema_mejorado(modo, porcentaje)

def desactivar_pathfinding_mejorado():
    """Desactivar sistema mejorado (rollback)"""
    replacement = get_safe_replacement()
    return replacement.desactivar_sistema_mejorado("Manual")

def calcular_ruta_realista_nueva(pos_actual, pos_destino, operario_id=None):
    """Nueva función calcular_ruta_realista con sistema seguro"""
    replacement = get_safe_replacement()
    return replacement.calcular_ruta_realista_safe(pos_actual, pos_destino, operario_id)

def generar_reporte_pathfinding():
    """Generar reporte del sistema de pathfinding"""
    replacement = get_safe_replacement()
    return replacement.generar_reporte_completo()

if __name__ == "__main__":
    print("="*60)
    print("TESTING SISTEMA DE REEMPLAZO SEGURO")
    print("="*60)
    
    replacement = SafePathfindingReplacement()
    
    # Test básico
    print("\n1. Activando sistema mejorado en modo A/B...")
    exito = replacement.activar_sistema_mejorado("AB_TEST", 30)
    
    if exito:
        print("\n2. Testing rutas...")
        
        test_routes = [
            ((1750, 550), (100, 50)),
            ((100, 50), (300, 300)),
            ((300, 300), (800, 400)),
        ]
        
        for i, (start, end) in enumerate(test_routes):
            print(f"\nTest {i+1}: {start} -> {end}")
            resultado = replacement.calcular_ruta_realista_safe(start, end)
            print(f"Resultado: {len(resultado)} puntos")
        
        print("\n3. Generando reporte...")
        reporte = replacement.generar_reporte_completo()
        
        print(f"Llamadas totales: {reporte['rendimiento']['llamadas_totales']}")
        print(f"Distribución: {reporte['rendimiento']['distribucion']}")
        
        print("\n4. Test rollback...")
        replacement.desactivar_sistema_mejorado()
        
        print("\n✅ Sistema de reemplazo seguro funcionando!")
    else:
        print("❌ Error en activación")