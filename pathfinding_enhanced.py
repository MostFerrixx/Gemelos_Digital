
def calcular_ruta_realista_mejorada_v2(pos_actual, pos_destino, operario_id=None):
    """
    VERSIÓN MEJORADA - Calibración perfecta mundo ↔ grid
    Reemplazo directo con escalado correcto
    """
    global _enhanced_calibrator_global
    if '_enhanced_calibrator_global' not in globals():
        from enhanced_calibrator import EnhancedCalibrator
        _enhanced_calibrator_global = EnhancedCalibrator()
    
    try:
        world_path, runs = _enhanced_calibrator_global.calculate_route_enhanced(pos_actual, pos_destino)
        
        if world_path:
            print(f"[ENHANCED] Ruta: {len(world_path)} puntos, {runs} nodos")
            return world_path
        else:
            print(f"[FALLBACK] Sin ruta, usando línea directa")
            return [pos_actual, pos_destino]
    
    except Exception as e:
        print(f"[ERROR ENHANCED] {e}, usando fallback")
        return [pos_actual, pos_destino]
