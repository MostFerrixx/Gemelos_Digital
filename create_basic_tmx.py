#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CREAR ARCHIVO TMX BÁSICO PROGRAMÁTICAMENTE
No necesita Tiled instalado - genera TMX desde código
"""

import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

def create_basic_warehouse_tmx():
    """Crear un TMX básico del almacén actual"""
    
    print("CREANDO TMX BÁSICO DEL ALMACÉN...")
    
    # Dimensiones basadas en el almacén actual
    map_width = 50   # tiles
    map_height = 25  # tiles
    tile_width = 32  # pixels por tile
    tile_height = 32 # pixels por tile
    
    # Crear estructura XML del TMX
    map_elem = ET.Element('map', {
        'version': '1.10',
        'orientation': 'orthogonal',
        'renderorder': 'right-down',
        'width': str(map_width),
        'height': str(map_height),
        'tilewidth': str(tile_width),
        'tileheight': str(tile_height),
        'infinite': '0'
    })
    
    # Crear tileset básico
    tileset = ET.SubElement(map_elem, 'tileset', {
        'firstgid': '1',
        'name': 'warehouse_tiles',
        'tilewidth': str(tile_width),
        'tileheight': str(tile_height),
        'tilecount': '10'
    })
    
    # Imagen del tileset (no necesaria para nuestro test, usaremos colores)
    image = ET.SubElement(tileset, 'image', {
        'source': 'warehouse_tileset.png',
        'width': str(tile_width * 10),
        'height': str(tile_height)
    })
    
    # Definir propiedades de tiles
    tiles_properties = [
        {'id': '0', 'name': 'floor', 'walkable': 'true', 'color': '#CCCCCC'},      # Piso navegable
        {'id': '1', 'name': 'wall', 'walkable': 'false', 'color': '#666666'},      # Pared/obstáculo  
        {'id': '2', 'name': 'rack', 'walkable': 'false', 'color': '#8B4513'},      # Rack
        {'id': '3', 'name': 'aisle', 'walkable': 'true', 'color': '#E6E6E6'},      # Pasillo
        {'id': '4', 'name': 'picking', 'walkable': 'true', 'color': '#90EE90'},    # Zona picking
        {'id': '5', 'name': 'depot', 'walkable': 'true', 'color': '#FFD700'},      # Depot
        {'id': '6', 'name': 'inbound', 'walkable': 'true', 'color': '#87CEEB'},    # Inbound
    ]
    
    for tile_prop in tiles_properties:
        tile = ET.SubElement(tileset, 'tile', {'id': tile_prop['id']})
        properties = ET.SubElement(tile, 'properties')
        
        # Propiedad walkable
        prop_walk = ET.SubElement(properties, 'property', {
            'name': 'walkable', 
            'type': 'bool', 
            'value': tile_prop['walkable']
        })
        
        # Propiedad color para renderizado
        prop_color = ET.SubElement(properties, 'property', {
            'name': 'color',
            'type': 'string',
            'value': tile_prop['color']
        })
        
        # Propiedad name
        prop_name = ET.SubElement(properties, 'property', {
            'name': 'name',
            'type': 'string', 
            'value': tile_prop['name']
        })
    
    # Crear capa principal
    layer = ET.SubElement(map_elem, 'layer', {
        'id': '1',
        'name': 'ground',
        'width': str(map_width),
        'height': str(map_height)
    })
    
    # Crear datos del mapa (layout simplificado del almacén)
    map_data = create_warehouse_layout_data(map_width, map_height)
    
    data = ET.SubElement(layer, 'data', {'encoding': 'csv'})
    data.text = ','.join(map(str, map_data))
    
    return map_elem

def create_warehouse_layout_data(width, height):
    """Crear datos del layout del almacén simplificado"""
    
    print(f"Generando layout {width}x{height}...")
    
    # Inicializar con piso navegable (tile 1 = floor)
    data = [1] * (width * height)
    
    def set_tile(x, y, tile_id):
        """Helper para establecer tile en coordenada"""
        if 0 <= x < width and 0 <= y < height:
            data[y * width + x] = tile_id
    
    def set_rect(x1, y1, x2, y2, tile_id):
        """Helper para establecer rectángulo de tiles"""
        for y in range(y1, min(y2, height)):
            for x in range(x1, min(x2, width)):
                set_tile(x, y, tile_id)
    
    # Crear bordes (paredes)
    set_rect(0, 0, width, 1, 2)      # Borde superior
    set_rect(0, height-1, width, height, 2)  # Borde inferior
    set_rect(0, 0, 1, height, 2)     # Borde izquierdo
    set_rect(width-1, 0, width, height, 2)   # Borde derecho
    
    # Crear racks (simplificado - columnas de racks)
    rack_start_x = 5
    rack_spacing = 4
    rack_count = 8
    
    for i in range(rack_count):
        rack_x = rack_start_x + i * rack_spacing
        if rack_x < width - 2:
            # Rack doble (2 tiles de ancho con espacio en medio)
            set_rect(rack_x, 5, rack_x + 1, height - 5, 3)      # Rack izquierdo
            set_rect(rack_x + 2, 5, rack_x + 3, height - 5, 3)  # Rack derecho
            
            # Zonas de picking entre racks
            set_rect(rack_x + 1, 6, rack_x + 2, height - 6, 5)  # Picking area
    
    # Pasillos horizontales
    set_rect(1, 4, width-1, 5, 4)           # Pasillo superior
    set_rect(1, height-5, width-1, height-4, 4)  # Pasillo inferior
    
    # Zona depot
    set_rect(width-8, height//2-2, width-2, height//2+2, 6)
    
    # Zona inbound  
    set_rect(2, height//2-2, 6, height//2+2, 7)
    
    print(f"Layout creado: {len(data)} tiles")
    return data

def save_tmx_file(map_elem, filename):
    """Guardar TMX con formato bonito"""
    
    # Convertir a string con formato bonito
    rough_string = ET.tostring(map_elem, 'unicode')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    # Limpiar líneas vacías extras
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    clean_xml = '\n'.join(lines)
    
    # Guardar archivo
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(clean_xml)
    
    print(f"TMX guardado: {filename}")
    return True

def create_torture_tmx():
    """Crear TMX con la matriz de tortura para testing"""
    
    print("\nCREANDO TMX DE TORTURA...")
    
    # Matriz de tortura corregida (25x13)
    torture_matrix = [
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        [0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        [0,1,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,1,0],
        [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
        [0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,0,1,1],
        [0,1,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0,0,1,0,0,0],
        [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
        [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        [0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
    ]
    
    width = len(torture_matrix[0])
    height = len(torture_matrix)
    
    # Crear TMX para matriz de tortura
    map_elem = ET.Element('map', {
        'version': '1.10',
        'orientation': 'orthogonal', 
        'renderorder': 'right-down',
        'width': str(width),
        'height': str(height),
        'tilewidth': '32',
        'tileheight': '32',
        'infinite': '0'
    })
    
    # Tileset simple
    tileset = ET.SubElement(map_elem, 'tileset', {
        'firstgid': '1',
        'name': 'torture_tiles',
        'tilewidth': '32', 
        'tileheight': '32',
        'tilecount': '2'
    })
    
    # Tile 0 = navegable, Tile 1 = obstáculo
    for i in range(2):
        tile = ET.SubElement(tileset, 'tile', {'id': str(i)})
        properties = ET.SubElement(tile, 'properties')
        
        walkable = 'true' if i == 0 else 'false'
        color = '#90EE90' if i == 0 else '#8B4513'
        
        ET.SubElement(properties, 'property', {
            'name': 'walkable', 'type': 'bool', 'value': walkable
        })
        ET.SubElement(properties, 'property', {
            'name': 'color', 'type': 'string', 'value': color
        })
    
    # Capa de datos
    layer = ET.SubElement(map_elem, 'layer', {
        'id': '1', 'name': 'torture', 'width': str(width), 'height': str(height)
    })
    
    # Convertir matriz a datos TMX (1-indexed)
    tmx_data = []
    for row in torture_matrix:
        for cell in row:
            tmx_data.append(cell + 1)  # TMX usa 1-indexed
    
    data = ET.SubElement(layer, 'data', {'encoding': 'csv'})
    data.text = ','.join(map(str, tmx_data))
    
    return map_elem

def main():
    """Crear ambos archivos TMX"""
    print("="*50)
    print("GENERADOR DE ARCHIVOS TMX")
    print("="*50)
    
    # Crear TMX del almacén
    warehouse_tmx = create_basic_warehouse_tmx()
    save_tmx_file(warehouse_tmx, 'warehouse_basic.tmx')
    
    # Crear TMX de tortura
    torture_tmx = create_torture_tmx()
    save_tmx_file(torture_tmx, 'torture_layout.tmx')
    
    print("\n" + "="*50)
    print("ARCHIVOS TMX CREADOS:")
    print("- warehouse_basic.tmx (50x25) - Layout del almacén")
    print("- torture_layout.tmx (25x13) - Matriz de tortura")
    print("="*50)
    
    return True

if __name__ == "__main__":
    main()