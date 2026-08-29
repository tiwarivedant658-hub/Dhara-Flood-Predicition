# DATA_PROVENANCE.md

Before claiming validation results, record:

- source portal and exact dataset/product name
- download date
- temporal coverage
- spatial resolution/grid
- processing/reprojection/resampling steps
- license/access conditions
- event-label definition
- train/test chronological cutoff
- feature list and model hyperparameters
- generated `validation_metrics.json`

The application exposes `model_source`:
- `validated_historical` = a locally trained artifact exists
- `prototype_synthetic` = no historical artifact exists and the demo fallback is used

Never present prototype-synthetic metrics as field accuracy.
