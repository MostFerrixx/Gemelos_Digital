# -*- coding: utf-8 -*-
"""
Script de auditoría TMX para crear diccionario visual de tilesets
Mapea cada GID a sus propiedades personalizadas e imágenes asociadas.
"""

import pytmx
import sys

def inspect_tmx_tileset_dictionary():
    """Crea un diccionario visual definitivo de GIDs a propiedades TMX"""
    
    print("=" * 70)
    print("AUDITORIA: DICCIONARIO VISUAL DEL TILESET TMX")
    print("=" * 70)
    
    try:
        # Paso 1: Cargar el mapa TMX
        print("1. CARGANDO MAPA TMX...")
        tm = pytmx.TiledMap('layouts/WH1.tmx')
        print(f"   Mapa cargado exitosamente: {tm.width}x{tm.height} tiles")
        print(f"   Tamaño de tiles: {tm.tilewidth}x{tm.tileheight} píxeles")
        print()
        
        # Paso 2: Listar todas las capas
        print("2. LISTADO COMPLETO DE CAPAS...")
        for i, layer in enumerate(tm.layers):
            layer_name = getattr(layer, 'name', f'Layer_{i}')
            layer_type = type(layer).__name__
            print(f"   Capa {i+1}: '{layer_name}' (Tipo: {layer_type})")
        print()
        
        # Paso 3: Inspeccionar Tilesets y sus Propiedades (EL PASO CRÍTICO)
        print("3. INSPECCION CRITICA DE TILESETS Y PROPIEDADES...")
        
        tileset_dict = {}
        
        if hasattr(tm, 'tilesets') and tm.tilesets:
            for tileset_idx, tileset in enumerate(tm.tilesets):
                print(f"   Tileset {tileset_idx + 1}:")
                print(f"     Nombre: {getattr(tileset, 'name', 'Sin nombre')}")
                print(f"     First GID: {getattr(tileset, 'firstgid', 'N/A')}")
                print(f"     Tile Count: {getattr(tileset, 'tilecount', 'N/A')}")
                print(f"     Imagen: {getattr(tileset, 'source', 'N/A')}")
                print()
                
                # Usar get_tile_properties_by_gid para extraer propiedades
                first_gid = getattr(tileset, 'firstgid', 1)
                tile_count = getattr(tileset, 'tilecount', 0)
                
                print(f"     Tiles con propiedades personalizadas:")
                for gid in range(first_gid, first_gid + tile_count):
                    if hasattr(tm, 'get_tile_properties_by_gid'):
                        properties = tm.get_tile_properties_by_gid(gid)
                        if properties:
                            # Almacenar en diccionario
                            tileset_dict[gid] = {
                                'local_id': properties.get('id', gid - first_gid),
                                'properties': properties,
                                'tileset': tileset.name,
                                'image_source': getattr(tileset, 'source', None)
                            }
                            
                            # Extraer propiedades relevantes
                            tile_type = properties.get('type', 'sin_tipo')
                            walkable = properties.get('walkable', 'sin_walkable')
                            name = properties.get('name', 'sin_nombre')
                            
                            print(f"       GID {gid}: type='{tile_type}', walkable='{walkable}', name='{name}'")
                print()
        
        # Paso 4: Generar Diccionario Visual
        print("4. DICCIONARIO VISUAL DEFINITIVO...")
        print("=" * 50)
        print(f"{'GID':<5} | {'Propiedades Personalizadas':<40}")
        print("=" * 50)
        
        for gid in sorted(tileset_dict.keys()):
            props = tileset_dict[gid]['properties']
            props_str = str(props) if props else "{sin propiedades}"
            print(f"{gid:<5} | {props_str:<40}")
        
        print("=" * 50)
        print()
        
        # Paso 5: Análisis de Discrepancia
        print("5. ANALISIS DE DISCREPANCIA CON MAPEO ANTERIOR...")
        
        # Mapeo anterior (incorrecto) que usamos
        previous_mapping = {
            1: "floor (suelo navegable)",
            2: "rack (racks/estantes - MUROS)",
            3: "picking_location (puntos de picking)",
            4: "parking (estacionamiento)",
            5: "depot (zona depot)",
            6: "inbound (zona entrada)"
        }
        
        print("   MAPEO ANTERIOR (ASUMIDO):")
        for gid, description in previous_mapping.items():
            print(f"     GID {gid}: {description}")
        print()
        
        print("   MAPEO REAL (BASADO EN PROPIEDADES TMX):")
        discrepancies = []
        
        for gid in sorted(previous_mapping.keys()):
            if gid in tileset_dict:
                real_props = tileset_dict[gid]['properties']
                real_type = real_props.get('type', 'sin_tipo')
                real_name = real_props.get('name', 'sin_nombre')
                real_walkable = real_props.get('walkable', 'sin_walkable')
                
                print(f"     GID {gid}: type='{real_type}', name='{real_name}', walkable='{real_walkable}'")
                
                # Comparar con asunción anterior
                assumed_type = "rack" if gid == 2 else "floor"
                if real_type != assumed_type and gid == 2:
                    discrepancies.append(f"GID {gid}: Se asumió 'rack', pero realmente es '{real_type}'")
            else:
                print(f"     GID {gid}: NO TIENE PROPIEDADES DEFINIDAS EN TMX")
                discrepancies.append(f"GID {gid}: No existe en tileset TMX")
        
        print()
        if discrepancies:
            print("   DISCREPANCIAS ENCONTRADAS:")
            for disc in discrepancies:
                print(f"     - {disc}")
        else:
            print("   No se encontraron discrepancias significativas.")
        
        print()
        
        # Paso 6: Lógica Condicional Definitiva
        print("6. LOGICA CONDICIONAL DEFINITIVA...")
        
        # Identificar muros basados en propiedades reales
        wall_conditions = []
        floor_conditions = []
        
        for gid, data in tileset_dict.items():
            props = data['properties']
            tile_type = props.get('type', '')
            walkable = props.get('walkable', '')
            
            if tile_type == 'rack' or walkable == 'false':
                wall_conditions.append(f"gid == {gid}")  # {props.get('name', 'Sin nombre')}
            elif walkable == 'true':
                floor_conditions.append(f"gid == {gid}")  # {props.get('name', 'Sin nombre')}
        
        print("   CODIGO PYTHON DEFINITIVO:")
        print()
        print("   # Identificar muros/obstáculos:")
        if wall_conditions:
            wall_logic = " or ".join(wall_conditions)
            print(f"   is_wall = {wall_logic}")
        else:
            print("   is_wall = False  # No hay muros definidos en TMX")
        
        print()
        print("   # Identificar suelo navegable:")
        if floor_conditions:
            floor_logic = " or ".join(floor_conditions)
            print(f"   is_walkable = {floor_logic}")
        else:
            print("   is_walkable = True  # Todos son navegables por defecto")
        
        print()
        print("   # Usando propiedades TMX (método más robusto):")
        print("   tile_properties = tm.get_tile_properties_by_gid(gid)")
        print("   if tile_properties:")
        print("       is_wall = tile_properties.get('walkable') == 'false'")
        print("       tile_type = tile_properties.get('type', 'unknown')")
        
    except Exception as e:
        print(f"ERROR CRITICO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_tmx_tileset_dictionary()