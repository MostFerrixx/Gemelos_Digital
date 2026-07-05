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
        this.setupOptimizationPanel(); // INIT-3 v2: panel de optimizacion Optuna
        this.setupExperimentPanel(); // MEJ-EXP-WEB: comparador A/B

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
        document.getElementById('btn-load-work-areas').addEventListener('click', () => this.loadWorkAreas());

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
                    document.getElementById('tiempos-picking').value = '';
                    document.getElementById('tiempos-lift').value = 2.0;
                } else if (e.target.value === 'real') {
                    document.getElementById('tiempos-time-per-cell').value = 1.0;
                    document.getElementById('tiempos-speed-forklift').value = 0.5;
                    document.getElementById('tiempos-picking').value = 15;
                    document.getElementById('tiempos-lift').value = 8.0;
                }
                // 'custom': el usuario edita manualmente, no se sobreescriben los campos
            });
            // Cambio manual de cualquier campo -> muestra "Personalizado"
            ['tiempos-time-per-cell', 'tiempos-speed-forklift',
             'tiempos-picking', 'tiempos-lift'].forEach(id => {
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

    _serializeDestinoStagingRows() {
        const container = document.getElementById('destino-staging-list');
        const map = {};
        if (!container) return map;
        container.querySelectorAll('.destino-staging-row').forEach(row => {
            const name = row.querySelector('.destino-staging-name').value.trim();
            const zone = parseInt(row.querySelector('.destino-staging-zone').value, 10);
            if (name && !isNaN(zone) && zone >= 1 && zone <= 7) {
                map[name] = zone;
            }
        });
        return map;
    }

    // C5: determina si los valores actuales coinciden con un preset conocido.
    _updateTiemposPreset(tpc, sfk, pick, lift) {
        const sel = document.getElementById('tiempos-preset');
        if (!sel) return;
        const isDemo = Math.abs(tpc - 0.1) < 0.001 && Math.abs(sfk - 0.8) < 0.001
                       && pick == null && Math.abs(lift - 2.0) < 0.001;
        const isReal = Math.abs(tpc - 1.0) < 0.001 && Math.abs(sfk - 0.5) < 0.001
                       && pick != null && Math.abs(pick - 15.0) < 0.001
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
            'layout-datos': { title: 'Layout y Datos', subtitle: 'Archivos de mapa, secuencia y escala' },
            'staging': { title: 'Outbound Staging', subtitle: 'Distribución de salida por zonas' },
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
     * INIT-3 v2: panel de optimizacion Optuna (start/status/stop via
     * /api/optimization/*). El estudio corre en background en el servidor;
     * este panel solo lanza y consulta por polling, no bloquea la pestaña.
     */
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
                n_trials: parseInt(document.getElementById('opt-n-trials').value, 10) || 20,
                n_jobs: parseInt(document.getElementById('opt-n-jobs').value, 10) || 2,
                cost_ground: parseFloat(document.getElementById('opt-cost-ground').value) || 15.0,
                cost_forklift: parseFloat(document.getElementById('opt-cost-forklift').value) || 50.0,
                penalty_failed: parseFloat(document.getElementById('opt-penalty-failed').value) || 100.0,
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
                replicas: parseInt(document.getElementById('exp-replicas').value, 10) || 5,
                base_seed: parseInt(document.getElementById('exp-base-seed').value, 10) || 1000,
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
        // Tab 1: Carga de Trabajo
        document.getElementById('total-ordenes').value = config.total_ordenes || 300;

        const dist = config.distribucion_tipos || {};
        document.getElementById('pct-pequeno').value = dist.pequeno?.porcentaje || 60;
        document.getElementById('pct-mediano').value = dist.mediano?.porcentaje || 30;
        document.getElementById('pct-grande').value = dist.grande?.porcentaje || 10;

        document.getElementById('vol-pequeno').value = dist.pequeno?.volumen || 5;
        document.getElementById('vol-mediano').value = dist.mediano?.volumen || 25;
        document.getElementById('vol-grande').value = dist.grande?.volumen || 80;
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
        if (config.agent_types && config.agent_types.length > 0) {
            this.fleetManager.loadFleet(config.agent_types);
        }
        // QA-3 Opcion B: mapa area->equipo (siembra desde convencion lo que falte).
        this.fleetManager.setWorkAreaEquipment(config.work_area_equipment || {});

        // Tab 4: Layout y Datos
        document.getElementById('layout-file').value = config.layout_file || 'layouts/WH1.tmx';
        document.getElementById('sequence-file').value = config.sequence_file || 'layouts/Warehouse_Logic.xlsx';
        // MEJ-3: map_scale eliminada (sin lector desde que se archivo el viewer Pygame).

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

        // INIT-6 Opcion B: destino -> staging_id
        this._renderDestinoStagingRows(config.destino_staging_map || {});

        // C5: Tiempos de Operacion — cargar bloque tiempos desde config.
        // Ausencia del bloque = usar defaults demo (comportamiento actual).
        const t = config.tiempos || {};
        const tpc  = (t.time_per_cell != null)          ? t.time_per_cell          : 0.1;
        const sfk  = (t.speed_factor_forklift != null)  ? t.speed_factor_forklift  : 0.8;
        const pick = (t.tiempo_picking_por_linea != null) ? t.tiempo_picking_por_linea : null;
        const lift = (t.tiempo_horquilla != null)        ? t.tiempo_horquilla       : 2.0;
        const tpcEl  = document.getElementById('tiempos-time-per-cell');
        const sfkEl  = document.getElementById('tiempos-speed-forklift');
        const pickEl = document.getElementById('tiempos-picking');
        const liftEl = document.getElementById('tiempos-lift');
        if (tpcEl)  tpcEl.value  = tpc;
        if (sfkEl)  sfkEl.value  = sfk;
        if (pickEl) pickEl.value = (pick != null) ? pick : '';
        if (liftEl) liftEl.value = lift;
        this._updateTiemposPreset(tpc, sfk, pick, lift);

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
            // C5: defaults del bloque tiempos (perfil DEMO = valores actuales del motor)
            tiempos: {
                cell_size_m: 1.0,
                time_per_cell: 0.1,
                speed_factor_ground: 1.0,
                speed_factor_forklift: 0.8,
                tiempo_picking_por_linea: null,
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
            // Tab 2: Estrategias
            dispatch_strategy: document.getElementById('dispatch-strategy').value,
            radio_cercania: parseInt(document.getElementById('radio-cercania')?.value) || 100,
            radio_expansion_paso: parseInt(document.getElementById('radio-expansion-paso')?.value) || 50,
            radio_max_expansiones: parseInt(document.getElementById('radio-max-expansiones')?.value) || 5,
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
        // INIT-6 Opcion B: destino -> staging_id
        config.destino_staging_map = this._serializeDestinoStagingRows();

        // C5: bloque tiempos completo. Mismo patron que congestion/outbound:
        // base = bloque en memoria (para preservar cell_size_m y speed_factor_ground
        // que la UI no expone); la UI sobreescribe solo las claves que conoce.
        const defaultsTiempos = this.getDefaultAdvancedBlocks().tiempos;
        const baseTiempos = JSON.parse(JSON.stringify(
            (this.currentConfig && this.currentConfig.tiempos) || defaultsTiempos));
        const tpcVal  = parseFloat(document.getElementById('tiempos-time-per-cell')?.value);
        const sfkVal  = parseFloat(document.getElementById('tiempos-speed-forklift')?.value);
        const pickRaw = document.getElementById('tiempos-picking')?.value;
        const liftVal = parseFloat(document.getElementById('tiempos-lift')?.value);
        if (!isNaN(tpcVal)  && tpcVal  > 0) baseTiempos.time_per_cell          = tpcVal;
        if (!isNaN(sfkVal)  && sfkVal  > 0) baseTiempos.speed_factor_forklift  = sfkVal;
        baseTiempos.tiempo_picking_por_linea =
            (pickRaw !== '' && pickRaw != null && !isNaN(parseFloat(pickRaw)))
            ? parseFloat(pickRaw) : null;
        if (!isNaN(liftVal) && liftVal >= 0) baseTiempos.tiempo_horquilla       = liftVal;
        config.tiempos = baseTiempos;

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
