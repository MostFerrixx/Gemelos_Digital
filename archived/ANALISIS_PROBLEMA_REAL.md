# ANÁLISIS DEL PROBLEMA REAL - Generación de Archivos

**Fecha:** 2025-10-07  
**Estado:** ✅ Simulación termina OK, ❌ Errores en exportación

---

## ✅ BUENAS NOTICIAS

### 1. **Bucle infinito RESUELTO**
```
[ALMACEN] Simulacion finalizada en t=4907.00
[GroundOp-01] Simulacion finalizada, saliendo...
[DISPATCHER-PROCESS] Simulacion finalizada en t=4907.10
Simulacion Headless completada.
```

### 2. **Simulación funciona correctamente**
- 609 WorkOrders completadas de 609 totales
- Tiempo total: 4907 segundos simulados
- Operarios finalizaron correctamente

---

## ❌ PROBLEMA REAL IDENTIFICADO

### Error 1: `exportar_metricas()` 
```
Error exportando metricas JSON: exportar_metricas() takes 1 positional argument but 2 were given
```

**CAUSA:** Firma incorrecta del método `exportar_metricas()`  
**UBICACIÓN:** `src/engines/analytics_engine.py`

### Error 2: KeyError 'event_type'
```
Error en pipeline de analiticas: 'event_type'
```

**CAUSA:** Los eventos tienen campo `'type'` pero el código busca `'event_type'`  
**UBICACIÓN:** `src/engines/analytics_engine.py`

---

## 📊 RESULTADO ACTUAL

### Archivos Generados (1 de 4-5 esperados):
✅ `raw_events_20251007_191051.json` (401,090 bytes)

### Archivos FALTANTES:
❌ `replay_YYYYMMDD_HHMMSS.jsonl` ← **OBJETIVO PRINCIPAL**
❌ `simulacion_completada_YYYYMMDD_HHMMSS.json`
❌ `metricas_YYYYMMDD_HHMMSS.xlsx`
❌ Otros archivos de análisis

---

## 🔍 DIAGNÓSTICO DETALLADO

### 1. ¿Por qué falta el archivo `.jsonl`?

**RUTA DE GENERACIÓN:**
```
SimulationEngine.run()
  → volcar_replay_a_archivo(replay_buffer, output_dir)
```

**PROBLEMA:** Esta función NO se ejecuta cuando hay errores en analytics

**VERIFICAR:**
- ¿Se llama `volcar_replay_a_archivo()` después de completar?
- ¿Se ejecuta incluso si analytics falla?
- ¿Ruta de output_dir es correcta?

### 2. ¿Qué causa el error en analytics?

**ARCHIVO:** `src/engines/analytics_engine.py`

**Método `exportar_metricas()`:**
```python
# ACTUAL (INCORRECTO):
def exportar_metricas(self, output_dir):  # 2 argumentos
    # ...

# LLAMADA:
exporter.exportar_metricas(self.session_output_dir)  # 2 argumentos
# Error: "takes 1 positional argument but 2 were given"
```

**PROBLEMA:** Probablemente es un método de clase incorrecto o falta `self`

---

## 🛠️ PLAN DE REPARACIÓN

### PRIORIDAD 1: Asegurar generación de `.jsonl` ✅
**Archivo:** `src/engines/simulation_engine.py`
**Acción:** Garantizar que `volcar_replay_a_archivo()` se ejecute SIEMPRE

```python
try:
    # Analytics pipeline
    exporter = AnalyticsExporterV2(...)
    exporter.exportar_metricas(...)
except Exception as e:
    print(f"[WARNING] Analytics failed: {e}")
finally:
    # SIEMPRE generar JSONL
    volcar_replay_a_archivo(self.replay_buffer, self.session_output_dir)
```

### PRIORIDAD 2: Fix error `exportar_metricas()` ✅
**Archivo:** `src/engines/analytics_engine.py`
**Revisar:**
1. Firma del método
2. Si es método de instancia o clase
3. Cómo se instancia el exporter

### PRIORIDAD 3: Fix error `'event_type'` ✅
**Archivo:** `src/engines/analytics_engine.py`
**Cambiar:**
```python
# ANTES:
event_type = evento['event_type']  # ❌ No existe

# DESPUÉS:
event_type = evento.get('type') or evento.get('event_type', 'unknown')  # ✅
```

---

## 📝 ARCHIVOS A MODIFICAR

| Archivo | Razón |
|---------|-------|
| `src/engines/simulation_engine.py` | Garantizar generación `.jsonl` |
| `src/engines/analytics_engine.py` | Fix `exportar_metricas()` |
| `src/engines/analytics_engine.py` | Fix `'event_type'` → `'type'` |

---

## 🎯 OBJETIVO

**DESPUÉS DEL FIX:**
```bash
python test_quick_jsonl.py

# DEBE GENERAR:
output/simulation_YYYYMMDD_HHMMSS/
  ├── replay_YYYYMMDD_HHMMSS.jsonl  ← ✅ PRINCIPAL
  ├── raw_events_YYYYMMDD_HHMMSS.json  ← ✅ Ya funciona
  ├── simulacion_completada_YYYYMMDD_HHMMSS.json  ← Bonus
  ├── metricas_YYYYMMDD_HHMMSS.xlsx  ← Bonus
  └── ...
```

---

## ⚠️ NOTA IMPORTANTE

El archivo `replay_buffer` **TIENE DATOS** (609 eventos).  
El problema NO es que falten eventos, sino que **NO se está volcando a disco**.

**EVIDENCIA:**
```
[DISPATCHER-PROCESS] WorkOrders completadas: 609/609
[ANALYTICS V2] Eventos exportados: 609 eventos  ← Buffer tiene datos
```

---

**SIGUIENTE PASO:** Aplicar los 3 fixes identificados.


