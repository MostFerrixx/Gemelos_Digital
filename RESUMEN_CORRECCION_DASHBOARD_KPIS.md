# RESUMEN: Correccion de KPIs del Dashboard

**Fecha:** 2025-10-27  
**Estado:** Correcciones Implementadas

---

## PROBLEMAS CORREGIDOS

### 1. WIP nunca disminuye

**Problema:** El KPI mostraba "58/58" siempre.

**Causa:** `estado_visual["work_orders"]` no se actualizaba durante el procesamiento de eventos.

**Solucion Implementada:**
Agregada actualizacion de `estado_visual["work_orders"]` al procesar eventos `work_order_update` en linea 522-525 de `replay_engine.py`.

```python
# CRITICAL FIX: Update estado_visual["work_orders"] so metrics work correctly
if wo_id not in estado_visual["work_orders"]:
    estado_visual["work_orders"][wo_id] = {}
estado_visual["work_orders"][wo_id].update(evento)
```

**Resultado Esperado:** WIP ahora deberia disminuir correctamente (58/58 -> 45/58 -> 0/58)

---

### 2. Throughput siempre vacio

**Problema:** T/put mostraba "-" siempre.

**Causa:** Dependia del mismo problema que WIP (workorders_completadas siempre era 0).

**Solucion Implementada:**
1. Corregido el calculo de throughput en lineas 807-824
2. Agregado debug para verificacion cada 5 segundos

**Mejoras:**
- Cambio de formula: `(completadas / tiempo) * 60.0` (mas claro)
- Agregado logging cada 5 segundos para verificar valores

**Resultado Esperado:** T/put ahora deberia mostrar valores como "2.5/min"

---

### 3. Utilizacion vuelve a 0

**Problema:** Util aumenta momentaneamente pero luego vuelve a 0.

**Causa:** Dificil diagnosticar sin ver los estados reales.

**Solucion Implementada:**
Agregado logging en linea 570-571 para rastrear cambios de estado:

```python
# DEBUG: Track status changes for utilization calculation
if 'status' in data and data['status'] != prev_agent_state.get('status'):
    print(f"[DEBUG-UTIL] {agent_id}: {prev_agent_state.get('status', 'None')} -> {data['status']}")
```

**Resultado Esperado:** Con el debug podremos ver que estados se estan enviando y ajustar la logica en `state.py` si es necesario.

---

## ARCHIVOS MODIFICADOS

1. **src/engines/replay_engine.py**
   - Linea 522-525: Agregada actualizacion de estado_visual["work_orders"]
   - Linea 570-571: Agregado debug para cambios de estado
   - Linea 807-824: Mejorado calculo de throughput con debug

---

## PRUEBAS A REALIZAR

Despues de ejecutar una nueva simulacion:

1. **Verificar WIP:**
   - Debe empezar en 58/58
   - Debe ir disminuyendo progresivamente
   - Debe terminar en 0/58

2. **Verificar T/put:**
   - No debe mostrar "-"
   - Debe mostrar valores numericos (ej: "2.5/min")
   - Debe aumentar durante la simulacion

3. **Verificar Util:**
   - Debe aumentar cuando operarios comienzan a trabajar
   - Debe mantenerse > 0% mientras trabajan
   - Revisar logs [DEBUG-UTIL] para entender el comportamiento

---

## COMANDOS DE VALIDACION

```bash
# Generar nueva simulacion
python entry_points/run_generate_replay.py

# Ver replay con las correcciones
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

Durante el replay, observar:
- WIP disminuyendo en el dashboard
- T/put mostrando valores numericos
- Logs [DEBUG-THROUGHPUT] en la consola cada 5 segundos
- Logs [DEBUG-UTIL] en la consola cuando hay cambios de estado

---

## SIGUIENTE PASO

Si las correcciones no funcionan completamente:
1. Revisar los logs de [DEBUG-UTIL] para ver que estados se estan usando
2. Ajustar la logica en `state.py` funcion `actualizar_metricas_tiempo()` si es necesario
