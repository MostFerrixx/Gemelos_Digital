#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONVERSOR TMX -> PANTALLA: Convertir coordenadas TMX a posiciones de pantalla
"""

class TMXScreenConverter:
    """Convertir coordenadas TMX a coordenadas de pantalla correctas"""
    
    def __init__(self):
        self.screen_width = None
        self.screen_height = None
        self.layout_area = None
        self.tmx_bounds = None
        self.initialized = False
    
    def initialize_for_screen(self, screen_width, screen_height):
        """Inicializar para dimensiones de pantalla específicas"""
        
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Calcular área de layout igual que en direct_layout_patch.py
        available_width = screen_width - 100
        available_height = screen_height - 150
        
        # TMX es 30x30 tiles
        width, height = 30, 30
        tile_size_x = available_width // width
        tile_size_y = available_height // height
        tile_size = min(tile_size_x, tile_size_y, 25)  # Máximo 25px
        
        # Calcular área total del layout
        total_layout_width = width * tile_size
        total_layout_height = height * tile_size
        offset_x = (screen_width - total_layout_width) // 2
        offset_y = (screen_height - total_layout_height - 120) // 2 + 20
        
        self.layout_area = {
            'offset_x': offset_x,
            'offset_y': offset_y,
            'width': total_layout_width,
            'height': total_layout_height,
            'tile_size': tile_size
        }
        
        # Obtener bounds TMX actuales
        try:
            from tmx_coordinate_system import tmx_coords
            if tmx_coords.is_tmx_active():
                self.tmx_bounds = tmx_coords.get_bounds()
                self.initialized = True
                
                print(f"[TMX_CONVERTER] Inicializado para pantalla {screen_width}x{screen_height}")
                print(f"[TMX_CONVERTER] Layout area: {offset_x},{offset_y} - {total_layout_width}x{total_layout_height}")
                print(f"[TMX_CONVERTER] TMX bounds: 0-{self.tmx_bounds['max_x']} x 0-{self.tmx_bounds['max_y']}")
                
                return True
        except Exception as e:
            print(f"[TMX_CONVERTER] Error inicializando: {e}")
        
        return False
    
    def convert_tmx_to_screen(self, tmx_x, tmx_y):
        """Convertir coordenadas TMX a coordenadas de pantalla"""
        
        if not self.initialized:
            # Fallback: usar coordenadas TMX directamente
            return (tmx_x, tmx_y)
        
        # Convertir TMX (0-959) a posición en área de layout
        # TMX bounds: 0 a self.tmx_bounds['max_x'] (959)
        # Layout area: offset a offset + width
        
        tmx_max_x = self.tmx_bounds['max_x']
        tmx_max_y = self.tmx_bounds['max_y']
        
        # Normalizar coordenadas TMX a 0.0-1.0
        norm_x = tmx_x / tmx_max_x
        norm_y = tmx_y / tmx_max_y
        
        # Mapear a área de layout en pantalla
        screen_x = self.layout_area['offset_x'] + (norm_x * self.layout_area['width'])
        screen_y = self.layout_area['offset_y'] + (norm_y * self.layout_area['height'])
        
        return (int(screen_x), int(screen_y))
    
    def is_initialized(self):
        """Verificar si el convertidor está inicializado"""
        return self.initialized
    
    def get_layout_bounds_on_screen(self):
        """Obtener los límites del layout en pantalla"""
        if not self.initialized:
            return None
        
        return {
            'min_x': self.layout_area['offset_x'],
            'min_y': self.layout_area['offset_y'],
            'max_x': self.layout_area['offset_x'] + self.layout_area['width'],
            'max_y': self.layout_area['offset_y'] + self.layout_area['height']
        }

# Instancia global
tmx_screen_converter = TMXScreenConverter()

def convert_operator_coordinates(operators_data, screen_width, screen_height):
    """Convertir coordenadas de todos los operarios para renderizado"""
    
    # Inicializar convertidor si es necesario
    if not tmx_screen_converter.is_initialized():
        tmx_screen_converter.initialize_for_screen(screen_width, screen_height)
    
    # Convertir coordenadas de cada operario
    converted_operators = {}
    
    for op_id, data in operators_data.items():
        tmx_x = data.get('x', 0)
        tmx_y = data.get('y', 0)
        
        # Convertir TMX a pantalla
        screen_x, screen_y = tmx_screen_converter.convert_tmx_to_screen(tmx_x, tmx_y)
        
        # Crear copia de datos con coordenadas convertidas
        converted_data = data.copy()
        converted_data['x'] = screen_x
        converted_data['y'] = screen_y
        converted_data['tmx_x'] = tmx_x  # Guardar originales para debug
        converted_data['tmx_y'] = tmx_y
        
        converted_operators[op_id] = converted_data
    
    return converted_operators

if __name__ == "__main__":
    # Test del convertidor
    print("Testing TMX Screen Converter...")
    
    # Activar TMX
    try:
        from force_tmx_activation import force_tmx_activation
        force_tmx_activation()
    except ImportError:
        print("Error: No se pudo activar TMX")
        exit(1)
    
    # Test conversión
    converter = TMXScreenConverter()
    converter.initialize_for_screen(1920, 1080)
    
    # Test de coordenadas
    test_coords = [
        (0, 0),      # Esquina superior izquierda TMX
        (959, 959),  # Esquina inferior derecha TMX
        (320, 128),  # Coordenada típica de operario
        (837, 297),  # Otra coordenada típica
        (480, 480),  # Centro del layout TMX
    ]
    
    print("\nTest de conversión TMX -> Pantalla:")
    for tmx_x, tmx_y in test_coords:
        screen_x, screen_y = converter.convert_tmx_to_screen(tmx_x, tmx_y)
        print(f"TMX ({tmx_x:3d}, {tmx_y:3d}) -> Pantalla ({screen_x:4d}, {screen_y:4d})")
    
    # Mostrar área de layout
    bounds = converter.get_layout_bounds_on_screen()
    if bounds:
        print(f"\nÁrea de layout en pantalla:")
        print(f"  X: {bounds['min_x']} a {bounds['max_x']} (ancho: {bounds['max_x'] - bounds['min_x']})")
        print(f"  Y: {bounds['min_y']} a {bounds['max_y']} (alto: {bounds['max_y'] - bounds['min_y']})")