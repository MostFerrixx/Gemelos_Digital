#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTEGRACIÓN DE LAYOUTS PERSONALIZADOS - Sistema para usar texturas del usuario
"""

import os
import sys
import json
from typing import Dict, List, Optional, Tuple

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

class CustomLayoutIntegration:
    """Integración de layouts personalizados con texturas del usuario"""
    
    def __init__(self):
        self.layouts_folder = "layouts"
        self.custom_mapping_file = "layouts/custom_tileset_mapping.json"
        self.custom_mapping = None
        
    def load_custom_tileset_mapping(self):
        """Cargar mapeo de tileset personalizado"""
        
        if not os.path.exists(self.custom_mapping_file):
            print("No hay tileset personalizado configurado")
            return False
            
        try:
            with open(self.custom_mapping_file, 'r', encoding='utf-8') as f:
                self.custom_mapping = json.load(f)
                
            print(f"Tileset personalizado cargado: {self.custom_mapping['tileset_name']}")
            print(f"Tiles configurados: {len(self.custom_mapping['tiles'])}")
            
            return True
            
        except Exception as e:
            print(f"Error cargando tileset personalizado: {e}")
            return False
            
    def get_tile_properties_by_id(self, tile_id: int) -> Optional[Dict]:
        """Obtener propiedades de un tile por su ID"""
        
        if not self.custom_mapping:
            return None
            
        for tile in self.custom_mapping['tiles']:
            if tile['id'] == tile_id:
                return tile
                
        return None
        
    def get_walkable_tile_ids(self) -> List[int]:
        """Obtener IDs de tiles navegables"""
        
        if not self.custom_mapping:
            return [0]  # Fallback
            
        walkable_ids = []
        for tile in self.custom_mapping['tiles']:
            if tile.get('walkable', False):
                walkable_ids.append(tile['id'])
                
        return walkable_ids if walkable_ids else [0]
        
    def get_obstacle_tile_ids(self) -> List[int]:
        """Obtener IDs de tiles obstáculo"""
        
        if not self.custom_mapping:
            return [1]  # Fallback
            
        obstacle_ids = []
        for tile in self.custom_mapping['tiles']:
            if not tile.get('walkable', True):
                obstacle_ids.append(tile['id'])
                
        return obstacle_ids if obstacle_ids else [1]
        
    def interpret_tmx_tile(self, tile_gid: int) -> Dict:
        """Interpretar tile TMX usando mapeo personalizado"""
        
        # Extraer ID real del tile (sin flags de rotación/flip)
        tile_id = tile_gid & 0x0FFFFFFF
        
        if tile_id == 0:  # Tile vacío
            return {
                'walkable': True,
                'type': 'empty',
                'navigation_value': 1
            }
            
        # Buscar en mapeo personalizado
        tile_props = self.get_tile_properties_by_id(tile_id - 1)  # TMX es 1-indexed
        
        if tile_props:
            return {
                'walkable': tile_props.get('walkable', True),
                'type': tile_props.get('type', 'unknown'),
                'navigation_value': 1 if tile_props.get('walkable', True) else 0,
                'name': tile_props.get('name', 'Unknown'),
                'description': tile_props.get('description', '')
            }
        else:
            # Fallback para tiles no configurados
            return {
                'walkable': True,
                'type': 'unknown',
                'navigation_value': 1
            }
            
    def create_navigation_matrix_from_tmx_data(self, tmx_data, width: int, height: int) -> List[List[int]]:
        """Crear matriz de navegación desde datos TMX usando mapeo personalizado"""
        
        # Inicializar matriz
        matrix = [[1 for _ in range(width)] for _ in range(height)]
        
        # Si no hay datos TMX, usar matriz por defecto
        if not tmx_data:
            print("No hay datos TMX, usando matriz por defecto")
            return matrix
            
        try:
            # Buscar capa principal de tiles
            main_layer = None
            for layer in tmx_data.visible_layers:
                if hasattr(layer, 'data'):  # Es una capa de tiles
                    main_layer = layer
                    break
                    
            if not main_layer:
                print("No se encontró capa de tiles principal")
                return matrix
                
            print(f"Procesando capa: {getattr(main_layer, 'name', 'Sin nombre')}")
            
            # Procesar cada tile de la capa
            for y in range(height):
                for x in range(width):
                    if y < len(main_layer.data) and x < len(main_layer.data[y]):
                        tile_gid = main_layer.data[y][x]
                        tile_info = self.interpret_tmx_tile(tile_gid)
                        matrix[y][x] = tile_info['navigation_value']
                        
        except Exception as e:
            print(f"Error procesando datos TMX: {e}")
            # Retornar matriz por defecto en caso de error
            
        return matrix
        
    def patch_dynamic_layout_loader(self):
        """Aplicar patch al dynamic layout loader para usar texturas personalizadas"""
        
        try:
            from dynamic_layout_loader import DynamicLayoutLoader
            
            # Cargar mapeo personalizado
            if not self.load_custom_tileset_mapping():
                print("No se puede aplicar patch: no hay tileset personalizado")
                return False
                
            # Crear instancia de integración
            integration = self
            
            # Método mejorado para extraer matriz de navegación
            def _extract_navigation_matrix_custom(self, tmx_data, layout_info):
                """Extraer matriz de navegación usando mapeo personalizado"""
                
                width = layout_info.get('width', 50)
                height = layout_info.get('height', 30)
                
                print(f"Extrayendo matriz personalizada: {width}x{height}")
                
                # Usar integración personalizada
                matrix = integration.create_navigation_matrix_from_tmx_data(tmx_data, width, height)
                
                # Estadísticas
                total_tiles = width * height
                walkable_tiles = sum(sum(row) for row in matrix)
                walkable_pct = (walkable_tiles / total_tiles) * 100
                
                print(f"Matriz extraída: {walkable_tiles}/{total_tiles} navegables ({walkable_pct:.1f}%)")
                
                return matrix
                
            # Guardar método original
            if not hasattr(DynamicLayoutLoader, '_extract_navigation_matrix_original'):
                DynamicLayoutLoader._extract_navigation_matrix_original = DynamicLayoutLoader._extract_navigation_matrix
                
            # Aplicar método personalizado
            DynamicLayoutLoader._extract_navigation_matrix = _extract_navigation_matrix_custom
            
            print("[PATCH] Dynamic Layout Loader parcheado para texturas personalizadas")
            return True
            
        except Exception as e:
            print(f"Error aplicando patch personalizado: {e}")
            return False
            
    def create_example_layout_instructions(self):
        """Crear instrucciones para layouts personalizados"""
        
        if not self.custom_mapping:
            print("Carga primero el mapeo personalizado")
            return
            
        instructions = f"""# INSTRUCCIONES PARA LAYOUTS PERSONALIZADOS

## Tileset personalizado configurado: {self.custom_mapping['tileset_name']}

### Tiles disponibles:

"""
        
        for tile in self.custom_mapping['tiles']:
            walkable_icon = "🚶" if tile['walkable'] else "🚫"
            instructions += f"**ID {tile['id']}**: {tile['name']} {walkable_icon}\n"
            instructions += f"  - Tipo: {tile['type']}\n"
            instructions += f"  - Navegable: {'Sí' if tile['walkable'] else 'No'}\n"
            instructions += f"  - Descripción: {tile['description']}\n"
            instructions += f"  - Textura: {tile['texture_file']}\n\n"
            
        instructions += f"""
### Cómo crear tu layout en Tiled:

1. **Abrir Tiled**
2. **Nuevo mapa**: File > New Map
   - Orientación: Orthogonal
   - Tile size: 32x32
   - Map size: El tamaño que prefieras
3. **Importar tileset**: Map > Add External Tileset
   - Seleccionar: `layouts/custom_warehouse_tileset.tsx`
4. **Pintar tu layout**:
   - Usar tiles navegables para pasillos
   - Usar tiles obstáculo para racks/paredes
   - Usar tiles especiales para depot, inbound, picking
5. **Guardar**: File > Save As... en carpeta `layouts/`

### Ejemplo de uso de tiles:

- **Pasillos principales**: Usar tiles tipo 'corridor' o 'floor'
- **Racks de almacén**: Usar tiles tipo 'rack' 
- **Paredes**: Usar tiles tipo 'wall'
- **Zona depot**: Usar tiles tipo 'depot'
- **Zona entrada**: Usar tiles tipo 'inbound'

### Objetos especiales (opcional):

Crear una **Object Layer** y agregar:
- 1 objeto "depot" en la zona de depot
- 1 objeto "inbound" en la zona de entrada  
- Varios objetos "picking" en puntos de interés

¡Tu layout personalizado estará listo para usar en el simulador!
"""
        
        instructions_path = "layouts/INSTRUCCIONES_LAYOUT_PERSONALIZADO.md"
        with open(instructions_path, 'w', encoding='utf-8') as f:
            f.write(instructions)
            
        print(f"Instrucciones guardadas: {instructions_path}")
        return instructions_path

def create_custom_layout_patch():
    """Crear y aplicar patch para layouts personalizados"""
    
    integration = CustomLayoutIntegration()
    
    # Aplicar patch si hay tileset personalizado
    if integration.patch_dynamic_layout_loader():
        integration.create_example_layout_instructions()
        return True
    else:
        print("Para usar layouts personalizados:")
        print("1. Ejecuta: python custom_tileset_generator.py")
        print("2. Configura tus texturas")
        print("3. Ejecuta este script nuevamente")
        return False

def main():
    """Crear patch para layouts personalizados"""
    
    print("="*60)
    print("INTEGRACIÓN DE LAYOUTS PERSONALIZADOS")
    print("="*60)
    
    result = create_custom_layout_patch()
    
    if result:
        print("\n[ÉXITO] Patch aplicado - Layouts personalizados habilitados")
    else:
        print("\n[INFO] Configura primero tu tileset personalizado")
        
    print("="*60)

if __name__ == "__main__":
    main()