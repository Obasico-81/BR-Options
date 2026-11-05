"""Montador de operação (v0): recebe a TESE do usuário e monta a execução de menor custo e risco.
Não gera sinal de entrada nem promete vantagem estatística (ver Base técnica, "Decisão de produto").
Teses: alta | baixa | forte (movimento forte, direção incerta) | alta_com_caixa (put vendida coberta por caixa).
Estruturas de risco ilimitado não são oferecidas."""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from math import log, sqrt, erf, exp, pi, floor
from datetime import date, timedelta
from typing import Optional

TAXA_B3 = 0.00134          # 0,134% do prêmio por lado (swing, PF) — conferir vigência
LOTE = 100
_CORRETAGEM: Optional[float] = None   # R$ por ordem; None = não informada (o custo não soma corretagem)


@dataclass(frozen=True)
class Opcao:
    tipo: str              # "C" | "P"
    strike: float
    bid: float
    ask: float
    volume: int
    dias: int
    simbolo: str = ""      # código de negociação (ex.: PETRL524): liga a perna ao preço diário (resultado_no_dia)

    @property
    def mid(self) -> float: return (self.bid + self.ask) / 2
    @property
    def spread(self) -> float: return (self.ask - self.bid) / self.mid if self.mid > 0 else 9.9


@dataclass(frozen=True)
class Montagem:
    tese: str
    estrutura: str
    pernas: tuple              # (lado, Opcao): lado +1 compra, -1 venda
    lotes: int
    premio: float              # R$ total pago (>0 débito) ou recebido (<0 crédito) no preço do mercado (bid/ask)
    perda_max: float
    ganho_max: Optional[float] # None = ilimitado
    pontos_equilibrio: tuple
    prob_implicita: float      # probabilidade implícita no preço de terminar com lucro
    custo_total: float         # custo_spread + custo_taxas + custo_fixo
    alvo: Optional[float]      # resultado em R$ que dispara a saída por ganho
    stop: Optional[float]      # resultado (negativo) que dispara a saída por perda; None = sem limite (trava e strangle)
    data_max_dias: int         # sair quando faltar este número de dias
    avisos: tuple = ()
    theta_dia: Optional[float] = None   # R$/dia que a operação desvaloriza se nada mudar (só compra simples)
    custo_spread: float = 0.0  # spread em relação ao preço médio (já está no prêmio), por todos os lotes
    custo_taxas: float = 0.0   # taxas da B3 de entrada e saída, por todos os lotes
    custo_fixo: float = 0.0    # corretagem cadastrada por ordem: pernas × 2, não cresce com os lotes (0 sem cadastro)


SPREAD_MAX = 0.20  # spread máximo (venda − compra) / médio, no fechamento; era 10% até 02/11/2026

def brl(v: float) -> str:
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def brl2(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _n(x: float) -> float: return 0.5 * (1 + erf(x / sqrt(2)))


def set_corretagem(v) -> None:
    """Corretagem do usuário em R$ por ordem; None (ou inválida/negativa) = não informada. Espelha setCorretagem."""
    global _CORRETAGEM
    try:
        _CORRETAGEM = None if v is None or float(v) < 0 else float(v)
    except (TypeError, ValueError):
        _CORRETAGEM = None


def _fixo(n_pernas: int) -> float:
    """Corretagem do usuário por ordem (cada perna, na entrada e na saída); 0 sem cadastro. Não cresce com os lotes."""
    return 0.0 if _CORRETAGEM is None else _CORRETAGEM * n_pernas * 2


def _custos(spread1: float, taxas1: float, n_pernas: int, lotes: int) -> dict:
    """Custos da operação em R$, como custos() do JS: spread e taxas por lote; corretagem por ordem."""
    s, t, f = spread1 * lotes, taxas1 * lotes, _fixo(n_pernas)
    return dict(custo_total=_r2(s + t + f), custo_spread=_r2(s), custo_taxas=_r2(t), custo_fixo=_r2(f))


# juro livre de risco (10% a.a.): no Black-Scholes dos perfis e na chance implícita. Sem ele a chance ficava baixa nas
# operações de alta e alta nas de baixa (replay 2015–2026, pesquisa/replay.py).
R_BS = 0.10


def prob_acima(S: float, K: float, dias: int, vol: float) -> float:
    t = dias / 365
    return _n((log(S / K) + (R_BS - 0.5 * vol**2) * t) / (vol * sqrt(t)))


def _liquidas(chain, tipo, dias_min, dias_max, spread_max, vol_min):
    return [o for o in chain if o.tipo == tipo and dias_min <= o.dias <= dias_max
            and o.bid > 0 and o.ask >= o.bid and o.spread <= spread_max and o.volume >= vol_min]


def _perto(opcoes, alvo):
    return min(opcoes, key=lambda o: (abs(o.strike - alvo), o.spread)) if opcoes else None


def _preco(o: Opcao, lado: int) -> float:       # execução no pior lado (bid/ask)
    return o.ask if lado > 0 else o.bid


def montar(tese: str, S: float, chain: list, vol_impl: float, perda_aceita: float,
           prazo_alvo: int = 45, caixa: float = 0.0, spread_max: float = SPREAD_MAX, vol_min: int = 500,
           stop_frac: float = 0.70, alvo_frac: float = 0.50) -> Montagem | str:
    """Retorna Montagem ou uma string explicando por que não há operação possível."""
    j = (max(prazo_alvo - 15, 7), prazo_alvo + 15)
    venc = incons = None
    # vencimento mais próximo do prazo alvo que tenha opções líquidas (e, na trava, preços consistentes)
    dias_disp = sorted({o.dias for o in chain if j[0] <= o.dias <= j[1]}, key=lambda d: abs(d - prazo_alvo))
    for d in dias_disp:
        ch = [o for o in chain if o.dias == d]
        pernas = _escolher(tese, S, ch, spread_max, vol_min)
        if pernas:
            inc = _inconsistente(pernas) if tese in ("alta", "baixa") else None
            if inc:
                incons = incons or inc; continue   # tenta o próximo vencimento
            venc = d; break
    if venc is None:
        return incons or "Sem opções líquidas no prazo pedido. Tente outro prazo ou outro ativo."
    cred = sum(-l * _preco(o, l) for l, o in pernas)   # >0 crédito por ação
    premio = -cred * LOTE                              # >0 débito
    mid = sum(-l * o.mid for l, o in pernas); premio_mid = -mid * LOTE
    est = _estrutura(tese, pernas)
    perda1, ganho1, eq = _payoff(tese, pernas, premio, S)
    if tese == "alta_com_caixa":
        caixa1 = pernas[0][1].strike * LOTE
        if caixa < caixa1:
            return f"Falta caixa: a put vendida exige reservar {brl(caixa1)}."
        lotes = int(caixa // caixa1); perda_lote = perda1
        # a perda máxima é o caixa; o limite de saída trava antes, e no total (todos os lotes) não passa do risco aceito
        stop = -min(stop_frac * perda1, perda_aceita / lotes) if lotes else 0.0
    else:
        lotes = int(perda_aceita // perda1) if perda1 > 0 else 0
        stop = None   # trava e strangle: sem limite (o risco já é o que se pagou; replay 2015–2026)
    if lotes < 1:
        return f"A menor operação arrisca {brl(perda1)}, acima do seu limite de {brl(perda_aceita)}."
    taxas = sum(TAXA_B3 * o.mid * LOTE for l, o in pernas) * 2
    c = _custos(abs(premio - premio_mid), taxas, len(pernas), lotes)
    ganho = ganho1
    alvo = alvo_frac * ganho1 if ganho1 is not None else None
    ks = [o.strike for l, o in pernas]
    if tese == "forte": prob = prob_acima(S, eq[1], venc, vol_impl) + 1 - prob_acima(S, eq[0], venc, vol_impl)
    elif tese in ("alta", "alta_com_caixa"): prob = prob_acima(S, eq[0], venc, vol_impl)
    else: prob = 1 - prob_acima(S, eq[0], venc, vol_impl)
    avisos = ["Probabilidade implícita no preço de mercado; não é vantagem do usuário.",
              "Nos testes de 2015–2025 nenhuma estrutura teve lucro médio estável."]
    return Montagem(tese, est, tuple(pernas), lotes, round(premio * lotes, 2), round(perda1 * lotes, 2),
                    None if ganho is None else round(ganho * lotes, 2), tuple(round(x, 2) for x in eq),
                    round(prob, 3), c.pop("custo_total"),
                    None if alvo is None else round(alvo * lotes, 2), None if stop is None else round(stop * lotes, 2),
                    7, tuple(avisos), **c)


def _inconsistente(pernas) -> Optional[str]:
    """Trava com preços de fechamento impossíveis (ex.: opção de outro papel com o mesmo prefixo, ou preço parado): entrada
    com crédito, ou débito igual ou maior que a distância entre os strikes. Devolve a mensagem, ou None. Espelha inconsistente."""
    a, b = pernas[0][1], pernas[1][1]
    deb, larg, par = (a.ask - b.bid) * LOTE, abs(b.strike - a.strike) * LOTE, f"comprar {a.simbolo} e vender {b.simbolo}"
    if deb <= 0:
        return f"Preços de fechamento inconsistentes: {par} {f'daria crédito de {brl(-deb)}' if deb < 0 else 'não teria custo'}. O app não monta esta operação com esses preços."
    if deb >= larg:
        return f"Preços de fechamento inconsistentes: {par} custaria {brl(deb)}, e a trava paga no máximo {brl(larg)}. O app não monta esta operação com esses preços."
    return None


def _escolher(tese, S, ch, spread_max, vol_min):
    C = _liquidas(ch, "C", 0, 999, spread_max, vol_min); P = _liquidas(ch, "P", 0, 999, spread_max, vol_min)
    if tese == "alta":
        a, b = _perto(C, S), _perto([o for o in C if o.strike > S * 1.02], S * 1.05)
        return [(+1, a), (-1, b)] if a and b and b.strike > a.strike else None
    if tese == "baixa":
        a, b = _perto(P, S), _perto([o for o in P if o.strike < S * 0.98], S * 0.95)
        return [(+1, a), (-1, b)] if a and b and b.strike < a.strike else None
    if tese == "forte":
        c, p = _perto([o for o in C if o.strike >= S * 1.02], S * 1.05), _perto([o for o in P if o.strike <= S * 0.98], S * 0.95)
        return [(+1, c), (+1, p)] if c and p else None
    if tese == "alta_com_caixa":
        p = _perto([o for o in P if o.strike < S], S * 0.95)
        return [(-1, p)] if p else None
    raise ValueError(f"tese desconhecida: {tese}")


def _estrutura(tese, pernas):
    return {"alta": "Trava de alta com calls", "baixa": "Trava de baixa com puts",
            "forte": "Strangle comprado", "alta_com_caixa": "Put vendida coberta por caixa"}[tese]


def _payoff(tese, pernas, premio, S):
    """Retorna (perda máx por lote R$, ganho máx por lote R$ ou None, pontos de equilíbrio)."""
    deb = premio / LOTE                    # por ação; <0 = crédito
    ks = [o.strike for l, o in pernas]
    if tese == "alta":
        return deb * LOTE, (ks[1] - ks[0] - deb) * LOTE, (ks[0] + deb,)
    if tese == "baixa":
        return deb * LOTE, (ks[0] - ks[1] - deb) * LOTE, (ks[0] - deb,)
    if tese == "forte":
        return deb * LOTE, None, (ks[1] - deb, ks[0] + deb)          # (equilíbrio inferior, superior)
    if tese == "alta_com_caixa":
        cred = -deb
        return (ks[0] - cred) * LOTE, cred * LOTE, (ks[0] - cred,)


def montar_sinal(S: float, chain: list, vol_impl: float, perda_aceita: float, entrada: float, alvo: float,
                 prazo_dias: int, estrutura: str = "trava", caixa: float = 0.0, tol_entrada: float = 0.02,
                 margem_prazo: int = 10, min_rr: float = 1.0, spread_max: float = SPREAD_MAX, vol_min: int = 500,
                 stop_frac: float = 0.70, alvo_frac: float = 0.50) -> Montagem | str:
    """Compra por sinal externo: o sinal traz preço de entrada, alvo e prazo estimado até o alvo.
    estrutura "trava": trava de alta com a call vendida no alvo ou acima dele (ganho máximo só se o alvo for cumprido).
    estrutura "put": put vendida no preço de entrada, com caixa (compra a ação na entrada se for exercida).
    Retorna Montagem ou a razão pela qual não há operação possível (nunca adapta a estrutura para forçar uma)."""
    if alvo <= entrada:
        return "Sinal inválido: o alvo precisa estar acima do preço de entrada."
    if S > entrada * (1 + tol_entrada):
        return f"Aguardar: o preço {brl2(S)} ainda está acima da entrada do sinal ({brl2(entrada)})."
    if S >= alvo:
        return f"O preço {brl2(S)} já atingiu o alvo do sinal ({brl2(alvo)})."
    dmin = prazo_dias + margem_prazo
    dias_disp = sorted({o.dias for o in chain if dmin <= o.dias <= dmin + 35})
    if not dias_disp:
        return f"Sem vencimento depois do prazo do sinal ({prazo_dias} dias, mais margem de {margem_prazo})."
    motivo = "Sem opções líquidas para esta estrutura."
    for d in dias_disp:
        ch = [o for o in chain if o.dias == d]
        C = _liquidas(ch, "C", 0, 999, spread_max, vol_min); P = _liquidas(ch, "P", 0, 999, spread_max, vol_min)
        if estrutura == "put":
            p = _perto([o for o in P if o.strike <= S], entrada)
            if not p: continue
            caixa1 = p.strike * LOTE
            if caixa < caixa1:
                motivo = f"Falta caixa: a put vendida exige reservar {brl(caixa1)}."; continue
            pernas = [(-1, p)]; est = "Put vendida no preço de entrada do sinal"; tese = "sinal_put"
        else:
            a = _perto(C, S)
            b = _perto([o for o in C if alvo <= o.strike <= alvo * 1.05], alvo)
            if not a or not b or b.strike <= a.strike:
                motivo = f"Sem call líquida no alvo do sinal ({brl2(alvo)}) ou até 5% acima."; continue
            pernas = [(+1, a), (-1, b)]; est = "Trava de alta até o alvo do sinal"; tese = "sinal_alta"
            inc = _inconsistente(pernas)
            if inc:
                motivo = inc; continue
        cred = sum(-l * _preco(o, l) for l, o in pernas); premio = -cred * LOTE
        premio_mid = -sum(-l * o.mid for l, o in pernas) * LOTE
        base = "alta_com_caixa" if tese == "sinal_put" else "alta"
        perda1, ganho1, eq = _payoff(base, pernas, premio, S)
        if tese == "sinal_alta":
            if perda1 <= 0 or ganho1 / perda1 < min_rr:
                motivo = f"A trava custa {brl(perda1)} para ganhar no máximo {brl(ganho1)}: ganho máximo menor que o risco."
                continue
            lotes = int(perda_aceita // perda1); stop = None   # trava: sem limite (o risco já é o que se pagou)
            if lotes < 1:
                motivo = f"A menor operação arrisca {brl(perda1)}, acima do seu limite de {brl(perda_aceita)}."; continue
        else:
            lotes = int(caixa // (p.strike * LOTE)); stop = -min(stop_frac * perda1, perda_aceita / lotes)   # total ≤ risco aceito
        taxas = sum(TAXA_B3 * o.mid * LOTE for l, o in pernas) * 2
        c = _custos(abs(premio - premio_mid), taxas, len(pernas), lotes)
        prob = prob_acima(S, eq[0], d, vol_impl)
        avisos = ["Probabilidade implícita no preço de mercado; não é vantagem do usuário.",
                  "O alvo vem do sinal recebido; a ferramenta não valida o sinal.",
                  "Nos testes de 2015–2025 nenhuma estrutura teve lucro médio estável."]
        return Montagem(tese, est, tuple(pernas), lotes, round(premio * lotes, 2), round(perda1 * lotes, 2),
                        round(ganho1 * lotes, 2), tuple(round(x, 2) for x in eq), round(prob, 3),
                        c.pop("custo_total"), round(alvo_frac * ganho1 * lotes, 2), None if stop is None else round(stop * lotes, 2), 7, tuple(avisos), **c)
    return motivo


# --- Black-Scholes pelo preço de mercado (juro R_BS), usado só nos perfis e no theta da compra simples ---
PERFIS = {"maior": 0.20, "eq": 0.42, "freq": 0.72}   # delta-alvo: Lucro maior · Equilibrada · Lucro frequente


def _bs_preco(S, K, T, v, tipo):
    d1 = (log(S / K) + (R_BS + v * v / 2) * T) / (v * sqrt(T)); d2 = d1 - v * sqrt(T)
    return S * _n(d1) - K * exp(-R_BS * T) * _n(d2) if tipo == "C" else K * exp(-R_BS * T) * _n(-d2) - S * _n(-d1)


def _iv_opcao(S, o: Opcao):
    """IV pelo preço médio da opção, bisseção em [2%, 300%] (60 passos, como o JS). None se fora do intervalo."""
    T = o.dias / 365; p = o.mid; lo, hi = 0.02, 3.0
    if not p > 0 or _bs_preco(S, o.strike, T, hi, o.tipo) < p or _bs_preco(S, o.strike, T, lo, o.tipo) > p:
        return None
    for _ in range(60):
        m = (lo + hi) / 2
        if _bs_preco(S, o.strike, T, m, o.tipo) < p: lo = m
        else: hi = m
    return (lo + hi) / 2


def _delta_abs(S, o: Opcao):
    v = _iv_opcao(S, o)
    if v is None: return None
    T = o.dias / 365; d1 = (log(S / o.strike) + (R_BS + v * v / 2) * T) / (v * sqrt(T))
    return _n(d1) if o.tipo == "C" else 1 - _n(d1)


def _theta_dia(S, o: Opcao):
    """R$ por ação que a opção perde por dia corrido se nada mudar, pela IV do próprio preço."""
    v = _iv_opcao(S, o)
    if v is None: return None
    T = o.dias / 365; K = o.strike; sq = sqrt(T)
    d1 = (log(S / K) + (R_BS + v * v / 2) * T) / (v * sq); d2 = d1 - v * sq; pdf = exp(-d1 * d1 / 2) / sqrt(2 * pi)
    th = (-S * pdf * v / (2 * sq) - R_BS * K * exp(-R_BS * T) * _n(d2)) if o.tipo == "C" else (-S * pdf * v / (2 * sq) + R_BS * K * exp(-R_BS * T) * _n(-d2))
    return -th / 365


def vol_real_60(fech: dict, ate: str) -> Optional[float]:
    """Volatilidade realizada: retornos log dos últimos 60 pregões (61 fechamentos até `ate`), desvio-padrão amostral
    anualizado por √252. None com menos de 21 fechamentos. Espelha volReal60 do montador.js (mesma ordem das contas)."""
    ds = sorted(d for d in (fech or {}) if d <= ate)[-61:]
    if len(ds) < 21:
        return None
    r = [log(fech[ds[i]] / fech[ds[i - 1]]) for i in range(1, len(ds))]
    mu = 0.0
    for x in r: mu += x
    mu /= len(r); q = 0.0
    for x in r: q += (x - mu) * (x - mu)
    return sqrt(q / (len(r) - 1)) * sqrt(252)


def tendencia(fech: dict, maxmin: dict, ate: str, com_ifr: bool = False) -> Optional[dict]:
    """Tendência do papel (só histórico; colore o minigráfico). maxmin[data] = [máxima, mínima] do dia. Janela: os
    últimos 150 pregões até `ate` com fechamento, máxima e mínima. Alta: fechamento > média de 21 > média de 50, média de 50 acima da de 5 pregões antes, ADX(14) >= 20
    (e, com com_ifr, IFR(14) > 50). Queda: o espelho (IFR < 50). Senão, neutro. ADX e IFR pelo método de Wilder.
    Com menos de 60 pregões na janela: None. Espelha tendencia do montador.js (mesma ordem das contas)."""
    if not maxmin:
        return None
    ds = sorted(d for d in (fech or {}) if d <= ate and d in maxmin)[-150:]
    if len(ds) < 60:
        return None
    c, h, l = [fech[d] for d in ds], [maxmin[d][0] for d in ds], [maxmin[d][1] for d in ds]
    u = len(c) - 1

    def media(ini, fim):
        q = 0.0
        for i in range(ini, fim + 1): q += c[i]
        return q / (fim - ini + 1)
    mm21, mm50, mm50ant = media(u - 20, u), media(u - 49, u), media(u - 54, u - 5)
    sTR = sP = sN = 0.0; adx = None; soma_dx = 0.0; n_dx = 0; gm = pm = 0.0
    for i in range(1, u + 1):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm = up if up > dn and up > 0 else 0.0
        ndm = dn if dn > up and dn > 0 else 0.0
        ch = c[i] - c[i - 1]; g = ch if ch > 0 else 0.0; pp = -ch if ch < 0 else 0.0
        if i <= 14:
            sTR += tr; sP += pdm; sN += ndm; gm += g; pm += pp
            if i == 14:
                gm /= 14; pm /= 14
        else:
            sTR = sTR - sTR / 14 + tr; sP = sP - sP / 14 + pdm; sN = sN - sN / 14 + ndm
            gm = (gm * 13 + g) / 14; pm = (pm * 13 + pp) / 14
        if i >= 14:
            pdi = 100 * sP / sTR if sTR > 0 else 0.0
            ndi = 100 * sN / sTR if sTR > 0 else 0.0
            dx = 100 * abs(pdi - ndi) / (pdi + ndi) if pdi + ndi > 0 else 0.0
            if n_dx < 14:
                soma_dx += dx; n_dx += 1
                if n_dx == 14:
                    adx = soma_dx / 14
            else:
                adx = (adx * 13 + dx) / 14
    ifr = 100.0 if pm == 0 else 100 - 100 / (1 + gm / pm)
    forte = adx is not None and adx >= 20
    alta = forte and c[u] > mm21 > mm50 > mm50ant and (not com_ifr or ifr > 50)
    queda = forte and c[u] < mm21 < mm50 < mm50ant and (not com_ifr or ifr < 50)
    return {"classe": "alta" if alta else "queda" if queda else "neutro", "mm21": mm21, "mm50": mm50, "mm50ant": mm50ant, "adx": adx, "ifr": ifr}


def movimento_necessario(m: Montagem, S: float, fech: dict, ate: str) -> dict:
    """Bloco "Movimento e tempo" (só informação): quanto a ação precisa andar até o primeiro ponto de equilíbrio e
    quanto costuma oscilar no prazo da operação, em fração. Espelha movimentoNecessario do montador.js."""
    vr = vol_real_60(fech, ate); dias = m.pernas[0][1].dias
    return dict(precisa=abs(m.pontos_equilibrio[0] / S - 1), oscilacao=None if vr is None else vr * sqrt(dias / 365), vol_real_60=vr)


def montar_aposta(lado: str, S: float, chain: list, vol_impl: float, valor: float, prazo_alvo: int = 45,
                  spread_max: float = SPREAD_MAX, vol_min: int = 1000, jan: float = 0.05,
                  perfil: Optional[str] = None, tol_delta: Optional[float] = None) -> Montagem | str:
    """Aposta simples: lado "alta" compra call ATM; lado "baixa" compra put ATM. Só opções muito líquidas.
    Perda máxima = valor pago (prêmio). Sem stop e sem alvo: o teste de 2015–2025 não mostrou que saída antecipada ajude."""
    tipo = "C" if lado == "alta" else "P"
    dias_disp = sorted({o.dias for o in chain if max(prazo_alvo - 15, 7) <= o.dias <= prazo_alvo + 15}, key=lambda d: (abs(d - prazo_alvo), d))
    escolha = None
    if perfil in PERFIS:
        # perfil: opção com |delta| mais perto do alvo, dentro da tolerância; empate -> menor spread
        alvo_d = PERFIS[perfil]; tol = tol_delta if tol_delta is not None else (0.15 if perfil == "freq" else 0.12)
        for d in dias_disp:
            L = [x for x in _liquidas([o for o in chain if o.dias == d], tipo, 0, 999, spread_max, vol_min) if abs(x.strike / S - 1) <= 0.20]
            best = None
            for y in L:
                dl = _delta_abs(S, y)
                if dl is None: continue
                gap = abs(dl - alvo_d)
                if gap <= tol and (best is None or gap < best[1] or (gap == best[1] and y.spread < best[0].spread)):
                    best = (y, gap)
            if best: escolha = best[0]; break
    else:
        for d in dias_disp:
            L = _liquidas([o for o in chain if o.dias == d], tipo, 0, 999, spread_max, vol_min)
            o = _perto([x for x in L if abs(x.strike / S - 1) <= jan], S)
            if o: escolha = o; break
    if escolha is None:
        return "Sem opção muito líquida perto do preço atual neste prazo."
    o = escolha; custo1 = o.ask * LOTE
    lotes = int(valor // custo1)
    if lotes < 1:
        return f"A menor operação custa {brl(custo1)}, acima do valor máximo que você definiu ({brl(valor)})."
    prem = o.ask
    if tipo == "C":
        ganho = None; eq = (o.strike + prem,); prob = prob_acima(S, eq[0], o.dias, vol_impl)
        est = "Call comprada (posição de alta)"; tese = "aposta_alta"
    else:
        ganho = (o.strike - prem) * LOTE * lotes; eq = (o.strike - prem,); prob = 1 - prob_acima(S, eq[0], o.dias, vol_impl)
        est = "Put comprada (posição de baixa)"; tese = "aposta_baixa"
    c = _custos((o.ask - o.mid) * LOTE, TAXA_B3 * o.mid * LOTE * 2, 1, lotes)
    perda = prem * LOTE * lotes
    avisos = ("Probabilidade implícita no preço de mercado; não é vantagem do usuário.",
              "Nos testes de 2015–2025, na maior parte dos casos a opção comprada venceu sem valor.")
    return Montagem(tese, est, ((+1, o),), lotes, round(perda, 2), round(perda, 2), None if ganho is None else round(ganho, 2),
                    tuple(round(x, 2) for x in eq), round(prob, 3), c.pop("custo_total"), None, None, 0, avisos,
                    None if (th := _theta_dia(S, o)) is None else round(th * LOTE * lotes, 2), **c)


# --- Marcação diária: valor de hoje e regras de saída (espelha resultadoNoDia e regraDeSaida do montador.js) ---
def _r2(x: float) -> float:
    """Arredonda como o Math.round do JS (o round do Python arredonda 2,675 para 2,67)."""
    return floor(x * 100 + 0.5) / 100


def resultado_no_dia(m: Montagem, precos: dict) -> Optional[float]:
    """Resultado (R$, todos os lotes) se a operação fosse desfeita no fechamento de um dia, pelo preço médio de cada perna
    ((compra + venda) / 2), nunca abaixo do risco máximo. precos: {símbolo: [compra, venda]}. None se faltar preço.
    Espelha resultadoNoDia do montador.js."""
    v = 0.0
    for l, o in m.pernas:
        p = (precos or {}).get(o.simbolo)
        if not p or not p[0] > 0 or not p[1] >= p[0]:
            return None
        v += l * (p[0] + p[1]) / 2
    return _r2(max(v * LOTE * m.lotes - m.premio, -m.perda_max))


def resultado_com_precos(m: Montagem, precos: list) -> float:
    """Resultado com os preços em que cada perna foi de fato desfeita (encerramento registrado): sem piso."""
    return _r2(sum(l * p for (l, _), p in zip(m.pernas, precos)) * LOTE * m.lotes - m.premio)


def execucao(m: Montagem, lotes: int, precos) -> Montagem:
    """Operação real: a montagem refeita com o preço executado de cada perna (R$ por opção, na ordem de m.pernas) e a
    quantidade de lotes da nota. Prêmio, risco, ganho e equilíbrio vêm dos preços executados; alvo e limite são os da
    montagem, na proporção dos lotes. Espelha execucao do montador.js."""
    pernas = tuple((l, replace(o, ask=p) if l > 0 else replace(o, bid=p)) for (l, o), p in zip(m.pernas, precos))
    premio1 = sum(l * p for (l, _), p in zip(m.pernas, precos)) * LOTE
    if m.tese in ("aposta_alta", "aposta_baixa"):
        o, p = pernas[0][1], precos[0]
        perda1 = p * LOTE
        ganho1, eq = (None, (o.strike + p,)) if o.tipo == "C" else ((o.strike - p) * LOTE, (o.strike - p,))
    else:
        t = "alta_com_caixa" if m.tese == "sinal_put" else "alta" if m.tese == "sinal_alta" else m.tese
        perda1, ganho1, eq = _payoff(t, pernas, premio1, None)
    prop = lotes / m.lotes
    return replace(m, pernas=pernas, lotes=lotes, premio=_r2(premio1 * lotes), perda_max=_r2(perda1 * lotes),
                   ganho_max=None if ganho1 is None else _r2(ganho1 * lotes), pontos_equilibrio=tuple(_r2(x) for x in eq),
                   alvo=None if m.alvo is None else _r2(m.alvo * prop), stop=None if m.stop is None else _r2(m.stop * prop))


def regra_de_saida(m: Montagem, marcas: list, venc: str) -> Optional[dict]:
    """Primeira regra de saída atingida nos fechamentos depois da entrada e antes do vencimento: alvo, limite (stop) ou
    prazo (a partir de data_max_dias antes do vencimento). marcas: [{"d": "AAAA-MM-DD", "r": resultado ou None}] em ordem
    de data. Devolve {"regra", "d", "r"} ou None."""
    prazo = (date.fromisoformat(venc) - timedelta(days=m.data_max_dias)).isoformat() if m.data_max_dias > 0 else None
    for mk in marcas:
        d, r = mk["d"], mk["r"]
        if r is None or d >= venc:
            continue
        if m.alvo is not None and r >= m.alvo:
            return {"regra": "alvo", "d": d, "r": r}
        if m.stop is not None and r <= m.stop:
            return {"regra": "limite", "d": d, "r": r}
        if prazo and d >= prazo:
            return {"regra": "prazo", "d": d, "r": r}
    return None
