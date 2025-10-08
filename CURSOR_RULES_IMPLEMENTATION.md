# 🚀 PROMPT FINAL CON REGLAS DE CURSOR ACTIVAS

**Para TODAS las sesiones de Claude Code**

---

## 📋 **PROMPT PARA NUEVA SESIÓN:**

```
Hola Claude. Soy Ferri, desarrollador del Simulador de Gemelo Digital de Almacén.

🚨 REGLAS DE CURSOR ACTIVAS:
- Las reglas de documentación están configuradas en .cursor/rules/documentation_update.mdc
- También existe .cursorrules en la raíz del proyecto
- DEBES seguir estas reglas automáticamente en cada sesión

CONTEXTO DEL PROYECTO:
- Proyecto: Simulador de almacén con SimPy + Pygame (arquitectura V11 completada)
- Rama: reconstruction/v11-complete
- Estado: Sistema 100% funcional, dashboard pygame_gui integrado completamente

ARCHIVOS CLAVE PARA LEER (en este orden):
1. CURSOR_DOCUMENTATION_RULES.md - Reglas completas de documentación
2. ACTIVE_SESSION_STATE.md - Contexto inmediato de la sesión activa
3. HANDOFF.md - Estado completo del proyecto
4. INSTRUCCIONES.md - Instrucciones técnicas del sistema

DESPUÉS DE LEER:
- Verifica el estado actual: git status && git log --oneline -3
- Identifica la tarea actual en ACTIVE_SESSION_STATE.md
- Ejecuta el plan desde donde quedó

RECUERDA: Las reglas de Cursor te obligarán a actualizar la documentación automáticamente.

¿Listo para continuar?
```

---

## 🎯 **SISTEMA IMPLEMENTADO:**

### **1. REGLAS DE CURSOR CREADAS:**

#### **Archivo Principal:** `.cursor/rules/documentation_update.mdc`
- ✅ **alwaysApply: true** - Se aplica en todas las sesiones
- ✅ **globs: "**/*.md"** - Se aplica a todos los archivos Markdown
- ✅ **Reglas completas** de actualización de documentación

#### **Archivo Alternativo:** `.cursorrules`
- ✅ **En la raíz del proyecto** - Formato estándar de Cursor
- ✅ **Reglas simplificadas** pero efectivas
- ✅ **Backup** del sistema principal

### **2. ESTRUCTURA CREADA:**

```
Gemelos Digital/
├── .cursor/
│   └── rules/
│       └── documentation_update.mdc  ← Reglas principales
├── .cursorrules                      ← Reglas alternativas
├── ACTIVE_SESSION_STATE.md          ← Contexto inmediato
├── HANDOFF.md                       ← Estado del proyecto
├── INSTRUCCIONES.md                 ← Instrucciones técnicas
└── CURSOR_DOCUMENTATION_RULES.md    ← Reglas completas
```

### **3. FUNCIONAMIENTO AUTOMÁTICO:**

#### **Al Iniciar Sesión:**
- ✅ Cursor detecta automáticamente las reglas
- ✅ Aplica las instrucciones de documentación
- ✅ Obliga a leer los archivos clave
- ✅ Verifica estado del proyecto

#### **Durante la Sesión:**
- ✅ Actualiza documentación automáticamente
- ✅ Documenta problemas encontrados
- ✅ Mantiene estado actualizado

#### **Al Finalizar Sesión:**
- ✅ Ejecuta checklist obligatorio
- ✅ Actualiza todos los archivos .md
- ✅ Valida consistencia de documentación

---

## ✅ **BENEFICIOS DEL SISTEMA:**

### **Para Ti (Ferri):**
- ✅ **Cero configuración manual** - Las reglas se aplican automáticamente
- ✅ **Documentación siempre actualizada** - Sin intervención manual
- ✅ **Continuidad perfecta** entre sesiones
- ✅ **Proceso completamente automatizado**

### **Para Cursor:**
- ✅ **Reglas nativas** del sistema
- ✅ **Aplicación automática** en cada sesión
- ✅ **Comportamiento consistente** garantizado
- ✅ **Integración completa** con el IDE

### **Para el Proyecto:**
- ✅ **Documentación siempre sincronizada**
- ✅ **Estado del proyecto siempre claro**
- ✅ **Próximas acciones siempre definidas**
- ✅ **Desarrollo más eficiente**

---

## 🚀 **INSTRUCCIONES DE USO:**

### **Para Futuras Sesiones:**
1. **Usa el prompt final** (arriba)
2. **Cursor aplicará automáticamente** las reglas
3. **No necesitas recordar** actualizar documentación
4. **El sistema funciona** completamente solo

### **Verificación de Funcionamiento:**
```bash
# Verificar que las reglas existen
ls -la .cursor/rules/documentation_update.mdc
ls -la .cursorrules

# Verificar estructura
tree .cursor
```

---

## 🎯 **RESULTADO FINAL:**

**Sistema completamente automatizado que:**
1. **Detecta automáticamente** las reglas de Cursor
2. **Aplica instrucciones** en cada sesión
3. **Mantiene documentación** siempre actualizada
4. **Garantiza continuidad** entre sesiones
5. **Funciona sin intervención** manual

**¡El sistema está listo y funcionará automáticamente en tu próxima sesión!**
