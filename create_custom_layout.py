#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CREADOR DE LAYOUTS PERSONALIZADOS
"""

import os
import sys

def create_custom_layout(name, width=25, height=18, pattern="basic"):
    """Crear layout personalizado"""
    
    print(f"Creando layout personalizado: {name}")
    print(f"Tamaño: {width}x{height} tiles")
    print(f"Patrón: {pattern}")
    
    # Generar matriz según patrón
    if pattern == "basic":
        matrix = create_basic_pattern(width, height)
    elif pattern == "warehouse":
        matrix = create_warehouse_pattern(width, height)
    elif pattern == "corridors":
        matrix = create_corridors_pattern(width, height)
    else:
        matrix = create_empty_pattern(width, height)
    
    # Convertir matriz a CSV
    csv_data = ',\n'.join([','.join(map(str, row)) for row in matrix])
    
    # Crear contenido TMX
    tmx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" width="{width}" height="{height}" tilewidth="32" tileheight="32" infinite="0" nextlayerid="3" nextobjectid="5">
 <properties>
  <property name="author" value="User"/>
  <property name="description" value="Layout personalizado {name}"/>
  <property name="version" value="1.0"/>
  <property name="pattern" value="{pattern}"/>
 </properties>
 <tileset firstgid="1" name="warehouse_tileset" tilewidth="32" tileheight="32" tilecount="12" columns="4">
  <image source="../tilesets/warehouse_tileset.png" width="128" height="96"/>
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
    <property name="type" value="picking"/>
   </properties>
  </tile>
  <tile id="3">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="depot"/>
   </properties>
  </tile>
  <tile id="4">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="inbound"/>
   </properties>
  </tile>
  <tile id="5">
   <properties>
    <property name="walkable" value="false"/>
    <property name="type" value="wall"/>
   </properties>
  </tile>
  <tile id="6">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="corridor"/>
   </properties>
  </tile>
 </tileset>
 <layer id="1" name="Navigation" width="{width}" height="{height}">
  <data encoding="csv">
{csv_data}
  </data>
 </layer>
 <objectgroup id="2" name="Locations">
  <object id="1" name="Main_Depot" type="depot" x="{(width-2)*32}" y="{(height-2)*32}" width="32" height="32">
   <properties>
    <property name="capacity" type="int" value="5"/>
   </properties>
  </object>
  <object id="2" name="Inbound_Dock" type="inbound" x="32" y="32" width="64" height="32">
   <properties>
    <property name="dock_count" type="int" value="2"/>
   </properties>
  </object>
  <object id="3" name="Picking_Zone_1" type="picking" x="128" y="128" width="32" height="32">
   <properties>
    <property name="priority" value="high"/>
   </properties>
  </object>
  <object id="4" name="Picking_Zone_2" type="picking" x="256" y="256" width="32" height="32">
   <properties>
    <property name="priority" value="medium"/>
   </properties>
  </object>
 </objectgroup>
</map>'''
    
    # Guardar archivo
    os.makedirs("layouts", exist_ok=True)
    layout_path = f"layouts/{name}.tmx"
    
    with open(layout_path, 'w', encoding='utf-8') as f:
        f.write(tmx_content)
    
    print(f"Layout creado: {layout_path}")
    return layout_path

def create_basic_pattern(width, height):
    """Patrón básico con racks simples"""
    matrix = []
    
    for y in range(height):
        row = []
        for x in range(width):
            if y == 0 or y == height-1 or x == 0 or x == width-1:
                tile = 1  # Bordes navegables
            elif y % 4 == 2 and 2 <= x <= width-3:
                tile = 2  # Racks
            else:
                tile = 1  # Suelo navegable
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def create_warehouse_pattern(width, height):
    """Patrón de almacén con pasillos principales"""
    matrix = []
    
    for y in range(height):
        row = []
        for x in range(width):
            # Pasillos principales
            if y < 2 or y > height-3 or x < 2 or x > width-3:
                tile = 1  # Pasillos principales
            # Patrón de racks
            elif (x - 2) % 4 in [1, 2] and 3 <= y <= height-4:
                tile = 2  # Racks
            else:
                tile = 1  # Pasillos secundarios
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def create_corridors_pattern(width, height):
    """Patrón con corredores principales"""
    matrix = []
    
    main_corridor_x = width // 2
    main_corridor_y = height // 2
    
    for y in range(height):
        row = []
        for x in range(width):
            # Corredor principal horizontal
            if y == main_corridor_y:
                tile = 7  # Corredor principal
            # Corredor principal vertical
            elif x == main_corridor_x:
                tile = 7  # Corredor principal
            # Bordes
            elif y == 0 or y == height-1 or x == 0 or x == width-1:
                tile = 1  # Bordes navegables
            # Racks en cuadrantes
            elif (x % 3 == 1 or x % 3 == 2) and (y % 3 == 1 or y % 3 == 2):
                tile = 2  # Racks
            else:
                tile = 1  # Suelo navegable
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def create_empty_pattern(width, height):
    """Patrón vacío - solo suelo navegable"""
    return [[1 for _ in range(width)] for _ in range(height)]

def main():
    """Función principal interactiva"""
    
    print("=" * 60)
    print("CREADOR DE LAYOUTS PERSONALIZADOS")
    print("=" * 60)
    
    # Solicitar parámetros
    name = input("Nombre del layout (sin extensión): ").strip()
    if not name:
        name = "mi_layout_personalizado"
    
    try:
        width = int(input("Ancho en tiles (default 25): ") or "25")
        height = int(input("Alto en tiles (default 18): ") or "18")
    except ValueError:
        width, height = 25, 18
    
    print("\nPatrones disponibles:")
    print("1. basic - Racks simples en filas")
    print("2. warehouse - Almacén típico con pasillos")
    print("3. corridors - Corredores principales")
    print("4. empty - Suelo vacío")
    
    pattern_choice = input("Selecciona patrón (1-4, default 1): ").strip()
    patterns = {"1": "basic", "2": "warehouse", "3": "corridors", "4": "empty"}
    pattern = patterns.get(pattern_choice, "basic")
    
    # Crear layout
    layout_path = create_custom_layout(name, width, height, pattern)
    
    print("\n" + "=" * 60)
    print("LAYOUT CREADO EXITOSAMENTE")
    print("=" * 60)
    print(f"Archivo: {layout_path}")
    print(f"Tamaño: {width}x{height} tiles")
    print(f"Patrón: {pattern}")
    print("\nPara usar:")
    print("1. Ejecuta: python run_simulator.py")
    print("2. Ve al tab 'Layout del Almacén'")
    print("3. Marca 'Usar layout personalizado'")
    print(f"4. Selecciona '{name}' del dropdown")
    print("5. Inicia simulación")
    print("=" * 60)

if __name__ == "__main__":
    main()