// Port de montador.py (mesmas regras). Funciona no navegador (window.Montador) e no Node (module.exports).
(function (root) {
  const TAXA_B3 = 0.00134, LOTE = 100;
  const SPREAD_MAX = 0.20; // spread máximo (venda − compra) / médio, no fechamento; era 10% (15% no Lucro frequente) até 02/11/2026
  // Corretagem do usuário (R$ por ordem). null = não informada: o custo não soma corretagem (até 03/11/2026 havia uma margem fixa).
  let CORRETAGEM = null;
  const setCorretagem = (v) => { CORRETAGEM = (v === null || v === undefined || isNaN(+v) || +v < 0) ? null : +v; };
  // corretagem por ordem: cada perna, na entrada e na saída; não cresce com os lotes
  const fixo = (n) => CORRETAGEM === null ? 0 : CORRETAGEM * n * 2;
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
  // Trava com preços de fechamento impossíveis (ex.: opção de outro papel com o mesmo prefixo, ou preço parado): entrada
  // com crédito, ou débito igual ou maior que a distância entre os strikes. Devolve a mensagem, ou null. Espelha _inconsistente.
  const inconsistente = (pernas) => {
    const a = pernas[0][1], b = pernas[1][1], deb = (a.a - b.b) * LOTE, larg = Math.abs(b.k - a.k) * LOTE, par = "comprar " + a.s + " e vender " + b.s;
    if (deb <= 0) return "Preços de fechamento inconsistentes: " + par + (deb < 0 ? " daria crédito de " + brl0(-deb) : " não teria custo") + ". O app não monta esta operação com esses preços.";
    if (deb >= larg) return "Preços de fechamento inconsistentes: " + par + " custaria " + brl0(deb) + ", e a trava paga no máximo " + brl0(larg) + ". O app não monta esta operação com esses preços.";
    return null;
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
  // custos da operação (R$): spread em relação ao preço médio (já está no prêmio) e taxas da B3 de entrada e saída, por lote;
  // corretagem cadastrada, por ordem (0 sem cadastro). custoTotal = soma dos três.
  const custos = (spread1, taxas1, n, lotes) => {
    const s = spread1 * lotes, t = taxas1 * lotes, f = fixo(n);
    return { custoSpread: r2(s), custoTaxas: r2(t), custoFixo: r2(f), custoTotal: r2(s + t + f) };
  };
  function montar(tese, S, chain, volImpl, perdaAceita, o = {}) {
    const prazoAlvo = o.prazoAlvo ?? 45, caixa = o.caixa ?? 0, spreadMax = o.spreadMax ?? SPREAD_MAX, volMin = o.volMin ?? 500, stopFrac = o.stopFrac ?? 0.70, alvoFrac = o.alvoFrac ?? 0.50;
    const jmin = Math.max(prazoAlvo - 15, 7), jmax = prazoAlvo + 15;
    const dias = [...new Set(chain.filter((x) => x.d >= jmin && x.d <= jmax).map((x) => x.d))].sort((a, b) => Math.abs(a - prazoAlvo) - Math.abs(b - prazoAlvo) || a - b);
    let venc = null, pernas = null, incons = null;
    for (const d of dias) {
      const p = escolher(tese, S, chain.filter((x) => x.d === d), spreadMax, volMin); if (!p) continue;
      const inc = tese === "alta" || tese === "baixa" ? inconsistente(p) : null; if (inc) { incons = incons ?? inc; continue; }   // tenta o próximo vencimento
      venc = d; pernas = p; break;
    }
    if (venc === null) return incons ?? "Sem opções líquidas no prazo pedido. Tente outro prazo ou outro ativo.";
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
    const alvo = ganho1 === null ? null : alvoFrac * ganho1;
    let prob;
    if (tese === "forte") prob = probAcima(S, eq[1], venc, volImpl) + 1 - probAcima(S, eq[0], venc, volImpl);
    else if (tese === "alta" || tese === "alta_com_caixa") prob = probAcima(S, eq[0], venc, volImpl);
    else prob = 1 - probAcima(S, eq[0], venc, volImpl);
    return { tese, estrutura: NOMES[tese], pernas, lotes, dias: venc, premio: r2(premio * lotes), perdaMax: r2(perda1 * lotes), ganhoMax: ganho1 === null ? null : r2(ganho1 * lotes),
      equilibrio: eq.map(r2), probImplicita: Math.round(prob * 1000) / 1000, ...custos(Math.abs(premio - premioMid), taxas, pernas.length, lotes), alvo: alvo === null ? null : r2(alvo * lotes), stop: r2(stop * lotes), saidaDias: 7 };
  }

  const brl0 = (v) => "R$ " + Math.round(v).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  const brl2 = (v) => "R$ " + v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Compra por sinal externo (entrada, alvo, prazo até o alvo). Espelha montar_sinal de montador.py.
  function montarSinal(S, chain, volImpl, perdaAceita, entrada, alvo, prazoDias, o = {}) {
    const estrutura = o.estrutura ?? "trava", caixa = o.caixa ?? 0, tol = o.tolEntrada ?? 0.02, margem = o.margemPrazo ?? 10, minRR = o.minRR ?? 1.0,
      spreadMax = o.spreadMax ?? SPREAD_MAX, volMin = o.volMin ?? 500, stopFrac = o.stopFrac ?? 0.70, alvoFrac = o.alvoFrac ?? 0.50;
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
        const inc = inconsistente(pernas); if (inc) { motivo = inc; continue; }
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
      const taxas = pernas.reduce((s, [l, x]) => s + TAXA_B3 * mid(x) * LOTE, 0) * 2;
      const prob = probAcima(S, eq[0], d, volImpl);
      return { tese, estrutura: est, pernas, lotes, dias: d, premio: r2(premio * lotes), perdaMax: r2(perda1 * lotes), ganhoMax: r2(ganho1 * lotes), equilibrio: eq.map(r2),
        probImplicita: Math.round(prob * 1000) / 1000, ...custos(Math.abs(premio - premioMid), taxas, pernas.length, lotes), alvo: r2(alvoFrac * ganho1 * lotes), stop: r2(stop * lotes), saidaDias: 7 };
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
    const prazoAlvo = o.prazoAlvo ?? 45, spreadMax = o.spreadMax ?? SPREAD_MAX, volMin = o.volMin ?? 1000, jan = o.jan ?? 0.05, tipo = lado === "alta" ? "C" : "P";
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
    const perda = prem * LOTE * lotes;
    return { tese, estrutura: est, pernas: [[1, esc]], lotes, dias: esc.d, premio: r2(perda), perdaMax: r2(perda), ganhoMax: ganho === null ? null : r2(ganho), equilibrio: eq.map(r2),
      probImplicita: Math.round(prob * 1000) / 1000, ...custos((esc.a - mid(esc)) * LOTE, TAXA_B3 * mid(esc) * LOTE * 2, 1, lotes), alvo: null, stop: null, saidaDias: 0, thetaDia: (() => { const t = thetaDia(S, esc); return t === null ? null : r2(t * LOTE * lotes); })() };
  }
  // Operação real: a montagem refeita com o preço executado de cada perna (R$ por opção, na ordem de m.pernas) e a
  // quantidade de lotes da nota. Prêmio, risco, ganho e equilíbrio vêm dos preços executados; alvo e limite são os da
  // montagem, na proporção dos lotes. Espelha execucao do montador.py.
  function execucao(m, ex) {
    const lotes = ex.lotes, pr = ex.precos;
    const pernas = m.pernas.map(([l, x], i) => [l, l > 0 ? { ...x, a: pr[i] } : { ...x, b: pr[i] }]);
    const premio1 = pernas.reduce((s, [l], i) => s + l * pr[i], 0) * LOTE;
    let perda1, ganho1, eq;
    if (m.tese === "aposta_alta" || m.tese === "aposta_baixa") {
      const x = pernas[0][1], p = pr[0]; perda1 = p * LOTE;
      if (x.t === "C") { ganho1 = null; eq = [x.k + p]; } else { ganho1 = (x.k - p) * LOTE; eq = [x.k - p]; }
    } else [perda1, ganho1, eq] = payoff(m.tese === "sinal_put" ? "alta_com_caixa" : m.tese === "sinal_alta" ? "alta" : m.tese, pernas, premio1);
    const prop = lotes / m.lotes;
    return { ...m, pernas, lotes, premio: r2(premio1 * lotes), perdaMax: r2(perda1 * lotes), ganhoMax: ganho1 === null ? null : r2(ganho1 * lotes),
      equilibrio: eq.map(r2), alvo: m.alvo === null ? null : r2(m.alvo * prop), stop: m.stop === null ? null : r2(m.stop * prop), real: true };
  }
  // resultado no vencimento para um preço final da ação (por todos os lotes)
  function resultadoNoVencimento(m, ST) {
    let pay = 0;
    for (const [l, x] of m.pernas) { const v = x.t === "C" ? Math.max(ST - x.k, 0) : Math.max(x.k - ST, 0); pay += l * v; }
    return r2((pay * LOTE - m.premio / m.lotes) * m.lotes);
  }
  // --- Movimento necessário × oscilação típica (bloco "Movimento e tempo"; só informação, sem veredito) ---
  // fech: {data ISO: fechamento} do papel; ate: data dos preços. Retornos log dos últimos 60 pregões (61 fechamentos até
  // `ate`), desvio-padrão amostral anualizado por √252. Com menos de 21 fechamentos: null. Espelha vol_real_60 do montador.py.
  function volReal60(fech, ate) {
    const ds = Object.keys(fech || {}).filter((d) => d <= ate).sort().slice(-61); if (ds.length < 21) return null;
    const r = []; for (let i = 1; i < ds.length; i++) r.push(Math.log(fech[ds[i]] / fech[ds[i - 1]]));
    const mu = r.reduce((a, b) => a + b, 0) / r.length, sd = Math.sqrt(r.reduce((a, b) => a + (b - mu) * (b - mu), 0) / (r.length - 1));
    return sd * Math.sqrt(252);
  }
  // --- Tendência do papel (só histórico; colore o minigráfico). Janela: os últimos 150 pregões até `ate` com fechamento,
  // máxima e mínima (maxmin[data] = [máxima, mínima]). Alta: fechamento > média de 21 > média de 50, média de 50 acima da de 5 pregões antes, ADX(14) >= 20
  // (e, com comIfr, IFR(14) > 50). Queda: o espelho (IFR < 50). Senão, neutro. ADX e IFR pelo método de Wilder.
  // Com menos de 60 pregões na janela: null. Espelha tendencia do montador.py (mesma ordem das contas).
  function tendencia(fech, maxmin, ate, comIfr) {
    if (!maxmin) return null;
    const ds = Object.keys(fech || {}).filter((d) => d <= ate && maxmin[d] !== undefined).sort().slice(-150);
    if (ds.length < 60) return null;
    const c = ds.map((d) => fech[d]), h = ds.map((d) => maxmin[d][0]), l = ds.map((d) => maxmin[d][1]), u = c.length - 1;
    const media = (ini, fim) => { let s = 0; for (let i = ini; i <= fim; i++) s += c[i]; return s / (fim - ini + 1); };
    const mm21 = media(u - 20, u), mm50 = media(u - 49, u), mm50ant = media(u - 54, u - 5);
    let sTR = 0, sP = 0, sN = 0, adx = null, somaDX = 0, nDX = 0, gm = 0, pm = 0;
    for (let i = 1; i <= u; i++) {
      const tr = Math.max(h[i] - l[i], Math.abs(h[i] - c[i - 1]), Math.abs(l[i] - c[i - 1]));
      const up = h[i] - h[i - 1], dn = l[i - 1] - l[i], pdm = up > dn && up > 0 ? up : 0, ndm = dn > up && dn > 0 ? dn : 0;
      const ch = c[i] - c[i - 1], g = ch > 0 ? ch : 0, p = ch < 0 ? -ch : 0;
      if (i <= 14) { sTR += tr; sP += pdm; sN += ndm; gm += g; pm += p; if (i === 14) { gm /= 14; pm /= 14; } }
      else { sTR = sTR - sTR / 14 + tr; sP = sP - sP / 14 + pdm; sN = sN - sN / 14 + ndm; gm = (gm * 13 + g) / 14; pm = (pm * 13 + p) / 14; }
      if (i >= 14) {
        const pdi = sTR > 0 ? 100 * sP / sTR : 0, ndi = sTR > 0 ? 100 * sN / sTR : 0, dx = pdi + ndi > 0 ? 100 * Math.abs(pdi - ndi) / (pdi + ndi) : 0;
        if (nDX < 14) { somaDX += dx; nDX++; if (nDX === 14) adx = somaDX / 14; } else adx = (adx * 13 + dx) / 14;
      }
    }
    const ifr = pm === 0 ? 100 : 100 - 100 / (1 + gm / pm);
    const forte = adx !== null && adx >= 20;
    const alta = forte && c[u] > mm21 && mm21 > mm50 && mm50 > mm50ant && (!comIfr || ifr > 50);
    const queda = forte && c[u] < mm21 && mm21 < mm50 && mm50 < mm50ant && (!comIfr || ifr < 50);
    return { classe: alta ? "alta" : queda ? "queda" : "neutro", mm21, mm50, mm50ant, adx, ifr };
  }
  // Quanto a ação precisa andar até o (primeiro) ponto de equilíbrio e quanto costuma oscilar no prazo da operação, em fração.
  function movimentoNecessario(m, S, fech, ate) {
    const vr = volReal60(fech, ate);
    return { precisa: Math.abs(m.equilibrio[0] / S - 1), oscilacao: vr === null ? null : vr * Math.sqrt(m.dias / 365), volReal60: vr };
  }
  // --- Marcação diária: valor de hoje e regras de saída, com os preços de fechamento de cada pregão ---
  const addDiasISO = (iso, n) => { const d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  // Resultado (R$, todos os lotes) se a operação fosse desfeita no fechamento de um dia: o lado comprado vende pela melhor
  // compra e o vendido recompra pela melhor venda (o lado pior, como na montagem). precos: {símbolo: [compra, venda]}.
  // null se faltar preço de alguma perna naquele dia.
  function resultadoNoDia(m, precos) {
    let v = 0;
    for (const [l, x] of m.pernas) { const p = precos && precos[x.s]; if (!p || !(p[0] > 0) || !(p[1] >= p[0])) return null; v += l > 0 ? p[0] : -p[1]; }
    return r2(v * LOTE * m.lotes - m.premio);
  }
  // Primeira regra de saída atingida nos fechamentos depois da entrada e antes do vencimento: alvo (resultado >= alvo),
  // limite (resultado <= stop) ou prazo (a partir de `saidaDias` antes do vencimento). marcas: [{d, r}] em ordem de data,
  // r = resultadoNoDia ou null (dia sem preço: pulado). Devolve {regra, d, r} ou null (nenhuma regra até o último dia).
  function regraDeSaida(m, marcas, venc) {
    const prazo = m.saidaDias > 0 ? addDiasISO(venc, -m.saidaDias) : null;
    for (const { d, r } of marcas) {
      if (r === null || d >= venc) continue;
      if (m.alvo !== null && m.alvo !== undefined && r >= m.alvo) return { regra: "alvo", d, r };
      if (m.stop !== null && m.stop !== undefined && r <= m.stop) return { regra: "limite", d, r };
      if (prazo && d >= prazo) return { regra: "prazo", d, r };
    }
    return null;
  }
  const api = { setCorretagem, montar, montarSinal, montarAposta, execucao, probAcima, resultadoNoVencimento, volReal60, tendencia, movimentoNecessario, resultadoNoDia, regraDeSaida };
  if (typeof module !== "undefined") module.exports = api; else root.Montador = api;
})(typeof window !== "undefined" ? window : globalThis);
