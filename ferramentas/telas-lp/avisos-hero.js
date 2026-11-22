const M = require("../../montador.js"), A = require("../../aovivo.js");
const dia = require("../../pwa/snapshot.json").por_data["2026-11-19"], juro = 0.11;
// "se encerrar agora" com a ação em S2, depois de `passados` dias (mesma vol implícita do fechamento, mesmo spread em reais)
const agora = (m, S0, S2, passados = 0) => { const livro = {};
  for (const [, x] of m.pernas) { const T0 = x.d / 365, T = Math.max(x.d - passados, 0.5) / 365, iv = A.volImplicita((x.b + x.a) / 2, S0, x.k, T0, juro, x.t) ?? 0.35, meio = Math.max((x.a - x.b) / 2, 0.005), mid = Math.max(A.bs(S2, x.k, T, juro, iv, x.t), 0.01), r2 = (v) => Math.max(Math.round(v * 100) / 100, 0.01);
    livro[x.s] = [r2(mid - meio), Math.max(r2(mid + meio), r2(mid - meio) + 0.01), 1e7, 1e7]; }
  return M.resultadoAgora(m, livro); };
const mont = (ativo, tese, perda) => { const a = dia[ativo]; return [a, M.montar(tese, a.S, a.chain, a.iv, perda, { prazoAlvo: 30, caixa: 1e9, perfil: "maior" })]; };
for (const [ativo, tese, perda] of [["PETR4","alta",2000],["VALE3","alta",2000],["VALE3","alta",2200],["ITUB4","alta",2000],["BBAS3","alta",2000],["BBAS3","baixa",2000],["BBDC4","alta",2000]]) {
  const [a, m] = mont(ativo, tese, perda); if (!m || !m.pernas) { console.log(ativo, tese, "nada"); continue; }
  const s = tese === "alta" ? 1 : -1, out = [`${ativo} ${tese} ${m.lotes}L risco ${m.perdaMax} ganho ${m.ganhoMax} alvo ${m.alvo} S ${a.S}`];
  out.push(`3% hoje: ${agora(m, a.S, a.S * (1 + s * 0.03))}`, `4% hoje: ${agora(m, a.S, a.S * (1 + s * 0.04))}`);
  for (const t of [10, 15, 20]) { for (let k = 1; k <= 15; k++) { const r = agora(m, a.S, a.S * (1 + s * k / 100), t); if (r >= m.alvo) { out.push(`alvo em ${t}d com ${k}%: ${r}`); break; } } }
  console.log(out.join(" | "));
}
