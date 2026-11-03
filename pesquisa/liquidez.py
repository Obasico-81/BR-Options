#!/usr/bin/env python3
"""Quais papéis têm opções líquidas o bastante para o app? (etapa 3: ampliar os ativos)

Lê um COTAHIST anual e, para cada prefixo de opção (4 letras: PETR, ITUB, ...):
  - escolhe o papel à vista do prefixo (o de maior volume financeiro no ano: PETR4, ITUB4, ...) e só conta as opções
    cujo papel-objeto é ele (CODISI da opção = ISIN do papel; o prefixo BBDC também traz opções de BBDC3, por exemplo);
  - mede o volume financeiro diário das opções e quantas séries passam no corte de liquidez do app;
  - para os TOP prefixos, grava as cadeias dos últimos N pregões no mesmo formato do snapshot.json
    (montar_dia do atualizador), para o montador.js testar se as estruturas montam (liquidez_montador.js).

Uso: python pesquisa/liquidez.py --zip COTAHIST_A2026.ZIP --saida PASTA [--dias 40] [--top 25]
"""
import argparse, json, os, sys
from collections import defaultdict
from datetime import date
from statistics import median

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from atualizar_dados import campo, preco, iso, linhas_do_zip, montar_dia

VOLTOT = (171, 188)   # volume financeiro do papel no dia, (16)V99 — layout oficial do COTAHIST


def voltot(ln):
    return int(ln[VOLTOT[0] - 1:VOLTOT[1]] or 0) / 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True); ap.add_argument("--saida", required=True)
    ap.add_argument("--dias", type=int, default=40); ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--min-dias", type=int, default=20, help="pregões mínimos com opções para entrar no ranking")
    a = ap.parse_args(); os.makedirs(a.saida, exist_ok=True)

    # 1ª passada: papéis à vista (fechamento e volume) e prefixos que têm opções
    fech, vol_vista, prefixos, isin = defaultdict(dict), defaultdict(float), set(), {}
    for ln in linhas_do_zip(a.zip):
        if len(ln) < 210 or ln[0:2] != "01":
            continue
        tp = ln[24:27]
        if tp == "010":
            cod = campo(ln, "codneg"); p = preco(campo(ln, "preult"))
            isin[cod] = campo(ln, "codisi")
            if p > 0:
                fech[cod][iso(campo(ln, "data"))] = p; vol_vista[cod] += voltot(ln)
        elif tp in ("070", "080"):
            prefixos.add(ln[12:16])
    vista = {}
    for pf in prefixos:
        cand = [c for c in fech if c.startswith(pf) and len(c) in (5, 6)]
        if cand:
            vista[pf] = max(cand, key=lambda c: vol_vista[c])
    datas = sorted({d for s in fech.values() for d in s}); ultimos = set(datas[-a.dias:])

    # 2ª passada: opções
    vol_opc = defaultdict(lambda: defaultdict(float))        # pf -> dia -> R$
    liq = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # pf -> dia -> [calls, puts] líquidas perto do dinheiro
    cadeia = defaultdict(lambda: defaultdict(list))          # pf -> dia -> linhas (só últimos N dias)
    fora = defaultdict(lambda: [0, 0.0])                     # pf -> [linhas, R$] de opções de outro papel-objeto
    for ln in linhas_do_zip(a.zip):
        if len(ln) < 210 or ln[0:2] != "01":
            continue
        tp = ln[24:27]
        if tp not in ("070", "080"):
            continue
        pf = ln[12:16]
        if pf not in vista:
            continue
        if campo(ln, "codisi") != isin.get(vista[pf]):
            fora[pf][0] += 1; fora[pf][1] += voltot(ln); continue
        d = iso(campo(ln, "data")); vol_opc[pf][d] += voltot(ln)
        S = fech[vista[pf]].get(d)
        if not S:
            continue
        b, k, K = preco(campo(ln, "preofc")), preco(campo(ln, "preofv")), preco(campo(ln, "preexe"))
        q = int(campo(ln, "quatot") or 0); venc = iso(campo(ln, "datven"))
        dias = (date.fromisoformat(venc) - date.fromisoformat(d)).days
        if b > 0 and k >= b and (k - b) / ((k + b) / 2) <= 0.20 and q >= 500 and 7 <= dias <= 100 and K > 0 and abs(K / S - 1) <= 0.15:
            liq[pf][d][0 if tp == "070" else 1] += 1
        if d in ultimos:
            cadeia[pf][d].append(dict(t="C" if tp == "070" else "P", k=K, b=b, a=k, v=q, venc=venc, s=campo(ln, "codneg")))

    linhas = []
    for pf, porDia in vol_opc.items():
        ds = sorted(porDia)
        if len(ds) < a.min_dias:
            continue
        lc = [liq[pf][d][0] for d in ds]; lp = [liq[pf][d][1] for d in ds]
        linhas.append(dict(prefixo=pf, papel=vista[pf], dias=len(ds), vol_mediano_mil=median(porDia[d] for d in ds) / 1000,
                           calls_liq=median(lc), puts_liq=median(lp),
                           dias_2c2p=100 * sum(1 for c, p in zip(lc, lp) if c >= 2 and p >= 2) / len(ds),
                           preco=fech[vista[pf]][max(fech[vista[pf]])]))
    linhas.sort(key=lambda r: -r["vol_mediano_mil"])
    print(f"Pregões no arquivo: {len(datas)} ({datas[0]} a {datas[-1]}). Corte do app: spread <= 20%, quantidade >= 500, 7 a 100 dias, strike a até 15% do preço.")
    print(f"{'prefixo':8}{'papel':8}{'dias':>5}{'vol. opções/dia (R$ mil, mediana)':>36}{'calls líq.':>12}{'puts líq.':>11}{'% dias c/ 2C+2P':>17}{'preço':>10}")
    for r in linhas[:60]:
        print(f"{r['prefixo']:8}{r['papel']:8}{r['dias']:>5}{r['vol_mediano_mil']:>36,.0f}{r['calls_liq']:>12.0f}{r['puts_liq']:>11.0f}{r['dias_2c2p']:>16.0f}%{r['preco']:>10.2f}")

    mostrar = sorted((pf for pf in fora if pf in {r["prefixo"] for r in linhas[:60]}), key=lambda pf: -fora[pf][1])
    if mostrar:
        print("\nOpções de outro papel-objeto com o mesmo prefixo, fora da conta (linhas no ano · R$ milhões no ano):")
        for pf in mostrar:
            print(f"  {pf} (papel do ranking: {vista[pf]}): {fora[pf][0]} · {fora[pf][1] / 1e6:,.1f}")

    # cadeias dos últimos N pregões para os TOP prefixos, no formato do snapshot
    saida = {}
    for r in linhas[:a.top]:
        pf = r["prefixo"]; por = {}
        for d in sorted(cadeia[pf]):
            S = fech[vista[pf]].get(d)
            if S:
                por[d] = montar_dia(d, S, cadeia[pf][d])
        saida[pf] = dict(papel=vista[pf], por_data=por)
    json.dump(saida, open(os.path.join(a.saida, "cadeias_top.json"), "w"), separators=(",", ":"))
    json.dump(linhas, open(os.path.join(a.saida, "liquidez.json"), "w"), ensure_ascii=False, indent=0)
    print(f"\nCadeias de {len(saida)} prefixos x até {a.dias} pregões gravadas em cadeias_top.json")


if __name__ == "__main__":
    main()
