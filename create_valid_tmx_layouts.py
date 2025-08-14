#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CREADOR DE LAYOUTS TMX VÁLIDOS - Compatible con PyTMX
"""

import os
import sys

def create_valid_basic_layout():
    """Crear layout básico válido para PyTMX"""
    
    tmx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" width="20" height="15" tilewidth="32" tileheight="32" infinite="0" nextlayerid="3" nextobjectid="4">
 <properties>
  <property name="author" value="System"/>
  <property name="description" value="Layout básico de ejemplo"/>
  <property name="version" value="1.0"/>
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
  <tile id="7">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="workstation"/>
   </properties>
  </tile>
 </tileset>
 <layer id="1" name="Ground" width="20" height="15">
  <data encoding="csv">
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
1,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,1,1,
1,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,1,1,
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
1,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,1,1,
1,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,1,1,
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
1,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,1,1,
1,1,2,2,1,2,2,1,2,2,1,2,2,1,2,2,1,1,1,1,
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
  </data>
 </layer>
 <objectgroup id="2" name="Special_Locations">
  <object id="1" name="Main_Depot" type="depot" x="576" y="416" width="32" height="32">
   <properties>
    <property name="capacity" type="int" value="5"/>
   </properties>
  </object>
  <object id="2" name="Inbound_Main" type="inbound" x="32" y="32" width="32" height="32">
   <properties>
    <property name="dock_count" type="int" value="2"/>
   </properties>
  </object>
  <object id="3" name="Picking_Zone_1" type="picking" x="96" y="96" width="32" height="32">
   <properties>
    <property name="priority" value="high"/>
   </properties>
  </object>
 </objectgroup>
</map>'''
    
    return tmx_content

def create_valid_warehouse_layout():
    """Crear layout de almacén válido para PyTMX"""
    
    # Generar matriz 30x20 con patrón de racks
    width, height = 30, 20
    matrix_data = []
    
    for y in range(height):
        row = []
        for x in range(width):
            if y < 2 or y > height - 3:
                tile = 1  # Pasillos horizontales
            elif x < 2 or x > width - 3:
                tile = 1  # Bordes navegables
            elif (x - 2) % 4 in [1, 2] and 3 <= y <= height - 4:
                tile = 2  # Racks
            else:
                tile = 1  # Pasillos
            
            row.append(str(tile))
        matrix_data.append(','.join(row))
    
    csv_data = ',\n'.join(matrix_data)
    
    tmx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" width="{width}" height="{height}" tilewidth="32" tileheight="32" infinite="0" nextlayerid="3" nextobjectid="8">
 <properties>
  <property name="author" value="System"/>
  <property name="description" value="Almacén típico con racks y pasillos"/>
  <property name="version" value="1.0"/>
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
  <tile id="7">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="workstation"/>
   </properties>
  </tile>
 </tileset>
 <layer id="1" name="Navigation" width="{width}" height="{height}">
  <data encoding="csv">
{csv_data}
  </data>
 </layer>
 <objectgroup id="2" name="Locations">
  <object id="1" name="Main_Depot" type="depot" x="896" y="576" width="32" height="32">
   <properties>
    <property name="capacity" type="int" value="5"/>
   </properties>
  </object>
  <object id="2" name="Inbound_Dock" type="inbound" x="32" y="32" width="64" height="32">
   <properties>
    <property name="dock_count" type="int" value="2"/>
   </properties>
  </object>
  <object id="3" name="Picking_A1" type="picking" x="128" y="128" width="32" height="32">
   <properties>
    <property name="priority" value="high"/>
   </properties>
  </object>
  <object id="4" name="Picking_A2" type="picking" x="128" y="192" width="32" height="32">
   <properties>
    <property name="priority" value="medium"/>
   </properties>
  </object>
  <object id="5" name="Picking_B1" type="picking" x="256" y="128" width="32" height="32">
   <properties>
    <property name="priority" value="high"/>
   </properties>
  </object>
  <object id="6" name="Emergency_Exit" type="emergency" x="32" y="576" width="32" height="32"/>
  <object id="7" name="Workstation_1" type="workstation" x="800" y="128" width="64" height="32"/>
 </objectgroup>
</map>'''
    
    return tmx_content

def create_valid_tmx_files():
    """Crear archivos TMX válidos"""
    
    print("=" * 60)
    print("CREANDO LAYOUTS TMX VÁLIDOS")
    print("=" * 60)
    
    # Asegurar que existe la carpeta layouts
    os.makedirs("layouts", exist_ok=True)
    
    # Crear layout básico válido
    print("1. Creando basic_example_valid.tmx...")
    basic_tmx = create_valid_basic_layout()
    basic_path = "layouts/basic_example_valid.tmx"
    
    with open(basic_path, 'w', encoding='utf-8') as f:
        f.write(basic_tmx)
    
    print(f"   Layout básico creado: {basic_path}")
    
    # Crear layout warehouse válido
    print("2. Creando warehouse_example_valid.tmx...")
    warehouse_tmx = create_valid_warehouse_layout()
    warehouse_path = "layouts/warehouse_example_valid.tmx"
    
    with open(warehouse_path, 'w', encoding='utf-8') as f:
        f.write(warehouse_tmx)
    
    print(f"   Layout warehouse creado: {warehouse_path}")
    
    # Crear layout simple para testing
    print("3. Creando simple_test.tmx...")
    simple_tmx = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" width="10" height="8" tilewidth="32" tileheight="32" infinite="0" nextlayerid="3" nextobjectid="3">
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
 </tileset>
 <layer id="1" name="Ground" width="10" height="8">
  <data encoding="csv">
1,1,1,1,1,1,1,1,1,1,
1,1,1,1,1,1,1,1,1,1,
1,1,2,2,1,1,2,2,1,1,
1,1,2,2,1,1,2,2,1,1,
1,1,2,2,1,1,2,2,1,1,
1,1,2,2,1,1,2,2,1,1,
1,1,1,1,1,1,1,1,1,1,
1,1,1,1,1,1,1,1,1,1
  </data>
 </layer>
 <objectgroup id="2" name="Objects">
  <object id="1" name="Depot" type="depot" x="288" y="224" width="32" height="32"/>
  <object id="2" name="Inbound" type="inbound" x="32" y="32" width="32" height="32"/>
 </objectgroup>
</map>'''
    
    simple_path = "layouts/simple_test.tmx"
    with open(simple_path, 'w', encoding='utf-8') as f:
        f.write(simple_tmx)
    
    print(f"   Layout simple creado: {simple_path}")
    
    print("\n" + "=" * 60)
    print("LAYOUTS TMX VÁLIDOS CREADOS")
    print("=" * 60)
    print("Archivos creados:")
    print(f"  - {basic_path}")
    print(f"  - {warehouse_path}")
    print(f"  - {simple_path}")
    print("\nEstos layouts deberían ser compatibles con PyTMX")
    print("=" * 60)

def main():
    """Función principal"""
    create_valid_tmx_files()

if __name__ == "__main__":
    main()