#!/usr/bin/env python3
"""Replay do app no histórico: as operações que o montador.py monta, refeitas a cada 5 pregões de 2015 até hoje com a
cadeia do dia (mesma filtragem do atualizador), acompanhadas até a saída. Só mede; não escolhe parâmetro.

Perguntas (fixadas antes de rodar):
  1. Calibração: quando a tela mostra "Chance implícita no preço" de X%, em quantas operações o papel terminou além do
     ponto de equilíbrio no vencimento? E em quantas houve lucro depois das taxas (segurando até o vencimento)?
  2. Regra de saída (alvo 50% do ganho máximo, limite 70% do risco, prazo 7 dias antes do vencimento): comparada a
     segurar até o vencimento, muda a frequência de lucro, o resultado médio e as perdas grandes?
  3. Uma operação por vez (a próxima só depois da saída da anterior), por papel e estrutura: maior sequência de
     perdas seguidas e maior queda acumulada, em múltiplos do risco de uma operação.

Execução no pior lado (compra na venda, venda na compra), taxas da B3 de entrada e saída (as do montador), sem
corretagem. Risco aceito e caixa grandes para a montagem não parar no limite do usuário (o resultado vai em fração
do risco; na put vendida coberta o limite de perda vira 70% do risco por lote). Vencimento: fechamento do papel no
dia do vencimento (ou o último pregão até 4 dias antes).

Uso: python pesquisa/replay.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida resultado.txt] [--passo 5]
"""
import argparse, glob, math, os, sys
from collections import defaultdict
from datetime import date, timedelta

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
from atualizar_dados import ATIVOS, campo, preco, iso, linhas_do_zip, montar_dia      # noqa: E402
import montador as MT                                                                 # noqa: E402
from dataclasses import replace                                                      # noqa: E402

TESES = ("alta", "baixa", "forte", "alta_com_caixa", "aposta_alta", "aposta_baixa")
NOME = {"alta": "Trava de alta", "baixa": "Trava de baixa", "forte": "Strangle comprado", "alta_com_caixa": "Put vendida coberta",
        "aposta_alta": "Call comprada", "aposta_baixa": "Put comprada"}
PERIODOS = (("2015–2020", "2015", "2020"), ("2021–2025", "2021", "2025"), ("2026", "2026", "2026"), ("tudo", "0000", "9999"))
B = 2000
PERDA = CAIXA = 1e8   # risco aceito >= risco total, como o app garante (limiteRisco): o limite da put vendida fica em 70% do risco


# ---------- leitura ----------
def ler_spot(zips):
    papeis = {pap: nome for nome, (_, pap) in ATIVOS.items()}
    fech, isin = {n: {} for n in ATIVOS}, {n: set() for n in ATIVOS}
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) < 242 or ln[0:2] != "01" or ln[24:27] != "010":
                continue
            cod = campo(ln, "codneg")
            if cod in papeis:
                p = preco(campo(ln, "preult"))
                if p > 0:
                    fech[papeis[cod]][iso(campo(ln, "data"))] = p
                    isin[papeis[cod]].add(campo(ln, "codisi"))
    return fech, isin


def ler_cadeias(zips, dias, isin):
    """opc[(nome, data)] = linhas das opções do papel (filtro pelo papel-objeto) nos dias pedidos."""
    prefixos = {pref: nome for nome, (pref, _) in ATIVOS.items()}
    alvo = {d.replace("-", "") for d in dias}
    # só séries de 5 a 100 dias (as que o atualizador põe na cadeia): limites em AAAAMMDD por dia de entrada
    lim = {d.replace("-", ""): ((date.fromisoformat(d) + timedelta(days=5)).strftime("%Y%m%d"),
                                 (date.fromisoformat(d) + timedelta(days=100)).strftime("%Y%m%d")) for d in dias}
    opc = defaultdict(list)
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) < 242 or ln[0:2] != "01" or ln[2:10] not in alvo:
                continue
            tp = ln[24:27]
            if tp not in ("070", "080"):
                continue
            lo, hi = lim[ln[2:10]]
            if not lo <= ln[202:210] <= hi:
                continue
            cod = campo(ln, "codneg"); nome = prefixos.get(cod[:4])
            if not nome or campo(ln, "codisi") not in isin[nome]:
                continue
            b, a = preco(campo(ln, "preofc")), preco(campo(ln, "preofv"))
            if not (b > 0 and a >= b):
                continue
            opc[(nome, iso(campo(ln, "data")))].append(dict(
                t="C" if tp == "070" else "P", k=preco(campo(ln, "preexe")), b=b, a=a,
                v=int(campo(ln, "quatot") or 0), venc=iso(campo(ln, "datven")), s=cod))
    return opc


def ler_precos(zips, vigiar):
    """px[(símbolo, vencimento)][data] = [compra, venda, strike] das séries vigiadas (as pernas das montagens). O strike
    do dia importa no vencimento: a B3 ajusta o strike por proventos e desdobramentos durante a vida da opção."""
    simbolos = {s for s, _ in vigiar}
    px = defaultdict(dict)
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) < 242 or ln[0:2] != "01" or ln[24:27] not in ("070", "080"):
                continue
            cod = campo(ln, "codneg")
            if cod not in simbolos:
                continue
            chave = (cod, iso(campo(ln, "datven")))
            if chave in vigiar:
                px[chave][iso(campo(ln, "data"))] = [preco(campo(ln, "preofc")), preco(campo(ln, "preofv")), preco(campo(ln, "preexe"))]
    return px


# ---------- montagem e resultado ----------
def montar_tudo(nome, dia, S, linhas):
    p = montar_dia(dia, S, linhas)
    ch = [MT.Opcao(o["t"], o["k"], o["b"], o["a"], o["v"], o["d"], o["s"]) for o in p["chain"]]
    vencs = {o["s"]: o["venc"] for o in linhas}
    out = []
    for t in TESES:
        if t.startswith("aposta"):
            m = MT.montar_aposta(t.split("_")[1], S, ch, p["iv"], PERDA)
        else:
            m = MT.montar(t, S, ch, p["iv"], PERDA, caixa=CAIXA)
        if isinstance(m, str):
            continue
        venc = vencs[m.pernas[0][1].simbolo]
        out.append(dict(ativo=nome, data=dia, tese=t, m=m, venc=venc, S=S, iv=p["iv"]))
    return out


def intrinseco(tipo, K, ST):
    return max(0.0, ST - K) if tipo == "C" else max(0.0, K - ST)


def no_vencimento(m, ST, ks):
    """ks: strike de cada perna no último pregão da série (ajustado pela B3, se houve evento)."""
    return sum(l * intrinseco(o.tipo, k, ST) for (l, o), k in zip(m.pernas, ks)) * MT.LOTE * m.lotes - m.premio


def strike_final(o, serie, venc):
    ds = [d for d in serie if d <= venc]
    return serie[max(ds)][2] if ds and serie[max(ds)][2] > 0 else o.strike


def alem_do_equilibrio(tese, eq, ST):
    if tese in ("alta", "alta_com_caixa", "aposta_alta"):
        return ST > eq[0]
    if tese in ("baixa", "aposta_baixa"):
        return ST < eq[0]
    return ST < eq[0] or ST > eq[1]


R_JURO = 0.11   # o mesmo juro com que o atualizador tira a volatilidade implícita (atualizar_dados.R)


def chance_com_juro(tese, S, eq, dias, vol, r=R_JURO):
    """Mesma conta da tela (prob_acima), com o juro na deriva: d2 = (ln(S/K) + (r − σ²/2)t) / (σ√t)."""
    t = dias / 365
    acima = lambda K: 0.5 * (1 + math.erf((math.log(S / K) + (r - 0.5 * vol * vol) * t) / (vol * math.sqrt(t)) / math.sqrt(2)))
    if tese in ("alta", "alta_com_caixa", "aposta_alta"):
        return acima(eq[0])
    if tese in ("baixa", "aposta_baixa"):
        return 1 - acima(eq[0])
    return acima(eq[1]) + 1 - acima(eq[0])


def no_pior_lado(m, precos):
    """Desfazer no pior lado do fechamento (vende pela compra, recompra pela venda), sem piso: a marcação antiga do app,
    aqui só para medir a execução ruim. None se faltar preço."""
    v = 0.0
    for l, o in m.pernas:
        p = (precos or {}).get(o.simbolo)
        if not p or not p[0] > 0 or not p[1] >= p[0]:
            return None
        v += p[0] if l > 0 else -p[1]
    return v * MT.LOTE * m.lotes - m.premio


def no_meio(m, precos):
    """Resultado se a operação fosse desfeita no preço médio (compra+venda)/2 de cada perna. None se faltar preço."""
    v = 0.0
    for l, o in m.pernas:
        p = (precos or {}).get(o.simbolo)
        if not p or not p[0] > 0 or not p[1] >= p[0]:
            return None
        v += l * (p[0] + p[1]) / 2
    return v * MT.LOTE * m.lotes - m.premio


def fech_no(fech, venc):
    ds = [d for d in fech if d <= venc]
    if not ds:
        return None
    d = max(ds)
    return fech[d] if d >= (date.fromisoformat(venc) - timedelta(days=4)).isoformat() else None


# ---------- estatística ----------
def boot_media(vals_por_mes, rnd):
    """IC 95% da média, reamostrando meses (blocos)."""
    import numpy as np
    meses = list(vals_por_mes.values())
    if len(meses) < 3:
        return float("nan"), float("nan")
    soma = np.array([sum(v) for v in meses]); n = np.array([len(v) for v in meses])
    idx = rnd.integers(0, len(meses), size=(B, len(meses)))
    m = soma[idx].sum(1) / n[idx].sum(1)
    return tuple(np.percentile(m, [2.5, 97.5]))


def pct(x):
    return f"{100 * x:.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida"); ap.add_argument("--passo", type=int, default=5)
    a = ap.parse_args()
    import numpy as np
    rnd = np.random.default_rng(20261105)
    zips = sorted(glob.glob(os.path.join(a.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {a.zips}")
    fech, isin = ler_spot(zips)
    datas = sorted(set().union(*(set(f) for f in fech.values())))
    entradas = datas[::a.passo]
    print(f"{len(datas)} pregões, {len(entradas)} dias de entrada", flush=True)
    opc = ler_cadeias(zips, entradas, isin)
    ops = []
    for chave in sorted(opc):
        nome, dia = chave; linhas = opc.pop(chave); S = fech[nome].get(dia)
        if S:
            ops += montar_tudo(nome, dia, S, linhas)
    ultimo = datas[-1]
    ops = [o for o in ops if o["venc"] <= ultimo]
    print(f"{len(ops)} montagens com vencimento até {ultimo}", flush=True)
    vigiar = {(o.simbolo, op["venc"]) for op in ops for _, o in op["m"].pernas}
    px = ler_precos(zips, vigiar)

    linhas_res = []
    for op in ops:
        m, venc = op["m"], op["venc"]
        ST = fech_no(fech[op["ativo"]], venc)
        if ST is None:
            continue
        taxas = m.custo_taxas
        ks = [strike_final(o, px.get((o.simbolo, venc), {}), venc) for _, o in m.pernas]
        ajuste = any(abs(k - o.strike) > 1e-9 for (_, o), k in zip(m.pernas, ks))
        # pontos de equilíbrio deslocados pelo mesmo ajuste de strike (proventos): diferença média das pernas
        dk = sum(k - o.strike for (_, o), k in zip(m.pernas, ks)) / len(ks)
        eq = tuple(x + dk for x in m.pontos_equilibrio)
        segurar = no_vencimento(m, ST, ks) - taxas
        marcas, meio = [], []
        for d in sorted({d for _, o in m.pernas for d in px.get((o.simbolo, venc), {}) if op["data"] < d < venc}):
            precos = {o.simbolo: (px[(o.simbolo, venc)].get(d) or [None])[:2] for _, o in m.pernas}
            precos = {k: v for k, v in precos.items() if v and v[0] is not None}
            marcas.append({"d": d, "r": no_pior_lado(m, precos)}); meio.append({"d": d, "r": no_meio(m, precos)})
        rg = MT.regra_de_saida(m, marcas, venc)
        regra = (rg["r"] - taxas) if rg else segurar
        risco = m.perda_max
        # variantes da marcação: regra conferida no preço médio e saída no preço médio; ou conferida no médio e saída no
        # pior lado (compra/venda do fechamento) naquele dia
        rm = MT.regra_de_saida(m, meio, venc)
        regra_meio = (rm["r"] - taxas) if rm else segurar
        pior_dia = {mk["d"]: mk["r"] for mk in marcas}
        regra_meio_pior = ((pior_dia.get(rm["d"]) if pior_dia.get(rm["d"]) is not None else rm["r"]) - taxas) if rm else segurar
        abaixo = any(mk["r"] is not None and mk["r"] < -risco for mk in marcas)
        # cada parte da regra, conferida no preço médio: resultado com saída no médio e no pior lado daquele dia
        partes = {}
        if not op["tese"].startswith("aposta"):
            for nomev, mv in (("completa", m), ("sem limite", replace(m, stop=-1e18)), ("sem alvo", replace(m, alvo=None)),
                              ("só prazo", replace(m, alvo=None, stop=-1e18))):
                rv = MT.regra_de_saida(mv, meio, venc)
                if rv:
                    pr = pior_dia.get(rv["d"]); pr = pr if pr is not None else rv["r"]
                    # saída no pregão seguinte, pelo médio (a regra dispara num fechamento; sai-se no próximo): tira o
                    # efeito de um preço do fim do dia que não se repete
                    seg = next((mk["r"] for mk in meio if mk["d"] > rv["d"] and mk["r"] is not None), None)
                    prox = (seg - taxas) / risco if seg is not None else segurar / risco
                    # saída no médio, no pior lado, no meio do caminho entre os dois e no médio do pregão seguinte
                    partes[nomev] = ((rv["r"] - taxas) / risco, (pr - taxas) / risco, ((rv["r"] + pr) / 2 - taxas) / risco, prox)
                else:
                    partes[nomev] = (segurar / risco,) * 4
        linhas_res.append(dict(ativo=op["ativo"], data=op["data"], tese=op["tese"], prob=m.prob_implicita,
                               alem=alem_do_equilibrio(op["tese"], eq, ST), segurar=segurar / risco, ajuste=ajuste,
                               regra=regra / risco, saida=(rg["regra"] if rg else "vencimento"), d_saida=(rg["d"] if rg else venc),
                               custo=m.custo_total / risco, venc=venc,
                               prob_r=chance_com_juro(op["tese"], op["S"], m.pontos_equilibrio, m.pernas[0][1].dias, op["iv"]),
                               regra_meio=regra_meio / risco, saida_meio=(rm["regra"] if rm else "vencimento"),
                               regra_meio_pior=regra_meio_pior / risco, abaixo=abaixo, partes=partes))
    print(f"{len(linhas_res)} operações medidas; {sum(r['ajuste'] for r in linhas_res)} com strike ajustado pela B3 até o vencimento", flush=True)

    txt = ["# Replay do app no histórico", "",
           f"Arquivos: {os.path.basename(zips[0])} a {os.path.basename(zips[-1])}; entradas a cada {a.passo} pregões; "
           f"{len(linhas_res)} operações com vencimento até {ultimo}. IC 95%: bootstrap em blocos mensais ({B} reamostras).", ""]
    txt.append("Operações por estrutura: " + ", ".join(f"{NOME[t]} {sum(1 for r in linhas_res if r['tese'] == t)}" for t in TESES))

    # 1. calibração
    faixas = [(0, .1), (.1, .2), (.2, .3), (.3, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, .9), (.9, 1.01)]
    for titulo, de, ate in PERIODOS:
        R = [r for r in linhas_res if de <= r["data"][:4] <= ate]
        txt += ["", f"## 1. Chance implícita × o que aconteceu — {titulo} ({len(R)} operações)",
                "| chance na tela | operações | chance média % | terminou além do equilíbrio % | IC 95% | lucro depois das taxas % | IC 95% |",
                "|---|---|---|---|---|---|---|"]
        for lo, hi in faixas:
            F = [r for r in R if lo <= r["prob"] < hi]
            if len(F) < 20:
                continue
            pm = sum(r["prob"] for r in F) / len(F)
            al = defaultdict(list); lu = defaultdict(list)
            for r in F:
                al[r["data"][:7]].append(r["alem"]); lu[r["data"][:7]].append(r["segurar"] > 0)
            fa, fl = sum(r["alem"] for r in F) / len(F), sum(r["segurar"] > 0 for r in F) / len(F)
            ia, il = boot_media(al, rnd), boot_media(lu, rnd)
            txt.append(f"| {int(lo * 100)}–{min(int(hi * 100), 100)}% | {len(F)} | {pct(pm)} | {pct(fa)} | [{pct(ia[0])}, {pct(ia[1])}] | "
                       f"{pct(fl)} | [{pct(il[0])}, {pct(il[1])}] |")
    txt += ["", "### Calibração por estrutura (tudo): chance média % × terminou além do equilíbrio % × lucro depois das taxas %",
            "| estrutura | operações | chance média | além do equilíbrio | lucro | custo médio (% do risco) |", "|---|---|---|---|---|---|"]
    for t in TESES:
        F = [r for r in linhas_res if r["tese"] == t]
        if F:
            txt.append(f"| {NOME[t]} | {len(F)} | {pct(sum(r['prob'] for r in F) / len(F))} | {pct(sum(r['alem'] for r in F) / len(F))} | "
                       f"{pct(sum(r['segurar'] > 0 for r in F) / len(F))} | {pct(sum(r['custo'] for r in F) / len(F))} |")

    # 2. regra de saída × segurar
    for titulo, de, ate in PERIODOS:
        txt += ["", f"## 2. Regra de saída × segurar até o vencimento — {titulo}",
                "| estrutura | operações | lucro % (regra / segurar) | resultado médio, % do risco (regra / segurar) | diferença (pp) | IC 95% | perda ≥ 90% do risco (regra / segurar) | pior 5% (regra / segurar) | saídas: alvo · limite · prazo · venc. |",
                "|---|---|---|---|---|---|---|---|---|"]
        for t in ("alta", "baixa", "forte", "alta_com_caixa"):
            F = [r for r in linhas_res if r["tese"] == t and de <= r["data"][:4] <= ate]
            if len(F) < 20:
                continue
            n = len(F); dif = defaultdict(list)
            for r in F:
                dif[r["data"][:7]].append(r["regra"] - r["segurar"])
            md = sum(r["regra"] - r["segurar"] for r in F) / n; ic = boot_media(dif, rnd)
            q = lambda k: sorted(r[k] for r in F)[max(0, int(0.05 * n) - 1)]
            sa = defaultdict(int)
            for r in F:
                sa[r["saida"]] += 1
            txt.append(f"| {NOME[t]} | {n} | {pct(sum(r['regra'] > 0 for r in F) / n)} / {pct(sum(r['segurar'] > 0 for r in F) / n)} | "
                       f"{100 * sum(r['regra'] for r in F) / n:+.1f} / {100 * sum(r['segurar'] for r in F) / n:+.1f} | {100 * md:+.1f} | "
                       f"[{100 * ic[0]:+.1f}, {100 * ic[1]:+.1f}] | {pct(sum(r['regra'] <= -0.9 for r in F) / n)} / {pct(sum(r['segurar'] <= -0.9 for r in F) / n)} | "
                       f"{100 * q('regra'):+.0f} / {100 * q('segurar'):+.0f} | {sa['alvo']} · {sa['limite']} · {sa['prazo']} · {sa['vencimento']} |")
        F = [r for r in linhas_res if r["tese"].startswith("aposta") and de <= r["data"][:4] <= ate]
        if F:
            n = len(F)
            txt.append(f"| Compra simples (call ou put; sem regra no app) | {n} | — / {pct(sum(r['segurar'] > 0 for r in F) / n)} | "
                       f"— / {100 * sum(r['segurar'] for r in F) / n:+.1f} | — | — | — / {pct(sum(r['segurar'] <= -0.9 for r in F) / n)} | — | — |")

    # 3. uma por vez
    txt += ["", "## 3. Uma operação por vez (segurando até o vencimento), por papel — tudo",
            "| estrutura | papel | operações | lucro % | resultado somado (× risco) | maior sequência de perdas | maior queda acumulada (× risco) |",
            "|---|---|---|---|---|---|---|"]
    for t in TESES:
        chave, saida = "segurar", "venc"
        for nome in ATIVOS:
            F = sorted((r for r in linhas_res if r["tese"] == t and r["ativo"] == nome), key=lambda r: r["data"])
            seq, livre = [], ""
            for r in F:
                if r["data"] > livre:
                    seq.append(r); livre = r[saida]
            if len(seq) < 10:
                continue
            maior = cur = 0; acum = pico = queda = 0.0
            for r in seq:
                cur = cur + 1 if r[chave] < 0 else 0; maior = max(maior, cur)
                acum += r[chave]; pico = max(pico, acum); queda = max(queda, pico - acum)
            txt.append(f"| {NOME[t]} | {nome} | {len(seq)} | {pct(sum(r[chave] > 0 for r in seq) / len(seq))} | {acum:+.1f} | {maior} | {queda:.1f} |")
    # 4. diagnóstico: chance com o juro e a marcação no preço médio
    txt += ["", "## 4a. Chance com o juro na conta (r = 11% a.a., o mesmo da volatilidade implícita) — tudo",
            "| estrutura | operações | chance da tela | chance com juro | terminou além do equilíbrio |", "|---|---|---|---|---|"]
    for t in TESES:
        F = [r for r in linhas_res if r["tese"] == t]
        if F:
            txt.append(f"| {NOME[t]} | {len(F)} | {pct(sum(r['prob'] for r in F) / len(F))} | {pct(sum(r['prob_r'] for r in F) / len(F))} | "
                       f"{pct(sum(r['alem'] for r in F) / len(F))} |")
    txt += ["", "| chance com juro | operações | chance média % | terminou além do equilíbrio % | IC 95% |", "|---|---|---|---|---|"]
    for lo, hi in faixas:
        F = [r for r in linhas_res if lo <= r["prob_r"] < hi]
        if len(F) < 20:
            continue
        al = defaultdict(list)
        for r in F:
            al[r["data"][:7]].append(r["alem"])
        ia = boot_media(al, rnd)
        txt.append(f"| {int(lo * 100)}–{min(int(hi * 100), 100)}% | {len(F)} | {pct(sum(r['prob_r'] for r in F) / len(F))} | "
                   f"{pct(sum(r['alem'] for r in F) / len(F))} | [{pct(ia[0])}, {pct(ia[1])}] |")
    txt += ["", "## 4b. Marcação diária: pior lado do fechamento (como o app hoje) × preço médio — tudo",
            "| estrutura | operações | alguma marcação pior que o risco máximo % | lucro % (pior / médio / médio→pior) | resultado médio % do risco (pior / médio / médio→pior / segurar) | pior 5% (pior / médio) | saídas no limite % (pior / médio) |",
            "|---|---|---|---|---|---|---|"]
    for t in ("alta", "baixa", "forte", "alta_com_caixa"):
        F = [r for r in linhas_res if r["tese"] == t]
        if not F:
            continue
        n = len(F); q = lambda k: sorted(r[k] for r in F)[max(0, int(0.05 * n) - 1)]
        med = lambda k: 100 * sum(r[k] for r in F) / n
        txt.append(f"| {NOME[t]} | {n} | {pct(sum(r['abaixo'] for r in F) / n)} | {pct(sum(r['regra'] > 0 for r in F) / n)} / "
                   f"{pct(sum(r['regra_meio'] > 0 for r in F) / n)} / {pct(sum(r['regra_meio_pior'] > 0 for r in F) / n)} | "
                   f"{med('regra'):+.1f} / {med('regra_meio'):+.1f} / {med('regra_meio_pior'):+.1f} / {med('segurar'):+.1f} | "
                   f"{100 * q('regra'):+.0f} / {100 * q('regra_meio'):+.0f} | {pct(sum(r['saida'] == 'limite' for r in F) / n)} / "
                   f"{pct(sum(r['saida_meio'] == 'limite' for r in F) / n)} |")
    txt += ["", "## 5. Cada parte da regra de saída, conferida no preço médio — tudo",
            "| estrutura | regra | lucro % (saída no médio) | resultado médio % do risco (saída no médio / no pior lado) | pior 5% (médio) |",
            "|---|---|---|---|---|"]
    for t in ("alta", "baixa", "forte", "alta_com_caixa"):
        F = [r for r in linhas_res if r["tese"] == t]
        if not F:
            continue
        n = len(F)
        for nomev in ("completa", "sem limite", "sem alvo", "só prazo"):
            vm = sorted(r["partes"][nomev][0] for r in F)
            txt.append(f"| {NOME[t]} | {nomev} | {pct(sum(x > 0 for x in vm) / n)} | {100 * sum(vm) / n:+.1f} / "
                       f"{100 * sum(r['partes'][nomev][1] for r in F) / n:+.1f} | {100 * vm[max(0, int(0.05 * n) - 1)]:+.0f} |")
        vs = sorted(r["segurar"] for r in F)
        txt.append(f"| {NOME[t]} | segurar até o vencimento | {pct(sum(x > 0 for x in vs) / n)} | {100 * sum(vs) / n:+.1f} | {100 * vs[max(0, int(0.05 * n) - 1)]:+.0f} |")
    # 6. o alvo, por período: alvo + prazo (a regra das travas sem limite) × só prazo × segurar, com três execuções
    txt += ["", "## 6. Alvo (50% do ganho máximo) por período: alvo + prazo × só prazo × segurar até o vencimento",
            "Resultado médio em % do risco, saída no preço médio / no meio do caminho / no pior lado do fechamento / no médio do "
            "pregão seguinte. Diferenças = (alvo + prazo) − segurar, com IC 95%.", "",
            "| estrutura | período | operações | alvo + prazo | só prazo | segurar | diferença (meio do caminho) | IC 95% | diferença (pregão seguinte) | IC 95% |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for t in ("alta", "baixa", "forte"):
        for titulo, de, ate in PERIODOS:
            F = [r for r in linhas_res if r["tese"] == t and de <= r["data"][:4] <= ate]
            if len(F) < 20:
                continue
            n = len(F); med = lambda nomev, i: 100 * sum(r["partes"][nomev][i] for r in F) / n
            dif, dif2 = defaultdict(list), defaultdict(list)
            for r in F:
                dif[r["data"][:7]].append(r["partes"]["sem limite"][2] - r["segurar"])
                dif2[r["data"][:7]].append(r["partes"]["sem limite"][3] - r["segurar"])
            ic, ic2 = boot_media(dif, rnd), boot_media(dif2, rnd); seg = 100 * sum(r["segurar"] for r in F) / n
            v4 = lambda nomev: " / ".join(f"{med(nomev, i):+.1f}" for i in (0, 2, 1, 3))
            txt.append(f"| {NOME[t]} | {titulo} | {n} | {v4('sem limite')} | {v4('só prazo')} | {seg:+.1f} | "
                       f"{med('sem limite', 2) - seg:+.1f} | [{100 * ic[0]:+.1f}, {100 * ic[1]:+.1f}] | "
                       f"{med('sem limite', 3) - seg:+.1f} | [{100 * ic2[0]:+.1f}, {100 * ic2[1]:+.1f}] |")
    txt += ["", "Limitações: observações sobrepostas (entradas a cada 5 pregões, prazos de ~45 dias); preço de fechamento "
            "(melhor oferta no fim do dia), não o preço que se consegue no meio do pregão; sem corretagem; no vencimento vale o strike do último pregão da série (a B3 ajusta por proventos e "
            "desdobramentos); se o código da série mudar no ajuste, fica o strike da entrada; risco aceito e caixa grandes (o limite de perda da put vendida fica em 70% do risco, como no app)."]
    saida = "\n".join(txt)
    print(saida)
    if a.saida:
        with open(a.saida, "w", encoding="utf-8") as f:
            f.write(saida + "\n")


if __name__ == "__main__":
    main()
