import time as tm
import pandas as pd,streamlit as st
from market_universe import MARKET_GROUPS,build_universe
from scanner_engine import scan_asset,market_open
from ko_profile import Profile,trailing_stop
from trade_journal import create_trade,update_trade,close_trade,load,enriched_df,statistics,export_bytes,backup_bytes,restore_bytes
st.set_page_config(page_title="KO Market Radar V4.3",page_icon="📡",layout="wide")
st.title("📡 KO Market Radar V4.3 · Learning Journal")
st.caption("60m Regime · 15m Bias · 5m Setup · 3m Trigger · echte Trade-Snapshots · MFE/MAE · Signalstatistik")
profile=Profile()
tabs=st.tabs(["🔥 Radar","💼 Offene Trades","📓 Journal & Lernen","💾 Backup"])
with tabs[0]:
    st.sidebar.header("Marktuniversum");groups=st.sidebar.multiselect("Gruppen",list(MARKET_GROUPS),default=["Deutschland","US Tech","Indizes"]);max_assets=st.sidebar.slider("Max. Assets",10,50,30);only_open=st.sidebar.checkbox("Geschlossene Märkte überspringen",True);spread_ok=st.sidebar.checkbox("Spread manuell akzeptabel",True);event=st.sidebar.checkbox("Event-Risiko",False)
    if st.sidebar.button("Cache leeren"):st.cache_data.clear();st.rerun()
    items=build_universe(groups)[:max_assets];items=[x for x in items if not(only_open and not market_open(x["ticker"]))];rows=[];errors=[];start=tm.time();bar=st.progress(0)
    for i,m in enumerate(items,1):
        try:r,*_=scan_asset(m,spread_ok,event);rows.append(r)
        except Exception as e:errors.append({"Asset":m["name"],"Fehler":str(e)})
        bar.progress(i/max(1,len(items)))
    bar.empty()
    if rows:
        scan=pd.DataFrame(rows);rank={"A+":0,"A":1,"B":2,"C":3,"-":9};scan["rank"]=scan.Grade.map(rank);scan=scan.sort_values(["rank","Score","ADX"],ascending=[True,False,False]);st.caption(f"{len(scan)} analysiert · {tm.time()-start:.1f}s")
        st.dataframe(scan[["Asset","Signal","Grade","Score","60m Regime","15m Bias","5m Setup","3m Trigger","Entry Status","Setup-Hinweis"]],use_container_width=True,hide_index=True)
        selected=st.selectbox("Setup für Trade-Snapshot",scan.Asset.tolist());r=scan[scan.Asset==selected].iloc[0]
        st.subheader(f"{r.Asset} · {r.Signal} · Grade {r.Grade}");st.write(r["Setup-Hinweis"])
        with st.form("new_trade"):
            c1,c2,c3,c4=st.columns(4);wkn=c1.text_input("WKN",value="VY479C" if selected=="DHL Group" else "").upper();direction=c2.selectbox("Richtung",["LONG","SHORT"],index=0 if "LONG" in r.Signal else 1);entry=c3.number_input("Zertifikat Kaufpreis",min_value=.0001,value=1.22,format="%.4f");qty=c4.number_input("Stückzahl",min_value=1,value=1639,step=1)
            c5,c6,c7=st.columns(3);stop=c5.number_input("Tatsächlicher Stop",min_value=.0001,value=1.1495,format="%.4f");leverage=c6.number_input("Hebel (falls bekannt)",min_value=0.0,value=0.0,step=.1);ko_dist=c7.number_input("KO-Abstand % (falls bekannt)",min_value=0.0,value=0.0,step=.1)
            notes=st.text_input("Notiz");save=st.form_submit_button("Trade mit Signal-Snapshot speichern",type="primary")
        if save:
            snapshot={k:(v.item() if hasattr(v,"item") else v) for k,v in r.drop(labels=["rank"]).to_dict().items()};product={"leverage":leverage or None,"ko_distance_pct":ko_dist or None};tid=create_trade(wkn,r.Asset,r.Ticker,direction,entry,stop,qty,snapshot,product,notes);st.success(f"Trade gespeichert: {tid[:8]} · Investment {entry*qty:.2f} EUR · Risiko {(entry-stop)*qty:.2f} EUR")
    if errors:
        with st.expander(f"Nicht auswertbar ({len(errors)})"):st.dataframe(pd.DataFrame(errors),hide_index=True)
with tabs[1]:
    trades=load("OPEN")
    if not trades:st.info("Keine offenen Trades.")
    for t in trades:
        with st.container(border=True):
            entry=t["certificate_entry"];st.write(f"**{t['wkn']} · {t['asset']} · {t['direction']}**");m=st.columns(4);m[0].metric("Kauf",f"{entry:.4f}");m[1].metric("Stop",f"{t['certificate_stop']:.4f}");m[2].metric("Stück",int(t['quantity']));m[3].metric("Investment",f"{t['investment']:.2f} EUR")
            with st.form("upd"+t["id"]):
                a,b,c=st.columns(3);current=a.number_input("Aktueller Geldkurs",min_value=.0001,value=float(entry),format="%.4f",key="c"+t["id"]);new_stop=b.number_input("Neuer Stop",min_value=.0001,value=float(t["certificate_stop"]),format="%.4f",key="s"+t["id"]);action=c.form_submit_button("Verlauf aktualisieren")
            if action:update_trade(t["id"],current,new_stop);st.rerun()
            perf=(t["highest_price"]/entry-1)*100 if t["highest_price"] else 0;st.caption(f"Bisher MFE {perf:+.2f}% · regelbasierter Trailing-Stop {trailing_stop(entry,perf,profile):.4f}")
            with st.form("close"+t["id"]):
                x,y=st.columns(2);exit_price=x.number_input("Verkaufskurs",min_value=.0001,value=float(current),format="%.4f",key="e"+t["id"]);reason=y.selectbox("Exitgrund",["Stop","Trailing-Stop","Gewinnziel","Trendbruch","Manuell","Handelsschluss"]);do=y.form_submit_button("Trade schließen")
            if do:close_trade(t["id"],exit_price,reason);st.rerun()
with tabs[2]:
    summary,groups_df=statistics();df=enriched_df()
    if summary.get("trades",0)==0:st.info("Noch keine geschlossenen Trades. Ab ca. 20-30 Trades sind erste Tendenzen sinnvoll; Regeländerungen erst nach deutlich mehr Daten.")
    else:
        m=st.columns(6);m[0].metric("Trades",summary["trades"]);m[1].metric("Trefferquote",f"{summary['win_rate']:.1f}%");m[2].metric("P/L",f"{summary['total_pnl']:+.2f} EUR");m[3].metric("Profit Factor",f"{summary['profit_factor']:.2f}");m[4].metric("Ø Gewinn",f"{summary['avg_win']:+.2f}%");m[5].metric("Ø R",f"{summary['avg_r']:+.2f}R")
        st.subheader("Signalgruppen");st.dataframe(groups_df,use_container_width=True,hide_index=True)
    st.subheader("Alle Trade-Datensätze");st.dataframe(df,use_container_width=True,hide_index=True)
    st.download_button("Journal als CSV herunterladen",export_bytes(),"trade_journal.csv","text/csv")
with tabs[3]:
    st.warning("Streamlit Community Cloud speichert lokale SQLite-Dateien nicht garantiert dauerhaft. Nach jedem Handelstag Backup herunterladen.")
    st.download_button("SQLite-Backup herunterladen",backup_bytes(),"trade_journal.sqlite3","application/octet-stream")
    up=st.file_uploader("SQLite-Backup wiederherstellen",type=["sqlite3","db"])
    if up and st.button("Backup einspielen"):restore_bytes(up.read());st.success("Backup wiederhergestellt");st.rerun()
st.caption("Entscheidungshilfe, keine Gewinngarantie. Das Journal ändert Regeln nicht automatisch; es liefert erst die Datenbasis für kontrollierte Backtests.")
