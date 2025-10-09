# ✅ CHECKLIST - NUEVA SESIÓN DE DEBUGGING

**Propósito:** Guía paso a paso para continuar el debugging del replay_buffer vacío

---

## 📋 FASE 1: PREPARACIÓN (5 minutos)

### ☐ 1.1 Lectura de Documentación
```
- [ ] Leer RESUMEN_PARA_NUEVA_SESION.md (1-2 min)
- [ ] Leer ACTIVE_SESSION_STATE.md (2-3 min)  
- [ ] Leer STATUS_VISUAL.md (1 min)
- [ ] Opcional: HANDOFF.md para contexto completo
```

### ☐ 1.2 Verificación del Entorno
```bash
# Navegar al proyecto
cd "C:\Users\ferri\OneDrive\Escritorio\Gemelos Digital"

# Verificar estado de git
git status
git log --oneline -3

# Verificar archivos modificados
git diff --name-only
```

### ☐ 1.3 Entender el Problema
```
Problema: replay_buffer está vacío al finalizar simulación
Causa: buffer es None cuando se llama registrar_evento()
Ubicación: src/subsystems/simulation/warehouse.py:431-449
```

**✅ Fase 1 completa cuando entiendas:** "El buffer se crea OK pero luego es None"

---

## 🔍 FASE 2: REPRODUCIR EL BUG (5 minutos)

### ☐ 2.1 Ejecutar Test Rápido
```bash
python test_quick_jsonl.py
```

**Esperado:**
- Simulación completa en 20-40 segundos
- Mensaje: `[REPLAY WARNING] No replay data to save`
- Solo 1 archivo generado en output/

### ☐ 2.2 Ver Logs de REPLAY
```bash
python test_quick_jsonl.py 2>&1 | Select-String -Pattern "REPLAY|ALMACEN DEBUG"
```

**Esperado:**
```
[ALMACEN DEBUG] __init__ replay_buffer: ReplayBuffer(events=0)  ← OK
[REPLAY ERROR] replay_buffer is None at registrar_evento!      ← PROBLEMA
[REPLAY DEBUG] replay_buffer len: 0                            ← VACÍO
```

### ☐ 2.3 Confirmar Síntomas
```
- [ ] Simulación completa correctamente (609 WOs completadas)
- [ ] Buffer se inicializa en __init__
- [ ] Buffer es None en registrar_evento()
- [ ] Buffer está vacío al finalizar
- [ ] Archivo .jsonl NO se genera
```

**✅ Fase 2 completa cuando:** Puedas reproducir el bug consistentemente

---

## 🕵️ FASE 3: CAPTURAR STACKTRACE (10 minutos)

### ☐ 3.1 Capturar Output Completo
```bash
python test_quick_jsonl.py 2>&1 > debug_full.txt
```

### ☐ 3.2 Analizar Stacktrace
```bash
# Buscar la sección con [REPLAY ERROR]
notepad debug_full.txt
# Buscar: "REPLAY ERROR"
```

**Buscar:**
1. Líneas antes del error (contexto)
2. Stacktrace completo (File "...", line X)
3. Flujo de llamadas completo
4. ID de la instancia de almacén

### ☐ 3.3 Identificar Flujo de Llamadas

**Preguntas clave:**
```
1. ¿Desde dónde se llama registrar_evento()?
   → Respuesta esperada: dispatcher.py:502

2. ¿Qué instancia de almacén se usa?
   → Verificar: id(self) en el log

3. ¿Es la misma instancia que se inicializó con buffer?
   → Comparar IDs de instancia

4. ¿Hay alguna serialización/deserialización?
   → Buscar: pickle, multiprocessing.Process
```

### ☐ 3.4 Agregar Debug Adicional (si necesario)

Si el stacktrace no es suficiente, agregar:

```python
# En warehouse.py, método registrar_evento (línea ~444):
print(f"[DEBUG] self id: {id(self)}")
print(f"[DEBUG] self.dispatcher.almacen id: {id(self.dispatcher.almacen)}")
print(f"[DEBUG] replay_buffer type: {type(self.replay_buffer)}")
print(f"[DEBUG] Has attr: {hasattr(self, 'replay_buffer')}")
```

**✅ Fase 3 completa cuando:** Tengas stacktrace completo y flujo de llamadas identificado

---

## 🔧 FASE 4: IDENTIFICAR CAUSA RAÍZ (15 minutos)

### ☐ 4.1 Verificar Hipótesis 1: Múltiples Instancias

```python
# Agregar en warehouse.py __init__ (línea ~152):
print(f"[INIT] AlmacenMejorado instance created: id={id(self)}")

# Agregar en registrar_evento (línea ~444):
print(f"[EVENTO] Called on instance: id={id(self)}")
```

**Si IDs son diferentes → HAY MÚLTIPLES INSTANCIAS**

### ☐ 4.2 Verificar Hipótesis 2: Sobrescritura

```bash
# Buscar todas las asignaciones a replay_buffer
grep -n "replay_buffer\s*=" src/subsystems/simulation/warehouse.py
```

**Esperado:** Solo 1 línea (la del __init__)

### ☐ 4.3 Verificar Hipótesis 3: Serialización

```bash
# Buscar uso de pickle o multiprocessing en modo headless
grep -n "pickle\|Process\|Queue" src/engines/simulation_engine.py
```

**Verificar:** ¿Se crea proceso hijo en modo headless?

### ☐ 4.4 Revisar Creación de Dispatcher

```python
# En warehouse.py, línea ~173-178:
self.dispatcher = DispatcherV11(
    env=env,
    almacen=self,  # ← ¿Pasa la referencia correcta?
    ...
)
```

**Verificar:** ¿El dispatcher guarda `almacen=self` correctamente?

### ☐ 4.5 Conclusión de Causa Raíz

```
Causa identificada: _________________________________

Evidencia: _________________________________________

Archivo afectado: __________________________________

Línea(s) problemática(s): __________________________
```

**✅ Fase 4 completa cuando:** Sepas EXACTAMENTE por qué buffer es None

---

## 🛠️ FASE 5: IMPLEMENTAR FIX (15 minutos)

### ☐ 5.1 Diseñar Solución

**Si múltiples instancias:**
```
Solución: Asegurar que solo haya UNA instancia con buffer correcto
Implementación: Pasar buffer a todas las instancias correctamente
```

**Si sobrescritura:**
```
Solución: Remover código que sobrescribe buffer
Implementación: Eliminar línea problemática
```

**Si serialización:**
```
Solución: No serializar almacén, o reconstruir buffer
Implementación: Pasar buffer por otro medio (global, singleton, etc.)
```

### ☐ 5.2 Implementar Fix

```python
# Archivo: _______________________
# Línea: ________________________

# ANTES:
[código problemático]

# DESPUÉS:
[código corregido]
```

### ☐ 5.3 Agregar Comentario Explicativo

```python
# BUGFIX JSONL: [Explicación breve del fix]
# Problema: [Descripción del problema]
# Solución: [Descripción de la solución]
[código del fix]
```

**✅ Fase 5 completa cuando:** Fix implementado y comentado

---

## ✅ FASE 6: VALIDAR FIX (15 minutos)

### ☐ 6.1 Test Rápido
```bash
python test_quick_jsonl.py
```

**Esperado:**
```
[REPLAY DEBUG] Evento agregado al buffer: work_order_update, total: 1
[REPLAY DEBUG] Evento agregado al buffer: work_order_update, total: 2
[REPLAY DEBUG] Evento agregado al buffer: work_order_update, total: 3
...
[REPLAY DEBUG] replay_buffer len: 609
[REPLAY] Generating replay file: output/simulation_YYYYMMDD_HHMMSS/replay_YYYYMMDD_HHMMSS.jsonl
[REPLAY] Replay file generated successfully: 609 events
```

### ☐ 6.2 Verificar Archivo Generado

```bash
# Verificar que existe
ls output/simulation_*/replay_*.jsonl

# Ver tamaño
ls -lh output/simulation_*/replay_*.jsonl

# Contar líneas (debe ser > 500)
wc -l output/simulation_*/replay_*.jsonl

# Ver contenido
head -5 output/simulation_*/replay_*.jsonl
```

### ☐ 6.3 Validar Contenido

```bash
# Verificar formato JSON
cat output/simulation_*/replay_*.jsonl | python -m json.tool | head -20

# Buscar eventos clave
grep "SIMULATION_START" output/simulation_*/replay_*.jsonl
grep "work_order_update" output/simulation_*/replay_*.jsonl | wc -l
grep "SIMULATION_END" output/simulation_*/replay_*.jsonl
```

### ☐ 6.4 Test Completo

```bash
# Ejecutar simulación completa
python entry_points/run_live_simulation.py --headless

# Verificar que .jsonl se genera correctamente
ls -lh output/simulation_*/replay_*.jsonl
```

### ☐ 6.5 Test con Replay Viewer

```bash
# Cargar archivo en replay viewer
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

**Esperado:** Replay viewer carga y reproduce la simulación

**✅ Fase 6 completa cuando:**
- [ ] Archivo .jsonl se genera
- [ ] Contiene > 500 eventos
- [ ] Formato JSON válido
- [ ] Replay viewer funciona

---

## 🧹 FASE 7: CLEANUP (10 minutos)

### ☐ 7.1 Remover Logs de Debug

**Archivos a limpiar:**

```python
# src/subsystems/simulation/warehouse.py
- Líneas 152-153: Remover debug en __init__
- Líneas 436-437: Remover debug en add_event (if <= 3)
- Líneas 444-449: Simplificar a solo warning si needed

# src/engines/simulation_engine.py
- Líneas 1393-1395: Remover debug en finally
```

### ☐ 7.2 Actualizar Documentación

```markdown
# ACTIVE_SESSION_STATE.md
- [ ] Marcar FASE 4 como ✅ COMPLETADA
- [ ] Actualizar "Próximo paso" a testing/commit
- [ ] Documentar solución implementada

# HANDOFF.md
- [ ] Mover bug de "Known Issues" a "Resolved"
- [ ] Actualizar "What Has Been Done"
- [ ] Actualizar métricas de progreso

# INSTRUCCIONES.md
- [ ] Remover bug de lista de bugs conocidos
- [ ] Actualizar sección de archivos generados
```

### ☐ 7.3 Verificar Calidad de Código

```bash
# Verificar solo ASCII
find src/ -name "*.py" -exec file {} \; | grep -v "ASCII"

# Verificar linting (si tienes pylint/flake8)
pylint src/subsystems/simulation/warehouse.py
pylint src/engines/simulation_engine.py
```

### ☐ 7.4 Limpiar Archivos Temporales

```bash
# Remover outputs de test
rm -rf output/simulation_20*

# Remover archivos de debug
rm debug_full.txt test_output.log

# Restaurar config si estaba en backup
rm config.json.backup_test
```

**✅ Fase 7 completa cuando:** Código limpio y documentación actualizada

---

## 📦 FASE 8: COMMIT (10 minutos)

### ☐ 8.1 Revisar Cambios

```bash
git status
git diff src/subsystems/simulation/warehouse.py
git diff src/engines/simulation_engine.py
```

### ☐ 8.2 Staging

```bash
# Archivos de código
git add src/subsystems/simulation/warehouse.py
git add src/engines/simulation_engine.py
git add src/subsystems/simulation/dispatcher.py
git add src/subsystems/simulation/operators.py

# Documentación
git add ACTIVE_SESSION_STATE.md
git add HANDOFF.md
git add INSTRUCCIONES.md
```

### ☐ 8.3 Commit

```bash
git commit -m "fix(replay): Resolver buffer vacio en generacion de .jsonl

- Fix: [DESCRIPCIÓN ESPECÍFICA DEL FIX]
- Causa: replay_buffer era None en registrar_evento()
- Solución: [DESCRIPCIÓN DE LA SOLUCIÓN]
- Resuelve también: Bucle infinito, AttributeErrors WorkOrder
- Archivos modificados: warehouse.py, simulation_engine.py, dispatcher.py, operators.py
- Testing: Validado con test_quick_jsonl.py y simulación completa"
```

### ☐ 8.4 Verificación Post-Commit

```bash
# Ver commit
git log -1 --stat

# Ejecutar test final
python test_quick_jsonl.py

# Verificar que .jsonl se genera
ls output/simulation_*/replay_*.jsonl
```

**✅ Fase 8 completa cuando:** Commit exitoso y test final pasa

---

## 🎯 CRITERIOS DE ÉXITO FINAL

### ☑️ Funcionalidad
- [ ] Simulación completa sin errores
- [ ] Archivo `.jsonl` se genera automáticamente
- [ ] Archivo contiene > 500 eventos para 600 WOs
- [ ] Replay viewer puede cargar el archivo
- [ ] No hay mensajes `[REPLAY ERROR]`

### ☑️ Calidad
- [ ] Código limpio (sin logs de debug)
- [ ] Solo caracteres ASCII
- [ ] Comentarios claros en fix
- [ ] Sin errores de linting

### ☑️ Documentación
- [ ] ACTIVE_SESSION_STATE.md actualizado
- [ ] HANDOFF.md actualizado
- [ ] INSTRUCCIONES.md actualizado
- [ ] Commit message descriptivo

### ☑️ Testing
- [ ] test_quick_jsonl.py pasa ✅
- [ ] Simulación completa pasa ✅
- [ ] Replay viewer funciona ✅

---

## ⏱️ TIEMPO ESTIMADO POR FASE

```
FASE 1: Preparación           →  5 minutos
FASE 2: Reproducir bug         →  5 minutos
FASE 3: Capturar stacktrace    → 10 minutos
FASE 4: Identificar causa      → 15 minutos
FASE 5: Implementar fix        → 15 minutos
FASE 6: Validar                → 15 minutos
FASE 7: Cleanup                → 10 minutos
FASE 8: Commit                 → 10 minutos
                              ════════════
                    TOTAL      → 85 minutos (~1.5 horas)
```

---

## 🚨 SI TE ATASCAS

### Problema: No puedo reproducir el bug
**Solución:** Verificar que estás usando `test_quick_jsonl.py` y no el script principal

### Problema: Stacktrace no es claro
**Solución:** Agregar más debug logs, ver sección 3.4

### Problema: No sé cuál es la causa raíz
**Solución:** Revisar ANALISIS_PROBLEMA_REAL.md para hipótesis detalladas

### Problema: El fix no funciona
**Solución:**  
1. Revertir cambios: `git checkout -- archivo.py`
2. Re-analizar el problema con más debug
3. Probar solución alternativa

### Problema: Tests fallan después del fix
**Solución:**
1. Verificar que no rompiste nada más
2. Ejecutar `git diff` para ver todos los cambios
3. Revisar linter errors: `python -m pylint archivo.py`

---

## ✅ CHECKLIST FINAL

Antes de dar por terminada la sesión:

```
- [ ] Bug del replay_buffer resuelto
- [ ] Archivo .jsonl se genera correctamente
- [ ] Logs de debug removidos
- [ ] Documentación actualizada
- [ ] Tests pasan
- [ ] Commit realizado
- [ ] Código limpio y comentado
- [ ] No introduje nuevos bugs
```

---

**¡ÉXITO!** 🎉

Cuando completes este checklist, el sistema debería estar **100% funcional** con generación de archivos `.jsonl` operativa.

---

**Última actualización:** 2025-10-08 19:50 UTC  
**Tiempo estimado total:** 1.5 horas  
**Dificultad:** Media (problema bien acotado)

