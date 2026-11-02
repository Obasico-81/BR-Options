// Port de montador.py (mesmas regras). Funciona no navegador (window.Montador) e no Node (module.exports).
(function (root) {
  const TAXA_B3 = 0.00134, CUSTO_FIXO = 2.0, LOTE = 100;
  // Corretagem do usuário (R$ por ordem). null = não informada: vale a margem fixa de R$ 2 por estrutura.
  let CORRETAGEM = null;
  const setCorretagem = (v) => { CORRETAGEM = (v === null || v === undefined || isNaN(+v) || +v < 0) ? null : +v; };
  const fixo = (n) => CORRETAGEM === null ? CUSTO_FIXO * 2 : CORRETAGEM * n * 2;
  const mid = (o) => (o.b + o.a) / 2;
  const spread = (o) => (mid(o) > 0 ? (o.a - o.b) / mid(o) : 9.9);
  const erf = (x) => { // Abramowitz-Stegun 7.1.26 não basta p/ paridade; usa série de alta precisão
    const s = Math.sign(x); x = Math.abs(x);
    const t = 1 / (1 + 0.3275911 * x);
    const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
    return s * y;
  };
  const N = (x) => 0.5 * (1 + erf(x / Math.SQRT2));
  const probAcima = (S, K, dias, vol) => { const t = dias / 365; return N((Math.log(S / K) - 0.5 * vol * vol * t) / (vol * Math.sqrt(t))); };
  const liquidas = (ch, tipo, spreadMax, volMin) => ch.filter((o) => o.t === tipo && o.b > 0 && o.a >= o.b && spread(o) <= spreadMax && o.v >= volMin);
  const perto = (L, alvo) => L.length ? L.reduce((m, o) => {
    const key = (x) => [Math.abs(x.k - alvo), spread(x)];
    const a = key(o), b = key(m); return (a[0] < b[0] || (a[0] === b[0] && a[1] < b[1])) ? o : m; }) : null;
  const preco = (o, lado) => (lado > 0 ? o.a : o.b);
  const escolher = (tese, S, ch, spreadMax, volMin) => {
    const C = liquidas(ch, "C", spreadMax, volMin), P = liquidas(ch, "P", spreadMax, volMin);
    if (tese === "alta") { const a = perto(C, S), b = perto(C.filter((o) => o.k > S * 1.02), S * 1.05); return a && b && b.k > a.k ? [[1, a], [-1, b]] : null; }
    if (tese === "baixa") { const a = perto(P, S), b = perto(P.filter((o) => o.k < S * 0.98), S * 0.95); return a && b && b.k < a.k ? [[1, a], [-1, b]] : null; }
    if (tese === "forte") { const c = perto(C.filter((o) => o.k >= S * 1.02), S * 1.05), p = perto(P.filter((o) => o.k <= S * 0.98), S * 0.95); return c && p ? [[1, c], [1, p]] : null; }
    if (tese === "alta_com_caixa") { const p = perto(P.filter((o) => o.k < S), S * 0.95); return p ? [[-1, p]] : null; }
    throw new Error("tese desconhecida: " + tese);
  };
  const NOMES = { alta: "Trava de alta com calls", baixa: "Trava de baixa com puts", forte: "Strangle comprado", alta_com_caixa: "Put vendida coberta por caixa" };
  function payoff(tese, pernas, premio) {
    const deb = premio / LOTE, ks = pernas.map((p) => p[1].k);
    if (tese === "alta") return [deb * LOTE, (ks[1] - ks[0] - deb) * LOTE, [ks[0] + deb]];
    if (tese === "baixa") return [deb * LOTE, (ks[0] - ks[1] - deb) * LOTE, [ks[0] - deb]];
    if (tese === "forte") return [deb * LOTE, null, [ks[1] - deb, ks[0] + deb]];
    const cred = -deb; return [(ks[0] - cred) * LOTE, cred * LOTE, [ks[0] - cred]];
  }
  const r2 = (x) => Math.round(x * 100) / 100;
  function montar(tese, S, chain, volImpl, perdaAceita, o = {}) {
    const prazoAlvo = o.prazoAlvo ?? 45, caixa = o.caixa ?? 0, spreadMax = o.spreadMax ?? 0.10, volMin = o.volMin ?? 500, stopFrac = o.stopFrac ?? 0.70, alvoFrac = o.alvoFrac ?? 0.50;
    const jmin = Math.max(prazoAlvo - 15, 7), jmax = prazoAlvo + 15;
    const dias = [...new Set(chain.filter((x) => x.d >= jmin && x.d <= jmax).map((x) => x.d))].sort((a, b) => Math.abs(a - prazoAlvo) - Math.abs(b - prazoAlvo) || a - b);
    let venc = null, pernas = null;
    for (const d of dias) { const p = escolher(tese, S, chain.filter((x) => x.d === d), spreadMax, volMin); if (p) { venc = d; pernas = p; break; } }
    if (venc === null) return "Sem opções líquidas no prazo pedido. Tente outro prazo ou outro ativo.";
    const cred = pernas.reduce((s, [l, x]) => s + -l * preco(x, l), 0), premio = -cred * LOTE;
    const premioMid = -pernas.reduce((s, [l, x]) => s + -l * mid(x), 0) * LOTE;
    const [perda1, ganho1, eq] = payoff(tese, pernas, premio);
    let lotes, stop;
    const fmt = (v) => v.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
    if (tese === "alta_com_caixa") {
      const caixa1 = pernas[0][1].k * LOTE;
      if (caixa < caixa1) return "Falta caixa: a put vendida exige reservar R$ " + fmt(caixa1) + ".";
      lotes = Math.floor(caixa / caixa1); stop = -Math.min(stopFrac * perda1, perdaAceita);
    } else { lotes = perda1 > 0 ? Math.floor(perdaAceita / perda1) : 0; stop = -stopFrac * perda1; }
    if (lotes < 1) return "A menor operação arrisca R$ " + fmt(perda1) + ", acima do seu limite de R$ " + fmt(perdaAceita) + ".";
    const taxas = pernas.reduce((s, [l, x]) => s + TAXA_B3 * mid(x) * LOTE, 0) * 2;
    const custo = Math.abs(premio - premioMid) + taxas + fixo(pernas.length);
    const alvo = ganho1 === null ? null : alvoFrac * ganho1;
    let prob;
    if (tese === "forte") prob = probAcima(S, eq[1], venc, volImpl) + 1 - probAcima(S, eq[0], venc, volImpl);
    else if (tese === "alta" || tese === "alta_com_caixa") prob = probAcima(S, eq[0], venc, volImpl);
    else prob = 1 - probAcima(S, eq[0], venc, volImpl);
    return { tese, estrutura: NOMES[tese], pernas, lotes, dias: venc, premio: r2(premio * lotes), perdaMax: r2(perda1 * lotes), ganhoMax: ganho1 === null ? null : r2(ganho1 * lotes),
      equilibrio: eq.map(r2), probImplicita: Math.round(prob * 1000) / 1000, custoTotal: r2(custo * lotes), alvo: alvo === null ? null : r2(alvo * lotes), stop: r2(stop * lotes), saidaDias: 7 };
  }

  const brl0 = (v) => "R$ " + Math.round(v).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  const brl2 = (v) => "R$ " + v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Compra por sinal externo (entrada, alvo, prazo até o alvo). Espelha montar_sinal de montador.py.
  function montarSinal(S, chain, volImpl, perdaAceita, entrada, alvo, prazoDias, o = {}) {
    const estrutura = o.estrutura ?? "trava", caixa = o.caixa ?? 0, tol = o.tolEntrada ?? 0.02, margem = o.margemPrazo ?? 10, minRR = o.minRR ?? 1.0,
      spreadMax = o.spreadMax ?? 0.10, volMin = o.volMin ?? 500, stopFrac = o.stopFrac ?? 0.70, alvoFrac = o.alvoFrac ?? 0.50;
    if (alvo <= entrada) return "Sinal inválido: o alvo precisa estar acima do preço de entrada.";
    if (S > entrada * (1 + tol)) return "Aguardar: o preço " + brl2(S) + " ainda está acima da entrada do sinal (" + brl2(entrada) + ").";
    if (S >= alvo) return "O preço " + brl2(S) + " já atingiu o alvo do sinal (" + brl2(alvo) + ").";
    const dmin = prazoDias + margem;
    const dias = [...new Set(chain.filter((x) => x.d >= dmin && x.d <= dmin + 35).map((x) => x.d))].sort((a, b) => a - b);
    if (!dias.length) return "Sem vencimento depois do prazo do sinal (" + prazoDias + " dias, mais margem de " + margem + ").";
    let motivo = "Sem opções líquidas para esta estrutura.";
    for (const d of dias) {
      const ch = chain.filter((x) => x.d === d), C = liquidas(ch, "C", spreadMax, volMin), P = liquidas(ch, "P", spreadMax, volMin);
      let pernas, est, tese, p = null;
      if (estrutura === "put") {
        p = perto(P.filter((x) => x.k <= S), entrada); if (!p) continue;
        const caixa1 = p.k * LOTE;
        if (caixa < caixa1) { motivo = "Falta caixa: a put vendida exige reservar " + brl0(caixa1) + "."; continue; }
        pernas = [[-1, p]]; est = "Put vendida no preço de entrada do sinal"; tese = "sinal_put";
      } else {
        const a = perto(C, S), b = perto(C.filter((x) => x.k >= alvo && x.k <= alvo * 1.05), alvo);
        if (!a || !b || b.k <= a.k) { motivo = "Sem call líquida no alvo do sinal (" + brl2(alvo) + ") ou até 5% acima."; continue; }
        pernas = [[1, a], [-1, b]]; est = "Trava de alta até o alvo do sinal"; tese = "sinal_alta";
      }
      const cred = pernas.reduce((s, [l, x]) => s + -l * preco(x, l), 0), premio = -cred * LOTE;
      const premioMid = -pernas.reduce((s, [l, x]) => s + -l * mid(x), 0) * LOTE;
      const [perda1, ganho1, eq] = payoff(tese === "sinal_put" ? "alta_com_caixa" : "alta", pernas, premio);
      let lotes, stop;
      if (tese === "sinal_alta") {
        if (perda1 <= 0 || ganho1 / perda1 < minRR) { motivo = "A trava custa " + brl0(perda1) + " para ganhar no máximo " + brl0(ganho1) + ": ganho máximo menor que o risco."; continue; }
        lotes = Math.floor(perdaAceita / perda1); stop = -stopFrac * perda1;
        if (lotes < 1) { motivo = "A menor operação arrisca " + brl0(perda1) + ", acima do seu limite de " + brl0(perdaAceita) + "."; continue; }
      } else { lotes = Math.floor(caixa / (p.k * LOTE)); stop = -Math.min(stopFrac * perda1, perdaAceita); }
      const taxas = pernas.reduce((s, [l, x]) => s + TAXA_B3 * mid(x) * LOTE, 0) * 2, custo = Math.abs(premio - premioMid) + taxas + fixo(pernas.length);
      const prob = probAcima(S, eq[0], d, volImpl);
      return { tese, estrutura: est, pernas, lotes, dias: d, premio: r2(premio * lotes), perdaMax: r2(perda1 * lotes), ganhoMax: r2(ganho1 * lotes), equilibrio: eq.map(r2),
        probImplicita: Math.round(prob * 1000) / 1000, custoTotal: r2(custo * lotes), alvo: r2(alvoFrac * ganho1 * lotes), stop: r2(stop * lotes), saidaDias: 7 };
    }
    return motivo;
  }

  // --- delta de Black-Scholes pelo preço de mercado (juro 10% a.a.), usado só nos perfis da compra simples ---
  const R_BS = 0.10;
  const bsPreco = (S, K, T, v, tipo) => { const d1 = (Math.log(S / K) + (R_BS + v * v / 2) * T) / (v * Math.sqrt(T)), d2 = d1 - v * Math.sqrt(T);
    return tipo === "C" ? S * N(d1) - K * Math.exp(-R_BS * T) * N(d2) : K * Math.exp(-R_BS * T) * N(-d2) - S * N(-d1); };
  const ivOpt = (S, o) => { const T = o.d / 365, p = mid(o); let lo = 0.02, hi = 3;
    if (!(p > 0) || bsPreco(S, o.k, T, hi, o.t) < p || bsPreco(S, o.k, T, lo, o.t) > p) return null;
    for (let i = 0; i < 60; i++) { const mdl = (lo + hi) / 2; if (bsPreco(S, o.k, T, mdl, o.t) < p) lo = mdl; else hi = mdl; }
    return (lo + hi) / 2; };
  const deltaAbs = (S, o) => { const v = ivOpt(S, o); if (v === null) return null; const T = o.d / 365, d1 = (Math.log(S / o.k) + (R_BS + v * v / 2) * T) / (v * Math.sqrt(T));
    return o.t === "C" ? N(d1) : 1 - N(d1); };
  // theta por ação por dia corrido (R$ que a opção perde por dia se nada mudar), pela IV do próprio preço
  const thetaDia = (S, o) => { const v = ivOpt(S, o); if (v === null) return null; const T = o.d / 365, K = o.k, sq = Math.sqrt(T),
      d1 = (Math.log(S / K) + (R_BS + v * v / 2) * T) / (v * sq), d2 = d1 - v * sq, pdf = Math.exp(-d1 * d1 / 2) / Math.sqrt(2 * Math.PI);
    const th = o.t === "C" ? -S * pdf * v / (2 * sq) - R_BS * K * Math.exp(-R_BS * T) * N(d2) : -S * pdf * v / (2 * sq) + R_BS * K * Math.exp(-R_BS * T) * N(-d2);
    return -th / 365; };
  const PERFIS = { maior: 0.20, eq: 0.42, freq: 0.72 }; // delta-alvo de cada perfil da compra simples
  // Aposta simples: call ATM (alta) ou put ATM (baixa), só opções muito líquidas. Espelha montar_aposta de montador.py.
  function montarAposta(lado, S, chain, volImpl, valor, o = {}) {
    const prazoAlvo = o.prazoAlvo ?? 45, spreadMax = o.spreadMax ?? (o.perfil === "freq" ? 0.15 : 0.10), volMin = o.volMin ?? 1000, jan = o.jan ?? 0.05, tipo = lado === "alta" ? "C" : "P";
    const dias = [...new Set(chain.filter((x) => x.d >= Math.max(prazoAlvo - 15, 7) && x.d <= prazoAlvo + 15).map((x) => x.d))].sort((a, b) => Math.abs(a - prazoAlvo) - Math.abs(b - prazoAlvo) || a - b);
    let esc = null;
    if (o.perfil && PERFIS[o.perfil] !== undefined) {
      const alvoD = PERFIS[o.perfil];
      for (const d of dias) {
        const L = liquidas(chain.filter((x) => x.d === d), tipo, spreadMax, volMin).filter((y) => Math.abs(y.k / S - 1) <= 0.20);
        let best = null;
        for (const y of L) { const dl = deltaAbs(S, y); if (dl === null) continue; const gap = Math.abs(dl - alvoD); if (gap <= (o.tolDelta ?? (o.perfil === "freq" ? 0.15 : 0.12)) && (!best || gap < best.gap || (gap === best.gap && spread(y) < spread(best.o)))) best = { o: y, gap }; }
        if (best) { esc = best.o; break; }
      }
    } else
    for (const d of dias) { const L = liquidas(chain.filter((x) => x.d === d), tipo, spreadMax, volMin); const x = perto(L.filter((y) => Math.abs(y.k / S - 1) <= jan), S); if (x) { esc = x; break; } }
    if (!esc) return "Sem opção muito líquida perto do preço atual neste prazo.";
    const custo1 = esc.a * LOTE, lotes = Math.floor(valor / custo1);
    if (lotes < 1) return "A menor operação custa " + brl0(custo1) + ", acima do valor máximo que você definiu (" + brl0(valor) + ").";
    const prem = esc.a; let ganho, eq, prob, est, tese;
    if (tipo === "C") { ganho = null; eq = [esc.k + prem]; prob = probAcima(S, eq[0], esc.d, volImpl); est = "Call comprada (posição de alta)"; tese = "aposta_alta"; }
    else { ganho = (esc.k - prem) * LOTE * lotes; eq = [esc.k - prem]; prob = 1 - probAcima(S, eq[0], esc.d, volImpl); est = "Put comprada (posição de baixa)"; tese = "aposta_baixa"; }
    const custo = (esc.a - mid(esc)) * LOTE + TAXA_B3 * mid(esc) * LOTE * 2 + fixo(1), perda = prem * LOTE * lotes;
    return { tese, estrutura: est, pernas: [[1, esc]], lotes, dias: esc.d, premio: r2(perda), perdaMax: r2(perda), ganhoMax: ganho === null ? null : r2(ganho), equilibrio: eq.map(r2),
      probImplicita: Math.round(prob * 1000) / 1000, custoTotal: r2(custo * lotes), alvo: null, stop: null, saidaDias: 0, thetaDia: (() => { const t = thetaDia(S, esc); return t === null ? null : r2(t * LOTE * lotes); })() };
  }
  // resultado no vencimento para um preço final da ação (por todos os lotes)
  function resultadoNoVencimento(m, ST) {
    let pay = 0;
    for (const [l, x] of m.pernas) { const v = x.t === "C" ? Math.max(ST - x.k, 0) : Math.max(x.k - ST, 0); pay += l * v; }
    return r2((pay * LOTE - m.premio / m.lotes) * m.lotes);
  }
  const api = { setCorretagem, montar, montarSinal, montarAposta, probAcima, resultadoNoVencimento };
  if (typeof module !== "undefined") module.exports = api; else root.Montador = api;
})(typeof window !== "undefined" ? window : globalThis);
