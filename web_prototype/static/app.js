// Constants
const TILE_SIZE = 20; // Pixels per tile
const AGENT_RADIUS = 8;
const COLORS = {
    WALL: '#555555',
    FLOOR: '#1a1f26', // Matches body background
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

// Unique color palette for each operator (matching desktop renderer.py)
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

// Hash function to get unique color for each agent
function getOperatorColor(agentId) {
    // Simple hash function
    let hash = 0;
    for (let i = 0; i < agentId.length; i++) {
        hash = ((hash << 5) - hash) + agentId.charCodeAt(i);
        hash = hash & hash; // Convert to 32bit integer
    }
    const index = Math.abs(hash) % OPERATOR_COLOR_PALETTE.length;
    const [r, g, b] = OPERATOR_COLOR_PALETTE[index];
    return `rgb(${r}, ${g}, ${b})`;
}


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

                // GID mapping based on WH1.tmx:
                // 1 = floor, 2 = racks, 3 = picking, 4 = parking, 5 = depot, 6 = inbound

                if (gid === 1) {
                    // Floor - Concrete texture with grid lines
                    ctx.fillStyle = '#2a2e35';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    // Grid pattern
                    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
                    ctx.lineWidth = 0.5;
                    ctx.strokeRect(x, y, TILE_SIZE, TILE_SIZE);

                } else if (gid === 2) {
                    // Racks - Metallic structure
                    const gradient = ctx.createLinearGradient(x, y, x + TILE_SIZE, y + TILE_SIZE);
                    gradient.addColorStop(0, '#4a4a4a');
                    gradient.addColorStop(0.5, '#5a5a5a');
                    gradient.addColorStop(1, '#3a3a3a');
                    ctx.fillStyle = gradient;
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    // Rack shelves (horizontal lines)
                    ctx.strokeStyle = '#6a6a6a';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(x, y + TILE_SIZE * 0.25);
                    ctx.lineTo(x + TILE_SIZE, y + TILE_SIZE * 0.25);
                    ctx.moveTo(x, y + TILE_SIZE * 0.5);
                    ctx.lineTo(x + TILE_SIZE, y + TILE_SIZE * 0.5);
                    ctx.moveTo(x, y + TILE_SIZE * 0.75);
                    ctx.lineTo(x + TILE_SIZE, y + TILE_SIZE * 0.75);
                    ctx.stroke();

                    // Vertical supports
                    ctx.strokeStyle = '#7a7a7a';
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();
                    ctx.moveTo(x + TILE_SIZE * 0.2, y);
                    ctx.lineTo(x + TILE_SIZE * 0.2, y + TILE_SIZE);
                    ctx.moveTo(x + TILE_SIZE * 0.8, y);
                    ctx.lineTo(x + TILE_SIZE * 0.8, y + TILE_SIZE);
                    ctx.stroke();

                    // Shadow for depth
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
                    ctx.fillRect(x + TILE_SIZE - 3, y + 2, 3, TILE_SIZE - 2);

                } else if (gid === 3) {
                    // Picking locations - Yellow striped zone
                    ctx.fillStyle = '#2a2e35';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    // Yellow warning stripes
                    ctx.fillStyle = 'rgba(255, 200, 0, 0.25)';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    // Diagonal stripes
                    ctx.strokeStyle = 'rgba(255, 200, 0, 0.4)';
                    ctx.lineWidth = 2;
                    for (let i = -TILE_SIZE; i < TILE_SIZE * 2; i += 6) {
                        ctx.beginPath();
                        ctx.moveTo(x + i, y);
                        ctx.lineTo(x + i + TILE_SIZE, y + TILE_SIZE);
                        ctx.stroke();
                    }

                    // Border
                    ctx.strokeStyle = 'rgba(255, 200, 0, 0.6)';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2);

                } else if (gid === 4) {
                    // Parking/Start - Blue zone with grid
                    ctx.fillStyle = '#1e2530';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    ctx.fillStyle = 'rgba(100, 150, 255, 0.2)';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    // Parking grid
                    ctx.strokeStyle = 'rgba(100, 150, 255, 0.4)';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4);

                    // Dashed center line
                    ctx.setLineDash([3, 3]);
                    ctx.beginPath();
                    ctx.moveTo(x + TILE_SIZE / 2, y);
                    ctx.lineTo(x + TILE_SIZE / 2, y + TILE_SIZE);
                    ctx.stroke();
                    ctx.setLineDash([]);

                } else if (gid === 5) {
                    // Depot/Outbound - Green staging area
                    ctx.fillStyle = '#1e2e25';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    ctx.fillStyle = 'rgba(0, 200, 100, 0.2)';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    // Checkered pattern for staging
                    const checkerSize = TILE_SIZE / 4;
                    for (let cy = 0; cy < 4; cy++) {
                        for (let cx = 0; cx < 4; cx++) {
                            if ((cx + cy) % 2 === 0) {
                                ctx.fillStyle = 'rgba(0, 200, 100, 0.1)';
                                ctx.fillRect(x + cx * checkerSize, y + cy * checkerSize, checkerSize, checkerSize);
                            }
                        }
                    }

                    // Border
                    ctx.strokeStyle = 'rgba(0, 200, 100, 0.5)';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2);

                } else if (gid === 6) {
                    // Inbound - Orange receiving area
                    ctx.fillStyle = '#2e2520';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    ctx.fillStyle = 'rgba(255, 150, 50, 0.2)';
                    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

                    // Loading dock stripes
                    ctx.strokeStyle = 'rgba(255, 150, 50, 0.4)';
                    ctx.lineWidth = 2;
                    for (let i = 0; i < TILE_SIZE; i += 5) {
                        ctx.beginPath();
                        ctx.moveTo(x, y + i);
                        ctx.lineTo(x + TILE_SIZE, y + i);
                        ctx.stroke();
                    }

                    // Border
                    ctx.strokeStyle = 'rgba(255, 150, 50, 0.6)';
                    ctx.lineWidth = 1.5;
                    ctx.strokeRect(x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2);
                }
            });
        }
    });
}


function renderPickingNodes(state) {
    /**
     * Renders picking location nodes for each operator's tour.
     * Shows accumulated WO count at each location.
     * Matching desktop implementation from renderer.py renderizar_rutas_tours
     */
    if (!state || !state.agents) return;

    Object.entries(state.agents).forEach(([agentId, agent]) => {
        const assignedWOs = agent.work_orders_asignadas || [];

        // Skip if no assigned work orders
        if (assignedWOs.length === 0) return;

        // Skip if agent is idle (not actively working on tour)
        const status = agent.status || 'idle';
        if (status === 'idle' || status === 'completed') return;

        // Group WOs by location and calculate accumulated counts
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

        // Convert to array and sort by pick sequence
        const locations = Array.from(locationMap.values())
            .sort((a, b) => a.minSequence - b.minSequence);

        // Calculate accumulated counts (from current location forward)
        const locationsWithAccumulated = [];
        for (let i = 0; i < locations.length; i++) {
            const accumulated = locations.slice(0, i + 1)
                .reduce((sum, loc) => sum + loc.woCount, 0);
            locationsWithAccumulated.push({
                ...locations[i],
                accumulated
            });
        }

        // Get unique color for this operator
        const operatorColor = getOperatorColor(agentId);

        // Draw picking nodes
        locationsWithAccumulated.forEach((location, idx) => {
            const [px, py] = location.pos;
            const woCount = location.accumulated;

            // Determine if current node (first few are more prominent)
            const isCurrent = idx < 2;

            // Fixed radius as requested (very small)
            const radius = 7;

            // Adjust color brightness for current node
            let nodeColor = operatorColor;
            if (isCurrent) {
                // Make brighter for current node
                const rgb = operatorColor.match(/\d+/g).map(Number);
                nodeColor = `rgb(${Math.min(255, rgb[0] + 50)}, ${Math.min(255, rgb[1] + 50)}, ${Math.min(255, rgb[2] + 50)})`;
            }

            // Draw circle
            ctx.beginPath();
            ctx.arc(px, py, radius, 0, Math.PI * 2);
            ctx.fillStyle = nodeColor;
            ctx.fill();

            // Border
            ctx.strokeStyle = '#000';
            ctx.lineWidth = isCurrent ? 2 : 1;
            ctx.stroke();

            // Draw WO count text
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 10px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            // No background box for very small nodes to keep it clean
            // Draw text directly
            ctx.strokeText(woCount.toString(), px, py); // Small stroke for contrast
            ctx.fillText(woCount.toString(), px, py);
        });
    });
}


function renderScene(state) {
    renderMap();

    // Draw picking nodes BEFORE agents so agents appear on top
    renderPickingNodes(state);

    // Draw Agents as Person Icons (User Requested Style)
    Object.entries(state.agents).forEach(([id, agent]) => {
        const [gridX, gridY] = agent.position;
        const screenX = gridX * TILE_SIZE + TILE_SIZE / 2;
        const screenY = gridY * TILE_SIZE + TILE_SIZE / 2;

        // Get agent color based on type and status
        const agentType = agent.type.includes('Forklift') ? 'Forklift' : 'GroundOperator';
        const colorScheme = AGENT_COLORS[agentType];
        const agentColor = colorScheme[agent.status] || colorScheme.base;

        ctx.save();
        ctx.translate(screenX, screenY);

        // Draw Person Icon (Head + Body)
        // Head (Circle)
        ctx.beginPath();
        ctx.arc(0, -7, 5, 0, Math.PI * 2);
        ctx.fillStyle = agentColor;
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Body (Rounded shape/Shoulders)
        ctx.beginPath();
        // Draw a semi-circle for the body
        ctx.arc(0, 7, 8, Math.PI, 0);
        ctx.lineTo(8, 7); // Close the shape
        ctx.fillStyle = agentColor;
        ctx.fill();
        ctx.stroke();

        ctx.restore();

        // Agent ID Label
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        // Background for label
        const label = id.split('-').pop();
        const metrics = ctx.measureText(label);
        const padding = 3;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
        ctx.fillRect(
            screenX - metrics.width / 2 - padding,
            screenY + 16,
            metrics.width + padding * 2,
            14
        );

        // Label text
        ctx.fillStyle = '#fff';
        ctx.fillText(label, screenX, screenY + 18);
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
            <div class="agent-info">
                <div class="agent-name">${id.split('-').pop()}</div>
                <div class="agent-details">${agent.status} · (${Math.round(agent.position[0])}, ${Math.round(agent.position[1])})</div>
            </div>
        `;
        list.appendChild(div);
    });

    // Fetch and update metrics
    fetchAndUpdateMetrics(currentTime);
}

