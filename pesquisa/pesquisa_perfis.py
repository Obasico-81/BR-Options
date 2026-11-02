"""Perfis por delta: compra simples de call/put 30-60d, execução no ask, custos B3 + R$2 por ordem (ida), pagamento no vencimento.
Por faixa de |delta|: taxa de acerto, ganho médio/perda média, retorno médio sobre o prêmio (IC bootstrap mensal), maior sequência de perdas."""
import pandas as pd, numpy as np, pickle, warnings; warnings.filterwarnings("ignore")
from delta_iv_lib import ivf, delta
rows=[]
for at in ("bova","petr","vale","bbas","bbdc","itub"):
    ser=pickle.load(open(f"/tmp/claude-0/ser_{at}1525.pkl","rb")).S.dropna()
    o=pd.read_csv(f"/tmp/claude-0/{at.upper()}_opc_1525.csv",parse_dates=["refdate","maturity_date"],low_memory=False,usecols=["refdate","instrument_market","maturity_date","strike_price","best_bid","best_ask","traded_contracts"])
    o=o[o.instrument_market.isin([70,80])&(o.best_bid>0)&(o.best_ask>=o.best_bid)&(o.traded_contracts>=1000)].copy()
    o["dias"]=(o.maturity_date-o.refdate).dt.days; o=o[o.dias.between(30,60)]
    o["mid"]=(o.best_ask+o.best_bid)/2; o["sp"]=(o.best_ask-o.best_bid)/o.mid; o=o[(o.sp<=0.10)&(o.best_ask>=0.05)]
    o=o[o.refdate.dt.dayofyear%3==0]
    for r in o.itertuples():
        if r.refdate not in ser.index: continue
        S=ser[r.refdate]; tp="c" if r.instrument_market==70 else "p"
        if abs(r.strike_price/S-1)>0.20: continue
        v=ivf(r.mid,S,r.strike_price,r.dias/365,tp)
        if not np.isfinite(v): continue
        ix=ser.index.searchsorted(r.maturity_date,side="right")-1
        if ser.index[ix]<r.maturity_date-pd.Timedelta(days=4): continue
        ST=ser.iloc[ix]; pay=max(ST-r.strike_price,0) if tp=="c" else max(r.strike_price-ST,0)
        pnl=(pay-r.best_ask)*100-2.0-0.00134*(r.best_ask+pay)*100
        rows.append((at,tp,r.refdate,abs(delta(S,r.strike_price,r.dias/365,v,tp)),r.best_ask*100,pnl))
    print(at,flush=True)
D=pd.DataFrame(rows,columns=["ativo","tp","ent","dl","prem","pnl"]); D["ret"]=D.pnl/D.prem; D["mes"]=D.ent.dt.to_period("M"); D.to_pickle("/tmp/claude-0/perfis.pkl")
D["faixa"]=pd.cut(D.dl,[0,.15,.25,.35,.5,.65,.8,1.0]); rng=np.random.default_rng(5)
def ic(g):
    s=g.groupby("mes").ret.sum().values; c=g.groupby("mes").ret.size().values; m=[]
    for _ in range(1500): k=rng.integers(0,len(s),len(s)); m.append(s[k].sum()/c[k].sum())
    return np.percentile(m,[2.5,97.5])
def seq(g):
    x=(g.sort_values("ent").pnl<=0).values; best=cur=0
    for v in x: cur=cur+1 if v else 0; best=max(best,cur)
    return best
out=[]
for f,g in D.groupby("faixa",observed=True):
    w=g[g.pnl>0]; l=g[g.pnl<=0]; lo,hi=ic(g)
    out.append(dict(faixa=str(f),n=len(g),acerto=100*len(w)/len(g),ganho_medio_R=w.pnl.mean(),perda_media_R=l.pnl.mean(),razao=w.ret.mean()/abs(l.ret.mean()),ret_medio=100*g.ret.mean(),ic_lo=100*lo,ic_hi=100*hi,mediana=100*g.ret.median(),seq_perdas=seq(g)))
pd.set_option("display.width",220); pd.set_option("display.float_format",lambda v:f"{v:,.1f}")
print(pd.DataFrame(out).to_string(index=False))
print("\nPor período (retorno médio %):"); D["per"]=np.where(D.ent.dt.year<=2020,"2015-20","2021-25"); print((100*D.groupby(["per","faixa"],observed=True).ret.mean()).unstack(0).round(1).to_string())
print("\nPor tipo (retorno médio %):"); print((100*D.groupby(["tp","faixa"],observed=True).ret.mean()).unstack(0).round(1).to_string())
print("\nPor ativo, faixa delta <=0.25 (n, ret %):"); x=D[D.dl<=0.25]; print(x.groupby("ativo").ret.agg(n="size",ret=lambda s:100*s.mean()).round(1).to_string())
