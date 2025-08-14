#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CREADOR DE LAYOUT TUTORIAL - Muestra cómo usar cada tile del tileset
"""

import os

def create_tutorial_layout():
    """Crear layout tutorial que muestra el uso de cada tile"""
    
    print("Creando layout tutorial...")
    
    # Diseño 25x18 que muestra todos los tiles
    width, height = 25, 18
    
    # Matriz que demuestra el uso de cada tile
    matrix = [
        # Fila 0 - Muro perimetral
        [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
        
        # Fila 1 - Zona de entrada con inbound
        [6, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 8, 6],
        
        # Fila 2 - Pasillo principal horizontal
        [6, 1, 1, 7, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 6],
        
        # Fila 3 - Primera sección de racks con picking
        [6, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 1, 1, 6],
        [6, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 1, 1, 6],
        
        # Fila 5 - Pasillo secundario
        [6, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 6],
        
        # Fila 6-7 - Segunda sección de racks
        [6, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 11, 11, 6],
        [6, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 11, 11, 6],
        
        # Fila 8 - Pasillo principal central (más rápido)
        [6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 6],
        
        # Fila 9-10 - Tercera sección de racks
        [6, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 11, 11, 6],
        [6, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 11, 11, 6],
        
        # Fila 11 - Pasillo secundario
        [6, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 6],
        
        # Fila 12-13 - Cuarta sección con área de oficinas
        [6, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 1, 1, 1, 1, 11, 11, 6],
        [6, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 11, 11, 11, 1, 11, 11, 6],
        
        # Fila 14 - Pasillo hacia zona de carga
        [6, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 6],
        
        # Fila 15 - Zona de carga y depot
        [6, 9, 9, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 6],
        
        # Fila 16 - Zona depot ampliada
        [6, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 6],
        
        # Fila 17 - Muro perimetral
        [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6]
    ]
    
    # Convertir a CSV (ajustar IDs para TMX - sumar 1)
    csv_data = ',\n'.join([','.join([str(tile+1) for tile in row]) for row in matrix])
    
    # Crear contenido TMX
    tmx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" width="{width}" height="{height}" tilewidth="32" tileheight="32" infinite="0" nextlayerid="3" nextobjectid="12">
 <properties>
  <property name="author" value="Tutorial"/>
  <property name="description" value="Layout tutorial que muestra el uso de todos los tiles"/>
  <property name="version" value="1.0"/>
  <property name="tutorial" value="true"/>
 </properties>
 <tileset firstgid="1" name="warehouse_tileset" tilewidth="32" tileheight="32" tilecount="12" columns="4">
  <image source="../tilesets/warehouse_tileset.png" width="128" height="96"/>
  <tile id="0">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="floor"/>
    <property name="speed_modifier" value="1.0"/>
    <property name="name" value="Floor_Walkable"/>
   </properties>
  </tile>
  <tile id="1">
   <properties>
    <property name="walkable" value="false"/>
    <property name="type" value="rack"/>
    <property name="name" value="Rack_Obstacle"/>
   </properties>
  </tile>
  <tile id="2">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="picking"/>
    <property name="name" value="Picking_Point"/>
   </properties>
  </tile>
  <tile id="3">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="depot"/>
    <property name="name" value="Depot_Zone"/>
   </properties>
  </tile>
  <tile id="4">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="inbound"/>
    <property name="name" value="Inbound_Zone"/>
   </properties>
  </tile>
  <tile id="5">
   <properties>
    <property name="walkable" value="false"/>
    <property name="type" value="wall"/>
    <property name="name" value="Wall_Blocked"/>
   </properties>
  </tile>
  <tile id="6">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="corridor"/>
    <property name="speed_modifier" value="1.2"/>
    <property name="name" value="Corridor_Main"/>
   </properties>
  </tile>
  <tile id="7">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="workstation"/>
    <property name="name" value="Workstation"/>
   </properties>
  </tile>
  <tile id="8">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="emergency"/>
    <property name="name" value="Emergency_Exit"/>
   </properties>
  </tile>
  <tile id="9">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="loading"/>
    <property name="name" value="Loading_Dock"/>
   </properties>
  </tile>
  <tile id="10">
   <properties>
    <property name="walkable" value="false"/>
    <property name="type" value="office"/>
    <property name="name" value="Office_Area"/>
   </properties>
  </tile>
  <tile id="11">
   <properties>
    <property name="walkable" value="false"/>
    <property name="type" value="reserved"/>
    <property name="name" value="Reserved_Future"/>
   </properties>
  </tile>
 </tileset>
 <layer id="1" name="Ground_Tutorial" width="{width}" height="{height}">
  <data encoding="csv">
{csv_data}
  </data>
 </layer>
 <objectgroup id="2" name="Tutorial_Objects">
  <object id="1" name="Main_Depot" type="depot" x="640" y="480" width="128" height="64">
   <properties>
    <property name="capacity" type="int" value="8"/>
    <property name="description" value="Zona principal de estacionamiento"/>
   </properties>
  </object>
  <object id="2" name="Inbound_Main" type="inbound" x="32" y="32" width="64" height="32">
   <properties>
    <property name="dock_count" type="int" value="2"/>
    <property name="description" value="Zona de entrada principal"/>
   </properties>
  </object>
  <object id="3" name="Loading_Dock_1" type="loading" x="32" y="480" width="64" height="32">
   <properties>
    <property name="truck_capacity" type="int" value="1"/>
    <property name="description" value="Muelle de carga"/>
   </properties>
  </object>
  <object id="4" name="Emergency_Exit_1" type="emergency" x="736" y="32" width="32" height="32">
   <properties>
    <property name="exit" value="true"/>
    <property name="description" value="Salida de emergencia"/>
   </properties>
  </object>
  <object id="5" name="Workstation_Scanner" type="workstation" x="96" y="64" width="32" height="32">
   <properties>
    <property name="equipment" value="scanner"/>
    <property name="description" value="Estación de escaneo"/>
   </properties>
  </object>
  <object id="6" name="Picking_Zone_A1" type="picking" x="64" y="96" width="96" height="64">
   <properties>
    <property name="priority" value="high"/>
    <property name="zone" value="A"/>
    <property name="description" value="Zona picking alta prioridad"/>
   </properties>
  </object>
  <object id="7" name="Picking_Zone_A2" type="picking" x="192" y="96" width="96" height="64">
   <properties>
    <property name="priority" value="medium"/>
    <property name="zone" value="A"/>
    <property name="description" value="Zona picking media prioridad"/>
   </properties>
  </object>
  <object id="8" name="Picking_Zone_B1" type="picking" x="320" y="96" width="96" height="64">
   <properties>
    <property name="priority" value="high"/>
    <property name="zone" value="B"/>
    <property name="description" value="Zona picking alta prioridad"/>
   </properties>
  </object>
  <object id="9" name="Office_Area_1" type="office" x="576" y="384" width="64" height="64">
   <properties>
    <property name="restricted" value="true"/>
    <property name="description" value="Área administrativa"/>
   </properties>
  </object>
  <object id="10" name="Main_Corridor" type="corridor" x="32" y="256" width="704" height="32">
   <properties>
    <property name="speed_modifier" value="1.2"/>
    <property name="description" value="Pasillo principal - velocidad aumentada"/>
   </properties>
  </object>
  <object id="11" name="Future_Expansion" type="reserved" x="704" y="192" width="64" height="128">
   <properties>
    <property name="future_use" value="true"/>
    <property name="description" value="Zona reservada para expansión futura"/>
   </properties>
  </object>
 </objectgroup>
</map>'''
    
    # Guardar archivo
    os.makedirs("layouts", exist_ok=True)
    layout_path = "layouts/tutorial_completo.tmx"
    
    with open(layout_path, 'w', encoding='utf-8') as f:
        f.write(tmx_content)
    
    return layout_path

def create_explanation():
    """Crear archivo de explicación del layout"""
    
    explanation = """
# TUTORIAL LAYOUT - EXPLICACIÓN DE TILES

Este layout tutorial muestra cómo usar cada tile del warehouse_tileset:

## DISEÑO DEL LAYOUT:

### ZONA SUPERIOR (Entrada):
- **Tiles Azul Claro (ID 6)**: Pasillos perimetrales rápidos
- **Tiles Naranja (ID 4)**: Zona de entrada/inbound (esquina superior izquierda)
- **Tile Rojo (ID 8)**: Salida de emergencia (esquina superior derecha)
- **Tile Amarillo (ID 7)**: Estación de trabajo con scanner

### ZONAS DE PICKING (4 secciones):
- **Tiles Verde (ID 2)**: Racks con puntos de picking
- **Tiles Gris Claro (ID 0)**: Pasillos navegables entre racks
- Patrón: 3 tiles de picking + 1 pasillo, repetido

### PASILLO PRINCIPAL CENTRAL:
- **Tiles Amarillo (ID 7)**: Corredor principal con velocidad aumentada (20% más rápido)
- Atraviesa todo el almacén horizontalmente

### ZONA INFERIOR (Salida):
- **Tiles Marrón Claro (ID 9)**: Muelle de carga (esquina inferior izquierda)  
- **Tiles Azul (ID 3)**: Zona de depot/estacionamiento (esquina inferior derecha)

### ÁREAS ESPECIALES:
- **Tiles Amarillo Claro (ID 10)**: Área de oficinas (lado derecho)
- **Tiles Blanco (ID 11)**: Zonas reservadas para expansión futura

## OBJETOS ESPECIALES COLOCADOS:

1. **Main_Depot**: Zona de estacionamiento principal (8 operarios)
2. **Inbound_Main**: Entrada principal (2 muelles)
3. **Loading_Dock_1**: Muelle de carga
4. **Emergency_Exit_1**: Salida de emergencia
5. **Workstation_Scanner**: Estación de escaneo
6. **Picking_Zone_A1, A2, B1**: Zonas de picking con diferentes prioridades
7. **Office_Area_1**: Área administrativa restringida
8. **Main_Corridor**: Pasillo principal con velocidad aumentada
9. **Future_Expansion**: Zona reservada

## NAVEGACIÓN:
- Los operarios pueden moverse por tiles verdes, azules, naranjas, grises, amarillos y rojos
- NO pueden pasar por tiles marrones (racks), amarillo claro (oficinas) o blancos (reservados)
- El pasillo central amarillo les da 20% más velocidad
- Los pasillos perimetrales azul claro también son optimizados

¡Este layout te muestra todos los tipos de tiles y cómo combinarlos!
"""
    
    explanation_path = "layouts/TUTORIAL_EXPLICACION.md"
    with open(explanation_path, 'w', encoding='utf-8') as f:
        f.write(explanation)
    
    return explanation_path

def main():
    """Crear layout tutorial completo"""
    
    print("=" * 60)
    print("CREANDO LAYOUT TUTORIAL COMPLETO")
    print("=" * 60)
    
    # Crear layout
    layout_path = create_tutorial_layout()
    print(f"✓ Layout tutorial creado: {layout_path}")
    
    # Crear explicación
    explanation_path = create_explanation()
    print(f"✓ Explicación creada: {explanation_path}")
    
    print("\n" + "=" * 60)
    print("LAYOUT TUTORIAL COMPLETADO")
    print("=" * 60)
    
    print(f"\nArchivos creados:")
    print(f"📄 Layout TMX: {layout_path}")
    print(f"📖 Explicación: {explanation_path}")
    
    print(f"\n🎯 PARA ABRIR EN TILED:")
    print(f"1. Abre Tiled Map Editor")
    print(f"2. File → Open")
    print(f"3. Navega a: {os.path.abspath(layout_path)}")
    print(f"4. ¡Explora el layout tutorial!")
    
    print(f"\n🔧 RUTA COMPLETA DEL ARCHIVO:")
    print(f"{os.path.abspath(layout_path)}")
    
    print(f"\n🚀 PARA USAR EN SIMULADOR:")
    print(f"1. python run_simulator.py")
    print(f"2. Tab 'Layout del Almacén'")
    print(f"3. Marca 'Usar layout personalizado'")
    print(f"4. Selecciona 'tutorial_completo' del dropdown")
    
    print("=" * 60)

if __name__ == "__main__":
    main()