#!/usr/bin/env python3
"""Robustez do histórico das operações e saídas antecipadas (3, 7 e 15 dias corridos depois da entrada).

Hipóteses e critério fixados antes de rodar (16/11/2026):
  H1. O resultado médio positivo do strangle comprado e da call comprada (segurando até o vencimento) é robusto: o IC 95%
      do resultado médio fica inteiro acima de zero E o resultado médio é positivo em 2015–2020 e em 2021–2026.
      Se falhar qualquer parte, não se comunica rentabilidade dessas operações.
  H2. "Ganhar mais vezes não é ganhar mais" nas travas: o Lucro frequente tem frequência de lucro maior e resultado médio
      menor que o Lucro maior, nos dois períodos.
  Medidas descritivas (sem hipótese): saída 3, 7 e 15 dias corridos depois da entrada (no primeiro pregão a partir da
  data, antes do vencimento), no pior lado do fechamento (vende pela melhor compra, recompra pela melhor venda) e no preço
  médio (limite otimista); resultado por ativo; efeito da corretagem de R$ 5 por ordem numa operação de até R$ 500 de risco.

Mesmas operações do pesquisa/historico.py (montador.py do app, Selic do dia, a cada 5 pregões, 8 papéis, 14 variações).
Resultado em % do risco máximo da operação, depois das taxas da B3 de entrada e saída. IC 95%: bootstrap em blocos
mensais. Só mede; não escolhe parâmetro.

Uso: python pesquisa/robustez.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida r.md] [--selic serie.json]
"""
import argparse, glob, os, sys
from collections import defaultdict
from datetime import date, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..")); sys.path.insert(0, AQUI)
import atualizar_dados as AD                                                          # noqa: E402
import montador as MT                                                                  # noqa: E402
import replay as RP                                                                    # noqa: E402
from juro import serie_selic, selic_em                                                 # noqa: E402
from historico import VARIANTES, montar, boot, B                                        # noqa: E402

SAIDAS = (3, 7, 15)                       # dias corridos depois da entrada
PERIODOS = (("2015–2020", "2015", "2020"), ("2021–2026", "2021", "2026"))
CORRETAGEM, RISCO_USUARIO = 5.0, 500.0   # R$ por ordem; risco máximo de quem abre o app


def saida_em(m, px, venc, alvo, pior):
    """Resultado (R$, antes das taxas) desfazendo no primeiro pregão >= alvo e < venc, com preço das duas pontas em até
    3 pregões; None se faltar preço. pior: vende pela compra e recompra pela venda; senão, preço médio."""
    dias = sorted({d for _, o in m.pernas for d in px.get((o.simbolo, venc), {}) if alvo <= d < venc})
    for d in dias[:3]:
        v = 0.0
        for l, o in m.pernas:
            q = px.get((o.simbolo, venc), {}).get(d)
            if not q or not (q[0] > 0 and q[1] >= q[0]):
                v = None; break
            v += l * ((q[0] if l > 0 else q[1]) if pior else (q[0] + q[1]) / 2)
        if v is not None:
            return v * MT.LOTE * m.lotes - m.premio
    return None


_CACHE = {}


def media_ic(R, chave, rnd):
    """Média e IC 95% (bootstrap em blocos mensais); a mesma consulta devolve o mesmo IC (a tabela e as hipóteses batem)."""
    ck = (id(R[0]) if R else None, len(R), chave)
    if ck in _CACHE:
        return _CACHE[ck]
    _CACHE[ck] = _media_ic(R, chave, rnd)
    return _CACHE[ck]


def _media_ic(R, chave, rnd):
    pm = defaultdict(list)
    for r in R:
        if r[chave] is not None:
            pm[r["data"][:7]].append(r[chave])
    vals = [v for L in pm.values() for v in L]
    if not vals:
        return None, (float("nan"), float("nan")), 0
    return sum(vals) / len(vals), boot(pm, rnd), len(vals)


def pct(x):
    return "—" if x is None or x != x else f"{100 * x:+.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida"); ap.add_argument("--passo", type=int, default=5)
    ap.add_argument("--selic")
    a = ap.parse_args()
    import numpy as np
    rnd = np.random.default_rng(20261117)
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
        for k, _, (tese, perfil) in VARIANTES:
            m = montar(tese, perfil, S, ch, p["iv"])
            if not isinstance(m, str):
                ops.append(dict(k=k, ativo=nome, data=dia, m=m, venc=vencs[m.pernas[0][1].simbolo]))
    MT.set_juro(MT.R_PADRAO)
    ultimo = datas[-1]
    ops = [o for o in ops if o["venc"] <= ultimo]
    print(f"{len(ops)} montagens com vencimento até {ultimo}", flush=True)
    px = RP.ler_precos(zips, {(o.simbolo, op["venc"]) for op in ops for _, o in op["m"].pernas})
    R, falta = [], defaultdict(int)
    for op in ops:
        m, venc = op["m"], op["venc"]
        ST = RP.fech_no(fech[op["ativo"]], venc)
        if ST is None:
            continue
        risco = m.perda_max
        ks = [RP.strike_final(o, px.get((o.simbolo, venc), {}), venc) for _, o in m.pernas]
        venc_r = (RP.no_vencimento(m, ST, ks) - m.custo_taxas) / risco
        # corretagem numa operação de até R$ 500 de risco (o mesmo número de lotes que o app montaria)
        r1 = risco / m.lotes; lotes_u = max(1, int(RISCO_USUARIO // r1)); risco_u = lotes_u * r1; n = len(m.pernas)
        linha = dict(k=op["k"], ativo=op["ativo"], data=op["data"], venc=venc_r, venc_cor=venc_r - CORRETAGEM * n / risco_u)
        for N in SAIDAS:
            alvo = (date.fromisoformat(op["data"]) + timedelta(days=N)).isoformat()
            if alvo >= venc:   # vence antes: é o mesmo que segurar até o vencimento
                linha[f"s{N}"] = linha[f"m{N}"] = venc_r; linha[f"s{N}_cor"] = linha["venc_cor"]; continue
            sp, sm = saida_em(m, px, venc, alvo, True), saida_em(m, px, venc, alvo, False)
            if sp is None:
                falta[N] += 1
            linha[f"s{N}"] = None if sp is None else (sp - m.custo_taxas) / risco
            linha[f"m{N}"] = None if sm is None else (sm - m.custo_taxas) / risco
            linha[f"s{N}_cor"] = None if sp is None else linha[f"s{N}"] - 2 * CORRETAGEM * n / risco_u
        R.append(linha)
    print(f"{len(R)} operações medidas; sem preço para sair: " + ", ".join(f"{N} dias {falta[N]}" for N in SAIDAS), flush=True)

    txt = ["# Robustez do histórico e saídas antecipadas", "",
           f"Arquivos: {os.path.basename(zips[0])} a {os.path.basename(zips[-1])}; {len(R)} operações com vencimento até {ultimo}. "
           "Resultado médio por operação, em % do risco máximo, depois das taxas da B3; IC 95% por bootstrap em blocos mensais "
           f"({B} reamostras). Saídas em dias corridos depois da entrada (primeiro pregão a partir da data, com preço nas duas "
           "pontas em até 3 pregões). Corretagem: R$ 5 por ordem numa operação de até R$ 500 de risco.", "",
           "## 1. Segurando até o vencimento", "",
           "| operação | operações | resultado médio | IC 95% | 2015–2020 | 2021–2026 | ativos com média positiva | com corretagem |",
           "|---|---|---|---|---|---|---|---|"]
    for k, nome, _ in VARIANTES:
        F = [r for r in R if r["k"] == k]
        if not F:
            continue
        mu, ic, n = media_ic(F, "venc", rnd)
        per = [media_ic([r for r in F if de <= r["data"][:4] <= ate], "venc", rnd)[0] for _, de, ate in PERIODOS]
        at = defaultdict(list)
        for r in F:
            at[r["ativo"]].append(r["venc"])
        pos = sum(1 for v in at.values() if len(v) >= 20 and sum(v) / len(v) > 0); tot = sum(1 for v in at.values() if len(v) >= 20)
        mc = sum(r["venc_cor"] for r in F) / len(F)
        txt.append(f"| {nome} | {n} | {pct(mu)} | [{pct(ic[0])}; {pct(ic[1])}] | {pct(per[0])} | {pct(per[1])} | {pos} de {tot} | {pct(mc)} |")

    txt += ["", "## 2. Saída antecipada, no pior lado do fechamento (vende pela compra, recompra pela venda)", "",
            "| operação | " + " | ".join(f"{N} dias: média [IC 95%] · com lucro" for N in SAIDAS) + " | vencimento: com lucro |",
            "|---|" + "---|" * (len(SAIDAS) + 1)]
    for k, nome, _ in VARIANTES:
        F = [r for r in R if r["k"] == k]
        if not F:
            continue
        cel = []
        for N in SAIDAS:
            mu, ic, n = media_ic(F, f"s{N}", rnd)
            vals = [r[f"s{N}"] for r in F if r[f"s{N}"] is not None]
            cel.append(f"{pct(mu)} [{pct(ic[0])}; {pct(ic[1])}] · {100 * sum(v > 0 for v in vals) / len(vals):.0f}%" if vals else "—")
        txt.append(f"| {nome} | " + " | ".join(cel) + f" | {100 * sum(r['venc'] > 0 for r in F) / len(F):.0f}% |")

    txt += ["", "## 3. Saída antecipada no preço médio (limite otimista) e com corretagem (pior lado)", "",
            "| operação | " + " | ".join(f"{N} dias, médio" for N in SAIDAS) + " | " + " | ".join(f"{N} dias, pior lado + corretagem" for N in SAIDAS) + " |",
            "|---|" + "---|" * (2 * len(SAIDAS))]
    for k, nome, _ in VARIANTES:
        F = [r for r in R if r["k"] == k]
        if not F:
            continue
        med = [media_ic(F, f"m{N}", rnd)[0] for N in SAIDAS]
        cor = []
        for N in SAIDAS:
            vals = [r[f"s{N}_cor"] for r in F if r[f"s{N}"] is not None]
            cor.append(sum(vals) / len(vals) if vals else None)
        txt.append(f"| {nome} | " + " | ".join(pct(x) for x in med) + " | " + " | ".join(pct(x) for x in cor) + " |")

    # hipóteses
    def h1(k):
        F = [r for r in R if r["k"] == k]; mu, ic, _ = media_ic(F, "venc", rnd)
        per = [media_ic([r for r in F if de <= r["data"][:4] <= ate], "venc", rnd)[0] for _, de, ate in PERIODOS]
        return ic[0] > 0 and all(p is not None and p > 0 for p in per), mu, ic, per
    txt += ["", "## Hipóteses", ""]
    for k in ("forte/eq", "aposta_alta/maior", "aposta_alta/eq", "aposta_alta/freq"):
        ok, mu, ic, per = h1(k)
        nome = next(n for kk, n, _ in VARIANTES if kk == k)
        txt.append(f"- H1 {nome}: {'PASSA' if ok else 'NÃO PASSA'} (média {pct(mu)}, IC [{pct(ic[0])}; {pct(ic[1])}], "
                   f"2015–2020 {pct(per[0])}, 2021–2026 {pct(per[1])})")
    for lado in ("alta", "baixa"):
        res = []
        for _, de, ate in PERIODOS:
            fq = [r for r in R if r["k"] == f"{lado}/freq" and de <= r["data"][:4] <= ate]
            mx = [r for r in R if r["k"] == f"{lado}/maior" and de <= r["data"][:4] <= ate]
            if fq and mx:
                wf, wm = sum(r["venc"] > 0 for r in fq) / len(fq), sum(r["venc"] > 0 for r in mx) / len(mx)
                rf, rm = sum(r["venc"] for r in fq) / len(fq), sum(r["venc"] for r in mx) / len(mx)
                res.append((wf > wm and rf < rm, wf, wm, rf, rm))
        ok = len(res) == 2 and all(x[0] for x in res)
        txt.append(f"- H2 trava de {lado}: {'PASSA' if ok else 'NÃO PASSA'} (" + "; ".join(
            f"{p[0]}: com lucro {100 * x[1]:.0f}% × {100 * x[2]:.0f}%, média {pct(x[3])} × {pct(x[4])}" for p, x in zip(PERIODOS, res)) + ", Lucro frequente × Lucro maior)")
    saida = "\n".join(txt)
    print(saida)
    if a.saida:
        open(a.saida, "w", encoding="utf-8").write(saida + "\n")


if __name__ == "__main__":
    main()
