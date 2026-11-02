"""Gregas complementares ao delta: theta, vega, gama (como % do prêmio) e 'movimento necessário / esperado'.
Para cada compra simples (call/put, 30-60d, líquida), mede se o terço do sinal dentro da MESMA faixa de delta separa o retorno. Cortes só com o passado (walk-forward)."""
import pandas as pd, numpy as np, pickle, warnings; warnings.filterwarnings("ignore")
import os; DADOS=os.environ.get("DADOS","/tmp/claude-0"); SUF=os.environ.get("SUF","1525")   # pasta e sufixo dos dados
from scipy.stats import norm
from delta_iv_lib import ivf
R=0.10
rows=[]
for at in ("bova","petr","vale","bbas","bbdc","itub"):
    ser=pickle.load(open(f"{DADOS}/ser_{at}{SUF}.pkl","rb")).S.dropna(); lr=np.log(ser).diff(); rv60=lr.rolling(60).std()*np.sqrt(252)
    o=pd.read_csv(f"{DADOS}/{at.upper()}_opc_{SUF}.csv",parse_dates=["refdate","maturity_date"],low_memory=False,usecols=["refdate","instrument_market","maturity_date","strike_price","best_bid","best_ask","traded_contracts"])
    o=o[o.instrument_market.isin([70,80])&(o.best_bid>0)&(o.best_ask>=o.best_bid)&(o.traded_contracts>=1000)].copy()
    o["dias"]=(o.maturity_date-o.refdate).dt.days; o=o[o.dias.between(30,60)]
    o["mid"]=(o.best_ask+o.best_bid)/2; o["sp"]=(o.best_ask-o.best_bid)/o.mid; o=o[(o.sp<=0.10)&(o.best_ask>=0.05)&(o.refdate.dt.dayofyear%3==0)]
    for r in o.itertuples():
        if r.refdate not in ser.index: continue
        S=ser[r.refdate]; tp="c" if r.instrument_market==70 else "p"; K=r.strike_price; T=r.dias/365
        if abs(K/S-1)>0.20: continue
        v=ivf(r.mid,S,K,T,tp)
        if not np.isfinite(v): continue
        ix=ser.index.searchsorted(r.maturity_date,side="right")-1
        if ser.index[ix]<r.maturity_date-pd.Timedelta(days=4): continue
        ST=ser.iloc[ix]; pay=max(ST-K,0) if tp=="c" else max(K-ST,0); ask=r.best_ask
        d1=(np.log(S/K)+(R+v*v/2)*T)/(v*np.sqrt(T)); d2=d1-v*np.sqrt(T)
        dl=norm.cdf(d1) if tp=="c" else 1-norm.cdf(d1)
        gama=norm.pdf(d1)/(S*v*np.sqrt(T)); vega=S*norm.pdf(d1)*np.sqrt(T)/100
        th=(-S*norm.pdf(d1)*v/(2*np.sqrt(T)) - (R*K*np.exp(-R*T)*norm.cdf(d2) if tp=="c" else -R*K*np.exp(-R*T)*norm.cdf(-d2)))/365
        eq=(K+ask) if tp=="c" else (K-ask); need=abs(eq-S)/S; rv=rv60.get(r.refdate,np.nan)
        pnl=(pay-ask)*100-2.0-0.00134*(ask+pay)*100
        rows.append(dict(ativo=at,tp=tp,ent=r.refdate,dl=dl,iv=v,rv=rv,theta_pct=-th/ask*100,vega_pct=vega/ask*100,gama_rel=gama*S*0.01/dl if dl>0 else np.nan,need=need,exp_move=rv*np.sqrt(T) if rv==rv else np.nan,ivrv=v/rv if rv==rv else np.nan,ret=pnl/(ask*100)))
    print(at,flush=True)
D=pd.DataFrame(rows).sort_values("ent").reset_index(drop=True); D["razao_mov"]=D.need/D.exp_move; D["mes"]=D.ent.dt.to_period("M"); D.to_pickle(f"{DADOS}/gregas.pkl")
print(len(D), "operações;", int((D.ent.dt.year<=2025).sum()), "até 2025 e", int((D.ent.dt.year>=2026).sum()), "em 2026")
D["faixa"]=pd.cut(D.dl,[0,.25,.40,.60,.80,1.0],labels=["0-.25","25-.40","40-.60","60-.80",".80+"])
sinais={"theta_pct":"theta/prêmio %/dia (maior = decai mais rápido)","vega_pct":"vega/prêmio (maior = mais sensível à IV)","gama_rel":"gama relativo","razao_mov":"movimento necessário / esperado (maior = mais difícil)","ivrv":"IV / vol realizada 60d"}
rng=np.random.default_rng(7)
def ic(g):
    s=g.groupby("mes").ret.sum().values; c=g.groupby("mes").ret.size().values; m=[]
    for _ in range(1000): k=rng.integers(0,len(s),len(s)); m.append(s[k].sum()/c[k].sum())
    return np.percentile(m,[2.5,97.5])
res=[]; T={}
for sg,desc in sinais.items():
    t=np.full(len(D),np.nan); 
    for fx,g in D.groupby("faixa",observed=True):            # terços dentro da faixa de delta, só com passado da mesma faixa
        v=g[sg].values; idx=g.index.values
        for j in range(len(g)):
            if not np.isfinite(v[j]): continue
            prev=v[:j][np.isfinite(v[:j])]
            if len(prev)<150: continue
            q1,q2=np.quantile(prev,[1/3,2/3]); t[idx[j]]=0 if v[j]<=q1 else (1 if v[j]<=q2 else 2)
    D["t"]=t; T[sg]=t.copy(); a=D.dropna(subset=["t"]); a=a[a.ent.dt.year<=2025]   # linha de base: entradas 2015-2025
    m0=a[a.t==0].ret.mean(); m2=a[a.t==2].ret.mean()
    # diferença bootstrap (terço alto - baixo) por blocos mensais
    ms=sorted(a.mes.unique()); by={m:a[a.mes==m] for m in ms}; dif=[]
    for _ in range(800):
        s=pd.concat([by[ms[k]] for k in rng.integers(0,len(ms),len(ms))]); dif.append(s[s.t==2].ret.mean()-s[s.t==0].ret.mean())
    lo,hi=np.percentile(dif,[2.5,97.5]); sp=a[sg].corr(a.ret,method="spearman")
    per=a.assign(p=np.where(a.ent.dt.year<=2020,"15-20","21-25")); d_p=per.groupby("p").apply(lambda g:g[g.t==2].ret.mean()-g[g.t==0].ret.mean(),include_groups=False)
    res.append(dict(sinal=sg,n=len(a),ret_t0=100*m0,ret_t1=100*a[a.t==1].ret.mean(),ret_t2=100*m2,dif_alto_baixo=100*(m2-m0),ic_lo=100*lo,ic_hi=100*hi,spearman=sp,dif_15_20=100*d_p.get("15-20",np.nan),dif_21_25=100*d_p.get("21-25",np.nan)))
pd.set_option("display.width",230); pd.set_option("display.float_format",lambda v:f"{v:,.1f}")
print("\nRetorno médio % por terço do sinal (0 baixo, 2 alto), dentro de cada faixa de delta; diferença alto-baixo com IC 95% (bootstrap mensal):")
print(pd.DataFrame(res).to_string(index=False))
print("\nOutros:",sinais)
# --- Fora da amostra: entradas em 2026, terços com o mesmo corte walk-forward (só passado), nada reajustado
res26=[]
for sg in sinais:
    D["t"]=T[sg]; a=D.dropna(subset=["t"]); a=a[a.ent.dt.year>=2026]
    if not len(a): continue
    m0=a[a.t==0].ret.mean(); m2=a[a.t==2].ret.mean()
    ms=sorted(a.mes.unique()); by={m:a[a.mes==m] for m in ms}; dif=[]
    for _ in range(800):
        s_=pd.concat([by[ms[k]] for k in rng.integers(0,len(ms),len(ms))]); dif.append(s_[s_.t==2].ret.mean()-s_[s_.t==0].ret.mean())
    lo,hi=np.nanpercentile(dif,[2.5,97.5])
    res26.append(dict(sinal=sg,n=len(a),meses=len(ms),n_t0=int((a.t==0).sum()),n_t2=int((a.t==2).sum()),ret_t0=100*m0,ret_t1=100*a[a.t==1].ret.mean(),ret_t2=100*m2,dif_alto_baixo=100*(m2-m0),ic_lo=100*lo,ic_hi=100*hi,spearman=a[sg].corr(a.ret,method="spearman")))
print("\n=== Fora da amostra: entradas em 2026 (mesmo sinal, mesmos cortes walk-forward) ===")
print(pd.DataFrame(res26).to_string(index=False) if res26 else "Sem operações de 2026 com vencimento já ocorrido nos dados.")
