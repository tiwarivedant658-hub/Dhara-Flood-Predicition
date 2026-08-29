# ML Model Status

Bundled artifact: `data/research/dhara_model.joblib`

Algorithm: Random Forest classifier.
Validation: chronological 80/20 split.

**Important:** the bundled model is trained on synthetic prototype data so the ZIP is runnable offline. Its metrics are demonstration metrics only. Replace `data/research/raw/*.csv` with verified historical data and rerun `build_dataset.py` and `train_model.py` before presenting metrics as real-world validation.
