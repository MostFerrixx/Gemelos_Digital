# RESUMEN VISUAL DE ARCHIVOS DUPLICADOS

## MAPA DE DUPLICADOS ENCONTRADOS

```
PROYECTO RAIZ/
│
├── 📁 ENTRY POINTS (Comandos principales)
│   ├── ❌ run_live_simulation.py (OBSOLETO - ELIMINAR)
│   ├── ❌ run_replay_viewer.py (OBSOLETO - ELIMINAR)
│   └── ✅ configurator.py (CORRECTO - MANTENER)
│
├── 📁 MODULOS CORE
│   ├── ❌ analytics_engine.py (OBSOLETO - ELIMINAR)
│   ├── ❌ analytics/ (OBSOLETO - ELIMINAR)
│   │   ├── exporter.py
│   │   └── exporter_v2.py
│   ├── ❌ core/ (OBSOLETO - ELIMINAR)
│   │   ├── config_manager.py
│   │   └── config_utils.py
│   └── ⚠️ simulation_buffer.py (REVISAR - Puede ser correcto)
│
├── 📁 TESTS (32 archivos)
│   ├── ❌ test_config_compatibility.py (IDENTICO - ELIMINAR)
│   ├── ❌ test_generate_config.py (IDENTICO - ELIMINAR)
│   ├── 📦 test_bugfix_workorders.py (DIFERENTE - MOVER A tests/)
│   ├── 📦 test_complete_o_key_fix.py (DIFERENTE - MOVER A tests/)
│   ├── 📦 test_dashboard_*.py (13 archivos - MOVER A tests/)
│   ├── 📦 test_replay_*.py (8 archivos - MOVER A tests/)
│   ├── 📦 test_event_sourcing_*.py (2 archivos - MOVER A tests/)
│   └── ✅ test_quick_jsonl.py (MANTENER - Usado en docs)
│
├── 📁 DEBUG (11 archivos)
│   └── 📦 debug_*.py (MOVER A tools/debug/)
│
└── 📁 TOOLS
    └── ❌ tools/configurator.py (OBSOLETO - ELIMINAR)
```

---

## ARCHIVOS CORRECTOS A USAR

### ✅ COMANDOS PRINCIPALES

| Comando | Archivo CORRECTO | Archivo OBSOLETO |
|---------|------------------|------------------|
| Configurador | `configurator.py` | `tools/configurator.py` ❌ |
| Simulacion | `entry_points/run_live_simulation.py` | `run_live_simulation.py` ❌ |
| Replay | `entry_points/run_replay_viewer.py` | `run_replay_viewer.py` ❌ |
| Test Rapido | `test_quick_jsonl.py` | N/A |

### ✅ MODULOS INTERNOS

| Modulo | Ubicacion CORRECTA | Ubicacion OBSOLETA |
|--------|-------------------|-------------------|
| AnalyticsEngine | `src/engines/analytics_engine.py` | `analytics_engine.py` ❌ |
| Exporter | `src/analytics/exporter.py` | `analytics/exporter.py` ❌ |
| ExporterV2 | `src/analytics/exporter_v2.py` | `analytics/exporter_v2.py` ❌ |
| ConfigManager | `src/core/config_manager.py` | `core/config_manager.py` ❌ |
| ConfigUtils | `src/core/config_utils.py` | `core/config_utils.py` ❌ |
| ReplayBuffer | `simulation_buffer.py` ⚠️ | `src/shared/buffer.py` ⚠️ |

---

## ESTADISTICAS DE DUPLICACION

```
TOTAL DE ARCHIVOS DUPLICADOS: 50+

CATEGORIA                    | CANTIDAD | ESTADO
-----------------------------|----------|------------------
Entry Points                 | 3        | 2 obsoletos, 1 correcto
Modulos Core/Analytics       | 6        | 5 obsoletos, 1 revisar
Tests Identicos              | 2        | Eliminar de raiz
Tests Diferentes             | 13       | Consolidar
Tests Solo en Raiz           | 17       | Mover a tests/
Archivos Debug               | 11       | Mover a tools/debug/
```

---

## IMPACTO DE LA LIMPIEZA

### ANTES (Situacion Actual)
```
❌ 50+ archivos duplicados
❌ Confusion sobre cual modificar
❌ Imports incorrectos
❌ Mantenimiento complejo
❌ Agentes AI confundidos
```

### DESPUES (Post-Limpieza)
```
✅ 1 version por archivo
✅ Claridad absoluta
✅ Imports correctos
✅ Mantenimiento simple
✅ Agentes AI efectivos
```

---

## PLAN DE LIMPIEZA EN 5 FASES

```
FASE 1: LIMPIEZA INMEDIATA
├── Eliminar entry points obsoletos (2 archivos)
├── Eliminar tests identicos (2 archivos)
└── Eliminar configurator obsoleto (1 archivo)
    Tiempo estimado: 5 minutos
    Riesgo: BAJO

FASE 2: CONSOLIDACION DE MODULOS
├── Eliminar analytics_engine.py (raiz)
├── Eliminar analytics/ (raiz)
├── Eliminar core/ (raiz)
└── Corregir imports en simulation_engine.py
    Tiempo estimado: 15 minutos
    Riesgo: MEDIO (requiere pruebas)

FASE 3: ORGANIZACION DE TESTS
├── Mover tests a tests/ (30+ archivos)
└── Mantener solo test_quick_jsonl.py en raiz
    Tiempo estimado: 10 minutos
    Riesgo: BAJO

FASE 4: LIMPIEZA DE DEBUG
├── Crear tools/debug/
└── Mover debug_*.py (11 archivos)
    Tiempo estimado: 5 minutos
    Riesgo: BAJO

FASE 5: ACTUALIZACION DE DOCUMENTACION
├── Actualizar INSTRUCCIONES.md
├── Actualizar HANDOFF.md
└── Actualizar ACTIVE_SESSION_STATE.md
    Tiempo estimado: 10 minutos
    Riesgo: BAJO

TOTAL: ~45 minutos
```

---

## COMANDOS PARA EJECUTAR (Despues de Aprobacion)

### FASE 1: Limpieza Inmediata
```bash
# Crear directorio legacy si no existe
mkdir -p legacy

# Mover entry points obsoletos
mv run_live_simulation.py legacy/
mv run_replay_viewer.py legacy/

# Eliminar tests identicos
rm test_config_compatibility.py
rm test_generate_config.py

# Mover configurator obsoleto
mv tools/configurator.py legacy/tools_configurator_old.py
```

### FASE 2: Consolidacion de Modulos
```bash
# Eliminar duplicados en raiz
rm analytics_engine.py
rm -rf analytics/
rm -rf core/

# IMPORTANTE: Despues de esto, corregir imports manualmente en:
# - src/engines/simulation_engine.py (linea 38)
```

### FASE 3: Organizacion de Tests
```bash
# Mover tests a subdirectorios apropiados
mv test_dashboard_*.py tests/integration/
mv test_replay_*.py tests/integration/
mv test_event_sourcing_*.py tests/integration/
mv test_bugfix_*.py tests/bugfixes/
mv test_pyqt6_*.py tests/bugfixes/
mv test_complete_*.py tests/bugfixes/
mv test_minimal_*.py tests/integration/
mv test_real_*.py tests/integration/
mv test_multi_*.py tests/integration/
mv test_modern_*.py tests/integration/
mv test_fase8_*.py tests/integration/
mv test_pick_*.py tests/integration/

# Mantener en raiz:
# - test_quick_jsonl.py (usado en documentacion)
```

### FASE 4: Limpieza de Debug
```bash
# Crear directorio debug en tools
mkdir -p tools/debug

# Mover archivos debug
mv debug_*.py tools/debug/
```

### FASE 5: Verificacion
```bash
# Verificar que el sistema sigue funcionando
python test_quick_jsonl.py

# Verificar imports
python -c "from src.engines.simulation_engine import SimulationEngine; print('OK')"
```

---

## VERIFICACION POST-LIMPIEZA

### Checklist de Verificacion:
- [ ] `python configurator.py` funciona correctamente
- [ ] `python entry_points/run_live_simulation.py --headless` funciona
- [ ] `python entry_points/run_replay_viewer.py [archivo.jsonl]` funciona
- [ ] `python test_quick_jsonl.py` funciona
- [ ] No hay errores de import
- [ ] Documentacion actualizada
- [ ] Git status limpio (archivos eliminados commiteados)

---

## BENEFICIOS ESPERADOS

1. **Claridad Absoluta**
   - Solo 1 version de cada archivo
   - No mas confusion sobre cual modificar

2. **Mantenimiento Simplificado**
   - Menos archivos que mantener
   - Estructura mas clara

3. **Agentes AI Mas Efectivos**
   - No mas ambiguedad en instrucciones
   - Modificaciones en archivos correctos

4. **Codigo Mas Limpio**
   - Imports correctos
   - Estructura organizada

5. **Documentacion Precisa**
   - Comandos actualizados
   - Referencias correctas

---

**RECOMENDACION FINAL:**

✅ **APROBAR Y EJECUTAR** el plan de limpieza en 5 fases
⚠️ **HACER BACKUP** antes de empezar (commit actual)
🧪 **PROBAR** despues de cada fase
📝 **DOCUMENTAR** cambios realizados

---

**Fecha:** 2025-01-15
**Estado:** PENDIENTE DE APROBACION
**Prioridad:** ALTA

