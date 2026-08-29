# DHARA historical-data pipeline (IMD + GSI + MOSDAC + Bhuvan)

This SIH build is wired for **real Indian historical observations**, not synthetic
accuracy claims. The ZIP intentionally does **not** bundle scraped government data:
several datasets require portal download/registration and should be stored locally
with their original metadata and attribution.

## Sources

- **IMD**: historical/gridded rainfall or station rainfall. Export to CSV with
  `timestamp,lat,lon,rain_1h,rain_3h,rain_6h,rain_24h,rain_72h`.
- **MOSDAC / ISRO**: Soil Wetness Index / soil moisture. The official MOSDAC
  Soil Moisture product is available from April 2015 onward and is described as
  0–1 dry-to-saturated SWI, with GeoTIFF distribution. Use the product portal and
  convert/extract values to `timestamp,lat,lon,soil_wetness,soil_change`.
- **GSI / Bhusanket**: field-validated landslide inventory and event reports.
  Convert verified events to `event_time,lat,lon,event_type`. For flash-flood
  labels, use verified flood/landslide-trigger evidence and document the label
  definition; do not label an event merely because rainfall was high.
- **Bhuvan / NRSC / ISRO**: historical flood inundation, flood hazard, hydrology,
  river/drainage and other terrain layers. Convert sampled grid/static layers to
  `lat,lon,river_proximity,twi_proxy,historical_hazard`.

## Important label definition

For each observation at time `t` and grid cell `(lat,lon)`:

`event=1` iff a verified event occurs in the same/nearby cell during `[t, t+6h]`.
Otherwise `event=0`.

This is a **future-event label**, so using event data from the same future window
as an input would cause leakage. The builder only uses GSI/Bhuvan event records
to create the target label.

## Required normalized files

Place them under `data/research/raw/`:

- `imd.csv`
- `mosdac.csv`
- `terrain.csv`
- `bhuvan.csv`
- `gsi.csv`

Example headers are provided in `data/research/templates/`.

## Why four sources?

IMD supplies meteorological forcing; MOSDAC supplies satellite-derived soil
wetness; Bhuvan supplies earth-observation/hydrology/flood layers; GSI supplies
verified geohazard/event evidence. The resulting table is a multi-source,
time-indexed labelled dataset suitable for chronological ML validation.

## Official portals

IMD: https://mausam.imd.gov.in/
MOSDAC Soil Moisture: https://www.mosdac.gov.in/soil-moisture-0
MOSDAC download API guide: https://mosdac.gov.in/downloadapi-manual
GSI Bhusanket: https://bhusanket.gsi.gov.in/
Bhuvan Flood Services: https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/flood/flood.php?uname=empty
Bhuvan Flood Hazard: https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/flood_hz/flood_hz.php?uname=empty
Bhuvan Spatial FEWS: https://bhuvan-app1.nrsc.gov.in/fews/

See `DATA_PROVENANCE.md` for source notes and the exact reproducibility record
that should be kept for an SIH/research submission.


## Ground-truth rule

For a flash-flood prediction claim, do not use a landslide-only GSI inventory as the target label. Keep GSI landslides as secondary/cascading-hazard evidence. The training builder expects `--events` containing verified flood/flash-flood/inundation records.
