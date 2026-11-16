from datetime import datetime,time
from zoneinfo import ZoneInfo
import numpy as np,pandas as pd,streamlit as st,ta,yfinance as yf
from market_universe import BASISWERT_IDS
MIN15,MIN5,MIN3=210,60,80
def _series(frame,col):
    x=frame[col];x=x.iloc[:,0] if isinstance(x,pd.DataFrame) else x
    return pd.to_numeric(x,errors="coerce")
@st.cache_data(ttl=300,show_spinner=False)
def download(ticker,interval,period):
    d=yf.download(ticker,interval=interval,period=period,auto_adjust=True,prepost=False,progress=False,threads=False)
    if d.empty:return d
    o=pd.DataFrame(index=d.index)
    for c in ["Open","High","Low","Close","Volume"]:o[c]=_series(d,c)
    return o.dropna(subset=["Open","High","Low","Close"])
@st.cache_data(ttl=180,show_spinner=False)
def download_3m(ticker):
    d=download(ticker,"1m","7d")
    return d.resample("3min",origin="start_day",label="right",closed="right").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna() if not d.empty else d
def market_open(ticker):
    if ticker.endswith(".DE") or ticker in {"^GDAXI","^STOXX50E"}:
        n=datetime.now(ZoneInfo("Europe/Berlin"));return n.weekday()<5 and time(9)<=n.time()<time(17,30)
    if ticker.startswith("^") or ticker.isalpha():
        n=datetime.now(ZoneInfo("America/New_York"));return n.weekday()<5 and time(9,30)<=n.time()<time(16)
    return True
def indicators(df):
    d=df.copy();c,h,l,v=d.Close,d.High,d.Low,d.Volume.fillna(0)
    for n in [9,20,50,200]:d[f"EMA{n}"]=ta.trend.EMAIndicator(c,n).ema_indicator()
    d["RSI"]=ta.momentum.RSIIndicator(c,14).rsi();d["ATR"]=ta.volatility.AverageTrueRange(h,l,c,14).average_true_range();d["ADX"]=ta.trend.ADXIndicator(h,l,c,14).adx();d["MACD"]=ta.trend.MACD(c).macd_diff()
    typ=(h+l+c)/3;dates=pd.Series(d.index.date,index=d.index);cv=v.groupby(dates).cumsum();d["VWAP"]=((typ*v).groupby(dates).cumsum()/cv.replace(0,np.nan)).fillna(d.EMA20)
    return d.dropna()
def _regime(raw):
    h=raw.resample("60min",origin="start_day",label="right",closed="right").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna();h=indicators(h.iloc[:-1])
    if len(h)<3:return "NEUTRAL"
    r,p=h.iloc[-1],h.iloc[-2];long=sum([r.Close>r.EMA20,r.EMA20>r.EMA50,r.EMA20>p.EMA20,r.MACD>=0]);short=sum([r.Close<r.EMA20,r.EMA20<r.EMA50,r.EMA20<p.EMA20,r.MACD<=0])
    return "LONG" if long>=3 and long>short else "SHORT" if short>=3 and short>long else "NEUTRAL"
def _bias(d):
    r=d.iloc[-1];long=sum([r.Close>r.EMA20,r.EMA20>r.EMA50,r.EMA50>r.EMA200,r.ADX>=18,r.MACD>0]);short=sum([r.Close<r.EMA20,r.EMA20<r.EMA50,r.EMA50<r.EMA200,r.ADX>=18,r.MACD<0]);return ("LONG" if long>=4 and long>short else "SHORT" if short>=4 and short>long else None),long,short
def _setup(d,side):
    r=d.iloc[-1];checks=[r.Close>r.VWAP,r.EMA9>r.EMA20,r.RSI>50,r.MACD>0] if side=="LONG" else [r.Close<r.VWAP,r.EMA9<r.EMA20,r.RSI<50,r.MACD<0];return sum(checks)
def _trigger(d,side):
    r,p=d.iloc[-1],d.iloc[-2];checks=[r.Close>r.EMA9,r.EMA9>r.EMA20,r.RSI>52,r.Close>p.High] if side=="LONG" else [r.Close<r.EMA9,r.EMA9<r.EMA20,r.RSI<48,r.Close<p.Low];return sum(checks)
def _grade(signal,score,adx,dist,hot):
    issues=[]
    if adx<20:issues.append(f"ADX nur {adx:.1f}")
    if dist>.75:issues.append(f"Entry {dist:.2f} ATR von EMA20")
    if hot:issues.append("RSI bereits heiß")
    if "PRE" in signal:issues.append("3m Trigger unvollständig")
    if not any(x in signal for x in ["EARLY","CONFIRMED","PRE"]):return "-","; ".join(issues) or "Kein handelbares Setup"
    grade="A+" if score>=90 else "A" if score>=85 else "B" if score>=75 else "C" if score>=70 else "-"
    if issues and grade in {"A+","A"}:grade="B"
    if len(issues)>=2 and grade=="B":grade="C"
    return grade,"; ".join(issues) or "A-Setup erfüllt"
def scan_asset(meta,spread_ok=True,event=False):
    raw15,raw5=download(meta["ticker"],"15m","30d"),download(meta["ticker"],"5m","5d");d15,d5=indicators(raw15.iloc[:-1]),indicators(raw5.iloc[:-1])
    if len(d15)<MIN15 or len(d5)<MIN5:raise ValueError(f"zu wenig Daten 15m={len(d15)} 5m={len(d5)}")
    reg=_regime(raw15);bias,long_count,short_count=_bias(d15);side=bias or ("LONG" if long_count>=short_count else "SHORT");setup=_setup(d5,side);aligned=reg in {side,"NEUTRAL"}
    raw3=download_3m(meta["ticker"]) if bias and setup>=2 and aligned else pd.DataFrame();d3=indicators(raw3.iloc[:-1]) if not raw3.empty else pd.DataFrame();has3=len(d3)>=MIN3;trigger=_trigger(d3,side) if has3 else 0;r=d5.iloc[-1]
    price=float(r.Close);atr=float(r.ATR);dist=abs(price-r.EMA20)/atr;hot=(side=="LONG" and r.RSI>68) or (side=="SHORT" and r.RSI<32);over=(side=="LONG" and r.RSI>72) or (side=="SHORT" and r.RSI<28);score=min(100,(long_count if side=="LONG" else short_count)*8+setup*7+trigger*7);entry="OPTIMAL" if dist<=.75 else "AKZEPTABEL" if dist<=1 else "SPÄT"
    if not spread_ok or event:signal="NO TRADE"
    elif bias and reg not in {bias,"NEUTRAL"}:signal="CONTEXT CONFLICT"
    elif over and setup>=3:signal="HOT ENTRY"
    elif dist>1 and setup>=3:signal="LATE ENTRY"
    elif bias and has3 and setup>=3 and trigger>=3 and score>=80:signal=("CONFIRMED " if score>=85 else "EARLY ")+side
    elif bias and setup>=3:signal="PRE-"+side
    elif bias:signal="WATCH "+side
    else:signal="WAIT"
    risk=1.2*atr;stop=price-risk if side=="LONG" else price+risk;tp1=price+1.8*risk if side=="LONG" else price-1.8*risk;tp2=price+2.8*risk if side=="LONG" else price-2.8*risk;grade,hint=_grade(signal,score,float(r.ADX),dist,hot)
    row={"Asset":meta["name"],"Ticker":meta["ticker"],"Signal":signal,"Grade":grade,"Score":score,"60m Regime":reg,"15m Bias":bias or "NEUTRAL","5m Setup":f"{setup}/4","3m Trigger":f"{trigger}/4" if has3 else "FALLBACK","Entry Status":entry,"Setup-Hinweis":hint,"Basiswert ISIN":BASISWERT_IDS.get(meta["ticker"],""),"RSI":float(r.RSI),"ADX":float(r.ADX),"ATR %":atr/price*100,"EMA20 ATR":dist,"Entry":price,"Stop":stop,"TP1":tp1,"TP2":tp2,"CRV":1.8,"Signalzeit":str(d5.index[-1])}
    return row
