#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARGADOR DE LAYOUTS DINÁMICO - Sistema para cargar mapas TMX personalizados
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Verificar si PyTMX está disponible
try:
    import pytmx
    import pytmx.util_pygame
    PYTMX_AVAILABLE = True
except ImportError:
    PYTMX_AVAILABLE = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

class DynamicLayoutLoader:
    """Cargador de layouts TMX dinámico para el simulador"""
    
    def __init__(self, layouts_folder="layouts"):
        self.layouts_folder = layouts_folder
        self.current_layout = None
        self.current_layout_path = None
        
        # Asegurar que existe la carpeta layouts
        os.makedirs(layouts_folder, exist_ok=True)
        
        # Cache de layouts cargados
        self.layouts_cache = {}
        
        print(f"Dynamic Layout Loader inicializado - Carpeta: {layouts_folder}")
    
    def scan_available_layouts(self) -> List[Dict]:
        """Escanear carpeta layouts y obtener lista de TMX disponibles"""
        
        layouts = []
        
        if not os.path.exists(self.layouts_folder):
            print(f"Carpeta {self.layouts_folder} no existe")
            return layouts
        
        for file in os.listdir(self.layouts_folder):
            if file.lower().endswith('.tmx'):
                layout_path = os.path.join(self.layouts_folder, file)
                
                try:
                    layout_info = self._analyze_tmx_file(layout_path)
                    if layout_info:
                        layouts.append(layout_info)
                
                except Exception as e:
                    print(f"Error analizando {file}: {e}")
                    # Agregar layout básico aunque tenga errores
                    layouts.append({
                        'filename': file,
                        'name': file.replace('.tmx', ''),
                        'path': layout_path,
                        'valid': False,
                        'error': str(e),
                        'description': 'Layout con errores'
                    })
        
        # Ordenar por nombre
        layouts.sort(key=lambda x: x['name'])
        
        print(f"Encontrados {len(layouts)} layouts disponibles")
        return layouts
    
    def _analyze_tmx_file(self, tmx_path: str) -> Optional[Dict]:
        """Analizar archivo TMX y extraer información"""
        
        if not PYTMX_AVAILABLE:
            return {
                'filename': os.path.basename(tmx_path),
                'name': Path(tmx_path).stem,
                'path': tmx_path,
                'valid': False,
                'error': 'PyTMX no disponible',
                'description': 'Requiere PyTMX para cargar'
            }
        
        try:
            # Cargar TMX
            tmx_data = pytmx.util_pygame.load_pygame(tmx_path)
            
            # Extraer información básica
            layout_info = {
                'filename': os.path.basename(tmx_path),
                'name': Path(tmx_path).stem,
                'path': tmx_path,
                'valid': True,
                'width': tmx_data.width,
                'height': tmx_data.height,
                'tile_width': tmx_data.tilewidth,
                'tile_height': tmx_data.tileheight,
                'total_tiles': tmx_data.width * tmx_data.height,
                'layers_count': len(list(tmx_data.layers)),
                'description': f"Layout {tmx_data.width}×{tmx_data.height} tiles"
            }
            
            # Analizar propiedades del mapa si existen
            if hasattr(tmx_data, 'properties') and tmx_data.properties:
                if 'description' in tmx_data.properties:
                    layout_info['description'] = tmx_data.properties['description']
                if 'author' in tmx_data.properties:
                    layout_info['author'] = tmx_data.properties['author']
                if 'version' in tmx_data.properties:
                    layout_info['version'] = tmx_data.properties['version']
            
            # Contar tipos de tiles
            layout_info['tiles_analysis'] = self._analyze_tiles_in_layout(tmx_data)
            
            return layout_info
            
        except Exception as e:
            raise Exception(f"Error cargando TMX: {e}")
    
    def _analyze_tiles_in_layout(self, tmx_data) -> Dict:
        """Analizar tipos de tiles en el layout"""
        
        tiles_count = {
            'walkable': 0,
            'obstacles': 0,
            'picking_points': 0,
            'depot_zones': 0,
            'special': 0,
            'unknown': 0
        }
        
        try:
            # Analizar cada capa
            for layer in tmx_data.layers:
                if hasattr(layer, 'data'):
                    for y in range(tmx_data.height):
                        for x in range(tmx_data.width):
                            tile_gid = layer.data[y][x]
                            
                            if tile_gid == 0:
                                continue
                            
                            # ARREGLO: Usar API correcta de PyTMX
                            tile_properties = tmx_data.get_tile_properties_by_gid(tile_gid)
                            if tile_properties:
                                tile_type = tile_properties.get('type', 'unknown')
                                walkable = tile_properties.get('walkable', 'false')
                                
                                if walkable.lower() == 'true':
                                    if tile_type == 'picking':
                                        tiles_count['picking_points'] += 1
                                    elif tile_type == 'depot':
                                        tiles_count['depot_zones'] += 1
                                    else:
                                        tiles_count['walkable'] += 1
                                else:
                                    tiles_count['obstacles'] += 1
                            else:
                                tiles_count['unknown'] += 1
        
        except Exception as e:
            print(f"Error analizando tiles: {e}")
        
        return tiles_count
    
    def load_layout(self, layout_path: str) -> Optional[Dict]:
        """Cargar layout específico y prepararlo para uso en simulador"""
        
        if not os.path.exists(layout_path):
            print(f"Layout no encontrado: {layout_path}")
            return None
        
        print(f"Cargando layout: {layout_path}")
        
        try:
            # Verificar si está en cache
            if layout_path in self.layouts_cache:
                print("Layout cargado desde cache")
                layout_data = self.layouts_cache[layout_path]
            else:
                # Cargar nuevo layout
                layout_data = self._load_tmx_layout(layout_path)
                if layout_data:
                    self.layouts_cache[layout_path] = layout_data
            
            if layout_data:
                self.current_layout = layout_data
                self.current_layout_path = layout_path
                print(f"Layout cargado exitosamente: {layout_data['info']['name']}")
                return layout_data
            
        except Exception as e:
            print(f"Error cargando layout {layout_path}: {e}")
        
        return None
    
    def _load_tmx_layout(self, tmx_path: str) -> Optional[Dict]:
        """Cargar y procesar archivo TMX"""
        
        if not PYTMX_AVAILABLE:
            print("PyTMX no disponible - usando layout fallback")
            return self._create_fallback_layout(tmx_path)
        
        try:
            tmx_data = pytmx.util_pygame.load_pygame(tmx_path)
            
            # Extraer datos del layout
            layout_data = {
                'info': {
                    'name': Path(tmx_path).stem,
                    'path': tmx_path,
                    'width': tmx_data.width,
                    'height': tmx_data.height,
                    'tile_width': tmx_data.tilewidth,
                    'tile_height': tmx_data.tileheight
                },
                'navigation_matrix': [],
                'special_locations': {},
                'tmx_data': tmx_data
            }
            
            # Crear matriz de navegación
            layout_data['navigation_matrix'] = self._extract_navigation_matrix(tmx_data)
            
            # Extraer ubicaciones especiales
            layout_data['special_locations'] = self._extract_special_locations(tmx_data)
            
            return layout_data
            
        except Exception as e:
            print(f"Error procesando TMX: {e}")
            return self._create_fallback_layout(tmx_path)
    
    def _extract_navigation_matrix(self, tmx_data) -> List[List[int]]:
        """Extraer matriz de navegación del TMX"""
        
        matrix = []
        
        # Buscar capa principal de navegación
        nav_layer = None
        for layer in tmx_data.layers:
            if hasattr(layer, 'data') and 'navigation' in layer.name.lower():
                nav_layer = layer
                break
        
        # Si no hay capa específica, usar primera capa con datos
        if not nav_layer:
            for layer in tmx_data.layers:
                if hasattr(layer, 'data'):
                    nav_layer = layer
                    break
        
        if nav_layer:
            for y in range(tmx_data.height):
                row = []
                for x in range(tmx_data.width):
                    tile_gid = nav_layer.data[y][x]
                    
                    # Determinar navegabilidad
                    walkable = 1  # Por defecto navegable
                    
                    if tile_gid == 0:
                        walkable = 1  # Tile vacío = navegable
                    else:
                        # Verificar propiedades del tile
                        tile_properties = tmx_data.get_tile_properties_by_gid(tile_gid)
                        if tile_properties:
                            walkable_prop = tile_properties.get('walkable', 'true')
                            walkable = 1 if walkable_prop.lower() == 'true' else 0
                    
                    row.append(walkable)
                
                matrix.append(row)
        else:
            # Crear matriz por defecto si no hay capas
            matrix = [[1 for _ in range(tmx_data.width)] for _ in range(tmx_data.height)]
        
        return matrix
    
    def _extract_special_locations(self, tmx_data) -> Dict:
        """Extraer ubicaciones especiales (depot, picking, etc.)"""
        
        locations = {
            'depot_points': [],
            'inbound_points': [],
            'picking_points': [],
            'workstations': [],
            'emergency_exits': []
        }
        
        # Buscar capas de objetos
        for layer in tmx_data.layers:
            if hasattr(layer, 'objects'):  # Capa de objetos
                for obj in layer.objects:
                    obj_type = getattr(obj, 'type', '').lower()
                    obj_name = getattr(obj, 'name', '')
                    
                    # Convertir coordenadas de pixels a tiles
                    tile_x = int(obj.x // tmx_data.tilewidth)
                    tile_y = int(obj.y // tmx_data.tileheight)
                    
                    location_data = {
                        'name': obj_name,
                        'pixel_pos': (obj.x, obj.y),
                        'tile_pos': (tile_x, tile_y),
                        'properties': getattr(obj, 'properties', {})
                    }
                    
                    # Clasificar según tipo
                    if obj_type == 'depot':
                        locations['depot_points'].append(location_data)
                    elif obj_type == 'inbound':
                        locations['inbound_points'].append(location_data)
                    elif obj_type == 'picking':
                        locations['picking_points'].append(location_data)
                    elif obj_type == 'workstation':
                        locations['workstations'].append(location_data)
                    elif obj_type == 'emergency':
                        locations['emergency_exits'].append(location_data)
        
        return locations
    
    def _create_fallback_layout(self, tmx_path: str) -> Dict:
        """Crear layout fallback cuando TMX no se puede cargar"""
        
        return {
            'info': {
                'name': Path(tmx_path).stem + ' (fallback)',
                'path': tmx_path,
                'width': 50,
                'height': 30,
                'tile_width': 32,
                'tile_height': 32
            },
            'navigation_matrix': [[1 for _ in range(50)] for _ in range(30)],
            'special_locations': {
                'depot_points': [{'tile_pos': (45, 25), 'pixel_pos': (1440, 800)}],
                'inbound_points': [{'tile_pos': (5, 5), 'pixel_pos': (160, 160)}],
                'picking_points': [],
                'workstations': [],
                'emergency_exits': []
            },
            'tmx_data': None
        }
    
    def get_layout_for_pathfinding(self) -> Optional[Tuple[List[List[int]], Dict]]:
        """Obtener datos del layout para sistema de pathfinding"""
        
        if not self.current_layout:
            return None
        
        return (
            self.current_layout['navigation_matrix'],
            self.current_layout['special_locations']
        )
    
    def get_layouts_list_for_ui(self) -> List[Dict]:
        """Obtener lista de layouts formateada para UI"""
        
        available_layouts = self.scan_available_layouts()
        
        # Formato para dropdown UI
        ui_layouts = []
        
        for layout in available_layouts:
            ui_item = {
                'display_name': f"{layout['name']} ({layout.get('width', '?')}×{layout.get('height', '?')})",
                'filename': layout['filename'],
                'path': layout['path'],
                'valid': layout['valid'],
                'description': layout['description']
            }
            ui_layouts.append(ui_item)
        
        return ui_layouts
    
    def create_sample_layouts(self):
        """Crear layouts de ejemplo para testing"""
        
        print("Creando layouts de ejemplo...")
        
        # Layout básico pequeño
        self._create_basic_sample_layout()
        
        # Layout de almacén típico
        self._create_warehouse_sample_layout()
        
        print("Layouts de ejemplo creados")
    
    def _create_basic_sample_layout(self):
        """Crear layout básico de ejemplo"""
        
        tmx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.8" tiledversion="1.8.5" orientation="orthogonal" renderorder="right-down" width="20" height="15" tilewidth="32" tileheight="32" infinite="0" nextlayerid="3" nextobjectid="4">
 <properties>
  <property name="author" value="System"/>
  <property name="description" value="Layout básico de ejemplo"/>
  <property name="version" value="1.0"/>
 </properties>
 <tileset firstgid="1" source="../tilesets/warehouse_tileset.tsx"/>
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
  <object id="1" name="Depot_Main" type="depot" x="576" y="416" width="32" height="32">
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
        
        sample_path = os.path.join(self.layouts_folder, "basic_example.tmx")
        with open(sample_path, 'w', encoding='utf-8') as f:
            f.write(tmx_content)
        
        print(f"Layout básico creado: {sample_path}")
    
    def _create_warehouse_sample_layout(self):
        """Crear layout de almacén más complejo"""
        
        # Generar matriz más compleja
        width, height = 30, 20
        
        # Crear patrón de racks
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
                
                row.append(tile)
            matrix_data.append(row)
        
        # Convertir matriz a CSV
        csv_data = '\n'.join([','.join(map(str, row)) for row in matrix_data])
        
        tmx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.8" tiledversion="1.8.5" orientation="orthogonal" renderorder="right-down" width="{width}" height="{height}" tilewidth="32" tileheight="32" infinite="0" nextlayerid="3" nextobjectid="10">
 <properties>
  <property name="author" value="System"/>
  <property name="description" value="Almacén típico con racks y pasillos"/>
  <property name="version" value="1.0"/>
 </properties>
 <tileset firstgid="1" source="../tilesets/warehouse_tileset.tsx"/>
 <layer id="1" name="Navigation" width="{width}" height="{height}">
  <data encoding="csv">
{csv_data}
  </data>
 </layer>
 <objectgroup id="2" name="Locations">
  <object id="1" name="Main_Depot" type="depot" x="896" y="576" width="32" height="32"/>
  <object id="2" name="Inbound_Dock" type="inbound" x="32" y="32" width="64" height="32"/>
  <object id="3" name="Picking_A1" type="picking" x="128" y="128" width="32" height="32"/>
  <object id="4" name="Picking_A2" type="picking" x="128" y="192" width="32" height="32"/>
  <object id="5" name="Picking_B1" type="picking" x="256" y="128" width="32" height="32"/>
  <object id="6" name="Emergency_Exit" type="emergency" x="32" y="576" width="32" height="32"/>
  <object id="7" name="Workstation_1" type="workstation" x="800" y="128" width="64" height="32"/>
 </objectgroup>
</map>'''
        
        sample_path = os.path.join(self.layouts_folder, "warehouse_example.tmx")
        with open(sample_path, 'w', encoding='utf-8') as f:
            f.write(tmx_content)
        
        print(f"Layout warehouse creado: {sample_path}")

def main():
    """Testing del cargador dinámico"""
    
    print("="*60)
    print("CARGADOR DE LAYOUTS DINÁMICO - TESTING")
    print("="*60)
    
    loader = DynamicLayoutLoader()
    
    # Crear layouts de ejemplo
    loader.create_sample_layouts()
    
    # Escanear layouts disponibles
    available = loader.scan_available_layouts()
    
    print(f"\nLayouts disponibles:")
    for layout in available:
        status = "✅" if layout['valid'] else "❌"
        print(f"  {status} {layout['name']} - {layout['description']}")
    
    # Test cargar layout
    if available:
        first_layout = available[0]
        print(f"\nCargando layout: {first_layout['name']}")
        
        loaded = loader.load_layout(first_layout['path'])
        if loaded:
            matrix, locations = loader.get_layout_for_pathfinding()
            print(f"Matriz navegación: {len(matrix)}x{len(matrix[0]) if matrix else 0}")
            print(f"Ubicaciones especiales: {len(locations)} tipos")
    
    print(f"\n✅ Cargador dinámico funcionando correctamente")
    
    return loader

if __name__ == "__main__":
    loader = main()