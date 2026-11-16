from pathlib import Path
files=[Path('intraday_ko_scanner_v4_3_3.py'),Path('intraday_ko_scanner_v4_3.py')]
p=next((x for x in files if x.exists()),None)
if not p:raise SystemExit('Keine V4.3-Hauptdatei im GitHub-Root gefunden.')
s=p.read_text(encoding='utf-8')
s=s.replace('close_trade,load,enriched_df','close_trade,delete_trade,load,enriched_df')
if 'delete_trade' not in s.split('\n',20)[0:20].__str__():
    # fallback import pattern
    s=s.replace('from trade_journal import ', 'from trade_journal import delete_trade,',1)
if 'Falschen Journal-Eintrag löschen' not in s:
    marker='st.download_button("Journal als CSV herunterladen",export_bytes(),"trade_journal.csv","text/csv")'
    if marker not in s:raise SystemExit('Journal-Download-Anker nicht gefunden; Datei unverändert.')
    block='''if not journal.empty:
        st.subheader("🗑️ Falschen Journal-Eintrag löschen")
        _delete_options={f"{row['wkn']} · {row['asset']} · {row['status']} · {str(row['entry_time'])[:19]} · {row['id'][:8]}":row['id'] for _,row in journal.iterrows()}
        _delete_label=st.selectbox("Zu löschenden Trade auswählen",list(_delete_options.keys()),key="journal_delete_select")
        _delete_confirm=st.checkbox("Ich bestätige: Dieser Trade soll dauerhaft gelöscht werden",key="journal_delete_confirm")
        if st.button("🗑️ Trade endgültig löschen",disabled=not _delete_confirm,key="journal_delete_button"):
            delete_trade(_delete_options[_delete_label])
            st.success("Trade gelöscht. Bilanz und Lernstatistik werden neu berechnet.")
            st.rerun()
    '''+marker
    s=s.replace(marker,block,1)
p.write_text(s,encoding='utf-8')
print('Löschen-Funktion erfolgreich in',p.name,'integriert.')
