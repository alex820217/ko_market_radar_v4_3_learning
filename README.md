# KO Market Radar V4.3 Learning Journal

## GitHub-Dateien
- intraday_ko_scanner_v4_3.py
- scanner_engine.py
- market_universe.py
- trade_journal.py
- ko_profile.py
- requirements.txt
- runtime.txt

Streamlit Main file: `intraday_ko_scanner_v4_3.py`

## Lernlogik
Beim Einstieg wird der komplette Radar-Snapshot gespeichert. Während des Trades werden höchster/niedrigster Zertifikatkurs gepflegt. Beim Exit berechnet das Journal P/L, R-Multiple, MFE und MAE. Gruppenstatistiken vergleichen EARLY/CONFIRMED, Grade und LONG/SHORT.

## Wichtiger Speicherhinweis
SQLite im Streamlit-Container ist nicht garantiert persistent. Nach jedem Handelstag das SQLite-Backup herunterladen. Später kann dieselbe Struktur auf Supabase/PostgreSQL migriert werden.
