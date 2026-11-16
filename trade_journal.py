import io,json,sqlite3,uuid
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
DB=Path(__file__).with_name("trade_journal.sqlite3")

def _db():
    c=sqlite3.connect(DB);c.row_factory=sqlite3.Row
    c.execute('''create table if not exists trades(id text primary key,status text not null,wkn text,asset text,ticker text,direction text,entry_time text,exit_time text,certificate_entry real,certificate_stop real,certificate_exit real,quantity real,investment real,highest_price real,lowest_price real,exit_reason text,signal_snapshot text,product_snapshot text,notes text)''');c.commit();return c

def create_trade(wkn,asset,ticker,direction,entry,stop,quantity,signal_snapshot,product_snapshot=None,notes=""):
    c=_db();tid=str(uuid.uuid4());investment=entry*quantity
    c.execute("insert into trades values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(tid,"OPEN",wkn.upper(),asset,ticker,direction,datetime.now(timezone.utc).isoformat(timespec="seconds"),None,entry,stop,None,quantity,investment,entry,entry,None,json.dumps(signal_snapshot,ensure_ascii=False),json.dumps(product_snapshot or {},ensure_ascii=False),notes));c.commit();c.close();return tid

def update_trade(tid,current_price,new_stop=None):
    c=_db();r=c.execute("select * from trades where id=?",(tid,)).fetchone()
    if not r:return
    hi=max(r["highest_price"] or current_price,current_price);lo=min(r["lowest_price"] or current_price,current_price);stop=new_stop if new_stop is not None else r["certificate_stop"]
    c.execute("update trades set highest_price=?,lowest_price=?,certificate_stop=? where id=?",(hi,lo,stop,tid));c.commit();c.close()

def close_trade(tid,exit_price,reason):
    c=_db();c.execute("update trades set status='CLOSED',certificate_exit=?,exit_reason=?,exit_time=? where id=?",(exit_price,reason,datetime.now(timezone.utc).isoformat(timespec="seconds"),tid));c.commit();c.close()
def load(status=None):
    c=_db();q="select * from trades"+(" where status=?" if status else "")+" order by entry_time desc";rows=c.execute(q,(status,) if status else ()).fetchall();c.close();return [dict(r) for r in rows]
def enriched_df():
    rows=load();out=[]
    for r in rows:
        s=json.loads(r["signal_snapshot"] or "{}");entry=r["certificate_entry"];risk=entry-r["certificate_stop"] if entry and r["certificate_stop"] else None;exit_=r["certificate_exit"]
        pnl=(exit_-entry)*r["quantity"] if exit_ is not None else None;pct=(exit_/entry-1)*100 if exit_ is not None else None;r_mult=(exit_-entry)/risk if exit_ is not None and risk and risk>0 else None;mfe=(r["highest_price"]/entry-1)*100 if entry and r["highest_price"] else None;mae=(r["lowest_price"]/entry-1)*100 if entry and r["lowest_price"] else None
        out.append({**r,**{f"signal_{k}":v for k,v in s.items()},"pnl_eur":pnl,"pnl_pct":pct,"r_multiple":r_mult,"mfe_pct":mfe,"mae_pct":mae,"tp10_before_exit":bool(r["highest_price"] and r["highest_price"]>=entry*1.10)})
    return pd.DataFrame(out)
def statistics():
    df=enriched_df();closed=df[df.status=="CLOSED"] if not df.empty else df
    if closed.empty:return {"trades":0},pd.DataFrame()
    wins=closed[closed.pnl_eur>0];losses=closed[closed.pnl_eur<=0];gross_win=wins.pnl_eur.sum();gross_loss=abs(losses.pnl_eur.sum());pf=gross_win/gross_loss if gross_loss else float("inf")
    summary={"trades":len(closed),"win_rate":len(wins)/len(closed)*100,"avg_win":wins.pnl_pct.mean() if len(wins) else 0,"avg_loss":losses.pnl_pct.mean() if len(losses) else 0,"profit_factor":pf,"total_pnl":closed.pnl_eur.sum(),"avg_r":closed.r_multiple.mean()}
    cols=[c for c in ["signal_Signal","signal_Grade","signal_15m Bias","direction"] if c in closed]
    groups=[]
    for c in cols:
        g=closed.groupby(c,dropna=False).agg(Trades=("id","count"),Trefferquote=("pnl_eur",lambda x:(x>0).mean()*100),Pnl_EUR=("pnl_eur","sum"),Avg_R=("r_multiple","mean"),MFE=("mfe_pct","mean"),MAE=("mae_pct","mean")).reset_index().rename(columns={c:"Gruppe"});g.insert(0,"Dimension",c.replace("signal_",""));groups.append(g)
    return summary,pd.concat(groups,ignore_index=True) if groups else pd.DataFrame()
def export_bytes():
    return enriched_df().to_csv(index=False).encode("utf-8-sig")
def backup_bytes():
    return DB.read_bytes() if DB.exists() else b""
def restore_bytes(data):
    DB.write_bytes(data)
