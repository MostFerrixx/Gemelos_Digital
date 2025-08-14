#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONFIGURADOR DE TEXTURAS PERSONALIZADAS - Sistema completo
"""

import os
import sys

def main():
    """Configurar sistema de texturas personalizadas"""
    
    print("="*70)
    print("CONFIGURADOR DE TEXTURAS PERSONALIZADAS")
    print("Sistema para usar tus propias texturas en layouts de Tiled")
    print("="*70)
    
    print("\n🎯 OBJETIVO:")
    print("Permitir que uses tus propias texturas/imágenes para crear")
    print("layouts personalizados en Tiled que funcionen con el simulador.")
    
    print("\n📋 PROCESO:")
    print("1. Coloca tus texturas en carpeta 'custom_textures'")
    print("2. Ejecuta el configurador para asignar propiedades")
    print("3. Se genera tileset personalizado para Tiled")
    print("4. Crea tu layout en Tiled con ese tileset")
    print("5. El simulador podrá usar tu layout personalizado")
    
    print("\n" + "="*70)
    print("PASO 1: GENERAR TILESET PERSONALIZADO")
    print("="*70)
    
    # Ejecutar generador de tileset personalizado
    print("Ejecutando generador de tileset personalizado...")
    try:
        exec(open('custom_tileset_generator.py', encoding='utf-8').read())
        
        # Verificar si se generaron los archivos
        if (os.path.exists('layouts/custom_warehouse_tileset.png') and 
            os.path.exists('layouts/custom_warehouse_tileset.tsx') and
            os.path.exists('layouts/custom_tileset_mapping.json')):
            
            print("\n✅ TILESET PERSONALIZADO GENERADO")
            
            print("\n" + "="*70)
            print("PASO 2: APLICAR INTEGRACIÓN")
            print("="*70)
            
            # Aplicar integración
            exec(open('custom_layout_integration.py', encoding='utf-8').read())
            
            print("\n✅ INTEGRACIÓN APLICADA")
            
            print("\n" + "="*70)
            print("🎉 CONFIGURACIÓN COMPLETADA")
            print("="*70)
            
            print("✅ Tileset personalizado generado")
            print("✅ Integración con TMX configurada") 
            print("✅ Instrucciones de uso creadas")
            
            print("\n📁 ARCHIVOS GENERADOS:")
            print("  - layouts/custom_warehouse_tileset.png (imagen del tileset)")
            print("  - layouts/custom_warehouse_tileset.tsx (definición para Tiled)")
            print("  - layouts/custom_tileset_mapping.json (mapeo interno)")
            print("  - layouts/INSTRUCCIONES_LAYOUT_PERSONALIZADO.md (guía de uso)")
            
            print("\n🎮 CÓMO USAR:")
            print("1. Abrir Tiled Map Editor")
            print("2. Crear nuevo mapa (File > New Map)")
            print("3. Importar tileset: Map > Add External Tileset")
            print("   → Seleccionar: layouts/custom_warehouse_tileset.tsx")
            print("4. Pintar tu layout con tus texturas")
            print("5. Guardar como .tmx en carpeta layouts/")
            print("6. Ejecutar simulador y seleccionar tu layout")
            
            print("\n📖 Ver instrucciones detalladas en:")
            print("   layouts/INSTRUCCIONES_LAYOUT_PERSONALIZADO.md")
            
        else:
            print("\n❌ NO SE GENERÓ EL TILESET PERSONALIZADO")
            print("Revisa que hayas colocado tus texturas en 'custom_textures'")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nAsegúrate de que:")
        print("- Tienes texturas en 'custom_textures/'")
        print("- Las texturas son PNG, JPG, etc.")
        print("- Ejecutas desde la carpeta correcta")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()