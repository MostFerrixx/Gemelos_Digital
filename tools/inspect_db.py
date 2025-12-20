#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Inspector - Audit warehouse.db stock levels
Usage: python tools/inspect_db.py
"""

import sqlite3
import os
from pathlib import Path

def main():
    # Find warehouse.db
    project_root = Path(__file__).parent.parent
    db_path = project_root / "warehouse.db"
    
    if not db_path.exists():
        print(f"❌ ERROR: warehouse.db not found at {db_path}")
        return
    
    print(f"📦 Connecting to: {db_path}\n")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query: Stock by SKU (aggregate qty_available across all locations)
    query = """
        SELECT 
            s.sku_code,
            s.description,
            s.volume_m3,
            COALESCE(SUM(i.qty_available), 0) as total_qty_available,
            COUNT(i.location_id) as num_locations
        FROM sku_catalog s
        LEFT JOIN inventory i ON s.sku_code = i.sku_code
        GROUP BY s.sku_code, s.description, s.volume_m3
        ORDER BY s.sku_code
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Print header
    print("=" * 90)
    print(f"{'SKU':<12} {'DESCRIPTION':<30} {'VOL (m³)':<10} {'TOTAL QTY':<12} {'LOCATIONS'}")
    print("=" * 90)
    
    total_skus = 0
    total_qty = 0
    
    for row in rows:
        sku = row['sku_code'] or 'N/A'
        desc = (row['description'] or 'N/A')[:28]
        vol = row['volume_m3'] or 0
        qty = row['total_qty_available'] or 0
        locs = row['num_locations'] or 0
        
        print(f"{sku:<12} {desc:<30} {vol:<10.4f} {qty:<12} {locs}")
        total_skus += 1
        total_qty += qty
    
    print("=" * 90)
    print(f"TOTAL: {total_skus} SKUs, {total_qty} units in inventory")
    print()
    
    # Highlight specific SKUs if they exist
    critical_skus = ['SKU042', 'SKU044', 'SKU046', 'SKU029']
    print("🔍 Critical SKUs for testing:")
    print("-" * 50)
    
    for sku in critical_skus:
        cursor.execute("""
            SELECT 
                s.sku_code, 
                s.description,
                COALESCE(SUM(i.qty_available), 0) as qty
            FROM sku_catalog s
            LEFT JOIN inventory i ON s.sku_code = i.sku_code
            WHERE s.sku_code = ?
        """, (sku,))
        
        result = cursor.fetchone()
        if result and result['sku_code']:
            print(f"  {result['sku_code']}: {result['qty']} units - {result['description']}")
        else:
            print(f"  {sku}: NOT FOUND in database")
    
    print()
    conn.close()

if __name__ == "__main__":
    main()
