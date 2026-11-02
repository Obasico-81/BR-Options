"""Compara montador.py e montador.js no snapshot, para todos ativos e teses."""
import json, math, subprocess, sys
r2 = lambda x: math.floor(x * 100 + 0.5) / 100   # mesmo arredondamento do Math.round do JS (o round do Python arredonda 5,885 para 5,88)
sys.path.insert(0, "..")
from montador import Opcao, montar, montar_sinal, montar_aposta
snap = json.load(open("snapshot.json")); res = {}
for nome, a in snap["ativos"].items():
    ch = [Opcao(o["t"], o["k"], o["b"], o["a"], o["v"], o["d"]) for o in a["chain"]]
    for tese in ("alta", "baixa", "forte", "alta_com_caixa"):
        m = montar(tese, a["S"], ch, a["iv"], perda_aceita=300, caixa=30000)
        res[f"{nome}/{tese}"] = m if isinstance(m, str) else dict(lotes=m.lotes, premio=m.premio, perda=m.perda_max, ganho=m.ganho_max, eq=list(m.pontos_equilibrio), prob=m.prob_implicita, custo=m.custo_total, alvo=m.alvo, stop=m.stop, ks=[(l, o.tipo, o.strike) for l, o in m.pernas])
    for est in ("trava", "put"):
        for nm, ent, al, pz in (("ok", a["S"], r2(a["S"] * 1.10), 30), ("espera", a["S"] * 0.95, r2(a["S"] * 1.10), 30), ("longo", a["S"], r2(a["S"] * 1.10), 120)):
            m = montar_sinal(a["S"], ch, a["iv"], 300, ent, al, pz, estrutura=est, caixa=30000)
            res[f"{nome}/sinal_{est}_{nm}"] = m if isinstance(m, str) else dict(lotes=m.lotes, premio=m.premio, perda=m.perda_max, ganho=m.ganho_max, eq=list(m.pontos_equilibrio), prob=m.prob_implicita, custo=m.custo_total, alvo=m.alvo, stop=m.stop, ks=[(l, o.tipo, o.strike) for l, o in m.pernas])
    for lado in ("alta", "baixa"):
        for nm, val in (("ok", 1500), ("pouco", 20)):
            m = montar_aposta(lado, a["S"], ch, a["iv"], val)
            res[f"{nome}/aposta_{lado}_{nm}"] = m if isinstance(m, str) else dict(lotes=m.lotes, premio=m.premio, perda=m.perda_max, ganho=m.ganho_max, eq=list(m.pontos_equilibrio), prob=m.prob_implicita, custo=m.custo_total, alvo=0, stop=0, ks=[(l, o.tipo, o.strike) for l, o in m.pernas])

js = subprocess.run(["node", "-e", """
const M=require('./montador.js'),s=require('./snapshot.json'),out={};
for(const [n,a] of Object.entries(s.ativos)) for(const t of ['alta','baixa','forte','alta_com_caixa']){
 const m=M.montar(t,a.S,a.chain,a.iv,300,{caixa:30000});
 out[n+'/'+t]= typeof m==='string'? m : {lotes:m.lotes,premio:m.premio,perda:m.perdaMax,ganho:m.ganhoMax,eq:m.equilibrio,prob:m.probImplicita,custo:m.custoTotal,alvo:m.alvo,stop:m.stop,ks:m.pernas.map(([l,o])=>[l,o.t,o.k])};}
for(const [n,a] of Object.entries(s.ativos)) for(const est of ['trava','put']) for(const [nm,ent,al,pz] of [['ok',a.S,Math.round(a.S*1.10*100)/100,30],['espera',a.S*0.95,Math.round(a.S*1.10*100)/100,30],['longo',a.S,Math.round(a.S*1.10*100)/100,120]]){
 const m=M.montarSinal(a.S,a.chain,a.iv,300,ent,al,pz,{estrutura:est,caixa:30000});
 out[n+'/sinal_'+est+'_'+nm]= typeof m==='string'? m : {lotes:m.lotes,premio:m.premio,perda:m.perdaMax,ganho:m.ganhoMax,eq:m.equilibrio,prob:m.probImplicita,custo:m.custoTotal,alvo:m.alvo,stop:m.stop,ks:m.pernas.map(([l,o])=>[l,o.t,o.k])};}
for(const [n,a] of Object.entries(s.ativos)) for(const lado of ['alta','baixa']) for(const [nm,val] of [['ok',1500],['pouco',20]]){
 const m=M.montarAposta(lado,a.S,a.chain,a.iv,val);
 out[n+'/aposta_'+lado+'_'+nm]= typeof m==='string'? m : {lotes:m.lotes,premio:m.premio,perda:m.perdaMax,ganho:m.ganhoMax,eq:m.equilibrio,prob:m.probImplicita,custo:m.custoTotal,alvo:0,stop:0,ks:m.pernas.map(([l,o])=>[l,o.t,o.k])};}
console.log(JSON.stringify(out));"""], capture_output=True, text=True); 
if js.returncode: print(js.stderr); sys.exit(1)
jr = json.loads(js.stdout); falhas = 0
for k, v in res.items():
    j = jr[k]
    if isinstance(v, str) or isinstance(j, str):
        ok = v == j or (isinstance(v, str) and isinstance(j, str) and v.split(":")[0] == j.split(":")[0]); print(("OK  " if ok else "ERRO"), k, v if isinstance(v, str) else "montado"); falhas += 0 if ok else 1; continue
    ok = all(abs(v[f] - j[f]) < 0.011 for f in ("lotes", "premio", "perda", "custo", "stop")) and (v["ganho"] is None) == (j["ganho"] is None) \
        and all(abs(a - b) < 0.011 for a, b in zip(v["eq"], j["eq"])) and abs(v["prob"] - j["prob"]) < 0.002 and [list(x) for x in v["ks"]] == j["ks"]
    print(("OK  " if ok else "ERRO"), k, f"lotes {v['lotes']} premio {v['premio']} perda {v['perda']} prob {v['prob']}" + ("" if ok else f" | js {j}")); falhas += 0 if ok else 1
print(falhas, "falha(s)"); sys.exit(1 if falhas else 0)
