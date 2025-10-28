# ANALISIS: Disminucion Gradual de Volumen en Dashboard

**Fecha:** 2025-10-27
**Problema Reportado:** El volumen no disminuye gradualmente en las barras del dashboard cuando los operarios descargan parcialmente en stagings

---

## PROBLEMA IDENTIFICADO

### Comportamiento Actual (INCORRECTO):
- Los operarios descargan en multiples staging areas
- El volumen del operario se mantiene constante en el dashboard
- Solo se actualiza cuando el operario termina de descargar todo (cargo_volume = 0)
- No hay actualizacion gradual del volumen en las barras del dashboard

### Comportamiento Esperado (CORRECTO):
- Los operarios descargan progresivamente en cada staging
- El volumen deberia disminuir gradualmente en las barras del dashboard
- Cada descarga parcial deberia actualizar el volumen visible
- El usuario deberia ver la disminucion progresiva del volumen

---

## AUDITORIA EXHAUSTIVA

### 1. GENERACION DE EVENTOS (operators.py)

#### Eventos Generados:

**A) Eventos `estado_agente` (linea 554 y 939):**
```python
self.almacen.registrar_evento('estado_agente', {
    'agent_id': self.id,
    'agent_type': self.type,
    'position': self.current_position,
    'status': 'idle',
    'current_task': None,
    'cargo_volume': self.cargo_volume  # <--- Volumen actual
})
```

**B) Eventos `partial_discharge` (linea 541 y 921):**
```python
self.almacen.registrar_evento('partial_discharge', {
    'agent_id': self.id,
    'staging_id': staging_id,
    'wos_descargadas': [wo.id for wo in staging_wos],
    'volumen_descargado': volumen_staging,
    'cargo_restante': self.cargo_volume,  # <--- Volumen DESPUES de descarga
    'timestamp': self.env.now
})
```

**C) Orden de Eventos Generados:**

```
ANTES DE DESCARGA EN STAGING 1:
- evento 'estado_agente' con cargo_volume = 150L (antes)

DURANTE DESCARGA EN STAGING 1:
- evento 'partial_discharge' con cargo_restante = 100L (despues de descargar 50L)

DESPUES DE DESCARGA EN STAGING 1:
- evento 'estado_agente' con cargo_volume = 100L (actualizado)

DURANTE DESCARGA EN STAGING 2:
- evento 'partial_discharge' con cargo_restante = 50L (despues de descargar 50L)

DESPUES DE DESCARGA EN STAGING 2:
- evento 'estado_agente' con cargo_volume = 50L (actualizado)
```

### 2. PROCESAMIENTO EN REPLAY ENGINE

**Archivo:** `src/engines/replay_engine.py`

**Metodo:** `_process_event_batch()` (linea 504)

#### Problema Encontrado:

El replay engine SOLO procesa eventos `estado_agente` pero NO procesa eventos `partial_discharge`:

```python
elif event_type == 'estado_agente':
    # Actualiza estado_visual
    if agent_id not in estado_visual["operarios"]:
        estado_visual["operarios"][agent_id] = {}
    estado_visual["operarios"][agent_id].update(data)
    
    # ... resto del codigo
```

**LO QUE FALTA:** No hay handler para `partial_discharge`

### 3. DASHBOARD WORLD-CLASS

**Archivo:** `src/subsystems/visualization/dashboard_world_class.py`

**Metodo:** `_render_single_operator()` (linea 728)

El dashboard usa el campo `carga_actual` del estado del operario:

```python
carga_actual = operario.get('carga_actual', 0)  # Obtiene de estado_visual["operarios"]
carga_porcentaje = (carga_actual / capacidad_max * 100)
```

**PROBLEMA:** El dashboard obtiene `carga_actual` desde `estado_visual["operarios"]`, pero este valor NO se actualiza cuando hay eventos `partial_discharge`

---

## CAUSA RAIZ

**PROBLEMA PRINCIPAL:** El replay engine NO procesa eventos `partial_discharge`, entonces el `cargo_volume` en `estado_visual["operarios"]` NO se actualiza hasta que llega el proximo evento `estado_agente`.

**FLUJO ACTUAL (INCORRECTO):**

```
Operario descarga 50L en staging 1:
  -> Genera evento 'partial_discharge' (ignorado por replay_engine)
  -> cargo_volume = 100L (internamente en operario)
  -> Dashboard muestra 150L (valor antiguo de estado_visual)

... tiempo despues ...
  -> Genera evento 'estado_agente' con cargo_volume = 100L
  -> Dashboard actualiza a 100L (salto grande)

Operario descarga 50L en staging 2:
  -> Genera evento 'partial_discharge' (ignorado por replay_engine)
  -> cargo_volume = 50L (internamente en operario)
  -> Dashboard muestra 100L (valor antiguo)

... tiempo despues ...
  -> Genera evento 'estado_agente' con cargo_volume = 50L
  -> Dashboard actualiza a 50L (salto grande)
```

---

## SOLUCION DISEÑADA

### Paso 1: Agregar Handler para `partial_discharge` en replay_engine.py

**Archivo:** `src/engines/replay_engine.py`

**Ubicacion:** En metodo `_process_event_batch()`, despues de la linea 525

**Codigo a agregar:**

```python
elif event_type == 'partial_discharge':
    agent_id = evento.get('agent_id')
    cargo_restante = evento.get('cargo_restante', 0)
    
    if agent_id:
        # Actualizar inmediatamente el cargo_volume en estado_visual
        if agent_id not in estado_visual["operarios"]:
            estado_visual["operarios"][agent_id] = {}
        
        # ACTUALIZAR EL VOLUMEN EN EL ESTADO VISUAL
        estado_visual["operarios"][agent_id]['carga'] = cargo_restante
        estado_visual["operarios"][agent_id]['cargo_volume'] = cargo_restante
        
        print(f"[PARTIAL-DISCHARGE] {agent_id} cargo actualizado a {cargo_restante}L")
```

### Paso 2: Verificar que `carga_actual` se lee correctamente

**Archivo:** `src/subsystems/visualization/dashboard_world_class.py`

**Linea 786:** Actualmente lee `carga_actual`

**Modificar para leer `cargo_volume` tambien:**

```python
# ACTUAL:
carga_actual = operario.get('carga_actual', 0)

# CAMBIAR A:
carga_actual = operario.get('carga_actual') or operario.get('cargo_volume', 0)
```

### Paso 3: Verificar sincronizacion con `estado_visual`

El `estado_visual` es global y se usa tanto para el dashboard de pygame como para el dashboard de PyQt6 (multiproceso).

Asegurar que ambos dashboard usen la misma clave para el volumen.

---

## IMPACTOS Y RIESGOS

### Impactos Positivos:
- El dashboard mostrara disminucion gradual del volumen
- Mejor feedback visual para el usuario
- Mas realista y profesional

### Riesgos:
- Si el handler no actualiza correctamente, puede causar inconsistencias
- Debe asegurarse que `partial_discharge` se genere ANTES de `estado_agente`
- El volumen debe sincronizarse entre ambos dashboard (Pygame y PyQt6)

---

## VALIDACION

### Criterios de Exito:
- [ ] Eventos `partial_discharge` se procesan correctamente
- [ ] `cargo_volume` se actualiza en `estado_visual` inmediatamente
- [ ] Las barras del dashboard muestran disminucion gradual
- [ ] No hay saltos de volumen visibles en la UI
- [ ] El volumen final es 0 cuando el operario descarga todo

### Tests a Realizar:
1. Generar simulacion con descarga multiple
2. Reproducir en replay viewer
3. Verificar que el volumen disminuye gradualmente en cada descarga
4. Verificar que no hay saltos visibles de volumen

---

## ARCHIVOS A MODIFICAR

1. `src/engines/replay_engine.py`
   - Agregar handler para `partial_discharge`
   - Actualizar `estado_visual["operarios"][agent_id]['cargo_volume']`

2. `src/subsystems/visualization/dashboard_world_class.py`
   - Modificar `_render_single_operator()` para leer `cargo_volume` ademas de `carga_actual`

---

**CONCLUSION:** El problema es que el replay engine NO procesa eventos `partial_discharge`, causando que el dashboard no refleje la disminucion gradual del volumen. La solucion es agregar un handler que actualice inmediatamente el `cargo_volume` en `estado_visual` cuando se procese un evento `partial_discharge`.

---

## IMPLEMENTACION REALIZADA

### Cambios Implementados:

#### 1. Agregado handler para `partial_discharge` en `replay_engine.py`

**Ubicacion:** Linea 526-541

```python
# ===== Partial Discharge Events =====
elif event_type == 'partial_discharge':
    agent_id = evento.get('agent_id')
    cargo_restante = evento.get('cargo_restante', 0)
    volumen_descargado = evento.get('volumen_descargado', 0)
    
    if agent_id:
        # Actualizar inmediatamente el cargo_volume en estado_visual
        if agent_id not in estado_visual["operarios"]:
            estado_visual["operarios"][agent_id] = {}
        
        # ACTUALIZAR EL VOLUMEN EN EL ESTADO VISUAL
        estado_visual["operarios"][agent_id]['carga'] = cargo_restante
        estado_visual["operarios"][agent_id]['cargo_volume'] = cargo_restante
        
        print(f"[PARTIAL-DISCHARGE] {agent_id} cargo actualizado a {cargo_restante}L (descargados {volumen_descargado}L)")
```

**Efecto:** El volumen se actualiza inmediatamente cuando se procesa un evento `partial_discharge`.

#### 2. Modificado dashboard para leer `cargo_volume`

**Ubicacion:** `dashboard_world_class.py` linea 787

**Antes:**
```python
carga_actual = operario.get('carga_actual', 0)
```

**Despues:**
```python
# Leer cargo_volume o carga_actual (prioridad a cargo_volume)
carga_actual = operario.get('cargo_volume') or operario.get('carga_actual', 0)
```

**Efecto:** El dashboard ahora lee `cargo_volume` (que se actualiza en tiempo real) ademas de `carga_actual`.

---

## RESULTADO ESPERADO

### Comportamiento Nuevo (CORRECTO):

```
Operario descarga 50L en staging 1:
  -> Genera evento 'partial_discharge'
  -> Handler actualiza cargo_volume = 100L en estado_visual
  -> Dashboard muestra 100L (actualizacion inmediata)

Operario descarga 50L en staging 2:
  -> Genera evento 'partial_discharge'
  -> Handler actualiza cargo_volume = 50L en estado_visual
  -> Dashboard muestra 50L (actualizacion inmediata)

Operario descarga 50L en staging 3:
  -> Genera evento 'partial_discharge'
  -> Handler actualiza cargo_volume = 0L en estado_visual
  -> Dashboard muestra 0L (actualizacion inmediata)
```

El volumen disminuye gradualmente en cada descarga, mostrando una transicion suave en las barras del dashboard.

---

## VALIDACION

### Criterios de Exito:
- [x] Eventos `partial_discharge` se procesan correctamente
- [x] `cargo_volume` se actualiza en `estado_visual` inmediatamente
- [ ] Las barras del dashboard muestran disminucion gradual (necesita testing)
- [ ] No hay saltos de volumen visibles en la UI (necesita testing)
- [ ] El volumen final es 0 cuando el operario descarga todo (necesita testing)

### Tests a Realizar:
1. Generar simulacion con descarga multiple
2. Reproducir en replay viewer
3. Verificar que el volumen disminuye gradualmente en cada descarga
4. Verificar que no hay saltos visibles de volumen

---

## ARCHIVOS MODIFICADOS

1. ✅ `src/engines/replay_engine.py`
   - Agregado handler para `partial_discharge`
   - Actualiza `estado_visual["operarios"][agent_id]['cargo_volume']`

2. ✅ `src/subsystems/visualization/dashboard_world_class.py`
   - Modificado `_render_single_operator()` para leer `cargo_volume` ademas de `carga_actual`

---

**ESTADO:** Implementacion completa, requiere testing para validacion final.

