## Asunto: Continuación del Desarrollo del Simulador de Gemelo Digital de Almacén

Hola Claude Code. Estoy desarrollando un **Simulador de Gemelo Digital de Almacén** usando **SimPy** (simulación de eventos discretos) y **Pygame** (visualización en tiempo real).

### CONTEXTO CRÍTICO

Actualmente estamos en medio de una **Re-arquitectura V11** del proyecto para transformarlo de una estructura caótica a una profesional. El proyecto está **88% completado** (FASE 2 - Implementación de Visualización en progreso - state.py y renderer.py COMPLETOS).

**Rama Actual de Trabajo:** `reconstruction/v11-complete`
**Estado:** Migrando a estructura de paquete Python profesional con layout `src/`

### TU MISIÓN

Ayudarme a continuar el desarrollo del simulador siguiendo las mejores prácticas de Python, manteniendo la arquitectura V11, y asegurando que todo funcione correctamente.

---

## INSTRUCCIONES CRÍTICAS DE INICIO

### 1. LECTURA OBLIGATORIA DE DOCUMENTACIÓN (EN ESTE ORDEN)

Antes de hacer CUALQUIER cosa, DEBES leer estos archivos en orden:

#### **A. Documentación de Estado y Plan (CRÍTICO - LEER PRIMERO)**

1. **`HANDOFF.md`** (raíz del proyecto)
   - Guía rápida de handoff
   - Estado actual en 1 página
   - Qué se ha hecho y qué falta
   - **LEER PRIMERO - 2 minutos**

2. **`docs/V11_MIGRATION_STATUS.md`**
   - Estado COMPLETO de la migración V11
   - Progreso de FASE 1, 2 y 3 (82% done)
   - FASE 2: Implementación de visualización (1/4 módulos completos)
   - Problemas conocidos y soluciones
   - Comandos útiles y referencias
   - **LEER COMPLETO - 10 minutos**

3. **`PHASE3_CHECKLIST.md`**
   - Checklist detallada de 16 módulos subsystems
   - Estado: 16/16 creados, 11/16 production-ready
   - state.py COMPLETADO (558 lines)
   - Prioridades, templates, referencias
   - **GUÍA PRÁCTICA - usar durante ejecución**

#### **B. Documentación Técnica del Proyecto**

4. **`docs/DYNAMIC_LAYOUTS_USER_GUIDE.md`**
   - Guía de layouts dinámicos y TMX maps

5. **`docs/TILES_REFERENCE.md`**
   - Referencia de tiles y tilesets

6. **`INSTRUCCIONES.md`** (raíz)
   - Instrucciones generales del proyecto (archivo largo y detallado)

#### **C. ADVERTENCIA sobre README.md**

⚠️ **NO leas `README.md` como fuente de verdad** - Está desactualizado:
- Menciona `git/` como directorio válido (ESTÁ VACÍO)
- Referencias a estructura antigua (pre-V11)
- Controles y comandos que pueden haber cambiado

**En su lugar:** Usa `HANDOFF.md` y `docs/V11_MIGRATION_STATUS.md` para entender el estado actual.

---

### 2. LECTURA EXHAUSTIVA DEL CÓDIGO

Después de leer la documentación, DEBES:

#### **A. Entender la Arquitectura Actual (V11 en progreso)**

```bash
# Verificar rama
git checkout reconstruction/v11-complete
git log --oneline -10

# Ver estructura nueva (V11)
find src/ tools/ entry_points/ tests/ -type d

# Ver qué está migrado
find src/ -name "*.py" ! -name "__init__.py"
```

**Estructura V11 (nueva - 82% completa):**
```
digital-twin-warehouse/
├── src/                      # Código de producción
│   ├── engines/              # ✅ Motores (simulation, replay, analytics)
│   ├── subsystems/           # ⏳ 11/16 módulos production-ready
│   │   ├── config/           # ✅ COMPLETO: settings.py, colors.py
│   │   ├── simulation/       # ✅ COMPLETO: 8/8 módulos (warehouse, operators, etc.)
│   │   ├── visualization/    # ⏳ 1/4: state.py ✅, renderer.py ⏳, dashboard.py ⏳
│   │   └── utils/            # ⏳ SKELETON: helpers.py
│   ├── analytics/            # ✅ Migrado
│   ├── communication/        # ✅ Migrado
│   ├── core/                 # ✅ Migrado
│   └── shared/               # ✅ Migrado
├── tools/                    # ✅ Herramientas (configurator, inspector)
├── entry_points/             # ✅ Scripts de entrada
├── tests/                    # ✅ Tests organizados
├── debug/                    # ✅ Scripts de debug
└── data/                     # ✅ Layouts, configs, assets
```

**Estructura Legacy (antigua - PRESERVADA en raíz):**
```
Gemelos Digital/  (raíz)
├── run_simulator.py          # ⚠️ Legacy V10 - preservado como referencia
├── simulation_engine.py      # ⚠️ Legacy - copiado a src/engines/
├── replay_engine.py          # ⚠️ Legacy - copiado a src/engines/
├── configurator.py           # ⚠️ Legacy - copiado a tools/
├── git/                      # 🔴 VACÍO - Submódulo roto (razón de V11)
└── test_*.py (16 archivos)   # ⚠️ Legacy - copiados a tests/
```

#### **B. Leer Motores Principales (YA MIGRADOS)**

1. **`src/engines/simulation_engine.py`** (1730 líneas)
   - Motor principal de simulación SimPy
   - Arquitectura productor-consumidor (multiprocessing)
   - Integración con TMX maps (pytmx)
   - Sistema de replay (.jsonl)

2. **`src/engines/replay_engine.py`** (835 líneas)
   - Motor de replay de eventos
   - Reproducción de simulaciones grabadas

3. **`src/engines/analytics_engine.py`** (560 líneas)
   - Procesamiento de métricas
   - Exportación a Excel

**IMPORTANTE:** Estos archivos tienen imports ROTOS porque importan de `subsystems/` que aún NO existe (FASE 3 pendiente).

#### **C. Leer Herramientas**

1. **`tools/configurator.py`** (473 líneas)
   - GUI PyQt6 de configuración
   - **FUNCIONAL y AUTOCONTENIDO** (único que funciona actualmente)
   - Genera `config.json`

2. **`tools/inspector_tmx.py`** (181 líneas)
   - Inspector de archivos TMX

#### **D. Entender Configuración**

1. **`data/config/config.json`**
   - Configuración activa del simulador
   - Define: estrategias, fleet groups, work areas, etc.

2. **`setup.py`** (raíz)
   - Configuración de paquete Python
   - Entry points definidos
   - Dependencias listadas

---

### 3. ENTENDER LAS INTERACCIONES Y FLUJO DEL SISTEMA

#### **A. Flujo de Simulación (cuando esté completo V11)**

```python
# Entry point
entry_points/run_live_simulation.py
    ↓
# Motor de simulación
src/engines/simulation_engine.py
    ↓
# Subsistemas core (PENDIENTE FASE 3)
src/subsystems/simulation/warehouse.py (AlmacenMejorado)
src/subsystems/simulation/operators.py (crear_operarios, GroundOperator, Forklift)
src/subsystems/simulation/layout_manager.py (LayoutManager - TMX)
src/subsystems/simulation/pathfinder.py (A* pathfinding)
    ↓
# Visualización (PENDIENTE FASE 3)
src/subsystems/visualization/state.py (estado_visual global)
src/subsystems/visualization/renderer.py (RendererOriginal)
    ↓
# Analytics
src/analytics/exporter_v2.py (AnalyticsExporter)
```

#### **B. Conceptos Clave del Sistema**

**SimPy (Discrete Event Simulation):**
- `env = simpy.Environment()` - Entorno de simulación
- `env.process()` - Crear procesos de agentes
- `yield env.timeout()` - Esperar tiempo simulado
- `env.run()` - Ejecutar simulación

**Pygame (Visualización):**
- Renderizado en tiempo real
- Multiprocessing: simulación en un proceso, visualización en otro
- Queue para comunicación entre procesos

**TMX Maps (Tiled):**
- Mapas de almacén en formato TMX
- Lectura con pytmx
- Conversión grid ↔ pixel
- Matriz de colisiones

**Work Areas:**
- Zonas identificadas por STRINGS (ej: "Area_Ground", "Area_Rack")
- NO son enteros
- Configurables en Excel (Warehouse_Logic.xlsx)

**Agent Types:**
- `GroundOperator`: Operadores de piso (carga ligera)
- `Forklift`: Montacargas (carga pesada)
- Cada tipo tiene prioridades por Work Area

**Config System:**
- `data/config/config.json` - Config activa
- `core/config_manager.py` - ConfigurationManager
- Estrategias: "Optimizacion Global", "FIFO Estricto", "Cercania"

#### **C. Sistema de Imports (OBJETIVO V11)**

**Imports ROTOS (actuales - porque subsystems/ está vacío):**
```python
from config.settings import *  # ❌ NO EXISTE
from simulation.warehouse import AlmacenMejorado  # ❌ NO EXISTE
```

**Imports OBJETIVO (cuando FASE 3 esté lista):**
```python
from subsystems.config.settings import LOGICAL_WIDTH, LOGICAL_HEIGHT
from subsystems.simulation.warehouse import AlmacenMejorado
from subsystems.simulation.operators import crear_operarios
from subsystems.visualization.state import estado_visual
```

---

### 4. PROBLEMAS CONOCIDOS Y CRÍTICOS

#### **Problema 1: Submódulo `git/` Vacío** 🔴 CRÍTICO

**Contexto:**
- El directorio `git/` era un submódulo Git pero está **VACÍO**
- Faltaban módulos críticos: `config/`, `simulation/`, `visualization/`, `utils/`
- Esto causaba `ModuleNotFoundError` en todo el proyecto

**Solución V11:**
- Renombrar `git/` → `subsystems/`
- Recrear los 16 módulos faltantes desde cero (FASE 3)
- Migrar todos los imports

#### **Problema 2: Tests en .gitignore** ✅ RESUELTO

**Contexto:**
- `.gitignore` tenía patrones que bloqueaban `test_*.py`
- Los tests no se podían commitear normalmente

**Solución:**
- Usar `git add -f tests/**/*.py` para forzar adición
- Tests ahora organizados en `tests/{unit,integration,bugfixes,manual}/`

#### **Problema 3: Múltiples Versiones de run_simulator.py** ⚠️ IMPORTANTE

**Contexto:**
- `run_simulator.py` en raíz puede estar corrupto/incompleto
- V9.0.0 tenía versión correcta (2528 líneas, imports simples)
- V10+ tiene imports complejos de `git/` vacío

**Solución:**
- Usar V9.0.0 como baseline cuando se necesite referencia
- `run_simulator.py` actual será archivado en FASE 6

---

### 5. REGLAS DE TRABAJO OBLIGATORIAS

#### **A. Verificación Inicial SIEMPRE**

```bash
# 1. Verificar rama
git branch  # Debe estar en: reconstruction/v11-complete

# 2. Verificar estado
git status  # Debe estar limpio

# 3. Revisar últimos commits
git log --oneline -10
```

#### **B. Antes de Hacer Cambios**

1. **NUNCA asumir** que entiendes el código sin leerlo primero
2. **SIEMPRE verificar** dependencias entre archivos
3. **USAR las herramientas** de testing para validar
4. **REVISAR logs** después de ejecutar simulaciones
5. **PREGUNTAR si no estás seguro** antes de hacer cambios
6. **MANTENER compatibilidad** con `config.json` existente
7. **DOCUMENTAR cambios** importantes

#### **C. Testing y Validación**

```bash
# Configurador (único funcional actualmente)
python tools/configurator.py

# Validar config.json
python tests/unit/test_config_compatibility.py

# Cuando FASE 3 esté lista:
python -m entry_points.run_live_simulation --headless
```

#### **D. Commits Progresivos**

- **NO hacer** commits gigantes
- **SÍ hacer** commits pequeños y descriptivos
- **Formato:** `tipo(scope): descripción`
  - Ejemplos: `feat(v11):`, `fix(simulation):`, `docs(v11):`
- **Siempre** incluir: "Generated with Claude Code" y "Co-Authored-By: Claude"

---

### 6. FLUJO DE TRABAJO RECOMENDADO

#### **Para CUALQUIER Tarea:**

1. **Leer** archivos relevantes completamente
2. **Entender** relaciones entre componentes
3. **Planificar** cambios (usar TodoWrite si es complejo)
4. **Implementar** cambios
5. **Probar** con tests o ejecución
6. **Verificar** que no rompiste nada
7. **Commitear** con mensaje descriptivo
8. **Documentar** si es cambio significativo

#### **Si Continuamos con FASE 3:**

1. Leer `PHASE3_CHECKLIST.md`
2. Empezar con `subsystems/config/settings.py`
3. Seguir orden de prioridad (🔴 CRITICAL primero)
4. Validar cada módulo antes de continuar
5. Commitear por grupos lógicos

---

### 7. CONTEXTO DE SESIÓN ANTERIOR

**Usuario (Ferri):**
- Desarrollador principal del proyecto
- Ha trabajado en el proyecto por varios meses
- Actualmente ejecutando Plan Maestro V11

**Yo (Claude Code anterior):**
- Ayudé a crear el Plan Maestro V11
- Ejecuté FASE 1 (estructura base) ✅
- Ejecuté FASE 2 (migración de 61 archivos) ✅
- Ejecuté FASE 3 (16 módulos subsystems creados) ✅
- Implementé FASE 2-Impl (state.py completo) ✅
- Creé documentación completa de handoff
- Dejé el proyecto en FASE 2 - Implementación de Visualización

**Progreso Actual:**
- **88% completado** (FASE 2-Impl en progreso)
- **23+ commits** en rama reconstruction/v11-complete
- **61 archivos** migrados exitosamente
- **16/16 módulos subsystems** creados (12/16 production-ready)
- **state.py (558 lines)** implementado completamente ✨
- **renderer.py (723 lines)** implementado completamente ✨
- **Siguiente:** dashboard.py (30min-1h), helpers.py (30min)

---

### 8. HERRAMIENTAS Y COMANDOS ÚTILES

#### **Git**
```bash
# Ver estructura
find src/ -type d | sort

# Contar archivos migrados
find src/ tools/ entry_points/ tests/ -name "*.py" ! -name "__init__.py" | wc -l

# Ver cambios desde estructura base
git diff --stat f338a8a..HEAD
```

#### **Análisis de Código**
```bash
# Buscar imports rotos
grep -r "from config\." src/ --include="*.py"
grep -r "from simulation\." src/ --include="*.py"

# Buscar clases
grep -rn "^class " src/ --include="*.py"

# Buscar constantes
grep -rn "^[A-Z_]* =" src/ --include="*.py"
```

#### **Testing**
```bash
# Validar sintaxis
python -m py_compile src/engines/simulation_engine.py

# Probar imports (fallará hasta FASE 3)
python -c "from subsystems.config.settings import LOGICAL_WIDTH"
```

---

### 9. ARCHIVOS IMPORTANTES DE REFERENCIA

**Para Crear Módulos (FASE 3):**
- `src/engines/simulation_engine.py` - Ver cómo se usan las clases
- `run_simulator.py` (raíz) - Versión legacy con todo inline
- `data/config/config.json` - Estructura de configuración

**Para Entender Sistema:**
- `data/layouts/WH1.tmx` - Ejemplo de mapa TMX
- `data/layouts/Warehouse_Logic.xlsx` - Datos de work areas
- `tools/configurator.py` - Cómo se genera config.json

**Para Debugging:**
- `debug/debug_dashboard_state.py` - Debug de estado
- `debug/debug_O_key_press.py` - Debug de teclas
- `debug/debug_workorder_loading.py` - Debug de work orders

---

### 10. EXPECTATIVAS Y ESTILO DE TRABAJO

**Yo espero que tú (nuevo Claude Code):**

1. **Seas proactivo** pero no sorpresivo
   - Haz cosas cuando te lo pida
   - Sugiere mejoras pero no las implementes sin permiso

2. **Leas primero, actúes después**
   - El código fuente es tu fuente de verdad
   - No asumas, verifica

3. **Uses las herramientas disponibles**
   - Tests, validadores, debuggers
   - Comandos documentados

4. **Mantengas el estilo profesional**
   - Commits descriptivos
   - Código limpio (solo ASCII)
   - Documentación actualizada

5. **Comuniques claramente**
   - Explica qué vas a hacer
   - Muestra qué hiciste
   - Reporta problemas encontrados

**Estilo de Código:**
- **Encoding:** UTF-8, pero solo caracteres ASCII en código
- **Docstrings:** Español o Inglés según contexto
- **Nombres:** Descriptivos (español para dominio, inglés para técnico)
- **Imports:** Absolutos desde `src/`

---

### 11. PRÓXIMOS PASOS SUGERIDOS

**Inmediato (si continuamos V11):**
1. Leer `HANDOFF.md` y `docs/V11_MIGRATION_STATUS.md`
2. Verificar rama: `git checkout reconstruction/v11-complete`
3. Revisar commits: `git log --oneline -10`
4. Leer `PHASE3_CHECKLIST.md`
5. Continuar FASE 2: Implementar `dashboard.py` (30min-1h) o `helpers.py` (30min)

**Alternativo (si hacemos otra cosa):**
1. Leer documentación de estado
2. Preguntar a Ferri qué necesita
3. Leer código relevante para la tarea
4. Planificar y ejecutar

---

### 12. INFORMACIÓN DE CONTACTO Y SOPORTE

**Si te atascas:**
- Revisa `docs/V11_MIGRATION_STATUS.md` sección "Critical Issues"
- Lee `PHASE3_CHECKLIST.md` para referencias específicas
- Analiza commits anteriores: `git show <commit_hash>`
- Pregunta a Ferri directamente

**Commits clave de referencia:**
- `f338a8a` - Estructura base V11
- `fc95861` - Migración de módulos core
- `92435e1` - Arquitectura unificada y skeletons de visualización
- `d02ba77` - Actualización de documentación (Phase 1 complete)
- Estado actual: state.py (558 lines) + renderer.py (723 lines) implementados completamente

**Tags importantes:**
- `BEFORE_V11_RECONSTRUCTION` - Punto de seguridad (volver si hay problemas)
- `v11.0.0-phase1` - Phase 1 complete (arquitectura unificada)
- `V10.0.5` - Última versión estable antes de V11

---

## RESUMEN EJECUTIVO

**Estado:** Proyecto en migración V11 (88% done)
**Rama:** `reconstruction/v11-complete`
**Siguiente:** FASE 2-Impl - Implementar dashboard.py y helpers.py (1-2h restantes)

**Documentación CRÍTICA (LEER EN ORDEN):**
1. `HANDOFF.md` ← Inicio rápido
2. `docs/V11_MIGRATION_STATUS.md` ← Estado completo
3. `PHASE3_CHECKLIST.md` ← Guía práctica

**Código CRÍTICO (LEER PARA ENTENDER):**
1. `src/engines/simulation_engine.py` ← Motor principal
2. `tools/configurator.py` ← Único funcional
3. `data/config/config.json` ← Configuración activa

**Advertencia:** `README.md` está desactualizado, usa HANDOFF.md en su lugar.

---

**¿Entendiste todo? Confirma que has leído la documentación y estás listo para ayudarme a continuar el desarrollo del simulador.**
