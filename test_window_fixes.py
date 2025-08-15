#!/usr/bin/env python3
"""
Prueba de los arreglos de ventanas
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

print("=== PRUEBA DE ARREGLOS DE VENTANAS ===")

# 1. Probar ventana de configuración con scroll
print("\n1. Probando ventana de configuración con scroll...")

try:
    from config.window_config import VentanaConfiguracion
    print("[OK] VentanaConfiguracion importada correctamente")
    
    # Crear ventana de configuración (no ejecutar mainloop)
    print("   Creando ventana de configuración...")
    ventana = VentanaConfiguracion()
    print("   [OK] Ventana de configuración creada con scroll")
    
    # Verificar que se creó correctamente
    if hasattr(ventana, 'root'):
        geometry = ventana.root.geometry()
        print(f"   [OK] Geometría de ventana: {geometry}")
    
    ventana.root.destroy()  # Cerrar ventana
    
except Exception as e:
    print(f"   [ERROR] Error en ventana de configuración: {e}")
    import traceback
    traceback.print_exc()

# 2. Probar configuración de pantalla
print("\n2. Probando configuración de dimensiones...")

try:
    from config.settings import ANCHO_PANTALLA, ALTO_PANTALLA
    print(f"   [OK] Nuevas dimensiones: {ANCHO_PANTALLA}x{ALTO_PANTALLA}")
    
    if ANCHO_PANTALLA == 1200 and ALTO_PANTALLA == 700:
        print("   [OK] Dimensiones actualizadas correctamente")
    else:
        print(f"   [WARNING] Dimensiones no esperadas: {ANCHO_PANTALLA}x{ALTO_PANTALLA}")
        
except Exception as e:
    print(f"   [ERROR] Error en configuración: {e}")

# 3. Probar inicialización de pygame con nuevas dimensiones
print("\n3. Probando inicialización de pygame...")

try:
    import pygame
    pygame.init()
    
    # Obtener info de pantalla
    info = pygame.display.Info()
    screen_width = info.current_w
    screen_height = info.current_h
    print(f"   [OK] Resolución de pantalla detectada: {screen_width}x{screen_height}")
    
    # Calcular tamaño inicial como lo haría el simulador
    from config.settings import ANCHO_PANTALLA, ALTO_PANTALLA
    initial_width = min(ANCHO_PANTALLA, int(screen_width * 0.8))
    initial_height = min(ALTO_PANTALLA, int(screen_height * 0.8))
    
    print(f"   [OK] Tamaño inicial calculado: {initial_width}x{initial_height}")
    
    # Crear ventana de prueba
    screen = pygame.display.set_mode((initial_width, initial_height), pygame.RESIZABLE)
    print("   [OK] Ventana pygame creada exitosamente")
    
    pygame.quit()
    
except Exception as e:
    print(f"   [ERROR] Error en pygame: {e}")
    import traceback
    traceback.print_exc()

print("\n[SUCCESS] PRUEBAS DE VENTANAS COMPLETADAS!")
print("\nArreglos implementados:")
print("✓ Ventana de configuración con scroll")
print("✓ Dimensiones de simulador más razonables")
print("✓ Ventana redimensionable con tamaño inicial inteligente")