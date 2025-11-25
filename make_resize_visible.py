"""
Script para hacer el resize handle más visible
Solo modifica la línea de .resize-indicator
"""

# Leer archivo CSS
with open('web_prototype/static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar el estilo del resize-indicator para hacerlo más visible
old_indicator = '''.resize-indicator {
    width: 60px;
    height: 4px;
    background: var(--color-border-strong);
    border-radius: 2px;
    transition: all var(--transition-base);
}'''

new_indicator = '''.resize-indicator {
    width: 100px; /* Increased from 60px for better visibility */
    height: 4px;
    background: rgba(88, 166, 255, 0.4); /* More visible default color */
    border-radius: 2px;
    transition: all var(--transition-base);
    box-shadow: 0 0 8px rgba(88, 166, 255, 0.3); /* Subtle glow for visibility */
}'''

# Hacer el reemplazo
content = content.replace(old_indicator, new_indicator)

# Guardar
with open('web_prototype/static/style.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Resize indicator actualizado para estar siempre visible")
