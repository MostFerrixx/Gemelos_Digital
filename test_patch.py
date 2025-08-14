#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST DE PATCH - Verificar qué está pasando exactamente
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def test_simple_patch():
    """Test simple de patch"""
    
    print("=" * 60)
    print("TESTING PATCH MECHANISMS")
    print("=" * 60)
    
    # Importar el módulo
    from visualization.original_renderer import dibujar_almacen, RendererOriginal
    import visualization.original_renderer as renderer_module
    
    print(f"Función original dibujar_almacen: {dibujar_almacen}")
    print(f"Módulo renderer: {renderer_module}")
    print(f"RendererOriginal class: {RendererOriginal}")
    
    # Test 1: Patch de función
    def nueva_funcion(screen, almacen):
        print("NUEVA FUNCION EJECUTADA!")
        return "test"
    
    # Guardamos la original
    original_dibujar = renderer_module.dibujar_almacen
    
    # Reemplazamos
    renderer_module.dibujar_almacen = nueva_funcion
    
    print(f"Después del patch: {renderer_module.dibujar_almacen}")
    
    # Test llamar la nueva función
    resultado = renderer_module.dibujar_almacen(None, None)
    print(f"Resultado: {resultado}")
    
    # Test 2: ¿Qué pasa con RendererOriginal?
    print("\nTesting RendererOriginal class...")
    
    # Ver método actual
    original_method = getattr(RendererOriginal, 'renderizar_frame_completo', None)
    print(f"Método original renderizar_frame_completo: {original_method}")
    
    # Crear instancia
    try:
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((100, 100))
        renderer = RendererOriginal(screen)
        print(f"Instancia de RendererOriginal creada: {renderer}")
        
        # ¿Qué método está usando?
        método_actual = getattr(renderer, 'renderizar_frame_completo', None)
        print(f"Método en instancia: {método_actual}")
        
        pygame.quit()
        
    except Exception as e:
        print(f"Error creando instancia: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_simple_patch()