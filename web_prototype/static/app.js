// =============================================
// Gemelo Digital - Web Simulator
// Modular Architecture with Shared State
// =============================================

// ============================================
//  CONSTANTS
// ============================================
const TILE_SIZE = 20; // Pixels per tile
const AGENT_RADIUS = 8;
const COLORS = {
    WALL: '#555555',
    FLOOR: '#1a1f26',
    ZONE_PICKING: 'rgba(0, 200, 100, 0.2)',
    ZONE_STAGING: 'rgba(200, 200, 50, 0.2)'
};

// Agent colors matching replay_engine colors.py
const AGENT_COLORS = {
    GroundOperator: {
        base: 'rgb(255, 100, 0)',      // Orange
        idle: 'rgb(128, 128, 128)',     // Gray
        picking: 'rgb(0, 200, 0)',      // Green
        unloading: 'rgb(0, 200, 0)',    // Green
        moving: 'rgb(255, 255, 0)'      // Yellow
    },
    Forklift: {
        base: 'rgb(0, 150, 255)',       // Blue
        idle: 'rgb(128, 128, 128)',
        picking: 'rgb(0, 200, 0)',
        unloading: 'rgb(0, 200, 0)',
        moving: 'rgb(255, 255, 0)'
    }
};

// Unique color palette for operators (matching desktop renderer)
const OPERATOR_COLOR_PALETTE = [
    [255, 50, 50],      // Red
    [50, 255, 50],      // Green
    [100, 150, 255],    // Blue
    [255, 255, 0],      // Yellow
    [255, 0, 255],      // Magenta
    [0, 255, 255],      // Cyan
    [255, 165, 0],      // Orange
    [255, 100, 150],    // Pink
    [150, 100, 255],    // Purple
    [50, 200, 200],     // Turquoise
    [200, 200, 50],     // Yellow-green
    [255, 150, 50]      // Orange-ish
];

// Table column configuration (18 columns, matching PyQt6 Dashboard)
const COLUMNS = [
    { key: 'id', header: 'WO_ID', width: '110px' },
    { key: 'order_id', header: 'ORDER ID', width: '100px' },
    { key: 'tour_id', header: 'TOUR ID', width: '100px' },
    { key: 'sku_id', header: 'SKU', width: '90px' },
    { key: 'product', header: 'PRODUCT', width: '150px' },
    { key: 'status', header: 'STATUS', width: '120px' },
    { key: 'assigned_agent_id', header: 'AGENT', width: '140px' },
    { key: 'priority', header: 'PRIORITY', width: '90px' },
    { key: 'items', header: 'ITEMS', width: '70px' },
    { key: 'total_qty', header: 'TOTAL QTY', width: '90px' },
    { key: 'volume', header: 'VOLUME', width: '90px' },
    { key: 'location', header: 'LOCATION', width: '120px' },
    { key: 'staging', header: 'STAGING', width: '120px' },
    { key: 'work_group', header: 'WORK GROUP', width: '110px' },
    { key: 'work_area', header: 'WORK AREA', width: '110px' },
    { key: 'executions', header: 'EXECUTIONS', width: '100px' },
    { key: 'start_time', header: 'START TIME', width: '100px' },
    { key: 'progress', header: 'PROGRESS', width: '100px' }
];

// ============================================
//  APPSTATE SINGLETON (Single Source of Truth)
// ============================================
const AppState = {
    // Timeline
    currentTime: 0,
    maxTime: 0,
    isPlaying: false,
    playbackSpeed: 1,

    // Data
    workOrders: new Map(),
    agents: {},
    layout: null,

    // UI State
    isTableVisible: false,
    canvasHeightPercent: 65,
    sortColumn: 'id',
    sortDirection: 'asc',

    // Listeners (Observer Pattern)
    listeners: [],

    // Subscribe to state changes
    subscribe(callback) {
        this.listeners.push(callback);
        console.log('[AppState] Listener subscribed, total:', this.listeners.length);
    },

    // Notify all listeners
    notify() {
        this.listeners.forEach(cb => {
            try {
                cb(this);
            } catch (error) {
                console.error('[AppState] Error in listener:', error);
            }
        });
    },

    // Setters with automatic notification
    setTime(time) {
        this.currentTime = time;
        this.notify();
    },

    setWorkOrders(wos) {
        this.workOrders = new Map(Object.entries(wos || {}));
        this.notify();
    },

    setAgents(agents) {
        this.agents = agents || {};
        this.notify();
    },

    setLayout(layout) {
        this.layout = layout;
        this.notify();
    },

    toggleTable() {
        this.isTableVisible = !this.isTableVisible;
        this.notify();
    },

    setSort(column, direction) {
        this.sortColumn = column;
        this.sortDirection = direction;
        this.notify();
    }
};

// ============================================
//  TABLE MODULE (from Dashboard v10)
// ============================================
const TableModule = {
    tableEl: null,

    init() {
        console.log('[TableModule] Initializing...');
        this.tableEl = document.getElementById('workOrderTable');

        if (!this.tableEl) {
            console.error('[TableModule] Table element not found!');
            return;
        }

        // Setup headers
        this.setupHeaders();

        // Setup sorting
        this.setupSorting();

        // Subscribe to state changes
        AppState.subscribe(state => this.render(state));

        console.log('[TableModule] Ready');
    },

    setupHeaders() {
        const thead = this.tableEl.querySelector('thead');
        if (!thead) return;

        thead.innerHTML = '<tr></tr>';
        const tr = thead.querySelector('tr');

        COLUMNS.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col.header;
            th.style.width = col.width;
            th.dataset.column = col.key;
            tr.appendChild(th);
        });
    },

    setupSorting() {
        const headers = this.tableEl.querySelectorAll('th');

        headers.forEach((th, idx) => {
            th.addEventListener('click', () => {
                const column = COLUMNS[idx].key;

                // Toggle direction if same column, else default to asc
                let direction = 'asc';
                if (AppState.sortColumn === column) {
                    direction = AppState.sortDirection === 'asc' ? 'desc' : 'asc';
                }

                // Update state
                AppState.setSort(column, direction);

                // Update UI indicators
                headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
                th.classList.add(`sort-${direction}`);
            });
        });
    },

    render(state) {
        if (!state.isTableVisible) return; // Don't render if collapsed

        const tbody = this.tableEl.querySelector('tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (state.workOrders.size === 0) {
            const tr = tbody.insertRow();
            const td = tr.insertCell();
            td.colSpan = COLUMNS.length;
            td.textContent = 'No work orders available';
            td.style.textAlign = 'center';
            td.style.padding = '40px';
            td.style.color = 'var(--color-text-secondary)';
            return;
        }

        // Sort work orders
        const sortedWOs = this.sortWorkOrders(Array.from(state.workOrders.values()), state);

        // Render rows
        sortedWOs.forEach(wo => {
            const row = this.createRow(wo);
            tbody.appendChild(row);
        });
    },

    sortWorkOrders(wos, state) {
        return wos.sort((a, b) => {
            let aVal = a[state.sortColumn] ?? '';
            let bVal = b[state.sortColumn] ?? '';

            // Handle numeric sorting
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return state.sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
            }

            // String sorting
            aVal = String(aVal).toLowerCase();
            bVal = String(bVal).toLowerCase();

            if (state.sortDirection === 'asc') {
                return aVal > bVal ? 1 : -1;
            } else {
                return aVal < bVal ? 1 : -1;
            }
        });
    },

    createRow(wo) {
        const tr = document.createElement('tr');
        tr.dataset.woId = wo.id;

        // Apply status class for color coding (CRITICAL - matches PyQt6)
        const status = wo.status || 'released';
        tr.classList.add(`status-${status}`);

        COLUMNS.forEach(col => {
            const td = tr.insertCell();
            let value = wo[col.key];

            // Format specific fields
            if (value === null || value === undefined) {
                value = '';
            } else if (col.key === 'location' || col.key === 'staging') {
                // Format arrays as (x, y)
                if (Array.isArray(value)) {
                    value = `(${value.join(', ')})`;
                }
            } else if (col.key === 'volume' && typeof value === 'number') {
                value = value.toFixed(2);
            } else if (col.key === 'start_time' && typeof value === 'number') {
                value = value.toFixed(2);
            } else if (col.key === 'progress' && typeof value === 'number') {
                value = (value * 100).toFixed(1) + '%';
            }

            td.textContent = value;
            td.title = value; // Tooltip for overflow
        });

        return tr;
    }
};

// ============================================
//  CANVAS MODULE (Enhanced with state subscription)
// ============================================
const CanvasModule = {
    canvas: null,
    ctx: null,
    scale: 1.0, // Current scale factor (1.0 = 100%, 0.5 = 50%, etc.)
    resizeRAF: null, // RequestAnimationFrame ID for throttling

    init() {
        console.log('[CanvasModule] Initializing...');
        this.canvas = document.getElementById('simCanvas');

        if (!this.canvas) {
            console.error('[CanvasModule] Canvas element not found!');
            return;
        }

        this.ctx = this.canvas.getContext('2d');

        // Observar cambios de tamaño del contenedor con throttling
        const container = document.getElementById('canvas-section');
        if (container) {
            const resizeObserver = new ResizeObserver(() => {
                // Performance: Usar RAF para evitar redibujados excesivos durante drag
                if (this.resizeRAF) {
                    cancelAnimationFrame(this.resizeRAF);
                }
                this.resizeRAF = requestAnimationFrame(() => {
                    this.resize();
                });
            });
            resizeObserver.observe(container);
            console.log('[CanvasModule] ResizeObserver attached to canvas-section');
        }

        // Subscribe to state changes
        AppState.subscribe(state => this.render(state));

        console.log('[CanvasModule] Ready');
    },

    /**
     * Redimensiona el canvas para que quepa en el contenedor disponible
     * manteniendo la relación de aspecto del layout original.
     */
    resize() {
        if (!this.canvas || !AppState.layout) return;

        const container = document.getElementById('canvas-section');
        if (!container) return;

        // Obtener dimensiones del contenedor (restando márgenes)
        const containerRect = container.getBoundingClientRect();
        const availableWidth = containerRect.width - 40; // Considerar márgenes
        const availableHeight = containerRect.height - 40;

        // Dimensiones originales del layout en píxeles
        const layoutWidth = AppState.layout.width * TILE_SIZE;
        const layoutHeight = AppState.layout.height * TILE_SIZE;

        // Calcular escala para que quepa todo (usar la menor para mantener aspect ratio)
        const scaleX = availableWidth / layoutWidth;
        const scaleY = availableHeight / layoutHeight;
        const newScale = Math.min(scaleX, scaleY, 1.0); // No agrandar más allá del 100%

        // Aplicar nuevo tamaño al canvas
        this.canvas.width = layoutWidth * newScale;
        this.canvas.height = layoutHeight * newScale;

        // Guardar escala actual
        // IMPORTANTE: Este valor será necesario para mouse mapping en el futuro.
        // Si necesitas detectar clics sobre agentes, deberás dividir las coordenadas
        // del mouse por esta escala: logicalX = mouseX / scale, logicalY = mouseY / scale
        this.scale = newScale;

        console.log(`[CanvasModule] Resized to ${this.canvas.width}x${this.canvas.height} (scale: ${newScale.toFixed(3)})`);

        // Re-renderizar con la nueva escala
        this.render(AppState);
    },

    /**
     * Obtiene la escala actual del canvas.
     * @returns {number} Factor de escala actual (1.0 = tamaño original)
     * 
     * FUTURO: Usar este método para convertir coordenadas del mouse a coordenadas lógicas:
     * const scale = CanvasModule.getScale();
     * const logicalX = mouseEvent.offsetX / scale;
     * const logicalY = mouseEvent.offsetY / scale;
     */
    getScale() {
        return this.scale;
    },

    render(state) {
        if (!state.layout) return;

        // Aplicar transformación de escala si es necesaria
        if (this.scale && this.scale !== 1.0) {
            this.ctx.save();
            this.ctx.scale(this.scale, this.scale);
        }

        // Clear and render map
        this.renderMap(state.layout);

        // Render picking nodes BEFORE agents
        this.renderPickingNodes(state);

        // Render agents
        this.renderAgents(state.agents);

        // Restaurar contexto si se aplicó escala
        if (this.scale && this.scale !== 1.0) {
            this.ctx.restore();
        }
    },

    renderMap(layout) {
        // Existing renderMap logic (preserved)
        this.ctx.fillStyle = COLORS.FLOOR;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        layout.layers.forEach(layer => {
            if (layer.tiles) {
                layer.tiles.forEach(tile => {
                    const x = tile.x * TILE_SIZE;
                    const y = tile.y * TILE_SIZE;
                    const gid = tile.gid;

                    // GID mapping (from original code)
                    if (gid === 1) {
                        // Floor
                        this.ctx.fillStyle = '#2a2e35';
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
                        this.ctx.lineWidth = 0.5;
                        this.ctx.strokeRect(x, y, TILE_SIZE, TILE_SIZE);
                    } else if (gid === 2) {
                        // Racks
                        const gradient = this.ctx.createLinearGradient(x, y, x + TILE_SIZE, y + TILE_SIZE);
                        gradient.addColorStop(0, '#4a4a4a');
                        gradient.addColorStop(0.5, '#5a5a5a');
                        gradient.addColorStop(1, '#3a3a3a');
                        this.ctx.fillStyle = gradient;
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                        this.ctx.strokeStyle = '#6a6a6a';
                        this.ctx.lineWidth = 2;
                        this.ctx.beginPath();
                        this.ctx.moveTo(x, y + TILE_SIZE * 0.25);
                        this.ctx.lineTo(x + TILE_SIZE, y + TILE_SIZE * 0.25);
                        this.ctx.moveTo(x, y + TILE_SIZE * 0.5);
                        this.ctx.lineTo(x + TILE_SIZE, y + TILE_SIZE * 0.5);
                        this.ctx.moveTo(x, y + TILE_SIZE * 0.75);
                        this.ctx.lineTo(x + TILE_SIZE, y + TILE_SIZE * 0.75);
                        this.ctx.stroke();

                        this.ctx.strokeStyle = '#7a7a7a';
                        this.ctx.lineWidth = 1.5;
                        this.ctx.beginPath();
                        this.ctx.moveTo(x + TILE_SIZE * 0.2, y);
                        this.ctx.lineTo(x + TILE_SIZE * 0.2, y + TILE_SIZE);
                        this.ctx.moveTo(x + TILE_SIZE * 0.8, y);
                        this.ctx.lineTo(x + TILE_SIZE * 0.8, y + TILE_SIZE);
                        this.ctx.stroke();

                        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
                        this.ctx.fillRect(x + TILE_SIZE - 3, y + 2, 3, TILE_SIZE - 2);
                    } else if (gid === 3) {
                        // Picking locations
                        this.ctx.fillStyle = '#2a2e35';
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                        this.ctx.fillStyle = 'rgba(255, 200, 0, 0.25)';
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                        this.ctx.strokeStyle = 'rgba(255, 200, 0, 0.4)';
                        this.ctx.lineWidth = 2;
                        for (let i = -TILE_SIZE; i < TILE_SIZE * 2; i += 6) {
                            this.ctx.beginPath();
                            this.ctx.moveTo(x + i, y);
                            this.ctx.lineTo(x + i + TILE_SIZE, y + TILE_SIZE);
                            this.ctx.stroke();
                        }

                        this.ctx.strokeStyle = 'rgba(255, 200, 0, 0.6)';
                        this.ctx.lineWidth = 1;
                        this.ctx.strokeRect(x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2);
                    } else if (gid === 4) {
                        // Parking/Start
                        this.ctx.fillStyle = '#1e2530';
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                        this.ctx.fillStyle = 'rgba(100, 150, 255, 0.2)';
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                        this.ctx.strokeStyle = 'rgba(100, 150, 255, 0.4)';
                        this.ctx.lineWidth = 1;
                        this.ctx.strokeRect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4);

                        this.ctx.setLineDash([3, 3]);
                        this.ctx.beginPath();
                        this.ctx.moveTo(x + TILE_SIZE / 2, y);
                        this.ctx.lineTo(x + TILE_SIZE / 2, y + TILE_SIZE);
                        this.ctx.stroke();
                        this.ctx.setLineDash([]);
                    } else if (gid === 5) {
                        // Depot/Outbound
                        this.ctx.fillStyle = '#1e2e25';
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                        this.ctx.fillStyle = 'rgba(0, 200, 100, 0.2)';
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                        const checkerSize = TILE_SIZE / 4;
                        for (let cy = 0; cy < 4; cy++) {
                            for (let cx = 0; cx < 4; cx++) {
                                if ((cx + cy) % 2 === 0) {
                                    this.ctx.fillStyle = 'rgba(0, 200, 100, 0.1)';
                                    this.ctx.fillRect(x + cx * checkerSize, y + cy * checkerSize, checkerSize, checkerSize);
                                }
                            }
                        }

                        this.ctx.strokeStyle = 'rgba(0, 200, 100, 0.5)';
                        this.ctx.lineWidth = 2;
                        this.ctx.strokeRect(x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2);
                    } else if (gid === 6) {
                        // Inbound
                        this.ctx.fillStyle = '#2e2520';
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                        this.ctx.fillStyle = 'rgba(255, 150, 50, 0.2)';
                        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                        this.ctx.strokeStyle = 'rgba(255, 150, 50, 0.4)';
                        this.ctx.lineWidth = 2;
                        for (let i = 0; i < TILE_SIZE; i += 5) {
                            this.ctx.beginPath();
                            this.ctx.moveTo(x, y + i);
                            this.ctx.lineTo(x + TILE_SIZE, y + i);
                            this.ctx.stroke();
                        }

                        this.ctx.strokeStyle = 'rgba(255, 150, 50, 0.6)';
                        this.ctx.lineWidth = 1.5;
                        this.ctx.strokeRect(x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2);
                    }
                });
            }
        });
    },

    renderPickingNodes(state) {
        // Existing logic (preserved)
        if (!state || !state.agents) return;

        Object.entries(state.agents).forEach(([agentId, agent]) => {
            const assignedWOs = agent.work_orders_asignadas || [];

            if (assignedWOs.length === 0) return;

            const status = agent.status || 'idle';
            if (status === 'idle' || status === 'completed') return;

            const locationMap = new Map();

            assignedWOs.forEach((wo, idx) => {
                const location = wo.location;
                if (!location || location.length !== 2) return;

                const [gridX, gridY] = location;
                const pixelX = gridX * TILE_SIZE + TILE_SIZE / 2;
                const pixelY = gridY * TILE_SIZE + TILE_SIZE / 2;
                const locKey = `${pixelX},${pixelY}`;

                if (!locationMap.has(locKey)) {
                    locationMap.set(locKey, {
                        pos: [pixelX, pixelY],
                        woCount: 0,
                        minSequence: wo.pick_sequence || idx
                    });
                }

                locationMap.get(locKey).woCount++;
            });

            const locations = Array.from(locationMap.values())
                .sort((a, b) => a.minSequence - b.minSequence);

            const locationsWithAccumulated = [];
            for (let i = 0; i < locations.length; i++) {
                const accumulated = locations.slice(0, i + 1)
                    .reduce((sum, loc) => sum + loc.woCount, 0);
                locationsWithAccumulated.push({
                    ...locations[i],
                    accumulated
                });
            }

            const operatorColor = this.getOperatorColor(agentId);

            locationsWithAccumulated.forEach((location, idx) => {
                const [px, py] = location.pos;
                const woCount = location.accumulated;
                const isCurrent = idx < 2;
                const radius = 7;

                let nodeColor = operatorColor;
                if (isCurrent) {
                    const rgb = operatorColor.match(/\d+/g).map(Number);
                    nodeColor = `rgb(${Math.min(255, rgb[0] + 50)}, ${Math.min(255, rgb[1] + 50)}, ${Math.min(255, rgb[2] + 50)})`;
                }

                this.ctx.beginPath();
                this.ctx.arc(px, py, radius, 0, Math.PI * 2);
                this.ctx.fillStyle = nodeColor;
                this.ctx.fill();

                this.ctx.strokeStyle = '#000';
                this.ctx.lineWidth = isCurrent ? 2 : 1;
                this.ctx.stroke();

                this.ctx.fillStyle = '#fff';
                this.ctx.font = 'bold 10px Inter, sans-serif';
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';

                this.ctx.strokeText(woCount.toString(), px, py);
                this.ctx.fillText(woCount.toString(), px, py);
            });
        });
    },

    renderAgents(agents) {
        // Existing logic with person icon (preserved)
        Object.entries(agents).forEach(([id, agent]) => {
            const [gridX, gridY] = agent.position;
            const screenX = gridX * TILE_SIZE + TILE_SIZE / 2;
            const screenY = gridY * TILE_SIZE + TILE_SIZE / 2;

            const agentType = agent.type.includes('Forklift') ? 'Forklift' : 'GroundOperator';
            const colorScheme = AGENT_COLORS[agentType];
            const agentColor = colorScheme[agent.status] || colorScheme.base;

            this.ctx.save();
            this.ctx.translate(screenX, screenY);

            // Head (Circle)
            this.ctx.beginPath();
            this.ctx.arc(0, -7, 5, 0, Math.PI * 2);
            this.ctx.fillStyle = agentColor;
            this.ctx.fill();
            this.ctx.strokeStyle = '#fff';
            this.ctx.lineWidth = 1;
            this.ctx.stroke();

            // Body (Rounded shape)
            this.ctx.beginPath();
            this.ctx.arc(0, 7, 8, Math.PI, 0);
            this.ctx.lineTo(8, 7);
            this.ctx.fillStyle = agentColor;
            this.ctx.fill();
            this.ctx.stroke();

            this.ctx.restore();

            // Agent ID Label
            this.ctx.fillStyle = '#fff';
            this.ctx.font = 'bold 11px Inter, sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'top';

            const label = id.split('-').pop();
            const metrics = this.ctx.measureText(label);
            const padding = 3;
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
            this.ctx.fillRect(
                screenX - metrics.width / 2 - padding,
                screenY + 16,
                metrics.width + padding * 2,
                14
            );

            this.ctx.fillStyle = '#fff';
            this.ctx.fillText(label, screenX, screenY + 18);
        });
    },

    getOperatorColor(agentId) {
        // Hash function to get unique color
        let hash = 0;
        for (let i = 0; i < agentId.length; i++) {
            hash = ((hash << 5) - hash) + agentId.charCodeAt(i);
            hash = hash & hash;
        }
        const index = Math.abs(hash) % OPERATOR_COLOR_PALETTE.length;
        const [r, g, b] = OPERATOR_COLOR_PALETTE[index];
        return `rgb(${r}, ${g}, ${b})`;
    }
};

// ============================================
//  CONTROLS MODULE (Unified Timeline)
// ============================================
const ControlsModule = {
    playInterval: null,
    seekDebounceTimer: null,
    currentAbortController: null,
    loadingTimeoutId: null,

    init() {
        console.log('[ControlsModule] Initializing...');

        const playPauseBtn = document.getElementById('play-pause-btn');
        const timeSlider = document.getElementById('time-slider');
        const speedSelect = document.getElementById('speed-select');

        if (playPauseBtn) {
            playPauseBtn.addEventListener('click', () => this.togglePlay());
        }

        if (timeSlider) {
            timeSlider.addEventListener('input', (e) => this.handleSeek(e));
        }

        if (speedSelect) {
            speedSelect.addEventListener('change', (e) => {
                AppState.playbackSpeed = parseFloat(e.target.value);
                console.log('[ControlsModule] Speed changed to:', AppState.playbackSpeed);
            });
        }

        // Subscribe to state changes
        AppState.subscribe(state => this.updateUI(state));

        console.log('[ControlsModule] Ready');
    },

    togglePlay() {
        if (AppState.isPlaying) {
            this.stop();
        } else {
            this.play();
        }
    },

    play() {
        AppState.isPlaying = true;
        const playPauseBtn = document.getElementById('play-pause-btn');
        if (playPauseBtn) {
            playPauseBtn.querySelector('.btn-icon').textContent = '⏸';
            playPauseBtn.querySelector('.btn-label').textContent = 'Pause';
        }

        let lastTime = Date.now();

        this.playInterval = setInterval(() => {
            const now = Date.now();
            const deltaMs = now - lastTime;
            lastTime = now;

            const deltaTime = (deltaMs / 1000) * AppState.playbackSpeed;
            let newTime = AppState.currentTime + deltaTime;

            if (newTime >= AppState.maxTime) {
                newTime = AppState.maxTime;
                this.stop();
            }

            this.seekTo(newTime);
        }, 100);

        console.log('[ControlsModule] Playback started');
    },

    stop() {
        AppState.isPlaying = false;
        clearInterval(this.playInterval);

        const playPauseBtn = document.getElementById('play-pause-btn');
        if (playPauseBtn) {
            playPauseBtn.querySelector('.btn-icon').textContent = '▶';
            playPauseBtn.querySelector('.btn-label').textContent = 'Play';
        }

        console.log('[ControlsModule] Playback stopped');
    },

    handleSeek(e) {
        const targetTime = parseFloat(e.target.value);

        if (AppState.isPlaying) {
            this.stop();
        }

        // Update slider position immediately for smooth visual feedback
        AppState.currentTime = targetTime;
        this.updateUI(AppState);

        // Cancel previous debounce timer
        if (this.seekDebounceTimer) {
            clearTimeout(this.seekDebounceTimer);
        }

        // Debounce: wait 100ms after last movement before fetching
        this.seekDebounceTimer = setTimeout(() => {
            this.seekTo(targetTime);
            this.seekDebounceTimer = null;
        }, 100);
    },

    async seekTo(time) {
        // AGGRESSIVE CANCELLATION: Abort any pending request immediately
        if (this.currentAbortController) {
            this.currentAbortController.abort();
            console.log('[ControlsModule] Aborted previous request');
        }

        // Create new abort controller for this request
        this.currentAbortController = new AbortController();

        // Show loading indicator if request takes longer than 200ms
        this.loadingTimeoutId = setTimeout(() => {
            this.setLoadingState(true);
        }, 200);

        try {
            const response = await fetch(`/api/state?t=${time}`, {
                signal: this.currentAbortController.signal
            });
            const data = await response.json();

            // Clear loading timeout and hide indicator
            clearTimeout(this.loadingTimeoutId);
            this.setLoadingState(false);

            // Update AppState (will notify all subscribers)
            AppState.setTime(time);
            AppState.maxTime = data.max_time;
            AppState.setWorkOrders(data.work_orders);
            AppState.setAgents(data.agents);

            // Update metrics separately
            await this.updateMetrics(time);

            // Clear controller reference
            this.currentAbortController = null;
        } catch (error) {
            // Clear loading timeout
            clearTimeout(this.loadingTimeoutId);
            this.setLoadingState(false);

            if (error.name === 'AbortError') {
                // Request was cancelled - this is expected behavior
                console.log('[ControlsModule] Request cancelled (user moved slider)');
                return;
            }
            console.error('[ControlsModule] Error seeking:', error);
        }
    },

    setLoadingState(isLoading) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = isLoading ? 'flex' : 'none';
        }
    },

    async updateMetrics(time) {
        try {
            const response = await fetch(`/api/metrics?t=${time}`);
            const metrics = await response.json();

            if (!metrics) return;

            const woMetrics = metrics.work_orders || {};

            // Update compact metrics in panel header
            this.setMetricValue('metric-total', woMetrics.total || 0);
            this.setMetricValue('metric-released', woMetrics.released || 0);
            this.setMetricValue('metric-assigned', woMetrics.assigned || 0);
            this.setMetricValue('metric-in-progress', woMetrics.in_progress || 0);
            this.setMetricValue('metric-staged', woMetrics.staged || 0);
        } catch (error) {
            console.error('[ControlsModule] Error fetching metrics:', error);
        }
    },

    setMetricValue(elementId, value) {
        const el = document.getElementById(elementId);
        if (el) {
            el.textContent = value;
        }
    },

    updateUI(state) {
        // Update time displays and slider
        const currentTimeEl = document.getElementById('current-time');
        const maxTimeEl = document.getElementById('max-time');
        const timeSlider = document.getElementById('time-slider');

        if (currentTimeEl) {
            currentTimeEl.textContent = this.formatTime(state.currentTime);
        }

        if (maxTimeEl && state.maxTime > 0) {
            maxTimeEl.textContent = this.formatTime(state.maxTime);
        }

        if (timeSlider) {
            timeSlider.max = state.maxTime;
            timeSlider.value = state.currentTime;
        }
    },

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
};

// ============================================
//  RESIZE MODULE (Draggable Handle)
// ============================================
const ResizeModule = {
    isDragging: false,

    init() {
        console.log('[ResizeModule] Initializing...');

        const handle = document.getElementById('resize-handle');

        if (!handle) {
            console.error('[ResizeModule] Resize handle not found!');
            return;
        }

        handle.addEventListener('mousedown', (e) => this.startDrag(e));
        document.addEventListener('mousemove', (e) => this.drag(e));
        document.addEventListener('mouseup', () => this.stopDrag());

        // Load saved preference
        const saved = localStorage.getItem('canvasHeightPercent');
        if (saved) {
            const percent = parseFloat(saved);
            document.getElementById('canvas-section').style.flexBasis = `${percent}%`;
            AppState.canvasHeightPercent = percent;
        }

        console.log('[ResizeModule] Ready');
    },

    startDrag(e) {
        this.isDragging = true;
        e.preventDefault();
        console.log('[ResizeModule] Drag started');
    },

    drag(e) {
        if (!this.isDragging) return;

        const mainLayout = document.getElementById('main-layout');
        if (!mainLayout) return;

        const rect = mainLayout.getBoundingClientRect();
        const offsetY = e.clientY - rect.top;
        const percent = (offsetY / rect.height) * 100;

        // Clamp between 30% and 85%
        const clamped = Math.max(30, Math.min(85, percent));

        document.getElementById('canvas-section').style.flexBasis = `${clamped}%`;
        AppState.canvasHeightPercent = clamped;
    },

    stopDrag() {
        if (!this.isDragging) return;

        this.isDragging = false;

        // Save preference
        localStorage.setItem('canvasHeightPercent', AppState.canvasHeightPercent);
        console.log('[ResizeModule] Drag stopped, saved:', AppState.canvasHeightPercent);
    }
};

// ============================================
//  PANEL MODULE (Toggle Bottom Panel)
// ============================================
const PanelModule = {
    init() {
        console.log('[PanelModule] Initializing...');

        const toggleBtn = document.getElementById('toggleTableBtn');
        const panel = document.getElementById('bottom-panel');

        if (!toggleBtn || !panel) {
            console.error('[PanelModule] Toggle button or panel not found!');
            return;
        }

        toggleBtn.addEventListener('click', () => {
            AppState.toggleTable();
        });

        // Subscribe to state changes
        AppState.subscribe(state => {
            if (state.isTableVisible) {
                panel.classList.remove('collapsed');
                console.log('[PanelModule] Panel expanded');
            } else {
                panel.classList.add('collapsed');
                console.log('[PanelModule] Panel collapsed');
            }
        });

        console.log('[PanelModule] Ready');
    }
};

// ============================================
//  METRICS MODULE (Compact Metrics in Panel Header)
// ============================================
const MetricsModule = {
    init() {
        console.log('[MetricsModule] Initializing...');

        const metricsBar = document.getElementById('metricsBar');

        if (!metricsBar) {
            console.error('[MetricsModule] Metrics bar not found!');
            return;
        }

        // Create metric elements
        const metrics = [
            { id: 'metric-total', label: 'Total', class: '' },
            { id: 'metric-released', label: 'Released', class: 'released' },
            { id: 'metric-assigned', label: 'Assigned', class: 'assigned' },
            { id: 'metric-in-progress', label: 'In Progress', class: 'in-progress' },
            { id: 'metric-staged', label: 'Staged', class: 'staged' }
        ];

        metricsBar.innerHTML = '';

        metrics.forEach(m => {
            const div = document.createElement('div');
            div.className = `metric-compact ${m.class}`;
            div.innerHTML = `
                <div class="label">${m.label}</div>
                <div class="value" id="${m.id}">0</div>
            `;
            metricsBar.appendChild(div);
        });

        console.log('[MetricsModule] Ready');
    }
};

// ============================================
//  INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('===========================================');
    console.log('  Gemelo Digital - Web Simulator v2.0');
    console.log('  Modular Architecture Initialized');
    console.log('===========================================');

    // Initialize all modules
    TableModule.init();
    CanvasModule.init();
    ControlsModule.init();
    ResizeModule.init();
    PanelModule.init();
    MetricsModule.init();

    // Load layout
    try {
        const response = await fetch('/api/layout');
        const layout = await response.json();
        AppState.setLayout(layout);
        console.log('[Main] Layout loaded:', layout);

        // Redimensionar canvas inicial para que se ajuste al contenedor
        // Pequeño delay para asegurar que el DOM esté completamente renderizado
        setTimeout(() => {
            CanvasModule.resize();
            console.log('[Main] Initial canvas resize completed');
        }, 100);
    } catch (error) {
        console.error('[Main] Error loading layout:', error);
    }

    // Load initial state at t=0
    await ControlsModule.seekTo(0);

    console.log('[Main] System ready');
});
