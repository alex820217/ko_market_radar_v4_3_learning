"""One-time updater for intraday_ko_scanner_v4_3.py.
Adds colored radar cells without changing signal logic or journal data.
"""
from pathlib import Path
P=Path("intraday_ko_scanner_v4_3.py")
if not P.exists():raise SystemExit("intraday_ko_scanner_v4_3.py nicht im aktuellen Ordner gefunden")
s=P.read_text(encoding="utf-8")
imp='from radar_style import style_radar,signal_badge\n'
if imp not in s:
    anchor='import pandas as pd,streamlit as st\n'
    if anchor not in s:raise SystemExit("Import-Anker nicht gefunden")
    s=s.replace(anchor,anchor+imp,1)
old='st.dataframe(scan[["Asset","Signal","Grade","Score","60m Regime","15m Bias","5m Setup","3m Trigger","Entry Status","Setup-Hinweis"]],use_container_width=True,hide_index=True)'
new='''radar_cols=["Asset","Signal","Grade","Score","60m Regime","15m Bias","5m Setup","3m Trigger","Entry Status","Setup-Hinweis"]
        radar_view=scan[radar_cols].copy()
        st.dataframe(style_radar(radar_view),use_container_width=True,hide_index=True,height=min(760,38+35*len(radar_view)))'''
if old not in s:
    raise SystemExit("Radar-Tabelle nicht gefunden. Keine Datei geändert.")
s=s.replace(old,new,1)
old2='st.subheader(f"{r.Asset} · {r.Signal} · Grade {r.Grade}");st.write(r["Setup-Hinweis"])'
new2='''st.subheader(f"{r.Asset} · {signal_badge(r.Signal)} · Grade {r.Grade}")
        st.caption(f"Setup-Hinweis: {r['Setup-Hinweis']}")'''
if old2 in s:s=s.replace(old2,new2,1)
P.write_text(s,encoding="utf-8")
print("V4.3.1 Farb-UI erfolgreich angewendet.")
