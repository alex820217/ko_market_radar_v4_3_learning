MARKET_GROUPS = {
    "Deutschland": {"DAX":"^GDAXI","SAP":"SAP.DE","Siemens":"SIE.DE","Allianz":"ALV.DE","Deutsche Telekom":"DTE.DE","Airbus":"AIR.DE","Rheinmetall":"RHM.DE","Mercedes-Benz":"MBG.DE","BMW":"BMW.DE","BASF":"BAS.DE","Infineon":"IFX.DE","Deutsche Bank":"DBK.DE","Commerzbank":"CBK.DE","Adidas":"ADS.DE","Vonovia":"VNA.DE","DHL Group":"DHL.DE"},
    "US Tech": {"Microsoft":"MSFT","Apple":"AAPL","NVIDIA":"NVDA","Amazon":"AMZN","Meta":"META","Alphabet":"GOOGL","Tesla":"TSLA","AMD":"AMD","Broadcom":"AVGO","Netflix":"NFLX","Palantir":"PLTR","Micron":"MU","Qualcomm":"QCOM","Intel":"INTC","Adobe":"ADBE","Salesforce":"CRM"},
    "Indizes": {"Nasdaq 100":"^NDX","S&P 500":"^GSPC","Dow Jones":"^DJI","Euro Stoxx 50":"^STOXX50E","Russell 2000":"^RUT"},
    "Metalle": {"Gold":"GC=F","Silber":"SI=F","Kupfer":"HG=F","Platin":"PL=F"},
    "Energie": {"WTI Öl":"CL=F","Brent Öl":"BZ=F","Natural Gas":"NG=F","Heizöl":"HO=F"},
}
BASISWERT_IDS={"NVDA":"US67066G1040","MSFT":"US5949181045","AAPL":"US0378331005","AMZN":"US0231351067","META":"US30303M1027","GOOGL":"US02079K3059","TSLA":"US88160R1014","AMD":"US0079031078","AIR.DE":"NL0000235190","RHM.DE":"DE0007030009","VNA.DE":"DE000A1ML7J1","ALV.DE":"DE0008404005","DTE.DE":"DE0005557508","SAP.DE":"DE0007164600","BAS.DE":"DE000BASF111","IFX.DE":"DE0006231004","DBK.DE":"DE0005140008","CBK.DE":"DE000CBK1001","ADS.DE":"DE000A1EWWW0","DHL.DE":"DE0005552004","^GDAXI":"DE0008469008","^STOXX50E":"EU0009658145","^GSPC":"US78378X1072"}

def build_universe(groups):
    out=[];seen=set()
    for group in groups:
        for name,ticker in MARKET_GROUPS[group].items():
            if ticker not in seen:out.append({"group":group,"name":name,"ticker":ticker});seen.add(ticker)
    return out
