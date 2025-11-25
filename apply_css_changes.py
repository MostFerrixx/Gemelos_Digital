"""
Script para aplicar cambios CSS de forma quirúrgica
Elimina estilos del header y agrega estilos de sidebar
"""
import re

# Leer archivo CSS original
with open('web_prototype/static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Definir los nuevos estilos de sidebar y layout para insertar
sidebar_styles = """/* ============================================
   APP CONTAINER & LAYOUT
   ============================================ */
#app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100%;
}

/* Top Section: Sidebar + Canvas in a row */
#top-section {
    display: flex;
    flex-direction: row;
    flex: 1;
    overflow: hidden;
    transition: flex var(--transition-slow);
}

/* ============================================
   VERTICAL SIDEBAR
   ============================================ */
#vertical-sidebar {
    width: 55px;
    background: var(--glass-bg);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid var(--glass-border);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--spacing-lg) 0;
    box-shadow: var(--shadow-md);
    transition: all var(--transition-slow);
    z-index: 50;
}

.sidebar-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-xl);
    width: 100%;
}

/* Sidebar Logo */
.sidebar-logo {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-accent-blue);
    cursor: pointer;
    transition: all var(--transition-base);
}

.sidebar-logo:hover {
    color: var(--color-accent-blue-hover);
    transform: scale(1.1);
}

.sidebar-logo svg {
    width: 100%;
    height: 100%;
}

/* Sidebar Title */
.sidebar-title {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    user-select: none;
}

/* Sidebar Toggle Button */
.sidebar-toggle-btn {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-base);
    font-size: 1.25rem;
    color: var(--color-text-primary);
}

.sidebar-toggle-btn:hover {
    background: var(--color-surface-hover);
    border-color: var(--color-accent-blue);
    transform: scale(1.05);
    box-shadow: var(--shadow-md);
}

.sidebar-toggle-btn.active {
    background: var(--color-accent-blue);
    border-color: var(--color-accent-blue);
}

/* Sidebar Connection Status */
.sidebar-connection {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-sm);
}

.connection-dot {
    width: 10px;
    height: 10px;
    background: var(--color-accent-green);
    border-radius: 50%;
    box-shadow: 0 0 10px rgba(63, 185, 80, 0.6);
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% {
        opacity: 1;
        transform: scale(1);
    }
    50% {
        opacity: 0.7;
        transform: scale(0.95);
    }
}

"""

# Patrón para encontrar y eliminar todo el bloque del HEADER hasta MAIN LAYOUT
# Busca desde "/* === HEADER ===" hasta "/* === MAIN LAYOUT"
pattern = r'/\* ============================================\s+HEADER\s+============================================ \*/.*?(?=/\* ============================================\s+MAIN LAYOUT)'

# Reemplazar el bloque del header con los nuevos estilos de sidebar
new_content = re.sub(pattern, sidebar_styles, content, flags=re.DOTALL)

# Actualizar también #canvas-section para quitar margin-left y ajustar layout
new_content = new_content.replace(
    'margin: var(--spacing-lg);\n    margin-bottom: 0;',
    'margin: var(--spacing-lg);\n    margin-left: 0;\n    margin-bottom: 0;'
)

# Escribir el archivo modificado
with open('web_prototype/static/style.css', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ CSS actualizado exitosamente")
print(f"Líneas en archivo original: {len(content.splitlines())}")
print(f"Líneas en archivo nuevo: {len(new_content.splitlines())}")
