#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CREAR TMX FUNCIONAL - Compatible con PyTMX
"""

import os

def create_working_tmx_layout():
    """Crear un TMX que PyTMX pueda leer correctamente"""
    
    print("Creando layout TMX funcional...")
    
    # Layout simple pero funcional - 20x15
    tmx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0" orientation="orthogonal" renderorder="right-down" width="20" height="15" tilewidth="32" tileheight="32" nextlayerid="3" nextobjectid="4">
 <tileset firstgid="1" name="warehouse_simple" tilewidth="32" tileheight="32" tilecount="3" columns="3">
  <image source="warehouse_tileset.png" width="96" height="32"/>
  <tile id="0">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="floor"/>
   </properties>
  </tile>
  <tile id="1">
   <properties>
    <property name="walkable" value="false"/>
    <property name="type" value="rack"/>
   </properties>
  </tile>
  <tile id="2">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="corridor"/>
   </properties>
  </tile>
 </tileset>
 <layer id="1" name="Ground" width="20" height="15">
  <data encoding="csv">
3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,
3,1,1,1,3,1,1,1,3,1,1,1,3,1,1,1,3,1,1,3,
3,1,2,1,3,1,2,1,3,1,2,1,3,1,2,1,3,1,1,3,
3,1,2,1,3,1,2,1,3,1,2,1,3,1,2,1,3,1,1,3,
3,1,1,1,3,1,1,1,3,1,1,1,3,1,1,1,3,1,1,3,
3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,
3,1,1,1,3,1,1,1,3,1,1,1,3,1,1,1,3,1,1,3,
3,1,2,1,3,1,2,1,3,1,2,1,3,1,2,1,3,1,1,3,
3,1,2,1,3,1,2,1,3,1,2,1,3,1,2,1,3,1,1,3,
3,1,1,1,3,1,1,1,3,1,1,1,3,1,1,1,3,1,1,3,
3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3
  </data>
 </layer>
 <objectgroup id="2" name="Objects">
  <object id="1" name="Depot_Main" type="depot" x="576" y="416" width="64" height="32"/>
  <object id="2" name="Inbound_Main" type="inbound" x="32" y="32" width="64" height="32"/>
  <object id="3" name="Picking_A1" type="picking" x="96" y="96" width="32" height="32"/>
 </objectgroup>
</map>'''
    
    # Guardar layout
    layout_path = "layouts/layout_funcional.tmx"
    with open(layout_path, 'w', encoding='utf-8') as f:
        f.write(tmx_content)
    
    print(f"Layout funcional creado: {layout_path}")
    
    # Crear también un layout personalizado tuyo
    tmx_tu_layout = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0" orientation="orthogonal" renderorder="right-down" width="25" height="18" tilewidth="32" tileheight="32" nextlayerid="3" nextobjectid="6">
 <tileset firstgid="1" name="warehouse_custom" tilewidth="32" tileheight="32" tilecount="3" columns="3">
  <image source="warehouse_tileset.png" width="96" height="32"/>
  <tile id="0">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="floor"/>
   </properties>
  </tile>
  <tile id="1">
   <properties>
    <property name="walkable" value="false"/>
    <property name="type" value="rack"/>
   </properties>
  </tile>
  <tile id="2">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="corridor"/>
   </properties>
  </tile>
 </tileset>
 <layer id="1" name="Layout_Custom" width="25" height="18">
  <data encoding="csv">
3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,3,
3,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,3,
3,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,
3,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,3,
3,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,3,
3,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,
3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3
  </data>
 </layer>
 <objectgroup id="2" name="Special_Locations">
  <object id="1" name="Depot_Principal" type="depot" x="704" y="512" width="96" height="64"/>
  <object id="2" name="Entrada_Main" type="inbound" x="32" y="32" width="96" height="32"/>
  <object id="3" name="Picking_Zona1" type="picking" x="96" y="96" width="64" height="32"/>
  <object id="4" name="Picking_Zona2" type="picking" x="320" y="96" width="64" height="32"/>
  <object id="5" name="Picking_Zona3" type="picking" x="544" y="320" width="64" height="32"/>
 </objectgroup>
</map>'''
    
    custom_path = "layouts/mi_layout_personalizado.tmx"
    with open(custom_path, 'w', encoding='utf-8') as f:
        f.write(tmx_tu_layout)
    
    print(f"Tu layout personalizado creado: {custom_path}")
    
    return layout_path, custom_path

def create_layout_instructions():
    """Crear instrucciones para crear layouts funcionales"""
    
    instructions = '''# CÓMO CREAR LAYOUTS TMX FUNCIONALES

## PROBLEMA ACTUAL:
PyTMX no puede leer los TMX creados con Tiled por incompatibilidades de formato.

## SOLUCIÓN TEMPORAL:
Usar layouts TMX simplificados generados programáticamente.

## LAYOUTS CREADOS:

### 1. layout_funcional.tmx (20x15)
- Layout básico de prueba
- Racks simples en patrón grid
- Pasillos navegables
- 3 objetos: depot, inbound, picking

### 2. mi_layout_personalizado.tmx (25x18)  
- Layout más grande y detallado
- Patrón de racks realista
- Pasillos principales horizontales
- 5 objetos especiales
- Múltiples zonas de picking

## USAR EN SIMULADOR:
1. python run_simulator.py
2. Tab "Layout del Almacén"
3. Seleccionar "layout_funcional" o "mi_layout_personalizado"
4. Estos SÍ deberían funcionar y mostrarse

## TILES USADOS:
- ID 1 (floor): Suelo navegable - tile 0 del tileset
- ID 2 (rack): Racks obstáculo - tile 1 del tileset  
- ID 3 (corridor): Pasillos - tile 2 del tileset

## PARA CREAR MÁS LAYOUTS:
Modificar este script o usar el patrón TMX simplificado.
'''
    
    with open("layouts/INSTRUCCIONES_LAYOUTS.md", 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print("Instrucciones creadas: layouts/INSTRUCCIONES_LAYOUTS.md")

def main():
    """Crear layouts funcionales"""
    
    print("=" * 50)
    print("CREANDO LAYOUTS TMX FUNCIONALES")
    print("=" * 50)
    
    os.makedirs("layouts", exist_ok=True)
    
    layout_path, custom_path = create_working_tmx_layout()
    create_layout_instructions()
    
    print("\n" + "=" * 50)
    print("LAYOUTS TMX FUNCIONALES CREADOS")
    print("=" * 50)
    print(f"1. {layout_path} - Layout básico funcional")
    print(f"2. {custom_path} - Tu layout personalizado")
    print(f"3. layouts/INSTRUCCIONES_LAYOUTS.md - Guía")
    print("\nEstos layouts SÍ deberían funcionar en el simulador")
    print("y mostrar un diseño diferente al layout por defecto.")
    print("=" * 50)

if __name__ == "__main__":
    main()