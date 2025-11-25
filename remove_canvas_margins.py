"""
Script para eliminar los márgenes del canvas-section
Esto hará que el canvas llegue hasta el footer sin espacios
"""

with open('web_prototype/static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar y reemplazar la sección de #canvas-section
old_canvas_margins = '''    margin: var(--spacing-lg);
    margin-left: 0;
    margin-bottom: 0;'''

new_canvas_margins = '''    margin: 0; /* No margins - canvas goes edge to edge */'''

content = content.replace(old_canvas_margins, new_canvas_margins)

# Guardar
with open('web_prototype/static/style.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Márgenes del canvas eliminados")
print("   Canvas ahora llega hasta el footer sin espacios")
