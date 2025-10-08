# 🚀 PROMPT UNIVERSAL CON REGLAS OBLIGATORIAS

**Para TODAS las sesiones de Claude Code**

---

## 📋 **PROMPT PARA NUEVA SESIÓN:**

```
Hola Claude. Soy Ferri, desarrollador del Simulador de Gemelo Digital de Almacén.

🚨 REGLAS OBLIGATORIAS DE DOCUMENTACIÓN:
- DEBES leer y actualizar los archivos .md según CURSOR_DOCUMENTATION_RULES.md
- AL FINALIZAR la sesión, DEBES actualizar ACTIVE_SESSION_STATE.md obligatoriamente
- DURANTE la sesión, DEBES actualizar cuando completes fases o encuentres problemas

CONTEXTO DEL PROYECTO:
- Proyecto: Simulador de almacén con SimPy + Pygame (arquitectura V11 completada)
- Rama: reconstruction/v11-complete
- Estado: Sistema 100% funcional, dashboard pygame_gui integrado completamente

ARCHIVOS CLAVE PARA LEER (en este orden):
1. CURSOR_DOCUMENTATION_RULES.md - REGLAS OBLIGATORIAS (LEER PRIMERO)
2. ACTIVE_SESSION_STATE.md - Contexto inmediato de la sesión activa
3. HANDOFF.md - Estado completo del proyecto
4. INSTRUCCIONES.md - Instrucciones técnicas del sistema

DESPUÉS DE LEER:
- Verifica el estado actual: git status && git log --oneline -3
- Identifica la tarea actual en ACTIVE_SESSION_STATE.md
- Ejecuta el plan desde donde quedó

RECUERDA: Al finalizar esta sesión, DEBES actualizar la documentación según las reglas obligatorias.

¿Listo para continuar?
```

---

## 🔧 **IMPLEMENTACIÓN DE LAS REGLAS**

### **1. AL INICIAR SESIÓN:**

**COMANDOS OBLIGATORIOS:**
```bash
# 1. Leer reglas de documentación
cat CURSOR_DOCUMENTATION_RULES.md

# 2. Verificar estado del proyecto
git status
git log --oneline -3

# 3. Validar archivos mencionados en documentación
ls -la ACTIVE_SESSION_STATE.md HANDOFF.md INSTRUCCIONES.md
```

### **2. DURANTE LA SESIÓN:**

**ACTUALIZACIONES OBLIGATORIAS:**
- ✅ Al completar una fase: Marcar en ACTIVE_SESSION_STATE.md
- ✅ Al encontrar problema: Documentar en ACTIVE_SESSION_STATE.md
- ✅ Al cambiar enfoque: Actualizar próxima acción
- ✅ Al modificar archivos técnicos: Actualizar INSTRUCCIONES.md

### **3. AL FINALIZAR SESIÓN:**

**CHECKLIST OBLIGATORIO:**
```bash
# 1. Verificar estado actual
git status
git log --oneline -3

# 2. Actualizar ACTIVE_SESSION_STATE.md con:
#    - Fases completadas marcadas como ✅
#    - Próxima acción claramente definida
#    - Problemas encontrados documentados
#    - Tiempo estimado restante actualizado

# 3. Si completaste fase importante: Actualizar HANDOFF.md
# 4. Si cambió algo técnico: Actualizar INSTRUCCIONES.md

# 5. Verificar consistencia de documentación
grep -n "Estado:" *.md
grep -n "Fecha:" *.md
```

---

## 📝 **TEMPLATES PARA ACTUALIZACIÓN OBLIGATORIA**

### **ACTUALIZACIÓN DE ACTIVE_SESSION_STATE.md:**

```markdown
# 🚀 ESTADO DE SESIÓN ACTIVA - [NOMBRE_TAREA]

**Fecha:** [FECHA_ACTUAL]
**Sesión:** [NOMBRE_SESIÓN]
**Estado:** [ESTADO_ACTUAL]

## 📋 CONTEXTO INMEDIATO
### TAREA ACTUAL: [DESCRIPCIÓN_CLARA]
### PROBLEMA IDENTIFICADO: [LISTA_PROBLEMAS]
### SOLUCIÓN DISEÑADA: [LISTA_SOLUCIONES]

## 🛠️ PLAN DE IMPLEMENTACIÓN
### FASE 1: [NOMBRE] ([TIEMPO]) - ✅ COMPLETADA / ⏳ EN PROGRESO / ⏳ PENDIENTE
- [x] Tarea 1 (completada)
- [ ] Tarea 2 (pendiente)

### PRÓXIMO PASO: [ACCIÓN_INMEDIATA]
**ESTADO:** ✅ [ESTADO_ACTUAL]
**TIEMPO ESTIMADO RESTANTE:** [TIEMPO]
```

### **ACTUALIZACIÓN DE HANDOFF.md:**

```markdown
## What Has Been Done
✅ **[NUEVA_FASE_COMPLETADA]:** [DESCRIPCIÓN]
- [Detalle 1]
- [Detalle 2]

## What Needs to Be Done Next
### IMMEDIATE TASK: [NUEVA_TAREA] ⏳
**Próximo Paso:** [DESCRIPCIÓN_DETALLADA]
```

---

## ⚠️ **VALIDACIÓN FINAL OBLIGATORIA**

**ANTES de finalizar cualquier sesión, ejecuta:**

```bash
# Verificar que la documentación está actualizada
echo "=== VERIFICACIÓN DE DOCUMENTACIÓN ==="
echo "1. ACTIVE_SESSION_STATE.md actualizado:"
grep -n "Fecha:" ACTIVE_SESSION_STATE.md
grep -n "Estado:" ACTIVE_SESSION_STATE.md

echo "2. Próxima acción definida:"
grep -A 2 "PRÓXIMO PASO" ACTIVE_SESSION_STATE.md

echo "3. Estado del proyecto:"
git status --porcelain
git log --oneline -1

echo "=== DOCUMENTACIÓN VERIFICADA ==="
```

**SOLO después de esta verificación puedes finalizar la sesión.**

---

## 🎯 **RESULTADO ESPERADO**

Con estas reglas obligatorias:

✅ **Cada sesión** mantiene documentación actualizada  
✅ **Cada nueva sesión** puede continuar inmediatamente  
✅ **No hay pérdida** de contexto entre sesiones  
✅ **Documentación** siempre refleja el estado real  
✅ **Proceso** es automático y consistente  

**¡ESTAS REGLAS SON OBLIGATORIAS Y DEBEN SEGUIRSE EN TODAS LAS SESIONES!**
