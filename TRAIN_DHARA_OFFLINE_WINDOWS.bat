@echo off
cd /d "%~dp0"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python scripts\build_dataset.py --imd data\research\raw\imd.csv --mosdac data\research\raw\mosdac.csv --terrain data\research\raw\terrain.csv --bhuvan data\research\raw\bhuvan.csv --events data\research\raw\events.csv
python scripts\train_model.py
pause
