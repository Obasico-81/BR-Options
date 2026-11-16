#!/usr/bin/env python3
"""Juro do Black-Scholes: Selic do dia × 11% fixo (decisão de usar a Selic do dia no app).

Pergunta (fixada antes de rodar): a "Chance implícita no preço" fica tão ou mais calibrada com a Selic de cada dia
(volatilidade implícita e chance com o mesmo juro, como o app passa a fazer) do que com o juro fixo de 11% a.a.?

Operações: as que o montador.py monta a cada 5 pregões de 2015 até hoje, nas 6 estruturas do app, com a cadeia do dia
(mesma filtragem do atualizador), seguradas até o vencimento (mesma leitura do pesquisa/replay.py: fechamento do papel
no vencimento e strike ajustado pela B3 por proventos). Cada versão monta com o próprio juro (a volatilidade implícita e
o delta dos perfis mudam com ele, então algumas operações escolhem outras séries).

Medidas, nas duas versões:
  - chance média × terminou além do equilíbrio, por faixa de chance, por estrutura e por nível da Selic;
  - erro de calibração: |chance média − frequência| por faixa, ponderado pelas operações;
  - Brier: média de (chance − resultado)², e a diferença (Selic do dia − fixo) nas operações iguais nas duas versões
    (mesmas séries), com IC 95% por bootstrap em blocos mensais.
Selic: meta do Copom por dia (Banco Central, SGS 432). Só mede; não escolhe parâmetro.

Uso: python pesquisa/juro.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida resultado.txt] [--passo 5] [--selic serie.json]
"""
import argparse, glob, json, math, os, sys
from collections import defaultdict
from datetime import date, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..")); sys.path.insert(0, AQUI)
import atualizar_dados as AD                                                          # noqa: E402
import montador as MT                                                                  # noqa: E402
import replay as RP                                                                    # noqa: E402

TESES = RP.TESES
NOME = RP.NOME
FIXO = AD.R                      # 11% a.a., o juro de antes
FAIXAS = [(0, .1), (.1, .2), (.2, .3), (.3, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, .9), (.9, 1.01)]
NIVEIS = (("Selic abaixo de 7%", 0, 7), ("Selic de 7% a 11%", 7, 11), ("Selic de 11% ou mais", 11, 100))
B = 2000


def serie_selic(arquivo):
    """Meta Selic por dia (ISO → % a.a.), de dez/2014 até hoje. O Banco Central limita a consulta diária a 10 anos."""
    if arquivo:
        return {k: float(v) for k, v in json.load(open(arquivo)).items()}
    s, ini = {}, date(2014, 12, 1)
    while ini <= date.today():
        fim = min(date(ini.year + 9, 12, 31), date.today())
        s.update(AD.selic_bcb(ini.isoformat(), fim.isoformat()))
        ini = fim + timedelta(days=1)
    if not s:
        raise SystemExit("Sem a série da Selic do Banco Central.")
    return s


def selic_em(serie, ordenadas, d):
    import bisect
    i = bisect.bisect_right(ordenadas, d) - 1
    return serie[ordenadas[i]] if i >= 0 else None


def montar(nome, dia, S, linhas, r):
    """As 6 estruturas com o juro r (volatilidade implícita do dia e montador)."""
    MT.set_juro(r)
    p = AD.montar_dia(dia, S, linhas, r)
    ch = [MT.Opcao(o["t"], o["k"], o["b"], o["a"], o["v"], o["d"], o["s"]) for o in p["chain"]]
    vencs = {o["s"]: o["venc"] for o in linhas}
    out = {}
    for t in TESES:
        m = MT.montar_aposta(t.split("_")[1], S, ch, p["iv"], RP.PERDA) if t.startswith("aposta") else MT.montar(t, S, ch, p["iv"], RP.PERDA, caixa=RP.CAIXA)
        if not isinstance(m, str):
            out[t] = dict(ativo=nome, data=dia, tese=t, m=m, venc=vencs[m.pernas[0][1].simbolo], iv=p["iv"])
    return out


def pct(x):
    return f"{100 * x:.1f}"


def calib(R):
    """[(faixa, n, chance média, frequência)] e o erro de calibração ponderado."""
    linhas, err, tot = [], 0.0, 0
    for lo, hi in FAIXAS:
        F = [r for r in R if lo <= r["prob"] < hi]
        if not F:
            continue
        pm, fq = sum(r["prob"] for r in F) / len(F), sum(r["alem"] for r in F) / len(F)
        linhas.append((lo, hi, len(F), pm, fq)); err += abs(pm - fq) * len(F); tot += len(F)
    return linhas, (err / tot if tot else float("nan"))


def boot_dif(por_mes, rnd):
    """IC 95% da média de diferenças pareadas, reamostrando meses."""
    import numpy as np
    meses = list(por_mes.values())
    soma = np.array([sum(v) for v in meses]); n = np.array([len(v) for v in meses])
    idx = rnd.integers(0, len(meses), size=(B, len(meses)))
    m = soma[idx].sum(1) / n[idx].sum(1)
    return tuple(np.percentile(m, [2.5, 97.5]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida"); ap.add_argument("--passo", type=int, default=5)
    ap.add_argument("--selic", help="série em JSON {data ISO: % a.a.} no lugar do Banco Central (teste local)")
    a = ap.parse_args()
    import numpy as np
    rnd = np.random.default_rng(20261116)
    zips = sorted(glob.glob(os.path.join(a.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {a.zips}")
    selic = serie_selic(a.selic); ords = sorted(selic)
    print(f"Selic: {len(selic)} dias, de {ords[0]} a {ords[-1]}", flush=True)
    fech, isin = RP.ler_spot(zips)
    datas = sorted(set().union(*(set(f) for f in fech.values())))
    entradas = datas[::a.passo]
    opc = RP.ler_cadeias(zips, entradas, isin)
    ops = {"fixo": [], "selic": []}
    for chave in sorted(opc):
        nome, dia = chave; linhas = opc.pop(chave); S = fech[nome].get(dia)
        sd = selic_em(selic, ords, dia)
        if not S or sd is None:
            continue
        for versao, r in (("fixo", FIXO), ("selic", AD.juro_da_selic(sd))):
            for t, op in montar(nome, dia, S, linhas, r).items():
                op["selic"] = sd; ops[versao].append(op)
    MT.set_juro(MT.R_PADRAO)
    ultimo = datas[-1]
    for v in ops:
        ops[v] = [o for o in ops[v] if o["venc"] <= ultimo]
    print(f"montagens com vencimento até {ultimo}: fixo {len(ops['fixo'])}, Selic do dia {len(ops['selic'])}", flush=True)
    vigiar = {(o.simbolo, op["venc"]) for v in ops for op in ops[v] for _, o in op["m"].pernas}
    px = RP.ler_precos(zips, vigiar)

    res = {}
    for v in ops:
        R = []
        for op in ops[v]:
            m, venc = op["m"], op["venc"]
            ST = RP.fech_no(fech[op["ativo"]], venc)
            if ST is None:
                continue
            ks = [RP.strike_final(o, px.get((o.simbolo, venc), {}), venc) for _, o in m.pernas]
            dk = sum(k - o.strike for (_, o), k in zip(m.pernas, ks)) / len(ks)
            eq = tuple(x + dk for x in m.pontos_equilibrio)
            R.append(dict(ativo=op["ativo"], data=op["data"], tese=op["tese"], prob=m.prob_implicita, selic=op["selic"],
                          alem=RP.alem_do_equilibrio(op["tese"], eq, ST), pernas=tuple(o.simbolo for _, o in m.pernas)))
        res[v] = R
    F, S_ = res["fixo"], res["selic"]
    sm = [r["selic"] for r in S_]

    txt = ["# Juro do Black-Scholes: Selic do dia × 11% fixo", "",
           f"Arquivos: {os.path.basename(zips[0])} a {os.path.basename(zips[-1])}; entradas a cada {a.passo} pregões; operações "
           f"com vencimento até {ultimo}, seguradas até o vencimento. Fixo: {len(F)} operações; Selic do dia: {len(S_)}.",
           f"Selic nos dias de entrada: de {min(sm):.2f}% a {max(sm):.2f}% (média {sum(sm) / len(sm):.2f}%). "
           f"Juro fixo: {FIXO * 100:.0f}% a.a. (taxa contínua); Selic convertida em taxa contínua (ln(1 + Selic)).",
           "IC 95%: bootstrap em blocos mensais ({} reamostras).".format(B)]

    # 1. calibração por faixa
    cf, ef = calib(F); cs, es = calib(S_)
    txt += ["", "## 1. Chance na tela × terminou além do equilíbrio, por faixa (tudo)",
            "| chance na tela | ops (fixo) | chance média | além do equilíbrio | ops (Selic) | chance média | além do equilíbrio |", "|---|---|---|---|---|---|---|"]
    ds = {(lo, hi): (n, pm, fq) for lo, hi, n, pm, fq in cs}
    for lo, hi, n, pm, fq in cf:
        n2, pm2, fq2 = ds.get((lo, hi), (0, float("nan"), float("nan")))
        txt.append(f"| {int(lo * 100)}–{min(int(hi * 100), 100)}% | {n} | {pct(pm)} | {pct(fq)} | {n2} | {pct(pm2)} | {pct(fq2)} |")
    txt.append(f"\nErro de calibração (|chance média − frequência| por faixa, ponderado): fixo {pct(ef)} pontos; Selic do dia {pct(es)} pontos.")

    # 2. por estrutura
    txt += ["", "## 2. Por estrutura (tudo): chance média × além do equilíbrio",
            "| estrutura | ops (fixo) | chance média | além do equilíbrio | ops (Selic) | chance média | além do equilíbrio |", "|---|---|---|---|---|---|---|"]
    for t in TESES:
        a1 = [r for r in F if r["tese"] == t]; a2 = [r for r in S_ if r["tese"] == t]
        if a1 and a2:
            txt.append(f"| {NOME[t]} | {len(a1)} | {pct(sum(r['prob'] for r in a1) / len(a1))} | {pct(sum(r['alem'] for r in a1) / len(a1))} | "
                       f"{len(a2)} | {pct(sum(r['prob'] for r in a2) / len(a2))} | {pct(sum(r['alem'] for r in a2) / len(a2))} |")

    # 3. por nível da Selic (onde o juro fixo mais se afasta do do dia)
    txt += ["", "## 3. Por nível da Selic no dia da entrada: chance média × além do equilíbrio, e erro de calibração",
            "| Selic | ops | fixo: chance média | Selic do dia: chance média | além do equilíbrio (Selic do dia) | erro de calibração fixo | erro Selic do dia |", "|---|---|---|---|---|---|---|"]
    for rot, lo, hi in NIVEIS:
        a1 = [r for r in F if lo <= r["selic"] < hi]; a2 = [r for r in S_ if lo <= r["selic"] < hi]
        if a1 and a2:
            txt.append(f"| {rot} | {len(a2)} | {pct(sum(r['prob'] for r in a1) / len(a1))} | {pct(sum(r['prob'] for r in a2) / len(a2))} | "
                       f"{pct(sum(r['alem'] for r in a2) / len(a2))} | {pct(calib(a1)[1])} | {pct(calib(a2)[1])} |")
    txt.append("\n(Por nível, as chances de alta e de baixa se compensam na média; o erro de calibração por faixa é a medida que conta.)")

    # 4. Brier pareado nas operações iguais nas duas versões
    chave = lambda r: (r["ativo"], r["data"], r["tese"], r["pernas"])
    mf = {chave(r): r for r in F}
    par = [(mf[chave(r)], r) for r in S_ if chave(r) in mf]
    br = lambda r: (r["prob"] - r["alem"]) ** 2
    dif = defaultdict(list)
    for f, s in par:
        dif[s["data"][:7]].append(br(s) - br(f))
    bf = sum(br(f) for f, _ in par) / len(par); bs = sum(br(s) for _, s in par) / len(par)
    ic = boot_dif(dif, rnd)
    txt += ["", f"## 4. Brier nas operações iguais nas duas versões ({len(par)} de {len(S_)}; mesmas séries)",
            f"Fixo {bf:.5f}; Selic do dia {bs:.5f}; diferença (Selic do dia − fixo) {bs - bf:+.5f}, IC 95% [{ic[0]:+.5f}, {ic[1]:+.5f}]. "
            "Negativo = a Selic do dia acerta mais."]
    for rot, lo, hi in NIVEIS:
        P = [(f, s) for f, s in par if lo <= s["selic"] < hi]
        if len(P) < 50:
            continue
        d2 = defaultdict(list)
        for f, s in P:
            d2[s["data"][:7]].append(br(s) - br(f))
        i2 = boot_dif(d2, rnd)
        txt.append(f"- {rot}: {len(P)} operações; diferença {sum(br(s) - br(f) for f, s in P) / len(P):+.5f}, IC 95% [{i2[0]:+.5f}, {i2[1]:+.5f}]")

    saida = "\n".join(txt)
    print(saida)
    if a.saida:
        with open(a.saida, "w", encoding="utf-8") as f:
            f.write(saida + "\n")


if __name__ == "__main__":
    main()
