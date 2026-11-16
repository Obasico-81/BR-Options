#!/usr/bin/env python3
"""Decisões do cliente no app com vantagem estatística? Só mede; não escolhe parâmetro.

Critério fixado antes de rodar (17/11/2026), para o app comunicar uma escolha:
  a diferença por operação entre as duas escolhas (mesmo papel e mesmo dia) tem IC com correção de Bonferroni pelo número
  de comparações da família (IC 95% conjunto) inteiro de um lado do zero E o mesmo sinal em 2015–2020 e em 2021–2026.
Famílias:
  D1. Perfil: Lucro maior × Equilibrada × Lucro frequente, na trava de alta, trava de baixa, call comprada e put comprada
      (3 pares × 4 = 12 comparações), segurando até o vencimento.
  D2. Segurar até o vencimento × desfazer 3, 7 ou 15 dias depois da entrada no preço médio do fechamento (limite otimista
      para quem desfaz), nas 14 operações (42 comparações).
Mesmas operações do pesquisa/historico.py (a cada 5 pregões, 8 papéis, Selic do dia, pior lado na entrada, taxas da B3).
Resultado em % do risco máximo. IC por bootstrap em blocos mensais.

Uso: python pesquisa/decisoes.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida r.md] [--selic serie.json]
"""
import argparse, glob, os, sys, time
from collections import defaultdict
from datetime import date, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..")); sys.path.insert(0, AQUI)
import atualizar_dados as AD                                                          # noqa: E402
import montador as MT                                                                  # noqa: E402
import replay as RP                                                                    # noqa: E402
from juro import serie_selic, selic_em                                                 # noqa: E402
from historico import VARIANTES, montar                                                 # noqa: E402
from robustez import saida_em                                                           # noqa: E402

B = 4000
PERIODOS = (("2015–2020", "2015", "2020"), ("2021–2026", "2021", "2026"))
NOME = {k: n for k, n, _ in VARIANTES}


def boot_ic(pm, rnd, alfa):
    import numpy as np
    meses = list(pm.values())
    if len(meses) < 3:
        return float("nan"), float("nan")
    soma = np.array([sum(v) for v in meses]); n = np.array([len(v) for v in meses])
    idx = rnd.integers(0, len(meses), size=(B, len(meses)))
    m = soma[idx].sum(1) / n[idx].sum(1)
    return tuple(np.percentile(m, [100 * alfa / 2, 100 * (1 - alfa / 2)]))


def pct(x):
    return "—" if x is None or x != x else f"{100 * x:+.1f}"


def avalia(pares, rnd, n_comp):
    """pares: [(data, diferença)]. Devolve n, média, IC 95% conjunto (Bonferroni), médias por período e se passa."""
    if not pares:
        return None
    pm = defaultdict(list)
    for d, v in pares:
        pm[d[:7]].append(v)
    mu = sum(v for _, v in pares) / len(pares)
    ic = boot_ic(pm, rnd, 0.05 / n_comp)
    per = []
    for _, de, ate in PERIODOS:
        G = [v for d, v in pares if de <= d[:4] <= ate]
        per.append(sum(G) / len(G) if G else None)
    lado = 1 if ic[0] > 0 else -1 if ic[1] < 0 else 0
    ok = lado != 0 and all(p is not None and p * lado > 0 for p in per)
    return len(pares), mu, ic, per, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida"); ap.add_argument("--passo", type=int, default=5)
    ap.add_argument("--selic")
    a = ap.parse_args()
    import numpy as np
    rnd = np.random.default_rng(20261119)
    zips = sorted(glob.glob(os.path.join(a.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {a.zips}")
    for _ in range(4):   # a API do Banco Central às vezes devolve vazio num pedaço da série
        selic = serie_selic(a.selic); ords = sorted(selic)
        if ords and ords[0] <= "2015-01-31":
            break
        time.sleep(30)
    else:
        raise SystemExit("Série da Selic incompleta (não cobre 2015): resultado não seria comparável.")
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
        for k, _, (tese, perfil) in VARIANTES:
            m = montar(tese, perfil, S, ch, p["iv"])
            if not isinstance(m, str):
                ops.append(dict(k=k, ativo=nome, data=dia, m=m, venc=vencs[m.pernas[0][1].simbolo]))
    MT.set_juro(MT.R_PADRAO)
    ultimo = datas[-1]
    ops = [o for o in ops if o["venc"] <= ultimo]
    print(f"{len(ops)} montagens com vencimento até {ultimo}; Selic desde {ords[0]}", flush=True)
    px = RP.ler_precos(zips, {(o.simbolo, op["venc"]) for op in ops for _, o in op["m"].pernas})
    R = {}
    for op in ops:
        m, venc = op["m"], op["venc"]
        ST = RP.fech_no(fech[op["ativo"]], venc)
        if ST is None:
            continue
        risco, tx = m.perda_max, m.custo_taxas
        ks = [RP.strike_final(o, px.get((o.simbolo, venc), {}), venc) for _, o in m.pernas]
        linha = dict(venc=(RP.no_vencimento(m, ST, ks) - tx) / risco)
        for N in (3, 7, 15):
            alvo = (date.fromisoformat(op["data"]) + timedelta(days=N)).isoformat()
            if alvo >= venc:
                linha[N] = linha["venc"]; continue
            sm = saida_em(m, px, venc, alvo, False)
            linha[N] = None if sm is None else (sm - tx) / risco
        R[(op["k"], op["ativo"], op["data"])] = linha

    txt = ["# Decisões do cliente com vantagem estatística?", "",
           f"Arquivos: {os.path.basename(zips[0])} a {os.path.basename(zips[-1])}; {len(R)} operações com vencimento até {ultimo}. "
           "Diferença por operação (mesmo papel e dia), em pontos percentuais do risco máximo, depois das taxas da B3. "
           f"IC 95% conjunto: bootstrap em blocos mensais ({B} reamostras), Bonferroni pelo número de comparações da família. "
           "Passa: IC inteiro de um lado do zero e o mesmo sinal nos dois períodos.", "",
           "## D1. Perfil (segurando até o vencimento)", "",
           "| comparação | pares | diferença média | IC 95% conjunto | 2015–2020 | 2021–2026 | passa |", "|---|---|---|---|---|---|---|"]
    fams = [("alta", "Trava de alta"), ("baixa", "Trava de baixa"), ("aposta_alta", "Call comprada"), ("aposta_baixa", "Put comprada")]
    pares_p = [("maior", "freq"), ("maior", "eq"), ("eq", "freq")]
    NP = {"maior": "Lucro maior", "eq": "Equilibrada", "freq": "Lucro frequente"}
    for f, fn in fams:
        for x, y in pares_p:
            pares = [(d, R[(f"{f}/{x}", at, d)]["venc"] - R[(f"{f}/{y}", at, d)]["venc"])
                     for (k, at, d) in R if k == f"{f}/{x}" and (f"{f}/{y}", at, d) in R]
            ev = avalia(pares, rnd, len(fams) * len(pares_p))
            if ev:
                n, mu, ic, per, ok = ev
                txt.append(f"| {fn}: {NP[x]} − {NP[y]} | {n} | {pct(mu)} | [{pct(ic[0])}; {pct(ic[1])}] | {pct(per[0])} | {pct(per[1])} | {'PASSA' if ok else 'não'} |")
    txt += ["", "## D2. Segurar até o vencimento − desfazer antes (preço médio do fechamento)", "",
            "| operação | 3 dias: diferença [IC conjunto] | 7 dias | 15 dias | passa (3 / 7 / 15) |", "|---|---|---|---|---|"]
    for k, nome, _ in VARIANTES:
        cel, oks = [], []
        for N in (3, 7, 15):
            pares = [(d, v["venc"] - v[N]) for (kk, at, d), v in R.items() if kk == k and v[N] is not None]
            ev = avalia(pares, rnd, len(VARIANTES) * 3)
            if ev:
                n, mu, ic, per, ok = ev
                cel.append(f"{pct(mu)} [{pct(ic[0])}; {pct(ic[1])}] ({pct(per[0])} / {pct(per[1])})"); oks.append("PASSA" if ok else "não")
            else:
                cel.append("—"); oks.append("—")
        txt.append(f"| {nome} | " + " | ".join(cel) + f" | {' / '.join(oks)} |")
    saida = "\n".join(txt)
    print(saida)
    if a.saida:
        open(a.saida, "w", encoding="utf-8").write(saida + "\n")


if __name__ == "__main__":
    main()
