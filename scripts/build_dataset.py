"""Build a leakage-safe, spatially/temporally aligned DHARA training table.

Required predictors:
  IMD: timestamp,lat,lon,rain_1h,rain_3h,rain_6h,rain_24h,rain_72h
  MOSDAC: timestamp,lat,lon,soil_wetness,soil_change
  terrain: lat,lon,slope_score,elevation_norm,twi_proxy,river_proximity
  bhuvan: lat,lon,river_proximity,twi_proxy,historical_hazard

Ground truth:
  events.csv (preferred): event_time,lat,lon,event_type
  GSI may be supplied as --events only when its event_type is a verified
  flash-flood/flood event. A landslide inventory is NOT silently converted
  into a flash-flood label.

Label: event=1 when a verified target event occurs within [t,t+horizon]
inside --radius-km of the observation cell. Static layers are nearest-neighbor
matched; MOSDAC is nearest-in-time and nearest-in-space within tolerances.
"""
from __future__ import annotations
import argparse, math
from pathlib import Path
import numpy as np
import pandas as pd

FEATURES=["rain_1h","rain_3h","rain_6h","rain_24h","rain_72h","soil_wetness","soil_change","slope_score","elevation_norm","twi_proxy","river_proximity","historical_hazard"]

def read(path,time_col=None):
    df=pd.read_csv(path)
    if time_col:
        if time_col not in df.columns: raise SystemExit(f"Missing column '{time_col}' in {path}")
        df[time_col]=pd.to_datetime(df[time_col],utc=True,errors="coerce")
        df=df.dropna(subset=[time_col])
    for c in ["lat","lon"]:
        if c in df: df[c]=pd.to_numeric(df[c],errors="coerce")
    return df.dropna(subset=[c for c in ["lat","lon"] if c in df.columns])

def haversine_km(lat1,lon1,lat2,lon2):
    r=6371.0088
    p1,p2=math.radians(lat1),math.radians(lat2)
    dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))

def nearest_static(df, static, cols, max_km=50):
    if static is None or static.empty: return df
    vals=static[["lat","lon"]].to_numpy(float)
    out=[]
    for _,r in df.iterrows():
        ds=np.array([haversine_km(r.lat,r.lon,a,b) for a,b in vals])
        j=int(np.argmin(ds)); row=r.copy()
        if ds[j] <= max_km:
            for c in cols:
                if c in static.columns: row[c]=static.iloc[j][c]
        out.append(row)
    return pd.DataFrame(out)

def nearest_mosdac(base, mos, max_minutes=180, max_km=50):
    if mos.empty: return base
    out=[]
    mos=mos.sort_values("timestamp")
    for _,r in base.iterrows():
        m=mos[(mos.timestamp>=r.timestamp-pd.Timedelta(minutes=max_minutes)) & (mos.timestamp<=r.timestamp+pd.Timedelta(minutes=max_minutes))]
        if m.empty: continue
        ds=np.array([haversine_km(r.lat,r.lon,a,b) for a,b in m[["lat","lon"]].to_numpy(float)])
        j=int(np.argmin(ds))
        if ds[j] > max_km: continue
        row=r.copy(); mr=m.iloc[j]
        row["soil_wetness"]=mr.get("soil_wetness",np.nan); row["soil_change"]=mr.get("soil_change",np.nan)
        out.append(row)
    return pd.DataFrame(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--imd",required=True); ap.add_argument("--mosdac",required=True)
    ap.add_argument("--terrain"); ap.add_argument("--bhuvan")
    ap.add_argument("--events",required=True,help="Verified flood/flash-flood event file; GSI landslide inventory must not be used as flood labels")
    ap.add_argument("--out",default="data/research/training_data.csv")
    ap.add_argument("--horizon",type=int,default=6); ap.add_argument("--radius-km",type=float,default=10)
    ap.add_argument("--mosdac-time-min",type=int,default=180); ap.add_argument("--static-radius-km",type=float,default=50)
    args=ap.parse_args()
    imd=read(args.imd,"timestamp"); mos=read(args.mosdac,"timestamp")
    if imd.empty or mos.empty: raise SystemExit("IMD and MOSDAC files must contain valid rows.")
    # Exact coordinate joins are avoided; MOSDAC is matched by nearest time/location.
    base=nearest_mosdac(imd,mos,args.mosdac_time_min,args.static_radius_km)
    if base.empty: raise SystemExit("No IMD rows could be matched to MOSDAC within the configured tolerances.")
    terrain=read(args.terrain) if args.terrain else None
    base=nearest_static(base,terrain,["slope_score","elevation_norm","twi_proxy","river_proximity"],args.static_radius_km)
    bhu=read(args.bhuvan) if args.bhuvan else None
    base=nearest_static(base,bhu,["river_proximity","twi_proxy","historical_hazard"],args.static_radius_km)
    defaults={"slope_score":50,"elevation_norm":0.5,"twi_proxy":0.5,"river_proximity":0.5,"historical_hazard":0}
    for c,d in defaults.items():
        if c not in base: base[c]=d
        base[c]=pd.to_numeric(base[c],errors="coerce").fillna(d)
    events=read(args.events,"event_time")
    if events.empty: raise SystemExit("Events file has no valid event_time rows.")
    bad=events.event_type.astype(str).str.lower().isin(["landslide","debris_slide","rockfall"])
    if bad.any() and (~bad).sum()==0:
        raise SystemExit("The supplied events file contains only landslides. Provide verified flood/flash-flood event labels; GSI landslides are secondary hazard evidence, not flood ground truth.")
    target_terms=("flood","flash_flood","flash flood","inundation")
    events=events[events.event_type.astype(str).str.lower().apply(lambda x:any(t in x for t in target_terms))].copy()
    if events.empty: raise SystemExit("No flood/flash-flood event_type rows found in --events.")
    events=events.sort_values("event_time")
    labels=[]; event_times=[]
    for _,r in base.iterrows():
        w=events[(events.event_time>=r.timestamp)&(events.event_time<=r.timestamp+pd.Timedelta(hours=args.horizon))]
        hit=None
        for _,e in w.iterrows():
            if haversine_km(r.lat,r.lon,e.lat,e.lon)<=args.radius_km: hit=e; break
        labels.append(1 if hit is not None else 0); event_times.append(hit.event_time if hit is not None else pd.NaT)
    base["event"]=labels; base["event_time"]=event_times
    base=base.sort_values(["timestamp","lat","lon"])
    base=base[["timestamp","lat","lon"]+FEATURES+["event","event_time"]].dropna(subset=FEATURES)
    if base.event.nunique()<2: raise SystemExit("Labels contain only one class. Add more verified historical events and/or extend the period.")
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); base.to_csv(args.out,index=False)
    print(f"Saved {len(base):,} labelled rows -> {args.out}")
    print(f"Positive events: {int(base.event.sum()):,} ({base.event.mean()*100:.2f}%)")

if __name__=="__main__": main()
