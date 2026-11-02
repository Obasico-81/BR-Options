"""Calibração: |delta| (Black-Scholes, IV do próprio preço) no dia da entrada vs frequência real de terminar no dinheiro."""
import pandas as pd, numpy as np, pickle, warnings; warnings.filterwarnings("ignore")
from delta_iv_lib import ivf, delta
rows=[]
for at in ("bova","petr","vale","bbas","bbdc","itub"):
    ser=pickle.load(open(f"/tmp/claude-0/ser_{at}1525.pkl","rb")).S
    o=pd.read_csv(f"/tmp/claude-0/{at.upper()}_opc_1525.csv",parse_dates=["refdate","maturity_date"],low_memory=False,usecols=["refdate","instrument_market","maturity_date","strike_price","best_bid","best_ask","traded_contracts"])
    o=o[o.instrument_market.isin([70,80])&(o.best_bid>0)&(o.best_ask>=o.best_bid)&(o.traded_contracts>=1000)].copy()
    o["dias"]=(o.maturity_date-o.refdate).dt.days; o=o[o.dias.between(30,60)]
    o["mid"]=(o.best_ask+o.best_bid)/2; o["sp"]=(o.best_ask-o.best_bid)/o.mid; o=o[o.sp<=0.10]
    o=o[o.refdate.dt.dayofyear%5==0]   # amostra para acelerar
    for r in o.itertuples():
        if r.refdate not in ser.index: continue
        S=ser[r.refdate]; tp="c" if r.instrument_market==70 else "p"
        if abs(r.strike_price/S-1)>0.15: continue
        v=ivf(r.mid,S,r.strike_price,r.dias/365,tp)
        if not np.isfinite(v): continue
        ix=ser.index.searchsorted(r.maturity_date,side="right")-1
        if ix<0 or ser.index[ix]<r.maturity_date-pd.Timedelta(days=4): continue
        ST=ser.iloc[ix]; itm=(ST>r.strike_price) if tp=="c" else (ST<r.strike_price)
        rows.append((at,tp,r.refdate,abs(delta(S,r.strike_price,r.dias/365,v,tp)),itm))
D=pd.DataFrame(rows,columns=["ativo","tp","ent","dl","itm"]); D.to_pickle("/tmp/claude-0/calib_delta.pkl")
D["faixa"]=pd.cut(D.dl,[0,.1,.2,.3,.4,.5,.6,.7,.8,1.0])
t=D.groupby("faixa",observed=True).agg(n=("itm","size"),delta_medio=("dl","mean"),freq_itm=("itm","mean")); t["dif"]=t.freq_itm-t.delta_medio
print(t.round(3).to_string()); print("\nPor tipo:"); print(D.groupby(["tp","faixa"],observed=True).agg(n=("itm","size"),dl=("dl","mean"),itm=("itm","mean")).round(3).to_string())
print("\nPor período:"); D["per"]=np.where(D.ent.dt.year<=2020,"2015-20","2021-25")
print(D.groupby(["per","faixa"],observed=True).agg(n=("itm","size"),dl=("dl","mean"),itm=("itm","mean")).round(3).to_string())
