// Vaglio ao vivo: cotações do pregão, de qualquer fornecedor, e as regras de saída conferidas a cada cotação nova.
// O mesmo código roda no app e num servidor Node (para conferir com o app fechado e mandar a notificação).
//
// Fonte de cotações: o que cada fornecedor precisa implementar (o resto do app não muda ao trocar de fornecedor).
//   { nome, abrir(pedidos, aoReceber) -> fechar() }
//   pedidos: [{s, ativo, k, t, venc}]: o símbolo da opção; ativo, strike, tipo e vencimento só a fonte simulada usa.
//   aoReceber(s, [melhor compra, melhor venda, qtd na compra, qtd na venda], hora): qtds opcionais; hora: Date.
//
// Vigia: guarda o livro (a última cotação de cada símbolo) e, a cada cotação, refaz o "se encerrar agora" das operações
// que usam o símbolo (Montador.resultadoAgora: preço de execução, com as taxas da saída) e confere as regras de saída
// (Montador.regraDeSaida: alvo, limite, prazo). Avisa aoMudar({id, r, hora}) a cada valor novo e aoDisparar({id, regra,
// r, hora}) uma vez por operação, na primeira cotação que atinge uma regra.
(function (root) {
  const M = root.Montador || (typeof require === "function" ? require("./montador.js") : null);
  const isoLocal = (h) => new Date(h.getTime() - h.getTimezoneOffset() * 60000).toISOString().slice(0, 10);

  // ops: [{id, m, ativo, venc, forcar?}] (m: a montagem, ou a execução, de cada operação aberta; venc: AAAA-MM-DD)
  function vigia(fonte, ops, ev) {
    ev = ev || {};
    const livro = {}, porSimb = new Map(), disparou = new Set(), agora = new Map(), pedidos = [];
    for (const o of ops) for (const [, x] of o.m.pernas) {
      if (!porSimb.has(x.s)) { porSimb.set(x.s, []); pedidos.push({ s: x.s, ativo: o.ativo, k: x.k, t: x.t, venc: o.venc }); }
      porSimb.get(x.s).push(o);
    }
    const receber = (s, p, hora) => {
      livro[s] = p; const h = hora || new Date();
      for (const o of porSimb.get(s) || []) {
        const r = M.resultadoAgora(o.m, livro); if (r === null) continue;
        agora.set(o.id, { r, hora: h }); if (ev.aoMudar) ev.aoMudar({ id: o.id, r, hora: h });
        if (disparou.has(o.id)) continue;
        // forcar: regra que já disparou num fechamento sem pregão acompanhado: sai na primeira cotação executável
        const rg = o.forcar ? { regra: o.forcar } : M.regraDeSaida(o.m, [{ d: isoLocal(h), r }], o.venc);
        if (rg) { disparou.add(o.id); if (ev.aoDisparar) ev.aoDisparar({ id: o.id, regra: rg.regra, r, hora: h }); }
      }
    };
    const fechar = pedidos.length ? fonte.abrir(pedidos, receber) : () => {};
    return { livro, agora, fechar, receber };
  }

  // Ordem para encerrar agora, perna por perna: o que o cliente digita na corretora hoje e o que a API de uma corretora
  // parceira vai receber. Mesmos preços do resultadoAgora (vende a comprada no melhor comprador, recompra a vendida no
  // melhor vendedor). null se faltar preço.
  function ordemDeSaida(m, livro) {
    const q = 100 * m.lotes, o = [];
    for (const [l, x] of m.pernas) { const p = livro && livro[x.s], px = p && (l > 0 ? p[0] : p[1]); if (!(px > 0)) return null;
      o.push({ s: x.s, lado: l > 0 ? "venda" : "compra", qtd: q, preco: px }); }
    return o;
  }

  // --- Fonte simulada: para testar o app sem fornecedor. Não é dado de mercado. ---
  // O pregão anda a partir do último fechamento: a ação segue um passeio aleatório (com rumo opcional, para
  // demonstração) e cada opção é reprecificada por Black-Scholes com a volatilidade implícita do seu fechamento,
  // mantendo o spread do fechamento, em reais. Cada cotação representa `minutos` de pregão.
  // o: {base: {s: [compra, venda]}, spot: {ativo: preço}, juro (contínuo, ao ano), passo (ms entre cotações),
  //     minutos (de pregão por cotação), vol (da ação, ao ano), rumo (variação da ação por pregão, ex. 0.04), semente}
  const N = (x) => { const t = 1 / (1 + 0.2316419 * Math.abs(x)), d = 0.3989422804 * Math.exp(-x * x / 2),
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); return x > 0 ? 1 - p : p; };
  function bs(S, K, T, r, v, tipo) {
    if (T <= 0 || v <= 0) return Math.max(tipo === "C" ? S - K : K - S, 0);
    const d1 = (Math.log(S / K) + (r + v * v / 2) * T) / (v * Math.sqrt(T)), d2 = d1 - v * Math.sqrt(T);
    return tipo === "C" ? S * N(d1) - K * Math.exp(-r * T) * N(d2) : K * Math.exp(-r * T) * N(-d2) - S * N(-d1);
  }
  function volImplicita(preco, S, K, T, r, tipo) {
    let a = 0.01, b = 3;
    if (!(preco > 0) || bs(S, K, T, r, a, tipo) > preco || bs(S, K, T, r, b, tipo) < preco) return null;
    for (let i = 0; i < 60; i++) { const c = (a + b) / 2; if (bs(S, K, T, r, c, tipo) > preco) b = c; else a = c; }
    return (a + b) / 2;
  }
  function aleatorio(semente) {   // mulberry32: a mesma semente dá o mesmo pregão (testes e prints)
    let s = semente >>> 0;
    return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function simulada(o) {
    const passo = o.passo ?? 1500, minutos = o.minutos ?? 5, vol = o.vol ?? 0.35, rumo = o.rumo ?? 0, juro = o.juro ?? 0.11;
    const rnd = aleatorio(o.semente ?? Date.now()), gauss = () => Math.sqrt(-2 * Math.log(1 - rnd())) * Math.cos(2 * Math.PI * rnd());
    const fracDia = minutos / 420, dt = fracDia / 252;   // pregão de 7 horas; 252 pregões no ano
    // a ação continua de onde parou quando o app reabre a fonte (operação nova): o pregão não volta ao fechamento
    const spot = Object.assign({}, o.spot), hoje = new Date(), anos = (venc) => Math.max((new Date(venc + "T17:00:00") - hoje) / 864e5, 0.5) / 365;
    return {
      nome: "Simulada",
      abrir(pedidos, aoReceber) {
        const ops = pedidos.map((p) => { const b = o.base[p.s], S = spot[p.ativo]; if (!b || !(S > 0)) return null;
          const mid = (b[0] + b[1]) / 2, T = anos(p.venc), iv = volImplicita(mid, o.spot[p.ativo], p.k, T, juro, p.t) ?? 0.35;
          return { ...p, T, iv, meio: Math.max((b[1] - b[0]) / 2, 0.005) }; }).filter(Boolean);
        let t0 = hoje.getTime();
        const tique = () => {
          for (const a of new Set(ops.map((x) => x.ativo))) spot[a] *= Math.exp(rumo * fracDia - vol * vol * dt / 2 + vol * Math.sqrt(dt) * gauss());
          const h = new Date(t0 = Math.max(t0 + passo, Date.now()));
          for (const x of ops) {
            const mid = Math.max(bs(spot[x.ativo], x.k, x.T, juro, x.iv, x.t), 0.01), meio = x.meio;
            const r2 = (v) => Math.max(Math.round(v * 100) / 100, 0.01), q = () => 100 * (5 + Math.floor(rnd() * 46));
            aoReceber(x.s, [r2(mid - meio), Math.max(r2(mid + meio), r2(mid - meio) + 0.01), q(), q()], h);
          }
        };
        tique(); const id = setInterval(tique, passo);
        return () => clearInterval(id);
      },
    };
  }

  const api = { vigia, simulada, ordemDeSaida, isoLocal, bs, volImplicita };
  if (typeof module !== "undefined") module.exports = api; else root.AoVivo = api;
})(typeof window !== "undefined" ? window : globalThis);
