"""
Script para eliminar border-radius y border del canvas
para que cubra todo el espacio sin gaps visuales
"""

with open('web_prototype/static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Eliminar border-radius del canvas-section
content = content.replace(
    'border-radius: var(--radius-xl);',
    '/* border-radius removed for edge-to-edge layout */'
)

# Cambiar border para que sea solo en los lados (no abajo)
# Primero encontrar la sección de #canvas-section
lines = content.split('\n')
new_lines = []
in_canvas_section = False
border_found = False

for i, line in enumerate(lines):
    if '#canvas-section {' in line:
        in_canvas_section = True
        new_lines.append(line)
    elif in_canvas_section and '}' in line and not '{' in line:
        in_canvas_section = False
        new_lines.append(line)
    elif in_canvas_section and 'border: 1px solid' in line:
        # Reemplazar con border solo arriba y a los lados
        new_lines.append('    border-top: 1px solid var(--color-border);')
        new_lines.append('    border-left: 1px solid var(--color-border);')
        new_lines.append('    border-right: 1px solid var(--color-border);')
        new_lines.append('    /* No border-bottom to connect with footer */')
        border_found = True
    else:
        new_lines.append(line)

content = '\n'.join(new_lines)

# Guardar
with open('web_prototype/static/style.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Border-radius eliminado del canvas")
print("✅ Border inferior del canvas eliminado")
print("   Canvas ahora se conecta perfectamente con el footer")
