#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GENERADOR TMX DEL SISTEMA ACTUAL - Mapeo perfecto del warehouse real
Crea archivo TMX que representa exactamente el layout actual
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

from config.settings import *
from utils.ubicaciones_picking import ubicaciones_picking

class WarehouseTMXGenerator:
    """Genera TMX que mapea perfectamente el warehouse actual"""
    
    def __init__(self):
        # Usar las mismas dimensiones que el calibrator mejorado
        self.tile_size = ANCHO_PASILLO_VERTICAL  # 30 pixels
        self.grid_width = ANCHO_PANTALLA // self.tile_size    # 63
        self.grid_height = ALTO_PANTALLA // self.tile_size    # 30
        self.offset_x = (ANCHO_PANTALLA - self.grid_width * self.tile_size) // 2
        self.offset_y = (ALTO_PANTALLA - self.grid_height * self.tile_size) // 2
        
        print(f"TMX Generator - Grid: {self.grid_width}x{self.grid_height}, tile: {self.tile_size}px")
    
    def world_to_grid(self, world_x, world_y):
        """Convertir coordenadas mundo a grid"""
        grid_x = int((world_x - self.offset_x) // self.tile_size)
        grid_y = int((world_y - self.offset_y) // self.tile_size)
        
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))
        
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x, grid_y):
        """Convertir grid a coordenadas mundo"""
        world_x = grid_x * self.tile_size + self.offset_x + self.tile_size // 2
        world_y = grid_y * self.tile_size + self.offset_y + self.tile_size // 2
        
        return world_x, world_y
    
    def is_position_walkable(self, world_x, world_y):
        """Misma lógica que enhanced_calibrator"""
        
        if world_x < 0 or world_x >= ANCHO_PANTALLA or world_y < 0 or world_y >= ALTO_PANTALLA:
            return False
        
        # Zonas especiales siempre navegables
        depot_x, depot_y = POS_DEPOT
        if abs(world_x - depot_x) < 80 and abs(world_y - depot_y) < 60:
            return True
        
        inbound_x, inbound_y = POS_INBOUND
        if abs(world_x - inbound_x) < 80 and abs(world_y - inbound_y) < 60:
            return True
        
        # Pasillos horizontales
        if (Y_PASILLO_SUPERIOR - 20 <= world_y <= Y_PASILLO_SUPERIOR + 40) or \
           (Y_PASILLO_INFERIOR - 40 <= world_y <= Y_PASILLO_INFERIOR + 20):
            return True
        
        # Área de racks
        if Y_PASILLO_SUPERIOR + 40 < world_y < Y_PASILLO_INFERIOR - 40:
            x_rel = world_x - RACK_START_X
            
            if x_rel < 0:
                return True
            
            rack_width_total = ANCHO_RACK * 2 + ESPACIO_ENTRE_RACKS_DOBLES + ANCHO_PASILLO_VERTICAL
            col_index = x_rel // rack_width_total
            x_in_col = x_rel % rack_width_total
            
            if col_index >= NUM_COLUMNAS_RACKS:
                return True
            
            if x_in_col <= ANCHO_RACK:
                return False  # Rack izquierdo
            elif x_in_col <= ANCHO_RACK + ESPACIO_ENTRE_RACKS_DOBLES:
                return True   # Espacio entre racks dobles
            elif x_in_col <= ANCHO_RACK * 2 + ESPACIO_ENTRE_RACKS_DOBLES:
                return False  # Rack derecho
            else:
                return True   # Pasillo vertical
        
        return True
    
    def create_navigation_matrix(self):
        """Crear matriz de navegación del warehouse actual"""
        
        print("Generando matriz de navegación...")
        
        matrix = []
        walkable_count = 0
        
        for grid_y in range(self.grid_height):
            row = []
            for grid_x in range(self.grid_width):
                world_x, world_y = self.grid_to_world(grid_x, grid_y)
                walkable = self.is_position_walkable(world_x, world_y)
                
                if walkable:
                    walkable_count += 1
                
                row.append(walkable)
            
            matrix.append(row)
        
        total_cells = self.grid_width * self.grid_height
        walkable_percentage = (walkable_count / total_cells) * 100
        
        print(f"Matriz creada: {walkable_count}/{total_cells} navegables ({walkable_percentage:.1f}%)")
        
        return matrix
    
    def map_warehouse_locations(self):
        """Mapear ubicaciones específicas del warehouse"""
        
        print("Mapeando ubicaciones específicas...")
        
        locations = {}
        
        # Depot
        depot_grid = self.world_to_grid(POS_DEPOT[0], POS_DEPOT[1])
        locations['depot'] = {
            'world': POS_DEPOT,
            'grid': depot_grid,
            'type': 'depot'
        }
        
        # Inbound
        inbound_grid = self.world_to_grid(POS_INBOUND[0], POS_INBOUND[1])
        locations['inbound'] = {
            'world': POS_INBOUND,
            'grid': inbound_grid,
            'type': 'inbound'
        }
        
        # Ubicaciones de picking
        picking_locations = ubicaciones_picking.obtener_todas_ubicaciones()
        
        for i, picking_pos in enumerate(picking_locations[:20]):  # Primeras 20 para testing
            picking_grid = self.world_to_grid(picking_pos[0], picking_pos[1])
            locations[f'picking_{i}'] = {
                'world': picking_pos,
                'grid': picking_grid,
                'type': 'picking'
            }
        
        print(f"Mapeadas {len(locations)} ubicaciones específicas")
        return locations
    
    def generate_warehouse_tmx(self, output_file="warehouse_real.tmx"):
        """Generar archivo TMX del warehouse actual"""
        
        print(f"Generando {output_file}...")
        
        # Crear matriz de navegación
        matrix = self.create_navigation_matrix()
        
        # Mapear ubicaciones
        locations = self.map_warehouse_locations()
        
        # Generar TMX
        tmx_content = self.create_tmx_content(matrix, locations)
        
        # Escribir archivo
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(tmx_content)
        
        print(f"TMX generado: {output_file}")
        
        return output_file, matrix, locations
    
    def create_tmx_content(self, matrix, locations):
        """Crear contenido TMX"""
        
        # Header TMX
        tmx_header = f'''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.8" tiledversion="1.8.5" orientation="orthogonal" renderorder="right-down" 
     width="{self.grid_width}" height="{self.grid_height}" 
     tilewidth="{self.tile_size}" tileheight="{self.tile_size}" 
     infinite="0" nextlayerid="2" nextobjectid="1">
'''
        
        # Tileset
        tileset = '''
 <tileset firstgid="1" name="warehouse_tiles" tilewidth="30" tileheight="30" tilecount="4" columns="2">
  <image source="warehouse_tiles.png" width="60" height="60"/>
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
    <property name="type" value="depot"/>
   </properties>
  </tile>
  <tile id="3">
   <properties>
    <property name="walkable" value="true"/>
    <property name="type" value="inbound"/>
   </properties>
  </tile>
 </tileset>
'''
        
        # Layer de navegación
        navigation_layer = f'''
 <layer id="1" name="Navigation" width="{self.grid_width}" height="{self.grid_height}">
  <data encoding="csv">
'''
        
        # Generar datos de tiles
        for y in range(self.grid_height):
            row_data = []
            for x in range(self.grid_width):
                world_x, world_y = self.grid_to_world(x, y)
                
                # Determinar tipo de tile
                tile_id = 1  # Por defecto: navegable
                
                # Verificar ubicaciones especiales
                depot_x, depot_y = POS_DEPOT
                if abs(world_x - depot_x) < 40 and abs(world_y - depot_y) < 40:
                    tile_id = 3  # Depot
                else:
                    inbound_x, inbound_y = POS_INBOUND
                    if abs(world_x - inbound_x) < 40 and abs(world_y - inbound_y) < 40:
                        tile_id = 4  # Inbound
                    elif not matrix[y][x]:
                        tile_id = 2  # Rack (obstáculo)
                    # else: tile_id = 1 (navegable por defecto)
                
                row_data.append(str(tile_id))
            
            if y < self.grid_height - 1:
                navigation_layer += ','.join(row_data) + ',\n'
            else:
                navigation_layer += ','.join(row_data) + '\n'
        
        navigation_layer += '''  </data>
 </layer>
'''
        
        # Object layer para ubicaciones específicas
        object_layer = '''
 <objectgroup id="2" name="Locations">
'''
        
        for name, loc_data in locations.items():
            world_x, world_y = loc_data['world']
            obj_type = loc_data['type']
            
            object_layer += f'''  <object id="{len(object_layer)}" name="{name}" type="{obj_type}" x="{world_x-15}" y="{world_y-15}" width="30" height="30">
   <properties>
    <property name="world_x" type="float" value="{world_x}"/>
    <property name="world_y" type="float" value="{world_y}"/>
    <property name="grid_x" type="int" value="{loc_data['grid'][0]}"/>
    <property name="grid_y" type="int" value="{loc_data['grid'][1]}"/>
   </properties>
  </object>
'''
        
        object_layer += '''
 </objectgroup>
'''
        
        # Footer
        tmx_footer = '''</map>'''
        
        return tmx_header + tileset + navigation_layer + object_layer + tmx_footer
    
    def create_test_routes(self, locations):
        """Crear rutas de prueba usando ubicaciones mapeadas"""
        
        print("Creando rutas de prueba...")
        
        test_routes = []
        
        if 'depot' in locations and 'inbound' in locations:
            test_routes.append({
                'name': 'Depot to Inbound',
                'start': locations['depot']['world'],
                'end': locations['inbound']['world']
            })
        
        if 'inbound' in locations:
            picking_keys = [k for k in locations.keys() if k.startswith('picking_')]
            if picking_keys:
                test_routes.append({
                    'name': f'Inbound to {picking_keys[0]}',
                    'start': locations['inbound']['world'],
                    'end': locations[picking_keys[0]]['world']
                })
                
                if len(picking_keys) > 1:
                    test_routes.append({
                        'name': f'{picking_keys[0]} to {picking_keys[-1]}',
                        'start': locations[picking_keys[0]]['world'],
                        'end': locations[picking_keys[-1]]['world']
                    })
        
        print(f"Creadas {len(test_routes)} rutas de prueba")
        return test_routes

def main():
    """Generar TMX del warehouse actual"""
    print("="*60)
    print("GENERADOR TMX - WAREHOUSE REAL")
    print("="*60)
    
    generator = WarehouseTMXGenerator()
    
    # Generar TMX
    tmx_file, matrix, locations = generator.generate_warehouse_tmx()
    
    # Crear rutas de prueba
    test_routes = generator.create_test_routes(locations)
    
    # Mostrar resumen
    print(f"\n{'='*40}")
    print("RESUMEN DE GENERACIÓN")
    print("="*40)
    print(f"Archivo TMX: {tmx_file}")
    print(f"Grid: {generator.grid_width}x{generator.grid_height}")
    print(f"Ubicaciones mapeadas: {len(locations)}")
    print(f"Rutas de prueba: {len(test_routes)}")
    
    # Mostrar ubicaciones principales
    print(f"\nUbicaciones principales:")
    for name, data in locations.items():
        if data['type'] in ['depot', 'inbound']:
            print(f"  {name}: mundo{data['world']} -> grid{data['grid']}")
    
    # Mostrar rutas de prueba
    print(f"\nRutas de prueba:")
    for route in test_routes:
        print(f"  {route['name']}: {route['start']} -> {route['end']}")
    
    print(f"\n✅ TMX del warehouse real generado correctamente!")
    
    return generator, tmx_file, locations, test_routes

if __name__ == "__main__":
    generator, tmx_file, locations, test_routes = main()