"""Compara montador.py e montador.js no snapshot (snapshot.json da pasta atual), para todos os ativos.

Cobre: as 4 estruturas; o sinal (trava e put, 3 cenários); a compra simples no caminho padrão e nos 3 perfis
(Lucro maior · Equilibrada · Lucro frequente), com o theta; o movimento necessário × oscilação de 60 pregões em todo
caso montado e a volatilidade de 60 pregões em 3 datas por ativo; a marcação diária ("Se encerrar hoje" com os preços
do dia, com preços 7% mais altos e sem o preço de uma perna) e a regra de saída em duas sequências de dias; os custos separados (spread,
taxas da B3, corretagem por ordem e total); a operação real (execucao: outra quantidade e preços executados); a tendência do minigráfico (sem e com IFR) em séries sintéticas e, se o snapshot tiver máximas e mínimas, em 3 datas por ativo; a trava com preço de fechamento impossível, em cadeias sintéticas; tudo duas vezes, sem corretagem cadastrada e com corretagem de R$ 5 por ordem. Uso: python3 paridade.py   (esperado: "0 falha(s)")
"""
import json, math, subprocess, sys
from datetime import date, timedelta
from montador import Opcao, montar, montar_sinal, montar_aposta, set_corretagem, vol_real_60, movimento_necessario, resultado_no_dia, regra_de_saida, execucao, tendencia

r2 = lambda x: math.floor(x * 100 + 0.5) / 100   # mesmo arredondamento do Math.round do JS (o round do Python arredonda 5,885 para 5,88)
CORRETAGENS = (None, 5.0)
PERFIS = (None, "maior", "eq", "freq")
snap = json.load(open("snapshot.json"))
# preços do dia de cada ativo: os da própria cadeia e os mesmos 7% mais altos (montados igual no JS)
PRECOS = {n: ({o["s"]: [o["b"], o["a"]] for o in a["chain"]}, {o["s"]: [r2(o["b"] * 1.07), r2(o["a"] * 1.07)] for o in a["chain"]})
          for n, a in snap["ativos"].items()}
FATORES = (0.1, -0.2, 0.3, None, -0.5, 0.6, -0.8, 0.9, -1.0, 1.2)
add_dias = lambda iso, n: (date.fromisoformat(iso) + timedelta(days=n)).isoformat()
# cadeias sintéticas (S = 10) com trava de preço impossível: crédito na entrada; débito zero; débito igual ou maior que a distância entre os
# strikes; e o 1º vencimento impossível com o 2º bom (a montagem tem de seguir para o 2º). (t, k, compra, venda, volume, dias, símbolo)
CRED = [("C", 10.0, 0.20, 0.22, 1000, 45, "SINTA100"), ("C", 10.5, 0.60, 0.66, 1000, 45, "SINTA105")]
SINT = {"credito": CRED,
        "zero": [("C", 10.0, 0.40, 0.44, 1000, 45, "SINTD100"), ("C", 10.5, 0.44, 0.48, 1000, 45, "SINTD105")],
        "igual": [("C", 10.0, 0.90, 1.00, 1000, 45, "SINTE100"), ("C", 10.5, 0.50, 0.55, 1000, 45, "SINTE105")],
        "largura": [("C", 10.0, 0.90, 1.00, 1000, 45, "SINTB100"), ("C", 10.5, 0.45, 0.50, 1000, 45, "SINTB105")],
        "segue": CRED + [("C", 10.0, 0.40, 0.44, 1000, 50, "SINTC100"), ("C", 10.5, 0.20, 0.22, 1000, 50, "SINTC105")]}


def serie_tend(tipo, n=170):
    """Série sintética de pregões para a tendência: {fech, maxmin, ate}. Semente fixa por tipo."""
    import random
    rnd, S, ds, d = random.Random(tipo), 10.0, [], date(2026, 1, 2)
    if tipo.startswith("ifr_"):   # forma fixa em que o IFR muda a cor: tendência longa, 9 pregões contra, 5 a favor
        sg, fe, mm = (1 if tipo == "ifr_q" else -1), {}, {}
        while len(ds) < 150:
            if d.weekday() < 5: ds.append(d.isoformat())
            d += timedelta(days=1)
        for i, x in enumerate(ds):
            S *= 1 + sg * (0.003 if i < 136 else -0.02 if i < 145 else 0.02)
            fe[x] = round(S, 4); mm[x] = [round(S * 1.004, 4), round(S * 0.996, 4)]
        return {"fech": fe, "maxmin": mm, "ate": ds[-1]}
    while len(ds) < (59 if tipo == "curta" else n):
        if d.weekday() < 5: ds.append(d.isoformat())
        d += timedelta(days=1)
    fe, mm = {}, {}
    for i, x in enumerate(ds):
        if tipo != "plana":
            S *= math.exp({"alta": 0.004, "queda": -0.004, "buracos": 0.004}.get(tipo, 0.0) + rnd.gauss(0, 0.01))
        c = round(S, 2); h = c if tipo == "plana" else round(c * (1 + abs(rnd.gauss(0, 0.008))), 2)
        lo = c if tipo == "plana" else round(c * (1 - abs(rnd.gauss(0, 0.008))), 2)
        fe[x] = c
        if not (tipo == "buracos" and i % 7 == 3): mm[x] = [h, lo]
    return {"fech": fe, "maxmin": mm, "ate": ds[100] if tipo == "meio" else ds[-1]}


TEND = {t: serie_tend(t) for t in ("alta", "queda", "lateral", "plana", "curta", "buracos", "meio", "ifr_q", "ifr_a")}


def marcas(perda, dias, pequenas):
    """Fechamentos até depois do vencimento; resultado = fator × risco máximo. Sem `pequenas`: a cada 5 dias, fatores que
    batem alvo ou limite. Com `pequenas`: todo dia, ±1% do risco (não batem alvo nem limite), e a regra que dispara é o
    prazo, no primeiro dia a partir de vencimento − dias de saída (um dia a mais ou a menos muda o resultado)."""
    passo = 1 if pequenas else 5
    out, i = [], 1
    while passo * i <= dias + 5:
        f = 0.01 * (-1) ** i if pequenas else FATORES[(i - 1) % len(FATORES)]
        out.append({"d": add_dias(snap["data"], passo * i), "r": None if f is None else f * perda}); i += 1
    return out


def datas_vol(nome):
    """Datas para testar a vol. de 60 pregões: último dia, o dia com 21 fechamentos (mínimo) e o com 20 (dá None)."""
    ds = sorted(snap["fechamentos"][nome]); return {"fim": snap["data"], "21": ds[20], "20": ds[19]}


def resumo(m, nome, S, theta=False):
    if isinstance(m, str):
        return m
    d = dict(lotes=m.lotes, premio=m.premio, perda=m.perda_max, ganho=m.ganho_max, eq=list(m.pontos_equilibrio), prob=m.prob_implicita,
             custo=m.custo_total, c_spread=m.custo_spread, c_taxas=m.custo_taxas, c_fixo=m.custo_fixo, alvo=m.alvo or 0, stop=m.stop or 0, ks=[(l, o.tipo, o.strike, o.dias) for l, o in m.pernas])
    if theta:
        d["theta"] = m.theta_dia
    mv = movimento_necessario(m, S, snap["fechamentos"][nome], snap["data"]); d["mov"] = [mv["precisa"], mv["oscilacao"]]
    p0, p1 = PRECOS[nome]; dias = m.pernas[0][1].dias; venc = add_dias(snap["data"], dias)
    sem = {k: v for k, v in p0.items() if k != m.pernas[0][1].simbolo}
    d["marc"] = [resultado_no_dia(m, p0), resultado_no_dia(m, p1), resultado_no_dia(m, sem)]
    # operação real: 1 lote a mais e preços 5% piores que os da montagem (compra mais cara, venda mais barata)
    x = execucao(m, m.lotes + 1, [r2(o.ask * 1.05) if l > 0 else r2(o.bid * 0.95) for l, o in m.pernas])
    d["ex"] = [x.premio, x.perda_max, x.ganho_max, list(x.pontos_equilibrio), x.alvo, x.stop, resultado_no_dia(x, p0),
               [o.ask if l > 0 else o.bid for l, o in x.pernas]]
    d["regras"] = [regra_de_saida(m, marcas(m.perda_max, dias, peq), venc) for peq in (False, True)] \
        + [regra_de_saida(m, [{"d": venc, "r": 10 * m.perda_max}], venc)]   # no dia do vencimento: ignorado (vale o vencimento)
    return d


def lado_python(cor):
    set_corretagem(cor); res = {}
    for nome, a in snap["ativos"].items():
        ch = [Opcao(o["t"], o["k"], o["b"], o["a"], o["v"], o["d"], o["s"]) for o in a["chain"]]
        for tese in ("alta", "baixa", "forte", "alta_com_caixa"):
            res[f"{nome}/{tese}"] = resumo(montar(tese, a["S"], ch, a["iv"], perda_aceita=300, caixa=30000), nome, a["S"])
        for est in ("trava", "put"):
            for nm, ent, al, pz in (("ok", a["S"], r2(a["S"] * 1.10), 30), ("espera", a["S"] * 0.95, r2(a["S"] * 1.10), 30), ("longo", a["S"], r2(a["S"] * 1.10), 120)):
                res[f"{nome}/sinal_{est}_{nm}"] = resumo(montar_sinal(a["S"], ch, a["iv"], 300, ent, al, pz, estrutura=est, caixa=30000), nome, a["S"])
        for lado in ("alta", "baixa"):
            for pf in PERFIS:
                for nm, val in (("ok", 1500), ("pouco", 20)):
                    res[f"{nome}/compra_{lado}_{pf or 'padrao'}_{nm}"] = resumo(montar_aposta(lado, a["S"], ch, a["iv"], val, perfil=pf), nome, a["S"], theta=True)
        for rot, ate in datas_vol(nome).items():
            res[f"{nome}/vol60_{rot}"] = {"vol": vol_real_60(snap["fechamentos"][nome], ate)}
        if snap.get("maxmin", {}).get(nome):
            ds = sorted(snap["fechamentos"][nome])
            for rot, ate in (("fim", snap["data"]), ("30", ds[-30]), ("90", ds[-90])):
                for ifr in (False, True):
                    res[f"tend/{nome}/{rot}/{int(ifr)}"] = tendencia(snap["fechamentos"][nome], snap["maxmin"][nome], ate, ifr)
    for t, x in TEND.items():
        for ifr in (False, True):
            res[f"tend/sint_{t}/{int(ifr)}"] = tendencia(x["fech"], x["maxmin"], x["ate"], ifr)
    curto = lambda m: m if isinstance(m, str) else [m.lotes, m.premio, m.perda_max, [[l, o.simbolo, o.dias] for l, o in m.pernas]]
    for nm, ch in SINT.items():
        ch = [Opcao(*o) for o in ch]
        res[f"sint/{nm}/alta"] = curto(montar("alta", 10.0, ch, 0.3, perda_aceita=300, caixa=30000))
        res[f"sint/{nm}/sinal"] = curto(montar_sinal(10.0, ch, 0.3, 300, 10.0, 10.5, 30, estrutura="trava", caixa=30000))
    set_corretagem(None)
    return res


JS = """
const M=require('./montador.js'),s=require('./snapshot.json'),cor=JSON.parse(process.argv[1]),SINT=JSON.parse(process.argv[2]),TEND=JSON.parse(process.argv[3]),out={};
const r2=(x)=>Math.round(x*100)/100;
const PR={}; for(const [n,a] of Object.entries(s.ativos)) PR[n]=[Object.fromEntries(a.chain.map(o=>[o.s,[o.b,o.a]])),Object.fromEntries(a.chain.map(o=>[o.s,[r2(o.b*1.07),r2(o.a*1.07)]]))];
const FA=[0.1,-0.2,0.3,null,-0.5,0.6,-0.8,0.9,-1.0,1.2];
const addD=(iso,n)=>{const d=new Date(iso+'T12:00:00Z'); d.setUTCDate(d.getUTCDate()+n); return d.toISOString().slice(0,10);};
const marcas=(perda,dias,peq)=>{const o=[], passo=peq?1:5; for(let i=1;passo*i<=dias+5;i++){const f=peq?0.01*((-1)**i):FA[(i-1)%FA.length]; o.push({d:addD(s.data,passo*i),r:f===null?null:f*perda});} return o;};
const res=(m,theta,n,S)=>{ if(typeof m==='string') return m;
  const d={lotes:m.lotes,premio:m.premio,perda:m.perdaMax,ganho:m.ganhoMax,eq:m.equilibrio,prob:m.probImplicita,custo:m.custoTotal,c_spread:m.custoSpread,c_taxas:m.custoTaxas,c_fixo:m.custoFixo,alvo:m.alvo||0,stop:m.stop||0,ks:m.pernas.map(([l,o])=>[l,o.t,o.k,o.d])};
  if(theta) d.theta=m.thetaDia; const mv=M.movimentoNecessario(m,S,s.fechamentos[n],s.data); d.mov=[mv.precisa,mv.oscilacao];
  const [p0,p1]=PR[n], venc=addD(s.data,m.dias), sem={...p0}; delete sem[m.pernas[0][1].s];
  d.marc=[M.resultadoNoDia(m,p0),M.resultadoNoDia(m,p1),M.resultadoNoDia(m,sem)];
  const x=M.execucao(m,{lotes:m.lotes+1,precos:m.pernas.map(([l,o])=>l>0?r2(o.a*1.05):r2(o.b*0.95))});
  d.ex=[x.premio,x.perdaMax,x.ganhoMax,x.equilibrio,x.alvo,x.stop,M.resultadoNoDia(x,p0),x.pernas.map(([l,o])=>l>0?o.a:o.b)];
  d.regras=[false,true].map(peq=>M.regraDeSaida(m,marcas(m.perdaMax,m.dias,peq),venc)).concat([M.regraDeSaida(m,[{d:venc,r:10*m.perdaMax}],venc)]); return d; };
M.setCorretagem(cor);
for(const [n,a] of Object.entries(s.ativos)){
  for(const t of ['alta','baixa','forte','alta_com_caixa']) out[n+'/'+t]=res(M.montar(t,a.S,a.chain,a.iv,300,{caixa:30000}),false,n,a.S);
  for(const est of ['trava','put']) for(const [nm,ent,al,pz] of [['ok',a.S,r2(a.S*1.10),30],['espera',a.S*0.95,r2(a.S*1.10),30],['longo',a.S,r2(a.S*1.10),120]])
    out[n+'/sinal_'+est+'_'+nm]=res(M.montarSinal(a.S,a.chain,a.iv,300,ent,al,pz,{estrutura:est,caixa:30000}),false,n,a.S);
  for(const lado of ['alta','baixa']) for(const pf of [null,'maior','eq','freq']) for(const [nm,val] of [['ok',1500],['pouco',20]])
    out[n+'/compra_'+lado+'_'+(pf||'padrao')+'_'+nm]=res(M.montarAposta(lado,a.S,a.chain,a.iv,val,pf?{perfil:pf}:{}),true,n,a.S);
  const ds=Object.keys(s.fechamentos[n]).sort();
  for(const [rot,ate] of [['fim',s.data],['21',ds[20]],['20',ds[19]]]) out[n+'/vol60_'+rot]={vol:M.volReal60(s.fechamentos[n],ate)};
  if(s.maxmin&&s.maxmin[n]&&Object.keys(s.maxmin[n]).length) for(const [rot,ate] of [['fim',s.data],['30',ds[ds.length-30]],['90',ds[ds.length-90]]]) for(const ifr of [0,1])
    out['tend/'+n+'/'+rot+'/'+ifr]=M.tendencia(s.fechamentos[n],s.maxmin[n],ate,!!ifr);
}
for(const [t,x] of Object.entries(TEND)) for(const ifr of [0,1]) out['tend/sint_'+t+'/'+ifr]=M.tendencia(x.fech,x.maxmin,x.ate,!!ifr);
const curto=(m)=>typeof m==='string'?m:[m.lotes,m.premio,m.perdaMax,m.pernas.map(([l,o])=>[l,o.s,o.d])];
for(const [nm,ch0] of Object.entries(SINT)){ const ch=ch0.map(([t,k,b,a,v,d,s])=>({t,k,b,a,v,d,s}));
  out['sint/'+nm+'/alta']=curto(M.montar('alta',10,ch,0.3,300,{caixa:30000}));
  out['sint/'+nm+'/sinal']=curto(M.montarSinal(10,ch,0.3,300,10,10.5,30,{estrutura:'trava',caixa:30000})); }
console.log(JSON.stringify(out));
"""


def lado_js(cor):
    js = subprocess.run(["node", "-e", JS, json.dumps(cor), json.dumps(SINT), json.dumps(TEND)], capture_output=True, text=True)
    if js.returncode:
        print(js.stderr); sys.exit(1)
    return json.loads(js.stdout)


INC = "Preços de fechamento inconsistentes: "
FIM = ". O app não monta esta operação com esses preços."
ESPERADO = {"sint/credito/alta": lambda v: v == INC + "comprar SINTA100 e vender SINTA105 daria crédito de R$ 38" + FIM,
            "sint/zero/alta": lambda v: v == INC + "comprar SINTD100 e vender SINTD105 não teria custo" + FIM,
            "sint/igual/alta": lambda v: v == INC + "comprar SINTE100 e vender SINTE105 custaria R$ 50, e a trava paga no máximo R$ 50" + FIM,
            "sint/igual/sinal": lambda v: v == INC + "comprar SINTE100 e vender SINTE105 custaria R$ 50, e a trava paga no máximo R$ 50" + FIM,
            "sint/zero/sinal": lambda v: v == INC + "comprar SINTD100 e vender SINTD105 não teria custo" + FIM,
            "sint/largura/alta": lambda v: v == INC + "comprar SINTB100 e vender SINTB105 custaria R$ 55, e a trava paga no máximo R$ 50. O app não monta esta operação com esses preços.",
            "sint/segue/alta": lambda v: isinstance(v, list) and v[3] == [[1, "SINTC100", 50], [-1, "SINTC105", 50]] and v[0] == 12,
            "sint/credito/sinal": lambda v: v == INC + "comprar SINTA100 e vender SINTA105 daria crédito de R$ 38" + FIM,
            "sint/largura/sinal": lambda v: v == INC + "comprar SINTB100 e vender SINTB105 custaria R$ 55, e a trava paga no máximo R$ 50. O app não monta esta operação com esses preços.",
            "sint/segue/sinal": lambda v: isinstance(v, list) and v[3] == [[1, "SINTC100", 50], [-1, "SINTC105", 50]]}
# tendência nas séries sintéticas: a cor esperada (sem IFR, com IFR)
TEND_ESP = {"alta": ("alta",) * 2, "queda": ("queda",) * 2, "plana": ("neutro",) * 2, "curta": (None,) * 2,
            "buracos": ("alta",) * 2, "ifr_q": ("queda", "neutro"), "ifr_a": ("alta", "neutro")}
igual_ex = lambda a, b: all(all(perto(c, e) for c, e in zip(x, y)) and len(x) == len(y) if isinstance(x, list) else perto(x, y) for x, y in zip(a, b))
perto = lambda a, b, tol=0.011: (a is None and b is None) or (a is not None and b is not None and abs(a - b) < tol)
falhas = casos = montados = 0; regras = {}; tend = {}
for cor in CORRETAGENS:
    py, js = lado_python(cor), lado_js(cor)
    rotulo = "sem corretagem" if cor is None else f"corretagem R$ {cor:.2f}"
    for k, v in py.items():
        j = js[k]; casos += 1
        if k.startswith("sint/"):   # cadeias sintéticas: resultado esperado conferido abaixo; aqui, os dois lados iguais
            ok = v == j if isinstance(v, str) else isinstance(j, list) and v[:1] == j[:1] and perto(v[1], j[1]) and perto(v[2], j[2]) and v[3] == j[3]
            ok = ok and ESPERADO[k](v)
            if not ok: print("ERRO", rotulo, k, "| py:", v, "| js:", j)
            falhas += 0 if ok else 1; continue
        if k.startswith("tend/"):   # tendência: mesma cor e mesmas contas; nas sintéticas, a cor esperada
            ok = (v is None and j is None) or (v is not None and j is not None and v["classe"] == j["classe"]
                                               and all(perto(v[f], j[f], 1e-9) for f in ("mm21", "mm50", "mm50ant", "adx", "ifr")))
            t = k.split("/")[1][5:] if k.split("/")[1].startswith("sint_") else None
            if t in TEND_ESP: ok = ok and (v and v["classe"]) == TEND_ESP[t][int(k[-1])]
            tend[(v or {}).get("classe")] = tend.get((v or {}).get("classe"), 0) + 1
            if not ok: print("ERRO", rotulo, k, "| py:", v, "| js:", j)
            falhas += 0 if ok else 1; continue
        if isinstance(v, str) or isinstance(j, str):
            # mensagens: mesmo início (até os dois-pontos); as de preço inconsistente, iguais por inteiro
            ok = v == j or (isinstance(v, str) and isinstance(j, str) and not v.startswith("Preços de fechamento") and v.split(":")[0] == j.split(":")[0])
            if not ok: print("ERRO", rotulo, k, "| py:", v, "| js:", j)
            falhas += 0 if ok else 1; continue
        if "vol" in v:   # volatilidade de 60 pregões
            ok = perto(v["vol"], j["vol"], 1e-12)
            if not ok: print("ERRO", rotulo, k, "| py:", v, "| js:", j)
            falhas += 0 if ok else 1; continue
        montados += 1
        for x in v["regras"]: regras[x["regra"] if x else "nenhuma"] = regras.get(x["regra"] if x else "nenhuma", 0) + 1
        ok = all(perto(v[f], j[f]) for f in ("lotes", "premio", "perda", "custo", "c_spread", "c_taxas", "c_fixo", "stop", "alvo")) and (v["ganho"] is None) == (j["ganho"] is None) \
            and all(perto(a, b) for a, b in zip(v["eq"], j["eq"])) and abs(v["prob"] - j["prob"]) < 0.002 and [list(x) for x in v["ks"]] == j["ks"] \
            and ("theta" not in v or perto(v["theta"], j["theta"])) and all(perto(a, b, 1e-12) for a, b in zip(v["mov"], j["mov"])) \
            and all(perto(a, b) for a, b in zip(v["marc"], j["marc"])) and v["marc"][2] is None and j["marc"][2] is None and igual_ex(v["ex"], j["ex"]) \
            and all((x is None and y is None) or (x is not None and y is not None and x["regra"] == y["regra"] and x["d"] == y["d"] and perto(x["r"], y["r"]))
                    for x, y in zip(v["regras"], j["regras"]))
        if not ok: print("ERRO", rotulo, k, "| py:", v, "| js:", j)
        falhas += 0 if ok else 1
print("tendência (casos por cor):", ", ".join(f"{k or 'sem dados'} {v}" for k, v in sorted(tend.items(), key=lambda kv: str(kv[0]))))
print("regras de saída disparadas:", ", ".join(f"{k} {v}" for k, v in sorted(regras.items())))
print(f"{casos} casos ({montados} montados) em {len(snap['ativos'])} ativos, sem e com corretagem: {falhas} falha(s)")
sys.exit(1 if falhas else 0)
