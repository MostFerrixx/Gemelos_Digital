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

        // Initialize modules
        this.fleetManager = new FleetManager(this);
        configStorage = new ConfigurationStorage(this);

        // Setup event listeners
        this.setupEventListeners();
        this.setupTabNavigation();
        this.setupValidations();

        // Load initial configuration
        await this.loadConfiguration();

        console.log('[WEB_CONFIGURATOR] Initialization complete');
    }

    setupEventListeners() {
        // Toolbar buttons
        document.getElementById('btn-save').addEventListener('click', () => configStorage.saveAs());
        document.getElementById('btn-load').addEventListener('click', () => configStorage.loadFrom());
        document.getElementById('btn-manage').addEventListener('click', () => configStorage.manage());
        document.getElementById('btn-default').addEventListener('click', () => configStorage.loadDefault());
        document.getElementById('btn-use').addEventListener('click', () => configStorage.useConfiguration());

        // Layout & Data buttons
        document.getElementById('btn-generate-template').addEventListener('click', () => this.generateTemplate());
        document.getElementById('btn-populate-skus').addEventListener('click', () => this.populateSKUs());
        document.getElementById('btn-load-work-areas').addEventListener('click', () => this.loadWorkAreas());
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

    async loadConfiguration() {
        try {
            this.showLoading('Cargando configuración...');

            const response = await fetch('/api/configurator/config');
            const result = await response.json();

            this.hideLoading();

            if (result.success) {
                this.currentConfig = result.config;
                this.loadConfigToForm(result.config);
                console.log('[WEB_CONFIGURATOR] Configuration loaded successfully');
            } else {
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
        document.getElementById('dispatch-strategy').value = config.dispatch_strategy || 'Optimizacion Global';
        document.getElementById('tour-type').value = config.tour_type || 'Tour Mixto (Multi-Destino)';

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

        // Trigger validations
        this.validatePercentages();
        this.validateStagingDistribution();
    }

    serializeConfig() {
        // Tab 1: Carga de Trabajo
        const config = {
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

        return config;
    }

    async loadWorkAreas() {
        try {
            const sequenceFile = document.getElementById('sequence-file').value;

            if (!sequenceFile) {
                this.showNotification('Por favor especifique un archivo de secuencia', 'error');
                return;
            }

            this.showLoading('Cargando Work Areas...');

            const response = await fetch(`/api/configurator/work-areas?sequence_file=${encodeURIComponent(sequenceFile)}`);
            const result = await response.json();

            this.hideLoading();

            if (result.success) {
                this.workAreas = result.work_areas;
                this.fleetManager.setWorkAreas(this.workAreas);

                const count = this.workAreas.length;
                const areasList = this.workAreas.join(', ');

                this.showNotification(
                    `✓ ${count} Work Areas cargadas: ${areasList}`,
                    'success'
                );
            } else {
                this.showNotification('Error loading work areas', 'error');
            }
        } catch (error) {
            this.hideLoading();
            console.error('[WEB_CONFIGURATOR] Error loading work areas:', error);
            this.showNotification('Error: ' + error.message, 'error');
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
