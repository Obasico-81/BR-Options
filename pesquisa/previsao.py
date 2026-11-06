#!/usr/bin/env python3
"""Três testes de previsão com os COTAHIST anuais da B3 (2015 até hoje), nos 11 papéis do app. As hipóteses, os
modelos, os parâmetros e as medidas foram fixados antes de rodar; nada aqui escolhe parâmetro pelo resultado.

1. VOLATILIDADE — para os 20 pregões seguintes, qual previsão erra menos a oscilação que de fato aconteceu?
   Previsões, todas só com informação até o dia: volatilidade implícita da cadeia (a mesma conta do app: mediana das
   4 calls mais perto do dinheiro com 25 a 70 dias), volatilidade dos últimos 20 e 60 pregões, EWMA (lambda 0,94),
   HAR (regressão da variância futura na variância de 1, 5 e 22 pregões pela máxima/mínima e na de 22 pregões pelo
   fechamento; refeita todo mês só com o passado, todos os papéis juntos) e a média geométrica implícita × HAR.
   Medidas: QLIKE (perda padrão para previsão de variância; menor é melhor), erro médio em pontos de volatilidade
   anual, viés, e a cobertura da faixa de ±1 e ±2 desvios (a faixa do gráfico de payoff): o preço 20 pregões depois
   ficou dentro dela em quantos % dos casos (o esperado é 68,3% e 95,4%).

2. DIREÇÃO — um modelo de aprendizado de máquina acerta se o papel sobe ou cai em 5 e 20 pregões?
   Gradient boosting (HistGradientBoosting, parâmetros fixos) e regressão logística, com retornos de 1 a 120 pregões,
   distância às médias de 21 e 50, inclinação da média de 50, ADX e IFR (as contas do app), volatilidade, volume e o
   BOVA11 como mercado. Janela que anda: treina com os anos anteriores (só linhas cujo resultado já era conhecido) e
   testa o ano seguinte, de 2017 a 2026. Medidas: acerto contra "sempre alta", AUC (0,5 = moeda) e a diferença de
   retorno médio entre os dias em que o modelo disse alta e os em que disse queda.

3. CAUDAS — a "chance" das opções longe do dinheiro está calibrada?
   Para cada opção fora do dinheiro (15 a 70 dias), a chance de o papel terminar além do strike no vencimento por:
   app (lognormal com a implícita do dinheiro, prob_acima do montador), sorriso (lognormal com a implícita da própria
   opção) e caudas históricas (forma dos retornos passados de todos os papéis, padronizados pela volatilidade de 60
   pregões, até o fim do ano anterior; escala pela implícita do dinheiro). Medidas: chance prevista × frequência real
   por distância do strike (em desvios), e Brier (erro quadrático da probabilidade; menor é melhor).

IC 95%: bootstrap em blocos mensais (meses reamostrados, todos os papéis juntos). Preços do lote padrão; desdobramentos
e grupamentos ajustados para trás nos testes 1 e 2; no 3, preço sem ajuste e o strike do último pregão da série
(ajustado pela B3 por proventos e eventos).

Uso: python pesquisa/previsao.py --zips PASTA_COM_COTAHIST_Aaaaa.ZIP [--saida resultado.txt] [--passo 5]
"""
import argparse, glob, math, os, sys
from bisect import bisect_right
from collections import defaultdict
from datetime import date, timedelta
from statistics import median

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
from atualizar_dados import ATIVOS, campo, preco, iso, linhas_do_zip, iv_call, R as R_IV   # noqa: E402
import montador as MT                                                                      # noqa: E402

H = 20                                   # pregões à frente (testes 1 e 2)
SPLITS = (2, 3, 4, 5, 8, 10)
LAMBDA = 0.94
B = 2000
PER_VOL = (("2016–2020", "2016", "2020"), ("2021–2025", "2021", "2025"), ("2026", "2026", "2026"), ("tudo", "0000", "9999"))
PER_ML = (("2017–2020", "2017", "2020"), ("2021–2025", "2021", "2025"), ("2026", "2026", "2026"), ("tudo", "0000", "9999"))
FAIXAS = ((0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0))


# ---------- leitura ----------
def ler_spot(zips):
    """s[nome][data] = (fechamento, máxima, mínima, quantidade) do lote padrão; isin[nome] = ISINs do papel."""
    papeis = {pap: nome for nome, (_, pap) in ATIVOS.items()}
    s, isin = {n: {} for n in ATIVOS}, {n: set() for n in ATIVOS}
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) < 242 or ln[0:2] != "01" or ln[24:27] != "010":
                continue
            nome = papeis.get(campo(ln, "codneg"))
            if not nome:
                continue
            c, h, lo = preco(campo(ln, "preult")), preco(campo(ln, "premax")), preco(campo(ln, "premin"))
            if h >= c >= lo > 0:
                s[nome][iso(campo(ln, "data"))] = (c, h, lo, int(campo(ln, "quatot") or 0))
                isin[nome].add(campo(ln, "codisi"))
        print(f"{os.path.basename(z)}: papéis lidos", flush=True)
    return s, isin


def ler_opcoes(zips, isin, amostra):
    """cad[(nome, data)] = opções do papel (filtro pelo papel-objeto) nos dias da amostra, com compra e venda;
    ultimo[(símbolo, AAAAMMDD do vencimento)] = (AAAAMMDD do último pregão, strike nesse pregão)."""
    prefixos = {pref: nome for nome, (pref, _) in ATIVOS.items()}
    alvo = {d.replace("-", "") for d in amostra}
    cad, ultimo = defaultdict(list), {}
    for z in zips:
        for ln in linhas_do_zip(z):
            if len(ln) < 242 or ln[0:2] != "01":
                continue
            tp = ln[24:27]
            if tp != "070" and tp != "080":
                continue
            cod = campo(ln, "codneg"); nome = prefixos.get(cod[:4])
            if not nome or campo(ln, "codisi") not in isin[nome]:
                continue
            dt, venc, k = ln[2:10], ln[202:210], preco(campo(ln, "preexe"))
            u = ultimo.get((cod, venc))
            if u is None or dt > u[0]:
                ultimo[(cod, venc)] = (dt, k)
            if dt in alvo and k > 0:
                b, a = preco(campo(ln, "preofc")), preco(campo(ln, "preofv"))
                if b > 0 and a >= b:
                    cad[(nome, iso(dt))].append(("C" if tp == "070" else "P", k, b, a, cod, venc))
        print(f"{os.path.basename(z)}: opções lidas", flush=True)
    return cad, ultimo


def preparar(s):
    """Arrays do papel com desdobramentos/grupamentos ajustados para trás (preço × fator, quantidade ÷ fator)."""
    import numpy as np
    ds = sorted(s)
    c = [s[d][0] for d in ds]
    fat, acum, ev = [1.0] * len(ds), 1.0, []
    for i in range(len(ds) - 1, 0, -1):
        fat[i] = acum
        r = c[i] / c[i - 1]
        for k in SPLITS:
            if abs(r * k - 1) < 0.06:
                acum /= k; ev.append(f"{ds[i]} desdobramento {k}:1"); break
            if abs(r / k - 1) < 0.06:
                acum *= k; ev.append(f"{ds[i]} grupamento {k}:1"); break
    fat[0] = acum
    f = np.array(fat)
    arr = np.array([s[d] for d in ds], dtype=float)
    return dict(ds=ds, ix={d: i for i, d in enumerate(ds)}, C=arr[:, 0] * f, Hi=arr[:, 1] * f, Lo=arr[:, 2] * f,
                Q=arr[:, 3] / f, ev=sorted(ev))


def rmedia(x, k):
    """Média móvel de k termos terminando em t (NaN antes de ter k termos; NaN no meio vira 0)."""
    import numpy as np
    n = len(x); cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))]); out = np.full(n, np.nan)
    if n >= k:
        out[k - 1:] = (cs[k:] - cs[:-k]) / k
    return out


def iv_dinheiro(S, dia, linhas):
    """A volatilidade implícita do app (montar_dia): mediana das 4 calls mais perto do dinheiro com 25 a 70 dias.
    None quando nenhuma dá implícita (o app usaria 0,30 fixo; aqui o dia fica de fora)."""
    d0 = date.fromisoformat(dia)
    calls = []
    for t, k, b, a, _, venc in linhas:
        dias = (date(int(venc[:4]), int(venc[4:6]), int(venc[6:8])) - d0).days
        if t == "C" and 25 <= dias <= 70 and 5 <= dias <= 100:
            calls.append((abs(k / S - 1), k, (b + a) / 2, dias))
    calls.sort(key=lambda x: x[0])
    ivs = [v for v in (iv_call(m, S, k, dd / 365) for _, k, m, dd in calls[:4]) if v]
    return median(ivs) if ivs else None


def fech_no(s, ds, venc_iso):
    """Fechamento sem ajuste no vencimento (ou no último pregão até 4 dias antes). ds: datas de s, em ordem."""
    i = bisect_right(ds, venc_iso) - 1
    if i < 0 or ds[i] < (date.fromisoformat(venc_iso) - timedelta(days=4)).isoformat():
        return None
    return s[ds[i]][0]


# ---------- estatística ----------
def ic(num, den, rnd):
    """IC 95% de sum(num)/sum(den), reamostrando meses (num e den: somas por mês)."""
    import numpy as np
    num, den = np.asarray(num, float), np.asarray(den, float)
    if len(num) < 3:
        return float("nan"), float("nan")
    idx = rnd.integers(0, len(num), size=(B, len(num)))
    with np.errstate(invalid="ignore", divide="ignore"):
        v = num[idx].sum(1) / den[idx].sum(1)
    v = v[np.isfinite(v)]
    return tuple(np.percentile(v, [2.5, 97.5])) if len(v) else (float("nan"), float("nan"))


def por_mes(meses, valores):
    """Soma por mês: (lista de meses, somas, contagens)."""
    import numpy as np
    ms = sorted(set(meses)); ix = {m: i for i, m in enumerate(ms)}
    soma, cont = np.zeros(len(ms)), np.zeros(len(ms))
    for m, v in zip(meses, valores):
        soma[ix[m]] += v; cont[ix[m]] += 1
    return ms, soma, cont


# ---------- teste 1: volatilidade ----------
PREV = ("implícita (app)", "últimos 20", "últimos 60", "EWMA", "HAR", "implícita × HAR")


def teste_vol(A, s, cad, rnd):
    import numpy as np
    linhas_har, aval = [], []
    for nome, a in A.items():
        C, Hi, Lo, ds = a["C"], a["Hi"], a["Lo"], a["ds"]
        n = len(C)
        lc = np.log(C); r = np.concatenate([[np.nan], np.diff(lc)]); rr = r * r
        P = np.log(Hi / Lo) ** 2 / (4 * math.log(2))
        p1, p5, p22, r22 = P, rmedia(P, 5), rmedia(P, 22), rmedia(rr, 22)
        v20, v60 = rmedia(rr, 20), rmedia(rr, 60)
        ew = np.full(n, np.nan); e = np.nanmean(rr[1:21])
        for i in range(1, n):
            e = LAMBDA * e + (1 - LAMBDA) * rr[i]; ew[i] = e
        csr = np.concatenate([[0.0], np.cumsum(np.nan_to_num(rr))])
        for t in range(60, n - H):
            fut = csr[t + H + 1] - csr[t + 1]          # variância realizada dos 20 pregões seguintes (soma de r²)
            x = [1.0] + [math.log(max(v, 1e-6)) for v in (p1[t], p5[t], p22[t], r22[t])]
            y = math.log(max(fut / H, 1e-6))
            linhas_har.append((ds[t + H], x, y))
            dia = ds[t]
            if (nome, dia) not in cad:
                continue
            iv = iv_dinheiro(s[nome][dia][0], dia, cad[(nome, dia)])
            if iv is None:
                continue
            cal = (date.fromisoformat(ds[t + H]) - date.fromisoformat(dia)).days
            aval.append(dict(nome=nome, dia=dia, x=x, fut=fut, mov=lc[t + H] - lc[t],
                             f={"implícita (app)": iv * iv * cal / 365, "últimos 20": H * v20[t], "últimos 60": H * v60[t],
                                "EWMA": H * ew[t]}))
    # HAR: todos os papéis juntos, refeito a cada mês só com linhas cujo resultado terminou antes do mês
    linhas_har.sort(key=lambda z: z[0])
    fins = [z[0] for z in linhas_har]
    X = np.array([z[1] for z in linhas_har]); Y = np.array([z[2] for z in linhas_har])
    XtX = np.concatenate([np.zeros((1, 5, 5)), np.cumsum(X[:, :, None] * X[:, None, :], 0)])
    XtY = np.concatenate([np.zeros((1, 5)), np.cumsum(X * Y[:, None], 0)])
    YY = np.concatenate([[0.0], np.cumsum(Y * Y)])
    coef = {}
    aval = [v for v in aval if v["dia"] >= "2016-01-01"]
    for v in aval:
        m = v["dia"][:7]
        if m not in coef:
            k = bisect_right(fins, m + "-00")       # fim < primeiro dia do mês
            if k < 500:
                coef[m] = None
            else:
                b = np.linalg.solve(XtX[k], XtY[k])
                s2 = (YY[k] - 2 * b @ XtY[k] + b @ XtX[k] @ b) / (k - 5)
                coef[m] = (b, s2)
        if coef[m] is None:
            v["f"] = None; continue
        b, s2 = coef[m]
        v["f"]["HAR"] = H * math.exp(np.dot(b, v["x"]) + s2 / 2)
        v["f"]["implícita × HAR"] = math.sqrt(v["f"]["HAR"] * v["f"]["implícita (app)"])
    aval = [v for v in aval if v["f"] and all(np.isfinite(v["f"][p]) and v["f"][p] > 0 for p in PREV) and v["fut"] > 0]
    out = ["", "## 1. Volatilidade dos 20 pregões seguintes", "",
           "QLIKE: perda padrão para previsão de variância (menor é melhor). Erro: diferença média, em pontos de "
           "volatilidade anual, entre a prevista e a que aconteceu. Viés: prevista ÷ realizada − 1 (mediana). Faixa ±1σ e "
           "±2σ: em quantos % dos casos o preço 20 pregões depois ficou dentro da faixa (esperado 68,3% e 95,4%). "
           "Diferença de QLIKE contra a implícita (negativa = erra menos que a implícita), com IC 95%."]
    for titulo, de, ate in PER_VOL:
        vs = [v for v in aval if de <= v["dia"][:4] <= ate]
        if not vs:
            continue
        meses = [v["dia"][:7] for v in vs]
        out += ["", f"### {titulo} — {len(vs)} dias×papel, {len(set(meses))} meses; volatilidade realizada mediana "
                f"{100 * median(math.sqrt(v['fut'] * 252 / H) for v in vs):.1f}% ao ano",
                "| previsão | QLIKE | dif. QLIKE × implícita [IC 95%] | erro (pp de vol. anual) | viés | faixa ±1σ | faixa ±2σ |",
                "|---|---|---|---|---|---|---|"]
        qi = [v["fut"] / v["f"]["implícita (app)"] - math.log(v["fut"] / v["f"]["implícita (app)"]) - 1 for v in vs]
        for p in PREV:
            q = [v["fut"] / v["f"][p] - math.log(v["fut"] / v["f"][p]) - 1 for v in vs]
            err = sum(abs(math.sqrt(v["f"][p] * 252 / H) - math.sqrt(v["fut"] * 252 / H)) for v in vs) / len(vs)
            vies = median(math.sqrt(v["f"][p] / v["fut"]) for v in vs) - 1
            c1 = sum(abs(v["mov"]) <= math.sqrt(v["f"][p]) for v in vs) / len(vs)
            c2 = sum(abs(v["mov"]) <= 2 * math.sqrt(v["f"][p]) for v in vs) / len(vs)
            if p == "implícita (app)":
                dif = "—"
            else:
                _, sm, ct = por_mes(meses, [a - b for a, b in zip(q, qi)])
                lo, hi = ic(sm, ct, rnd)
                dif = f"{sum(q) / len(q) - sum(qi) / len(qi):+.3f} [{lo:+.3f}, {hi:+.3f}]"
            out.append(f"| {p} | {sum(q) / len(q):.3f} | {dif} | {100 * err:.1f} | {100 * vies:+.0f}% | "
                       f"{100 * c1:.1f}% | {100 * c2:.1f}% |")
    return out


# ---------- teste 2: direção ----------
FEAT = ("r1", "r5", "r20", "r60", "r120", "dist_mm21", "dist_mm50", "incl_mm50", "adx", "ifr", "vol20", "park20",
        "vol20_60", "volume5_60", "dist_max120", "mkt_r5", "mkt_r20", "rel20")


def linhas_ml(A):
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view
    bova = A.get("BOVA11")
    lcb = np.log(bova["C"]) if bova else None
    rows = []
    for nome, a in A.items():
        C, Hi, Lo, Q, ds = a["C"], a["Hi"], a["Lo"], a["Q"], a["ds"]
        n = len(C)
        if n < 150 + H:
            continue
        lc = np.log(C); r = np.concatenate([[np.nan], np.diff(lc)]); rr = r * r
        P = np.log(Hi / Lo) ** 2 / (4 * math.log(2))
        mm21, mm50 = rmedia(C, 21), rmedia(C, 50)
        v20, v60, pk20 = np.sqrt(rmedia(rr, 20)), np.sqrt(rmedia(rr, 60)), np.sqrt(rmedia(P, 20))
        q5, q60 = rmedia(Q, 5), rmedia(Q, 60)
        mx = np.full(n, np.nan); mx[119:] = sliding_window_view(C, 120).max(1)
        for t in range(149, n - H):
            jan = ds[t - 149:t + 1]
            fe = {d: C[a["ix"][d]] for d in jan}
            mm = {d: [Hi[a["ix"][d]], Lo[a["ix"][d]]] for d in jan}
            td = MT.tendencia(fe, mm, ds[t], False)
            jb = bova["ix"].get(ds[t]) if bova else None
            mk5 = lcb[jb] - lcb[jb - 5] if jb is not None and jb >= 5 else np.nan
            mk20 = lcb[jb] - lcb[jb - 20] if jb is not None and jb >= 20 else np.nan
            f = dict(r1=r[t], r5=lc[t] - lc[t - 5], r20=lc[t] - lc[t - 20], r60=lc[t] - lc[t - 60], r120=lc[t] - lc[t - 120],
                     dist_mm21=math.log(C[t] / mm21[t]), dist_mm50=math.log(C[t] / mm50[t]),
                     incl_mm50=math.log(mm50[t] / mm50[t - 5]),
                     adx=td["adx"] if td and td["adx"] is not None else np.nan,
                     ifr=td["ifr"] if td and td["ifr"] is not None else np.nan,
                     vol20=v20[t], park20=pk20[t], vol20_60=v20[t] / v60[t] if v60[t] > 0 else np.nan,
                     volume5_60=math.log(q5[t] / q60[t]) if q5[t] > 0 and q60[t] > 0 else np.nan,
                     dist_max120=math.log(C[t] / mx[t]), mkt_r5=mk5, mkt_r20=mk20,
                     rel20=(lc[t] - lc[t - 20]) - mk20 if np.isfinite(mk20) else np.nan)
            rows.append(dict(nome=nome, dia=ds[t], fim={5: ds[t + 5], 20: ds[t + 20]}, x=[f[k] for k in FEAT],
                             fwd={5: lc[t + 5] - lc[t], 20: lc[t + 20] - lc[t]}))
    return rows


def auc(y, p):
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(y, p) if 0 < sum(y) < len(y) else float("nan")


def teste_direcao(rows, rnd):
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    X = np.array([r["x"] for r in rows], dtype=float)
    dias = np.array([r["dia"] for r in rows])
    anos = sorted({d[:4] for d in dias if "2017" <= d[:4]})
    out = ["", "## 2. Direção: sobe ou cai em 5 e 20 pregões", "",
           f"{len(rows)} dias×papel com as {len(FEAT)} variáveis. Treino: anos anteriores (só linhas cujo resultado já "
           "era conhecido no início do ano de teste); teste: o ano seguinte, 2017 a 2026. Acerto: o modelo diz alta "
           "quando a chance prevista passa de 50%. \"Mais comum\": acerto de quem repete todo dia a direção mais frequente no "
           "treino (quase sempre \"alta\"). AUC: 0,5 = moeda. "
           "Retorno alta − queda: retorno médio em pontos percentuais nos dias em que o modelo disse alta menos nos dias "
           "em que disse queda (sem custos)."]
    modelos = {
        "gradient boosting": lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=3,
                                                                    min_samples_leaf=200, l2_regularization=1.0, random_state=0),
        "regressão logística": lambda: LogisticRegression(C=1.0, max_iter=2000)}
    for h in (5, 20):
        y = np.array([r["fwd"][h] > 0 for r in rows], dtype=int)
        fwd = np.array([r["fwd"][h] for r in rows])
        fim = np.array([r["fim"][h] for r in rows])
        for nm, fab in modelos.items():
            prob, ingenuo = np.full(len(rows), np.nan), np.full(len(rows), np.nan)
            for ano in anos:
                tr = fim < f"{ano}-01-01"; te = np.array([d[:4] == ano for d in dias])
                if tr.sum() < 2000 or te.sum() == 0:
                    continue
                Xtr, Xte = X[tr], X[te]
                if nm == "regressão logística":
                    med = np.nanmedian(Xtr, 0)
                    Xtr = np.where(np.isnan(Xtr), med, Xtr); Xte = np.where(np.isnan(Xte), med, Xte)
                    sc = StandardScaler().fit(Xtr); Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
                prob[te] = fab().fit(Xtr, y[tr]).predict_proba(Xte)[:, 1]
                ingenuo[te] = float(y[tr].mean() >= 0.5)
            out += ["", f"### {nm}, {h} pregões",
                    "| período | dias×papel | subiu % | acerto do modelo % | mais comum % | diferença (pp) [IC 95%] | AUC [IC 95%] | "
                    "% dos dias com \"alta\" | retorno alta − queda (pp) [IC 95%] |", "|---|---|---|---|---|---|---|---|---|"]
            for titulo, de, ate in PER_ML:
                sel = np.array([de <= d[:4] <= ate for d in dias]) & np.isfinite(prob)
                if sel.sum() < 50:
                    continue
                ys, ps, fs, ms = y[sel], prob[sel], fwd[sel], [d[:7] for d in dias[sel]]
                diz = ps > 0.5
                certo = (diz == ys.astype(bool)).astype(float); certo0 = (ingenuo[sel] == ys).astype(float)
                ac, ac0, base = certo.mean(), certo0.mean(), ys.mean()
                _, sm, ct = por_mes(ms, certo - certo0)
                lo, hi = ic(sm, ct, rnd)
                # AUC com meses reamostrados
                grupos = defaultdict(list)
                for i, m in enumerate(ms):
                    grupos[m].append(i)
                gl = [np.array(v) for v in grupos.values()]
                bs = []
                for _ in range(B // 2):
                    ii = np.concatenate([gl[j] for j in rnd.integers(0, len(gl), len(gl))])
                    bs.append(auc(ys[ii], ps[ii]))
                bs = np.array(bs); bs = bs[np.isfinite(bs)]
                alo, ahi = np.percentile(bs, [2.5, 97.5])
                # retorno médio nos dias "alta" menos nos dias "queda"
                if 0 < diz.sum() < len(diz):
                    spread = fs[diz].mean() - fs[~diz].mean()
                    mu, su, cu = por_mes([m for m, d in zip(ms, diz) if d], fs[diz])
                    md, sd, cd = por_mes([m for m, d in zip(ms, diz) if not d], fs[~diz])
                    todos = sorted(set(mu) | set(md)); iu = {m: i for i, m in enumerate(mu)}; idd = {m: i for i, m in enumerate(md)}
                    SU = np.array([su[iu[m]] if m in iu else 0 for m in todos]); CU = np.array([cu[iu[m]] if m in iu else 0 for m in todos])
                    SD = np.array([sd[idd[m]] if m in idd else 0 for m in todos]); CD = np.array([cd[idd[m]] if m in idd else 0 for m in todos])
                    idx = rnd.integers(0, len(todos), size=(B, len(todos)))
                    with np.errstate(invalid="ignore", divide="ignore"):
                        v = SU[idx].sum(1) / CU[idx].sum(1) - SD[idx].sum(1) / CD[idx].sum(1)
                    v = v[np.isfinite(v)]
                    slo, shi = np.percentile(v, [2.5, 97.5])
                    sp = f"{100 * spread:+.2f} [{100 * slo:+.2f}, {100 * shi:+.2f}]"
                else:
                    sp = "— (só um lado)"
                out.append(f"| {titulo} | {sel.sum()} | {100 * base:.1f} | {100 * ac:.1f} | {100 * ac0:.1f} | "
                           f"{100 * (ac - ac0):+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}] | {auc(ys, ps):.3f} [{alo:.3f}, {ahi:.3f}] | "
                           f"{100 * diz.mean():.0f} | {sp} |")
    return out


# ---------- teste 3: caudas ----------
MODELOS3 = ("app", "sorriso", "caudas históricas")


def tabela_z(A, ano, h, cache):
    """Retornos de h pregões de todos os papéis, padronizados pela volatilidade dos 60 pregões anteriores, terminados
    antes de 1º de janeiro do ano; centrados e com desvio 1 (só a forma). Ordenados."""
    import numpy as np
    if (ano, h) in cache:
        return cache[(ano, h)]
    zs = []
    for a in A.values():
        lc = np.log(a["C"])
        if "sig" not in a:
            r = np.concatenate([[np.nan], np.diff(lc)])
            a["sig"] = np.sqrt(rmedia(r * r, 60))
        k = bisect_right(a["ds"], f"{ano - 1}-12-31")        # índices < k têm data no ano anterior ou antes
        i = np.arange(60, max(60, k - h))                     # i + h < k
        if len(i) == 0:
            continue
        z = (lc[i + h] - lc[i]) / (a["sig"][i] * math.sqrt(h))
        zs.append(z[np.isfinite(z)])
    z = np.concatenate(zs) if zs else np.array([])
    z = np.sort((z - z.mean()) / z.std()) if len(z) > 200 else None
    cache[(ano, h)] = z
    return z


def teste_caudas(A, s, cad, ultimo, rnd):
    import numpy as np
    cache, rows = {}, []
    fim_dados = max(max(v) for v in s.values() if v)
    for (nome, dia), linhas in cad.items():
        if dia < "2016-01-01" or nome not in A:
            continue
        S = s[nome][dia][0]
        iv = iv_dinheiro(S, dia, linhas)
        if iv is None:
            continue
        d0 = date.fromisoformat(dia)
        for t, k, b, a, cod, venc in linhas:
            dv = date(int(venc[:4]), int(venc[4:6]), int(venc[6:8])); dias = (dv - d0).days
            if not 15 <= dias <= 70 or dv.isoformat() > fim_dados:
                continue
            if (t == "C" and k <= S) or (t == "P" and k >= S):
                continue                                       # só fora do dinheiro
            T = dias / 365
            dist = abs(math.log(k / S)) / (iv * math.sqrt(T))
            if dist >= 3:
                continue
            ST = fech_no(s[nome], A[nome]["ds"], dv.isoformat())
            if ST is None:
                continue
            kf = ultimo.get((cod, venc), (None, k))[1] or k
            ev = (ST > kf) if t == "C" else (ST < kf)
            mid = (b + a) / 2
            pc = mid if t == "C" else mid + S - k * math.exp(-R_IV * T)   # put pela paridade, como call
            ivp = iv_call(pc, S, k, T)
            pa = MT.prob_acima(S, k, dias, iv)
            ps = MT.prob_acima(S, k, dias, ivp) if ivp else None
            hh = max(1, round(dias * 252 / 365))
            z = tabela_z(A, int(dia[:4]), hh, cache)
            if z is None:
                continue
            u = (math.log(k / S) - (MT.R_BS - 0.5 * iv * iv) * T) / (iv * math.sqrt(T))
            acima = 1 - float(np.searchsorted(z, u, side="right")) / len(z)
            p = {"app": pa if t == "C" else 1 - pa,
                 "sorriso": (ps if t == "C" else 1 - ps) if ps is not None else None,
                 "caudas históricas": acima if t == "C" else 1 - acima}
            rows.append(dict(dia=dia, lado="acima (call)" if t == "C" else "abaixo (put)", dist=dist, ev=bool(ev), p=p,
                             filtro=(a - b) <= 0.5 * mid and ps is not None))
    out = ["", "## 3. Caudas: a chance das opções fora do dinheiro", "",
           f"{len(rows)} opções×dia fora do dinheiro, 15 a 70 dias, 2016 em diante. Distância: quantos desvios (pela "
           "implícita do dinheiro até o vencimento) o strike está do preço. \"Real\": em quantos % o papel terminou além do "
           "strike no vencimento. Colunas de modelo: chance média prevista. Amostra A: todas as opções com compra e venda "
           "(app × caudas, que não dependem do preço da opção). Amostra B: só as com spread de até 50% do preço médio e "
           "implícita própria calculável (os três modelos)."]
    for amostra, filtro, mods in (("A — todas", False, ("app", "caudas históricas")), ("B — spread até 50%", True, MODELOS3)):
        rs = [r for r in rows if r["filtro"] or not filtro]
        out += ["", f"### Amostra {amostra}: {len(rs)} opções×dia",
                "| lado | distância (desvios) | opções×dia | real % [IC 95%] | " + " | ".join(f"{m} %" for m in mods) + " |",
                "|---" * (4 + len(mods)) + "|"]
        for lado in ("abaixo (put)", "acima (call)"):
            for lo_, hi_ in FAIXAS:
                g = [r for r in rs if r["lado"] == lado and lo_ <= r["dist"] < hi_]
                if len(g) < 30:
                    continue
                ms = [r["dia"][:7] for r in g]
                _, sm, ct = por_mes(ms, [float(r["ev"]) for r in g])
                a_, b_ = ic(sm, ct, rnd)
                real = sum(r["ev"] for r in g) / len(g)
                cols = " | ".join(f"{100 * sum(r['p'][m] for r in g) / len(g):.1f}" for m in mods)
                out.append(f"| {lado} | {lo_:.1f}–{hi_:.1f} | {len(g)} | {100 * real:.1f} [{100 * a_:.1f}, {100 * b_:.1f}] | {cols} |")
        out += ["", f"Brier (menor é melhor; diferença contra o app, IC 95%), amostra {amostra}:", "",
                "| opções | " + " | ".join(mods) + " | " + " | ".join(f"{m} − app" for m in mods if m != "app") + " |",
                "|---" * (1 + 2 * len(mods) - 1) + "|"]
        for rotulo, cond in (("todas", lambda r: True), ("a 1 desvio ou mais", lambda r: r["dist"] >= 1)):
            g = [r for r in rs if cond(r)]
            if not g:
                continue
            br = {m: [(r["p"][m] - r["ev"]) ** 2 for r in g] for m in mods}
            ms = [r["dia"][:7] for r in g]
            difs = []
            for m in mods:
                if m == "app":
                    continue
                _, sm, ct = por_mes(ms, [x - y for x, y in zip(br[m], br["app"])])
                a_, b_ = ic(sm, ct, rnd)
                difs.append(f"{sum(br[m]) / len(g) - sum(br['app']) / len(g):+.4f} [{a_:+.4f}, {b_:+.4f}]")
            out.append(f"| {rotulo} ({len(g)}) | " + " | ".join(f"{sum(br[m]) / len(g):.4f}" for m in mods) + " | " + " | ".join(difs) + " |")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True); ap.add_argument("--saida"); ap.add_argument("--passo", type=int, default=5)
    a = ap.parse_args()
    import numpy as np
    zips = sorted(glob.glob(os.path.join(a.zips, "COTAHIST_A*.ZIP")))
    if not zips:
        raise SystemExit(f"Nenhum COTAHIST_A*.ZIP em {a.zips}")
    s, isin = ler_spot(zips)
    A, txt = {}, ["# Testes de previsão — volatilidade, direção e caudas", "",
                  f"Arquivos: {', '.join(os.path.basename(z) for z in zips)}. Cadeia de opções a cada {a.passo} pregões. "
                  f"IC 95%: bootstrap em blocos mensais ({B} reamostras).", "", "Papéis:"]
    for nome in ATIVOS:
        if len(s[nome]) < 150 + H:
            txt.append(f"- {nome}: só {len(s[nome])} pregões, fora"); continue
        A[nome] = preparar(s[nome])
        txt.append(f"- {nome}: {min(s[nome])} a {max(s[nome])}, {len(s[nome])} pregões; ajustes: {'; '.join(A[nome]['ev']) or 'nenhum'}")
    datas = sorted(set().union(*(set(v) for v in s.values())))
    amostra = datas[::a.passo]
    print(f"{len(datas)} pregões, {len(amostra)} dias com cadeia", flush=True)
    cad, ultimo = ler_opcoes(zips, isin, amostra)
    rnd = np.random.default_rng(20261106)
    txt += teste_vol(A, s, cad, rnd); print("teste 1 pronto", flush=True)
    txt += teste_direcao(linhas_ml(A), rnd); print("teste 2 pronto", flush=True)
    txt += teste_caudas(A, s, cad, ultimo, rnd); print("teste 3 pronto", flush=True)
    txt += ["", "Limitações: janelas sobrepostas (o IC por meses cobre a dependência entre dias próximos); proventos não "
            "ajustados nos testes 1 e 2 (a queda do dia ex entra na volatilidade realizada e no retorno, igual para todas "
            "as previsões); no teste 3, a chance do sorriso usa N(d2) com a implícita da própria opção (aproximação: não "
            "inclui a inclinação do sorriso)."]
    saida = "\n".join(txt)
    print(saida)
    if a.saida:
        with open(a.saida, "w", encoding="utf-8") as f:
            f.write(saida + "\n")


if __name__ == "__main__":
    main()
