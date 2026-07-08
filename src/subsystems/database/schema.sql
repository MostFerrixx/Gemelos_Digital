-- ================================================================
-- WAREHOUSE DATABASE SCHEMA
-- Digital Twin Warehouse Simulator
-- Version: 1.0
-- 
-- Single Source of Truth for LOGICAL warehouse data.
-- Physical geometry (coordinates) comes from TMX map files.
-- ================================================================

-- Schema version tracking for migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now'))
);

-- Insert initial version (ignore if exists)
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

-- ================================================================
-- SKU CATALOG (Master data - changes rarely)
-- ================================================================
CREATE TABLE IF NOT EXISTS sku_catalog (
    sku_code TEXT PRIMARY KEY,                    -- e.g., 'SKU029'
    description TEXT,                              -- Human-readable name
    volume_m3 REAL NOT NULL DEFAULT 0.01,         -- Volume in cubic meters
    weight_kg REAL,                                -- Weight in kilograms
    category TEXT DEFAULT 'GENERAL',              -- 'FRAGIL', 'HAZMAT', 'REFRIGERADO'
    equipment_required TEXT DEFAULT 'GroundOperator',  -- Agent type needed
    created_at TEXT DEFAULT (datetime('now'))
);

-- ================================================================
-- LOCATIONS (Logical identifiers - NO coordinates!)
-- Coordinates are resolved at runtime via TMX map
-- ================================================================
CREATE TABLE IF NOT EXISTS locations (
    location_id TEXT PRIMARY KEY,                 -- e.g., 'R-105', 'LOC-001'
    location_type TEXT NOT NULL DEFAULT 'PICKING', -- 'PICKING', 'STAGING_IN', 'STAGING_OUT'
    work_area TEXT NOT NULL DEFAULT 'Area_Ground', -- e.g., 'Area_Ground', 'Area_Mezzanine'
    work_group TEXT NOT NULL DEFAULT 'WG_Default', -- e.g., 'WG_A', 'WG_B'
    pick_sequence INTEGER,                        -- Order in master plan (for PICKING type)
    equipment_required TEXT DEFAULT 'GroundOperator', -- Agent type for this location
    capacity INTEGER DEFAULT 100,                 -- Max units this location can hold
    -- Temporary: store coordinates during transition period
    -- These will be deprecated once TMX integration is complete
    legacy_x INTEGER,
    legacy_y INTEGER
);

-- Unique pick_sequence (allow NULL for non-picking locations)
CREATE UNIQUE INDEX IF NOT EXISTS idx_locations_sequence 
    ON locations(pick_sequence) WHERE pick_sequence IS NOT NULL;

-- ================================================================
-- INVENTORY (Runtime state - changes during simulation)
-- ================================================================
CREATE TABLE IF NOT EXISTS inventory (
    location_id TEXT PRIMARY KEY REFERENCES locations(location_id) ON DELETE CASCADE,
    sku_code TEXT NOT NULL REFERENCES sku_catalog(sku_code) ON DELETE CASCADE,
    qty_available INTEGER NOT NULL DEFAULT 0,
    qty_reserved INTEGER NOT NULL DEFAULT 0,      -- Reserved for pending orders
    last_updated REAL,                             -- SimPy timestamp
    CHECK (qty_available >= 0),
    CHECK (qty_reserved >= 0)
);

-- ================================================================
-- ORDERS (For deterministic order mode)
-- ================================================================
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,                    -- e.g., 'ORD-001'
    status TEXT DEFAULT 'PENDING',                -- 'PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'
    priority INTEGER DEFAULT 5,                   -- 1-10, higher = more urgent
    created_at REAL,                               -- SimPy timestamp when created
    completed_at REAL                              -- SimPy timestamp when completed
);

CREATE TABLE IF NOT EXISTS order_lines (
    line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    sku_code TEXT NOT NULL REFERENCES sku_catalog(sku_code) ON DELETE CASCADE,
    qty_requested INTEGER NOT NULL,
    qty_picked INTEGER DEFAULT 0,
    assigned_location_id TEXT REFERENCES locations(location_id),
    CHECK (qty_requested > 0)
);

-- ================================================================
-- STAGING AREAS (Outbound staging locations)
-- ================================================================
CREATE TABLE IF NOT EXISTS staging_areas (
    staging_id INTEGER PRIMARY KEY,               -- e.g., 1, 2, 3...
    staging_type TEXT DEFAULT 'OUTBOUND',         -- 'INBOUND', 'OUTBOUND', 'CROSSDOCK'
    -- Temporary: store coordinates during transition
    legacy_x INTEGER,
    legacy_y INTEGER
);

-- ================================================================
-- INBOUND DOCKS (INIT-7 F0: muelles de recepcion)
-- Tabla propia (no staging_areas): staging_areas tiene PK simple staging_id
-- y una fila INBOUND id=1 pisaria la zona OUTBOUND id=1.
-- ================================================================
CREATE TABLE IF NOT EXISTS inbound_docks (
    dock_id INTEGER PRIMARY KEY,                  -- e.g., 1, 2, 3...
    x INTEGER NOT NULL,
    y INTEGER NOT NULL
);

-- ================================================================
-- PERFORMANCE INDICES
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_locations_type ON locations(location_type);
CREATE INDEX IF NOT EXISTS idx_locations_area ON locations(work_area);
CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory(sku_code);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_lines_order ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_sku ON order_lines(sku_code);

-- ================================================================
-- CONVENIENCE VIEWS
-- ================================================================

-- Full inventory view with all related data
CREATE VIEW IF NOT EXISTS v_inventory_full AS
SELECT 
    i.location_id,
    l.location_type,
    l.work_area,
    l.work_group,
    l.pick_sequence,
    l.legacy_x,
    l.legacy_y,
    i.sku_code,
    s.description AS sku_description,
    s.volume_m3,
    s.equipment_required,
    i.qty_available,
    i.qty_reserved,
    (i.qty_available - i.qty_reserved) AS qty_free
FROM inventory i
JOIN locations l ON i.location_id = l.location_id
JOIN sku_catalog s ON i.sku_code = s.sku_code;

-- Available SKUs view (for order validation)
CREATE VIEW IF NOT EXISTS v_available_skus AS
SELECT DISTINCT 
    s.sku_code,
    s.description,
    s.equipment_required,
    SUM(i.qty_available - i.qty_reserved) AS total_available
FROM sku_catalog s
LEFT JOIN inventory i ON s.sku_code = i.sku_code
GROUP BY s.sku_code;

-- Picking locations ordered by sequence
CREATE VIEW IF NOT EXISTS v_picking_sequence AS
SELECT 
    l.location_id,
    l.pick_sequence,
    l.work_area,
    l.work_group,
    l.equipment_required,
    l.legacy_x,
    l.legacy_y,
    i.sku_code,
    i.qty_available,
    i.qty_reserved
FROM locations l
LEFT JOIN inventory i ON l.location_id = i.location_id
WHERE l.location_type = 'PICKING'
ORDER BY l.pick_sequence;
