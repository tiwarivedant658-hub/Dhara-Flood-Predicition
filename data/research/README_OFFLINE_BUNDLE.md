# DHARA Offline ML Bundle

Everything needed for an offline demonstration is bundled here: source-style CSVs, labelled training data, a SQLite database, a trained Random Forest artifact, and validation metrics.

**Data disclaimer:** the bundled IMD/MOSDAC/Bhuvan/GSI-style CSVs are SYNTHETIC prototype data. They are included so the project can run and train without external downloads. They must not be represented as official observations or as operational validation. For SIH final claims, replace them with verified historical observations and rerun the pipeline.

## Commands
```cmd
.venv\Scripts\activate
python scripts\build_dataset.py --imd data\research\raw\imd.csv --mosdac data\research\raw\mosdac.csv --terrain data\research\raw\terrain.csv --bhuvan data\research\raw\bhuvan.csv --events data\research\raw\events.csv
python scripts\train_model.py
python run.py
```
