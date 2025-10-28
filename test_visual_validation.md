# TEST DE VALIDACION VISUAL - Disminucion Gradual de Volumen

**Fecha:** 2025-10-27
**Objetivo:** Validar que las barras de volumen disminuyen gradualmente en el dashboard

---

## INSTRUCCIONES PARA VALIDACION

### Paso 1: Generar Nueva Simulacion

```bash
python test_volumen_visual.py
```

Este script:
- Genera una simulacion corta con 1 Ground Operator
- Configuracion: 15 WOs, Tour Mixto (Multi-Staging)
- Analiza si hay eventos `partial_discharge`
- Abre el replay viewer automaticamente

### Paso 2: Observar el Dashboard

En el dashboard lateral izquierdo, busca el operario **GroundOp-Test01** y observa la barra de volumen.

**Validar:**

1. **Carga Inicial:** El operario empieza con carga (ej: 150L)
2. **Primera Descarga:** Cuando descarga en el PRIMER staging, el volumen DEBE disminuir (ej: 150L → 100L)
3. **Segunda Descarga:** Cuando descarga en el SEGUNDO staging, el volumen DEBE disminuir nuevamente (ej: 100L → 50L)
4. **Descarga Final:** Al terminar de descargar todo, el volumen DEBE llegar a 0L

### Paso 3: Criterios de Exito

- ✅ El volumen disminuye GRADUALMENTE en cada descarga
- ✅ NO hay saltos directos de 150L a 0L
- ✅ Las transiciones son SUAVES y VISIBLES
- ✅ El volumen final llega correctamente a 0L

### Paso 4: Reportar Resultados

**Si funciona correctamente:**
- Las barras muestran disminucion gradual
- Se ven 2-3 transiciones de volumen antes de llegar a 0L
- El comportamiento es realista

**Si NO funciona:**
- Las barras saltan directamente de carga inicial a 0L
- No se ven transiciones intermedias
- El comportamiento no es gradual

---

## ALTERNATIVA: Ejecutar Manualmente

Si el script automatico no funciona, ejecuta manualmente:

### 1. Generar simulacion:
```bash
python entry_points/run_generate_replay.py config_test_volumen.json
```

### 2. Encontrar el archivo generado:
Busca en `output/simulation_*/replay_*.jsonl` el mas reciente

### 3. Abrir replay viewer:
```bash
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

### 4. Observar y validar:
Usa las instrucciones del Paso 2 anterior

---

## SOLUCIONES APLICADAS

### Cambio 1: Handler para `partial_discharge`
**Archivo:** `src/engines/replay_engine.py` (linea 526-541)

El handler actualiza inmediatamente el volumen cuando se procesa un evento `partial_discharge`:
```python
elif event_type == 'partial_discharge':
    # Actualiza cargo_volume en estado_visual
    estado_visual["operarios"][agent_id]['cargo_volume'] = cargo_restante
```

### Cambio 2: Leer `cargo_volume` en dashboard
**Archivo:** `src/subsystems/visualization/dashboard_world_class.py` (linea 787)

El dashboard ahora lee `cargo_volume` en lugar de solo `carga_actual`:
```python
carga_actual = operario.get('cargo_volume') or operario.get('carga_actual', 0)
```

---

## RESULTADO ESPERADO

Si todo esta correcto, deberias ver:

```
Tiempo    Volumen    Evento
t=120s    150L       [Operario cargado]
t=121s    145L       [Descarga en staging 1: -5L]
t=122s    145L       [Sigue con carga]
t=130s    130L       [Descarga en staging 2: -15L]
t=131s    130L       [Sigue con carga]
t=150s    100L       [Descarga en staging 3: -30L]
t=151s      0L       [Descarga final, todo descargado]
```

La barra de volumen en el dashboard debe mostrar estas transiciones de forma visible y gradual.

---

**Listo para validacion!**

