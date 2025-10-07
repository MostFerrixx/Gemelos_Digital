# BUGFIX PLAN - entry_points/run_live_simulation.py

**Fecha:** 2025-10-06
**Objetivo:** Corregir entry_points/run_live_simulation.py para que funcione con arquitectura V11
**Status:** PLAN VALIDADO - Pendiente de implementacion

---

## 1. VALIDACION DE ESTRATEGIA

### ✅ Estrategia Aprobada

**Objetivo:** Terminar de corregir `entry_points/run_live_simulation.py` para que funcione con la nueva arquitectura V11 y pueda ejecutar simulaciones headless.

**Justificacion:**
1. Los archivos .jsonl existentes son de septiembre 2025 (pre-migracion V11)
2. El codigo actual esta en migracion V11 con estructura `src/subsystems/`
3. Los imports estan parcialmente actualizados pero con problemas de resolucion de rutas
4. SimulationEngine esta correctamente refactorizado y todos sus imports funcionan
5. El problema NO son los imports en si, sino la configuracion de rutas de archivos TMX

---

## 2. ANALISIS DEL PROBLEMA ACTUAL

### Problema Identificado #1: Import Path Correcto ✅

**Estado:** RESUELTO
**Archivo:** `entry_points/run_live_simulation.py` linea 16

```python
# ACTUAL (CORRECTO):
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
```

**Validacion:**
- ✅ El path se resuelve correctamente a: `C:\Users\ferri\OneDrive\Escritorio\Gemelos Digital\src`
- ✅ Todos los imports funcionan: `from engines.simulation_engine import SimulationEngine`
- ✅ SimulationEngine se importa sin errores

**Conclusion:** Los imports estan CORRECTOS, no requieren modificacion.

---

### Problema Identificado #2: Configuracion de Archivos TMX ❌

**Estado:** PROBLEMA PRINCIPAL
**Archivo:** Configuracion de rutas de archivos

**Error Observado:**
```
[TMX] Cargando layout: C:\Users\ferri\OneDrive\Escritorio\Gemelos Digital\entry_points\..\src\engines\layouts\WH1.tmx
[FATAL ERROR] No se pudo cargar archivo TMX: [LAYOUT-MANAGER ERROR] Archivo TMX no encontrado
```

**Causa Raiz:**
1. ConfigurationManager usa configuracion por defecto con ruta: `layouts/WH1.tmx`
2. LayoutManager resuelve rutas relativas desde `src/engines/` (su ubicacion)
3. Ruta resultante: `src/engines/layouts/WH1.tmx` (NO EXISTE)
4. Ruta real del archivo: `data/layouts/WH1.tmx` o `layouts/WH1.tmx` (raiz)

**Archivos Afectados:**
- `config.json` - Contiene rutas incorrectas
- `core/config_manager.py` - Busca config.json en ubicacion incorrecta
- `subsystems/simulation/layout_manager.py` - Resuelve rutas desde ubicacion incorrecta

---

### Problema Identificado #3: ConfigurationManager Path ❌

**Estado:** PROBLEMA SECUNDARIO
**Archivo:** `core/config_manager.py`

**Comportamiento Actual:**
```
[CONFIG] config.json no encontrado, usando configuracion por defecto
```

**Causa:**
- ConfigurationManager busca `config.json` en directorio de ejecucion
- Cuando ejecutamos desde `entry_points/`, busca en `entry_points/config.json`
- El archivo real esta en raiz: `./config.json`

---

## 3. PLAN DE BUGFIX DETALLADO

### BUGFIX #1: Corregir Resolucion de Rutas en LayoutManager

**Archivo:** `src/subsystems/simulation/layout_manager.py`
**Prioridad:** CRITICA
**Tiempo Estimado:** 10 minutos

**Problema:**
LayoutManager resuelve rutas relativas desde su propia ubicacion (`src/engines/`), no desde la raiz del proyecto.

**Solucion:**
Modificar LayoutManager para resolver rutas desde la raiz del proyecto.

**Cambios Necesarios:**

```python
# ANTES (linea ~20-30):
def __init__(self, tmx_file: str, ...):
    # Resuelve desde ubicacion actual del modulo
    self.tmx_path = os.path.abspath(tmx_file)

# DESPUES:
def __init__(self, tmx_file: str, ...):
    # Si es ruta relativa, resolver desde raiz del proyecto
    if not os.path.isabs(tmx_file):
        # Obtener raiz del proyecto (2 niveles arriba desde src/subsystems/simulation/)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        self.tmx_path = os.path.join(project_root, tmx_file)
    else:
        self.tmx_path = tmx_file

    self.tmx_path = os.path.abspath(self.tmx_path)
```

**Validacion:**
- Ruta relativa `data/layouts/WH1.tmx` se resolvera desde raiz del proyecto
- Rutas absolutas seguiran funcionando
- Compatible con todas las configuraciones existentes

---

### BUGFIX #2: Corregir ConfigurationManager para Encontrar config.json

**Archivo:** `src/core/config_manager.py`
**Prioridad:** ALTA
**Tiempo Estimado:** 5 minutos

**Problema:**
ConfigurationManager busca config.json en directorio de ejecucion, no en raiz del proyecto.

**Solucion:**
Buscar config.json primero en raiz del proyecto, luego en directorio actual.

**Cambios Necesarios:**

```python
# ANTES (linea ~30-40):
def __init__(self, config_path: str = "config.json"):
    self.config_path = config_path
    # Busca en directorio actual

# DESPUES:
def __init__(self, config_path: str = "config.json"):
    # Intentar primero en raiz del proyecto
    if not os.path.isabs(config_path):
        # Obtener raiz del proyecto (2 niveles arriba desde src/core/)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        project_config_path = os.path.join(project_root, config_path)

        if os.path.exists(project_config_path):
            self.config_path = project_config_path
        else:
            # Fallback: directorio actual
            self.config_path = config_path
    else:
        self.config_path = config_path
```

**Validacion:**
- `config.json` en raiz del proyecto se encontrara automaticamente
- Rutas absolutas seguiran funcionando
- Fallback a directorio actual si no se encuentra en raiz

---

### BUGFIX #3: Actualizar config.json con Rutas Correctas

**Archivo:** `config.json` (raiz del proyecto)
**Prioridad:** ALTA
**Tiempo Estimado:** 2 minutos

**Problema:**
config.json tiene rutas que apuntan a `layouts/WH1.tmx` cuando deberian ser `data/layouts/WH1.tmx`

**Solucion:**
Actualizar rutas en config.json a las ubicaciones reales de los archivos.

**Cambios Necesarios:**

```json
// ANTES:
{
    "layout_file": "layouts/WH1.tmx",
    "sequence_file": "layouts/Warehouse_Logic.xlsx",
    ...
}

// DESPUES:
{
    "layout_file": "data/layouts/WH1.tmx",
    "sequence_file": "data/layouts/Warehouse_Logic.xlsx",
    ...
}
```

**Validacion:**
- Archivos existen en: `data/layouts/WH1.tmx` ✅
- Archivos existen en: `data/layouts/Warehouse_Logic.xlsx` ✅

---

### BUGFIX #4: Verificar Imports en analytics/*.py (OPCIONAL)

**Archivos:**
- `src/analytics/exporter.py` ✅ CORREGIDO
- `src/analytics/exporter_v2.py` ✅ CORREGIDO

**Estado:** COMPLETADO (ya corregido en sesion anterior)

**Cambios Realizados:**
```python
# ANTES:
from analytics_engine import AnalyticsEngine

# DESPUES:
from engines.analytics_engine import AnalyticsEngine
```

---

## 4. ORDEN DE IMPLEMENTACION

### Paso 1: BUGFIX #3 - Actualizar config.json
**Tiempo:** 2 minutos
**Archivo:** `config.json`
**Accion:** Cambiar rutas de `layouts/` a `data/layouts/`

### Paso 2: BUGFIX #2 - Corregir ConfigurationManager
**Tiempo:** 5 minutos
**Archivo:** `src/core/config_manager.py`
**Accion:** Buscar config.json en raiz del proyecto

### Paso 3: BUGFIX #1 - Corregir LayoutManager
**Tiempo:** 10 minutos
**Archivo:** `src/subsystems/simulation/layout_manager.py`
**Accion:** Resolver rutas TMX desde raiz del proyecto

### Paso 4: Validacion y Testing
**Tiempo:** 5 minutos
**Comando:** `python entry_points/run_live_simulation.py --headless`
**Resultado Esperado:** Simulacion ejecutandose sin errores de archivos TMX

---

## 5. VALIDACIONES POST-BUGFIX

### Test 1: Import de SimulationEngine ✅
```bash
python -c "
import sys, os
sys.path.insert(0, 'src')
from engines.simulation_engine import SimulationEngine
print('OK')
"
```
**Resultado Esperado:** `OK`

### Test 2: Ejecucion Headless ✅
```bash
python entry_points/run_live_simulation.py --headless
```
**Resultado Esperado:**
- ConfigurationManager encuentra config.json
- LayoutManager carga WH1.tmx correctamente
- Simulacion ejecuta sin FATAL ERROR
- Genera archivo .jsonl en output/

### Test 3: Verificar Archivo .jsonl Generado ✅
```bash
ls -lh output/simulation_*/replay_events_*.jsonl | tail -1
```
**Resultado Esperado:** Archivo .jsonl recien creado con tamaño > 0 bytes

---

## 6. RIESGOS Y MITIGACIONES

### Riesgo 1: Cambio de Rutas Rompe Otros Scripts
**Probabilidad:** BAJA
**Impacto:** MEDIO
**Mitigacion:**
- Los cambios son compatibles hacia atras (rutas absolutas siguen funcionando)
- Rutas relativas ahora se resuelven desde raiz del proyecto (mas consistente)

### Riesgo 2: ConfigurationManager No Encuentra config.json
**Probabilidad:** BAJA
**Impacto:** BAJO
**Mitigacion:**
- Fallback a configuracion por defecto (comportamiento actual)
- Fallback a buscar en directorio actual

### Riesgo 3: LayoutManager Rompe Replay Viewer
**Probabilidad:** BAJA
**Impacto:** MEDIO
**Mitigacion:**
- Replay viewer usa rutas absolutas (no afectado)
- Cambio solo afecta rutas relativas

---

## 7. ARCHIVOS A MODIFICAR (RESUMEN)

### Modificaciones Requeridas:
1. ✅ `config.json` (raiz) - Actualizar rutas TMX
2. ✅ `src/core/config_manager.py` - Buscar config en raiz del proyecto
3. ✅ `src/subsystems/simulation/layout_manager.py` - Resolver rutas desde raiz

### Archivos Ya Corregidos:
1. ✅ `entry_points/run_live_simulation.py` - Imports correctos
2. ✅ `src/engines/simulation_engine.py` - Import analytics_engine corregido
3. ✅ `src/analytics/exporter.py` - Import analytics_engine corregido
4. ✅ `src/analytics/exporter_v2.py` - Import analytics_engine corregido

---

## 8. COMANDO FINAL ESPERADO

Una vez aplicados todos los BUGFIX:

```bash
cd "C:\Users\ferri\OneDrive\Escritorio\Gemelos Digital"
python entry_points/run_live_simulation.py --headless
```

**Salida Esperada:**
```
============================================================
SIMULADOR DE ALMACEN - GEMELO DIGITAL
Simulacion Live v2.6 - Sin Capacidades de Replay
Modo HEADLESS - Maxima Velocidad
============================================================

[CONFIG] Configuracion cargada desde: C:\...\config.json
[LAYOUT-MANAGER] Cargando archivo TMX: C:\...\data\layouts\WH1.tmx
[TMX] Archivo TMX cargado exitosamente
[SIMULATION] Iniciando simulacion...
[SIMULATION] Simulacion completada
[EXPORT] Archivo replay guardado en: output/simulation_*/replay_events_*.jsonl
```

---

## 9. ESTIMACION DE TIEMPO TOTAL

| Tarea | Tiempo Estimado |
|-------|-----------------|
| BUGFIX #3 (config.json) | 2 minutos |
| BUGFIX #2 (config_manager.py) | 5 minutos |
| BUGFIX #1 (layout_manager.py) | 10 minutos |
| Testing y validacion | 5 minutos |
| **TOTAL** | **22 minutos** |

---

## 10. CRITERIOS DE EXITO

✅ **BUGFIX EXITOSO SI:**
1. `python entry_points/run_live_simulation.py --headless` ejecuta sin errores
2. ConfigurationManager encuentra y carga config.json
3. LayoutManager carga WH1.tmx correctamente
4. Simulacion completa y genera archivo .jsonl
5. No hay FATAL ERROR de archivos no encontrados
6. Dashboard refactorizado funciona correctamente (validado en sesion anterior)

---

**Plan Creado:** 2025-10-06
**Estado:** VALIDADO - Listo para implementacion
**Proximos Pasos:** Aprobar e implementar BUGFIX en orden especificado

🚀 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
