# CÓMO CREAR LAYOUTS TMX FUNCIONALES

## PROBLEMA ACTUAL:
PyTMX no puede leer los TMX creados con Tiled por incompatibilidades de formato.

## SOLUCIÓN TEMPORAL:
Usar layouts TMX simplificados generados programáticamente.

## LAYOUTS CREADOS:

### 1. layout_funcional.tmx (20x15)
- Layout básico de prueba
- Racks simples en patrón grid
- Pasillos navegables
- 3 objetos: depot, inbound, picking

### 2. mi_layout_personalizado.tmx (25x18)  
- Layout más grande y detallado
- Patrón de racks realista
- Pasillos principales horizontales
- 5 objetos especiales
- Múltiples zonas de picking

## USAR EN SIMULADOR:
1. python run_simulator.py
2. Tab "Layout del Almacén"
3. Seleccionar "layout_funcional" o "mi_layout_personalizado"
4. Estos SÍ deberían funcionar y mostrarse

## TILES USADOS:
- ID 1 (floor): Suelo navegable - tile 0 del tileset
- ID 2 (rack): Racks obstáculo - tile 1 del tileset  
- ID 3 (corridor): Pasillos - tile 2 del tileset

## PARA CREAR MÁS LAYOUTS:
Modificar este script o usar el patrón TMX simplificado.
