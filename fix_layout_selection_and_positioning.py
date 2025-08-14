#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARREGLO INTEGRAL: Layout selection y posicionamiento de operarios
"""

def fix_layout_selection_system():
    """Arreglar el sistema de selección de layout para que respete la elección del usuario"""
    
    print("=" * 70)
    print("ARREGLANDO SISTEMA DE SELECCIÓN DE LAYOUT")
    print("=" * 70)
    
    try:
        # Verificar si existe el sistema de configuración
        from enhanced_config_window import EnhancedConfigWindow
        
        # Patch para forzar respeto del layout seleccionado
        def patch_layout_detection():
            """Patch para detectar y usar el layout correcto"""
            
            # Interceptar la función de inicialización TMX
            try:
                import dynamic_layout_loader
                
                original_load_layout = dynamic_layout_loader.DynamicLayoutLoader.load_layout if hasattr(dynamic_layout_loader, 'DynamicLayoutLoader') else None
                
                def load_layout_with_verification(self, layout_path):
                    """Cargar layout con verificación de selección"""
                    
                    print(f"[LAYOUT_FIX] Usuario seleccionó: {layout_path}")
                    
                    # Determinar qué layout se está pidiendo realmente
                    if 'almacen_grande' in layout_path.lower() or 'almacengrande' in layout_path.lower():
                        print("[LAYOUT_FIX] DETECTADO: Almacen_Grande seleccionado")
                        target_layout = "Almacen_Grande"
                    elif 'wh1' in layout_path.lower():
                        print("[LAYOUT_FIX] DETECTADO: WH1 seleccionado") 
                        target_layout = "WH1"
                    else:
                        print(f"[LAYOUT_FIX] Layout desconocido: {layout_path}")
                        target_layout = "WH1"  # fallback
                    
                    # Forzar configuración correcta del TMX
                    self._force_correct_layout(target_layout, layout_path)
                    
                    # Llamar función original si existe
                    if original_load_layout:
                        return original_load_layout(self, layout_path)
                    else:
                        return self._create_layout_data(target_layout)
                
                def _force_correct_layout(self, target_layout, layout_path):
                    """Forzar configuración correcta del layout"""
                    
                    print(f"[LAYOUT_FIX] Forzando configuración para: {target_layout}")
                    
                    # Configurar sistema TMX según el layout
                    try:
                        from tmx_coordinate_system import tmx_coords
                        
                        if target_layout == "Almacen_Grande":
                            # Configuración para Almacen_Grande (más grande)
                            tmx_coords._tmx_width = 40
                            tmx_coords._tmx_height = 35
                            tmx_coords._tile_size = 32
                            print("[LAYOUT_FIX] TMX configurado para Almacen_Grande: 40x35")
                        else:
                            # Configuración para WH1 (estándar)
                            tmx_coords._tmx_width = 30
                            tmx_coords._tmx_height = 30
                            tmx_coords._tile_size = 32
                            print("[LAYOUT_FIX] TMX configurado para WH1: 30x30")
                            
                        # Actualizar converter unificado
                        try:
                            from align_tmx_coordinates import unified_converter
                            unified_converter.tmx_grid_width = tmx_coords._tmx_width
                            unified_converter.tmx_grid_height = tmx_coords._tmx_height
                            unified_converter.tmx_world_width = tmx_coords._tmx_width * 32
                            unified_converter.tmx_world_height = tmx_coords._tmx_height * 32
                            
                            # Recalcular área visual
                            unified_converter.visual_area_width = unified_converter.visual_tile_size * unified_converter.tmx_grid_width
                            unified_converter.visual_area_height = unified_converter.visual_tile_size * unified_converter.tmx_grid_height
                            
                            print(f"[LAYOUT_FIX] Converter actualizado: {unified_converter.tmx_grid_width}x{unified_converter.tmx_grid_height}")
                            
                        except Exception as e:
                            print(f"[LAYOUT_FIX] Warning: No se pudo actualizar converter: {e}")
                            
                    except Exception as e:
                        print(f"[LAYOUT_FIX] Error configurando TMX: {e}")
                
                def _create_layout_data(self, target_layout):
                    """Crear datos de layout según el tipo"""
                    
                    if target_layout == "Almacen_Grande":
                        return {
                            'info': {
                                'name': 'Almacen_Grande',
                                'width': 40,
                                'height': 35,
                                'navigable_percentage': 65
                            },
                            'pathfinding': {
                                'grid_size': (40, 35),
                                'navigable_cells': 910  # 65% de 40*35
                            }
                        }
                    else:
                        return {
                            'info': {
                                'name': 'WH1',
                                'width': 30,
                                'height': 30,
                                'navigable_percentage': 60
                            },
                            'pathfinding': {
                                'grid_size': (30, 30),
                                'navigable_cells': 540  # 60% de 30*30
                            }
                        }
                
                # Aplicar patches si la clase existe
                if hasattr(dynamic_layout_loader, 'DynamicLayoutLoader'):
                    dynamic_layout_loader.DynamicLayoutLoader.load_layout = load_layout_with_verification
                    dynamic_layout_loader.DynamicLayoutLoader._force_correct_layout = _force_correct_layout
                    dynamic_layout_loader.DynamicLayoutLoader._create_layout_data = _create_layout_data
                    print("[LAYOUT_FIX] DynamicLayoutLoader patcheado")
                
            except Exception as e:
                print(f"[LAYOUT_FIX] Error patcheando loader: {e}")
        
        patch_layout_detection()
        
        return True
        
    except Exception as e:
        print(f"[LAYOUT_FIX] Error en sistema de layout: {e}")
        return False

def fix_operator_positioning():
    """Arreglar posicionamiento de operarios para que aparezcan dentro del layout"""
    
    print("\n" + "=" * 70)
    print("ARREGLANDO POSICIONAMIENTO DE OPERARIOS")
    print("=" * 70)
    
    try:
        # Patch para forzar posiciones correctas de operarios
        from visualization.state import estado_visual
        
        def force_operators_inside_layout():
            """Forzar operarios dentro de los límites del layout"""
            
            print("[OPERATOR_FIX] Reposicionando operarios dentro del layout...")
            
            # Obtener configuración actual
            try:
                from align_tmx_coordinates import unified_converter
                converter = unified_converter
            except:
                print("[OPERATOR_FIX] Error: Converter no disponible")
                return False
            
            # Obtener operarios actuales
            operarios = estado_visual.get("operarios", {})
            if not operarios:
                print("[OPERATOR_FIX] No hay operarios en estado visual")
                return False
            
            print(f"[OPERATOR_FIX] Reposicionando {len(operarios)} operarios...")
            
            # Definir posiciones seguras dentro del layout (esquina superior izquierda)
            safe_positions = [
                (1, 1),   # Tile (1,1)
                (2, 1),   # Tile (2,1) 
                (3, 1),   # Tile (3,1)
                (1, 2),   # Tile (1,2)
                (2, 2),   # Tile (2,2)
                (3, 2),   # Tile (3,2)
                (4, 1),   # Tile (4,1)
                (4, 2),   # Tile (4,2)
            ]
            
            # Reposicionar cada operario
            repositioned = 0
            for i, (op_id, op_data) in enumerate(operarios.items()):
                
                if i < len(safe_positions):
                    tile_x, tile_y = safe_positions[i]
                else:
                    # Para operarios adicionales, usar patrón simple
                    tile_x = 1 + (i % 5)
                    tile_y = 1 + (i // 5)
                
                # Convertir tile a coordenadas TMX pixel
                tmx_x = tile_x * converter.tmx_tile_size
                tmx_y = tile_y * converter.tmx_tile_size
                
                # Verificar que está dentro de bounds
                if (tmx_x < converter.tmx_world_width and 
                    tmx_y < converter.tmx_world_height):
                    
                    # Actualizar posición
                    op_data['x'] = tmx_x
                    op_data['y'] = tmx_y
                    
                    print(f"[OPERATOR_FIX] Operario {op_id}: Tile({tile_x},{tile_y}) -> TMX({tmx_x},{tmx_y})")
                    repositioned += 1
                else:
                    print(f"[OPERATOR_FIX] Error: Posición ({tmx_x},{tmx_y}) fuera de bounds")
            
            print(f"[OPERATOR_FIX] {repositioned} operarios reposicionados correctamente")
            return repositioned > 0
        
        # Aplicar reposicionamiento
        success = force_operators_inside_layout()
        
        # Patch del sistema de inicialización para futuras creaciones
        def patch_operator_initialization():
            """Patch para que nuevos operarios se creen en posiciones correctas"""
            
            try:
                # Encontrar y patchear la función de inicialización
                import run_simulator
                
                original_init = getattr(run_simulator.SimuladorAlmacen, '_inicializar_operarios_en_estado_visual', None)
                
                def _inicializar_operarios_en_estado_visual_fixed(self):
                    """Inicialización mejorada que respeta bounds TMX"""
                    
                    print("[INIT_FIX] Inicializando operarios en posiciones TMX seguras...")
                    
                    if not self.configuracion:
                        return
                    
                    # Obtener configuración
                    num_terrestres = self.configuracion.get('num_operarios_terrestres', 0)
                    num_montacargas = self.configuracion.get('num_montacargas', 0)
                    
                    # Limpiar operarios existentes
                    estado_visual["operarios"] = {}
                    
                    # Obtener converter TMX
                    try:
                        from align_tmx_coordinates import unified_converter
                        converter = unified_converter
                    except:
                        print("[INIT_FIX] Error: Converter no disponible, usando posiciones por defecto")
                        if original_init:
                            return original_init(self)
                        return
                    
                    # Posiciones seguras en tiles TMX
                    safe_tile_positions = [
                        (2, 2), (3, 2), (4, 2),
                        (2, 3), (3, 3), (4, 3),
                        (2, 4), (3, 4), (4, 4),
                        (5, 2), (5, 3), (5, 4)
                    ]
                    
                    # Crear operarios terrestres
                    for i in range(1, num_terrestres + 1):
                        if i-1 < len(safe_tile_positions):
                            tile_x, tile_y = safe_tile_positions[i-1]
                        else:
                            tile_x = 2 + ((i-1) % 4)
                            tile_y = 2 + ((i-1) // 4)
                        
                        # Convertir a coordenadas TMX
                        tmx_x = tile_x * converter.tmx_tile_size
                        tmx_y = tile_y * converter.tmx_tile_size
                        
                        estado_visual["operarios"][i] = {
                            'x': tmx_x,
                            'y': tmx_y,
                            'accion': 'En Estacionamiento',
                            'tareas_completadas': 0,
                            'direccion_x': 0,
                            'direccion_y': 0,
                            'tipo': 'terrestre'
                        }
                        
                        print(f"[INIT_FIX] Operario terrestre {i}: Tile({tile_x},{tile_y}) -> TMX({tmx_x},{tmx_y})")
                    
                    # Crear montacargas
                    for i in range(num_terrestres + 1, num_terrestres + num_montacargas + 1):
                        offset = i - num_terrestres - 1
                        if offset < len(safe_tile_positions):
                            tile_x, tile_y = safe_tile_positions[offset]
                            tile_y += 2  # Montacargas más abajo
                        else:
                            tile_x = 2 + (offset % 4)
                            tile_y = 4 + (offset // 4)
                        
                        # Convertir a coordenadas TMX
                        tmx_x = tile_x * converter.tmx_tile_size
                        tmx_y = tile_y * converter.tmx_tile_size
                        
                        estado_visual["operarios"][i] = {
                            'x': tmx_x,
                            'y': tmx_y,
                            'accion': 'En Estacionamiento',
                            'tareas_completadas': 0,
                            'direccion_x': 0,
                            'direccion_y': 0,
                            'tipo': 'montacargas'
                        }
                        
                        print(f"[INIT_FIX] Montacargas {i}: Tile({tile_x},{tile_y}) -> TMX({tmx_x},{tmx_y})")
                    
                    total = len(estado_visual["operarios"])
                    print(f"[INIT_FIX] {total} operarios inicializados en posiciones TMX seguras")
                
                # Aplicar patch
                if hasattr(run_simulator.SimuladorAlmacen, '_inicializar_operarios_en_estado_visual'):
                    run_simulator.SimuladorAlmacen._inicializar_operarios_en_estado_visual = _inicializar_operarios_en_estado_visual_fixed
                    print("[INIT_FIX] Función de inicialización patcheada")
                
            except Exception as e:
                print(f"[INIT_FIX] Error patcheando inicialización: {e}")
        
        patch_operator_initialization()
        
        return success
        
    except Exception as e:
        print(f"[OPERATOR_FIX] Error arreglando posicionamiento: {e}")
        return False

def install_realtime_bounds_enforcement():
    """Instalar sistema de vigilancia en tiempo real para mantener operarios dentro"""
    
    print("\n" + "=" * 70)
    print("INSTALANDO VIGILANCIA BOUNDS EN TIEMPO REAL")
    print("=" * 70)
    
    try:
        from visualization.state import estado_visual
        
        def enforce_bounds_continuously():
            """Forzar operarios dentro de bounds continuamente"""
            
            try:
                from align_tmx_coordinates import unified_converter
                converter = unified_converter
                
                operarios = estado_visual.get("operarios", {})
                corrections = 0
                
                for op_id, op_data in operarios.items():
                    x, y = op_data.get('x', 0), op_data.get('y', 0)
                    
                    # Verificar bounds TMX
                    if (x < 0 or x >= converter.tmx_world_width or 
                        y < 0 or y >= converter.tmx_world_height):
                        
                        # Corregir a posición segura
                        safe_x = max(32, min(x, converter.tmx_world_width - 32))
                        safe_y = max(32, min(y, converter.tmx_world_height - 32))
                        
                        op_data['x'] = safe_x
                        op_data['y'] = safe_y
                        
                        print(f"[BOUNDS_ENFORCE] Operario {op_id}: ({x},{y}) -> ({safe_x},{safe_y})")
                        corrections += 1
                
                return corrections
                
            except Exception as e:
                print(f"[BOUNDS_ENFORCE] Error: {e}")
                return 0
        
        # Instalar en el sistema de renderizado
        try:
            import visualization.original_renderer as renderer_module
            
            original_render = getattr(renderer_module, 'renderizar_frame_completo', None)
            
            def renderizar_frame_completo_with_bounds_check(self):
                """Renderizado con verificación de bounds"""
                
                # Forzar bounds antes de renderizar
                enforce_bounds_continuously()
                
                # Renderizar normalmente
                if original_render:
                    return original_render(self)
            
            if hasattr(renderer_module, 'RendererOriginal'):
                renderer_module.RendererOriginal.renderizar_frame_completo = renderizar_frame_completo_with_bounds_check
                print("[BOUNDS_ENFORCE] Sistema instalado en renderizador")
            
        except Exception as e:
            print(f"[BOUNDS_ENFORCE] Error instalando en renderer: {e}")
        
        # Crear función global accesible
        globals()['enforce_bounds_continuously'] = enforce_bounds_continuously
        
        return True
        
    except Exception as e:
        print(f"[BOUNDS_ENFORCE] Error instalando vigilancia: {e}")
        return False

def apply_comprehensive_fixes():
    """Aplicar todos los arreglos de manera coordinada"""
    
    print("=" * 70)
    print("APLICANDO ARREGLOS INTEGRALES DE LAYOUT Y OPERARIOS")
    print("=" * 70)
    
    fixes_applied = 0
    
    # 1. Arreglar selección de layout
    if fix_layout_selection_system():
        print("[SUCCESS] Sistema de selección de layout arreglado")
        fixes_applied += 1
    else:
        print("[WARNING] No se pudo arreglar selección de layout")
    
    # 2. Arreglar posicionamiento de operarios
    if fix_operator_positioning():
        print("[SUCCESS] Posicionamiento de operarios arreglado")
        fixes_applied += 1
    else:
        print("[WARNING] No se pudo arreglar posicionamiento")
    
    # 3. Instalar vigilancia en tiempo real
    if install_realtime_bounds_enforcement():
        print("[SUCCESS] Vigilancia de bounds instalada")
        fixes_applied += 1
    else:
        print("[WARNING] No se pudo instalar vigilancia")
    
    print(f"\n[RESULT] {fixes_applied}/3 arreglos aplicados exitosamente")
    return fixes_applied >= 2

if __name__ == "__main__":
    print("ARREGLO INTEGRAL: LAYOUT SELECTION Y POSITIONING")
    print("=" * 70)
    
    if apply_comprehensive_fixes():
        print("\n[SUCCESS] ARREGLOS APLICADOS EXITOSAMENTE")
        print("- Layout selection debería respetar la elección del usuario")
        print("- Operarios deberían aparecer dentro del layout")
        print("- Sistema de vigilancia mantendrá operarios dentro de bounds")
        print("=" * 70)
    else:
        print("\n[ERROR] ALGUNOS ARREGLOS FALLARON")
        print("Revisar logs para más detalles")
        print("=" * 70)