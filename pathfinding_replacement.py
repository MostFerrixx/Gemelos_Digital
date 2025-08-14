
def calcular_ruta_realista_mejorada(pos_actual, pos_destino, operario_id=None):
    """
    REEMPLAZO DIRECTO - Función mejorada usando pathfinding library
    Drop-in replacement para la función actual
    """
    global _calibrator_global
    if '_calibrator_global' not in globals():
        from improved_calibrator import ImprovedCalibrator
        _calibrator_global = ImprovedCalibrator()
    
    try:
        world_path, runs = _calibrator_global.calculate_route_enhanced(pos_actual, pos_destino)
        
        if world_path:
            print(f"[NEW PATHFINDING] Ruta: {len(world_path)} puntos, {runs} nodos")
            return world_path
        else:
            print(f"[FALLBACK] Sin ruta nueva, usando fallback")
            return [pos_actual, pos_destino]
    
    except Exception as e:
        print(f"[ERROR NEW PATHFINDING] {e}, usando fallback")
        return [pos_actual, pos_destino]
