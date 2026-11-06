#!/usr/bin/env python3
"""Dias seguidos sem operação, por papel do app (decisão de manter ou tirar papéis da lista).

Para cada pregão de cada papel, com a cadeia que o atualizador montaria (montar_dia) e o montador.py do app, nas quatro
operações do Início (trava de alta, trava de baixa, strangle comprado, put vendida coberta):
  liquidez   alguma monta em algum vencimento, sem limite de risco nem de caixa (só a liquidez das opções)
  padrão     alguma cabe no perfil de quem abre o app (risco máximo R$ 500, capital R$ 12.000) no vencimento que o app
             escolhe sozinho (o mais perto de 45 dias)
  qualquer   alguma cabe no perfil padrão em algum vencimento (o usuário troca o vencimento)
"Cabe": o risco de um lote está dentro do risco máximo (o app reduz os lotes até caber) e, na put vendida, o caixa de um
lote está dentro do capital. Só mede; não escolhe nada.

Uso: python pesquisa/disponibilidade.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida resultado.txt]
"""
import argparse, glob, os, sys
from collections import defaultdict

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
from atualizar_dados import ATIVOS, campo, preco, iso, linhas_do_zip, montar_dia   # noqa: E402
import montador as MT                                                             # noqa: E402

TESES = ("alta", "baixa", "forte", "alta_com_caixa")
RISCO, CAPITAL, PRAZO = 500, 12000, 45
CRIT = ("liquidez", "padrão", "qualquer")


def ler(zips):
    papeis = {pap: nome for nome, (_, pap) in ATIVOS.items()}
    prefixos = {pref: nome for nome, (pref, _) in ATIVOS.items()}
    fech, isin, opc = defaultdict(dict), defaultdict(set), defaultdict(list)
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) < 242 or ln[0:2] != "01":
                continue
            tp = ln[24:27]
            if tp == "010":
                nome = papeis.get(campo(ln, "codneg"))
                if nome and preco(campo(ln, "preult")) > 0:
                    fech[nome][iso(campo(ln, "data"))] = preco(campo(ln, "preult")); isin[nome].add(campo(ln, "codisi"))
            elif tp in ("070", "080"):
                cod = campo(ln, "codneg"); nome = prefixos.get(cod[:4])
                if nome:
                    b, a = preco(campo(ln, "preofc")), preco(campo(ln, "preofv"))
                    opc[(nome, iso(campo(ln, "data")))].append((campo(ln, "codisi"), dict(
                        t="C" if tp == "070" else "P", k=preco(campo(ln, "preexe")), b=b, a=a, v=int(campo(ln, "quatot") or 0),
                        venc=iso(campo(ln, "datven")), s=cod)))
        print(f"{os.path.basename(z)} lido", flush=True)
    return fech, isin, opc


def cabe(m, risco, capital):
    if isinstance(m, str):
        return False
    caixa1 = m.pernas[0][1].strike * MT.LOTE if m.tese == "alta_com_caixa" else 0
    return m.perda_max / m.lotes <= risco + 1e-9 and caixa1 <= capital


def dia(S, iv, chain):
    """{critério: True/False} num pregão."""
    r = dict.fromkeys(CRIT, False)
    vs = sorted({o.dias for o in chain if 10 <= o.dias <= 150})
    if not vs:
        return r
    padrao = sorted(vs, key=lambda d: abs(d - PRAZO))[0]   # como o app: o mais perto de 45 dias (empate: o mais curto)
    for t in TESES:
        for d in vs:
            m = MT.montar(t, S, chain, iv, 1e9, prazo_alvo=d, caixa=1e9)
            if isinstance(m, str):
                continue
            r["liquidez"] = True
            if cabe(m, RISCO, CAPITAL):
                r["qualquer"] = True
        if cabe(MT.montar(t, S, chain, iv, 1e9, prazo_alvo=padrao, caixa=1e9), RISCO, CAPITAL):
            r["padrão"] = True
    return r


def seq_final(xs):
    """Quantos dos últimos pregões seguidos são False."""
    n = 0
    for x in reversed(xs):
        if x:
            break
        n += 1
    return n


def maior_seq(xs):
    m = n = 0
    for x in xs:
        n = 0 if x else n + 1; m = max(m, n)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida")
    a = ap.parse_args()
    zips = sorted(glob.glob(os.path.join(a.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {a.zips}")
    fech, isin, opc = ler(zips)
    res = {}
    for nome in ATIVOS:
        serie = []
        for d in sorted(fech[nome]):
            linhas = [o for c, o in opc.get((nome, d), []) if c in isin[nome]]
            p = montar_dia(d, fech[nome][d], linhas)
            ch = [MT.Opcao(o["t"], o["k"], o["b"], o["a"], o["v"], o["d"], o["s"]) for o in p["chain"]]
            serie.append((d, dia(p["S"], p["iv"], ch)))
        res[nome] = serie
        print(f"{nome}: {len(serie)} pregões", flush=True)
    fim = max(d for s in res.values() for d, _ in s)
    txt = ["# Dias com operação disponível, por papel", "",
           f"Arquivos: {', '.join(os.path.basename(z) for z in zips)}; último pregão {fim}. Operações do Início (travas de alta "
           f"e de baixa, strangle comprado, put vendida coberta), montador.py do app.",
           "- liquidez: alguma monta em algum vencimento, sem limite de risco nem de caixa",
           f"- padrão: alguma cabe no perfil de quem abre o app (risco R$ {RISCO}, capital R$ {CAPITAL:,}) no vencimento que o app escolhe (o mais perto de {PRAZO} dias)".replace(",", "."),
           "- qualquer: alguma cabe no perfil padrão em algum vencimento", "",
           "Sequência atual = pregões seguidos, até o último, sem nenhuma operação pelo critério. % = pregões com operação.", ""]
    for ano in sorted({d[:4] for s in res.values() for d, _ in s}):
        txt += [f"## {ano}", "", "| papel | pregões | " + " | ".join(f"% {c}" for c in CRIT) + " | maior sequência sem (liquidez) | maior sequência sem (padrão) |",
                "|---" * (4 + len(CRIT)) + "|"]
        for nome, s in res.items():
            s = [(d, r) for d, r in s if d[:4] == ano]
            if not s:
                continue
            n = len(s)
            txt.append(f"| {nome} | {n} | " + " | ".join(f"{100 * sum(r[c] for _, r in s) / n:.0f}%" for c in CRIT) +
                       f" | {maior_seq([r['liquidez'] for _, r in s])} | {maior_seq([r['padrão'] for _, r in s])} |")
        txt.append("")
    txt += ["## Situação até o último pregão", "",
            "| papel | sequência atual sem (liquidez) | sem (padrão) | sem (qualquer) | último dia com operação (liquidez) | últimos 30 pregões (liquidez: █ monta, · não) |",
            "|---|---|---|---|---|---|"]
    for nome, s in res.items():
        if not s:
            txt.append(f"| {nome} | sem dados | | | | |"); continue
        liq = [r["liquidez"] for _, r in s]
        ult = max((d for d, r in s if r["liquidez"]), default="—")
        tira = "".join("█" if x else "·" for x in liq[-30:])
        txt.append(f"| {nome} | {seq_final(liq)} | {seq_final([r['padrão'] for _, r in s])} | {seq_final([r['qualquer'] for _, r in s])} | {ult} | `{tira}` |")
    saida = "\n".join(txt)
    print(saida)
    if a.saida:
        with open(a.saida, "w", encoding="utf-8") as f:
            f.write(saida + "\n")


if __name__ == "__main__":
    main()
