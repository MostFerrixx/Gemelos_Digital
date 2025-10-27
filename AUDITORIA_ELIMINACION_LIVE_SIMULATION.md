# AUDITORÍA PARA ELIMINACIÓN DE LIVE SIMULATION

**Fecha:** 2025-01-15
**Objetivo:** Eliminar todo el código relacionado con live simulation (`run_live_simulation.py`) de manera quirúrgica sin romper el modo replay.

---

## RESUMEN EJECUTIVO

### ¿QUÉ SE VA A ELIMINAR?
- **Entry Point:** `entry_points/run_live_simulation.py` (archivo completo)
- **Engine:** `src/engines/simulation_engine.py` (código específico de live simulation)
- **Código relacionado en subsystems:** Todo lo relacionado con generación de eventos en tiempo real

### ¿QUÉ SE VA A CONSERVAR?
- **Entry Point:** `entry_points/run_replay_viewer.py` (100% preservado)
- **Engine:** `src/engines/replay_engine.py` (100% preservado)
- **Subsystems:** Solo la parte que genera datos para replay (registrar_evento, replay_buffer)

---

## ARQUITECTURA ACTUAL

### FLUJO LIVE SIMULATION (A ELIMINAR)
```
entry_points/run_live_simulation.py
    ↓
SimulationEngine (simulation_engine.py)
    ↓
AlmacenMejorado → genera eventos → registro_evento()
    ↓
replay_buffer → archivo .jsonl
```

### FLUJO REPLAY (A CONSERVAR)
```
entry_points/run_replay_viewer.py
    ↓
ReplayViewerEngine (replay_engine.py)
    ↓
Lee archivo .jsonl → procesa eventos → renderiza
```

---

## ANÁLISIS DETALLADO POR ARCHIVO

### 1. ENTRY POINTS

#### 1.1 `entry_points/run_live_simulation.py` ❌ ELIMINAR COMPLETO
- **Estado:** ELIMINAR ARCHIVO COMPLETO
- **Razón:** Es el entry point de live simulation
- **Dependencias:** Ninguna para replay

#### 1.2 `entry_points/run_replay_viewer.py` ✅ CONSERVAR
- **Estado:** CONSERVAR 100%
- **Razón:** Es el único entry point necesario para replay
- **Dependencias:** Solo importa ReplayViewerEngine

---

### 2. ENGINES

#### 2.1 `src/engines/simulation_engine.py` ⚠️ ANÁLISIS CRÍTICO
**ESTE ARCHIVO ES EL MÁS COMPLEJO**

##### Código a ELIMINAR (marcado con ❌):
- **CLASE COMPLETA SimulationEngine** (líneas 101-1750) - ELIMINAR TODO
- **Función `_run_simulation_process_static`** (líneas 1411-1703) - ELIMINAR TODO
- **TODO el motor de simulación en tiempo real**

##### Código a CONSERVAR (marcado con ✅):
- **TODO LO RELACIONADO CON REPLAY_BUFFER** - Esto se usa para generar .jsonl

**PROBLEMA:** El archivo `simulation_engine.py` está mezclado entre:
- Generación de eventos (usado por replay para crear .jsonl)
- Renderizado en tiempo real (solo usado por live simulation)

**SOLUCIÓN:**
1. NO eliminar el archivo completamente
2. Crear un módulo nuevo `event_generator.py` que extraiga solo la generación de eventos
3. Eliminar todo el código de SimulationEngine que es específico de live simulation

**ARCHIVOS RELACIONADOS:**
- `simulation_buffer.py` - ✅ CONSERVAR (usado para generar .jsonl)
- `src/core/replay_utils.py` - ✅ CONSERVAR (utilidades para .jsonl)

#### 2.2 `src/engines/replay_engine.py` ✅ CONSERVAR
- **Estado:** CONSERVAR 100%
- **Razón:** Es el motor puro de replay
- **Dependencias:** Solo importa de visualization y communication

---

### 3. SUBSYSTEMS

#### 3.1 `src/subsystems/simulation/warehouse.py` ⚠️ ANÁLISIS CRÍTICO

**ESTE ARCHIVO CONTIENE LÓGICA MIXTA:**

##### Código a CONSERVAR ✅:
- **Líneas 1-559:** Clases SKU, WorkOrder, AlmacenMejorado (100% preservar)
- **Método `registrar_evento()`** (líneas 484-554) - ✅ PRESERVAR
  - Este método es CRÍTICO porque genera eventos para replay_buffer
  - Es usado tanto por live simulation como para generar .jsonl

##### Lógica de GENERACIÓN DE EVENTOS:
```python
def registrar_evento(self, tipo: str, datos: Dict[str, Any]):
    """
    Register an event for analytics AND replay buffer
    
    BUGFIX JSONL: Ahora también escribe eventos al replay_buffer
    para generación de archivos .jsonl
    """
    # ... código ...
    
    # BUGFIX JSONL: También agregar al replay_buffer para generación de .jsonl
    if self.replay_buffer is not None:
        # Convertir formato para replay
        self.replay_buffer.add_event(replay_evento)
```

**VEREDICTO:** Este método DEBE conservarse porque genera los .jsonl necesarios para replay.

##### Código relacionado con LIVE SIMULATION a ELIMINAR ❌:
- **Ningún código específico** - warehouse.py es 100% compatible con replay
- Todo lo que genera eventos va a replay_buffer
- No hay renderizado en tiempo real aquí

**CONCLUSIÓN:** `warehouse.py` se CONSERVA 100%

#### 3.2 `src/subsystems/simulation/dispatcher.py` ✅ CONSERVAR
- **Estado:** CONSERVAR 100%
- **Razón:** Solo gestiona asignación de WorkOrders
- No tiene lógica de visualización en tiempo real
- Los eventos que genera van a replay_buffer

#### 3.3 `src/subsystems/simulation/operators.py` ✅ CONSERVAR
- **Estado:** CONSERVAR 100%
- **Razón:** Solo gestiona comportamiento de operarios
- Los eventos que genera van a replay_buffer

---

### 4. VISUALIZATION

#### 4.1 `src/subsystems/visualization/state.py` ⚠️ ANALIZAR
- **Estado:** ANALIZAR línea por línea
- **Razón:** Puede tener código específico de live simulation

**ANÁLISIS:**
- Archivo usado tanto por live como por replay
- Contiene `estado_visual` dict compartido
- Debe conservarse porque replay lo necesita

#### 4.2 `src/subsystems/visualization/renderer.py` ⚠️ ANALIZAR
- **Estado:** ANALIZAR línea por línea
- **Razón:** Puede tener renderizado específico de live simulation

**ANÁLISIS:**
- Renderer tiene métodos para AMBOS modos
- Debe conservarse porque replay también renderiza

#### 4.3 `src/subsystems/visualization/dashboard*.py` ✅ CONSERVAR
- **Estado:** CONSERVAR
- **Razón:** Usado por replay

---

### 5. CORE UTILITIES

#### 5.1 `src/core/replay_utils.py` ✅ CONSERVAR
- **Estado:** CONSERVAR 100%
- **Razón:** Utilidades para .jsonl
- Líneas clave:
  - `agregar_evento_replay()` - ✅ conservar
  - `volcar_replay_a_archivo()` - ✅ conservar

#### 5.2 `simulation_buffer.py` ✅ CONSERVAR
- **Estado:** CONSERVAR 100%
- **Razón:** Buffer de eventos para generar .jsonl
- Clase `ReplayBuffer` - ✅ conservar

---

## MAPA DE DEPENDENCIAS

### LIVE SIMULATION (ELIMINAR)
```
run_live_simulation.py
    ↓
SimulationEngine
    ↓ (usa)
AlmacenMejorado.registrar_evento()
    ↓ (genera)
replay_buffer.add_event()
    ↓ (guarda)
archivo .jsonl
```

### REPLAY (CONSERVAR)
```
run_replay_viewer.py
    ↓ (usa)
ReplayViewerEngine
    ↓ (lee)
archivo .jsonl
    ↓ (procesa)
eventos
    ↓ (renderiza)
visualización
```

---

## PROPUESTA DE ELIMINACIÓN QUIRÚRGICA

### FASE 1: CREAR ÚNICO ENTRY POINT PARA GENERAR .JSONL
**NUEVA ARQUITECTURA:**
```
run_generate_replay.py (NUEVO ARCHIVO)
    ↓
EventGenerator (NUEVA CLASE)
    ↓
Usa AlmacenMejorado + DispatcherV11 + Operators
    ↓
Genera eventos → replay_buffer
    ↓
Guarda archivo .jsonl
```

**VENTAJAS:**
1. Separación clara entre generación de datos (.jsonl) y visualización (replay)
2. Permite ejecutar en modo headless para generar .jsonl
3. No rompe el modo replay existente

### FASE 2: ELIMINAR LIVE SIMULATION
**CÓDIGO A ELIMINAR:**
- `entry_points/run_live_simulation.py` (archivo completo)
- `src/engines/simulation_engine.py` (archivo completo)
- Toda lógica de renderizado en tiempo real

**CÓDIGO A CONSERVAR:**
- `src/subsystems/simulation/warehouse.py` (100%)
- `src/subsystems/simulation/dispatcher.py` (100%)
- `src/subsystems/simulation/operators.py` (100%)
- `simulation_buffer.py` (100%)
- `src/core/replay_utils.py` (100%)
- Todo lo relacionado con replay

---

## PLAN DE ACCIÓN

### PASO 1: CREAR NUEVO GENERADOR DE .JSONL
- [ ] Crear `entry_points/run_generate_replay.py`
- [ ] Crear `src/engines/event_generator.py`
- [ ] Extraer solo lógica de generación de eventos (sin renderizado)

### PASO 2: MIGRAR CÓDIGO NECESARIO
- [ ] Extraer `registrar_evento()` de warehouse.py (ya existe)
- [ ] Extraer ReplayBuffer logic (ya existe)
- [ ] Crear proceso SimPy puro (sin pygame)

### PASO 3: ELIMINAR LIVE SIMULATION
- [ ] Eliminar `entry_points/run_live_simulation.py`
- [ ] Eliminar `src/engines/simulation_engine.py`
- [ ] Eliminar código de renderizado en tiempo real

### PASO 4: VALIDAR
- [ ] Generar .jsonl nuevo con nuevo generador
- [ ] Abrir .jsonl con `run_replay_viewer.py`
- [ ] Verificar que todo funciona

---

## IMPACTO ESPERADO

### ANTES (HOY):
```
Opción 1: python run_live_simulation.py (live + genera .jsonl)
Opción 2: python run_replay_viewer.py archivo.jsonl (ve replay)
```

### DESPUÉS (PROPUESTA):
```
Opción 1: python run_generate_replay.py (genera .jsonl - headless)
Opción 2: python run_replay_viewer.py archivo.jsonl (ve replay)
```

**BENEFICIOS:**
1. ✅ Eliminado renderizado en tiempo real innecesario
2. ✅ Separación clara: generación vs visualización
3. ✅ Código más simple y mantenible
4. ✅ Generación de .jsonl más rápida (headless)

---

## ANÁLISIS COMPLETADO

### CONCLUSIONES FINALES

#### 1. GENERACIÓN DE .JSONL - FUNCIONA CON `simulation_engine.py`
La generación de archivos .jsonl DEPENDE de `SimulationEngine`:
- `SimulationEngine.registrar_evento()` → llena `replay_buffer`
- `replay_buffer` se vuelca con `volcar_replay_a_archivo()`
- Esto genera el archivo .jsonl necesario para replay

#### 2. PROBLEMA: NO PODEMOS ELIMINAR `simulation_engine.py` COMPLETAMENTE
**RAZÓN:** Si eliminamos `SimulationEngine`, perdemos la capacidad de generar .jsonl.

**SOLUCIÓN:**
Crear un nuevo módulo `src/engines/event_generator.py` que:
- Extraiga SOLO la lógica de generación de eventos de `SimulationEngine`
- Elimine TODO el código de renderizado en tiempo real
- Permita ejecutar simulaciones EN MODO HEADLESS para generar .jsonl
- NO tenga pygame, no tenga renderizado visual

#### 3. CÓDIGO A ELIMINAR (ESPECÍFICO DE LIVE SIMULATION)
De `simulation_engine.py`:
- ❌ TODA la clase `SimulationEngine` (1750 líneas)
- ❌ Función `_run_simulation_process_static()` (líneas 1411-1703)
- ❌ TODO código de Pygame y renderizado en tiempo real
- ❌ Modo "visual" (con UI)
- ❌ bucle principal de renderizado

**LO QUE SE CONSERVA:**
- ✅ Lógica de `AlmacenMejorado` (warehouse.py)
- ✅ Lógica de `DispatcherV11` (dispatcher.py)
- ✅ Lógica de `Operators` (operators.py)
- ✅ `registrar_evento()` que llena `replay_buffer`
- ✅ TODO el código de replay (replay_engine.py)

#### 4. PROPUESTA DE REFACTORIZACIÓN QUIRÚRGICA

**PASO 1: CREAR NUEVO GENERADOR DE EVENTOS**
```python
# src/engines/event_generator.py
class EventGenerator:
    """
    Generador puro de eventos para crear archivos .jsonl
    Sin renderizado, sin pygame, sin UI
    """
    def __init__(self, configuracion):
        self.env = simpy.Environment()
        self.almacen = AlmacenMejorado(...)
        self.replay_buffer = ReplayBuffer()
    
    def ejecutar(self):
        """Ejecuta simulación SimPy pura hasta completar"""
        # ... lógica de simulación ...
        # Guarda .jsonl al final
        volcar_replay_a_archivo(self.replay_buffer, ...)
```

**PASO 2: CREAR NUEVO ENTRY POINT**
```python
# entry_points/run_generate_replay.py
import EventGenerator

def main():
    event_gen = EventGenerator(config)
    event_gen.ejecutar()  # Genera .jsonl sin UI
```

**PASO 3: ELIMINAR LIVE SIMULATION**
- Eliminar `entry_points/run_live_simulation.py`
- Eliminar TODO `src/engines/simulation_engine.py`
- Dejar solo `EventGenerator` (código mínimo)

**PASO 4: CONSERVAR REPLAY**
- Mantener `entry_points/run_replay_viewer.py`
- Mantener `src/engines/replay_engine.py`
- NO tocar nada de replay

---

## PLAN DE ACCIÓN FINAL

### FASE 1: CREAR EVENT GENERATOR (NUEVO)
1. Crear `src/engines/event_generator.py`
2. Extraer lógica de simulación SimPy de `SimulationEngine`
3. Eliminar TODO el código de renderizado/Pygame
4. Mantener solo lógica de generación de .jsonl

### FASE 2: CREAR NUEVO ENTRY POINT
1. Crear `entry_points/run_generate_replay.py`
2. Importar `EventGenerator`
3. Ejecutar en modo headless
4. Generar .jsonl al finalizar

### FASE 3: ELIMINAR CÓDIGO ANTIGUO
1. Eliminar `entry_points/run_live_simulation.py` (archivo completo)
2. Eliminar `src/engines/simulation_engine.py` (archivo completo)
3. Actualizar documentación

### FASE 4: VALIDAR
1. Ejecutar `python entry_points/run_generate_replay.py`
2. Verificar que se genera .jsonl
3. Ejecutar `python entry_points/run_replay_viewer.py archivo.jsonl`
4. Verificar que replay funciona perfectamente

---

## ARCHIVOS A MODIFICAR/ELIMINAR

### ❌ ARCHIVOS A ELIMINAR COMPLETAMENTE:
1. `entry_points/run_live_simulation.py` (75 líneas)
2. `src/engines/simulation_engine.py` (1750 líneas)

### ➕ ARCHIVOS A CREAR:
1. `src/engines/event_generator.py` (NUEVO - ~300 líneas extraídas)
2. `entry_points/run_generate_replay.py` (NUEVO - ~50 líneas)

### ✅ ARCHIVOS A CONSERVAR (SIN CAMBIOS):
- `entry_points/run_replay_viewer.py` ✅
- `src/engines/replay_engine.py` ✅
- `src/subsystems/simulation/warehouse.py` ✅
- `src/subsystems/simulation/dispatcher.py` ✅
- `src/subsystems/simulation/operators.py` ✅
- `simulation_buffer.py` ✅
- `src/core/replay_utils.py` ✅

---

## RESUMEN EJECUTIVO FINAL

### ¿QUÉ SE ELIMINA?
- **~1825 líneas** de código de live simulation
- Renderizado en tiempo real
- Pygame en modo visual

### ¿QUÉ SE CONSERVA?
- **100% del código de replay**
- **100% de la lógica de simulación**
- **Generación de .jsonl**

### BENEFICIOS:
1. ✅ Código más simple (eliminar ~1825 líneas)
2. ✅ Separación clara: generación vs visualización
3. ✅ Generación de .jsonl más rápida (headless)
4. ✅ Replay sigue funcionando 100%

---

## PRÓXIMOS PASOS (EJECUTAR)

1. ✅ Auditoría completada
2. ✅ **Validación con dependencias COMPLETADA** - Ver `VALIDACION_AUDITORIA_CON_DEPENDENCIAS.md`
3. ⚠️ **PLAN ACTUALIZADO:** Refactorizar en lugar de eliminar completamente
4. ⏳ Refactorizar `simulation_engine.py` a `event_generator.py` (eliminar Pygame, mantener lógica SimPy)
5. ⏳ Crear `run_generate_replay.py` (nuevo entry point)
6. ⏳ Eliminar archivos innecesarios (`run_live_simulation.py`, `simulation_data_provider.py`)
7. ⏳ Actualizar referencias en `SimulationContext` para compatibilidad
8. ⏳ Validar que replay funciona
9. ⏳ Actualizar documentación

---

## ⚠️ CAMBIOS IMPORTANTES AL PLAN ORIGINAL

**PROBLEMA ENCONTRADO:** El plan original asumía que podíamos eliminar `simulation_engine.py` completamente.

**REALIDAD:** Hay dependencias críticas:
- `SimulationContext.from_simulation_engine()` requiere instancia de SimulationEngine
- `SimulationEngineDataProvider` está diseñado para SimulationEngine

**SOLUCIÓN ACTUALIZADA:**
- REFACTORIZAR `SimulationEngine` a `EventGenerator` (renombrar + eliminar Pygame)
- MANTENER compatibilidad con código existente
- ELIMINAR archivos específicos de live simulation (`simulation_data_provider.py`)

**Ver documento completo:** `VALIDACION_AUDITORIA_CON_DEPENDENCIAS.md`
