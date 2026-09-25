/**
 * Web Configurator - Main Application
 * Coordinates all modules and handles form management
 */

class WebConfigurator {
    constructor() {
        this.currentConfig = null;
        this.workAreas = [];
        this.init();
    }

    async init() {
        console.log('[WEB_CONFIGURATOR] Initializing...');

        // Disable Run Simulation button during initialization
        const btnRunSim = document.getElementById('btn-run-simulation');
        if (btnRunSim) {
            btnRunSim.disabled = true;
            btnRunSim.style.opacity = '0.5';
            btnRunSim.style.cursor = 'not-allowed';
            btnRunSim.title = 'Waiting for configuration to load...';
        }

        // Initialize modules
        this.fleetManager = new FleetManager(this);
        configStorage = new ConfigurationStorage(this);
        // Datos maestros (Excel/mapa -> warehouse.db). Ver master-data.js.
        this.masterData = (typeof MasterDataManager !== 'undefined')
            ? new MasterDataManager(this) : null;

        // Setup event listeners
        this.setupEventListeners();
        this.setupTabNavigation();
        this.setupValidations();
        this.setupOrderGenerationMode(); // NEW: Setup order mode toggle
        this.setupOptimizationPanel(); // INIT-3 v2: panel de optimizacion Optuna
        this.setupExperimentPanel(); // MEJ-EXP-WEB: comparador A/B

        // Load initial configuration
        await this.loadConfiguration();

        // Datos maestros: despues de cargar el config, porque el resumen usa
        // `sequence_file` para saber que Excel comparar contra la base.
        this.masterData?.init();

        // Re-enable Run Simulation button after configuration is loaded
        if (btnRunSim) {
            btnRunSim.disabled = false;
            btnRunSim.style.opacity = '1';
            btnRunSim.style.cursor = 'pointer';
            btnRunSim.title = 'Run Simulation';
        }

        console.log('[WEB_CONFIGURATOR] Initialization complete');
    }

    setupEventListeners() {
        // Toolbar buttons
        document.getElementById('btn-save').addEventListener('click', () => configStorage.saveAs());
        document.getElementById('btn-load').addEventListener('click', () => configStorage.loadFrom());
        document.getElementById('btn-manage').addEventListener('click', () => configStorage.manage());
        document.getElementById('btn-default').addEventListener('click', () => configStorage.loadDefault());
        document.getElementById('btn-use').addEventListener('click', () => configStorage.useConfiguration());

        // Import functionality
        const fileInput = document.getElementById('file-import-input');
        const importBtn = document.getElementById('btn-import');

        if (importBtn && fileInput) {
            importBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleFileImport(e));
        }

        // Layout & Data buttons
        document.getElementById('btn-load-work-areas').addEventListener('click', () => this.loadWorkAreas());

        // BK-25 capas 2 y 3: zonas y cupo por pasillo.
        ['zonas-enabled', 'cupo-enabled'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => this._updatePasillosVisibility());
        });
        document.getElementById('btn-add-zona')?.addEventListener('click', () => this._addZonaRow());

        // QA H-45: "Abrir Visor" abre la ULTIMA corrida (antes, el visor vacio).
        document.getElementById('btn-open-viewer')?.addEventListener('click', async (e) => {
            e.preventDefault();
            const ventana = window.open('about:blank', '_blank');   // antes del await: no lo bloquea el navegador
            let url = '/';
            try {
                const r = await (await fetch('/api/replays/latest')).json();
                if (r.disponible) url = '/?autoload=' + encodeURIComponent(r.replay);
            } catch (err) { /* sin corridas: visor vacio */ }
            if (ventana) ventana.location.href = url; else window.location.href = url;
        });

        // INIT-6 Opcion B: agregar fila de destino_staging_map
        const addDestinoBtn = document.getElementById('btn-add-destino-staging');
        if (addDestinoBtn) {
            addDestinoBtn.addEventListener('click', () => this._addDestinoStagingRow());
        }

        // C5: Tiempos preset selector
        const tiemposPreset = document.getElementById('tiempos-preset');
        if (tiemposPreset) {
            tiemposPreset.addEventListener('change', (e) => {
                if (e.target.value === 'demo') {
                    document.getElementById('tiempos-time-per-cell').value = 0.1;
                    document.getElementById('tiempos-speed-forklift').value = 0.8;
                    document.getElementById('tiempos-lift').value = 2.0;
                } else if (e.target.value === 'real') {
                    document.getElementById('tiempos-time-per-cell').value = 1.0;
                    document.getElementById('tiempos-speed-forklift').value = 0.5;
                    document.getElementById('tiempos-lift').value = 8.0;
                }
                // 'custom': el usuario edita manualmente, no se sobreescriben los campos
                // Los presets ya NO tocan tiempo_picking_por_linea: ese campo salio
                // de la UI y el tiempo de pick lo define la card "Tiempo de Pick por
                // Producto", que es independiente del perfil de velocidad.
            });
            // Cambio manual de cualquier campo -> muestra "Personalizado"
            ['tiempos-time-per-cell', 'tiempos-speed-forklift',
             'tiempos-lift'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.addEventListener('input', () => { tiemposPreset.value = 'custom'; });
            });
        }

        // BK-01: Listener dispatch-strategy — mostrar/ocultar radio_cercania
        const dispatchSelect = document.getElementById('dispatch-strategy');
        if (dispatchSelect) {
            dispatchSelect.addEventListener('change', () => this._updateRadioCercaniaVisibility());
        }

        // Outbound: Listener toggle-outbound — mostrar/ocultar truck_interval
        const outboundToggle = document.getElementById('toggle-outbound');
        if (outboundToggle) {
            outboundToggle.addEventListener('change', () => this._updateOutboundVisibility());
        }

        // INIT-7 F3: listeners del tab Inbound (toggle + modo de llegadas)
        const inboundToggle = document.getElementById('toggle-inbound');
        if (inboundToggle) {
            inboundToggle.addEventListener('change', () => this._updateInboundVisibility());
        }
        const inboundMode = document.getElementById('inbound-arrival-mode');
        if (inboundMode) {
            inboundMode.addEventListener('change', () => this._updateInboundVisibility());
        }
        // AUDIT menores 2026-07-10: aviso si cross-dock esta activo con
        // pedidos Estocasticos (el motor lo desactivaria en silencio de cara
        // a la UI; ahora se ve el porque sin ir a la consola).
        const xdToggleEl = document.getElementById('inbound-cross-dock');
        if (xdToggleEl) {
            xdToggleEl.addEventListener('change', () => this._updateCrossDockWarning());
        }
        document.querySelectorAll('input[name="order-generation-mode"]').forEach(radio => {
            radio.addEventListener('change', () => this._updateCrossDockWarning());
        });

        // INIT-8 UI: grid de clases de manejo + toggles de F3/F4.
        this._renderClasesManejoGrid();
        const vcTog = document.getElementById('vc-enabled');
        if (vcTog) vcTog.addEventListener('change', () => this._updateTiemposInit8Visibility());
        const varTog = document.getElementById('var-enabled');
        if (varTog) varTog.addEventListener('change', () => this._updateTiemposInit8Visibility());
    }

    // AUDIT menores 2026-07-10: cross-dock requiere pedidos Deterministas.
    _updateCrossDockWarning() {
        const warn = document.getElementById('inbound-crossdock-warn');
        const xd = document.getElementById('inbound-cross-dock');
        if (!warn || !xd) return;
        const mode = document.querySelector('input[name="order-generation-mode"]:checked')?.value;
        warn.style.display = (xd.checked && mode === 'stochastic') ? 'block' : 'none';
    }

    // BK-01: muestra/oculta el campo radio_cercania segun estrategia seleccionada
    _updateRadioCercaniaVisibility() {
        const sel = document.getElementById('dispatch-strategy');
        const group = document.getElementById('radio-cercania-group');
        if (!sel || !group) return;
        group.style.display = sel.value === 'Cercania' ? 'block' : 'none';
    }

    // Outbound: muestra/oculta el campo truck_interval segun el toggle outbound
    _updateOutboundVisibility() {
        const tog = document.getElementById('toggle-outbound');
        const group = document.getElementById('truck-interval-group');
        const capGroup = document.getElementById('truck-capacity-group');
        if (!tog || !group) return;
        group.style.display = tog.checked ? 'block' : 'none';
        if (capGroup) capGroup.style.display = tog.checked ? 'block' : 'none';
    }

    // INIT-7 F3: muestra/oculta las opciones inbound segun toggle y modo.
    _updateInboundVisibility() {
        const tog = document.getElementById('toggle-inbound');
        const opts = document.getElementById('inbound-options');
        const slotCard = document.getElementById('inbound-slotting-card');
        if (!tog || !opts) return;
        opts.style.display = tog.checked ? 'block' : 'none';
        if (slotCard) slotCard.style.display = tog.checked ? 'block' : 'none';
        const mode = document.getElementById('inbound-arrival-mode')?.value || 'deterministic';
        const asnGroup = document.getElementById('inbound-asn-group');
        const stochGroup = document.getElementById('inbound-stochastic-group');
        if (asnGroup) asnGroup.style.display = mode === 'deterministic' ? 'block' : 'none';
        if (stochGroup) stochGroup.style.display = mode === 'stochastic' ? 'block' : 'none';
        // AUDIT menores: recalcular el aviso de cross-dock (tambien al cargar).
        this._updateCrossDockWarning();
    }

    // INIT-6 Opcion B: editor de destino_staging_map (destino -> staging_id).
    _renderDestinoStagingRows(map) {
        const container = document.getElementById('destino-staging-list');
        if (!container) return;
        container.innerHTML = '';
        const entries = Object.entries(map || {});
        if (entries.length === 0) {
            this._addDestinoStagingRow();
        } else {
            entries.forEach(([destino, stagingId]) => this._addDestinoStagingRow(destino, stagingId));
        }
    }

    _addDestinoStagingRow(destino = '', stagingId = '') {
        const container = document.getElementById('destino-staging-list');
        if (!container) return;
        const row = document.createElement('div');
        row.className = 'destino-staging-row';
        row.innerHTML = `
            <input type="text" class="destino-staging-name" placeholder="Ej: TIENDA_NORTE">
            <input type="number" class="destino-staging-zone" min="1" max="7" placeholder="Zona (1-7)">
            <button class="btn-remove-priority" title="Quitar">✕</button>
        `;
        row.querySelector('.destino-staging-name').value = destino;
        row.querySelector('.destino-staging-zone').value = stagingId;
        row.querySelector('.btn-remove-priority').addEventListener('click', () => row.remove());
        container.appendChild(row);
    }

    // BK-25 capas 2 y 3: zonas de picking y cupo por pasillo.
    _updatePasillosVisibility() {
        [['zonas-enabled', 'zonas-options'], ['cupo-enabled', 'cupo-options']].forEach(([t, o]) => {
            const tog = document.getElementById(t), opts = document.getElementById(o);
            if (tog && opts) opts.style.display = tog.checked ? 'block' : 'none';
        });
    }

    // "1-3, 5" -> [1, 2, 3, 5]; null si el texto no se entiende.
    static parsePasillos(texto) {
        const out = [];
        for (const parte of String(texto).split(',').map(p => p.trim()).filter(Boolean)) {
            const m = parte.match(/^(\d+)(?:\s*-\s*(\d+))?$/);
            if (!m) return null;
            const desde = parseInt(m[1], 10), hasta = m[2] ? parseInt(m[2], 10) : desde;
            if (desde < 1 || hasta < desde) return null;
            for (let n = desde; n <= hasta; n++) if (!out.includes(n)) out.push(n);
        }
        return out.length ? out : null;
    }

    static textoPasillos(lista) {
        const nums = [...new Set((lista || []).map(Number))].sort((a, b) => a - b);
        const tramos = [];
        for (const n of nums) {
            const ult = tramos[tramos.length - 1];
            if (ult && n === ult[1] + 1) ult[1] = n; else tramos.push([n, n]);
        }
        return tramos.map(([a, b]) => a === b ? String(a) : a + '-' + b).join(', ');
    }

    _addZonaRow(quien = '', pasillos = '') {
        const cont = document.getElementById('zonas-list');
        if (!cont) return;
        const row = document.createElement('div');
        row.className = 'destino-staging-row zona-row';
        row.innerHTML = `
            <input type="text" class="zona-quien" placeholder="Ej: GroundOp-01 o Forklift">
            <input type="text" class="zona-pasillos" placeholder="Ej: 1-3, 5">
            <button class="btn-remove-priority" title="Quitar">&#10005;</button>`;
        row.querySelector('.zona-quien').value = quien;
        row.querySelector('.zona-pasillos').value = pasillos;
        row.querySelector('.btn-remove-priority').addEventListener('click', () => row.remove());
        cont.appendChild(row);
    }

    _renderPasillos(config) {
        const zp = config.zonas_picking || {};
        const zt = document.getElementById('zonas-enabled');
        if (zt) zt.checked = zp.enabled === true;
        const robo = document.getElementById('zonas-robo');
        if (robo) robo.checked = zp.robo_de_trabajo !== false;
        const cont = document.getElementById('zonas-list');
        if (cont) {
            cont.innerHTML = '';
            Object.entries(zp.asignacion || {}).forEach(([quien, lista]) =>
                this._addZonaRow(quien, WebConfigurator.textoPasillos(lista)));
        }
        const cp = config.pasillos || {};
        const ct = document.getElementById('cupo-enabled');
        if (ct) ct.checked = cp.enabled === true;
        const cap = document.getElementById('cupo-capacidad');
        if (cap) cap.value = cp.capacidad_default != null ? cp.capacidad_default : 0;
        this._updatePasillosVisibility();
    }

    // Se emiten solo si estan encendidos o ya existian en el config de origen
    // (el canonico sin estos bloques queda byte-identico).
    _serializePasillos(config) {
        const origen = this.currentConfig || {};
        const zonasOn = document.getElementById('zonas-enabled')?.checked === true;
        if (zonasOn || origen.zonas_picking) {
            const asignacion = {};
            document.querySelectorAll('#zonas-list .zona-row').forEach(row => {
                const quien = row.querySelector('.zona-quien').value.trim();
                const texto = row.querySelector('.zona-pasillos').value.trim();
                if (!quien) return;
                // Texto que no se entiende: viaja tal cual y el servidor
                // bloquea la corrida diciendo cual es (nada se descarta en silencio).
                asignacion[quien] = WebConfigurator.parsePasillos(texto) || texto;
            });
            config.zonas_picking = Object.assign({}, origen.zonas_picking || {}, {
                enabled: zonasOn,
                robo_de_trabajo: document.getElementById('zonas-robo')?.checked !== false,
                asignacion
            });
        }
        const cupoOn = document.getElementById('cupo-enabled')?.checked === true;
        if (cupoOn || origen.pasillos) {
            config.pasillos = Object.assign({}, origen.pasillos || {}, {
                enabled: cupoOn,
                capacidad_default: WebConfigurator.numero('cupo-capacidad', 0)
            });
        }
    }

    _serializeDestinoStagingRows() {
        const container = document.getElementById('destino-staging-list');
        const map = {};
        if (!container) return map;
        container.querySelectorAll('.destino-staging-row').forEach(row => {
            const name = row.querySelector('.destino-staging-name').value.trim();
            const raw = row.querySelector('.destino-staging-zone').value.trim();
            const zone = parseInt(raw, 10);
            // QA-7.4: una fila con destino y zona invalida ya no se descarta en
            // silencio (sus pedidos caian al reparto sin aviso): viaja tal cual
            // y la validacion del servidor bloquea la corrida diciendo cual es.
            if (name) {
                map[name] = (String(zone) === raw) ? zone : raw;
            }
        });
        return map;
    }

    // C5: determina si los valores actuales coinciden con un preset conocido.
    // El perfil se reconoce por los 3 campos VISIBLES (celda, factor montacargas,
    // horquilla). `tiempo_picking_por_linea` ya no participa: salio de la UI y no
    // tiene efecto cuando la formula de pick tiene base (el caso normal).
    _updateTiemposPreset(tpc, sfk, lift) {
        const sel = document.getElementById('tiempos-preset');
        if (!sel) return;
        const isDemo = Math.abs(tpc - 0.1) < 0.001 && Math.abs(sfk - 0.8) < 0.001
                       && Math.abs(lift - 2.0) < 0.001;
        const isReal = Math.abs(tpc - 1.0) < 0.001 && Math.abs(sfk - 0.5) < 0.001
                       && Math.abs(lift - 8.0) < 0.001;
        sel.value = isDemo ? 'demo' : (isReal ? 'real' : 'custom');
    }

    async handleFileImport(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            this.showLoading('Leyendo archivo...');

            const reader = new FileReader();

            reader.onload = async (e) => {
                try {
                    const content = e.target.result;
                    const config = JSON.parse(content);

                    // Handle both direct config object and preset format (wrapped in 'configuration')
                    const configToLoad = config.configuration || config;

                    // If config has sequence_file, try to load work areas first
                    if (configToLoad.sequence_file) {
                        try {
                            const response = await fetch(`/api/configurator/work-areas?sequence_file=${encodeURIComponent(configToLoad.sequence_file)}`);
                            const result = await response.json();

                            if (result.success) {
                                this.workAreas = result.work_areas;
                                this.fleetManager.setWorkAreas(this.workAreas);
                                console.log('[IMPORT] Work areas loaded:', this.workAreas);
                            }
                        } catch (waError) {
                            console.warn('[IMPORT] Could not load work areas:', waError);
                            // Continue anyway - work areas might be set manually later
                        }
                    }

                    // Now load the configuration to form
                    this.loadConfigToForm(configToLoad);
                    this.hideLoading();
                    this.showNotification(`✓ Configuración importada desde ${file.name}`, 'success');

                    // Reset input so same file can be selected again
                    event.target.value = '';

                } catch (parseError) {
                    this.hideLoading();
                    console.error('JSON Parse Error:', parseError);
                    this.showNotification('Error: El archivo no es un JSON válido', 'error');
                }
            };

            reader.onerror = () => {
                this.hideLoading();
                this.showNotification('Error al leer el archivo', 'error');
            };

            reader.readAsText(file);

        } catch (error) {
            this.hideLoading();
            console.error('Import Error:', error);
            this.showNotification('Error inesperado al importar', 'error');
        }
    }

    setupTabNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        const tabContents = document.querySelectorAll('.tab-content');

        // Tab metadata for header updates
        const tabInfo = {
            'carga': { title: 'Carga de Trabajo', subtitle: 'Configure el volumen y distribución de órdenes' },
            'estrategias': { title: 'Estrategias', subtitle: 'Defina la lógica de despacho y tipos de tours' },
            'flota': { title: 'Flota de Agentes', subtitle: 'Gestione grupos de operarios y montacargas' },
            'layout-datos': { title: 'Layout y Datos', subtitle: 'Mapa, Excel maestro y datos en uso' },
            'staging': { title: 'Outbound Staging', subtitle: 'Distribución de salida por zonas' },
            // Faltaba: al entrar a Inbound quedaba el titulo de la pestana anterior.
            'inbound': { title: 'Inbound', subtitle: 'Recepción de camiones, putaway y slotting' },
            'optimizacion': { title: 'Optimización', subtitle: 'Estudio Optuna: ajuste automático de flota y estrategia' },
            'experimentos': { title: 'Experimentos A/B', subtitle: 'Compara dos configuraciones con rigor estadístico' }
        };

        navItems.forEach(button => {
            button.addEventListener('click', () => {
                // Remove active class from all
                navItems.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));

                // Add active to clicked
                button.classList.add('active');
                const tabId = button.dataset.tab;

                // Show content
                const tabContent = document.getElementById(`tab-${tabId}`);
                if (tabContent) {
                    tabContent.classList.add('active');
                }

                // Update Header
                const info = tabInfo[tabId];
                if (info) {
                    document.getElementById('current-tab-title').textContent = info.title;
                    document.getElementById('current-tab-subtitle').textContent = info.subtitle;
                }
            });
        });
    }

    // AUD8-2: las claves de distribucion_tipos son CLASES DE MANEJO reales
    // (hoja SkuCatalog / INIT-8). [claveConfig, idInput, defaultPct]
    // H-07 (QA 2026-09-18): lee un numero del formulario y usa el valor por
    // defecto SOLO si el campo esta vacio o no es un numero. El patron previo
    // `parseInt(v) || defecto` trataba el 0 como "vacio": un 0% en una clase
    // se enviaba como el porcentaje por defecto (el formulario decia "Suma
    // 100%" y el servidor rechazaba "164%"), y "0 expansiones" pasaba a 5.
    static numero(id, defecto, entero = false) {
        const raw = document.getElementById(id)?.value;
        if (raw === undefined || raw === null || String(raw).trim() === '') return defecto;
        const v = entero ? parseInt(raw, 10) : parseFloat(raw);
        return isNaN(v) ? defecto : v;
    }

    static CLASES_DISTRIBUCION = [
        ['pequeno', 'pct-pequeno', 36],
        ['mediano', 'pct-mediano', 30],
        ['voluminoso', 'pct-voluminoso', 16],
        ['pesado', 'pct-pesado', 12],
        ['extra_grande', 'pct-extra-grande', 6],
    ];

    // INIT-8 UI: clases de manejo del grid de tiempos.
    // [claveConfig, idBase, etiqueta, defaults {mult, recargo, pack}]
    static CLASES_MANEJO_UI = [
        ['pequeno', 'cm-pequeno', 'Pequeño', { mult: 0.8, recargo: 0, pack: 0 }],
        ['mediano', 'cm-mediano', 'Mediano', { mult: 1, recargo: 0, pack: 0 }],
        ['voluminoso', 'cm-voluminoso', 'Voluminoso', { mult: 1.3, recargo: 3, pack: 0 }],
        ['pesado', 'cm-pesado', 'Pesado', { mult: 1.5, recargo: 5, pack: 0 }],
        ['extra_grande', 'cm-extra-grande', 'Extra grande', { mult: 2.2, recargo: 15, pack: 0 }],
        ['GENERAL', 'cm-general', 'GENERAL (sin clase)', { mult: 1, recargo: 0, pack: 0 }],
    ];

    // INIT-8 UI: filas del grid de clases de manejo (mult / recargo / pack).
    _renderClasesManejoGrid() {
        const grid = document.getElementById('clases-manejo-grid');
        if (!grid) return;
        grid.innerHTML = WebConfigurator.CLASES_MANEJO_UI.map(([, idBase, etiqueta, d]) => `
            <div class="dist-item">
                <h4>${etiqueta}</h4>
                <div class="form-group">
                    <label>Mult. de tiempo</label>
                    <input type="number" id="${idBase}-mult" min="0.1" step="0.1" value="${d.mult}">
                </div>
                <div class="form-group">
                    <label>Recargo (s)</label>
                    <input type="number" id="${idBase}-recargo" min="0" step="0.5" value="${d.recargo}">
                </div>
                <div class="form-group">
                    <label>Pack (s)</label>
                    <input type="number" id="${idBase}-pack" min="0" step="0.5" value="${d.pack}">
                </div>
            </div>`).join('');
    }

    // BK-05: materializa la flota legacy (contadores) como grupos visibles.
    // La resolucion la hace el BACKEND con la misma funcion que usa el motor
    // (core.fleet.resolver_flota); aca no se duplica la logica ni las
    // capacidades por defecto.
    async _materializeLegacyFleet(config) {
        const nGround = parseInt(config.num_operarios_terrestres, 10) || 0;
        const nFork = parseInt(config.num_montacargas, 10) || 0;

        if (nGround + nFork <= 0) {
            // Flota realmente vacia: no hay nada que materializar. El panel de
            // cobertura ya avisa que hay que crear agentes.
            this.fleetManager.clearAllGroups();
            this._setFleetDerivedNotice(false);
            return;
        }

        try {
            const response = await fetch('/api/configurator/resolve-fleet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: config })
            });
            const result = await response.json();

            if (result.success && Array.isArray(result.agent_types) && result.agent_types.length) {
                this.fleetManager.loadFleet(result.agent_types);
                this._setFleetDerivedNotice(true, nGround, nFork);
                return;
            }
            console.warn('[BK-05] resolve-fleet no devolvio agentes:', result);
        } catch (e) {
            console.error('[BK-05] No se pudo resolver la flota legacy:', e);
        }
        this._setFleetDerivedNotice(false);
    }

    // INIT-11 F1: flota definida por personas + equipos (resuelta en el backend).
    async _materializePersonasFleet(config) {
        try {
            const response = await fetch('/api/configurator/resolve-fleet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: config })
            });
            const result = await response.json();
            if (result.success && Array.isArray(result.agent_types)) {
                this.fleetManager.loadFleet(result.agent_types);
            }
        } catch (e) {
            console.error('[INIT-11] No se pudo resolver la flota de personas:', e);
        }
        this._setFleetDerivedNotice('personas', config.personas.length,
            Object.keys(config.equipos || {}).length,
            Object.keys(config.perfiles || {}).length,
            Object.keys(config.estacionamientos || {}).length);
    }

    // BK-05: aviso visible de que la flota se derivo de los contadores legacy.
    // INIT-11 F1: derived === 'personas' -> la flota sale de personas + equipos.
    _setFleetDerivedNotice(derived, nGround, nFork, nPerfiles, nEstacionamientos) {
        const panel = document.getElementById('fleet-derived-notice');
        if (!panel) return;
        if (derived === 'personas') {
            panel.style.display = '';
            panel.innerHTML =
                '<strong>Flota definida por personas y equipos.</strong> '
                + 'Esta configuracion define <code>' + nGround + '</code> grupos de '
                + 'personas y <code>' + nFork + '</code> equipos, y esa definicion '
                + 'es la que usa el motor. Los grupos de abajo la muestran, pero '
                + '<strong>editarlos aqui no tiene efecto</strong>: la edicion de '
                + 'personas y equipos se agrega en una proxima version.'
                + (nPerfiles ? ' Ademas usa <code>' + nPerfiles + '</code> perfiles '
                    + 'de trabajo y <code>' + nEstacionamientos + '</code> '
                    + 'estacionamientos de equipos.' : '');
            return;
        }
        if (!derived) {
            panel.style.display = 'none';
            panel.innerHTML = '';
            return;
        }
        panel.style.display = '';
        panel.innerHTML =
            '<strong>Flota derivada de la configuracion legacy.</strong> '
            + 'Esta configuracion no listaba los agentes uno por uno: los grupos '
            + 'de abajo se reconstruyeron desde los contadores '
            + '(<code>' + nGround + '</code> operarios terrestres, <code>'
            + nFork + '</code> montacargas) usando las mismas capacidades que '
            + 'aplica el motor. Podes editarlos normalmente; al guardar quedaran '
            + 'escritos de forma explicita.';
    }

    // INIT-8 UI: visibilidad de los bloques opt-in (F3/F4).
    _updateTiemposInit8Visibility() {
        const vc = document.getElementById('vc-enabled');
        const vcOpts = document.getElementById('vc-options');
        if (vc && vcOpts) vcOpts.style.display = vc.checked ? 'block' : 'none';
        const va = document.getElementById('var-enabled');
        const vaOpts = document.getElementById('var-options');
        if (va && vaOpts) vaOpts.style.display = va.checked ? 'block' : 'none';
    }

    setupValidations() {
        // Percentages validation for Carga de Trabajo (AUD8-2: 5 clases)
        WebConfigurator.CLASES_DISTRIBUCION.forEach(([, id]) => {
            const input = document.getElementById(id);
            if (input) {
                input.addEventListener('input', () => this.validatePercentages());
            }
        });

        // Staging distribution validation
        for (let i = 1; i <= 7; i++) {
            const input = document.getElementById(`staging-${i}`);
            if (input) {
                input.addEventListener('input', () => this.validateStagingDistribution());
            }
        }
    }

    validatePercentages() {
        // AUD8-2: suma sobre las 5 clases de manejo
        const total = WebConfigurator.CLASES_DISTRIBUCION.reduce((acc, [, id]) => {
            return acc + (parseInt(document.getElementById(id)?.value) || 0);
        }, 0);

        const label = document.getElementById('validation-percentages');
        if (total === 100) {
            label.textContent = '✓ OK: Suma 100%';
            label.className = 'validation-message valid';
        } else {
            label.textContent = `✗ ERROR: Suma ${total}% (debe ser 100%)`;
            label.className = 'validation-message invalid';
        }

        return total === 100;
    }

    validateStagingDistribution() {
        let total = 0;
        for (let i = 1; i <= 7; i++) {
            const value = parseInt(document.getElementById(`staging-${i}`).value) || 0;
            total += value;
        }

        const label = document.getElementById('validation-staging');
        if (total === 100) {
            label.textContent = '✓ OK: Suma 100%';
            label.className = 'validation-message valid';
        } else {
            label.textContent = `✗ ERROR: Suma ${total}% (debe ser 100%)`;
            label.className = 'validation-message invalid';
        }

        return total === 100;
    }

    /**
     * Setup Order Generation Mode toggle and file upload handlers
     * Implements dynamic UI for stochastic vs deterministic mode selection
     */
    setupOrderGenerationMode() {
        // Mode toggle radios
        const modeRadios = document.querySelectorAll('input[name="order-generation-mode"]');
        const stochasticOptions = document.getElementById('stochastic-options');
        const deterministicOptions = document.getElementById('deterministic-options');
        const modeBadge = document.getElementById('order-mode-badge');
        const policySelect = document.getElementById('fulfillment-policy');

        // Initialize state
        this.uploadedOrderFilePath = '';

        // Mode toggle handler
        modeRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                const mode = document.querySelector('input[name="order-generation-mode"]:checked').value;

                if (mode === 'deterministic') {
                    // Show deterministic options, hide stochastic
                    if (stochasticOptions) stochasticOptions.classList.add('hidden');
                    if (deterministicOptions) deterministicOptions.classList.remove('hidden');
                    if (modeBadge) {
                        modeBadge.textContent = 'Determinista';
                        modeBadge.className = 'badge badge-success';
                    }
                    // Enable policy selector
                    if (policySelect) policySelect.disabled = false;
                } else {
                    // Show stochastic options, hide deterministic
                    if (stochasticOptions) stochasticOptions.classList.remove('hidden');
                    if (deterministicOptions) deterministicOptions.classList.add('hidden');
                    if (modeBadge) {
                        modeBadge.textContent = 'Estocástico';
                        modeBadge.className = 'badge badge-info';
                    }
                    // Disable policy selector
                    if (policySelect) policySelect.disabled = true;
                }
            });
        });

        // File dropzone setup
        const dropzone = document.getElementById('orders-dropzone');
        const fileInput = document.getElementById('orders-file-input');

        if (dropzone && fileInput) {
            // Click to upload
            dropzone.addEventListener('click', () => fileInput.click());

            // Drag and drop events
            dropzone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropzone.classList.add('drag-over');
            });

            dropzone.addEventListener('dragleave', () => {
                dropzone.classList.remove('drag-over');
            });

            dropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropzone.classList.remove('drag-over');

                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleOrderFileUpload(files[0]);
                }
            });

            // File input change
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleOrderFileUpload(e.target.files[0]);
                }
            });
        }
    }

    /**
     * INIT-3 v2: panel de optimizacion Optuna (start/status/stop via
     * /api/optimization/*). El estudio corre en background en el servidor;
     * este panel solo lanza y consulta por polling, no bloquea la pestaña.
     */
    // QA-11: tabla de trials. Lo pedido y lo que REALMENTE se simulo, lado a
    // lado: si difieren (como en H-47) la fila se marca en rojo.
    _pintarTablaTrials(status) {
        const cont = document.getElementById('opt-trials-tabla');
        if (!cont) return;
        const trials = status.trials || [];
        if (!trials.length) { cont.innerHTML = ''; return; }
        const estados = { COMPLETE: 'Listo', RUNNING: 'Corriendo', FAIL: 'Falló o cortado',
                          CORTADO: 'Cortado', PRUNED: 'Cortado', WAITING: 'En cola' };
        const num = (v, d = 0) => (v === null || v === undefined) ? '-' : Number(v).toLocaleString('es-AR', { maximumFractionDigits: d });
        const filas = trials.map(t => {
            const p = t.params || {}, s = t.flota_simulada;
            const pedida = (p.num_operarios_terrestres ?? '-') + ' + ' + (p.num_montacargas ?? '-');
            const simulada = s ? s.terrestres + ' + ' + s.montacargas : '-';
            const distinta = s && (s.terrestres !== p.num_operarios_terrestres || s.montacargas !== p.num_montacargas);
            const mejor = t.numero === status.best_trial_number;
            const estilo = distinta ? ' style="color: var(--color-danger); font-weight:600;"'
                         : mejor ? ' style="font-weight:600;"' : '';
            return `<tr${estilo}><td>${t.numero}${mejor ? ' ★' : ''}</td><td>${estados[t.estado] || t.estado}</td>
                <td>${pedida}</td><td>${simulada}${distinta ? ' ⚠' : ''}</td><td>${p.dispatch_strategy || '-'}</td>
                <td>${p.max_wos_por_tour ?? '-'}</td><td>${num(t.tareas_por_hora, 1)}</td>
                <td>${num(t.costo_por_hora)}</td><td>${t.puntaje == null ? '-' : Number(t.puntaje).toFixed(4)}</td></tr>`;
        }).join('');
        cont.innerHTML = `<table class="master-table"><thead><tr>
            <th>Trial</th><th>Estado</th><th title="Terrestres + montacargas que pidió el optimizador">Flota pedida</th>
            <th title="Terrestres + montacargas que corrieron de verdad">Flota simulada</th><th>Estrategia</th>
            <th>Tope tareas</th><th>Tareas/hora</th><th>Costo/hora</th><th>Puntaje</th></tr></thead>
            <tbody>${filas}</tbody></table>`;
    }

    setupOptimizationPanel() {
        const btnStart = document.getElementById('btn-optimization-start');
        const btnStop = document.getElementById('btn-optimization-stop');
        const badge = document.getElementById('optimization-status-badge');
        const progressBox = document.getElementById('optimization-progress');
        const studyNameEl = document.getElementById('opt-study-name');
        const progressTextEl = document.getElementById('opt-progress-text');
        const bestScoreEl = document.getElementById('opt-best-score');
        const bestParamsEl = document.getElementById('opt-best-params');

        if (!btnStart || !btnStop) return; // tab no presente (defensivo)

        // QA-11.2: Optuna (TPE) sortea los primeros 10 trials; el 1ro es la
        // flota actual. Con menos, "optimizar" es un sorteo: se avisa.
        const trialsEl = document.getElementById('opt-n-trials');
        const avisoTrials = document.getElementById('opt-trials-aviso');
        const pintarAvisoTrials = () => {
            if (trialsEl && avisoTrials) avisoTrials.style.display =
                (parseInt(trialsEl.value, 10) || 0) < 11 ? 'block' : 'none';
        };
        trialsEl?.addEventListener('input', pintarAvisoTrials);
        pintarAvisoTrials();

        let pollHandle = null;
        let activeStudyName = null;

        const setBadge = (text, cls) => {
            badge.textContent = text;
            badge.className = `badge ${cls}`;
        };

        const renderStatus = (status) => {
            progressBox.classList.remove('hidden');
            studyNameEl.textContent = status.study_name || '-';
            progressTextEl.textContent =
                `${status.n_trials_completed || 0} / ${status.n_trials_total || 0} trials`;
            this._pintarTablaTrials(status);
            if (status.best_score !== undefined && status.best_score !== null) {
                bestScoreEl.textContent = Number(status.best_score).toFixed(4);
                bestParamsEl.textContent = JSON.stringify(status.best_params, null, 2);
            } else {
                bestScoreEl.textContent = 'Aun sin trials completados...';
                bestParamsEl.textContent = '';
            }
        };

        const stopPolling = () => {
            if (pollHandle) {
                clearInterval(pollHandle);
                pollHandle = null;
            }
        };

        const pollStatus = async () => {
            if (!activeStudyName) return;
            try {
                const resp = await fetch(`/api/optimization/status?study_name=${encodeURIComponent(activeStudyName)}`);
                const status = await resp.json();
                renderStatus(status);
                if (status.running) {
                    setBadge('Corriendo...', 'badge-warning');
                    btnStart.disabled = true;
                    btnStop.disabled = false;
                } else {
                    setBadge('Finalizado', 'badge-success');
                    btnStart.disabled = false;
                    btnStop.disabled = true;
                    stopPolling();
                }
            } catch (err) {
                console.error('[OPTIMIZATION] Error consultando estado:', err);
            }
        };

        btnStart.addEventListener('click', async () => {
            const body = {
                n_trials: WebConfigurator.numero('opt-n-trials', 20, true),
                n_jobs: WebConfigurator.numero('opt-n-jobs', 2, true),
                cost_ground: WebConfigurator.numero('opt-cost-ground', 15.0),
                cost_forklift: WebConfigurator.numero('opt-cost-forklift', 50.0),
                penalty_failed: WebConfigurator.numero('opt-penalty-failed', 100.0),
                // MEJ-SLA-OPT: $ por pedido con SLA vencido. NO usar || como los
                // demas: 0 es un valor valido (desactiva la penalizacion a proposito).
                penalty_late: (() => {
                    const v = parseFloat(document.getElementById('opt-penalty-late')?.value);
                    return Number.isNaN(v) ? 50.0 : v;
                })(),
            };
            try {
                const resp = await fetch('/api/optimization/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (!resp.ok) {
                    const err = await resp.json();
                    this.showNotification(`Error: ${err.detail || 'no se pudo iniciar'}`, 'error');
                    return;
                }
                const data = await resp.json();
                activeStudyName = data.study_name;
                this.showNotification(`Optimizacion iniciada: ${data.study_name}`, 'success');
                setBadge('Corriendo...', 'badge-warning');
                btnStart.disabled = true;
                btnStop.disabled = false;
                stopPolling();
                pollHandle = setInterval(pollStatus, 3000);
                pollStatus();
            } catch (err) {
                this.showNotification(`Error inesperado: ${err.message}`, 'error');
            }
        });

        btnStop.addEventListener('click', async () => {
            try {
                const resp = await fetch('/api/optimization/stop', { method: 'POST' });
                if (!resp.ok) {
                    const err = await resp.json();
                    this.showNotification(`Error: ${err.detail || 'no se pudo detener'}`, 'error');
                    return;
                }
                this.showNotification('Optimizacion detenida', 'success');
                setBadge('Detenido', 'badge-neutral');
                btnStart.disabled = false;
                btnStop.disabled = true;
                stopPolling();
                // QA H-49: un ultimo estado para que la tabla muestre los
                // trials cortados (antes quedaba la foto del ultimo sondeo).
                if (activeStudyName) {
                    try {
                        const r = await fetch(`/api/optimization/status?study_name=${encodeURIComponent(activeStudyName)}`);
                        renderStatus(await r.json());
                    } catch (e) { /* la tabla queda como estaba */ }
                }
            } catch (err) {
                this.showNotification(`Error inesperado: ${err.message}`, 'error');
            }
        });

        // Si ya habia un estudio corriendo (servidor no reiniciado desde que
        // se lanzo), retomar el polling en vez de mostrar "Inactivo".
        (async () => {
            try {
                const resp = await fetch('/api/optimization/status');
                const status = await resp.json();
                if (status.running && status.study_name) {
                    activeStudyName = status.study_name;
                    renderStatus(status);
                    setBadge('Corriendo...', 'badge-warning');
                    btnStart.disabled = true;
                    btnStop.disabled = false;
                    pollHandle = setInterval(pollStatus, 3000);
                }
            } catch (err) {
                console.error('[OPTIMIZATION] Error consultando estado inicial:', err);
            }
        })();
    }

    /**
     * MEJ-EXP-WEB: comparador A/B (start/status/stop via /api/experiment/*).
     * Mismo patron que el panel de optimizacion: subprocess en el servidor,
     * polling cada 3s, retoma un experimento en curso si se recarga la pagina.
     */
    setupExperimentPanel() {
        const btnStart = document.getElementById('btn-experiment-start');
        const btnStop = document.getElementById('btn-experiment-stop');
        const badge = document.getElementById('experiment-status-badge');
        const progressBox = document.getElementById('experiment-progress');
        const labelsEl = document.getElementById('exp-labels');
        const progressTextEl = document.getElementById('exp-progress-text');
        const resultContainer = document.getElementById('exp-result-container');
        const selectA = document.getElementById('exp-config-a');
        const selectB = document.getElementById('exp-config-b');

        if (!btnStart || !btnStop) return; // tab no presente (defensivo)

        let pollHandle = null;

        const KPI_LABELS = {
            'total_workorders_completed': 'WOs completadas',
            'total_workorders_failed': 'WOs fallidas',
            'total_simulation_time_seconds': 'Tiempo de simulación (s)',
            'avg_completion_time_seconds': 'Tiempo medio por WO (s)',
            'throughput_wo_per_s': 'Throughput (WO/s)',
            'fill_rate_pct': 'Fill-rate (%)',
        };

        const setBadge = (text, cls) => {
            badge.textContent = text;
            badge.className = `badge ${cls}`;
        };

        const stopPolling = () => {
            if (pollHandle) {
                clearInterval(pollHandle);
                pollHandle = null;
            }
        };

        const populateSelects = async () => {
            try {
                const resp = await fetch('/api/configurator/configurations');
                const data = await resp.json();
                const presets = data.configurations || data || [];
                [selectA, selectB].forEach(sel => {
                    if (!sel) return;
                    sel.innerHTML = '<option value="current">Actual (config.json)</option>';
                    presets.forEach(p => {
                        const opt = document.createElement('option');
                        opt.value = p.id;
                        opt.textContent = p.name;
                        sel.appendChild(opt);
                    });
                });
            } catch (err) {
                console.error('[EXPERIMENT] Error cargando presets:', err);
            }
        };

        const renderResultTable = (rows, labels) => {
            const available = (rows || []).filter(r => r.available);
            if (available.length === 0) {
                resultContainer.innerHTML = '<p class="help-text">Sin KPIs disponibles.</p>';
                return;
            }
            const fmt = (v, dec = 2) => (v == null ? '-' : Number(v).toFixed(dec));
            let html = '<table class="experiment-result-table"><thead><tr>' +
                '<th>KPI</th><th>A</th><th>B</th><th>Δ%</th><th>p</th><th>Veredicto</th>' +
                '</tr></thead><tbody>';
            available.forEach(r => {
                const significant = (r.verdict || '').indexOf('SIGNIFICATIVA') !== -1;
                html += `<tr class="${significant ? 'exp-significant' : ''}">` +
                    `<td>${KPI_LABELS[r.kpi] || r.kpi}</td>` +
                    `<td>${fmt(r.mean_a)}</td><td>${fmt(r.mean_b)}</td>` +
                    `<td>${r.delta_pct == null ? '-' : (r.delta_pct >= 0 ? '+' : '') + fmt(r.delta_pct, 1) + '%'}</td>` +
                    `<td>${r.pvalue == null ? '-' : fmt(r.pvalue, 4)}</td>` +
                    `<td>${r.verdict || '-'}</td></tr>`;
            });
            html += '</tbody></table>';
            html += '<p class="help-text">Veredicto por t-test pareado (α=0.05). "RUIDO" = la ' +
                'diferencia observada no es estadísticamente distinguible del azar con estas réplicas.</p>';
            resultContainer.innerHTML = html;
        };

        const renderStatus = (status) => {
            progressBox.classList.remove('hidden');
            const labels = status.labels || {};
            labelsEl.textContent = `A: ${labels.a || '-'}  vs  B: ${labels.b || '-'}`;
            progressTextEl.textContent =
                `${status.completed_replicas || 0} / ${status.total_replicas || 0} réplicas` +
                (status.current_label ? ` (corriendo ${status.current_label})` : '');
            if (status.status === 'done' && status.result) {
                renderResultTable(status.result, labels);
            } else if (status.status === 'error') {
                resultContainer.innerHTML =
                    `<p class="help-text" style="color:var(--color-danger);">Error: ${status.error || 'desconocido'}</p>`;
            }
        };

        const pollStatus = async () => {
            try {
                const resp = await fetch('/api/experiment/status');
                const status = await resp.json();
                renderStatus(status);
                if (status.running) {
                    setBadge('Corriendo...', 'badge-warning');
                    btnStart.disabled = true;
                    btnStop.disabled = false;
                } else {
                    if (status.status === 'done') {
                        setBadge('Finalizado', 'badge-success');
                    } else if (status.status === 'error') {
                        setBadge('Error', 'badge-error');
                    }
                    btnStart.disabled = false;
                    btnStop.disabled = true;
                    stopPolling();
                }
            } catch (err) {
                console.error('[EXPERIMENT] Error consultando estado:', err);
            }
        };

        btnStart.addEventListener('click', async () => {
            const body = {
                config_a: selectA?.value || 'current',
                config_b: selectB?.value || 'current',
                replicas: WebConfigurator.numero('exp-replicas', 5, true),
                base_seed: WebConfigurator.numero('exp-base-seed', 1000, true),
            };
            try {
                const resp = await fetch('/api/experiment/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (!resp.ok) {
                    const err = await resp.json();
                    this.showNotification(`Error: ${err.detail || 'no se pudo iniciar'}`, 'error');
                    return;
                }
                resultContainer.innerHTML = '';
                this.showNotification('Comparación A/B iniciada', 'success');
                setBadge('Corriendo...', 'badge-warning');
                btnStart.disabled = true;
                btnStop.disabled = false;
                stopPolling();
                pollHandle = setInterval(pollStatus, 3000);
                pollStatus();
            } catch (err) {
                this.showNotification(`Error inesperado: ${err.message}`, 'error');
            }
        });

        btnStop.addEventListener('click', async () => {
            try {
                const resp = await fetch('/api/experiment/stop', { method: 'POST' });
                if (!resp.ok) {
                    const err = await resp.json();
                    this.showNotification(`Error: ${err.detail || 'no se pudo detener'}`, 'error');
                    return;
                }
                this.showNotification('Comparación detenida', 'success');
                setBadge('Detenido', 'badge-neutral');
                btnStart.disabled = false;
                btnStop.disabled = true;
                stopPolling();
            } catch (err) {
                this.showNotification(`Error inesperado: ${err.message}`, 'error');
            }
        });

        populateSelects();

        // Si ya habia un experimento corriendo (servidor no reiniciado desde
        // que se lanzo), retomar el polling en vez de mostrar "Inactivo".
        (async () => {
            try {
                const resp = await fetch('/api/experiment/status');
                const status = await resp.json();
                if (status.running) {
                    renderStatus(status);
                    setBadge('Corriendo...', 'badge-warning');
                    btnStart.disabled = true;
                    btnStop.disabled = false;
                    pollHandle = setInterval(pollStatus, 3000);
                }
            } catch (err) {
                console.error('[EXPERIMENT] Error consultando estado inicial:', err);
            }
        })();
    }

    /**
     * Handle order file upload - sends to API and displays validation preview
     */
    async handleOrderFileUpload(file) {
        const dropzone = document.getElementById('orders-dropzone');
        const dropzoneContent = dropzone.querySelector('.dropzone-content');
        const validationPreview = document.getElementById('orders-validation-preview');
        const policySelect = document.getElementById('fulfillment-policy');

        // Validate file extension
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['json', 'csv'].includes(ext)) {
            this.showNotification('Solo se permiten archivos .json o .csv', 'error');
            return;
        }

        try {
            this.showLoading('Procesando archivo de órdenes...');

            // Create form data
            const formData = new FormData();
            formData.append('file', file);
            formData.append('fulfillment_policy', policySelect?.value || 'ship_partial');

            // Upload to API
            const response = await fetch('/api/upload-orders', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            this.hideLoading();

            if (result.success) {
                // Store file path for config serialization
                this.uploadedOrderFilePath = result.file_path;

                // Update dropzone appearance
                dropzone.classList.add('has-file');
                dropzoneContent.innerHTML = `
                    <span class="dropzone-icon">✅</span>
                    <p><strong>${file.name}</strong></p>
                    <small>Clic para cambiar archivo</small>
                `;

                // Show validation preview
                this.showValidationPreview(result.summary, result.exclusions);

                this.showNotification(`✓ ${file.name} procesado exitosamente`, 'success');
            } else {
                throw new Error(result.detail || 'Error procesando archivo');
            }

        } catch (error) {
            this.hideLoading();
            console.error('Order file upload error:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
        }
    }

    /**
     * Display validation preview with statistics and exclusions
     */
    showValidationPreview(summary, exclusions) {
        const preview = document.getElementById('orders-validation-preview');
        if (!preview) return;

        // Update stats
        document.getElementById('preview-orders').textContent = summary.total_orders_output || 0;
        document.getElementById('preview-items').textContent = summary.total_items_output || 0;
        document.getElementById('preview-skus').textContent = summary.skus_found || 0;
        document.getElementById('preview-missing').textContent = (summary.skus_missing || []).length;

        // Show exclusions if any
        const exclusionsList = document.getElementById('exclusions-list');
        const exclusionsItems = document.getElementById('exclusions-items');

        if (exclusions && exclusions.length > 0) {
            exclusionsList.classList.remove('hidden');
            exclusionsItems.innerHTML = exclusions.slice(0, 10).map(e =>
                `<li>Orden ${e.order_id}: ${e.reason}</li>`
            ).join('');

            if (exclusions.length > 10) {
                exclusionsItems.innerHTML += `<li>... y ${exclusions.length - 10} más</li>`;
            }
        } else {
            exclusionsList.classList.add('hidden');
        }

        preview.classList.remove('hidden');
    }

    async loadConfiguration() {
        try {
            this.showLoading('Cargando configuración...');

            const response = await fetch('/api/configurator/config');
            const result = await response.json();

            if (result.success) {
                this.currentConfig = result.config;

                // CRITICAL: Load work areas BEFORE loading config to form
                // This ensures WA dropdowns are populated before fleet reconstruction
                if (result.config.sequence_file) {
                    console.log('[WEB_CONFIGURATOR] Auto-loading work areas from sequence file...');
                    await this.loadWorkAreas(true); // true = silent mode (no notification)
                }

                // Now load config to form (including fleet with WA priorities)
                this.loadConfigToForm(result.config);

                this.hideLoading();
                console.log('[WEB_CONFIGURATOR] Configuration loaded successfully');
            } else {
                this.hideLoading();
                this.showNotification('Error loading configuration', 'error');
            }
        } catch (error) {
            this.hideLoading();
            console.error('[WEB_CONFIGURATOR] Error loading configuration:', error);
            this.showNotification('Error: ' + error.message, 'error');
        }
    }

    loadConfigToForm(config) {
        // H-01 (QA 2026-09-18): el formulario recuerda DE QUE configuracion se
        // cargo (la del servidor, un .json importado o un preset). Antes solo se
        // registraba la del servidor: al importar, lo que la web no edita
        // (y los parametros internos de congestion/outbound/tiempos) seguia
        // saliendo del config.json en vez del archivo importado.
        this.currentConfig = config;

        // Tab 1: Carga de Trabajo
        document.getElementById('total-ordenes').value = config.total_ordenes || 300;

        // AUD8-2: distribucion por CLASE DE MANEJO (5 clases; el campo
        // volumen quedo DEPRECATED -- la fisica vive en la hoja SkuCatalog).
        // Un preset viejo (3 tipos con 'grande') carga pequeno/mediano y deja
        // las clases nuevas en su default; el badge de suma avisa si != 100.
        const dist = config.distribucion_tipos || {};
        WebConfigurator.CLASES_DISTRIBUCION.forEach(([clave, id, defPct]) => {
            const el = document.getElementById(id);
            if (el) el.value = dist[clave]?.porcentaje ?? defPct;
        });
        // MEJ-3: capacidad_carro eliminada (el motor nunca la leyo; la capacidad
        // real es agent_types[].capacity, editable en Flota de Agentes).

        // Tab 2: Estrategias
        // Normalize strings to match HTML options (remove accents if present in JSON)
        const normalize = (str) => str ? str.normalize("NFD").replace(/[\u0300-\u036f]/g, "") : "";

        const strategy = config.dispatch_strategy || 'Optimizacion Global';
        const tour = config.tour_type || 'Tour Mixto (Multi-Destino)';

        // Try exact match first, then normalized match
        const strategySelect = document.getElementById('dispatch-strategy');
        const tourSelect = document.getElementById('tour-type');

        this.setSelectValue(strategySelect, strategy, normalize);
        this.setSelectValue(tourSelect, tour, normalize);

        // BK-01 + H-6: radio_cercania y params de expansion — cargar valores y mostrar/ocultar
        const radioCercaniaEl = document.getElementById('radio-cercania');
        if (radioCercaniaEl) radioCercaniaEl.value = config.radio_cercania != null ? config.radio_cercania : 100;
        const radioExpPasoEl = document.getElementById('radio-expansion-paso');
        if (radioExpPasoEl) radioExpPasoEl.value = config.radio_expansion_paso != null ? config.radio_expansion_paso : 50;
        const radioMaxExpEl = document.getElementById('radio-max-expansiones');
        if (radioMaxExpEl) radioMaxExpEl.value = config.radio_max_expansiones != null ? config.radio_max_expansiones : 5;
        this._updateRadioCercaniaVisibility();

        // Tab 3: Flota de Agentes
        // BK-05: si la flota viene explicita, se carga tal cual. Si viene en la
        // forma LEGACY (agent_types vacio + contadores num_operarios_*, que es
        // como esta el config.json canonico), se materializa preguntandole al
        // backend cual es la flota REAL que usaria el motor. Antes esta pestana
        // quedaba vacia y bloqueaba el guardado, aunque el motor corriera bien.
        // INIT-11 F1: si la flota se define con personas + equipos, esa
        // definicion MANDA en el motor. Se muestra la flota resultante y se
        // avisa que editar los grupos de esta pestana no tiene efecto.
        if (Array.isArray(config.personas) && config.personas.length > 0) {
            this._materializePersonasFleet(config);
        } else if (config.agent_types && config.agent_types.length > 0) {
            this.fleetManager.loadFleet(config.agent_types);
            this._setFleetDerivedNotice(false);
        } else {
            this._materializeLegacyFleet(config);
        }
        // QA-3 Opcion B: mapa area->equipo (siembra desde convencion lo que falte).
        // INIT-11 F1: los equipos declarados tambien son opciones del mapa.
        this.fleetManager.setEquipos(config.equipos || {});
        this.fleetManager.setWorkAreaEquipment(config.work_area_equipment || {});

        // Tab 4: Layout y Datos
        document.getElementById('layout-file').value = config.layout_file || 'layouts/WH1.tmx';
        document.getElementById('sequence-file').value = config.sequence_file || 'layouts/Warehouse_Logic.xlsx';
        // MEJ-3: map_scale eliminada (sin lector desde que se archivo el viewer Pygame).

        // Tab 2: zonas y cupo por pasillo (BK-25 capas 2 y 3)
        this._renderPasillos(config);

        // Tab 5: Outbound Staging
        // BK-25: rutas del modo aleatorio
        const rutasCfg = config.rutas_estocasticas || {};
        const togRutas = document.getElementById('toggle-rutas');
        if (togRutas) togRutas.checked = rutasCfg.enabled === true;
        const rutasCant = document.getElementById('rutas-cantidad');
        if (rutasCant) rutasCant.value = rutasCfg.cantidad != null ? rutasCfg.cantidad : 7;

        const stagingDist = config.outbound_staging_distribution || {};
        for (let i = 1; i <= 7; i++) {
            const value = stagingDist[i.toString()] || (i === 1 ? 100 : 0);
            document.getElementById(`staging-${i}`).value = value;
        }

        // Motor Avanzado (paso 2): toggles desde los bloques del config.
        // Ausencia de bloque = usar defaults validados (ON), NO apagar.
        const cong = config.congestion;
        const twChecked = cong ? (cong.enabled === true && cong.mode === 'timewindow') : true;
        const obChecked = config.outbound ? (config.outbound.enabled === true) : true;
        const twToggle = document.getElementById('toggle-timewindow');
        const obToggle = document.getElementById('toggle-outbound');
        if (twToggle) twToggle.checked = twChecked;
        if (obToggle) obToggle.checked = obChecked;

        // Outbound: cargar truck_interval/truck_capacity y mostrar/ocultar segun el toggle
        const truckIntervalEl = document.getElementById('truck-interval');
        if (truckIntervalEl) {
            const ti = (config.outbound && config.outbound.truck_interval != null)
                ? config.outbound.truck_interval : 90;
            truckIntervalEl.value = ti;
        }
        const truckCapacityEl = document.getElementById('truck-capacity');
        if (truckCapacityEl) {
            const tc = (config.outbound && config.outbound.truck_capacity != null)
                ? config.outbound.truck_capacity : 8;
            truckCapacityEl.value = tc;
        }
        this._updateOutboundVisibility();

        // INIT-7 F3: tab Inbound (bloque ausente = apagado, opt-in)
        const inb = config.inbound || {};
        const inbToggle = document.getElementById('toggle-inbound');
        if (inbToggle) inbToggle.checked = inb.enabled === true;
        const _setVal = (id, val, fallback) => {
            const el = document.getElementById(id);
            if (el) el.value = (val != null) ? val : fallback;
        };
        _setVal('inbound-arrival-mode', inb.arrival_mode, 'deterministic');
        _setVal('inbound-asn-file', inb.asn_file_path, 'layouts/Inbound Test.json');
        _setVal('inbound-truck-interval', inb.truck_interval, 600);
        _setVal('inbound-num-trucks', inb.num_trucks, 5);
        _setVal('inbound-pallets-per-truck', inb.pallets_per_truck, 10);
        _setVal('inbound-units-per-pallet', inb.units_per_pallet, 20);
        _setVal('inbound-unload-time', inb.unload_time_per_pallet, 15);
        _setVal('inbound-pallet-release', inb.pallet_release, 'per_pallet');
        _setVal('inbound-putaway-load-time', inb.putaway_load_time, 10);
        _setVal('inbound-slotting', inb.slotting_strategy, 'fija_por_sku');
        _setVal('inbound-putaway-priority', inb.putaway_priority, 'picks_first');
        const xdToggle = document.getElementById('inbound-cross-dock');
        if (xdToggle) xdToggle.checked = inb.cross_dock_enabled === true;
        this._updateInboundVisibility();

        // INIT-6 Opcion B: destino -> staging_id
        this._renderDestinoStagingRows(config.destino_staging_map || {});

        // C5: Tiempos de Operacion — cargar bloque tiempos desde config.
        // Ausencia del bloque = usar defaults demo (comportamiento actual).
        const t = config.tiempos || {};
        const tpc  = (t.time_per_cell != null)          ? t.time_per_cell          : 0.1;
        const sfk  = (t.speed_factor_forklift != null)  ? t.speed_factor_forklift  : 0.8;
        const lift = (t.tiempo_horquilla != null)        ? t.tiempo_horquilla       : 2.0;
        const tpcEl  = document.getElementById('tiempos-time-per-cell');
        const sfkEl  = document.getElementById('tiempos-speed-forklift');
        const liftEl = document.getElementById('tiempos-lift');
        if (tpcEl)  tpcEl.value  = tpc;
        if (sfkEl)  sfkEl.value  = sfk;
        if (liftEl) liftEl.value = lift;
        this._updateTiemposPreset(tpc, sfk, lift);

        // INIT-8 UI: modelo de tiempo de pick (base null = usar historico).
        const ptm = t.pick_time_model || {};
        const _setNum = (id, val, fallback) => {
            const el = document.getElementById(id);
            if (el) el.value = (val != null) ? val : fallback;
        };
        const ptmBaseEl = document.getElementById('ptm-base');
        if (ptmBaseEl) ptmBaseEl.value = (ptm.base != null) ? ptm.base : '';
        _setNum('ptm-por-unidad', ptm.por_unidad, 0);
        _setNum('ptm-por-volumen', ptm.por_volumen, 0);
        _setNum('ptm-por-kg', ptm.por_kg, 0);
        _setNum('ptm-minimo', ptm.minimo, 0);

        // INIT-8 UI: grid de clases de manejo (config manda; sin bloque =
        // defaults calibrados del grid).
        const cm = t.clases_manejo || {};
        WebConfigurator.CLASES_MANEJO_UI.forEach(([clave, idBase, , d]) => {
            const e = cm[clave] || {};
            _setNum(`${idBase}-mult`, e.mult, d.mult);
            _setNum(`${idBase}-recargo`, e.recargo, d.recargo);
            _setNum(`${idBase}-pack`, e.pack, d.pack);
        });

        // INIT-8 UI: bloques opt-in F3/F4 (ausentes = apagados).
        const vc = t.velocidad_por_carga || {};
        const vcEnabledEl = document.getElementById('vc-enabled');
        if (vcEnabledEl) vcEnabledEl.checked = vc.enabled === true;
        _setNum('vc-reduccion-kg', vc.reduccion_por_kg, 0.0084);
        _setNum('vc-reduccion-max', vc.reduccion_max, 0.5);
        const vcFkEl = document.getElementById('vc-aplica-forklift');
        if (vcFkEl) vcFkEl.checked = vc.aplica_forklift === true;

        const va = t.variabilidad || {};
        const varEnabledEl = document.getElementById('var-enabled');
        if (varEnabledEl) varEnabledEl.checked = va.enabled === true;
        _setNum('var-cv', va.cv, 0.25);
        this._updateTiemposInit8Visibility();

        // Trigger validations
        this.validatePercentages();
        this.validateStagingDistribution();
    }

    // Defaults VALIDADOS (copiados de config_stress_tw_v2.json, valores F1.3).
    // Se usan solo si el config en memoria no trae los bloques (config viejo).
    getDefaultAdvancedBlocks() {
        return {
            // MEJ-3: solo claves VIVAS (las F3 del enfoque de exclusion por celda
            // fueron purgadas; el motor usa sus defaults si algun modo las necesita).
            congestion: {
                enabled: true, mode: 'timewindow',
                spawn_offset: 0.3, staggered_start: true,
                timewindow: {
                    shadow: false, clearance: 0.0, dt_wait: 0.1,
                    max_expansions: 20000, plan_horizon: 0.0, allow_diagonal: false
                }
            },
            outbound: {
                enabled: true, dispatch_policy: 'interval', truck_interval: 90.0,
                truck_capacity: 8, loading_time: 2.0, zone_capacity_default: 8,
                slot_wait_alert: 60.0, slot_poll_dt: 0.1, dwell_scaffold: 10.0
            },
            // INIT-7: inbound opt-in (default APAGADO = comportamiento historico)
            inbound: {
                enabled: false, arrival_mode: 'deterministic',
                asn_file_path: 'layouts/Inbound Test.json',
                truck_interval: 600.0, num_trucks: 5, pallets_per_truck: 10,
                units_per_pallet: 20, unload_time_per_pallet: 15.0,
                pallet_release: 'per_pallet',
                putaway_load_time: 10.0, slotting_strategy: 'fija_por_sku',
                putaway_priority: 'picks_first', cross_dock_enabled: false
            },
            // C5: defaults del bloque tiempos (perfil DEMO = valores actuales del motor)
            tiempos: {
                cell_size_m: 1.0,
                time_per_cell: 0.1,
                speed_factor_ground: 1.0,
                speed_factor_forklift: 0.8,
                tiempo_horquilla: 2.0
            }
        };
    }

    serializeConfig() {
        // Get order generation mode
        const orderModeRadio = document.querySelector('input[name="order-generation-mode"]:checked');
        const orderMode = orderModeRadio ? orderModeRadio.value : 'stochastic';

        // Tab 1: Carga de Trabajo
        const config = {
            // NEW: Order generation mode settings
            order_generation_mode: orderMode,
            fulfillment_policy: document.getElementById('fulfillment-policy')?.value || 'ship_partial',
            order_file_path: this.uploadedOrderFilePath || '',

            total_ordenes: parseInt(document.getElementById('total-ordenes').value),
            // AUD8-2: claves = clases de manejo reales; sin 'volumen'
            // (DEPRECATED: la fisica del producto vive en SkuCatalog).
            distribucion_tipos: Object.fromEntries(
                WebConfigurator.CLASES_DISTRIBUCION.map(([clave, id, defPct]) => [
                    clave,
                    { porcentaje: WebConfigurator.numero(id, defPct, true) }
                ])
            ),
            // Tab 2: Estrategias
            dispatch_strategy: document.getElementById('dispatch-strategy').value,
            radio_cercania: WebConfigurator.numero('radio-cercania', 100, true),
            radio_expansion_paso: WebConfigurator.numero('radio-expansion-paso', 50, true),
            radio_max_expansiones: WebConfigurator.numero('radio-max-expansiones', 5, true),
            tour_type: document.getElementById('tour-type').value,

            // Tab 3: Flota de Agentes
            agent_types: this.fleetManager.serializeFleet(),
            // QA-3 Opcion B: mapa explicito area->tipo de equipo requerido.
            work_area_equipment: this.fleetManager.getWorkAreaEquipment(),

            // Tab 4: Layout y Datos
            layout_file: document.getElementById('layout-file').value,
            sequence_file: document.getElementById('sequence-file').value,

            // Tab 5: Outbound Staging
            outbound_staging_distribution: {},
            rutas_estocasticas: {
                enabled: document.getElementById('toggle-rutas')?.checked === true,
                cantidad: WebConfigurator.numero('rutas-cantidad', 7)
            },

            // Contadores de flota (fallback del motor cuando agent_types = [];
            // num_operarios_total es legacy-informativo pero REQUIRED_KEYS lo exige).
            // MEJ-3: purgadas las claves muertas (capacidad_carro/montacargas,
            // tiempo_descarga_por_tarea, assignment_rules, tareas_zona_*, num_operarios).
            num_operarios_terrestres: 0,
            num_montacargas: 0,
            num_operarios_total: 0
        };

        // Populate staging distribution
        for (let i = 1; i <= 7; i++) {
            config.outbound_staging_distribution[i.toString()] = parseInt(document.getElementById(`staging-${i}`).value);
        }

        // Calculate legacy fields from agent_types
        let groundOperatorCount = 0;
        let forkliftCount = 0;

        config.agent_types.forEach(agent => {
            if (agent.type === 'GroundOperator') {
                groundOperatorCount++;
            } else if (agent.type === 'Forklift') {
                forkliftCount++;
            }
        });

        config.num_operarios_terrestres = groundOperatorCount;
        config.num_montacargas = forkliftCount;
        config.num_operarios_total = groundOperatorCount + forkliftCount;

        // Motor Avanzado (paso 2). REGLA CRITICA (merge superficial en backend):
        // siempre enviar el bloque COMPLETO. Base = bloque del config en memoria
        // (this.currentConfig, viene del GET); si falta, defaults validados.
        const defaults = this.getDefaultAdvancedBlocks();
        const baseCong = JSON.parse(JSON.stringify(
            (this.currentConfig && this.currentConfig.congestion) || defaults.congestion));
        const baseOb = JSON.parse(JSON.stringify(
            (this.currentConfig && this.currentConfig.outbound) || defaults.outbound));

        const twOn = document.getElementById('toggle-timewindow')?.checked ?? true;
        const obOn = document.getElementById('toggle-outbound')?.checked ?? true;

        baseCong.enabled = twOn;
        baseCong.mode = twOn ? 'timewindow' : 'off';
        if (twOn) {
            // Forzar variante EFECTIVA: un config viejo con shadow:true dejaria
            // el toggle ON sin efecto real (el planner solo observaria).
            if (!baseCong.timewindow) baseCong.timewindow = JSON.parse(JSON.stringify(defaults.congestion.timewindow));
            baseCong.timewindow.shadow = false;
        }
        baseOb.enabled = obOn;
        // Outbound: la UI tambien controla truck_interval/truck_capacity (resto de claves se preservan)
        const tiEl = document.getElementById('truck-interval');
        if (tiEl && tiEl.value !== '') {
            const tiVal = parseInt(tiEl.value);
            if (!isNaN(tiVal) && tiVal >= 1) baseOb.truck_interval = tiVal;
        }
        const tcEl = document.getElementById('truck-capacity');
        if (tcEl && tcEl.value !== '') {
            const tcVal = parseInt(tcEl.value);
            if (!isNaN(tcVal) && tcVal >= 1) baseOb.truck_capacity = tcVal;
        }

        config.congestion = baseCong;
        config.outbound = baseOb;
        // INIT-6 Opcion B: destino -> staging_id.
        // Solo se emite si tiene contenido o si ya existia en el config (mismo
        // criterio que el bloque inbound de abajo). Antes se emitia SIEMPRE,
        // aunque fuera {}: guardar el canonico sin tocar nada le agregaba
        // `destino_staging_map: {}` y cambiaba la metadata del replay.
        this._serializePasillos(config);
        const destinoMap = this._serializeDestinoStagingRows();
        const destinoExistia = !!(this.currentConfig
            && Object.prototype.hasOwnProperty.call(this.currentConfig, 'destino_staging_map'));
        if (Object.keys(destinoMap).length > 0 || destinoExistia) {
            config.destino_staging_map = destinoMap;
        }

        // INIT-7 F3: bloque inbound completo (mismo patron base+overrides).
        // Solo se emite si el usuario lo activo alguna vez o ya existia en el
        // config: un config canonico SIN bloque inbound se conserva limpio
        // (opt-in real, el gate byte-identico depende de la ausencia).
        const inbToggleEl = document.getElementById('toggle-inbound');
        const inbOn = inbToggleEl?.checked ?? false;
        if (inbOn || (this.currentConfig && this.currentConfig.inbound)) {
            const baseInb = JSON.parse(JSON.stringify(
                (this.currentConfig && this.currentConfig.inbound) || defaults.inbound));
            baseInb.enabled = inbOn;
            const mode = document.getElementById('inbound-arrival-mode')?.value;
            if (mode) baseInb.arrival_mode = mode;
            const asn = document.getElementById('inbound-asn-file')?.value;
            if (asn && asn.trim() !== '') baseInb.asn_file_path = asn.trim();
            const _numField = (id, key, min, isFloat) => {
                const el = document.getElementById(id);
                if (!el || el.value === '') return;
                const v = isFloat ? parseFloat(el.value) : parseInt(el.value);
                if (!isNaN(v) && v >= min) baseInb[key] = v;
            };
            _numField('inbound-truck-interval', 'truck_interval', 1, true);
            _numField('inbound-num-trucks', 'num_trucks', 1, false);
            _numField('inbound-pallets-per-truck', 'pallets_per_truck', 1, false);
            _numField('inbound-units-per-pallet', 'units_per_pallet', 1, false);
            _numField('inbound-unload-time', 'unload_time_per_pallet', 0, true);
            _numField('inbound-putaway-load-time', 'putaway_load_time', 0, true);
            const release = document.getElementById('inbound-pallet-release')?.value;
            if (release) baseInb.pallet_release = release;
            const slot = document.getElementById('inbound-slotting')?.value;
            if (slot) baseInb.slotting_strategy = slot;
            // INIT-7 F5: prioridad de flota + cross-docking
            const prio = document.getElementById('inbound-putaway-priority')?.value;
            if (prio) baseInb.putaway_priority = prio;
            const xd = document.getElementById('inbound-cross-dock');
            if (xd) baseInb.cross_dock_enabled = xd.checked;
            config.inbound = baseInb;
        }

        // C5: bloque tiempos completo. Mismo patron que congestion/outbound:
        // base = bloque en memoria (para preservar cell_size_m y speed_factor_ground
        // que la UI no expone); la UI sobreescribe solo las claves que conoce.
        const defaultsTiempos = this.getDefaultAdvancedBlocks().tiempos;
        const baseTiempos = JSON.parse(JSON.stringify(
            (this.currentConfig && this.currentConfig.tiempos) || defaultsTiempos));
        const tpcVal  = parseFloat(document.getElementById('tiempos-time-per-cell')?.value);
        const sfkVal  = parseFloat(document.getElementById('tiempos-speed-forklift')?.value);
        const liftVal = parseFloat(document.getElementById('tiempos-lift')?.value);
        if (!isNaN(tpcVal)  && tpcVal  > 0) baseTiempos.time_per_cell          = tpcVal;
        if (!isNaN(sfkVal)  && sfkVal  > 0) baseTiempos.speed_factor_forklift  = sfkVal;
        if (!isNaN(liftVal) && liftVal >= 0) baseTiempos.tiempo_horquilla       = liftVal;
        // `tiempo_picking_por_linea` se ELIMINO del motor (2026-09-09): la UI no
        // la escribe ni la inventa. Si un archivo viejo la trae, `baseTiempos`
        // (base-preserve) la conserva tal cual y el motor simplemente la ignora.

        // INIT-8 UI: modelo de tiempo de pick (base-preserve + overrides;
        // base vacia = null = usar tiempo historico del agente).
        const basePtm = baseTiempos.pick_time_model || {};
        const ptmBaseRaw = document.getElementById('ptm-base')?.value;
        basePtm.base = (ptmBaseRaw !== '' && ptmBaseRaw != null
                        && !isNaN(parseFloat(ptmBaseRaw)))
                       ? parseFloat(ptmBaseRaw) : null;
        const _numOrKeep = (id, obj, key) => {
            const v = parseFloat(document.getElementById(id)?.value);
            if (!isNaN(v) && v >= 0) obj[key] = v;
        };
        _numOrKeep('ptm-por-unidad', basePtm, 'por_unidad');
        _numOrKeep('ptm-por-volumen', basePtm, 'por_volumen');
        _numOrKeep('ptm-por-kg', basePtm, 'por_kg');
        _numOrKeep('ptm-minimo', basePtm, 'minimo');
        baseTiempos.pick_time_model = basePtm;

        // INIT-8 UI: clases de manejo (por clase: base-preserve + overrides).
        const baseCm = baseTiempos.clases_manejo || {};
        WebConfigurator.CLASES_MANEJO_UI.forEach(([clave, idBase]) => {
            const entrada = baseCm[clave] || {};
            const m = parseFloat(document.getElementById(`${idBase}-mult`)?.value);
            if (!isNaN(m) && m > 0) entrada.mult = m;
            _numOrKeep(`${idBase}-recargo`, entrada, 'recargo');
            // pack: solo si es > 0 o la clave ya existia -- un canonico sin
            // packs se conserva SIN la clave (estabilidad byte-identica del
            // round-trip: el config viaja en la metadata del .jsonl/gate).
            const p = parseFloat(document.getElementById(`${idBase}-pack`)?.value);
            if (!isNaN(p) && p >= 0 && (p > 0 || 'pack' in entrada)) entrada.pack = p;
            baseCm[clave] = entrada;
        });
        baseTiempos.clases_manejo = baseCm;

        // INIT-8 UI: bloques opt-in F3/F4. Solo se emiten si el toggle esta
        // activo O el bloque ya existia (un canonico limpio se conserva
        // limpio: mismo patron que el bloque inbound).
        const vcOn = document.getElementById('vc-enabled')?.checked ?? false;
        if (vcOn || baseTiempos.velocidad_por_carga) {
            const baseVc = baseTiempos.velocidad_por_carga || {};
            baseVc.enabled = vcOn;
            _numOrKeep('vc-reduccion-kg', baseVc, 'reduccion_por_kg');
            _numOrKeep('vc-reduccion-max', baseVc, 'reduccion_max');
            baseVc.aplica_forklift =
                document.getElementById('vc-aplica-forklift')?.checked ?? false;
            baseTiempos.velocidad_por_carga = baseVc;
        }
        const varOn = document.getElementById('var-enabled')?.checked ?? false;
        if (varOn || baseTiempos.variabilidad) {
            const baseVar = baseTiempos.variabilidad || {};
            baseVar.enabled = varOn;
            const cvVal = parseFloat(document.getElementById('var-cv')?.value);
            if (!isNaN(cvVal) && cvVal > 0) baseVar.cv = cvVal;
            baseTiempos.variabilidad = baseVar;
        }

        config.tiempos = baseTiempos;

        // H-01 (QA 2026-09-18): conservar las claves que la web NO edita
        // (olas, prioridad de pedidos, fleet_defaults, personas, equipos,
        // perfiles...). Antes "Run Simulation" corria solo con lo que arma el
        // formulario y las descartaba en silencio: el mismo config daba otra
        // simulacion desde el boton que desde la consola. Se toman de la
        // configuracion de la que se cargo el formulario, y lo que el
        // formulario si edita siempre gana.
        const origen = this.currentConfig || {};
        Object.keys(origen).forEach((clave) => {
            if (!Object.prototype.hasOwnProperty.call(config, clave)) {
                config[clave] = JSON.parse(JSON.stringify(origen[clave]));
            }
        });

        return config;
    }

    async loadWorkAreas(silent = false) {
        try {
            const sequenceFile = document.getElementById('sequence-file').value;

            if (!sequenceFile) {
                if (!silent) {
                    this.showNotification('Por favor especifique un archivo de secuencia', 'error');
                }
                return;
            }

            if (!silent) {
                this.showLoading('Cargando Work Areas...');
            }

            const response = await fetch(`/api/configurator/work-areas?sequence_file=${encodeURIComponent(sequenceFile)}`);
            const result = await response.json();

            if (!silent) {
                this.hideLoading();
            }

            if (result.success && result.work_areas && result.work_areas.length > 0) {
                this.workAreas = result.work_areas;
                this.fleetManager.setWorkAreas(this.workAreas);

                const count = this.workAreas.length;
                const areasList = this.workAreas.join(', ');

                console.log(`[WEB_CONFIGURATOR] ${count} Work Areas loaded: ${areasList}`);

                if (!silent) {
                    const origen = result.origen === 'excel' ? ' (del Excel: no hay datos aplicados)' : '';
                    this.showNotification(
                        `✓ ${count} Work Areas cargadas: ${areasList}${origen}`,
                        'success'
                    );
                    // BK-35: el Excel trae areas distintas a las que usa el simulador
                    (result.avisos || []).forEach(a => this.showNotification('⚠ ' + a, 'warning'));
                }
            } else {
                console.warn('[WEB_CONFIGURATOR] No work areas found in file, using defaults');
                this.workAreas = ['Area_Ground', 'Area_High', 'Area_Special'];
                this.fleetManager.setWorkAreas(this.workAreas);

                if (!silent) {
                    this.showNotification('⚠ Usando Work Areas por defecto', 'warning');
                }
            }
        } catch (error) {
            if (!silent) {
                this.hideLoading();
            }
            console.error('[WEB_CONFIGURATOR] Error loading work areas:', error);

            if (!silent) {
                this.showNotification('Error: ' + error.message, 'error');
            }
        }
    }

    setSelectValue(selectElement, value, normalizeFn) {
        if (!selectElement) return;

        // Try exact match
        for (let i = 0; i < selectElement.options.length; i++) {
            if (selectElement.options[i].value === value) {
                selectElement.value = value;
                return;
            }
        }

        // Try normalized match
        const normalizedValue = normalizeFn(value);
        for (let i = 0; i < selectElement.options.length; i++) {
            if (normalizeFn(selectElement.options[i].value) === normalizedValue) {
                selectElement.value = selectElement.options[i].value;
                return;
            }
        }

        // Fallback: log warning
        console.warn(`[WEB_CONFIGURATOR] Could not match value '${value}' for select '${selectElement.id}'`);
    }

    // Utility methods
    showLoading(message = 'Cargando...') {
        const overlay = document.getElementById('loading-overlay');
        const messageEl = document.getElementById('loading-message');

        if (overlay && messageEl) {
            messageEl.textContent = message;
            overlay.classList.remove('hidden');
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    showNotification(message, type = 'info') {
        const toast = document.getElementById('notification-toast');
        const messageEl = document.getElementById('notification-message');

        if (toast && messageEl) {
            messageEl.textContent = message;
            toast.className = `notification-toast ${type}`;
            toast.classList.remove('hidden');

            // Auto-hide after 5 seconds
            setTimeout(() => {
                toast.classList.add('hidden');
            }, 5000);
        }
    }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.configurator = new WebConfigurator();
    });
} else {
    window.configurator = new WebConfigurator();
}
