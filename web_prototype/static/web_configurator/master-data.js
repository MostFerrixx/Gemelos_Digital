/**
 * Datos maestros: subir el Excel/mapa, aplicarlos y ver que esta usando el motor.
 *
 * Por que existe: el simulador NO lee el Excel, lee `warehouse.db`. Antes, editar
 * el Excel no tenia ningun efecto hasta que alguien corriera la migracion por
 * consola, y la UI no lo avisaba. Los botones "Examinar" tampoco hacian nada.
 *
 * Flujo: subir -> validar (sin aplicar) -> aplicar -> ver.
 * Ver docs/PLAN_DATOS_MAESTROS_WEB.md
 */
class MasterDataManager {
    constructor(configurator) {
        this.configurator = configurator;
        this.excelSubido = null;   // ruta del ultimo Excel subido y validado
        this.tabla = 'locations';
        this.offset = 0;
        this.limit = 25;
        this.total = 0;
        this.busqueda = '';
    }

    init() {
        const $ = (id) => document.getElementById(id);

        // Los botones "Examinar" ahora abren el selector de archivo de verdad.
        $('btn-browse-tmx')?.addEventListener('click', () => $('tmx-file-input').click());
        $('btn-browse-seq')?.addEventListener('click', () => $('excel-file-input').click());

        $('tmx-file-input')?.addEventListener('change', (e) => this.subirTmx(e));
        $('excel-file-input')?.addEventListener('change', (e) => this.subirExcel(e));
        $('btn-apply-master-data')?.addEventListener('click', () => this.aplicar());

        $('master-table-select')?.addEventListener('change', (e) => {
            this.tabla = e.target.value;
            this.offset = 0;
            this.cargarTabla();
        });
        let debounce;
        $('master-table-search')?.addEventListener('input', (e) => {
            clearTimeout(debounce);
            debounce = setTimeout(() => {
                this.busqueda = e.target.value.trim();
                this.offset = 0;
                this.cargarTabla();
            }, 300);
        });
        $('master-page-prev')?.addEventListener('click', () => {
            this.offset = Math.max(0, this.offset - this.limit);
            this.cargarTabla();
        });
        $('master-page-next')?.addEventListener('click', () => {
            if (this.offset + this.limit < this.total) {
                this.offset += this.limit;
                this.cargarTabla();
            }
        });

        // F3: edicion de las tablas chicas (pocas coordenadas).
        $('btn-save-staging-coords')?.addEventListener('click',
            () => this.guardarCoords('staging_areas'));
        $('btn-save-docks-coords')?.addEventListener('click',
            () => this.guardarCoords('inbound_docks'));

        this.cargarResumen();
        this.cargarTabla();
        this.cargarCoords('staging_areas');
        this.cargarCoords('inbound_docks');
    }

    // --- Editar tablas chicas (F3) --------------------------------------

    // Config de cada tabla editable: donde se dibuja, que endpoint la guarda y
    // como se llaman sus columnas de coordenadas en la BD.
    static COORDS = {
        staging_areas: {
            editor: 'staging-coords-editor', resultado: 'staging-coords-result',
            endpoint: '/api/master-data/staging-areas',
            colId: 'staging_id', colX: 'legacy_x', colY: 'legacy_y', etiqueta: 'Zona'
        },
        inbound_docks: {
            editor: 'docks-coords-editor', resultado: 'docks-coords-result',
            endpoint: '/api/master-data/inbound-docks',
            colId: 'dock_id', colX: 'x', colY: 'y', etiqueta: 'Muelle'
        }
    };

    async cargarCoords(tabla) {
        const cfg = MasterDataManager.COORDS[tabla];
        const cont = document.getElementById(cfg.editor);
        if (!cont) return;
        try {
            // BK-25: un carril de descarga puede tener decenas de celdas (20 por
            // carril en WH1 v3): el editor fila-por-fila no sirve y ademas se
            // cortaba en 100. Se pide todo y se resume por zona.
            const r = await fetch('/api/master-data/table/' + tabla + '?limit=1000');
            if (!r.ok) { cont.innerHTML = '<em>Sin datos. Aplicá el Excel maestro primero.</em>'; return; }
            const data = await r.json();
            if (!data.filas.length) { cont.innerHTML = '<em>Sin filas.</em>'; return; }

            // Agrupar por id: si una zona trae varias celdas es un CARRIL, y
            // eso se edita en el Excel maestro, no celda por celda aca.
            const porId = new Map();
            data.filas.forEach(f => {
                const id = f[cfg.colId];
                if (!porId.has(id)) porId.set(id, []);
                porId.get(id).push(f);
            });
            const hayCarriles = [...porId.values()].some(v => v.length > 1);
            if (hayCarriles) {
                cont.innerHTML = '<p class="description-text">Estas zonas son carriles de varias celdas. ' +
                    'Se definen en el Excel maestro (hoja OutboundStaging) y se aplican desde arriba.</p>' +
                    [...porId.entries()].map(([id, celdas]) => {
                        const xs = celdas.map(c => c[cfg.colX]), ys = celdas.map(c => c[cfg.colY]);
                        return `<div class="coord-row"><span class="coord-label">${cfg.etiqueta} ${id}</span>
                            <span>${celdas.length} celdas &middot; columnas ${Math.min(...xs)}-${Math.max(...xs)}
                            &middot; filas ${Math.min(...ys)}-${Math.max(...ys)}</span></div>`;
                    }).join('');
                const boton = document.getElementById('btn-save-staging-coords');
                if (boton && tabla === 'staging_areas') boton.style.display = 'none';
                return;
            }

            cont.innerHTML = data.filas.map(f => `
                <div class="coord-row" data-id="${f[cfg.colId]}">
                    <span class="coord-label">${cfg.etiqueta} ${f[cfg.colId]}</span>
                    <label>X</label>
                    <input type="number" class="coord-x" min="0" value="${f[cfg.colX] ?? 0}">
                    <label>Y</label>
                    <input type="number" class="coord-y" min="0" value="${f[cfg.colY] ?? 0}">
                </div>`).join('');
        } catch (e) {
            cont.innerHTML = '<em>Error al leer: ' + e.message + '</em>';
        }
    }

    async guardarCoords(tabla) {
        const cfg = MasterDataManager.COORDS[tabla];
        const filas = [...document.querySelectorAll('#' + cfg.editor + ' .coord-row')].map(row => ({
            id: parseInt(row.dataset.id, 10),
            x: parseInt(row.querySelector('.coord-x').value, 10),
            y: parseInt(row.querySelector('.coord-y').value, 10)
        }));
        if (filas.some(f => isNaN(f.x) || isNaN(f.y))) {
            this._resultado(cfg.resultado, 'Hay coordenadas vacías o inválidas.', 'error');
            return;
        }
        try {
            const r = await fetch(cfg.endpoint, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filas })
            });
            const data = await r.json();
            if (!r.ok || data.success === false) {
                this._resultado(cfg.resultado,
                    '<strong>No se pudo guardar:</strong> ' + (data.detail || 'error'), 'error');
                return;
            }
            this._resultado(cfg.resultado,
                '<strong>Ubicaciones guardadas</strong> (' + data.actualizadas + ' filas). '
                + 'El simulador las usará en la próxima corrida.', 'ok');
            this.cargarTabla();
        } catch (e) {
            this._resultado(cfg.resultado, 'Error: ' + e.message, 'error');
        }
    }

    _resultado(id, html, tipo) {
        const el = document.getElementById(id);
        if (!el) return;
        el.style.display = '';
        el.className = 'upload-result ' + (tipo || '');
        el.innerHTML = html;
    }

    // --- Subida ---------------------------------------------------------

    async subirExcel(evento) {
        const archivo = evento.target.files[0];
        if (!archivo) return;
        this._resultado('excel-upload-result', 'Validando <strong>' + archivo.name + '</strong>...', '');

        try {
            const fd = new FormData();
            fd.append('file', archivo);
            const r = await fetch('/api/master-data/upload-excel', { method: 'POST', body: fd });
            const data = await r.json();

            if (!data.valido) {
                this.excelSubido = null;
                this._resultado('excel-upload-result',
                    '<strong>El archivo no se puede usar:</strong><ul>'
                    + (data.errores || []).map(e => '<li>' + e + '</li>').join('')
                    + '</ul>', 'error');
                return;
            }

            this.excelSubido = data.excel_path;
            const filas = Object.entries(data.resumen || {})
                .map(([hoja, n]) => '<li>' + hoja + ': <strong>' + n + '</strong></li>').join('');
            this._resultado('excel-upload-result',
                '<strong>Archivo válido.</strong> Contiene:<ul>' + filas + '</ul>'
                + (data.avisos || []).map(a => '<div class="aviso">' + a + '</div>').join('')
                + '<div class="accion-pendiente">Todavía <strong>no se aplicó</strong>. '
                + 'Usá <strong>Aplicar Excel</strong> para que el simulador lo use.</div>',
                'ok');
        } catch (e) {
            this._resultado('excel-upload-result', 'Error al subir: ' + e.message, 'error');
        } finally {
            evento.target.value = '';
        }
    }

    async subirTmx(evento) {
        const archivo = evento.target.files[0];
        if (!archivo) return;
        this._resultado('tmx-upload-result', 'Validando <strong>' + archivo.name + '</strong>...', '');

        try {
            const fd = new FormData();
            fd.append('file', archivo);
            const r = await fetch('/api/master-data/upload-tmx', { method: 'POST', body: fd });
            const data = await r.json();

            if (!data.valido) {
                this._resultado('tmx-upload-result',
                    '<strong>Mapa inválido:</strong> ' + (data.errores || []).join('; '), 'error');
                return;
            }
            const rs = data.resumen || {};
            document.getElementById('layout-file').value = data.tmx_path.replace(/\\/g, '/');
            this._resultado('tmx-upload-result',
                '<strong>Mapa válido:</strong> ' + rs.ancho + ' x ' + rs.alto
                + ' celdas, ' + rs.capas + ' capas.'
                + '<div class="accion-pendiente">La ruta se actualizó arriba. '
                + 'Guardá con <strong>Aplicar Configuración</strong> para usarlo.</div>', 'ok');
        } catch (e) {
            this._resultado('tmx-upload-result', 'Error al subir: ' + e.message, 'error');
        } finally {
            evento.target.value = '';
        }
    }

    // --- Aplicar --------------------------------------------------------

    async aplicar() {
        // El import RECONSTRUYE las tablas: se avisa antes, porque reinicia el
        // stock inicial y pisa lo que se haya editado desde la web.
        const detalle = this.excelSubido
            ? 'el archivo que acabás de subir'
            : 'el Excel configurado arriba';
        const ok = confirm(
            'Se va a aplicar ' + detalle + ' a los datos del simulador.\n\n'
            + 'Esto reconstruye las tablas: el stock inicial vuelve al del Excel y se '
            + 'reemplaza cualquier edición hecha desde la web.\n\n'
            + 'Se hace una copia de seguridad automática antes.\n\n¿Continuar?');
        if (!ok) return;

        this._resultado('master-data-apply-result', 'Aplicando... puede tardar unos segundos.', '');
        try {
            const r = await fetch('/api/master-data/apply', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ excel_path: this.excelSubido || null })
            });
            const data = await r.json();
            if (!data.success) {
                this._resultado('master-data-apply-result',
                    '<strong>No se pudo aplicar:</strong><ul>'
                    + (data.errors || []).map(e => '<li>' + e + '</li>').join('') + '</ul>', 'error');
                return;
            }
            this._resultado('master-data-apply-result',
                '<strong>Datos aplicados.</strong> El simulador ya usa estos datos.'
                + (data.backup ? ' Copia de seguridad: <code>' + data.backup + '</code>' : ''),
                'ok');
            this.excelSubido = null;
            // QA H-41: el aviso de la subida decia "todavia no se aplico".
            const subida = document.getElementById('excel-upload-result');
            if (subida && subida.style.display !== 'none' && subida.innerHTML) {
                this._resultado('excel-upload-result', '<strong>Aplicado.</strong> Este Excel es el que usa el simulador.', 'ok');
            }
            this.cargarResumen();
            this.cargarTabla();
        } catch (e) {
            this._resultado('master-data-apply-result', 'Error: ' + e.message, 'error');
        }
    }

    // --- Ver ------------------------------------------------------------

    async cargarResumen() {
        const cont = document.getElementById('master-data-summary');
        const stale = document.getElementById('master-data-stale');
        if (!cont) return;
        try {
            const data = await (await fetch('/api/master-data/summary')).json();
            if (!data.disponible) {
                cont.innerHTML = '<em>No hay datos cargados todavía. Subí el Excel maestro y aplicalo.</em>';
                return;
            }
            const etiquetas = {
                locations: 'Ubicaciones', sku_catalog: 'Productos',
                staging_areas: 'Zonas de salida', inbound_docks: 'Muelles'
            };
            cont.innerHTML = Object.entries(data.conteos || {}).map(([k, v]) =>
                '<div class="master-stat"><span class="master-stat-num">' + (v ?? '-')
                + '</span><span class="master-stat-lbl">' + (etiquetas[k] || k) + '</span></div>'
            ).join('');

            // El aviso mas importante de la pantalla.
            if (stale) {
                if (data.excel_mas_nuevo) {
                    stale.style.display = '';
                    stale.innerHTML = '<strong>El Excel es más nuevo que los datos en uso.</strong> '
                        + 'Alguien lo editó y todavía no se aplicó, así que el simulador sigue '
                        + 'usando los datos anteriores. Usá <strong>Aplicar Excel</strong>.';
                } else {
                    stale.style.display = 'none';
                }
            }
        } catch (e) {
            cont.innerHTML = '<em>No se pudo leer el estado de los datos maestros.</em>';
        }
    }

    async cargarTabla() {
        const cont = document.getElementById('master-table-container');
        if (!cont) return;
        try {
            const url = '/api/master-data/table/' + this.tabla
                + '?limit=' + this.limit + '&offset=' + this.offset
                + (this.busqueda ? '&q=' + encodeURIComponent(this.busqueda) : '');
            const r = await fetch(url);
            if (!r.ok) { cont.innerHTML = '<em>Sin datos para mostrar.</em>'; return; }
            const data = await r.json();
            this.total = data.total || 0;

            if (!data.filas.length) {
                cont.innerHTML = '<em>Sin resultados.</em>';
            } else {
                // QA H-39: `equipment_required` de la base NO la usa el motor
                // (manda el mapa de equipos de la pestana Flota) y decia
                // GroundOperator hasta en racks altos. Se oculta y, si la tabla
                // tiene area de trabajo, se muestra el equipo que de verdad aplica.
                const EQUIPO = 'equipo (segun Flota)';
                const cols = data.columnas.filter(c => c !== 'equipment_required');
                const mapa = this.configurator?.fleetManager?.getWorkAreaEquipment?.() || {};
                if (cols.includes('work_area')) cols.splice(cols.indexOf('work_area') + 1, 0, EQUIPO);
                const valor = (f, c) => c === EQUIPO ? (mapa[f.work_area] || '-') : (f[c] ?? '');
                cont.innerHTML = '<table class="master-table"><thead><tr>'
                    + cols.map(c => '<th>' + c + '</th>').join('')
                    + '</tr></thead><tbody>'
                    + data.filas.map(f => '<tr>'
                        + cols.map(c => '<td>' + valor(f, c) + '</td>').join('')
                        + '</tr>').join('')
                    + '</tbody></table>';
            }

            const desde = this.total ? this.offset + 1 : 0;
            const hasta = Math.min(this.offset + this.limit, this.total);
            document.getElementById('master-table-info').textContent =
                desde + '-' + hasta + ' de ' + this.total;
            document.getElementById('master-page-prev').disabled = this.offset === 0;
            document.getElementById('master-page-next').disabled =
                this.offset + this.limit >= this.total;
        } catch (e) {
            cont.innerHTML = '<em>Error al leer la tabla: ' + e.message + '</em>';
        }
    }
}
