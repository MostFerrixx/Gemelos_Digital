// =============================================
// Digital Twin Warehouse - Dashboard Web App
// Main JavaScript - Matches PyQt6 WorkOrder Dashboard functionality
// =============================================

// ========== Global State ==========
const state = {
    workOrders: new Map(),        // Map<wo_id, wo_data>
    currentTime: 0,
    maxTime: 0,
    sortColumn: 'id',
    sortDirection: 'asc',
    isPlaying: false,
    playbackSpeed: 1.0,
    playInterval: null,
    lastUpdateTime: 0
};

// ========== Column Configuration (18 columns, matching PyQt6) ==========
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

// ========== Data Fetching (REST API) ==========
async function fetchStateAtTime(timestamp) {
    try {
        const response = await fetch(`/api/state?t=${timestamp}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('[API] Error fetching state:', error);
        return null;
    }
}

async function fetchMetricsAtTime(timestamp) {
    try {
        const response = await fetch(`/api/metrics?t=${timestamp}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('[API] Error fetching metrics:', error);
        return null;
    }
}

// ========== State Update Handler ==========
async function updateStateAtTime(timestamp) {
    const stateData = await fetchStateAtTime(timestamp);

    if (!stateData) {
        console.error('[State] Failed to fetch state data');
        return;
    }

    // Update global state
    state.currentTime = timestamp;
    state.maxTime = stateData.max_time || state.maxTime;

    // Clear and rebuild work orders map
    state.workOrders.clear();

    if (stateData.work_orders) {
        Object.entries(stateData.work_orders).forEach(([id, wo]) => {
            state.workOrders.set(id, wo);
        });
    }

    // Update UI
    renderTable();
    updateTimeDisplay(timestamp);

    // Update metrics
    const metrics = await fetchMetricsAtTime(timestamp);
    if (metrics) {
        updateMetrics(metrics);
    }

    console.log(`[State] Updated to t=${timestamp.toFixed(2)}s, WOs: ${state.workOrders.size}`);
}

// ========== Table Rendering ==========
function renderTable() {
    const tbody = document.querySelector('#workOrderTable tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (state.workOrders.size === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = COLUMNS.length;
        td.textContent = 'No work orders available';
        td.style.textAlign = 'center';
        td.style.padding = '40px';
        td.style.color = 'var(--text-secondary)';
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    // Sort work orders
    const sortedWOs = Array.from(state.workOrders.values()).sort((a, b) => {
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

    // Render rows
    sortedWOs.forEach(wo => {
        const row = createTableRow(wo);
        tbody.appendChild(row);
    });
}

function createTableRow(wo) {
    const tr = document.createElement('tr');
    tr.dataset.woId = wo.id;

    // Apply status class for color coding (CRITICAL - matches PyQt6)
    const status = wo.status || 'released';
    tr.classList.add(`status-${status}`);

    COLUMNS.forEach(col => {
        const td = document.createElement('td');
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
        tr.appendChild(td);
    });

    return tr;
}

// ========== Table Sorting ==========
function setupSorting() {
    const headers = document.querySelectorAll('#workOrderTable th');

    headers.forEach((th, idx) => {
        th.addEventListener('click', () => {
            const column = COLUMNS[idx].key;

            // Toggle direction if same column, else default to asc
            if (state.sortColumn === column) {
                state.sortDirection = state.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                state.sortColumn = column;
                state.sortDirection = 'asc';
            }

            // Update UI indicators
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            th.classList.add(`sort-${state.sortDirection}`);

            // Re-render with new sort
            renderTable();
        });
    });
}

// ========== Time Scrubber ==========
function setupTimeScrubber() {
    const slider = document.getElementById('timeSlider');

    if (!slider) return;

    slider.addEventListener('input', async (e) => {
        const targetTime = parseFloat(e.target.value);

        // Stop playback when user seeks manually
        if (state.isPlaying) {
            stopPlayback();
        }

        await updateStateAtTime(targetTime);
    });
}

function updateTimeDisplay(timestamp) {
    const currentTimeEl = document.getElementById('currentTime');
    const maxTimeEl = document.getElementById('maxTime');
    const slider = document.getElementById('timeSlider');

    if (currentTimeEl) {
        currentTimeEl.textContent = timestamp.toFixed(2) + 's';
    }

    if (maxTimeEl && state.maxTime > 0) {
        maxTimeEl.textContent = state.maxTime.toFixed(2) + 's';
    }

    if (slider) {
        slider.max = state.maxTime;
        slider.value = timestamp;
    }
}

// ========== Playback Controls ==========
function setupPlaybackControls() {
    const playBtn = document.getElementById('playBtn');
    const pauseBtn = document.getElementById('pauseBtn');
    const resetBtn = document.getElementById('resetBtn');

    if (playBtn) {
        playBtn.addEventListener('click', startPlayback);
    }

    if (pauseBtn) {
        pauseBtn.addEventListener('click', stopPlayback);
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', resetToStart);
    }
}

function startPlayback() {
    if (state.isPlaying) return;

    state.isPlaying = true;
    state.lastUpdateTime = Date.now();

    const playBtn = document.getElementById('playBtn');
    const pauseBtn = document.getElementById('pauseBtn');

    if (playBtn) playBtn.disabled = true;
    if (pauseBtn) pauseBtn.disabled = false;

    // Update every 100ms
    state.playInterval = setInterval(async () => {
        const now = Date.now();
        const deltaMs = now - state.lastUpdateTime;
        state.lastUpdateTime = now;

        // Advance simulation time based on playback speed
        const deltaTime = (deltaMs / 1000) * state.playbackSpeed;
        let newTime = state.currentTime + deltaTime;

        // Loop at end
        if (newTime >= state.maxTime) {
            newTime = state.maxTime;
            stopPlayback();
        }

        await updateStateAtTime(newTime);
    }, 100);

    console.log('[Playback] Started at speed', state.playbackSpeed);
}

function stopPlayback() {
    if (!state.isPlaying) return;

    state.isPlaying = false;

    if (state.playInterval) {
        clearInterval(state.playInterval);
        state.playInterval = null;
    }

    const playBtn = document.getElementById('playBtn');
    const pauseBtn = document.getElementById('pauseBtn');

    if (playBtn) playBtn.disabled = false;
    if (pauseBtn) pauseBtn.disabled = true;

    console.log('[Playback] Stopped');
}

async function resetToStart() {
    stopPlayback();
    await updateStateAtTime(0);
}

// ========== Metrics Display ==========
function updateMetrics(metrics) {
    if (!metrics) return;

    const woMetrics = metrics.work_orders || {};
    const perfMetrics = metrics.performance || {};

    // Update metric values
    setMetricValue('metric-total', woMetrics.total || 0);
    setMetricValue('metric-released', woMetrics.released || 0);
    setMetricValue('metric-assigned', woMetrics.assigned || 0);
    setMetricValue('metric-in-progress', woMetrics.in_progress || 0);
    setMetricValue('metric-staged', woMetrics.staged || 0);
}

function setMetricValue(elementId, value) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = value;
    }
}

// ========== Connection Status ==========
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connectionIndicator');
    const text = document.getElementById('connectionText');

    if (indicator) {
        if (connected) {
            indicator.classList.add('connected');
        } else {
            indicator.classList.remove('connected');
        }
    }

    if (text) {
        text.textContent = connected ? 'Connected' : 'Disconnected';
    }
}

// ========== Initialization ==========
async function initializeDashboard() {
    console.log('[Dashboard] Initializing...');

    // Setup table headers
    const thead = document.querySelector('#workOrderTable thead tr');
    if (thead) {
        thead.innerHTML = '';
        COLUMNS.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col.header;
            th.style.width = col.width;
            thead.appendChild(th);
        });
    }

    // Setup event handlers
    setupSorting();
    setupTimeScrubber();
    setupPlaybackControls();

    // Mark as connected (using REST API, not WebSocket for now)
    updateConnectionStatus(true);

    // Load initial state at t=0
    await updateStateAtTime(0);

    console.log('[Dashboard] Ready');
}

// ========== Entry Point ==
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
});
