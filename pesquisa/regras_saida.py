#!/usr/bin/env python3
"""As regras de saída do app no histórico: seguir "Quando sair" (alvo, limite, prazo) × segurar até o vencimento.

Hipótese e critério fixados antes de rodar (17/11/2026):
  H3. Seguir as regras de saída do app muda o resultado médio em relação a segurar até o vencimento. Passa só se o IC 95%
      da diferença por operação (regra, saindo no preço médio do pregão seguinte ao disparo − segurar) fica inteiro de um
      lado do zero E a diferença tem o mesmo sinal em 2015–2020 e em 2021–2026.
  Descritivo: frequência de lucro e resultado médio seguindo as regras, com a saída no pior lado do fechamento do disparo
  (vende pela compra, recompra pela venda), no preço médio desse fechamento (o que o app mostra) e no preço médio do
  pregão seguinte; por que regra cada operação saiu.

As regras são as do app: o montador.py monta (alvo = 50% do ganho máximo; limite só na put vendida, 70% do risco por lote
com risco aceito grande; prazo = 7 dias antes do vencimento) e o app confere todo fechamento depois da entrada, no preço
médio de cada perna, nunca abaixo do risco máximo (resultado_no_dia, regra_de_saida). Compra simples não tem regra
(segura até o vencimento) e fica fora. Mesmas operações do pesquisa/historico.py (a cada 5 pregões, 8 papéis, Selic do
dia, pior lado na entrada, taxas da B3 de entrada e saída, sem corretagem). Resultado em % do risco máximo.

Uso: python pesquisa/regras_saida.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida r.md] [--selic serie.json]
"""
import argparse, glob, os, sys
from collections import defaultdict, Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..")); sys.path.insert(0, AQUI)
import atualizar_dados as AD                                                          # noqa: E402
import montador as MT                                                                  # noqa: E402
import replay as RP                                                                    # noqa: E402
from juro import serie_selic, selic_em                                                 # noqa: E402
from historico import VARIANTES, montar, boot, B                                        # noqa: E402

COM_REGRA = [v for v in VARIANTES if not v[0].startswith("aposta")]
PERIODOS = (("2015–2020", "2015", "2020"), ("2021–2026", "2021", "2026"))


def pct(x):
    return "—" if x is None or x != x else f"{100 * x:+.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida"); ap.add_argument("--passo", type=int, default=5)
    ap.add_argument("--selic")
    a = ap.parse_args()
    import numpy as np
    rnd = np.random.default_rng(20261118)
    zips = sorted(glob.glob(os.path.join(a.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {a.zips}")
    selic = serie_selic(a.selic); ords = sorted(selic)
    fech, isin = RP.ler_spot(zips)
    datas = sorted(set().union(*(set(f) for f in fech.values())))
    opc = RP.ler_cadeias(zips, datas[::a.passo], isin)
    ops = []
    for chave in sorted(opc):
        nome, dia = chave; linhas = opc.pop(chave); S = fech[nome].get(dia); sd = selic_em(selic, ords, dia)
        if not S or sd is None:
            continue
        r = AD.juro_da_selic(sd); MT.set_juro(r)
        p = AD.montar_dia(dia, S, linhas, r)
        ch = [MT.Opcao(o["t"], o["k"], o["b"], o["a"], o["v"], o["d"], o["s"]) for o in p["chain"]]
        vencs = {o["s"]: o["venc"] for o in linhas}
        for k, _, (tese, perfil) in COM_REGRA:
            m = montar(tese, perfil, S, ch, p["iv"])
            if not isinstance(m, str):
                ops.append(dict(k=k, ativo=nome, data=dia, m=m, venc=vencs[m.pernas[0][1].simbolo]))
    MT.set_juro(MT.R_PADRAO)
    ultimo = datas[-1]
    ops = [o for o in ops if o["venc"] <= ultimo]
    print(f"{len(ops)} montagens com regra de saída e vencimento até {ultimo}", flush=True)
    px = RP.ler_precos(zips, {(o.simbolo, op["venc"]) for op in ops for _, o in op["m"].pernas})
    R, sem_seg = [], Counter()
    for op in ops:
        m, venc = op["m"], op["venc"]
        ST = RP.fech_no(fech[op["ativo"]], venc)
        if ST is None:
            continue
        risco, tx = m.perda_max, m.custo_taxas
        ks = [RP.strike_final(o, px.get((o.simbolo, venc), {}), venc) for _, o in m.pernas]
        segurar = (RP.no_vencimento(m, ST, ks) - tx) / risco
        dias, precos = [], {}
        for d in sorted({d for _, o in m.pernas for d in px.get((o.simbolo, venc), {}) if op["data"] < d < venc}):
            pr = {o.simbolo: px[(o.simbolo, venc)][d][:2] for _, o in m.pernas if d in px.get((o.simbolo, venc), {})}
            dias.append(d); precos[d] = pr
        marcas = [{"d": d, "r": MT.resultado_no_dia(m, precos[d])} for d in dias]
        rg = MT.regra_de_saida(m, marcas, venc)
        if rg:
            d = rg["d"]; pior = RP.no_pior_lado(m, precos[d]); medio = RP.no_meio(m, precos[d])
            seg = next((RP.no_meio(m, precos[x]) for x in dias if x > d and RP.no_meio(m, precos[x]) is not None), None)
            if seg is None:
                sem_seg[rg["regra"]] += 1   # sem pregão seguinte antes do vencimento: fica o resultado de segurar
            linha = dict(saida=rg["regra"], pior=(pior - tx) / risco if pior is not None else segurar,
                         medio=(medio - tx) / risco if medio is not None else segurar,
                         seg=(seg - tx) / risco if seg is not None else segurar)
        else:
            linha = dict(saida="vencimento", pior=segurar, medio=segurar, seg=segurar)
        linha.update(k=op["k"], data=op["data"], segurar=segurar, dif=linha["seg"] - segurar)
        R.append(linha)

    print("disparos sem pregão seguinte com preço antes do vencimento (ficam como segurar): " + (", ".join(f"{k} {v}" for k, v in sem_seg.items()) or "nenhum"), flush=True)

    def media_ic(F, chave):
        pm = defaultdict(list)
        for r in F:
            pm[r["data"][:7]].append(r[chave])
        return sum(r[chave] for r in F) / len(F), boot(pm, rnd)

    txt = ["# Regras de saída do app × segurar até o vencimento", "",
           f"Arquivos: {os.path.basename(zips[0])} a {os.path.basename(zips[-1])}; {len(R)} operações com regra de saída e vencimento até "
           f"{ultimo}. Resultado médio por operação, em % do risco máximo, depois das taxas da B3; IC 95% por bootstrap em blocos mensais "
           f"({B} reamostras). Compra simples: sem regra no app (segura até o vencimento).", "",
           "## 1. Por que regra saiu (% das operações)", "", "| operação | operações | alvo | limite | prazo | vencimento |", "|---|---|---|---|---|---|"]
    for k, nome, _ in COM_REGRA:
        F = [r for r in R if r["k"] == k]
        if F:
            c = Counter(r["saida"] for r in F)
            txt.append(f"| {nome} | {len(F)} | " + " | ".join(f"{100 * c[s] / len(F):.0f}%" for s in ("alvo", "limite", "prazo", "vencimento")) + " |")
    txt += ["", "## 2. Seguindo as regras: com lucro e resultado médio", "",
            "| operação | com lucro: pior lado / médio / pregão seguinte | segurar: com lucro | resultado médio: pior lado / médio / pregão seguinte | segurar |",
            "|---|---|---|---|---|"]
    for k, nome, _ in COM_REGRA:
        F = [r for r in R if r["k"] == k]
        if F:
            n = len(F); w = lambda c: f"{100 * sum(r[c] > 0 for r in F) / n:.0f}%"; mu = lambda c: pct(sum(r[c] for r in F) / n)
            txt.append(f"| {nome} | {w('pior')} / {w('medio')} / {w('seg')} | {w('segurar')} | {mu('pior')} / {mu('medio')} / {mu('seg')} | {mu('segurar')} |")
    txt += ["", "## 3. Diferença por operação: regra (preço médio do pregão seguinte) − segurar", "",
            "| operação | diferença média | IC 95% | 2015–2020 | 2021–2026 | H3 |", "|---|---|---|---|---|---|"]
    for k, nome, _ in COM_REGRA:
        F = [r for r in R if r["k"] == k]
        if not F:
            continue
        mu, ic = media_ic(F, "dif")
        per = []
        for _, de, ate in PERIODOS:
            G = [r for r in F if de <= r["data"][:4] <= ate]
            per.append(sum(r["dif"] for r in G) / len(G) if G else None)
        lado = ic[0] > 0 or ic[1] < 0
        ok = lado and all(p is not None for p in per) and (all(p > 0 for p in per) if ic[0] > 0 else all(p < 0 for p in per))
        txt.append(f"| {nome} | {pct(mu)} | [{pct(ic[0])}; {pct(ic[1])}] | {pct(per[0])} | {pct(per[1])} | {'PASSA' if ok else 'não passa'} |")
    saida = "\n".join(txt)
    print(saida)
    if a.saida:
        open(a.saida, "w", encoding="utf-8").write(saida + "\n")


if __name__ == "__main__":
    main()
