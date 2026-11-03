#!/usr/bin/env python3
"""Monta a base da pesquisa a partir dos arquivos anuais COTAHIST da B3 (no lugar dos CSV do rb3).

Gera, para cada papel, no formato que os scripts de pesquisa/ leem:
  {ATIVO}_opc_{SUF}.csv   colunas do rb3: refdate, instrument_market, maturity_date, strike_price,
                          best_bid, best_ask, traded_contracts (+ symbol)
  ser_{ativo}{SUF}.pkl    DataFrame com a coluna S (fechamento do papel à vista), índice = data do pregão

Corte já aplicado nas opções (o filtro comum a todos os scripts de pesquisa/): call ou put (070/080),
melhor compra > 0, melhor venda >= melhor compra, 30 a 60 dias até o vencimento, quantidade negociada >= 100.
Os scripts aplicam por cima os próprios filtros (volume >= 1.000, spread <= 10% etc.).

Uso: python pesquisa/montar_base.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP --saida PASTA --suf 1526
"""
import argparse, csv, glob, os, sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from atualizar_dados import campo, preco, iso, linhas_do_zip   # leitor validado com o arquivo real (--validar IGUAL)

# nome curto usado pelos scripts -> (prefixo das opções, papel à vista)
PAPEIS = {"bova": ("BOVA", "BOVA11"), "petr": ("PETR", "PETR4"), "vale": ("VALE", "VALE3"),
          "bbas": ("BBAS", "BBAS3"), "bbdc": ("BBDC", "BBDC4"), "itub": ("ITUB", "ITUB4")}
COLUNAS = ["refdate", "instrument_market", "maturity_date", "strike_price", "best_bid", "best_ask",
           "traded_contracts", "symbol"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida", required=True); ap.add_argument("--suf", default="1526")
    a = ap.parse_args()
    import pandas as pd
    os.makedirs(a.saida, exist_ok=True)
    prefixo = {pref: at for at, (pref, _) in PAPEIS.items()}
    papel = {pap: at for at, (_, pap) in PAPEIS.items()}
    arq = {at: open(os.path.join(a.saida, f"{at.upper()}_opc_{a.suf}.csv"), "w", newline="") for at in PAPEIS}
    esc = {at: csv.writer(f) for at, f in arq.items()}
    for w in esc.values():
        w.writerow(COLUNAS)
    fech = {at: {} for at in PAPEIS}
    n_opc = {at: 0 for at in PAPEIS}
    zips = sorted(glob.glob(os.path.join(a.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {a.zips}")
    # 1ª passada: ISIN de cada papel à vista. A opção só entra se o papel-objeto (CODISI) for o papel da pesquisa:
    # o prefixo de 4 letras também traz opções de outro papel (PETR: PETR3; BBDC: BBDC3; ITUB: ITUB3). Até 03/11/2026
    # a base misturava essas opções (o atualizador do app já filtra desde então).
    isin = {at: set() for at in PAPEIS}
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) >= 242 and ln[0:2] == "01" and ln[24:27] == "010" and campo(ln, "codneg") in papel:
                isin[papel[campo(ln, "codneg")]].add(campo(ln, "codisi"))
    print("ISIN dos papéis:", {at: sorted(v) for at, v in isin.items()}, flush=True)
    fora = {at: 0 for at in PAPEIS}
    for z in zips:
        n0 = sum(n_opc.values())
        for ln in linhas_do_zip(z):
            if len(ln) < 210 or ln[0:2] != "01":
                continue
            tp = ln[24:27]
            if tp == "010":
                cod = campo(ln, "codneg")
                if cod in papel:
                    p = preco(campo(ln, "preult"))
                    if p > 0:
                        fech[papel[cod]][iso(campo(ln, "data"))] = p
                continue
            if tp not in ("070", "080"):
                continue
            at = prefixo.get(ln[12:16])
            if not at:
                continue
            if campo(ln, "codisi") not in isin[at]:
                fora[at] += 1
                continue
            b, k = preco(campo(ln, "preofc")), preco(campo(ln, "preofv"))
            q = int(campo(ln, "quatot") or 0)
            if not (b > 0 and k >= b and q >= 100):
                continue
            d, v = iso(campo(ln, "data")), iso(campo(ln, "datven"))
            dias = (date.fromisoformat(v) - date.fromisoformat(d)).days
            if not 30 <= dias <= 60:
                continue
            esc[at].writerow([d, int(tp), v, preco(campo(ln, "preexe")), b, k, q, campo(ln, "codneg")])
            n_opc[at] += 1
        print(f"{os.path.basename(z)}: {sum(n_opc.values()) - n0} opções", flush=True)
    for f in arq.values():
        f.close()
    print("Opções de outro papel-objeto descartadas (linhas):", fora, flush=True)
    for at, serie in fech.items():
        s = pd.Series(serie, dtype=float); s.index = pd.to_datetime(s.index); s = s.sort_index()
        pd.DataFrame({"S": s}).to_pickle(os.path.join(a.saida, f"ser_{at}{a.suf}.pkl"))
        print(f"{at}: {n_opc[at]} opções, {len(s)} fechamentos ({s.index.min().date() if len(s) else '-'} a "
              f"{s.index.max().date() if len(s) else '-'})", flush=True)


if __name__ == "__main__":
    main()
