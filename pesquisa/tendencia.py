#!/usr/bin/env python3
"""Back-test da tendência que colore o minigráfico (tendencia do montador.py), com os COTAHIST anuais da B3.

Pergunta: quando o minigráfico fica verde (alta) ou vermelho (queda), o papel segue na mesma direção nos 20 pregões
seguintes mais vezes do que em um dia qualquer? Três regras, lado a lado:
  sem IFR     médias de 21 e 50 pregões (com a de 50 subindo/caindo) e ADX(14) >= 20   -> tendencia(..., False)
  com IFR     a mesma, e o IFR(14) acima de 50 na alta / abaixo de 50 na queda       -> tendencia(..., True)
  faixa ±3%   a regra publicada hoje: variação dos últimos 60 pregões acima de +3% / abaixo de −3%

Medida, para cada dia de cada papel (janela de 150 pregões até o dia, como no app):
  acerto da alta  = parcela dos dias verdes em que o fechamento 20 pregões depois ficou acima do dia
  acerto da queda = parcela dos dias vermelhos em que ficou abaixo
  linha de base   = a mesma parcela em todos os dias do período (subiu / caiu), sem olhar a cor
  diferença       = acerto − linha de base, com IC 95% por bootstrap em blocos mensais (todos os papéis juntos)

Preços: fechamento, máxima e mínima do lote padrão (mercado 010). Desdobramentos e grupamentos (salto de 1/k ou k no
fechamento, k = 2, 3, 4, 5, 8 ou 10) são ajustados para trás; bonificações e proventos não (ver Limitações no fim).
A hipótese e a medida foram fixadas antes de rodar; nada aqui escolhe parâmetro pelo resultado.

Uso: python pesquisa/tendencia.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida resultado.txt]
"""
import argparse, glob, os, sys
from collections import defaultdict

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
from atualizar_dados import ATIVOS, campo, preco, iso, linhas_do_zip   # noqa: E402
from montador import tendencia                                          # noqa: E402

JANELA, PRAZO, PREG_MINI, FAIXA_MINI = 150, 20, 60, 0.03
REGRAS = ("sem IFR", "com IFR", "faixa ±3%")
PERIODOS = (("2015–2020", "2015", "2020"), ("2021–2025", "2021", "2025"), ("2026", "2026", "2026"), ("tudo", "0000", "9999"))
SPLITS = (2, 3, 4, 5, 8, 10)
B = 2000


def ler_zips(zips):
    """serie[nome][data] = (fechamento, máxima, mínima) do papel à vista."""
    papeis = {pap: nome for nome, (_, pap) in ATIVOS.items()}
    serie = {n: {} for n in ATIVOS}
    for z in zips:
        n0 = sum(len(s) for s in serie.values())
        for ln in linhas_do_zip(z):
            if len(ln) < 121 or ln[0:2] != "01" or ln[24:27] != "010":
                continue
            cod = campo(ln, "codneg")
            if cod not in papeis:
                continue
            c, h, lo = preco(campo(ln, "preult")), preco(campo(ln, "premax")), preco(campo(ln, "premin"))
            if h >= c >= lo > 0:
                serie[papeis[cod]][iso(campo(ln, "data"))] = (c, h, lo)
        print(f"{os.path.basename(z)}: {sum(len(s) for s in serie.values()) - n0} pregões×papel", flush=True)
    return serie


def ajustar(s):
    """Ajusta para trás os desdobramentos e grupamentos. Devolve (série ajustada, eventos)."""
    ds = sorted(s)
    fat, acum, ev = [1.0] * len(ds), 1.0, []
    for i in range(len(ds) - 1, 0, -1):
        fat[i] = acum
        r = s[ds[i]][0] / s[ds[i - 1]][0]
        for k in SPLITS:
            if abs(r * k - 1) < 0.06:
                acum /= k; ev.append(f"{ds[i]} desdobramento {k}:1"); break
            if abs(r / k - 1) < 0.06:
                acum *= k; ev.append(f"{ds[i]} grupamento {k}:1"); break
    fat[0] = acum
    return {d: tuple(x * fat[i] for x in s[d]) for i, d in enumerate(ds)}, sorted(ev)


def classificar(s):
    """Uma linha por dia com janela completa e 20 pregões à frente: (data, cor de cada regra, retorno em 20 pregões)."""
    ds = sorted(s)
    out = []
    for i in range(JANELA - 1, len(ds) - PRAZO):
        jan = ds[i - JANELA + 1:i + 1]
        fe = {d: s[d][0] for d in jan}
        mm = {d: [s[d][1], s[d][2]] for d in jan}
        t0, t1 = tendencia(fe, mm, ds[i], False), tendencia(fe, mm, ds[i], True)
        vr = s[ds[i]][0] / s[ds[i - PREG_MINI + 1]][0] - 1          # mesma conta do miniGrafico (60 pregões)
        faixa = "alta" if vr > FAIXA_MINI else "queda" if vr < -FAIXA_MINI else "neutro"
        out.append((ds[i], (t0["classe"], t1["classe"], faixa), s[ds[i + PRAZO]][0] / s[ds[i]][0] - 1))
    return out


def contagens(linhas):
    """Por mês: [n, subiu, caiu] e, por regra, [n alta, subiu na alta, n queda, caiu na queda, soma r alta, soma r queda]."""
    import numpy as np
    meses = sorted({d[:7] for _, d, _, _ in linhas})
    ix = {m: i for i, m in enumerate(meses)}
    base = np.zeros((len(meses), 3))
    reg = np.zeros((len(REGRAS), len(meses), 6))
    for _, d, cls, r in linhas:
        m = ix[d[:7]]
        base[m] += (1, r > 0, r < 0)
        for k, c in enumerate(cls):
            if c == "alta":
                reg[k, m] += (1, r > 0, 0, 0, r, 0)
            elif c == "queda":
                reg[k, m] += (0, 0, 1, r < 0, 0, r)
    return meses, base, reg


def resumo(linhas, titulo, rnd):
    import numpy as np
    meses, base, reg = contagens(linhas)
    if not meses:
        return [f"\n### {titulo}: sem dados"]
    n_all, up_all, dn_all = base.sum(0)
    r_all = sum(r for *_, r in linhas) / len(linhas)
    idx = rnd.integers(0, len(meses), size=(B, len(meses)))
    bb = base[idx].sum(1)                                   # B × 3
    out = [f"\n### {titulo} — {int(n_all)} dias×papel, {len(meses)} meses; subiu em {100 * up_all / n_all:.1f}%, "
           f"caiu em {100 * dn_all / n_all:.1f}%; retorno médio em 20 pregões {100 * r_all:+.2f}%",
           "| regra | cor | dias | % dos dias | acerto % | linha de base % | diferença (pp) | IC 95% | retorno médio 20 pregões |",
           "|---|---|---|---|---|---|---|---|---|"]
    for k, nome in enumerate(REGRAS):
        tot = reg[k].sum(0)
        rb = reg[k][idx].sum(1)                             # B × 6
        for cor, (cn, ca, cr, bcol) in (("verde", (0, 1, 4, 1)), ("vermelho", (2, 3, 5, 2))):
            n = tot[cn]
            if n == 0:
                out.append(f"| {nome} | {cor} | 0 | 0 | — | — | — | — | — |"); continue
            ac, bs = tot[ca] / n, base.sum(0)[bcol] / n_all
            with np.errstate(invalid="ignore", divide="ignore"):
                dif = rb[:, ca] / rb[:, cn] - bb[:, bcol] / bb[:, 0]
            dif = dif[np.isfinite(dif)]
            lo, hi = np.percentile(dif, [2.5, 97.5]) * 100
            out.append(f"| {nome} | {cor} | {int(n)} | {100 * n / n_all:.1f} | {100 * ac:.1f} | {100 * bs:.1f} | "
                       f"{100 * (ac - bs):+.1f} | [{lo:+.1f}, {hi:+.1f}] | {100 * tot[cr] / n:+.2f}% |")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida")
    a = ap.parse_args()
    import numpy as np
    zips = sorted(glob.glob(os.path.join(a.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {a.zips}")
    serie = ler_zips(zips)
    todas, txt = [], ["# Tendência do minigráfico — back-test", "",
                      f"Arquivos: {', '.join(os.path.basename(z) for z in zips)}. Janela {JANELA} pregões, resultado "
                      f"{PRAZO} pregões depois. IC 95%: bootstrap em blocos mensais ({B} reamostras).", "",
                      "Papéis (pregões com máxima e mínima; ajustes de desdobramento/grupamento):"]
    por_papel = {}
    for nome in ATIVOS:
        s = serie[nome]
        if len(s) < JANELA + PRAZO:
            txt.append(f"- {nome}: só {len(s)} pregões, fora"); continue
        aj, ev = ajustar(s)
        ls = classificar(aj)
        por_papel[nome] = ls
        todas += [(nome, d, c, r) for d, c, r in ls]
        txt.append(f"- {nome}: {min(s)} a {max(s)}, {len(s)} pregões, {len(ls)} dias medidos; ajustes: {'; '.join(ev) or 'nenhum'}")
        print(txt[-1], flush=True)
    rnd = np.random.default_rng(20261104)
    for titulo, de, ate in PERIODOS:
        txt += resumo([x for x in todas if de <= x[1][:4] <= ate], titulo, rnd)
    txt += ["", "### Por papel (tudo), acerto % / linha de base % (dias)",
            "| papel | " + " | ".join(f"{r} verde | {r} vermelho" for r in REGRAS) + " |", "|---" * (1 + 2 * len(REGRAS)) + "|"]
    for nome, ls in por_papel.items():
        n = len(ls); up = sum(r > 0 for *_, r in ls) / n; dn = sum(r < 0 for *_, r in ls) / n
        cel = []
        for k in range(len(REGRAS)):
            al = [r for _, c, r in ls if c[k] == "alta"]; qu = [r for _, c, r in ls if c[k] == "queda"]
            cel.append(f"{100 * sum(r > 0 for r in al) / len(al):.0f} / {100 * up:.0f} ({len(al)})" if al else "—")
            cel.append(f"{100 * sum(r < 0 for r in qu) / len(qu):.0f} / {100 * dn:.0f} ({len(qu)})" if qu else "—")
        txt.append(f"| {nome} | " + " | ".join(cel) + " |")
    txt += ["", "Limitações: observações sobrepostas (cada dia entra, prazo de 20 pregões); bonificações e proventos não "
            "ajustados (a queda do dia ex entra no retorno, igual para a cor e para a linha de base); papéis medidos "
            "juntos, com pesos pelo número de dias."]
    # cor de hoje (série sem ajuste, como o app vê) e máxima/mínima dos últimos 160 pregões: prévia da tela antes do --ano
    import json
    hoje, mm_rec = {}, {}
    for nome in ATIVOS:
        s = serie[nome]
        if len(s) < 60:
            continue
        ds = sorted(s)[-160:]
        fe, mm = {d: s[d][0] for d in ds}, {d: [s[d][1], s[d][2]] for d in ds}
        t0, t1 = tendencia(fe, mm, ds[-1], False), tendencia(fe, mm, ds[-1], True)
        hoje[nome] = [ds[-1], t0["classe"], t1["classe"], round(t0["adx"], 1), round(t0["ifr"], 1)]
        mm_rec[nome] = mm
    txt += ["", "### Cor no último pregão (sem ajuste, como no app): data, sem IFR, com IFR, ADX, IFR"]
    txt += [f"- {n}: {v}" for n, v in hoje.items()]
    print("MAXMIN_RECENTE " + json.dumps(mm_rec, separators=(",", ":")))
    saida = "\n".join(txt)
    print(saida)
    if a.saida:
        with open(a.saida, "w", encoding="utf-8") as f:
            f.write(saida + "\n")


if __name__ == "__main__":
    main()
