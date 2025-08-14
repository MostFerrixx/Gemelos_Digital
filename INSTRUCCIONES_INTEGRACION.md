
# INSTRUCCIONES DE INTEGRACIÓN - OPERATORS.PY

## OPCIÓN 1: Reemplazo Seguro Gradual (RECOMENDADO)

1. Hacer backup de operators.py:
   ```bash
   cp git/simulation/operators.py git/simulation/operators_backup.py
   ```

2. Modificar SOLO la línea 9 en operators.py:
   CAMBIAR:
   ```python
   from utils.pathfinding import mover_por_ruta_realista
   ```
   
   POR:
   ```python
   # from utils.pathfinding import mover_por_ruta_realista  # Sistema original
   from mover_por_ruta_mejorado import mover_por_ruta_realista  # Sistema mejorado
   ```

3. Copiar mover_por_ruta_mejorado.py al directorio git/simulation/

4. Probar el simulador normalmente

## OPCIÓN 2: A/B Testing Controlado

1. Antes de ejecutar el simulador:
   ```python
   from pathfinding_manager import cambiar_modo_pathfinding
   cambiar_modo_pathfinding("AB_TEST")  # 50% mejorado, 50% original
   ```

## ROLLBACK DE EMERGENCIA

Si algo falla, restaurar operators.py original:
```bash
cp git/simulation/operators_backup.py git/simulation/operators.py
```

## MONITOREO

Durante la ejecución, verificar estadísticas:
```python
from pathfinding_manager import mostrar_reporte_pathfinding
mostrar_reporte_pathfinding()
```

El sistema incluye rollback automático si detecta problemas.
