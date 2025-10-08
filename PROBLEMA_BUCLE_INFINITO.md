# PROBLEMA: Bucle Infinito en Simulación Headless

**Fecha:** 2025-10-07  
**Problema:** La simulación no termina, queda en bucle infinito

---

## 🔴 PROBLEMA IDENTIFICADO

### Síntoma:
```
[DISPATCHER] 27119.00 - No hay WorkOrders pendientes para Forklift_Forklift-01
[DISPATCHER] 27119.77 - No hay WorkOrders pendientes para GroundOperator_GroundOp-01
... (se repite indefinidamente)
```

### Causa Raíz:
La condición de terminación `almacen.simulacion_ha_terminado()` no se cumple correctamente.

---

## 📊 ANÁLISIS

### Flujo Actual (INCORRECTO):
```
1. Todos los WorkOrders se completan
2. Operarios piden trabajo cada 1 segundo
3. Dispatcher dice "no hay trabajo"
4. Operarios verifican simulacion_ha_terminado() → FALSE ❌
5. GOTO paso 2 (bucle infinito)
```

### ¿Por qué `simulacion_ha_terminado()` retorna FALSE?

**Revisar:** `src/subsystems/simulation/warehouse.py:341-358`

```python
def simulacion_ha_terminado(self) -> bool:
    # Check if all work orders are completed
    if not self.dispatcher.lista_maestra_work_orders:
        # All work orders completed
        if not self._simulation_finished:
            self._simulation_finished = True
            print(f"[ALMACEN] Simulacion finalizada en t={self.env.now:.2f}")
        return True
    return False
```

**PROBLEMA:** Verifica `lista_maestra_work_orders` pero esta lista NUNCA se vacía.
Los WorkOrders completados se mueven a `work_orders_completados` pero NO se eliminan de `lista_maestra_work_orders`.

---

## 🔧 SOLUCIONES PROPUESTAS

### SOLUCIÓN 1: Comparar completados vs total (RECOMENDADA)

```python
def simulacion_ha_terminado(self) -> bool:
    # Check if all work orders are completed
    total_wos = len(self.dispatcher.lista_maestra_work_orders)
    completados = len(self.dispatcher.work_orders_completados)
    
    if completados >= total_wos and total_wos > 0:
        if not self._simulation_finished:
            self._simulation_finished = True
            print(f"[ALMACEN] Simulacion finalizada en t={self.env.now:.2f}")
            print(f"[ALMACEN] WorkOrders completadas: {completados}/{total_wos}")
        return True
    
    return False
```

### SOLUCIÓN 2: Verificar pendientes == 0

```python
def simulacion_ha_terminado(self) -> bool:
    # Check if no pending or in-progress work orders
    pendientes = len(self.dispatcher.work_orders_pendientes)
    activos = len(self.dispatcher.operadores_activos)
    
    if pendientes == 0 and activos == 0:
        if not self._simulation_finished:
            self._simulation_finished = True
            print(f"[ALMACEN] Simulacion finalizada en t={self.env.now:.2f}")
        return True
    
    return False
```

### SOLUCIÓN 3: Usar método del dispatcher

```python
def simulacion_ha_terminado(self) -> bool:
    # Delegate to dispatcher
    return self.dispatcher.simulacion_ha_terminado()
```

Y en `dispatcher.py` ya existe:

```python
def simulacion_ha_terminado(self) -> bool:
    return len(self.work_orders_completados) >= len(self.lista_maestra_work_orders)
```

---

## ✅ IMPLEMENTACIÓN RECOMENDADA

**Usar SOLUCIÓN 3** porque el dispatcher ya tiene la lógica correcta.

**Archivo:** `src/subsystems/simulation/warehouse.py`  
**Línea:** ~341-358

**CAMBIO:**

```python
# ANTES:
def simulacion_ha_terminado(self) -> bool:
    if not self.dispatcher.lista_maestra_work_orders:
        if not self._simulation_finished:
            self._simulation_finished = True
            print(f"[ALMACEN] Simulacion finalizada en t={self.env.now:.2f}")
        return True
    return False

# DESPUÉS:
def simulacion_ha_terminado(self) -> bool:
    # BUGFIX: Delegar al dispatcher que tiene la logica correcta
    terminado = self.dispatcher.simulacion_ha_terminado()
    
    if terminado and not self._simulation_finished:
        self._simulation_finished = True
        print(f"[ALMACEN] Simulacion finalizada en t={self.env.now:.2f}")
        print(f"[ALMACEN] WorkOrders completadas: {self.workorders_completadas_count}")
        print(f"[ALMACEN] Tareas completadas: {self.tareas_completadas_count}")
    
    return terminado
```

---

## 🚀 TESTING DESPUÉS DEL FIX

```bash
# 1. Aplicar el fix
# 2. Ejecutar test rápido:
python test_quick_jsonl.py

# DEBE terminar en < 30 segundos
# DEBE mostrar:
#   [ALMACEN] Simulacion finalizada en t=XXX.XX
#   [DISPATCHER-PROCESS] Simulacion finalizada en t=XXX.XX
#   [GroundOp-01] Simulacion finalizada, saliendo...
#   [GroundOp-02] Simulacion finalizada, saliendo...
```

---

## 📈 PRIORIDAD

**CRÍTICA** ⚠️

Este bug impide:
- ✅ Generación de archivos `.jsonl`
- ✅ Finalización de simulaciones
- ✅ Testing del sistema

**Debe arreglarse ANTES de continuar con testing.**

---

## 🔄 CAMBIOS ADICIONALES REALIZADOS

### 1. Reducir spam de logs (COMPLETADO)
**Archivo:** `src/subsystems/simulation/dispatcher.py:148-160`
- Solo loguea "No hay WorkOrders" cada 10 segundos

### 2. Verificar terminación antes de esperar (COMPLETADO)
**Archivo:** `src/subsystems/simulation/operators.py:194-202`
- Verifica si terminó ANTES de hacer timeout(1.0)

### 3. Properties de WorkOrder (COMPLETADO)
**Archivo:** `src/subsystems/simulation/warehouse.py:44-79`
- Agregadas properties: `sku_id`, `sku_name`, `work_group`, etc.

---

## 📝 ESTADO FINAL

| Tarea | Estado |
|-------|--------|
| Conexión replay_buffer | ✅ COMPLETADA |
| Bugfixes WorkOrder | ✅ COMPLETADAS |
| Reducir spam logs | ✅ COMPLETADA |
| **FIX terminación simulación** | ⏳ **PENDIENTE** |
| Testing generación JSONL | ⏳ BLOQUEADO |

---

**SIGUIENTE PASO CRÍTICO:** Aplicar fix de `simulacion_ha_terminado()` para que las simulaciones terminen correctamente.


