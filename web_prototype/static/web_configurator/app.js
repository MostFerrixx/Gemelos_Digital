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

        // Setup event listeners
        this.setupEventListeners();
        this.setupTabNavigation();
        this.setupValidations();
        this.setupOrderGenerationMode(); // NEW: Setup order mode toggle

        // Load initial configuration
        await this.loadConfiguration();

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
        document.getElementById('btn-generate-template').addEventListener('click', () => this.generateTemplate());
        document.getElementById('btn-populate-skus').addEventListener('click', () => this.populateSKUs());
        document.getElementById('btn-load-work-areas').addEventListener('click', () => this.loadWorkAreas());
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
            'layout-datos': { title: 'Layout y Datos', subtitle: 'Archivos de mapa, secuencia y escala' },
            'staging': { title: 'Outbound Staging', subtitle: 'Distribución de salida por zonas' }
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

    setupValidations() {
        // Percentages validation for Carga de Trabajo
        const pctInputs = ['pct-pequeno', 'pct-mediano', 'pct-grande'];
        pctInputs.forEach(id => {
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
        const pequeno = parseInt(document.getElementById('pct-pequeno').value) || 0;
        const mediano = parseInt(document.getElementById('pct-mediano').value) || 0;
        const grande = parseInt(document.getElementById('pct-grande').value) || 0;
        const total = pequeno + mediano + grande;

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
        // Tab 1: Carga de Trabajo
        document.getElementById('total-ordenes').value = config.total_ordenes || 300;

        const dist = config.distribucion_tipos || {};
        document.getElementById('pct-pequeno').value = dist.pequeno?.porcentaje || 60;
        document.getElementById('pct-mediano').value = dist.mediano?.porcentaje || 30;
        document.getElementById('pct-grande').value = dist.grande?.porcentaje || 10;

        document.getElementById('vol-pequeno').value = dist.pequeno?.volumen || 5;
        document.getElementById('vol-mediano').value = dist.mediano?.volumen || 25;
        document.getElementById('vol-grande').value = dist.grande?.volumen || 80;

        document.getElementById('capacidad-carro').value = config.capacidad_carro || 150;

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

        // Tab 3: Flota de Agentes
        if (config.agent_types && config.agent_types.length > 0) {
            this.fleetManager.loadFleet(config.agent_types);
        }

        // Tab 4: Layout y Datos
        document.getElementById('layout-file').value = config.layout_file || 'layouts/WH1.tmx';
        document.getElementById('sequence-file').value = config.sequence_file || 'layouts/Warehouse_Logic.xlsx';
        document.getElementById('map-scale').value = config.map_scale || 1.3;

        // Tab 5: Outbound Staging
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

        // Trigger validations
        this.validatePercentages();
        this.validateStagingDistribution();
    }

    // Defaults VALIDADOS (copiados de config_stress_tw_v2.json, valores F1.3).
    // Se usan solo si el config en memoria no trae los bloques (config viejo).
    getDefaultAdvancedBlocks() {
        return {
            congestion: {
                enabled: true, mode: 'timewindow', wait_timeout: 0.5,
                wait_hard_cap: 30.0, backoff_base: 0.1, backoff_jitter: 0.1,
                max_repath: 3, repath_cost_factor: 2.0, spawn_offset: 0.3,
                watchdog_window: 5.0, allow_swap: false, aging_rate: 1.0,
                staggered_start: true,
                timewindow: {
                    shadow: false, clearance: 0.0, dt_wait: 0.1,
                    max_expansions: 20000, plan_horizon: 0.0, allow_diagonal: false
                }
            },
            outbound: {
                enabled: true, dispatch_policy: 'interval', truck_interval: 20.0,
                truck_capacity: 8, loading_time: 2.0, zone_capacity_default: 8,
                slot_wait_alert: 60.0, slot_poll_dt: 0.1, dwell_scaffold: 10.0
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
            distribucion_tipos: {
                pequeno: {
                    porcentaje: parseInt(document.getElementById('pct-pequeno').value),
                    volumen: parseInt(document.getElementById('vol-pequeno').value)
                },
                mediano: {
                    porcentaje: parseInt(document.getElementById('pct-mediano').value),
                    volumen: parseInt(document.getElementById('vol-mediano').value)
                },
                grande: {
                    porcentaje: parseInt(document.getElementById('pct-grande').value),
                    volumen: parseInt(document.getElementById('vol-grande').value)
                }
            },
            capacidad_carro: parseInt(document.getElementById('capacidad-carro').value),

            // Tab 2: Estrategias
            dispatch_strategy: document.getElementById('dispatch-strategy').value,
            tour_type: document.getElementById('tour-type').value,

            // Tab 3: Flota de Agentes
            agent_types: this.fleetManager.serializeFleet(),

            // Tab 4: Layout y Datos
            layout_file: document.getElementById('layout-file').value,
            sequence_file: document.getElementById('sequence-file').value,
            map_scale: parseFloat(document.getElementById('map-scale').value),

            // Tab 5: Outbound Staging
            outbound_staging_distribution: {},

            // Legacy/compatibility fields
            num_operarios_terrestres: 0,
            num_montacargas: 0,
            num_operarios_total: 0,
            capacidad_montacargas: 1000,
            tiempo_descarga_por_tarea: 5,
            assignment_rules: {
                GroundOperator: {},
                Forklift: {}
            },
            tareas_zona_a: 0,
            tareas_zona_b: 0,
            num_operarios: 0
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
        config.num_operarios = groundOperatorCount + forkliftCount;

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

        config.congestion = baseCong;
        config.outbound = baseOb;

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
                    this.showNotification(
                        `✓ ${count} Work Areas cargadas: ${areasList}`,
                        'success'
                    );
                }
            } else {
                console.warn('[WEB_CONFIGURATOR] No work areas found in file, using defaults');
                this.workAreas = ['Area_Ground', 'Area_Rack', 'Area_Piso_L1'];
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

    generateTemplate() {
        this.showNotification(
            'Funcionalidad en desarrollo.\n\n' +
            'Creará Warehouse_Logic.xlsx con:\n' +
            '- Columnas de ubicaciones de picking\n' +
            '- Datos por defecto para el simulador\n' +
            '- Estructura lista para modificar',
            'info'
        );
    }

    populateSKUs() {
        this.showNotification(
            'Funcionalidad en desarrollo.\n\n' +
            'Rellenará el CSV con:\n' +
            '- SKUs aleatorios\n' +
            '- Cantidades aleatorias',
            'info'
        );
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
