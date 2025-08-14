
# PATCH AUTOMÁTICO PARA DYNAMIC LAYOUT LOADER
import json
import os

def _create_enhanced_fallback_layout(self, tmx_path):
    """Crear layout fallback mejorado basado en configuración"""
    
    # Leer configuración de layouts personalizados
    config_path = "layouts/layouts_personalizados.json"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            layouts_config = json.load(f)
        
        # Buscar configuración para este layout
        layout_name = os.path.splitext(os.path.basename(tmx_path))[0]
        
        for layout_config in layouts_config:
            if layout_config['info']['name'].lower() in layout_name.lower():
                return self._generate_layout_from_config(layout_config)
    
    # Fallback original si no hay configuración
    return self._create_fallback_layout_original(tmx_path)

def _generate_layout_from_config(self, layout_config):
    """Generar layout desde configuración"""
    
    info = layout_config['info']
    pattern = layout_config['pattern']
    
    # Generar matriz según patrón
    if pattern == 'warehouse_small':
        matrix = self._generate_warehouse_small_matrix(info['width'], info['height'])
    elif pattern == 'warehouse_large':
        matrix = self._generate_warehouse_large_matrix(info['width'], info['height'])
    elif pattern == 'central_corridor':
        matrix = self._generate_central_corridor_matrix(info['width'], info['height'])
    else:
        matrix = [[1 for _ in range(info['width'])] for _ in range(info['height'])]
    
    # Crear ubicaciones especiales basadas en el layout
    special_locations = self._generate_special_locations_for_pattern(pattern, info)
    
    return {
        'info': {
            'name': info['name'],
            'path': '',
            'width': info['width'],
            'height': info['height'],
            'tile_width': info['tile_width'],
            'tile_height': info['tile_height']
        },
        'navigation_matrix': matrix,
        'special_locations': special_locations,
        'tmx_data': None
    }

# Métodos auxiliares para generar matrices
def _generate_warehouse_small_matrix(self, width, height):
    """Generar matriz de almacén pequeño"""
    matrix = []
    
    for y in range(height):
        row = []
        for x in range(width):
            if y == 0 or y == height-1 or x == 0 or x == width-1:
                tile = 1  # Bordes navegables
            elif y % 4 == 2 and 2 <= x <= width-3:
                if x % 4 in [1, 2]:
                    tile = 0  # Racks
                else:
                    tile = 1  # Pasillos
            elif y == height // 2:
                tile = 1  # Corredor principal
            else:
                tile = 1
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def _generate_warehouse_large_matrix(self, width, height):
    """Generar matriz de almacén grande"""
    matrix = []
    
    for y in range(height):
        row = []
        for x in range(width):
            if y < 3 or y > height - 4:
                tile = 1  # Zonas despejadas
            elif y == height // 2:
                tile = 1  # Corredor central
            elif (y - 3) % 5 in [1, 2, 3] and 3 <= x <= width-4:
                if x % 6 in [1, 2, 3, 4]:
                    tile = 0  # Racks
                else:
                    tile = 1  # Pasillos
            else:
                tile = 1
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def _generate_central_corridor_matrix(self, width, height):
    """Generar matriz con corredor central"""
    matrix = []
    
    main_corridor_y = height // 2
    main_corridor_x = width // 2
    
    for y in range(height):
        row = []
        for x in range(width):
            if y == main_corridor_y or y == main_corridor_y - 1:
                tile = 1  # Corredor horizontal
            elif x == main_corridor_x or x == main_corridor_x - 1:
                tile = 1  # Corredor vertical
            elif (x % 4 in [1, 2]) and (y % 4 in [1, 2]):
                if abs(y - main_corridor_y) > 2 and abs(x - main_corridor_x) > 2:
                    tile = 0  # Racks
                else:
                    tile = 1
            else:
                tile = 1
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def _generate_special_locations_for_pattern(self, pattern, info):
    """Generar ubicaciones especiales según patrón"""
    
    width = info['width']
    height = info['height']
    
    locations = {
        'depot_points': [],
        'inbound_points': [],
        'picking_points': [],
        'workstations': [],
        'emergency_exits': []
    }
    
    # Depot siempre en esquina inferior derecha
    depot_x = (width - 3) * info['tile_width']
    depot_y = (height - 3) * info['tile_height']
    locations['depot_points'].append({
        'tile_pos': (width - 3, height - 3),
        'pixel_pos': (depot_x, depot_y)
    })
    
    # Inbound siempre en esquina superior izquierda
    inbound_x = 2 * info['tile_width']
    inbound_y = 2 * info['tile_height']
    locations['inbound_points'].append({
        'tile_pos': (2, 2),
        'pixel_pos': (inbound_x, inbound_y)
    })
    
    # Picking points distribuidos según patrón
    if pattern == 'warehouse_small':
        for i in range(3):
            x = (5 + i * 6) * info['tile_width']
            y = (6) * info['tile_height']
            locations['picking_points'].append({
                'tile_pos': (5 + i * 6, 6),
                'pixel_pos': (x, y)
            })
    
    elif pattern == 'warehouse_large':
        for i in range(5):
            x = (5 + i * 6) * info['tile_width']
            y = (8) * info['tile_height']
            locations['picking_points'].append({
                'tile_pos': (5 + i * 6, 8),
                'pixel_pos': (x, y)
            })
    
    elif pattern == 'central_corridor':
        # Picking en los 4 cuadrantes
        for qx in [0, 1]:
            for qy in [0, 1]:
                x = (width // 4 + qx * width // 2) * info['tile_width']
                y = (height // 4 + qy * height // 2) * info['tile_height']
                locations['picking_points'].append({
                    'tile_pos': (width // 4 + qx * width // 2, height // 4 + qy * height // 2),
                    'pixel_pos': (x, y)
                })
    
    return locations

# Aplicar patch a DynamicLayoutLoader
from dynamic_layout_loader import DynamicLayoutLoader

# Guardar método original
DynamicLayoutLoader._create_fallback_layout_original = DynamicLayoutLoader._create_fallback_layout

# Reemplazar con versión mejorada
DynamicLayoutLoader._create_enhanced_fallback_layout = _create_enhanced_fallback_layout
DynamicLayoutLoader._generate_layout_from_config = _generate_layout_from_config
DynamicLayoutLoader._generate_warehouse_small_matrix = _generate_warehouse_small_matrix
DynamicLayoutLoader._generate_warehouse_large_matrix = _generate_warehouse_large_matrix
DynamicLayoutLoader._generate_central_corridor_matrix = _generate_central_corridor_matrix
DynamicLayoutLoader._generate_special_locations_for_pattern = _generate_special_locations_for_pattern

# Reemplazar método de fallback
DynamicLayoutLoader._create_fallback_layout = _create_enhanced_fallback_layout

print("[PATCH] Sistema fallback mejorado aplicado")
