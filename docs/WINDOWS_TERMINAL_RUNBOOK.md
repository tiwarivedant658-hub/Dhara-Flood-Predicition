# WINDOWS TERMINAL — RUN DHARA + TRAIN DHARA

Run these commands **one at a time**. Wait for each command to finish.

## A. Start the web app (demo/live mode)

### 1. Go to the project
```powershell
cd path\to\flash-flood-prediction-sih192
```

### 2. Create virtual environment
```powershell
python -m venv .venv
```

### 3. Activate it
```powershell
.venv\Scripts\activate
```

If PowerShell blocks activation, use:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
then:
```powershell
.venv\Scripts\activate
```

### 4. Install packages
```powershell
python -m pip install --upgrade pip
```
then:
```powershell
pip install -r requirements.txt
```

### 5. Create environment file
```powershell
copy .env.example .env
```

### 6. Start DHARA
```powershell
python run.py
```

### 7. Open the browser
Go to:
`http://localhost:5000`

Stop the server with `Ctrl+C`.

---

## B. Train DHARA using the real historical data

Do this only after you have downloaded/exported the source datasets.

### 8. Create the raw-data folders
```powershell
mkdir data\research\raw
```

### 9. Put these normalized files into that folder
- `imd.csv`
- `mosdac.csv`
- `terrain.csv`
- `bhuvan.csv`
- `gsi.csv`

Use the headers in `data\research\templates\`.

### 10. Build the labelled dataset
```powershell
python scripts\build_dataset.py --imd data\research\raw\imd.csv --mosdac data\research\raw\mosdac.csv --terrain data\research\raw\terrain.csv --bhuvan data\research\raw\bhuvan.csv --gsi data\research\raw\gsi.csv
```

You should see something like:
```text
Saved XXXX labelled rows -> data/research/training_data.csv
Positive events: XXX (X.XX%)
```

The numbers above are examples only. Your terminal will print the real numbers.

### 11. Train + chronological validation
```powershell
python scripts\train_model.py
```

This prints the real held-out:
- Precision
- Recall
- F1
- ROC-AUC
- PR-AUC
- False Alarm Rate
- Warning Lead Time

### 12. Inspect the metrics
```powershell
type data\research\validation_metrics.json
```

### 13. Restart DHARA
If the server is running, press:
```text
Ctrl+C
```

Then:
```powershell
python run.py
```

The API now uses the validated artifact automatically.

### 14. Check the model source
Open:
`http://localhost:5000/api/prediction/<location_id>`

The JSON should contain:
```json
"model_source": "validated_historical"
```

If it says:
```json
"model_source": "prototype_synthetic"
```
the historical model has not been trained/installed yet.

## C. Fast health check

In another terminal while the server is running:
```powershell
curl http://localhost:5000/api/health
```

Expected:
```json
{"status":"ok","locations_loaded":25}
```

## D. Important

Do not claim the model is "90% accurate" or similar unless that number is present in
`validation_metrics.json` from the chronological held-out test set.

The project is designed to fail safely when there are insufficient real labels rather
than manufacture a score.

## Historical validation pipeline (v3)
1. Put normalized IMD, MOSDAC, terrain, Bhuvan, and verified flood events in `data\research\raw`.
2. Run `python scripts\build_dataset.py --imd data\research\raw\imd.csv --mosdac data\research\raw\mosdac.csv --terrain data\research\raw\terrain.csv --bhuvan data\research\raw\bhuvan.csv --events data\research\raw\events.csv`.
3. Run `python scripts\train_model.py`.
4. Read `data\research\validation_metrics.json`.
5. Do not report metrics until real historical data are present.
