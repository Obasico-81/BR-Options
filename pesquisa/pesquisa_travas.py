"""Travas de débito (alta com calls, baixa com puts) 30-60d, comprada ATM e vendida ~6% OTM; execução ask/bid; custos B3 + R$2/perna ida e volta.
Sinal de contexto: IV rank (walk-forward, terços) vindo de vrp.pkl. Resultado = retorno sobre o débito (perda máxima)."""
import pandas as pd, numpy as np, pickle, warnings; warnings.filterwarnings("ignore")
import os; DADOS=os.environ.get("DADOS","/tmp/claude-0"); SUF=os.environ.get("SUF","1525")   # pasta e sufixo dos dados
V=pd.read_pickle(f"{DADOS}/vrp.pkl")[["ativo","ent","iv","ivrank","rv60"]]
rows=[]
for at in ("bova","petr","vale","bbas","bbdc","itub"):
    ser=pickle.load(open(f"{DADOS}/ser_{at}{SUF}.pkl","rb")).S.dropna()
    o=pd.read_csv(f"{DADOS}/{at.upper()}_opc_{SUF}.csv",parse_dates=["refdate","maturity_date"],low_memory=False,usecols=["refdate","instrument_market","maturity_date","strike_price","best_bid","best_ask","traded_contracts"])
    o=o[o.instrument_market.isin([70,80])&(o.best_bid>0)&(o.best_ask>=o.best_bid)&(o.traded_contracts>=100)].copy()
    o["dias"]=(o.maturity_date-o.refdate).dt.days; o=o[o.dias.between(30,60)]
    o["mid"]=(o.best_ask+o.best_bid)/2; o["sp"]=(o.best_ask-o.best_bid)/o.mid; o=o[o.sp<=0.15]
    for d,g in o.groupby("refdate"):
        if d not in ser.index: continue
        S=ser[d]; mat=g.iloc[(g.dias-45).abs().argsort().iloc[0]].maturity_date; g=g[g.maturity_date==mat]
        ix=ser.index.searchsorted(mat,side="right")-1
        if ser.index[ix]<mat-pd.Timedelta(days=4): continue
        ST=ser.iloc[ix]
        for nome,mk,sgn in (("alta",70,1),("baixa",80,-1)):
            x=g[g.instrument_market==mk]
            if len(x)<2: continue
            l=x.iloc[(x.strike_price/S-1).abs().argsort().iloc[0]]
            if abs(l.strike_price/S-1)>0.04: continue
            alvo=l.strike_price*(1+sgn*0.06)
            c=x[(x.strike_price*sgn>l.strike_price*sgn)]   # mais OTM que a comprada
            if c.empty: continue
            s=c.iloc[(c.strike_price/alvo-1).abs().argsort().iloc[0]]
            if abs(s.strike_price/alvo-1)>0.03: continue
            deb=l.best_ask-s.best_bid
            if deb<=0.05: continue
            pay=max(sgn*(ST-l.strike_price),0)-max(sgn*(ST-s.strike_price),0)
            pnl=(pay-deb)*100-4.0-0.00134*((l.best_ask+s.best_bid)+2*pay)*100/2*1.0
            rows.append(dict(ativo=at,ent=d,tipo=nome,deb=deb*100,pnl=pnl,ret=pnl/(deb*100),maxg=(abs(s.strike_price-l.strike_price)-deb)/deb))
    print(at,flush=True)
T=pd.DataFrame(rows).merge(V,on=["ativo","ent"],how="left").sort_values("ent").reset_index(drop=True)
T["mes"]=T.ent.dt.to_period("M"); T.to_pickle(f"{DADOS}/travas.pkl")
rng=np.random.default_rng(3)
def ic(g):
    s=g.groupby("mes").ret.sum().values; c=g.groupby("mes").ret.size().values; m=[]
    for _ in range(2000): k=rng.integers(0,len(s),len(s)); m.append(s[k].sum()/c[k].sum())
    return np.percentile(m,[2.5,97.5])
print("\n=== Sem sinal (todas as entradas) ===")
for tp,g in T.groupby("tipo"):
    lo,hi=ic(g); print(f"{tp}: n={len(g)} retorno médio={100*g.ret.mean():+.1f}% IC95%[{100*lo:+.1f},{100*hi:+.1f}] mediana={100*g.ret.median():+.0f}% acerto={100*(g.pnl>0).mean():.0f}% ganho máx. médio/perda={g.maxg.mean():.2f}")
print("\nPor ativo (retorno médio %):"); print((100*T.groupby(["tipo","ativo"]).ret.mean()).unstack().round(1).to_string())
print("\nPor ano (retorno médio %):"); print((100*T.assign(ano=T.ent.dt.year).groupby(["tipo","ano"]).ret.mean()).unstack(0).round(1).to_string())
# sinal IV rank walk-forward
v=T.ivrank.values; t=np.full(len(T),np.nan)
for i in range(len(T)):
    if not np.isfinite(v[i]): continue
    prev=v[:i][np.isfinite(v[:i])]
    if len(prev)<150: continue
    q1,q2=np.quantile(prev,[1/3,2/3]); t[i]=0 if v[i]<=q1 else (1 if v[i]<=q2 else 2)
T["t"]=t; a=T.dropna(subset=["t"])
print("\n=== Por terço de IV rank (0=IV baixa no ano, 2=alta), walk-forward ===")
for tp,g0 in a.groupby("tipo"):
    for k,g in g0.groupby("t"):
        lo,hi=ic(g); print(f"{tp} terço {int(k)}: n={len(g)} ret={100*g.ret.mean():+.1f}% IC95%[{100*lo:+.1f},{100*hi:+.1f}] acerto={100*(g.pnl>0).mean():.0f}%")
print("\nPor período, terço 0/1/2:"); print((100*a.assign(per=np.where(a.ent.dt.year<=2020,"2015-20","2021-25")).groupby(["tipo","per","t"]).ret.mean()).unstack().round(1).to_string())
print("\nTerço 0 por ativo (n, ret %):"); print(a[a.t==0].groupby(["tipo","ativo"]).ret.agg(["size","mean"]).assign(mean=lambda d:100*d["mean"]).round(1).to_string())
