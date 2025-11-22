// Constants
const TILE_SIZE = 20; // Pixels per tile
const AGENT_RADIUS = 8;
const COLORS = {
    WALL: '#555555',
    FLOOR: '#252525',
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

// State
let canvas, ctx;
let layout = null;
let isPlaying = false;
let currentTime = 0;
let maxTime = 100;
let playbackSpeed = 1;
let animationFrameId;
let lastFrameTime = 0;

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    canvas = document.getElementById('simCanvas');
    ctx = canvas.getContext('2d');

    // Event Listeners
    document.getElementById('play-pause-btn').addEventListener('click', togglePlay);
    document.getElementById('time-slider').addEventListener('input', handleSeek);
    document.getElementById('speed-select').addEventListener('change', (e) => playbackSpeed = parseFloat(e.target.value));

    // Load Layout
    await loadLayout();

    // Start Loop
    requestAnimationFrame(gameLoop);
});

async function loadLayout() {
    try {
        const response = await fetch('/api/layout');
        layout = await response.json();

        // Resize canvas
        canvas.width = layout.width * TILE_SIZE;
        canvas.height = layout.height * TILE_SIZE;

        console.log("Layout loaded:", layout);
        renderMap();
    } catch (error) {
        console.error("Error loading layout:", error);
    }
}

async function fetchState(time) {
    try {
        const response = await fetch(`/api/state?t=${time}`);
        const state = await response.json();

        // Update Max Time
        maxTime = state.max_time;
        document.getElementById('time-slider').max = maxTime;
        document.getElementById('max-time').textContent = formatTime(maxTime);

        return state;
    } catch (error) {
        console.error("Error fetching state:", error);
        return null;
    }
}

async function fetchAndUpdateMetrics(time) {
    try {
        const response = await fetch(`/api/metrics?t=${time}`);
        const metrics = await response.json();

        // Update Work Orders metrics with exact state names
        document.getElementById('metric-wo-total').textContent = metrics.work_orders.total;
        document.getElementById('metric-wo-staged').textContent = metrics.work_orders.staged;
        document.getElementById('metric-wo-picked').textContent = metrics.work_orders.picked;
        document.getElementById('metric-wo-progress').textContent = metrics.work_orders.in_progress;
        document.getElementById('metric-wo-assigned').textContent = metrics.work_orders.assigned;
        document.getElementById('metric-wo-released').textContent = metrics.work_orders.released;

        // Update Performance metrics
        document.getElementById('metric-throughput').textContent = metrics.performance.throughput_per_minute.toFixed(2);
        document.getElementById('metric-avg-time').textContent = metrics.performance.avg_time_per_wo.toFixed(2);

        // Update Agents metrics
        document.getElementById('metric-agents-active').textContent = metrics.agents.active;
        document.getElementById('metric-agents-idle').textContent = metrics.agents.idle;
    } catch (error) {
        console.error("Error fetching metrics:", error);
    }
}

function togglePlay() {
    isPlaying = !isPlaying;
    document.getElementById('play-pause-btn').textContent = isPlaying ? "Pause" : "Play";
    lastFrameTime = performance.now();
}

function handleSeek(e) {
    currentTime = parseFloat(e.target.value);
    updateUI(currentTime);
    // Force a render update immediately
    fetchState(currentTime).then(state => {
        if (state) {
            renderScene(state);
            updateSidebar(state);
        }
    });
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updateUI(time) {
    document.getElementById('current-time').textContent = formatTime(time);
    document.getElementById('time-slider').value = time;
}

async function gameLoop(timestamp) {
    const deltaTime = (timestamp - lastFrameTime) / 1000; // Seconds
    lastFrameTime = timestamp;

    if (isPlaying) {
        currentTime += deltaTime * playbackSpeed;
        if (currentTime > maxTime) {
            currentTime = maxTime;
            isPlaying = false;
            document.getElementById('play-pause-btn').textContent = "Play";
        }
        updateUI(currentTime);
    }

    // Fetch state for current time
    const state = await fetchState(currentTime);

    if (state) {
        renderScene(state);
        updateSidebar(state);
    }

    requestAnimationFrame(gameLoop);
}

function renderMap() {
    if (!layout) return;

    ctx.fillStyle = COLORS.FLOOR;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    layout.layers.forEach(layer => {
        if (layer.tiles) {
            layer.tiles.forEach(tile => {
                const x = tile.x * TILE_SIZE;
                const y = tile.y * TILE_SIZE;
                const gid = tile.gid;

                if (gid === 4) {
                    ctx.fillStyle = COLORS.WALL;
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                } else if (gid === 5) {
                    ctx.fillStyle = COLORS.ZONE_PICKING;
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                } else if (gid === 6) {
                    ctx.fillStyle = COLORS.ZONE_STAGING;
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                } else if (gid === 1) {
                    ctx.fillStyle = 'rgba(200, 200, 255, 0.3)';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                } else if (gid === 2) {
                    ctx.fillStyle = 'rgba(255, 200, 200, 0.3)';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
                }
            });
        }
    });
}

function renderScene(state) {
    renderMap();

    // Draw Agents with status-based colors
    Object.entries(state.agents).forEach(([id, agent]) => {
        const [gridX, gridY] = agent.position;
        const screenX = gridX * TILE_SIZE + TILE_SIZE / 2;
        const screenY = gridY * TILE_SIZE + TILE_SIZE / 2;

        // Get agent color based on type and status
        const agentType = agent.type.includes('Forklift') ? 'Forklift' : 'GroundOperator';
        const colorScheme = AGENT_COLORS[agentType];
        const agentColor = colorScheme[agent.status] || colorScheme.base;

        ctx.beginPath();
        ctx.arc(screenX, screenY, AGENT_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = agentColor;
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Agent ID Label
        ctx.fillStyle = '#fff';
        ctx.font = '10px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(id.split('-').pop(), screenX, screenY - 12);
    });
}

function updateSidebar(state) {
    const list = document.getElementById('agents-list');
    list.innerHTML = '';

    Object.entries(state.agents).forEach(([id, agent]) => {
        const div = document.createElement('div');
        div.className = 'agent-list-item';

        const statusClass = agent.status === 'idle' ? 'status-idle' :
            agent.status === 'moving' ? 'status-moving' :
                agent.status === 'picking' ? 'status-picking' :
                    agent.status === 'unloading' ? 'status-unloading' : 'status-idle';

        div.innerHTML = `
            <span class="agent-status ${statusClass}"></span>
            <strong>${id.split('-').pop()}</strong>
            <div style="font-size: 0.8em; color: #aaa; margin-left: 16px;">
                ${agent.status} (${Math.round(agent.position[0])}, ${Math.round(agent.position[1])})
            </div>
        `;
        list.appendChild(div);
    });

    // Fetch and update metrics
    fetchAndUpdateMetrics(currentTime);
}
