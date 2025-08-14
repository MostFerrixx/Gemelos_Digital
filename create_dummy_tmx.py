#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CREAR TMX DUMMY - Para activar layouts mejorados
"""

import os

def create_dummy_tmx_files():
    """Crear archivos TMX dummy que activarán los layouts mejorados"""
    
    print("Creando TMX dummy para layouts mejorados...")
    
    # TMX dummy para almacén pequeño
    dummy_small = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0" orientation="orthogonal" width="25" height="18" tilewidth="32" tileheight="32">
 <properties>
  <property name="layout_type" value="Almacen_Pequeño"/>
  <property name="description" value="Almacén pequeño con racks organizados"/>
 </properties>
 <tileset firstgid="1" name="warehouse" tilewidth="32" tileheight="32">
  <image source="warehouse_tileset.png" width="128" height="96"/>
 </tileset>
 <layer name="dummy" width="25" height="18">
  <data encoding="csv">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
  </data>
 </layer>
</map>'''
    
    # TMX dummy para almacén grande
    dummy_large = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0" orientation="orthogonal" width="35" height="25" tilewidth="32" tileheight="32">
 <properties>
  <property name="layout_type" value="Almacen_Grande"/>
  <property name="description" value="Almacén grande con múltiples zonas"/>
 </properties>
 <tileset firstgid="1" name="warehouse" tilewidth="32" tileheight="32">
  <image source="warehouse_tileset.png" width="128" height="96"/>
 </tileset>
 <layer name="dummy" width="35" height="25">
  <data encoding="csv">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
  </data>
 </layer>
</map>'''
    
    # TMX dummy para corredor central
    dummy_corridor = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0" orientation="orthogonal" width="30" height="20" tilewidth="32" tileheight="32">
 <properties>
  <property name="layout_type" value="Layout_Corredor_Central"/>
  <property name="description" value="Layout con corredor central principal"/>
 </properties>
 <tileset firstgid="1" name="warehouse" tilewidth="32" tileheight="32">
  <image source="warehouse_tileset.png" width="128" height="96"/>
 </tileset>
 <layer name="dummy" width="30" height="20">
  <data encoding="csv">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
  </data>
 </layer>
</map>'''
    
    # Guardar archivos
    layouts = [
        ("Almacen_Pequeño.tmx", dummy_small),
        ("Almacen_Grande.tmx", dummy_large), 
        ("Layout_Corredor_Central.tmx", dummy_corridor)
    ]
    
    for filename, content in layouts:
        path = f"layouts/{filename}"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"TMX dummy creado: {path}")
    
    print("\nEstos TMX activarán los layouts mejorados en el sistema fallback")

def main():
    """Crear TMX dummy"""
    create_dummy_tmx_files()

if __name__ == "__main__":
    main()