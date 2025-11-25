"""
Script final para aplicar todos los cambios de fullscreen canvas
Incluye el fix del bottom-panel flex: 0 cuando está colapsado
"""

import subprocess

# 1. Aplicar cambios base de sidebar y resize
subprocess.run(['python', 'apply_fullscreen_changes.py'], check=True)

# 2. Agregar flex: 0 al .bottom-panel.collapsed
with open('web_prototype/static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Modificar .bottom-panel.collapsed para que no ocupe espacio
old_collapsed = '''.bottom-panel.collapsed {
    transform: translateY(100%);
    opacity: 0;
    pointer-events: none;
}'''

new_collapsed = '''.bottom-panel.collapsed {
    flex: 0; /* Don't take up any space when collapsed */
    transform: translateY(100%);
    opacity: 0;
    pointer-events: none;
}'''

content = content.replace(old_collapsed, new_collapsed)

# Guardar
with open('web_prototype/static/style.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Bottom panel fix aplicado - no ocupa espacio cuando está colapsado")
