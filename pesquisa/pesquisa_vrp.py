"""Prêmio de volatilidade: IV (ATM, 30-60d) vs volatilidade realizada até o vencimento; e se o sinal 'caro/barato' prevê o resultado de comprar call+put ATM.
Sinais (só passado): iv_rank252, razao = IV / RV60 passada. Cortes walk-forward (percentis da própria história até a data)."""
import pandas as pd, numpy as np, pickle, warnings; warnings.filterwarnings("ignore")
import os; DADOS=os.environ.get("DADOS","/tmp/claude-0"); SUF=os.environ.get("SUF","1525")   # pasta e sufixo dos dados
from delta_iv_lib import ivf
rows=[]
for at in ("bova","petr","vale","bbas","bbdc","itub"):
    ser=pickle.load(open(f"{DADOS}/ser_{at}{SUF}.pkl","rb")).S.dropna()
    lr=np.log(ser).diff()
    rv60=lr.rolling(60).std()*np.sqrt(252); rv20=lr.rolling(20).std()*np.sqrt(252)
    o=pd.read_csv(f"{DADOS}/{at.upper()}_opc_{SUF}.csv",parse_dates=["refdate","maturity_date"],low_memory=False,usecols=["refdate","instrument_market","maturity_date","strike_price","best_bid","best_ask","traded_contracts"])
    o=o[o.instrument_market.isin([70,80])&(o.best_bid>0)&(o.best_ask>=o.best_bid)&(o.traded_contracts>=100)].copy()
    o["dias"]=(o.maturity_date-o.refdate).dt.days; o=o[o.dias.between(30,60)]
    o["mid"]=(o.best_ask+o.best_bid)/2; o["sp"]=(o.best_ask-o.best_bid)/o.mid; o=o[o.sp<=0.15]
    for d,g in o.groupby("refdate"):
        if d not in ser.index: continue
        S=ser[d]; g=g.assign(m=(g.maturity_date-d).dt.days)
        mat=g.iloc[(g.dias-45).abs().argsort().iloc[0]].maturity_date; g=g[g.maturity_date==mat]
        c=g[(g.instrument_market==70)]; p=g[(g.instrument_market==80)]
        if c.empty or p.empty: continue
        c=c.iloc[(c.strike_price/S-1).abs().argsort().iloc[0]]; p=p.iloc[(p.strike_price/S-1).abs().argsort().iloc[0]]
        if abs(c.strike_price/S-1)>0.04 or abs(p.strike_price/S-1)>0.04: continue
        T=c.dias/365; ivc=ivf(c.mid,S,c.strike_price,T,"c"); ivp=ivf(p.mid,S,p.strike_price,T,"p")
        if not (np.isfinite(ivc) and np.isfinite(ivp)): continue
        ix=ser.index.searchsorted(mat,side="right")-1
        if ser.index[ix]<mat-pd.Timedelta(days=4): continue
        ST=ser.iloc[ix]; i0=ser.index.get_loc(d)
        seg=lr.iloc[i0+1:ix+1]
        if len(seg)<15: continue
        rvf=seg.std()*np.sqrt(252)
        cost=c.best_ask+p.best_ask; pay=max(ST-c.strike_price,0)+max(p.strike_price-ST,0)
        pnl=(pay-cost)*100-4.0-0.00134*(cost+pay)*100
        rows.append(dict(ativo=at,ent=d,iv=(ivc+ivp)/2,rvf=rvf,rv60=rv60.get(d,np.nan),rv20=rv20.get(d,np.nan),ret=pnl/(cost*100),pnl=pnl,risco=cost*100))
    print(at,sum(r["ativo"]==at for r in rows),flush=True)
D=pd.DataFrame(rows).sort_values("ent").reset_index(drop=True)
# IV rank 252 pregões por ativo (só passado)
D["ivrank"]=np.nan
for at,g in D.groupby("ativo"):
    s=g.set_index("ent").iv; lo=s.rolling(252,min_periods=150).min(); hi=s.rolling(252,min_periods=150).max()
    D.loc[g.index,"ivrank"]=((s-lo)/(hi-lo)).values
D["razao"]=D.iv/D.rv60; D["vrp"]=D.iv-D.rvf; D["vrp_rel"]=D.iv/D.rvf
D.to_pickle(f"{DADOS}/vrp.pkl")
pd.set_option("display.width",200); pd.set_option("display.float_format",lambda v:f"{v:,.3f}")
print("\nN",len(D),"| IV média",D.iv.mean().round(3),"| RV realizada média",D.rvf.mean().round(3),"| IV/RVfwd mediana",D.vrp_rel.median().round(3),"| % dias com IV>RVfwd",(D.vrp>0).mean().round(3))
print("\nPrêmio de volatilidade (IV-RV realizada) por ativo:"); print(D.groupby("ativo").agg(n=("iv","size"),iv=("iv","mean"),rvf=("rvf","mean"),vrp=("vrp","mean"),ret_straddle=("ret","mean")).to_string())
D["ano"]=D.ent.dt.year; print("\nPor ano:"); print(D.groupby("ano").agg(n=("iv","size"),vrp=("vrp","mean"),ret=("ret","mean")).to_string())
# walk-forward: cortes de terço a partir do passado (>=150 obs prévias)
def wf(col):
    out=[]; v=D[col].values; 
    for i in range(len(D)):
        if not np.isfinite(v[i]): out.append(np.nan); continue
        prev=v[:i][np.isfinite(v[:i])]
        if len(prev)<150: out.append(np.nan); continue
        q1,q2=np.quantile(prev,[1/3,2/3]); out.append(0 if v[i]<=q1 else (1 if v[i]<=q2 else 2))
    return np.array(out)
rng=np.random.default_rng(1)
def boot(x,m,B=2000):
    # bootstrap em blocos mensais (observações próximas se repetem)
    g=pd.Series(x).groupby(m.values); sums=g.sum().values; cnt=g.size().values
    ms=[]; 
    for _ in range(B):
        k=rng.integers(0,len(sums),len(sums)); ms.append(sums[k].sum()/cnt[k].sum())
    return np.percentile(ms,[2.5,97.5])
D["mes"]=D.ent.dt.to_period("M")
for col in ("ivrank","razao"):
    D["t_"+col]=wf(col); a=D.dropna(subset=["t_"+col])
    print(f"\n=== Sinal {col} (terços walk-forward; 0=barata/baixa, 2=cara/alta) | n={len(a)}")
    for tcl,g in a.groupby("t_"+col):
        lo,hi=boot(g.ret.values,g.mes)
        print(f" terço {int(tcl)}: n={len(g):4d} VRP médio={g.vrp.mean():+.3f}  retorno médio call+put={100*g.ret.mean():+6.1f}%  IC95%[{100*lo:+.1f},{100*hi:+.1f}]  acerto={100*(g.pnl>0).mean():.0f}%")
    print(" por período (retorno médio %, terço 0/1/2):")
    a=a.assign(per=np.where(a.ent.dt.year<=2020,"2015-20","2021-25"))
    print((100*a.groupby(["per","t_"+col]).ret.mean()).unstack().round(1).to_string())
print("\nCorrelação (Spearman) sinal -> retorno e sinal -> VRP:")
for col in ("ivrank","razao"):
    a=D.dropna(subset=[col]); print(col,"vs ret",a[col].corr(a.ret,method="spearman").round(3),"| vs vrp",a[col].corr(a.vrp,method="spearman").round(3))
