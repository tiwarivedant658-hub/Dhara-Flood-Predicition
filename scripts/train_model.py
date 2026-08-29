"""Train DHARA with chronological validation and publish honest metrics."""
from __future__ import annotations
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/research/training_data.csv"
MODEL=ROOT/"data/research/dhara_model.joblib"
METRICS=ROOT/"data/research/validation_metrics.json"
FEATURES=["rain_1h","rain_3h","rain_6h","rain_24h","rain_72h","soil_wetness","soil_change",
"slope_score","elevation_norm","twi_proxy","river_proximity","historical_hazard"]

def lead_time_hours(df, prob, threshold=.5, horizon=6):
    """Mean lead time = event_time - first prior threshold crossing."""
    work=df.copy()
    work["p"]=prob
    if "event_time" not in work: return None
    hits=[]
    for _,e in work[work.event==1].iterrows():
        before=work[(work.lat-e.lat).abs()<1e-9]
        before=before[(before.lon-e.lon).abs()<1e-9]
        before=before[(before.timestamp<=e.event_time)&
                      (before.timestamp>=e.event_time-pd.Timedelta(hours=horizon))]
        before=before[before.p>=threshold]
        if not before.empty:
            hits.append((e.event_time-before.timestamp.max()).total_seconds()/3600)
    return float(np.mean(hits)) if hits else None

def main():
    if not DATA.exists(): raise SystemExit(f"Missing {DATA}. Run build_dataset.py first.")
    df=pd.read_csv(DATA,parse_dates=["timestamp","event_time"]).sort_values("timestamp").reset_index(drop=True)
    if df.event.nunique()<2: raise SystemExit("Need both event=0 and event=1 labels.")
    cut=int(len(df)*.8)
    train,test=df.iloc[:cut],df.iloc[cut:]
    if train.event.nunique()<2 or test.event.nunique()<2:
        raise SystemExit("Chronological split must contain both classes; add more historical events.")
    model=RandomForestClassifier(n_estimators=400,max_depth=12,min_samples_leaf=3,
        class_weight="balanced_subsample",random_state=20260828,n_jobs=-1)
    model.fit(train[FEATURES],train.event.astype(int))
    p=model.predict_proba(test[FEATURES])[:,1]
    y=test.event.astype(int)
    threshold=.5; pred=(p>=threshold).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    metrics={
      "dataset_rows":int(len(df)),"train_rows":int(len(train)),"test_rows":int(len(test)),
      "train_end":str(train.timestamp.max()),"test_start":str(test.timestamp.min()),
      "event_rate_test":float(y.mean()),"threshold":threshold,
      "precision":float(precision_score(y,pred,zero_division=0)),
      "recall":float(recall_score(y,pred,zero_division=0)),
      "f1":float(f1_score(y,pred,zero_division=0)),
      "roc_auc":float(roc_auc_score(y,p)),
      "pr_auc":float(average_precision_score(y,p)),
      "false_alarm_rate":float(fp/(fp+tn)) if (fp+tn) else None,
      "tp":int(tp),"fp":int(fp),"tn":int(tn),"fn":int(fn),
      "warning_lead_time_hours":lead_time_hours(test,p,horizon=6),
      "validation":"chronological 80/20 (past -> future)",
      "feature_names":FEATURES
    }
    MODEL.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,MODEL)
    METRICS.write_text(json.dumps(metrics,indent=2),encoding="utf8")
    print("\nDHARA CHRONOLOGICAL VALIDATION")
    for k in ["precision","recall","f1","roc_auc","pr_auc","false_alarm_rate","warning_lead_time_hours"]:
        print(f"{k:28s}: {metrics[k]}")
    print(f"\nModel -> {MODEL}")
    print(f"Metrics -> {METRICS}")

if __name__=="__main__": main()
