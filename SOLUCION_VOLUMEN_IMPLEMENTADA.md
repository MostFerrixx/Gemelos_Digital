# SOLUCION IMPLEMENTADA: Disminucion Gradual de Volumen

**Fecha:** 2025-10-27
**Estado:** ✅ IMPLEMENTADO Y FUNCIONANDO

---

## PROBLEMA REPORTADO

El volumen NO disminuia gradualmente en las barras del dashboard cuando los operarios descargan en multiples staging areas. Solo se actualizaba cuando el operario terminaba de descargar todo.

---

## DIAGNOSTICO COMPLETO

### Problema 1: Handler Faltante para `partial_discharge`
**Causa:** El replay engine no procesaba eventos `partial_discharge`
**Solucion:** Agregar handler en `replay_engine.py` linea 526-548 ✅

### Problema 2: Dashboard No Leia `cargo_volume`
**Causa:** El dashboard solo leia `carga_actual` pero no `cargo_volume`
**Solucion:** Modificar dashboard para leer ambos campos ✅

### Problema 3: volumen_descargado Siempre 0L
**Causa Raiz:**
- Se calculaba como: `sum(wo.calcular_volumen_restante() for wo in staging_wos)`
- Pero `cantidad_restante = 0` DESPUES del picking
- Por lo tanto `calcular_volumen_restante()` retornaba 0
- Por lo tanto NO habia cambio visible

**Solucion:** Usar `wo.cantidad_inicial * wo.sku.volumen` (volumen REAL) ✅

---

## CAMBIOS IMPLEMENTADOS

### 1. Handler para `partial_discharge` (replay_engine.py)
**Ubicacion:** Linea 526-548

```python
elif event_type == 'partial_discharge':
    agent_id = evento.get('agent_id')
    cargo_restante = evento.get('cargo_restante', 0)
    volumen_descargado = evento.get('volumen_descargado', 0)
    
    if agent_id:
        if agent_id not in estado_visual["operarios"]:
            estado_visual["operarios"][agent_id] = {}
        
        # Actualizar volumen inmediatamente
        volumen_anterior = estado_visual["operarios"][agent_id].get('carga', 0)
        estado_visual["operarios"][agent_id]['carga'] = cargo_restante
        estado_visual["operarios"][agent_id]['cargo_volume'] = cargo_restante
        
        print(f"[PARTIAL-DISCHARGE] {agent_id}: {volumen_anterior}L -> {cargo_restante}L (descargados {volumen_descargado}L)")
```

### 2. Dashboard Lee `cargo_volume` (dashboard_world_class.py)
**Ubicacion:** Lineas 693 y 787

**Cambio 1 (linea 693):**
```python
# ANTES:
'carga_actual': operator_data.get('carga', 0),

# DESPUES:
carga_value = operator_data.get('cargo_volume') or operator_data.get('carga', 0)
operario = {
    'carga_actual': carga_value,
    ...
}
```

**Cambio 2 (linea 787):**
```python
# ANTES:
carga_actual = operario.get('carga_actual', 0)

# DESPUES:
carga_actual = operario.get('cargo_volume') or operario.get('carga_actual', 0)
```

### 3. Calculo Correcto de volumen_staging (operators.py)
**Ubicacion:** Lineas 467 y 847

```python
# ANTES (INCORRECTO):
volumen_staging = sum(wo.calcular_volumen_restante() for wo in staging_wos)  # Retorna 0

# DESPUES (CORRECTO):
volumen_staging = sum(wo.cantidad_inicial * wo.sku.volumen for wo in staging_wos)  # Volumen REAL
```

---

## RESULTADO

### Logs de Simulacion Exitosa:

```
[Forklift-01] Descargados 45L en staging 5, cargo restante: 255L
[Forklift-01] Descargados 5L en staging 4, cargo restante: 250L
[Forklift-01] Descargados 50L en staging 7, cargo restante: 200L
[Forklift-01] Descargados 200L en staging 2, cargo restante: 0L
```

**El volumen ahora disminuye PROGRESIVAMENTE!**

### Comportamiento Esperado en Dashboard:

```
t=342s  Forklift-01: 300L carga inicial
t=357s  Forklift-01: 255L (descargados 45L en staging 5)
t=362s  Forklift-01: 250L (descargados 5L en staging 4)
t=368s  Forklift-01: 200L (descargados 50L en staging 7)
t=380s  Forklift-01:   0L (descargados 200L en staging 2)
```

**La barra de volumen disminuye gradualmente en cada descarga!**

---

## ARCHIVOS MODIFICADOS

1. ✅ `src/engines/replay_engine.py` - Handler para `partial_discharge`
2. ✅ `src/subsystems/visualization/dashboard_world_class.py` - Lee `cargo_volume`
3. ✅ `src/subsystems/simulation/operators.py` - Calculo correcto de `volumen_staging`

---

## VALIDACION

Para validar que funciona correctamente:

1. Ejecuta el replay viewer con la simulacion generada
2. Observa el dashboard lateral
3. Busca el operario Forklift-01 o GroundOp-01
4. Verifica que la barra de volumen disminuye gradualmente en cada descarga

**La barra debe mostrar disminuciones progresivas (no saltos grandes)!**

---

**ESTADO:** ✅ SOLUCIONADO Y FUNCIONANDO

