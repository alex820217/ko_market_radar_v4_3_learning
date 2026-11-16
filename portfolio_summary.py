import json
import pandas as pd

def portfolio_metrics(rows):
    if not rows:
        return {"closed_pnl":0.0,"open_pnl":0.0,"total_pnl":0.0,"invested":0.0,"trades":0,"closed":0,"open":0,"wins":0,"losses":0,"win_rate":0.0,"return_pct":0.0}
    closed_pnl=open_pnl=invested=0.0;closed=open_=wins=losses=0
    for r in rows:
        entry=float(r.get("certificate_entry") or 0);qty=float(r.get("quantity") or 0);invested+=entry*qty
        if r.get("status")=="CLOSED" and r.get("certificate_exit") is not None:
            pnl=(float(r["certificate_exit"])-entry)*qty;closed_pnl+=pnl;closed+=1;wins+=pnl>0;losses+=pnl<=0
        elif r.get("status")=="OPEN":
            current=float(r.get("last_price") or r.get("highest_price") or entry);open_pnl+=(current-entry)*qty;open_+=1
    total=closed_pnl+open_pnl
    return {"closed_pnl":closed_pnl,"open_pnl":open_pnl,"total_pnl":total,"invested":invested,"trades":len(rows),"closed":closed,"open":open_,"wins":wins,"losses":losses,"win_rate":wins/closed*100 if closed else 0.0,"return_pct":total/invested*100 if invested else 0.0}

def equity_curve(df):
    if df is None or df.empty or "status" not in df:return pd.DataFrame()
    d=df[(df.status=="CLOSED") & df.pnl_eur.notna()].copy()
    if d.empty:return d
    d["exit_time"]=pd.to_datetime(d["exit_time"],errors="coerce");d=d.sort_values("exit_time");d["Kumuliertes P/L EUR"]=d["pnl_eur"].cumsum()
    return d[["exit_time","Kumuliertes P/L EUR"]]
