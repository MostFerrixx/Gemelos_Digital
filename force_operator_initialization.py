#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FORZAR INICIALIZACION OPERARIOS: Asegurar que operarios aparezcan en estado visual
"""

def force_initialize_operators_in_visual_state():
    """Forzar la inicialización de operarios en estado visual"""
    
    print("[FORCE_OPERATORS] Inicializando operarios en estado visual...")
    
    try:
        from visualization.state import estado_visual
        from config.settings import POS_DEPOT
        
        # Limpiar operarios existentes
        estado_visual["operarios"] = {}
        
        # Configuración por defecto (simular configuración mínima)
        num_terrestres = 3
        num_montacargas = 2
        num_traspaletas = 1
        
        print(f"[FORCE_OPERATORS] Creando {num_terrestres} terrestres, {num_montacargas} montacargas, {num_traspaletas} traspaletas")
        
        # Usar coordenadas TMX seguras en zona de estacionamiento
        from tmx_coordinate_system import tmx_coords
        
        if tmx_coords.is_tmx_active():
            # Posiciones seguras en zona de estacionamiento TMX
            safe_positions = [
                (96, 96),    # Esquina estacionamiento
                (128, 96),   # Espaciado horizontal
                (160, 96),   # Otro espacio
                (96, 128),   # Fila inferior
                (128, 128),  # Centro estacionamiento
                (160, 128),  # Más espacio
            ]
        else:
            # Fallback a posiciones legacy
            safe_positions = [
                (320, 128),
                (360, 128), 
                (400, 128),
                (320, 168),
                (360, 168),
                (400, 168),
            ]
        
        # Crear operarios terrestres
        for i in range(1, num_terrestres + 1):
            pos_idx = (i - 1) % len(safe_positions)
            x, y = safe_positions[pos_idx]
            
            estado_visual["operarios"][i] = {
                'x': x,
                'y': y,
                'accion': 'En Estacionamiento',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': 'terrestre'
            }
            print(f"[FORCE_OPERATORS] Operario {i} (terrestre): TMX({x}, {y})")
        
        # Crear montacargas
        for i in range(num_terrestres + 1, num_terrestres + num_montacargas + 1):
            pos_idx = (i - 1) % len(safe_positions)
            x, y = safe_positions[pos_idx]
            y += 32  # Offset para montacargas
            
            estado_visual["operarios"][i] = {
                'x': x,
                'y': y,
                'accion': 'En Estacionamiento',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': 'montacargas'
            }
            print(f"[FORCE_OPERATORS] Operario {i} (montacargas): TMX({x}, {y})")
        
        # Crear traspaletas
        for i in range(num_terrestres + num_montacargas + 1, num_terrestres + num_montacargas + num_traspaletas + 1):
            pos_idx = (i - 1) % len(safe_positions)
            x, y = safe_positions[pos_idx]
            y += 64  # Offset para traspaletas
            
            estado_visual["operarios"][i] = {
                'x': x,
                'y': y,
                'accion': 'En Estacionamiento',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': 'traspaleta'
            }
            print(f"[FORCE_OPERATORS] Operario {i} (traspaleta): TMX({x}, {y})")
        
        total_created = len(estado_visual["operarios"])
        print(f"[FORCE_OPERATORS] SUCCESS: {total_created} operarios creados en estado visual")
        
        # Verificar que se crearon correctamente
        for op_id, op_data in estado_visual["operarios"].items():
            print(f"  Operario {op_id}: {op_data['tipo']} en TMX({op_data['x']}, {op_data['y']}) - {op_data['accion']}")
        
        return True
        
    except Exception as e:
        print(f"[FORCE_OPERATORS] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def patch_operator_creation():
    """Patchear la creación de operarios para asegurar que se agreguen al estado visual"""
    
    try:
        # Patchear la función crear_operarios para forzar inicialización
        from simulation import operators
        
        original_crear_operarios = operators.crear_operarios
        
        def crear_operarios_with_forced_init(env, almacen, configuracion):
            """Crear operarios y forzar inicialización en estado visual"""
            
            print("[PATCH_OPERATORS] Ejecutando crear_operarios con inicialización forzada...")
            
            # Llamar función original
            result = original_crear_operarios(env, almacen, configuracion)
            
            # Forzar inicialización en estado visual
            force_initialize_operators_in_visual_state()
            
            return result
        
        # Aplicar patch
        operators.crear_operarios = crear_operarios_with_forced_init
        
        print("[PATCH_OPERATORS] Función crear_operarios patcheada exitosamente")
        return True
        
    except Exception as e:
        print(f"[PATCH_OPERATORS] Error aplicando patch: {e}")
        return False

def ensure_operators_visible():
    """Función principal para asegurar que operarios sean visibles"""
    
    print("=" * 60)
    print("FORZAR VISIBILIDAD DE OPERARIOS")
    print("=" * 60)
    
    # 1. Activar TMX
    try:
        from force_tmx_activation import force_tmx_activation
        tmx_success = force_tmx_activation()
        if tmx_success:
            print("[OK] Sistema TMX activado")
        else:
            print("[WARNING] TMX no se activó completamente")
    except ImportError:
        print("[WARNING] Force TMX activation no disponible")
    
    # 2. Patchear creación de operarios
    if patch_operator_creation():
        print("[OK] Patch de creación de operarios aplicado")
    else:
        print("[ERROR] No se pudo aplicar patch de creación")
    
    # 3. Forzar inicialización inmediata
    if force_initialize_operators_in_visual_state():
        print("[OK] Operarios inicializados en estado visual")
    else:
        print("[ERROR] No se pudieron inicializar operarios")
    
    # 4. Aplicar patch de renderizado
    try:
        from fix_operator_rendering_complete import force_patch_operator_rendering
        if force_patch_operator_rendering():
            print("[OK] Patch de renderizado aplicado")
        else:
            print("[WARNING] Patch de renderizado falló")
    except ImportError:
        print("[WARNING] Patch de renderizado no disponible")
    
    print("\n[INFO] Los operarios deberían ser visibles ahora")
    print("=" * 60)

if __name__ == "__main__":
    ensure_operators_visible()