# DHARA predictive-data contract

The live web app ships with a **prototype calibration model** so the demo works immediately. It must not be presented as field-validated accuracy.

For the research/SIH version, create `training_data.csv` using India-specific observations:

- IMD rainfall: 1h/3h/6h/24h/72h windows
- MOSDAC/ISRO soil wetness: current value + change
- DEM-derived elevation, slope, TWI and flow accumulation
- Bhuvan/NRSC river/drainage, LULC and flood-hazard layers
- GSI/Bhusanket historical landslide inventory and verified flood event labels
- Optional IoT telemetry: rain gauge, soil moisture and water level

Target: `event=1` when a verified flash-flood/trigger event occurs in the next 6 hours for the grid cell; otherwise `0`.

**Validation:** use a chronological split (past -> future), report precision, recall, F1, ROC-AUC, false-alarm rate and warning lead time. Do not randomly mix observations from the same event across train/test.
