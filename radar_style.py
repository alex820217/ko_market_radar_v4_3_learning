"""Modern color styling for KO Market Radar V4.3 tables and signal labels."""

def signal_style(value):
    v=str(value).upper()
    if "CONFIRMED LONG" in v or "EARLY LONG" in v:
        return "background-color:#DCFCE7;color:#166534;font-weight:800"
    if "CONFIRMED SHORT" in v or "EARLY SHORT" in v:
        return "background-color:#FEE2E2;color:#991B1B;font-weight:800"
    if "PRE-" in v or "WATCH" in v:
        return "background-color:#FEF3C7;color:#92400E;font-weight:750"
    if "LATE ENTRY" in v or "HOT ENTRY" in v or "NO TRADE" in v:
        return "background-color:#FDE8E8;color:#B42318;font-weight:750"
    if "CONTEXT CONFLICT" in v:
        return "background-color:#FFE4C7;color:#9A3412;font-weight:750"
    if "WAIT" in v:
        return "background-color:#F1F5F9;color:#64748B;font-weight:650"
    return ""

def grade_style(value):
    return {
        "A+":"background-color:#BBF7D0;color:#14532D;font-weight:850",
        "A":"background-color:#DCFCE7;color:#166534;font-weight:800",
        "B":"background-color:#FEF3C7;color:#92400E;font-weight:800",
        "C":"background-color:#FFEDD5;color:#9A3412;font-weight:800",
        "-":"background-color:#F8FAFC;color:#94A3B8",
    }.get(str(value),"")

def entry_style(value):
    v=str(value).upper()
    if "OPTIMAL" in v:return "background-color:#DCFCE7;color:#166534;font-weight:750"
    if "AKZEPTABEL" in v:return "background-color:#FEF3C7;color:#92400E;font-weight:750"
    if "SPÄT" in v:return "background-color:#FEE2E2;color:#991B1B;font-weight:750"
    return ""

def regime_style(value):
    v=str(value).upper()
    if v=="LONG":return "color:#15803D;font-weight:750"
    if v=="SHORT":return "color:#DC2626;font-weight:750"
    return "color:#64748B"

def style_radar(df):
    st=df.style
    if "Signal" in df:st=st.map(signal_style,subset=["Signal"])
    if "Grade" in df:st=st.map(grade_style,subset=["Grade"])
    if "Entry Status" in df:st=st.map(entry_style,subset=["Entry Status"])
    for col in ["60m Regime","15m Bias"]:
        if col in df:st=st.map(regime_style,subset=[col])
    return st

def signal_badge(signal):
    v=str(signal).upper()
    if "LONG" in v and any(x in v for x in ["EARLY","CONFIRMED"]):return f"🟢 {signal}"
    if "SHORT" in v and any(x in v for x in ["EARLY","CONFIRMED"]):return f"🔴 {signal}"
    if "PRE" in v or "WATCH" in v:return f"🟡 {signal}"
    if "LATE" in v or "HOT" in v or "NO TRADE" in v:return f"⛔ {signal}"
    if "CONFLICT" in v:return f"⚠️ {signal}"
    return f"⚪ {signal}"
