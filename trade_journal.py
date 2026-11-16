import json,sqlite3,uuid
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
DB=Path(__file__).with_name("trade_journal.sqlite3")

def _db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS trades(
      id TEXT PRIMARY KEY,status TEXT NOT NULL,wkn TEXT,asset TEXT,ticker TEXT,direction TEXT,
      entry_time TEXT,exit_time TEXT,certificate_entry REAL,certificate_stop REAL,certificate_exit REAL,
      quantity REAL,investment REAL,highest_price REAL,lowest_price REAL,exit_reason TEXT,
      signal_snapshot TEXT,product_snapshot TEXT,notes TEXT)""")
    c.commit(); return c

def create_trade(wkn,asset,ticker,direction,entry,stop,quantity,signal_snapshot,product_snapshot=None,notes=""):
    c=_db(); tid=str(uuid.uuid4()); investment=float(entry)*float(quantity)
    cols=("id,status,wkn,asset,ticker,direction,entry_time,exit_time,certificate_entry,certificate_stop,"
          "certificate_exit,quantity,investment,highest_price,lowest_price,exit_reason,signal_snapshot,product_snapshot,notes")
    vals=(tid,"OPEN",wkn.upper(),asset,ticker,direction,datetime.now(timezone.utc).isoformat(timespec="seconds"),None,
          float(entry),float(stop),None,float(quantity),investment,float(entry),float(entry),None,
          json.dumps(signal_snapshot,ensure_ascii=False,default=str),json.dumps(product_snapshot or {},ensure_ascii=False,default=str),notes)
    q=f"INSERT INTO trades ({cols}) VALUES ({','.join(['?']*19)})"
    c.execute(q,vals); c.commit(); c.close(); return tid

def update_trade(tid,current_price,new_stop=None):
    c=_db();r=c.execute("SELECT * FROM trades WHERE id=?",(tid,)).fetchone()
    if not r:c.close();return
    cp=float(current_price);hi=max(r["highest_price"] or cp,cp);lo=min(r["lowest_price"] or cp,cp);stop=float(new_stop) if new_stop is not None else r["certificate_stop"]
    c.execute("UPDATE trades SET highest_price=?,lowest_price=?,certificate_stop=? WHERE id=?",(hi,lo,stop,tid));c.commit();c.close()

def close_trade(tid,exit_price,reason):
    c=_db();c.execute("UPDATE trades SET status='CLOSED',certificate_exit=?,exit_reason=?,exit_time=? WHERE id=?",(float(exit_price),reason,datetime.now(timezone.utc).isoformat(timespec="seconds"),tid));c.commit();c.close()
def load(status=None):
    c=_db();q="SELECT * FROM trades"+(" WHERE status=?" if status else "")+" ORDER BY entry_time DESC";rows=c.execute(q,(status,) if status else ()).fetchall();c.close();return [dict(r) for r in rows]
def enriched_df():
    rows=load();out=[]
    for r in rows:
        snap=json.loads(r["signal_snapshot"] or "{}");entry=r["certificate_entry"];risk=entry-r["certificate_stop"] if entry and r["certificate_stop"] else None;ex=r["certificate_exit"]
        pnl=(ex-entry)*r["quantity"] if ex is not None else None;pct=(ex/entry-1)*100 if ex is not None else None;rm=(ex-entry)/risk if ex is not None and risk and risk>0 else None;mfe=(r["highest_price"]/entry-1)*100 if entry and r["highest_price"] else None;mae=(r["lowest_price"]/entry-1)*100 if entry and r["lowest_price"] else None
        out.append({**r,**{f"signal_{k}":v for k,v in snap.items()},"pnl_eur":pnl,"pnl_pct":pct,"r_multiple":rm,"mfe_pct":mfe,"mae_pct":mae,"tp10_before_exit":bool(r["highest_price"] and r["highest_price"]>=entry*1.10)})
    return pd.DataFrame(out)
def statistics():
    df=enriched_df();closed=df[df.status=="CLOSED"] if not df.empty else df
    if closed.empty:return {"trades":0},pd.DataFrame()
    wins=closed[closed.pnl_eur>0];losses=closed[closed.pnl_eur<=0];gw=wins.pnl_eur.sum();gl=abs(losses.pnl_eur.sum());pf=gw/gl if gl else float("inf")
    summary={"trades":len(closed),"win_rate":len(wins)/len(closed)*100,"avg_win":wins.pnl_pct.mean() if len(wins) else 0,"avg_loss":losses.pnl_pct.mean() if len(losses) else 0,"profit_factor":pf,"total_pnl":closed.pnl_eur.sum(),"avg_r":closed.r_multiple.mean()}
    groups=[]
    for col in [c for c in ["signal_Signal","signal_Grade","direction"] if c in closed]:
        g=closed.groupby(col,dropna=False).agg(Trades=("id","count"),Trefferquote=("pnl_eur",lambda x:(x>0).mean()*100),Pnl_EUR=("pnl_eur","sum"),Avg_R=("r_multiple","mean"),MFE=("mfe_pct","mean"),MAE=("mae_pct","mean")).reset_index().rename(columns={col:"Gruppe"});g.insert(0,"Dimension",col.replace("signal_",""));groups.append(g)
    return summary,pd.concat(groups,ignore_index=True) if groups else pd.DataFrame()
def export_bytes():return enriched_df().to_csv(index=False).encode("utf-8-sig")
def backup_bytes():return DB.read_bytes() if DB.exists() else b""
def restore_bytes(data):DB.write_bytes(data)
