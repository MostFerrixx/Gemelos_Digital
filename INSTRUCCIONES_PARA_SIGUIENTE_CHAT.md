# 📋 INSTRUCCIONES PARA LA SIGUIENTE VENTANA DE CHAT

**Fecha:** 2025-10-27  
**Tarea:** Implementar corrección de tours cortos con lógica de doble barrido

---

## 🎯 OBJETIVO

Implementar una corrección que haga que los Ground Operators generen tours más largos y eficientes, aumentando la utilización de capacidad del 38.9% al 70-90%.

---

## 📄 DOCUMENTO PRINCIPAL A LEER

**Archivo:** `DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md`

Este documento contiene:
- ✅ Contexto completo del problema
- ✅ Análisis de causa raíz
- ✅ Solución propuesta (lógica de doble barrido)
- ✅ **Código completo a implementar** (150+ líneas)
- ✅ Instrucciones paso a paso
- ✅ Script de validación
- ✅ Checklist de implementación

**Instrucción simple para el siguiente chat:**
```
Lee el archivo DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md 
desde el principio hasta el final y sigue las instrucciones 
para implementar la corrección.
```

---

## 🔧 CAMBIOS A REALIZAR

### 1. Modificar `src/subsystems/simulation/dispatcher.py`

**Método:** `_construir_tour_por_secuencia()` (líneas 502-594)

**Acción:** REEMPLAZAR COMPLETAMENTE el método con el código de la sección 5.1 del documento.

**Código:** Ver sección 5.1 en `DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md`

### 2. Modificar `config.json`

**Cambio:** Corregir capacidad de GroundOperator

**ANTES:**
```json
{
    "type": "GroundOperator",
    "capacity": 500,    ← CAMBIAR ESTO
    ...
}
```

**DESPUÉS:**
```json
{
    "type": "GroundOperator",
    "capacity": 150,    ← A ESTO
    ...
}
```

**Instrucciones detalladas:** Ver sección 6 del documento.

---

## ✅ VALIDACIÓN

### Después de implementar:

1. **Generar nueva simulación:**
   ```bash
   python entry_points/run_generate_replay.py
   ```

2. **Crear y ejecutar script de validación:**
   - Código del script en sección 7.1 del documento
   - Guardar como `validate_fix_tours.py`
   - Ejecutar: `python validate_fix_tours.py`

3. **Verificar criterios de éxito:**
   - ✅ WOs por tour >= 5 (promedio)
   - ✅ Utilización >= 70% (promedio)
   - ✅ No hay errores en logs

---

## 📚 CONTEXTO RÁPIDO

**Problema actual:**
- Ground Operators hacen tours de solo 1.75 WOs
- Utilización de capacidad: 38.9% (muy bajo)
- Causa: Bug en lógica de secuencia cíclica

**Solución propuesta:**
- Lógica de doble barrido (Principal + Secundario)
- Barrido 1: Agrega WOs progresivamente (seq >= min_seq)
- Barrido 2: Llena huecos (seq < min_seq) si queda capacidad
- Corrección de capacidad (500L → 150L)

**Resultado esperado:**
- Tours de 8-12 WOs
- Utilización de 70-90%
- Reducción de tours totales de 12 a 2-3

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### Código:
- [ ] Leer `DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md` completo
- [ ] Abrir `src/subsystems/simulation/dispatcher.py`
- [ ] Localizar método `_construir_tour_por_secuencia()` (líneas 502-594)
- [ ] Reemplazar con código de sección 5.1 del documento
- [ ] Guardar archivo

### Configuración:
- [ ] Abrir `config.json`
- [ ] Buscar `"type": "GroundOperator"`
- [ ] Cambiar `"capacity": 500` a `"capacity": 150`
- [ ] Guardar archivo

### Testing:
- [ ] Crear `validate_fix_tours.py` (código en sección 7.1)
- [ ] Ejecutar simulación
- [ ] Ejecutar validación
- [ ] Verificar criterios de éxito

### Documentación:
- [ ] Actualizar `HANDOFF.md` (plantilla en sección 8.1)
- [ ] Actualizar `ACTIVE_SESSION_STATE.md` (plantilla en sección 8.2)
- [ ] Crear commit de git (mensaje en sección 8.3)

---

## ⚠️ IMPORTANTE

1. **No cambies la capacidad de Forklift** (debe mantener 300L)
2. **Usa solo caracteres ASCII** en el código (no acentos, no ñ)
3. **Respeta la indentación** (4 espacios, no tabs)
4. **Sigue el código exactamente** como está en el documento
5. **Lee TODO el documento** antes de empezar a implementar

---

## 🆘 SI HAY PROBLEMAS

1. Revisa el documento completo de nuevo
2. Verifica logs del dispatcher: `grep "[DISPATCHER]" output/.../*.log`
3. Compara tu código con la sección 5.1 línea por línea
4. Ejecuta el script de validación para ver el comportamiento real

---

## 📞 CONTACTO CON SESIÓN ANTERIOR

Si necesitas clarificaciones sobre el análisis:
- Lee `RESUMEN_SESION_ANALISIS_TOURS.md`
- Lee `ANALISIS_PROBLEMA_TOURS_CORTOS.md`

Pero **todo lo necesario para implementar está en:**
**`DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md`**

---

**RESUMEN EN UNA LÍNEA:**
Lee `DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md` y sigue las instrucciones para implementar el fix.

---

**Última actualización:** 2025-10-27  
**Estado:** ✅ Listo para implementación

