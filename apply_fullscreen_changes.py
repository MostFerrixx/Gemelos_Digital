"""
Script para aplicar cambios de fullscreen canvas
Aplica todos los cambios necesarios en orden
"""

# 1. Aplicar sidebar styles
import subprocess
subprocess.run(['python', 'apply_css_changes.py'], check=True)

# 2. Aplicar cambios de resize  
subprocess.run(['python', 'make_resize_visible.py'], check=True)

# 3. Modificar para que resize handle esté oculto por defecto
with open('web_prototype/static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Cambiar flex de top-section de vuelta a flex: 1 para fullscreen por defecto
content = content.replace(
    'flex: 0 0 65%; /* Changed from flex: 1 to allow resize */',
    'flex: 1; /* Full height by default, changes to flex-basis when dashboard opens */'
)

# Hacer que resize-handle esté oculto por defecto
old_resize = '''.resize-handle {
    height: 8px;
    cursor: ns-resize;
    background: transparent;
    position: relative;
    z-index: 50;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 var(--spacing-lg);
}'''

new_resize = '''.resize-handle {
    height: 8px;
    cursor: ns-resize;
    background: transparent;
    position: relative;
    z-index: 50;
    display: none; /* Hidden by default, shown when dashboard opens */
    align-items: center;
    justify-content: center;
    margin: 0 var(--spacing-lg);
    transition: all var(--transition-base);
}

/* Show resize handle when dashboard is visible */
.resize-handle.visible {
    display: flex;
}'''

content = content.replace(old_resize, new_resize)

# Eliminar min-height y max-height de top-section (se aplicarán desde JS)
content = content.replace('    min-height: 30%;\n', '')
content = content.replace('    max-height: 85%;\n', '')

# Guardar
with open('web_prototype/static/style.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ CSS actualizado para canvas fullscreen por defecto")
print("✅ Resize handle oculto por defecto, se muestra solo cuando se abre dashboard")
