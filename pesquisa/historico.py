#!/usr/bin/env python3
"""Histórico das operações do app: de todas as vezes que o app montaria cada operação de 2015 até hoje, em quantas ela
terminou com lucro (segurando até o vencimento, depois das taxas da B3)? Por estrutura, por perfil e por faixa da
"Chance implícita no preço" que a tela mostraria no dia. Só mede; não escolhe parâmetro.

Operações: as que o montador.py monta a cada 5 pregões, nos papéis do app, com a cadeia do dia (mesma filtragem do
atualizador) e o juro da Selic do dia (como o app): travas de alta e de baixa nos três perfis (Lucro maior, Equilibrada,
Lucro frequente), strangle comprado, put vendida coberta e compra simples (call e put) nos três perfis. Execução no pior
lado na entrada; no vencimento, o fechamento do papel e o strike ajustado pela B3 (pesquisa/replay.py).

Saída: tabela em Markdown (stdout e --saida) e JSON com {estrutura/perfil: {faixa: [operações, com lucro]}} (--json),
para o app mostrar "em N operações parecidas, X% terminaram com lucro".

Uso: python pesquisa/historico.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida r.md] [--json h.json] [--selic serie.json]
"""
import argparse, glob, json, os, sys
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..")); sys.path.insert(0, AQUI)
import atualizar_dados as AD                                                          # noqa: E402
import montador as MT                                                                  # noqa: E402
import replay as RP                                                                    # noqa: E402
from juro import serie_selic, selic_em                                                 # noqa: E402

# (chave, nome, como montar)
VARIANTES = [("alta/" + p, "Trava de alta · " + n, ("alta", p)) for p, n in (("maior", "Lucro maior"), ("eq", "Equilibrada"), ("freq", "Lucro frequente"))] \
    + [("baixa/" + p, "Trava de baixa · " + n, ("baixa", p)) for p, n in (("maior", "Lucro maior"), ("eq", "Equilibrada"), ("freq", "Lucro frequente"))] \
    + [("forte/eq", "Strangle comprado", ("forte", None)), ("alta_com_caixa/eq", "Put vendida coberta", ("alta_com_caixa", None))] \
    + [(f"aposta_{l}/{p}", f"{'Call' if l == 'alta' else 'Put'} comprada · {n}", ("aposta_" + l, p)) for l in ("alta", "baixa") for p, n in (("maior", "Lucro maior"), ("eq", "Equilibrada"), ("freq", "Lucro frequente"))]
FAIXAS = [(0, .1), (.1, .2), (.2, .3), (.3, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, .9), (.9, 1.01)]
B = 2000


def montar(tese, perfil, S, ch, iv):
    if tese.startswith("aposta"):
        return MT.montar_aposta(tese.split("_")[1], S, ch, iv, RP.PERDA, perfil=perfil)
    return MT.montar(tese, S, ch, iv, RP.PERDA, caixa=RP.CAIXA, perfil=None if perfil in (None, "eq") else perfil)


def boot(por_mes, rnd):
    import numpy as np
    meses = list(por_mes.values())
    if len(meses) < 3:
        return float("nan"), float("nan")
    soma = np.array([sum(v) for v in meses]); n = np.array([len(v) for v in meses])
    idx = rnd.integers(0, len(meses), size=(B, len(meses)))
    m = soma[idx].sum(1) / n[idx].sum(1)
    return tuple(np.percentile(m, [2.5, 97.5]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida"); ap.add_argument("--json"); ap.add_argument("--passo", type=int, default=5)
    ap.add_argument("--selic")
    a = ap.parse_args()
    import numpy as np
    rnd = np.random.default_rng(20261116)
    zips = sorted(glob.glob(os.path.join(a.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {a.zips}")
    selic = serie_selic(a.selic); ords = sorted(selic)
    fech, isin = RP.ler_spot(zips)
    datas = sorted(set().union(*(set(f) for f in fech.values())))
    entradas = datas[::a.passo]
    opc = RP.ler_cadeias(zips, entradas, isin)
    ops = []
    for chave in sorted(opc):
        nome, dia = chave; linhas = opc.pop(chave); S = fech[nome].get(dia); sd = selic_em(selic, ords, dia)
        if not S or sd is None:
            continue
        r = AD.juro_da_selic(sd); MT.set_juro(r)
        p = AD.montar_dia(dia, S, linhas, r)
        ch = [MT.Opcao(o["t"], o["k"], o["b"], o["a"], o["v"], o["d"], o["s"]) for o in p["chain"]]
        vencs = {o["s"]: o["venc"] for o in linhas}
        for k, _, (tese, perfil) in VARIANTES:
            m = montar(tese, perfil, S, ch, p["iv"])
            if not isinstance(m, str):
                ops.append(dict(k=k, ativo=nome, data=dia, tese=tese, m=m, venc=vencs[m.pernas[0][1].simbolo]))
    MT.set_juro(MT.R_PADRAO)
    ultimo = datas[-1]
    ops = [o for o in ops if o["venc"] <= ultimo]
    print(f"{len(ops)} montagens com vencimento até {ultimo}", flush=True)
    px = RP.ler_precos(zips, {(o.simbolo, op["venc"]) for op in ops for _, o in op["m"].pernas})
    R = []
    for op in ops:
        m, venc = op["m"], op["venc"]
        ST = RP.fech_no(fech[op["ativo"]], venc)
        if ST is None:
            continue
        ks = [RP.strike_final(o, px.get((o.simbolo, venc), {}), venc) for _, o in m.pernas]
        res = RP.no_vencimento(m, ST, ks) - m.custo_taxas
        R.append(dict(k=op["k"], data=op["data"], prob=m.prob_implicita, lucro=res > 0, res=res / m.perda_max))

    txt = ["# Histórico das operações do app (2015 até hoje)", "",
           f"Arquivos: {os.path.basename(zips[0])} a {os.path.basename(zips[-1])}; entradas a cada {a.passo} pregões; operações com "
           f"vencimento até {ultimo}, seguradas até o vencimento; lucro depois das taxas da B3, sem corretagem. Juro: Selic do dia.",
           f"IC 95%: bootstrap em blocos mensais ({B} reamostras).", "",
           "## Por operação", "",
           "| operação | operações | chance média na tela | terminaram com lucro | IC 95% | resultado médio (% do risco) |", "|---|---|---|---|---|---|"]
    dados = {}
    for k, nome, _ in VARIANTES:
        F = [r for r in R if r["k"] == k]
        if not F:
            continue
        pm = defaultdict(list)
        for r in F:
            pm[r["data"][:7]].append(r["lucro"])
        ic = boot(pm, rnd)
        txt.append(f"| {nome} | {len(F)} | {100 * sum(r['prob'] for r in F) / len(F):.1f}% | {100 * sum(r['lucro'] for r in F) / len(F):.1f}% | "
                   f"[{100 * ic[0]:.1f}; {100 * ic[1]:.1f}] | {100 * sum(r['res'] for r in F) / len(F):+.1f}% |")
        dados[k] = {}
        for lo, hi in FAIXAS:
            G = [r for r in F if lo <= r["prob"] < hi]
            if G:
                dados[k][f"{int(lo * 100)}-{min(int(hi * 100), 100)}"] = [len(G), sum(r["lucro"] for r in G)]
    txt += ["", "## Por operação e faixa da chance na tela (operações; terminaram com lucro)", ""]
    for k, nome, _ in VARIANTES:
        if k in dados:
            txt.append(f"- **{nome}**: " + "; ".join(f"{f}%: {n} ops, {100 * l / n:.0f}% com lucro" for f, (n, l) in dados[k].items() if n >= 20))
    saida = "\n".join(txt)
    print(saida)
    print("JSON " + json.dumps(dados, separators=(",", ":")))
    if a.saida:
        open(a.saida, "w", encoding="utf-8").write(saida + "\n")
    if a.json:
        json.dump(dados, open(a.json, "w", encoding="utf-8"), separators=(",", ":"))


if __name__ == "__main__":
    main()
