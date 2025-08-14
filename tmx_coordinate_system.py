#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE COORDENADAS TMX UNIFICADO
Centraliza TODA la lógica de coordenadas para evitar conflictos entre sistemas
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

class TMXCoordinateSystem:
    """Sistema unificado de coordenadas TMX - autoridad única de coordenadas"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TMXCoordinateSystem, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if TMXCoordinateSystem._initialized:
            return
            
        # Estado del sistema
        self.tmx_active = False
        self.current_layout_data = None
        self.bounds = None
        self.tile_size = 32  # Tamaño estándar TMX
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Límites por defecto (legacy fallback)
        self.default_bounds = {
            'min_x': 0,
            'min_y': 0,
            'max_x': 1900,  # ANCHO_PANTALLA
            'max_y': 900    # ALTO_PANTALLA
        }
        
        TMXCoordinateSystem._initialized = True
        print("[TMX_COORDS] Sistema de coordenadas TMX inicializado")
    
    def _load_wh1_manual(self):
        """Cargar WH1.tmx manualmente con navegabilidad correcta"""
        
        wh1_path = "layouts/WH1.tmx"
        if not os.path.exists(wh1_path):
            print(f"[TMX_COORDS] Error: WH1.tmx no encontrado: {wh1_path}")
            return None
        
        try:
            import json
            
            # Leer archivo TMX
            with open(wh1_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extraer dimensiones del mapa
            import re
            width_match = re.search(r'width="(\d+)"', content)
            height_match = re.search(r'height="(\d+)"', content)
            
            if not width_match or not height_match:
                print("[TMX_COORDS] Error: No se pudieron extraer dimensiones")
                return None
            
            width = int(width_match.group(1))
            height = int(height_match.group(1))
            
            # Extraer datos CSV
            csv_start = content.find('<data encoding="csv">') + len('<data encoding="csv">')
            csv_end = content.find('</data>')
            csv_data = content[csv_start:csv_end].strip()
            
            # Procesar CSV
            rows = []
            for line in csv_data.split('\n'):
                if line.strip():
                    # Procesar línea, ignorar comas al final
                    line_clean = line.strip().rstrip(',')
                    if line_clean:
                        row = [int(x.strip()) for x in line_clean.split(',') if x.strip()]
                        if row:  # Solo agregar filas no vacías
                            rows.append(row)
            
            # Verificar dimensiones
            if len(rows) != height:
                print(f"[TMX_COORDS] Ajustando altura: TMX dice {height}, CSV tiene {len(rows)} filas")
                height = len(rows)
            
            if rows and len(rows[0]) != width:
                print(f"[TMX_COORDS] Ajustando ancho: TMX dice {width}, CSV tiene {len(rows[0])} columnas")
                width = len(rows[0])
            
            # Cargar mapeo de tiles
            with open('layouts/custom_tileset_mapping.json', 'r', encoding='utf-8') as f:
                tileset_mapping = json.load(f)
            
            # Crear diccionario de tiles
            tile_map = {}
            for tile in tileset_mapping['tiles']:
                tile_map[tile['id'] + 1] = tile  # TMX usa IDs 1-indexed
            
            # Convertir a matriz de navegación
            navigation_matrix = []
            tile_count = {}
            
            for y, row in enumerate(rows):
                nav_row = []
                for x, tile_id in enumerate(row):
                    tile_count[tile_id] = tile_count.get(tile_id, 0) + 1
                    
                    if tile_id in tile_map:
                        tile_info = tile_map[tile_id]
                        nav_value = 1 if tile_info['walkable'] else 0
                    else:
                        nav_value = 0  # No navegable por defecto si no está mapeado
                        
                    nav_row.append(nav_value)
                navigation_matrix.append(nav_row)
            
            print(f"[TMX_COORDS] WH1 parseado manualmente:")
            for tile_id, count in tile_count.items():
                if tile_id in tile_map:
                    tile_info = tile_map[tile_id]
                    print(f"  ID {tile_id} ({tile_info['name']}): {count} celdas - {'Navegable' if tile_info['walkable'] else 'Obstáculo'}")
                else:
                    print(f"  ID {tile_id} (No mapeado): {count} celdas - Obstáculo")
            
            # Crear ubicaciones especiales
            special_locations = {
                'depot_points': [],
                'inbound_points': [],
                'picking_points': [],
                'parking_points': []
            }
            
            for y, row in enumerate(rows):
                for x, tile_id in enumerate(row):
                    if tile_id in tile_map:
                        tile_info = tile_map[tile_id]
                        tile_type = tile_info['type']
                        
                        pixel_x = x * 32
                        pixel_y = y * 32
                        
                        if tile_type == 'depot':
                            special_locations['depot_points'].append({
                                'tile_pos': (x, y),
                                'pixel_pos': (pixel_x, pixel_y)
                            })
                        elif tile_type == 'inbound':
                            special_locations['inbound_points'].append({
                                'tile_pos': (x, y),
                                'pixel_pos': (pixel_x, pixel_y)
                            })
                        elif tile_type == 'picking':
                            special_locations['picking_points'].append({
                                'tile_pos': (x, y),
                                'pixel_pos': (pixel_x, pixel_y)
                            })
                        elif tile_type == 'parking':
                            special_locations['parking_points'].append({
                                'tile_pos': (x, y),
                                'pixel_pos': (pixel_x, pixel_y)
                            })
            
            # Calcular navegabilidad real
            total_cells = width * height
            walkable_cells = sum(sum(row) for row in navigation_matrix)
            navegabilidad = (walkable_cells / total_cells) * 100
            
            print(f"[TMX_COORDS] WH1 navegabilidad: {walkable_cells}/{total_cells} ({navegabilidad:.1f}%)")
            
            return {
                'info': {
                    'name': 'WH1_MANUAL_CORRECTO',
                    'path': wh1_path,
                    'width': width,
                    'height': height,
                    'tile_width': 32,
                    'tile_height': 32
                },
                'navigation_matrix': navigation_matrix,
                'special_locations': special_locations,
                'tmx_data': None
            }
            
        except Exception as e:
            print(f"[TMX_COORDS] Error parseando WH1 manualmente: {e}")
            return None
    
    def activate_tmx_mode(self, layout_data, visual_config=None):
        """Activar modo TMX con layout específico"""
        
        # INTERCEPTAR WH1 CON PARSER MANUAL CORRECTO
        if layout_data and 'WH1' in str(layout_data.get('info', {}).get('path', '')):
            print("[TMX_COORDS] Interceptando WH1 - Usando parser manual correcto")
            layout_data = self._load_wh1_manual()
            if not layout_data:
                print("[TMX_COORDS] Error: Parser manual WH1 falló")
                return False
        
        self.tmx_active = True
        self.current_layout_data = layout_data
        
        if layout_data:
            # Extraer dimensiones TMX
            width = layout_data['info']['width']
            height = layout_data['info']['height']
            tile_width = layout_data['info'].get('tile_width', 32)
            tile_height = layout_data['info'].get('tile_height', 32)
            
            # Calcular límites reales en pixels
            world_width = width * tile_width
            world_height = height * tile_height
            
            self.bounds = {
                'min_x': 0,
                'min_y': 0, 
                'max_x': world_width - 1,  # -1 porque las coordenadas son 0-indexed
                'max_y': world_height - 1,
                'tile_width': tile_width,
                'tile_height': tile_height,
                'grid_width': width,
                'grid_height': height
            }
            
            # Configuración visual opcional
            if visual_config:
                self.scale_factor = visual_config.get('scale', 1.0)
                self.offset_x = visual_config.get('offset_x', 0)
                self.offset_y = visual_config.get('offset_y', 0)
            
            print(f"[TMX_COORDS] Modo TMX activado:")
            print(f"  Layout: {layout_data['info']['name']}")
            print(f"  Grid: {width}x{height} tiles")
            print(f"  World: {world_width}x{world_height} pixels")
            print(f"  Bounds: ({self.bounds['min_x']},{self.bounds['min_y']}) - ({self.bounds['max_x']},{self.bounds['max_y']})")
            
        return True
    
    def deactivate_tmx_mode(self):
        """Desactivar modo TMX, volver a legacy"""
        
        self.tmx_active = False
        self.current_layout_data = None
        self.bounds = None
        print("[TMX_COORDS] Modo TMX desactivado - usando sistema legacy")
    
    def is_tmx_active(self):
        """Verificar si TMX está activo"""
        return self.tmx_active and self.current_layout_data is not None
    
    def get_bounds(self):
        """Obtener límites actuales del sistema"""
        if self.is_tmx_active() and self.bounds:
            return self.bounds
        else:
            return self.default_bounds
    
    def is_point_valid(self, x, y):
        """Verificar si un punto está dentro de los límites válidos"""
        bounds = self.get_bounds()
        
        return (bounds['min_x'] <= x <= bounds['max_x'] and
                bounds['min_y'] <= y <= bounds['max_y'])
    
    def clamp_point(self, x, y):
        """Forzar un punto a estar dentro de los límites válidos"""
        bounds = self.get_bounds()
        
        clamped_x = max(bounds['min_x'], min(x, bounds['max_x']))
        clamped_y = max(bounds['min_y'], min(y, bounds['max_y']))
        
        if (clamped_x != x or clamped_y != y):
            print(f"[TMX_COORDS] Punto clampado: ({x},{y}) -> ({clamped_x},{clamped_y})")
        
        return (clamped_x, clamped_y)
    
    def pixel_to_grid(self, x, y):
        """Convertir coordenadas pixel a coordenadas de grid TMX"""
        if not self.is_tmx_active():
            return None
            
        bounds = self.bounds
        grid_x = int(x // bounds['tile_width'])
        grid_y = int(y // bounds['tile_height'])
        
        # Clamp to grid bounds
        grid_x = max(0, min(grid_x, bounds['grid_width'] - 1))
        grid_y = max(0, min(grid_y, bounds['grid_height'] - 1))
        
        return (grid_x, grid_y)
    
    def grid_to_pixel(self, grid_x, grid_y):
        """Convertir coordenadas de grid TMX a coordenadas pixel"""
        if not self.is_tmx_active():
            return None
            
        bounds = self.bounds
        pixel_x = grid_x * bounds['tile_width'] + bounds['tile_width'] // 2  # Centro del tile
        pixel_y = grid_y * bounds['tile_height'] + bounds['tile_height'] // 2
        
        return (pixel_x, pixel_y)
    
    def get_safe_starting_position(self, operario_id=None):
        """Obtener una posición inicial segura para un operario"""
        
        if self.is_tmx_active() and self.current_layout_data:
            # Buscar parking points en TMX
            parking_points = self.current_layout_data.get('special_locations', {}).get('parking_points', [])
            
            if parking_points:
                # Usar el primer parking point disponible (se puede mejorar con lógica de ocupación)
                import random
                parking_point = random.choice(parking_points)
                pixel_pos = parking_point['pixel_pos']
                
                # Validar que esté dentro de bounds
                safe_pos = self.clamp_point(pixel_pos[0], pixel_pos[1])
                
                print(f"[TMX_COORDS] Posición inicial TMX para operario {operario_id}: {safe_pos}")
                return safe_pos
        
        # Fallback: posición legacy segura
        bounds = self.get_bounds()
        safe_x = bounds['min_x'] + 100  # Un poco adentro del borde
        safe_y = bounds['min_y'] + 100
        
        safe_pos = self.clamp_point(safe_x, safe_y)
        print(f"[TMX_COORDS] Posición inicial legacy para operario {operario_id}: {safe_pos}")
        return safe_pos
    
    def get_navigation_matrix(self):
        """Obtener matriz de navegación del layout actual"""
        if self.is_tmx_active() and self.current_layout_data:
            return self.current_layout_data.get('navigation_matrix', None)
        return None
    
    def is_grid_cell_walkable(self, grid_x, grid_y):
        """Verificar si una celda del grid es navegable"""
        nav_matrix = self.get_navigation_matrix()
        
        if nav_matrix is None:
            return True  # Legacy: asumir navegable
        
        # Verificar bounds del grid
        if (grid_y < 0 or grid_y >= len(nav_matrix) or
            grid_x < 0 or grid_x >= len(nav_matrix[0])):
            return False
        
        return nav_matrix[grid_y][grid_x] == 1
    
    def is_pixel_walkable(self, x, y):
        """Verificar si un pixel es navegable"""
        if not self.is_point_valid(x, y):
            return False
        
        grid_pos = self.pixel_to_grid(x, y)
        if grid_pos is None:
            return True  # Legacy: asumir navegable
        
        return self.is_grid_cell_walkable(grid_pos[0], grid_pos[1])
    
    def debug_info(self):
        """Información de debug del sistema"""
        info = {
            'tmx_active': self.tmx_active,
            'bounds': self.get_bounds(),
            'layout': self.current_layout_data['info']['name'] if self.current_layout_data else 'None'
        }
        return info

# Instancia global del sistema
tmx_coords = TMXCoordinateSystem()

# Funciones de utilidad global
def is_point_in_bounds(x, y):
    """Verificar si un punto está dentro de los límites globales"""
    return tmx_coords.is_point_valid(x, y)

def clamp_to_bounds(x, y):
    """Forzar un punto a estar dentro de los límites globales"""
    return tmx_coords.clamp_point(x, y)

def get_safe_operator_start(operario_id=None):
    """Obtener posición inicial segura para operario"""
    return tmx_coords.get_safe_starting_position(operario_id)

def initialize_tmx_system(layout_data, visual_config=None):
    """Inicializar sistema TMX con layout"""
    return tmx_coords.activate_tmx_mode(layout_data, visual_config)