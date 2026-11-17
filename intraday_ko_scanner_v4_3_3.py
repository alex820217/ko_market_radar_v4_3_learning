import time as tm
import pandas as pd
import streamlit as st
from market_universe import MARKET_GROUPS,build_universe
from scanner_engine import scan_asset,market_open
from radar_style import prepare_radar,signal_label
from trade_journal import create_trade,update_trade,close_trade,load,enriched_df,statistics,export_bytes,backup_bytes,restore_bytes
from portfolio_summary import portfolio_metrics,equity_curve
from ko_profile import Profile,trailing_stop

st.set_page_config(page_title="KO Market Radar V4.3.3",page_icon="📡",layout="wide")
st.markdown("""<style>
.block-container{max-width:1550px;padding-top:1.5rem;padding-bottom:3rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #e5e7eb;padding:12px;border-radius:14px;box-shadow:0 4px 14px rgba(15,23,42,.05)}
div[data-testid="stDataFrame"],[data-testid="stExpander"]{border:1px solid #e5e7eb;border-radius:14px;overflow:hidden}
.pnl-positive{color:#15803d;font-weight:800}.pnl-negative{color:#b91c1c;font-weight:800}.pnl-flat{color:#64748b;font-weight:800}
</style>""",unsafe_allow_html=True)
st.title("📡 KO Market Radar V4.3.3")
st.caption("Farbsichere Signale · Trade-Journal · offene und realisierte Gesamtbilanz · MFE/MAE · Signalstatistik")
profile=Profile()

def fmt_eur(x):return f"{x:+,.2f} €".replace(",","X").replace(".",",").replace("X",".")
def pnl_class(x):return "pnl-positive" if x>0 else "pnl-negative" if x<0 else "pnl-flat"
def render_balance():
    rows=load();m=portfolio_metrics(rows)
    st.subheader("💶 Gesamtbilanz")
    c=st.columns(7)
    c[0].metric("Gesamt P/L",fmt_eur(m["total_pnl"]),f"{m['return_pct']:+.2f}%")
    c[1].metric("Realisiert",fmt_eur(m["closed_pnl"]))
    c[2].metric("Offen",fmt_eur(m["open_pnl"]))
    c[3].metric("Trades",m["trades"])
    c[4].metric("Offen",m["open"])
    c[5].metric("Geschlossen",m["closed"])
    c[6].metric("Trefferquote",f"{m['win_rate']:.1f}%")
    if m["trades"]:
        state="im PLUS" if m["total_pnl"]>0 else "im MINUS" if m["total_pnl"]<0 else "ausgeglichen"
        st.markdown(f"**Aktueller Gesamtstatus: {state} ({fmt_eur(m['total_pnl'])})**")
    else:st.info("Noch keine Trades im Journal. Die Bilanz startet mit dem ersten gespeicherten Trade.")

render_balance()
tabs=st.tabs(["🔥 Radar","💼 Offene Trades","📓 Journal & Lernen","💾 Backup"])
with tabs[0]:
    st.sidebar.header("Marktuniversum")
    groups=st.sidebar.multiselect("Gruppen",list(MARKET_GROUPS),default=["Deutschland","US Tech","Indizes"])
    max_assets=st.sidebar.slider("Max. Assets",10,50,30)
    only_open=st.sidebar.checkbox("Geschlossene Märkte überspringen",True)
    spread_ok=st.sidebar.checkbox("Spread manuell akzeptabel",True)
    event=st.sidebar.checkbox("Event-Risiko",False)
    if st.sidebar.button("Cache leeren"):st.cache_data.clear();st.rerun()
    items=build_universe(groups)[:max_assets];items=[x for x in items if not(only_open and not market_open(x["ticker"]))]
    rows=[];errors=[];start=tm.time();bar=st.progress(0)
    for i,meta in enumerate(items,1):
        try:rows.append(scan_asset(meta,spread_ok,event))
        except Exception as exc:errors.append({"Asset":meta["name"],"Fehler":str(exc)})
        bar.progress(i/max(1,len(items)))
    bar.empty()
    if not rows:st.warning("Keine Assets auswertbar.")
    else:
        scan=pd.DataFrame(rows);rank={"A+":0,"A":1,"B":2,"C":3,"-":9};signal_rank=lambda x:0 if "EARLY" in x or "CONFIRMED" in x else 1 if "PRE" in x else 2 if "WATCH" in x else 3
        scan["_grade"]=scan.Grade.map(rank);scan["_signal"]=scan.Signal.map(signal_rank);scan=scan.sort_values(["_signal","_grade","Score","ADX"],ascending=[True,True,False,False])
        st.caption(f"{len(scan)} analysiert · {tm.time()-start:.1f}s")
        cols=["Asset","Signal","Grade","Score","60m Regime","15m Bias","5m Setup","3m Trigger","Entry Status","Setup-Hinweis"]
        display=prepare_radar(scan[cols])
        st.dataframe(display,use_container_width=True,hide_index=True,height=min(760,38+35*len(display)))
        st.caption("Legende: 🟢 Long/optimal/A · 🔴 Short/spät · 🟡 beobachten/akzeptabel/B · 🟠 C · ⛔ kein Einstieg · ⚠️ Konflikt")
        selected=st.selectbox("Setup für Trade-Snapshot",scan.Asset.tolist());r=scan[scan.Asset==selected].iloc[0]
        st.subheader(f"{r.Asset} · {signal_label(r.Signal)} · Grade {r.Grade}");st.write(r["Setup-Hinweis"])
        with st.form("new_trade"):
            a,b,c,d=st.columns(4);wkn=a.text_input("WKN").upper();direction=b.selectbox("Richtung",["LONG","SHORT"],index=0 if "LONG" in r.Signal else 1);entry=c.number_input("Zertifikat Kaufpreis",min_value=.0001,value=1.22,format="%.4f");qty=d.number_input("Stückzahl",min_value=1,value=1639,step=1)
            e,f,g=st.columns(3);stop=e.number_input("Tatsächlicher Stop",min_value=.0001,value=1.1495,format="%.4f");leverage=f.number_input("Hebel (optional)",min_value=0.0,value=0.0,step=.1);ko_dist=g.number_input("KO-Abstand % (optional)",min_value=0.0,value=0.0,step=.1)
            notes=st.text_input("Notiz");save=st.form_submit_button("Trade mit Signal-Snapshot speichern",type="primary")
        if save:
            snapshot={k:(v.item() if hasattr(v,"item") else v) for k,v in r.drop(labels=["_grade","_signal"]).to_dict().items()};product={"leverage":leverage or None,"ko_distance_pct":ko_dist or None}
            tid=create_trade(wkn,r.Asset,r.Ticker,direction,entry,stop,qty,snapshot,product,notes);st.success(f"Gespeichert: {tid[:8]} · Investment {entry*qty:.2f} € · Risiko {(entry-stop)*qty:.2f} €");st.rerun()
    if errors:
        with st.expander(f"Nicht auswertbar ({len(errors)})"):st.dataframe(pd.DataFrame(errors),hide_index=True)
with tabs[1]:
    trades=load("OPEN")
    if not trades:st.info("Keine offenen Trades.")
    for trade in trades:
        with st.container(border=True):
            entry=float(trade["certificate_entry"]);current=float(trade.get("last_price") or entry);perf=(current/entry-1)*100;pnl=(current-entry)*float(trade["quantity"])
            st.write(f"**{trade['wkn']} · {trade['asset']} · {trade['direction']}**")
            c=st.columns(6);c[0].metric("Kauf",f"{entry:.4f} €");c[1].metric("Aktuell",f"{current:.4f} €");c[2].metric("P/L",fmt_eur(pnl));c[3].metric("P/L %",f"{perf:+.2f}%");c[4].metric("Stop",f"{trade['certificate_stop']:.4f} €");c[5].metric("Stück",int(trade['quantity']))
            with st.form("upd"+trade["id"]):
                a,b=st.columns(2);new_price=a.number_input("Aktueller Geldkurs",min_value=.0001,value=current,format="%.4f",key="cp"+trade["id"]);new_stop=b.number_input("Neuer Stop",min_value=.0001,value=float(trade["certificate_stop"]),format="%.4f",key="ns"+trade["id"]);update=b.form_submit_button("Kurs und Stop aktualisieren")
            if update:update_trade(trade["id"],new_price,new_stop);st.rerun()
            suggested=trailing_stop(entry,perf,profile);st.caption(f"Regelbasierter Trailing-Stop bei aktueller Performance: {suggested:.4f} €")
            with st.form("close"+trade["id"]):
                x,y=st.columns(2);exit_price=x.number_input("Verkaufskurs",min_value=.0001,value=current,format="%.4f",key="ep"+trade["id"]);reason=y.selectbox("Exitgrund",["Stop","Trailing-Stop","Gewinnziel","Trendbruch","Manuell","Handelsschluss"]);close=y.form_submit_button("Trade schließen")
            if close:close_trade(trade["id"],exit_price,reason);st.rerun()
with tabs[2]:
    summary,groups_df=statistics();journal=enriched_df();curve=equity_curve(journal)
    if summary.get("trades",0)==0:st.info("Noch keine geschlossenen Trades. Erste Tendenzen ab etwa 20–30 Trades, belastbarere Gruppenvergleiche ab etwa 100 Trades.")
    else:
        c=st.columns(6);c[0].metric("Geschlossene Trades",summary["trades"]);c[1].metric("Trefferquote",f"{summary['win_rate']:.1f}%");c[2].metric("Realisiertes P/L",fmt_eur(summary["total_pnl"]));c[3].metric("Profit Factor",f"{summary['profit_factor']:.2f}");c[4].metric("Ø Gewinn",f"{summary['avg_win']:+.2f}%");c[5].metric("Ø R",f"{summary['avg_r']:+.2f}R")
        if not curve.empty:st.subheader("Kumulierte Bilanz");st.line_chart(curve.set_index("exit_time"))
        st.subheader("Signalgruppen");st.dataframe(groups_df,use_container_width=True,hide_index=True)
    st.subheader("Alle Trade-Datensätze");st.dataframe(journal,use_container_width=True,hide_index=True)
    st.download_button("Journal als CSV herunterladen",export_bytes(),"trade_journal.csv","text/csv")
with tabs[3]:
    st.warning("Lokale SQLite-Dateien sind auf Streamlit Community Cloud nicht dauerhaft garantiert. Nach jedem Handelstag Backup herunterladen.")
    st.download_button("SQLite-Backup herunterladen",backup_bytes(),"trade_journal.sqlite3","application/octet-stream")
    upload=st.file_uploader("SQLite-Backup wiederherstellen",type=["sqlite3","db"])
    if upload and st.button("Backup einspielen"):restore_bytes(upload.read());st.success("Backup wiederhergestellt");st.rerun()
st.caption("Technische Entscheidungshilfe. Keine automatische Order und keine Gewinngarantie.")
