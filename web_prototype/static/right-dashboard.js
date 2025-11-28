// ============================================
//  AGENT DASHBOARD MODULE (Dashboard de Agentes)
//  Right-side panel metrics and operators list
// ============================================

(function () {
    'use strict';

    // Module state
    let lastOperatorsData = null;
    let updateInterval = null;

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        console.log('[AgentDashboard] Initializing...');

        // Start updating dashboard every 500ms when playing
        // This syncs with the playback updates
        updateInterval = setInterval(updateDashboard, 500);

        console.log('[AgentDashboard] Ready');
    }

    async function updateDashboard() {
        // Get current time from the time slider
        const timeSlider = document.getElementById('time-slider');
        if (!timeSlider) return;

        const currentTime = parseFloat(timeSlider.value) || 0;

        try {
            const response = await fetch(`/api/snapshot?t=${currentTime}`);
            const data = await response.json();

            if (data.metricas) {
                updateTicker(data.metricas);
                updateCards(data.metricas);
            }

            if (data.state && data.state.agents) {
                updateOperators(data.state.agents);
            }
        } catch (error) {
            // Silently fail - don't spam console during playback
            // console.error('[AgentDashboard] Error:', error);
        }
    }

    function updateTicker(metricas) {
        // Tiempo
        const tiempoEl = document.getElementById('ticker-tiempo');
        if (tiempoEl) {
            tiempoEl.textContent = formatTime(metricas.tiempo || 0);
        }

        // WIP
        const wipEl = document.getElementById('ticker-wip');
        if (wipEl) {
            const completadas = metricas.workorders_completadas || 0;
            const total = metricas.total_wos || 0;
            const wip = metricas.wip || Math.max(total - completadas, 0);
            wipEl.textContent = `${wip}/${total}`;
        }

        // Utilización
        const utilEl = document.getElementById('ticker-util');
        if (utilEl) {
            const util = metricas.utilizacion_promedio || 0;
            utilEl.textContent = util > 0 ? `${util.toFixed(0)}%` : '-';
        }

        // Throughput
        const throughputEl = document.getElementById('ticker-throughput');
        if (throughputEl) {
            const throughput = metricas.throughput_min || 0;
            throughputEl.textContent = throughput > 0 ? `${throughput.toFixed(1)}/min` : '-';
        }
    }

    function updateCards(metricas) {
        // Tiempo Card
        const tiempoCardEl = document.getElementById('card-tiempo');
        if (tiempoCardEl) {
            tiempoCardEl.textContent = formatTime(metricas.tiempo || 0);
        }

        // WorkOrders Card
        const workordersCardEl = document.getElementById('card-workorders');
        if (workordersCardEl) {
            const completadas = metricas.workorders_completadas || 0;
            const total = metricas.total_wos || 0;
            workordersCardEl.textContent = `${completadas} / ${total}`;
        }

        // Tareas Card
        const tareasCardEl = document.getElementById('card-tareas');
        if (tareasCardEl) {
            tareasCardEl.textContent = metricas.tareas_completadas || 0;
        }

        // Progreso Card
        const progresoCardEl = document.getElementById('card-progreso');
        if (progresoCardEl) {
            const completadas = metricas.workorders_completadas || 0;
            const total = metricas.total_wos || 0;
            const progreso = total > 0 ? (completadas / total * 100) : 0;
            progresoCardEl.textContent = `${progreso.toFixed(1)}%`;
        }
    }

    function updateOperators(agents) {
        const operatorsContainer = document.getElementById('operators-list');
        if (!operatorsContainer) return;

        // EFFICIENCY: Only update if data has changed
        const agentsData = JSON.stringify(agents);
        if (lastOperatorsData === agentsData) {
            return; // No changes, avoid DOM manipulation
        }
        lastOperatorsData = agentsData;

        if (!agents || Object.keys(agents).length === 0) {
            operatorsContainer.innerHTML = `
                <div style="text-align: center; padding: 20px; color: var(--dashboard-text-muted);">
                    No hay operarios activos
                </div>
            `;
            return;
        }

        // Clear efficiently
        operatorsContainer.innerHTML = '';

        // Render each operator
        Object.entries(agents).forEach(([agentId, agent]) => {
            const item = createOperatorItem(agentId, agent);
            operatorsContainer.appendChild(item);
        });
    }

    function createOperatorItem(agentId, agent) {
        const div = document.createElement('div');
        div.className = 'operator-item';
        div.dataset.type = agent.type || 'GroundOperator';

        // Work Order actual
        const currentWO = agent.work_orders_asignadas && agent.work_orders_asignadas.length > 0
            ? agent.work_orders_asignadas[0].id
            : null;

        // Ubicación
        const location = agent.position
            ? `(${agent.position[0]}, ${agent.position[1]})`
            : 'Unknown';

        // Estado
        const status = agent.status || 'idle';
        const statusText = getStatusText(status);

        // Carga
        const cargoVolume = agent.cargo_volume || 0;
        const capacity = agent.capacidad || 100;
        const loadPercent = capacity > 0 ? (cargoVolume / capacity * 100) : 0;
        const loadLevel = loadPercent < 30 ? 'low' : loadPercent < 70 ? 'medium' : 'high';

        div.innerHTML = `
            <div class="operator-header">
                <span class="operator-id">${agentId}</span>
                ${currentWO ? `<span class="operator-wo">WO: ${currentWO}</span>` : ''}
            </div>
            <div class="operator-details">
                <span class="operator-status" data-status="${status}">${statusText}</span>
                <span class="operator-location">@${location}</span>
            </div>
            <div class="load-bar-container">
                <div class="load-bar-fill" data-level="${loadLevel}" 
                     style="width: ${loadPercent}%"></div>
                <span class="load-bar-label">${cargoVolume}/${capacity} L</span>
            </div>
        `;

        return div;
    }

    function getStatusText(status) {
        const statusMap = {
            'idle': 'Idle',
            'moving': 'En ruta',
            'working': 'Trabajando',
            'picking': 'Picking',
            'unloading': 'Descargando',
            'lifting': 'Elevando',
            'traveling': 'Viajando'
        };
        return statusMap[status.toLowerCase()] || 'Desconocido';
    }

    function formatTime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
})();
