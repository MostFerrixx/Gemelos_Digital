# examples/ — configs y datos de demostracion

Archivos ESTABLES (trackeados en git, fuera de la purga automatica de
`temp_web/`) para reproducir features con un comando. No son datos canonicos
del motor (eso vive en la raiz y en `layouts/`).

## Demo cross-docking (INIT-7 F5b)

Un pedido insaciable de SKU029 (5000 u, excede cualquier stock) genera un
backorder en la allocation t=0; el camion IN-001 del ASN canonico trae 24 u
de ese SKU y el cross-dock las rescata en la misma corrida (pick dinamico
WO-XD desde la ubicacion recien abastecida).

```
WAREHOUSE_SEED=42 python entry_points/run_generate_replay.py --config "examples/config_cross_dock_demo.json"
```

Que mirar: consola `[INBOUND] F5b: rescate cross-dock de 24u SKU029...`;
en la metadata del .jsonl `service_level.fill_rate_effective_pct` >
`fill_rate_pct`; en el visor, panel "Recepcion (Inbound)" -> grupo
"Cross-docking".
