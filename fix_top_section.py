"""
Script para actualizar SOLO la línea de #top-section en el CSS
"""

# Leer archivo CSS actual
with open('web_prototype/static/style.css', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar y reemplazar la línea de flex en #top-section
in_top_section = False
modified = False

for i, line in enumerate(lines):
    if '#top-section {' in line:
        in_top_section = True
        continue
    
    if in_top_section:
        # Reemplazar flex: 1; por flex: 0 0 65%;
        if 'flex: 1;' in line:
            lines[i] = line.replace('flex: 1;', 'flex: 0 0 65%; /* Changed from flex: 1 to allow resize */')
            modified = True
        # También agregar min-height y max-height si no existen
        elif '}' in line and not any('min-height' in l for l in lines[max(0,i-8):i]):
            # Insertar min/max height antes del cierre
            indent = '    '
            lines.insert(i, f'{indent}min-height: 30%;\n')
            lines.insert(i+1, f'{indent}max-height: 85%;\n')
            lines[i+2] = lines[i+2].replace('transition: flex var(--transition-slow);', 
                                             'transition: flex-basis 0.3s cubic-bezier(0.4, 0, 0.2, 1);')
            modified = True
            in_top_section = False
            break

# Escribir archivo modificado
with open('web_prototype/static/style.css', 'w', encoding='utf-8') as f:
    f.writelines(lines)

if modified:
    print("✅ #top-section actualizado exitosamente con flex: 0 0 65%")
else:
    print("⚠️ No se encontró la línea a modificar. Es posible que ya esté actualizado.")

print(f"Total líneas en archivo: {len(lines)}")
