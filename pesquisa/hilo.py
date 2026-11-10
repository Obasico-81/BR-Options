#!/usr/bin/env python3
"""Setup HiLo + candle de força + projeção de Fibonacci (live "O Poder das Opções", B.Trader, 09/11/2026), medido nos
COTAHIST anuais da B3, nos papéis do app.

O setup, como mostrado no vídeo:
  - gráfico diário com HiLo Activator de N períodos (no vídeo, 3): a tendência vira para alta quando o fechamento passa
    acima da média das N máximas anteriores; para baixa, quando passa abaixo da média das N mínimas anteriores;
  - no dia da virada, o candle é "de força" (barra cheia): corpo (abertura→fechamento) de pelo menos X% do tamanho
    (máxima→mínima), na direção da virada;
  - Fibonacci: o tamanho do candle projetado a partir da máxima (alta) ou da mínima (baixa): 61,8%, 100% e 161,8%;
  - operação: compra a call (alta) ou a put (baixa) do vencimento com pelo menos 15 dias e strike mais perto do nível de
    161,8% (o alvo), no fechamento do dia do sinal.

Medidas (fase de EXPLORAÇÃO: sinais de 2015 a 2021; 2022 em diante fica guardado para a confirmação):
  1. Toque: em quantos % dos sinais a máxima (mínima, na baixa) toca cada nível em 5, 10 e 20 pregões e até o HiLo virar
     de volta; comparado com o mesmo toque, à mesma distância percentual do fechamento, partindo de qualquer dia
     ("dia qualquer"), e com viradas sem candle de força e candles de força sem virada.
  2. A operação com os preços reais das opções: entrada pela oferta de venda no fechamento do sinal; saída no dia em que
     a ação toca o alvo (otimista: máxima da opção no dia, como no vídeo; realista: oferta de compra no fechamento), no
     20º pregão ou no vencimento (valor intrínseco). Comparada com a mesma compra, à mesma distância do alvo, em dias sem
     sinal (a cada 5 pregões). Variante do vídeo: em vez do 20º pregão, sai quando o HiLo vira de volta.
IC 95%: bootstrap em blocos mensais. Preços ajustados por desdobramentos/grupamentos para o HiLo e os toques; as opções,
com o preço e o strike do dia (sem ajuste), como foram negociadas.

Uso: python pesquisa/hilo.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida resultado.txt] [--fase explorar|confirmar]
"""
import argparse, glob, math, os, sys
from bisect import bisect_left
from collections import defaultdict
from datetime import date, timedelta

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
from atualizar_dados import ATIVOS, campo, preco, iso, linhas_do_zip   # noqa: E402

NS = (3, 5, 8, 13)               # períodos do HiLo (o do vídeo é 3)
CHEIAS = (0.6, 0.7, 0.8)         # corpo mínimo do candle de força, em fração do tamanho
NIVEIS = (0.618, 1.0, 1.618)     # projeções de Fibonacci a partir da máxima (mínima)
HS = (5, 10, 20)                 # pregões
PRINCIPAL = (3, 0.7)             # combinação principal (HiLo 3 do vídeo; barra cheia 70%)
MIN_DIAS, PRAZO_SAIDA, PASSO_BASE = 15, 20, 5
SPLITS = (2, 3, 4, 5, 8, 10)
B = 2000
FASES = {"explorar": ("2015-01-01", "2021-12-31"), "confirmar": ("2022-01-01", "2099-12-31")}


# ---------- leitura ----------
def ler_spot(zips):
    papeis = {pap: nome for nome, (_, pap) in ATIVOS.items()}
    s, isin = {n: {} for n in ATIVOS}, {n: set() for n in ATIVOS}
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) < 242 or ln[0:2] != "01" or ln[24:27] != "010":
                continue
            nome = papeis.get(campo(ln, "codneg"))
            if not nome:
                continue
            o = preco(ln[56:69].strip())
            h, lo, c = preco(campo(ln, "premax")), preco(campo(ln, "premin")), preco(campo(ln, "preult"))
            if h >= max(o, c) and min(o, c) >= lo > 0:
                s[nome][iso(campo(ln, "data"))] = (o, h, lo, c)
                isin[nome].add(campo(ln, "codisi"))
        print(f"{os.path.basename(z)}: papéis", flush=True)
    return s, isin


def ler_cadeias(zips, isin, entradas):
    """cad[(nome, data)] = opções (tipo, strike, compra, venda, símbolo, vencimento ISO) nos dias de entrada, com strike
    a até 40% do preço. entradas: {(nome, data ISO): fechamento sem ajuste}."""
    prefixos = {pref: nome for nome, (pref, _) in ATIVOS.items()}
    alvo = defaultdict(dict)
    for (nome, d), S in entradas.items():
        alvo[d.replace("-", "")][nome] = S
    cad = defaultdict(list)
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) < 242 or ln[0:2] != "01":
                continue
            tp = ln[24:27]
            if tp != "070" and tp != "080":
                continue
            dt = ln[2:10]
            if dt not in alvo:
                continue
            cod = campo(ln, "codneg"); nome = prefixos.get(cod[:4])
            if not nome or nome not in alvo[dt] or campo(ln, "codisi") not in isin[nome]:
                continue
            k, b, a = preco(campo(ln, "preexe")), preco(campo(ln, "preofc")), preco(campo(ln, "preofv"))
            if k > 0 and b > 0 and a >= b and abs(k / alvo[dt][nome] - 1) <= 0.40:
                cad[(nome, iso(dt))].append(("C" if tp == "070" else "P", k, b, a, cod, iso(ln[202:210])))
        print(f"{os.path.basename(z)}: cadeias", flush=True)
    return cad


def ler_series(zips, vigiar):
    """px[(símbolo, venc)][data] = (máxima, fechamento, compra, venda, strike)."""
    simb = {s for s, _ in vigiar}
    px = defaultdict(dict)
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) < 242 or ln[0:2] != "01" or ln[24:27] not in ("070", "080"):
                continue
            cod = campo(ln, "codneg")
            if cod not in simb:
                continue
            ch = (cod, iso(ln[202:210]))
            if ch in vigiar:
                px[ch][iso(campo(ln, "data"))] = (preco(campo(ln, "premax")), preco(campo(ln, "preult")),
                                                  preco(campo(ln, "preofc")), preco(campo(ln, "preofv")), preco(campo(ln, "preexe")))
        print(f"{os.path.basename(z)}: séries", flush=True)
    return px


# ---------- série do papel ----------
def preparar(s):
    import numpy as np
    ds = sorted(s)
    c = [s[d][3] for d in ds]
    fat, acum = [1.0] * len(ds), 1.0
    for i in range(len(ds) - 1, 0, -1):
        fat[i] = acum
        r = c[i] / c[i - 1]
        for k in SPLITS:
            if abs(r * k - 1) < 0.06:
                acum /= k; break
            if abs(r / k - 1) < 0.06:
                acum *= k; break
    fat[0] = acum
    f = np.array(fat); arr = np.array([s[d] for d in ds], dtype=float)
    return dict(ds=ds, ix={d: i for i, d in enumerate(ds)}, O=arr[:, 0] * f, H=arr[:, 1] * f, L=arr[:, 2] * f, C=arr[:, 3] * f,
                raw=arr, fat=f)


def hilo(a, n):
    """estado[t]: +1 alta, −1 baixa, 0 indefinido. Alta quando o fechamento passa da média das n máximas anteriores."""
    import numpy as np
    H, L, C = a["H"], a["L"], a["C"]; m = len(C)
    cs = lambda x: np.concatenate([[0.0], np.cumsum(x)])
    ch, cl = cs(H), cs(L)
    st = np.zeros(m, dtype=int)
    for t in range(n, m):
        mh = (ch[t] - ch[t - n]) / n; ml = (cl[t] - cl[t - n]) / n          # médias das n barras anteriores (t−n..t−1)
        st[t] = 1 if C[t] > mh else -1 if C[t] < ml else st[t - 1]
    return st


def niveis(a, t, d):
    """Distâncias dos níveis de Fibonacci ao fechamento do sinal (fração; positiva na alta, negativa na baixa)."""
    H, L, C = a["H"][t], a["L"][t], a["C"][t]; tam = H - L
    return [((H + k * tam) if d > 0 else (L - k * tam)) / C - 1 for k in NIVEIS]


def ic_media(meses, vals, rnd):
    import numpy as np
    if len(vals) < 5:
        return float("nan"), float("nan")
    ms = sorted(set(meses)); ix = {m: i for i, m in enumerate(ms)}
    soma, cont = np.zeros(len(ms)), np.zeros(len(ms))
    for m, v in zip(meses, vals):
        soma[ix[m]] += v; cont[ix[m]] += 1
    idx = rnd.integers(0, len(ms), size=(B, len(ms)))
    with np.errstate(invalid="ignore", divide="ignore"):
        x = soma[idx].sum(1) / cont[idx].sum(1)
    x = x[np.isfinite(x)]
    return tuple(np.percentile(x, [2.5, 97.5]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida"); ap.add_argument("--fase", default="explorar", choices=FASES)
    arg = ap.parse_args()
    import numpy as np
    rnd = np.random.default_rng(20261110)
    de, ate = FASES[arg.fase]
    zips = sorted(glob.glob(os.path.join(arg.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {arg.zips}")
    s, isin = ler_spot(zips)
    A = {n: preparar(s[n]) for n in ATIVOS if len(s[n]) > 300}
    pct = lambda x: f"{100 * x:.1f}%"
    txt = [f"# Setup HiLo + candle de força + Fibonacci — fase: {arg.fase} (sinais de {de[:4]} a {ate[:4] if ate < '2099' else 'hoje'})", "",
           f"Papéis: {', '.join(A)}. HiLo {NS}, candle de força com corpo ≥ {', '.join(f'{int(c * 100)}%' for c in CHEIAS)} do tamanho; "
           f"níveis de 61,8%, 100% e 161,8% do tamanho a partir da máxima (mínima). Principal: HiLo {PRINCIPAL[0]}, corpo ≥ {int(PRINCIPAL[1] * 100)}%. "
           f"IC 95% por bootstrap em blocos mensais."]

    # ---------- sinais e toques ----------
    fwd = {}   # (nome, h) -> (máximo à frente / fechamento, mínimo à frente / fechamento)
    for nome, a in A.items():
        H, L, C = a["H"], a["L"], a["C"]; m = len(C)
        for h in HS:
            mx = np.full(m, np.nan); mn = np.full(m, np.nan)
            for t in range(m - h):
                mx[t] = H[t + 1:t + h + 1].max() / C[t]; mn[t] = L[t + 1:t + h + 1].min() / C[t]
            fwd[(nome, h)] = (mx, mn)
    dias_periodo = {nome: [t for t, d in enumerate(a["ds"]) if de <= d <= ate] for nome, a in A.items()}
    base_ord = {}   # (nome, h, dir) -> razões ordenadas de todos os dias do período (para o "dia qualquer")
    for nome, a in A.items():
        for h in HS:
            mx, mn = fwd[(nome, h)]; ts = [t for t in dias_periodo[nome] if np.isfinite(mx[t])]
            base_ord[(nome, h, 1)] = np.sort(mx[ts]); base_ord[(nome, h, -1)] = np.sort(mn[ts])

    def p_base(nome, h, d, dist):
        x = base_ord[(nome, h, d)]
        if not len(x):
            return float("nan")
        return (len(x) - bisect_left(x, 1 + dist)) / len(x) if d > 0 else bisect_left(x, 1 + dist + 1e-12) / len(x)

    estados = {(nome, n): hilo(a, n) for nome, a in A.items() for n in NS}
    sinais = defaultdict(list)   # (n, cheia, tipo) -> [(nome, t, dir)]; tipo: setup | virada_sem_forca | forca_sem_virada
    for nome, a in A.items():
        O, H, L, C = a["O"], a["H"], a["L"], a["C"]
        corpo = np.abs(C - O) / np.where(H > L, H - L, np.nan)
        for n in NS:
            st = estados[(nome, n)]
            for t in dias_periodo[nome]:
                if t < n + 1 or t + 1 >= len(C):
                    continue
                d = 1 if C[t] > O[t] else -1 if C[t] < O[t] else 0
                virou = st[t] != 0 and st[t - 1] != 0 and st[t] != st[t - 1]
                for ch in CHEIAS:
                    forca = d != 0 and corpo[t] >= ch
                    if virou and forca and d == st[t]:
                        sinais[(n, ch, "setup")].append((nome, t, st[t]))
                    elif virou and not (forca and d == st[t]):
                        sinais[(n, ch, "virada_sem_forca")].append((nome, t, st[t]))
                    elif forca and not virou:
                        sinais[(n, ch, "forca_sem_virada")].append((nome, t, d))

    def toques(lista, h, nivel):
        """[(tocou 0/1, prob. do dia qualquer, mês)] para um horizonte (h em pregões, ou 'virar')."""
        out = []
        for nome, t, d in lista:
            a = A[nome]; dist = niveis(a, t, d)[nivel]
            if h == "virar":
                st = estados[(nome, PRINCIPAL[0])]; u = t + 1
                while u < len(a["C"]) and st[u] == d and u - t < 60:
                    u += 1
                if u >= len(a["C"]):
                    continue
                seg = a["H"][t + 1:u + 1] if d > 0 else a["L"][t + 1:u + 1]
                ok = (seg.max() / a["C"][t] >= 1 + dist) if d > 0 else (seg.min() / a["C"][t] <= 1 + dist)
                out.append((float(ok), float("nan"), a["ds"][t][:7]))
            else:
                mx, mn = fwd[(nome, h)]
                if not np.isfinite(mx[t]):
                    continue
                ok = mx[t] >= 1 + dist if d > 0 else mn[t] <= 1 + dist
                out.append((float(ok), p_base(nome, h, d, dist), a["ds"][t][:7]))
        return out

    n0, c0 = PRINCIPAL
    txt += ["", "## 1. Toque nos níveis de Fibonacci — combinação principal (HiLo 3, corpo ≥ 70%)", ""]
    for d, rot in ((1, "alta (call)"), (-1, "baixa (put)")):
        lst = [x for x in sinais[(n0, c0, "setup")] if x[2] == d]
        dist = np.array([niveis(A[nm], t, d) for nm, t, _ in lst]) if lst else np.zeros((0, 3))
        txt += [f"### Sinais de {rot}: {len(lst)}" + (f" · distância mediana do fechamento: 61,8% → {pct(abs(np.median(dist[:, 0])))}, "
                f"100% → {pct(abs(np.median(dist[:, 1])))}, 161,8% → {pct(abs(np.median(dist[:, 2])))}" if len(lst) else ""),
                "| nível | prazo | tocou (setup) | dia qualquer, mesma distância | diferença [IC 95%] |", "|---|---|---|---|---|"]
        for iv, nv in enumerate(NIVEIS):
            for h in HS:
                r = toques(lst, h, iv)
                if not r:
                    continue
                tc = np.mean([x[0] for x in r]); pb = np.nanmean([x[1] for x in r])
                lo, hi = ic_media([x[2] for x in r], [x[0] - x[1] for x in r], rnd)
                txt.append(f"| {nv * 100:.1f}% | {h} pregões | {pct(tc)} | {pct(pb)} | {100 * (tc - pb):+.1f} pp [{100 * lo:+.1f}, {100 * hi:+.1f}] |")
            r = toques(lst, "virar", iv)
            if r:
                txt.append(f"| {nv * 100:.1f}% | até o HiLo virar de volta | {pct(np.mean([x[0] for x in r]))} | — | — |")
        txt.append("")

    txt += ["## 2. Toque em 161,8% em 10 pregões, por combinação (setup × viradas sem força × força sem virada × dia qualquer)", "",
            "| HiLo | corpo ≥ | direção | setup: sinais / tocou | dia qualquer | virada sem força | força sem virada |", "|---|---|---|---|---|---|---|"]
    for n in NS:
        for ch in CHEIAS:
            for d, rot in ((1, "alta"), (-1, "baixa")):
                cel = []
                for tipo in ("setup", "virada_sem_forca", "forca_sem_virada"):
                    lst = [x for x in sinais[(n, ch, tipo)] if x[2] == d]
                    r = toques(lst, 10, 2)
                    cel.append((len(r), np.mean([x[0] for x in r]) if r else float("nan"), np.nanmean([x[1] for x in r]) if r else float("nan")))
                txt.append(f"| {n} | {int(ch * 100)}% | {rot} | {cel[0][0]} / {pct(cel[0][1])} | {pct(cel[0][2])} | {pct(cel[1][1])} | {pct(cel[2][1])} |")

    # ---------- a operação com opções ----------
    entradas = {}
    trades = []   # (combo, nome, t, dir, alvo_dist, base?)
    for n in NS:
        for ch in CHEIAS:
            for nome, t, d in sinais[(n, ch, "setup")]:
                trades.append(((n, ch), nome, t, d, niveis(A[nome], t, d)[2], False)); entradas[(nome, A[nome]["ds"][t])] = A[nome]["raw"][t][3]
    for d in (1, -1):   # dia qualquer: a cada 5 pregões, à distância mediana do alvo dos sinais principais
        lst = [x for x in sinais[(n0, c0, "setup")] if x[2] == d]
        if not lst:
            continue
        dmed = float(np.median([niveis(A[nm], t, d)[2] for nm, t, _ in lst]))
        sinal_dias = {(nm, t) for nm, t, _ in lst}
        for nome, a in A.items():
            for t in dias_periodo[nome][::PASSO_BASE]:
                if (nome, t) in sinal_dias or t + 1 >= len(a["C"]):
                    continue
                trades.append(("base", nome, t, d, dmed, True)); entradas[(nome, a["ds"][t])] = a["raw"][t][3]
    print(f"{len(trades)} operações a montar em {len(entradas)} dias×papel", flush=True)
    cad = ler_cadeias(zips, isin, entradas)

    escolhas = []
    for combo, nome, t, d, dist, base in trades:
        a = A[nome]; dia = a["ds"][t]; Sraw = a["raw"][t][3]; alvo_raw = Sraw * (1 + dist)
        lim = (date.fromisoformat(dia) + timedelta(days=MIN_DIAS)).isoformat()
        ops = [o for o in cad.get((nome, dia), []) if o[0] == ("C" if d > 0 else "P") and o[5] >= lim]
        if not ops:
            escolhas.append((combo, nome, t, d, dist, base, None)); continue
        venc = min(o[5] for o in ops)
        o = min((o for o in ops if o[5] == venc), key=lambda o: abs(o[1] - alvo_raw))
        escolhas.append((combo, nome, t, d, dist, base, o))
    vigiar = {(o[4], o[5]) for *_, o in escolhas if o}
    px = ler_series(zips, vigiar)

    def resultado(nome, t, d, dist, o, regra):
        """(retorno realista, retorno otimista, tocou o alvo?) ou None (sem dados para fechar a conta)."""
        a = A[nome]; ent = o[3]; serie = px.get((o[4], o[5]), {}); venc = o[5]; st = estados[(nome, n0)]
        if not ent > 0:
            return None
        alvo_adj = a["C"][t] * (1 + dist)
        u, motivo = t + 1, None
        while u < len(a["ds"]) and a["ds"][u] <= venc:
            if (a["H"][u] >= alvo_adj) if d > 0 else (a["L"][u] <= alvo_adj):
                motivo = "alvo"; break
            if (regra == "prazo" and u - t >= PRAZO_SAIDA) or (regra == "hilo" and st[u] == -d):
                motivo = "regra"; break
            u += 1
        if motivo is None:   # chegou ao vencimento sem tocar: valor intrínseco no último pregão até o vencimento
            ul = u - 1
            if ul <= t or a["ds"][ul] < (date.fromisoformat(venc) - timedelta(days=4)).isoformat():
                return None
            ks = [serie[x][4] for x in sorted(serie) if x <= venc and serie[x][4] > 0]
            k = ks[-1] if ks else o[1]; Sv = a["raw"][ul][3]
            v = max(0.0, Sv - k) if d > 0 else max(0.0, k - Sv)
            return v / ent - 1, v / ent - 1, False
        du = a["ds"][u]; p = serie.get(du)
        if not p:   # a opção não negociou no dia: próximo registro em até 5 dias
            prox = [x for x in sorted(serie) if du < x <= (date.fromisoformat(du) + timedelta(days=5)).isoformat()]
            if not prox:
                return None
            p = serie[prox[0]]
        sai = p[2] if p[2] > 0 else p[1]
        return sai / ent - 1, ((p[0] if p[0] > 0 else sai) if motivo == "alvo" else sai) / ent - 1, motivo == "alvo"

    txt += ["", "## 3. A operação com opções (preços reais): compra no fechamento do sinal, strike mais perto do alvo de 161,8%",
            "", f"Entrada pela oferta de venda. Saída: alvo tocado pela ação (realista: oferta de compra no fechamento; otimista: "
            f"máxima da opção no dia), ou {PRAZO_SAIDA}º pregão, ou vencimento (valor intrínseco). \"Dia qualquer\": a mesma compra, "
            f"à distância mediana do alvo dos sinais principais, a cada {PASSO_BASE} pregões sem sinal. Retorno sobre o prêmio pago.", "",
            "| combinação | direção | operações (sem opção) | com lucro (realista) | retorno médio realista [IC 95%] | mediana | retorno médio otimista | tocou o alvo |",
            "|---|---|---|---|---|---|---|---|"]

    def linha(rot, d, sel, regra):
        res, sem, meses = [], 0, []
        for combo, nome, t, dd, dist, base, o in sel:
            if dd != d:
                continue
            if o is None:
                sem += 1; continue
            r = resultado(nome, t, dd, dist, o, regra)
            if r:
                res.append(r); meses.append(A[nome]["ds"][t][:7])
        if not res:
            return f"| {rot} | {'alta' if d > 0 else 'baixa'} | 0 ({sem}) | — | — | — | — | — |"
        re = np.array([x[0] for x in res]); ot = np.array([x[1] for x in res]); tc = np.mean([x[2] for x in res])
        lo, hi = ic_media(meses, list(re), rnd)
        return (f"| {rot} | {'alta' if d > 0 else 'baixa'} | {len(res)} ({sem}) | {pct((re > 0).mean())} | {100 * re.mean():+.0f}% "
                f"[{100 * lo:+.0f}%, {100 * hi:+.0f}%] | {100 * np.median(re):+.0f}% | {100 * ot.mean():+.0f}% | {pct(tc)} |")

    for d in (1, -1):
        txt.append(linha("dia qualquer", d, [e for e in escolhas if e[0] == "base"], "prazo"))
        for n in NS:
            for ch in CHEIAS:
                txt.append(linha(f"HiLo {n}, corpo ≥ {int(ch * 100)}%", d, [e for e in escolhas if e[0] == (n, ch)], "prazo"))
        txt.append(linha(f"HiLo {n0}, corpo ≥ {int(c0 * 100)}% · saída quando o HiLo vira (vídeo)", d, [e for e in escolhas if e[0] == (n0, c0)], "hilo"))
    txt += ["", "Limitações: só pregões completos (o sinal é conferido no fechamento; na prática a decisão é um pouco antes); "
            "a saída no alvo usa o preço de fechamento da opção no dia do toque (realista) ou a máxima do dia (otimista, pode não "
            "ter sido possível); opções sem oferta no dia do sinal ficam de fora (coluna \"sem opção\"); muitas combinações na "
            "exploração: escolher a melhor e conferir só uma vez na fase de confirmação."]
    saida = "\n".join(txt)
    print(saida)
    if arg.saida:
        with open(arg.saida, "w", encoding="utf-8") as f:
            f.write(saida + "\n")


if __name__ == "__main__":
    main()
