"""Compara montador.py e montador.js no snapshot (snapshot.json da pasta atual), para todos os ativos.

Cobre: as 4 estruturas; o sinal (trava e put, 3 cenários); a compra simples no caminho padrão e nos 3 perfis
(Lucro maior · Equilibrada · Lucro frequente), com o theta; tudo duas vezes, sem corretagem cadastrada (margem
fixa) e com corretagem de R$ 5 por ordem. Uso: python3 paridade.py   (esperado: "0 falha(s)")
"""
import json, math, subprocess, sys
from montador import Opcao, montar, montar_sinal, montar_aposta, set_corretagem

r2 = lambda x: math.floor(x * 100 + 0.5) / 100   # mesmo arredondamento do Math.round do JS (o round do Python arredonda 5,885 para 5,88)
CORRETAGENS = (None, 5.0)
PERFIS = (None, "maior", "eq", "freq")
snap = json.load(open("snapshot.json"))


def resumo(m, theta=False):
    if isinstance(m, str):
        return m
    d = dict(lotes=m.lotes, premio=m.premio, perda=m.perda_max, ganho=m.ganho_max, eq=list(m.pontos_equilibrio), prob=m.prob_implicita,
             custo=m.custo_total, alvo=m.alvo or 0, stop=m.stop or 0, ks=[(l, o.tipo, o.strike, o.dias) for l, o in m.pernas])
    if theta:
        d["theta"] = m.theta_dia
    return d


def lado_python(cor):
    set_corretagem(cor); res = {}
    for nome, a in snap["ativos"].items():
        ch = [Opcao(o["t"], o["k"], o["b"], o["a"], o["v"], o["d"]) for o in a["chain"]]
        for tese in ("alta", "baixa", "forte", "alta_com_caixa"):
            res[f"{nome}/{tese}"] = resumo(montar(tese, a["S"], ch, a["iv"], perda_aceita=300, caixa=30000))
        for est in ("trava", "put"):
            for nm, ent, al, pz in (("ok", a["S"], r2(a["S"] * 1.10), 30), ("espera", a["S"] * 0.95, r2(a["S"] * 1.10), 30), ("longo", a["S"], r2(a["S"] * 1.10), 120)):
                res[f"{nome}/sinal_{est}_{nm}"] = resumo(montar_sinal(a["S"], ch, a["iv"], 300, ent, al, pz, estrutura=est, caixa=30000))
        for lado in ("alta", "baixa"):
            for pf in PERFIS:
                for nm, val in (("ok", 1500), ("pouco", 20)):
                    res[f"{nome}/compra_{lado}_{pf or 'padrao'}_{nm}"] = resumo(montar_aposta(lado, a["S"], ch, a["iv"], val, perfil=pf), theta=True)
    set_corretagem(None)
    return res


JS = """
const M=require('./montador.js'),s=require('./snapshot.json'),cor=JSON.parse(process.argv[1]),out={};
const r2=(x)=>Math.round(x*100)/100;
const res=(m,theta)=>{ if(typeof m==='string') return m;
  const d={lotes:m.lotes,premio:m.premio,perda:m.perdaMax,ganho:m.ganhoMax,eq:m.equilibrio,prob:m.probImplicita,custo:m.custoTotal,alvo:m.alvo||0,stop:m.stop||0,ks:m.pernas.map(([l,o])=>[l,o.t,o.k,o.d])};
  if(theta) d.theta=m.thetaDia; return d; };
M.setCorretagem(cor);
for(const [n,a] of Object.entries(s.ativos)){
  for(const t of ['alta','baixa','forte','alta_com_caixa']) out[n+'/'+t]=res(M.montar(t,a.S,a.chain,a.iv,300,{caixa:30000}));
  for(const est of ['trava','put']) for(const [nm,ent,al,pz] of [['ok',a.S,r2(a.S*1.10),30],['espera',a.S*0.95,r2(a.S*1.10),30],['longo',a.S,r2(a.S*1.10),120]])
    out[n+'/sinal_'+est+'_'+nm]=res(M.montarSinal(a.S,a.chain,a.iv,300,ent,al,pz,{estrutura:est,caixa:30000}));
  for(const lado of ['alta','baixa']) for(const pf of [null,'maior','eq','freq']) for(const [nm,val] of [['ok',1500],['pouco',20]])
    out[n+'/compra_'+lado+'_'+(pf||'padrao')+'_'+nm]=res(M.montarAposta(lado,a.S,a.chain,a.iv,val,pf?{perfil:pf}:{}),true);
}
console.log(JSON.stringify(out));
"""


def lado_js(cor):
    js = subprocess.run(["node", "-e", JS, json.dumps(cor)], capture_output=True, text=True)
    if js.returncode:
        print(js.stderr); sys.exit(1)
    return json.loads(js.stdout)


perto = lambda a, b, tol=0.011: (a is None and b is None) or (a is not None and b is not None and abs(a - b) < tol)
falhas = casos = montados = 0
for cor in CORRETAGENS:
    py, js = lado_python(cor), lado_js(cor)
    rotulo = "sem corretagem" if cor is None else f"corretagem R$ {cor:.2f}"
    for k, v in py.items():
        j = js[k]; casos += 1
        if isinstance(v, str) or isinstance(j, str):
            ok = v == j or (isinstance(v, str) and isinstance(j, str) and v.split(":")[0] == j.split(":")[0])
            if not ok: print("ERRO", rotulo, k, "| py:", v, "| js:", j)
            falhas += 0 if ok else 1; continue
        montados += 1
        ok = all(perto(v[f], j[f]) for f in ("lotes", "premio", "perda", "custo", "stop", "alvo")) and (v["ganho"] is None) == (j["ganho"] is None) \
            and all(perto(a, b) for a, b in zip(v["eq"], j["eq"])) and abs(v["prob"] - j["prob"]) < 0.002 and [list(x) for x in v["ks"]] == j["ks"] \
            and ("theta" not in v or perto(v["theta"], j["theta"]))
        if not ok: print("ERRO", rotulo, k, "| py:", v, "| js:", j)
        falhas += 0 if ok else 1
print(f"{casos} casos ({montados} montados) em {len(snap['ativos'])} ativos, sem e com corretagem: {falhas} falha(s)")
sys.exit(1 if falhas else 0)
