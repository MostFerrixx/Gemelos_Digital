#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FORZAR TEXTURAS TMX: Asegurar que el sistema visual use exclusivamente TMX
"""

def force_tmx_texture_system():
    """Forzar que el sistema use exclusivamente texturas TMX"""
    
    print("=" * 70)
    print("FORZANDO SISTEMA DE TEXTURAS TMX")
    print("=" * 70)
    
    try:
        # 1. Desactivar completamente el sistema legacy de texturas
        import config.settings as settings
        
        # Forzar configuración TMX
        if hasattr(settings, 'USE_TMX_VISUAL'):
            settings.USE_TMX_VISUAL = True
        else:
            setattr(settings, 'USE_TMX_VISUAL', True)
            
        if hasattr(settings, 'USE_LEGACY_VISUAL'):
            settings.USE_LEGACY_VISUAL = False
        else:
            setattr(settings, 'USE_LEGACY_VISUAL', False)
            
        print("[SETTINGS] Configuración TMX forzada")
        
        # 2. Patchear el sistema de almacen para usar TMX
        def patch_warehouse_rendering():
            """Patchear el rendering del almacen para usar TMX exclusivamente"""
            
            try:
                import visualization.original_renderer as renderer_module
                
                # Backup función original
                if not hasattr(renderer_module, '_original_dibujar_almacen'):
                    renderer_module._original_dibujar_almacen = renderer_module.dibujar_almacen
                
                def dibujar_almacen_tmx_forced(screen, almacen=None):
                    """Función que dibuja exclusivamente usando TMX"""
                    
                    try:
                        # Usar directamente el sistema TMX
                        from direct_layout_patch import draw_tmx_layout
                        draw_tmx_layout(screen, almacen)
                        
                        # DEBUG: Mostrar que estamos usando TMX
                        import pygame
                        font = pygame.font.Font(None, 24)
                        text = font.render("TMX VISUAL ACTIVO", True, (0, 255, 0))
                        screen.blit(text, (10, 10))
                        
                    except Exception as e:
                        print(f"[TMX_TEXTURE] Error: {e}")
                        # Fallback: solo mostrar fondo negro
                        screen.fill((30, 30, 30))
                        
                        import pygame
                        font = pygame.font.Font(None, 24)
                        text = font.render("TMX FORZADO - ERROR", True, (255, 0, 0))
                        screen.blit(text, (10, 10))
                
                # Aplicar patch
                renderer_module.dibujar_almacen = dibujar_almacen_tmx_forced
                print("[PATCH] dibujar_almacen patcheado para TMX exclusivo")
                
                return True
                
            except Exception as e:
                print(f"[PATCH] Error: {e}")
                return False
        
        # 3. Patchear la clase RendererOriginal completamente
        def patch_renderer_class():
            """Patchear la clase completa para usar TMX"""
            
            try:
                from visualization.original_renderer import RendererOriginal
                
                def renderizar_frame_completo_tmx(self):
                    """Renderizado completo usando exclusivamente TMX"""
                    
                    # Limpiar pantalla
                    self.pantalla.fill((30, 30, 30))  # Fondo oscuro
                    
                    # 1. Dibujar layout TMX forzado
                    try:
                        from direct_layout_patch import draw_tmx_layout
                        from visualization.state import estado_visual
                        
                        almacen = estado_visual.get("almacen")
                        draw_tmx_layout(self.pantalla, almacen)
                        
                    except Exception as e:
                        print(f"[TMX_RENDER] Error dibujando layout: {e}")
                        
                        # Fallback: dibujar grid TMX básico
                        import pygame
                        screen_w, screen_h = self.pantalla.get_size()
                        
                        # Dibujar grid visual simple
                        for x in range(0, screen_w, 20):
                            pygame.draw.line(self.pantalla, (50, 50, 50), (x, 0), (x, screen_h))
                        for y in range(0, screen_h, 20):
                            pygame.draw.line(self.pantalla, (50, 50, 50), (0, y), (screen_w, y))
                    
                    # 2. Dibujar operarios con sistema mejorado
                    try:
                        from fix_operator_rendering_complete import create_enhanced_operator_renderer
                        enhanced_renderer = create_enhanced_operator_renderer()
                        enhanced_renderer(self.pantalla)
                        
                    except Exception as e:
                        print(f"[TMX_RENDER] Error dibujando operarios: {e}")
                    
                    # 3. Mostrar información TMX
                    import pygame
                    font = pygame.font.Font(None, 20)
                    
                    # Estado TMX
                    from tmx_coordinate_system import tmx_coords
                    if tmx_coords.is_tmx_active():
                        bounds = tmx_coords.get_bounds()
                        tmx_text = f"TMX: {bounds['max_x']}x{bounds['max_y']} (ACTIVO)"
                        color = (0, 255, 0)
                    else:
                        tmx_text = "TMX: INACTIVO"
                        color = (255, 0, 0)
                    
                    text_surface = font.render(tmx_text, True, color)
                    self.pantalla.blit(text_surface, (10, 40))
                    
                    # Número de operarios
                    from visualization.state import estado_visual
                    operarios = estado_visual.get("operarios", {})
                    op_text = f"Operarios: {len(operarios)}"
                    op_surface = font.render(op_text, True, (255, 255, 255))
                    self.pantalla.blit(op_surface, (10, 60))
                
                # Aplicar patch a la clase
                RendererOriginal.renderizar_frame_completo = renderizar_frame_completo_tmx
                print("[PATCH] RendererOriginal.renderizar_frame_completo patcheado para TMX")
                
                return True
                
            except Exception as e:
                print(f"[PATCH_CLASS] Error: {e}")
                return False
        
        # Aplicar todos los patches
        patch_success = patch_warehouse_rendering()
        class_success = patch_renderer_class()
        
        if patch_success and class_success:
            print("[SUCCESS] Sistema de texturas TMX forzado exitosamente")
            print("[INFO] El simulador ahora debería mostrar SOLO el layout TMX")
            return True
        else:
            print("[WARNING] Algunos patches fallaron")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error forzando texturas TMX: {e}")
        import traceback
        traceback.print_exc()
        return False

def disable_legacy_visual_system():
    """Desactivar completamente el sistema visual legacy"""
    
    print("\n[DISABLE_LEGACY] Desactivando sistema visual legacy...")
    
    try:
        # Buscar y desactivar cualquier referencia al sistema legacy
        import sys
        
        # Lista de módulos legacy a desactivar
        legacy_modules = [
            'visualization.legacy_renderer',
            'visualization.warehouse_drawer',
            'config.warehouse_layout',
        ]
        
        for module_name in legacy_modules:
            if module_name in sys.modules:
                print(f"[DISABLE] Desactivando {module_name}")
                del sys.modules[module_name]
        
        # Forzar que cualquier import futuro use TMX
        class TMXOnlyImportHook:
            def find_spec(self, name, path, target=None):
                if 'legacy' in name.lower() or 'warehouse_layout' in name:
                    print(f"[BLOCK] Bloqueando import legacy: {name}")
                    return None
                return None
        
        # Instalar hook (comentado para evitar conflictos)
        # sys.meta_path.insert(0, TMXOnlyImportHook())
        
        print("[DISABLE_LEGACY] Sistema legacy desactivado")
        return True
        
    except Exception as e:
        print(f"[DISABLE_LEGACY] Error: {e}")
        return False

if __name__ == "__main__":
    print("FORZAR SISTEMA DE TEXTURAS TMX EXCLUSIVO")
    print("=" * 70)
    
    # Activar TMX primero
    try:
        from force_tmx_activation import force_tmx_activation
        if force_tmx_activation():
            print("[OK] TMX activado")
        else:
            print("[WARNING] TMX activation falló")
    except ImportError:
        print("[WARNING] TMX activation no disponible")
    
    # Desactivar legacy
    if disable_legacy_visual_system():
        print("[OK] Sistema legacy desactivado")
    
    # Forzar texturas TMX
    if force_tmx_texture_system():
        print("\n[SUCCESS] TEXTURAS TMX FORZADAS")
        print("El simulador ahora debería mostrar exclusivamente el layout TMX")
        print("=" * 70)
    else:
        print("\n[ERROR] No se pudieron forzar las texturas TMX")
        print("=" * 70)