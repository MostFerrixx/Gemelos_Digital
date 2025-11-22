# RESUMEN: Solucion para Disminucion Gradual de Volumen

**Fecha:** 2025-10-27
**Estado:** IMPLEMENTACION COMPLETADA

---

## PROBLEMA ORIGINAL

El volumen NO disminuye gradualmente en las barras del dashboard cuando los operarios descargan en multiples staging areas. El volumen solo cambia cuando el operario termina de descargar todo.

---

## DIAGNOSTICO COMPLETO

### Problema 1: Handler Faltante
**Solucion:** Agregar handler para `partial_discharge` en `replay_engine.py` (linea 526-548)
- Procesa eventos `partial_discharge` correctamente
- Actualiza `estado_visual["operarios"][agent_id]['carga']` y `['cargo_volume']`
- ✅ IMPLEMENTADO

### Problema 2: Dashboard No Lee cargo_volume
**Solucion:** Modificar dashboard para leer `cargo_volume` ademas de `carga_actual` (linea 693 y 787)
- Lee `cargo_volume` en `_render_operators_list()`
- Lee `cargo_volume` en `_render_single_operator()`
- ✅ IMPLEMENTADO

### Problema 3: volumen_descargado Siempre 0
**Causa Raiz:** 
- `volumen_staging` se calculaba como: `sum(wo.calcular_volumen_restante() for wo in staging_wos)`
- Pero DESPUES del picking, `cantidad_restante = 0`
- Por lo tanto `calcular_volumen_restante()` retorna 0
- Por lo tanto `volumen_staging` es siempre 0
- Por lo tanto NO hay cambio visible

**Solucion:** 
- Cambiar calculo de `volumen_staging` para usar `wo.cantidad_inicial * wo.sku.volumen`
- Esto calcula el volumen REAL de los WOs (independientemente de `cantidad_restante`)
- ✅ IMPLEMENTADO (linea 467 y 847 en `operators.py`)

---

## CAMBIOS IMPLEMENTADOS

### 1. Handler para partial_discharge (replay_engine.py)
**Ubicacion:** Linea 526-548

```python
elif event_type == 'partial_discharge':
    agent_id = evento.get('agent_id')
    cargo_restante = evento.get('cargo_restante', 0)
    volumen_descargado = evento.get('volumen_descargado', 0)
    
    if agent_id:
        if agent_id not in estado_visual["operarios"]:
            estado_visual["operarios"][agent_id] = {}
        
        volumen_anterior = estado_visual["operarios"][agent_id].get('carga', 0)
        estado_visual["operarios"][agent_id]['carga'] = cargo_restante
        estado_visual["operarios"][agent_id]['cargo_volume'] = cargo_restante
        
        print(f"[PARTIAL-DISCHARGE] {agent_id}: {volumen_anterior}L -> {cargo_restante}L (descargados {volumen_descargado}L)")
```

### 2. Dashboard Lee cargo_volume (dashboard_world_class.py)
**Ubicacion:** Lineas 693 y 787

```python
# Linea 693: Al crear operario dict
carga_value = operator_data.get('cargo_volume') or operator_data.get('carga', 0)
operario = {
    'carga_actual': carga_value,
    ...
}

# Linea 787: Al renderizar operario
carga_actual = operario.get('cargo_volume') or operario.get('carga_actual', 0)
```

### 3. Calculo Correcto de volumen_staging (operators.py)
**Ubicacion:** Lineas 467 y 847

```python
# ANTES (INCORRECTO):
volumen_staging = sum(wo.calcular_volumen_restante() for wo in staging_wos)  # Retorna 0

# DESPUES (CORRECTO):
volumen_staging = sum(wo.cantidad_inicial * wo.sku.volumen for wo in staging_wos)  # Volumen real
```

---

## RESULTADO ESPERADO

Despues de estas correcciones, los eventos deberian mostrar:

```
[PARTIAL-DISCHARGE] GroundOp-01: 150L -> 120L (descargados 30L) en t=340.0s
[PARTIAL-DISCHARGE] GroundOp-01: 120L -> 90L (descargados 30L) en t=350.0s
[PARTIAL-DISCHARGE] GroundOp-01: 90L -> 0L (descargados 90L) en t=360.0s
```

Y el dashboard deberia mostrar la disminucion gradual del volumen en cada descarga.

---

## ARCHIVOS MODIFICADOS

1. ✅ `src/engines/replay_engine.py` - Handler para `partial_discharge`
2. ✅ `src/subsystems/visualization/dashboard_world_class.py` - Lee `cargo_volume`
3. ✅ `src/subsystems/simulation/operators.py` - Calculo correcto de `volumen_staging`

---

**ESTADO:** Implementacion completa, requiere validacion final

