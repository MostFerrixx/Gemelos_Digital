#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST: Verificar las referencias directas en el renderer
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def test_renderer_references():
    """Test para verificar las referencias en el renderer"""
    
    print("=" * 60)
    print("TESTING RENDERER REFERENCES")
    print("=" * 60)
    
    # Importar el módulo
    from visualization.original_renderer import dibujar_almacen, RendererOriginal
    import visualization.original_renderer as renderer_module
    
    # Función original
    original_function = dibujar_almacen
    print(f"Función original dibujar_almacen: {original_function}")
    
    # Crear una instancia
    try:
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((100, 100), pygame.NOFRAME)
        renderer = RendererOriginal(screen)
        
        # Ver el método
        method = renderer.renderizar_frame_completo
        print(f"Método renderizar_frame_completo: {method}")
        
        # Examinar el código del método
        import inspect
        source_lines = inspect.getsource(method).split('\n')
        print("\nCódigo del método:")
        for i, line in enumerate(source_lines):
            print(f"  {i:2}: {line}")
        
        pygame.quit()
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test patch
    print("\n" + "=" * 40)
    print("TESTING PATCH")
    print("=" * 40)
    
    def nueva_funcion_dibujar(screen, almacen):
        print(">>> NUEVA FUNCIÓN EJECUTADA! <<<")
        screen.fill((255, 0, 0))  # Pantalla roja
    
    # Patch el módulo
    renderer_module.dibujar_almacen = nueva_funcion_dibujar
    print(f"Después del patch - Módulo: {renderer_module.dibujar_almacen}")
    
    # ¿Funciona el patch?
    try:
        # Crear nueva instancia después del patch
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((200, 200), pygame.NOFRAME)
        new_renderer = RendererOriginal(screen)
        
        print("Probando método después del patch...")
        # Esto debería mostrar ">>> NUEVA FUNCIÓN EJECUTADA! <<<"
        new_renderer.renderizar_frame_completo()
        
        pygame.quit()
        
    except Exception as e:
        print(f"Error en test de patch: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_renderer_references()