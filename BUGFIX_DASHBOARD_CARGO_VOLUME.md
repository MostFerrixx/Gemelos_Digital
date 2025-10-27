# Bugfix: Barras de Progreso de Litros en Dashboard World-Class

**Fecha:** 2025-10-27  
**Reportado por:** Usuario  
**Severidad:** Media  
**Estado:** RESUELTO

## Descripcion del Problema

En el dashboard lateral (World-Class) de operarios activos, las barras de progreso que muestran la cantidad de litros "pickeados" por cada operario no se actualizaban correctamente. A pesar de que los operarios estaban realizando trabajos y cargando mercaderia, el dashboard siempre mostraba "0/1000 L" (o "0/150 L" para operarios terrestres).

### Imagen de Evidencia
El usuario reporto que Forklift-01 (FL1) estaba "En ruta" hacia el area de salida (outbound staging) con mercaderia cargada, pero el dashboard mostraba "0/1000 L".

## Analisis del Bug

### Causa Raiz
El bug se encontraba en el archivo `src/subsystems/simulation/operators.py`:

**Problema 1 - Forklift (Linea 720-734):**
```python
# ANTES (INCORRECTO):
if wo:
    wo.cantidad_restante = 0  # Se pone en 0 primero
    # ... ejecutions tracking ...
    
    self.cargo_volume += wo.calcular_volumen_restante()  # Suma 0 porque ya se puso en 0!
```

El codigo estaba:
1. Poniendo `wo.cantidad_restante = 0` primero
2. Luego sumando el volumen con `self.cargo_volume += wo.calcular_volumen_restante()`
3. Como `cantidad_restante` ya era 0`, el metodo `calcular_volumen_restante()` retornaba 0
4. Entonces `cargo_volume` nunca se actualizaba

**Problema 2 - GroundOperator (Linea 381-404):**
El operario terrestre ni siquiera actualizaba `cargo_volume` despues del picking. Solo lo limpiaba al descargar en staging.

### Flujo de Datos
```
Operador -> cargo_volume (actualizado correctamente)
     |
     v
registrar_evento('estado_agente', {
    'cargo_volume': self.cargo_volume  # Este valor era siempre 0
})
     |
     v
ReplayBuffer -> Archivo .jsonl
     |
     v
ReplayViewer -> Dashboard
     |
     v
Mostrar "X/1000 L" en pantalla
```

## Solucion Implementada

### Correccion 1 - Forklift (Linea 720-724)
```python
# DESPUES (CORRECTO):
# ACTUALIZAR CARGO_VOLUME ANTES de poner cantidad_restante = 0
if wo:
    # Sumar el volumen ANTES de modificar cantidad_restante
    self.cargo_volume += wo.calcular_volumen_restante()
    wo.cantidad_restante = 0
    # ... resto del codigo ...
```

### Correccion 2 - GroundOperator (Linea 381-408)
```python
# DESPUES (CORRECTO):
# ACTUALIZAR CARGO_VOLUME ANTES de poner cantidad_restante = 0
if wo:
    # Sumar el volumen ANTES de modificar cantidad_restante
    self.cargo_volume += wo.calcular_volumen_restante()
    wo.status = 'picked'
    wo.cantidad_restante = 0
    # ... resto del codigo ...
```

### Cambios Realizados

**Archivo:** `src/subsystems/simulation/operators.py`

1. **Linea 720-728:** Reorganizado el orden de actualizacion en `Forklift.agent_process()` para actualizar `cargo_volume` ANTES de poner `cantidad_restante = 0`
2. **Linea 381-408:** Agregada actualizacion de `cargo_volume` en `GroundOperator.agent_process()` siguiendo el mismo patron correcto

## Validacion

### Archivos Modificados
- `src/subsystems/simulation/operators.py` (2 cambios)

### Testing
1. Generar replay con la correccion: `python entry_points/run_generate_replay.py`
2. Visualizar replay: `python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl`
3. Verificar que las barras de progreso ahora muestran valores correctos

### Resultados Esperados
- Las barras de progreso en el dashboard deberian actualizarse correctamente
- Los operarios deberian mostrar cantidad correcta de litros "pickeados"
- Las barras deberian llenarse a medida que los operarios realizan picking

## Impacto

### Componentes Afectados
- Dashboard World-Class (`src/subsystems/visualization/dashboard_world_class.py`) - NO requiere cambios (recibe datos correctos)
- Eventos `estado_agente` - Ahora incluyen `cargo_volume` correcto
- Archivos .jsonl - Ahora contienen datos correctos de cargo

### Archivos de Replay
Los archivos .jsonl generados ahora contienen:
```jsonl
{"type":"estado_agente","timestamp":123.45,"agent_id":"Forklift-01",...,"cargo_volume":750,"carga":750,"capacidad":1000}
```

## Referencias

- Archivo original con bug: `src/subsystems/simulation/operators.py` (lineas 720-734, 381-404)
- Dashboard que muestra el dato: `src/subsystems/visualization/dashboard_world_class.py` (linea 784-808)
- Flujo de eventos: `src/subsystems/simulation/warehouse.py` (linea 484-554)

## Notas Adicionales

### Metodo `calcular_volumen_restante()`
Este metodo de WorkOrder calcula el volumen basado en `cantidad_restante`. Por eso es critico llamarlo ANTES de poner `cantidad_restante = 0`.

### Campo `capacidad` en eventos
En `warehouse.py` (linea 543), el campo `capacidad` se define como:
```python
'capacidad': 150 if datos.get('tipo') == 'GroundOperator' else 1000
```

Esto significa:
- GroundOperator: Capacidad de 150 L
- Forklift: Capacidad de 1000 L

Estos valores deben coincidir con los definidos en `config.json` bajo la seccion `operarios`.

---

**Estado Final:** RESUELTO  
**Commit:** Pendiente  
**Fecha Resolucion:** 2025-10-27

