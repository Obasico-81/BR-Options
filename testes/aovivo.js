// Ao vivo: "se encerrar agora" pelo preço de execução (montador), o vigia que confere as regras a cada cotação e a fonte
// simulada (aovivo.js); depois o app servido por HTTP com ?aovivo=sim: a simulada sai no momento da regra, a real avisa
// e mostra a ordem pronta, e sem fonte nada muda.
// Uso: node testes/aovivo.js   (precisa de python3 e do Playwright; gera pwa/index.html antes: python3 build.py && python3 build_pwa.py)
const path = require("path"), { spawn } = require("child_process");
const RAIZ = path.join(__dirname, ".."), M = require(path.join(RAIZ, "montador.js")), A = require(path.join(RAIZ, "aovivo.js")), snap = require(path.join(RAIZ, "snapshot.json"));
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };
const r2 = (x) => Math.round(x * 100) / 100;

// ---------- 1. contas ----------
// trava de alta em qualquer ativo e prazo que monte no snapshot do dia
const achar = (tese, perda, o) => { for (const [n, x] of Object.entries(snap.ativos)) for (const p of [45, 30, 25, 60, 15, 75, 90]) {
  const m = M.montar(tese, x.S, x.chain, x.iv, perda, { caixa: 1e6, prazoAlvo: p, ...o }); if (typeof m !== "string") return { m, n, x }; } return null; };
const T = achar("alta", 500);
if (!T) { console.log("FALHA nenhuma trava de alta monta no snapshot"); process.exit(1); }
const { m } = T, [[, longa], [, curta]] = m.pernas, q = 100 * m.lotes;
M.setCorretagem(null);
const esperado = (bl, ac) => r2((bl - ac) * q - m.premio - 0.00134 * (bl + ac) * q);
confere("resultadoAgora: vende a comprada no melhor comprador e recompra a vendida no melhor vendedor, com as taxas da B3 da saída",
  M.resultadoAgora(m, { [longa.s]: [2, 2.2], [curta.s]: [0.9, 1.1] }) === esperado(2, 1.1), [M.resultadoAgora(m, { [longa.s]: [2, 2.2], [curta.s]: [0.9, 1.1] }), esperado(2, 1.1)]);
M.setCorretagem(5);
confere("resultadoAgora: com corretagem cadastrada, desconta a da saída (uma ordem por perna)",
  M.resultadoAgora(m, { [longa.s]: [2, 2.2], [curta.s]: [0.9, 1.1] }) === r2(esperado(2, 1.1) - 10));
M.setCorretagem(null);
confere("resultadoAgora: sem piso no risco máximo (é o que se receberia)", M.resultadoAgora(m, { [longa.s]: [0.01, 0.02], [curta.s]: [0.5, 9] }) < -m.perdaMax);
confere("resultadoAgora: quantidade no preço menor que a da operação -> null (preço não executável)",
  M.resultadoAgora(m, { [longa.s]: [2, 2.2, q - 100, q], [curta.s]: [0.9, 1.1, q, q] }) === null);
confere("resultadoAgora: quantidade que cobre a operação -> mesmo valor de sem quantidade",
  M.resultadoAgora(m, { [longa.s]: [2, 2.2, q, 100], [curta.s]: [0.9, 1.1, 100, q] }) === esperado(2, 1.1));
confere("resultadoAgora: perna sem cotação, ou sem o lado que interessa -> null",
  M.resultadoAgora(m, { [longa.s]: [2, 2.2] }) === null && M.resultadoAgora(m, { [longa.s]: [0, 2.2], [curta.s]: [0.9, 1.1] }) === null);
confere("resultadoAgora: sempre abaixo do preço médio (o spread e as taxas pesam contra)",
  M.resultadoAgora(m, { [longa.s]: [2, 2.2], [curta.s]: [0.9, 1.1] }) < M.resultadoNoDia(m, { [longa.s]: [2, 2.2], [curta.s]: [0.9, 1.1] }));
confere("ordemDeSaida: vender a comprada no melhor comprador, comprar a vendida no melhor vendedor, quantidade da operação",
  JSON.stringify(A.ordemDeSaida(m, { [longa.s]: [2, 2.2], [curta.s]: [0.9, 1.1] })) === JSON.stringify([{ s: longa.s, lado: "venda", qtd: q, preco: 2 }, { s: curta.s, lado: "compra", qtd: q, preco: 1.1 }]));

// ---------- 2. vigia, com uma fonte de cotações roteirizada ----------
// cotações que dão um resultado r (pelo preço de execução, sem corretagem): a curta fixa em 1,00 × 1,10
const livroPara = (r) => { const bl = (r + m.premio + 1.1 * q * (1 + 0.00134)) / (q * (1 - 0.00134)); return [[longa.s, [bl, bl + 0.2]], [curta.s, [1, 1.1]]]; };
const roteiro = (seq) => ({ nome: "Roteiro", abrir(pedidos, receber) { this.pedidos = pedidos; let h = new Date("2026-11-20T14:00:00-03:00").getTime();
  for (const r of seq) for (const [s, p] of livroPara(r)) receber(s, p, new Date(h += 1000)); return () => { this.fechado = true; }; } });
const venc = "2026-12-18";
{ const mud = [], disp = [], f = roteiro([0, 50, m.alvo - 30, m.alvo + 20, m.alvo + 40, 10]);
  const v = A.vigia(f, [{ id: 7, m, ativo: T.n, venc }], { aoMudar: (e) => mud.push(e.r), aoDisparar: (e) => disp.push(e) });
  confere("vigia: pede à fonte cada símbolo uma vez, com ativo, strike, tipo e vencimento", f.pedidos.length === 2 && f.pedidos[0].s === longa.s && f.pedidos[0].ativo === T.n && f.pedidos[0].k === longa.k && f.pedidos[0].venc === venc);
  confere("vigia: o alvo dispara uma vez, na primeira cotação que o atinge, com o resultado dela",
    disp.length === 1 && disp[0].regra === "alvo" && disp[0].id === 7 && Math.abs(disp[0].r - (m.alvo + 20)) < 0.05, disp);
  confere("vigia: o 'se encerrar agora' continua mudando depois do aviso", Math.abs(mud[mud.length - 1] - 10) < 0.05 && Math.abs(v.agora.get(7).r - 10) < 0.05, mud.slice(-2));
  v.fechar(); confere("vigia: fechar fecha a fonte", f.fechado === true); }
{ const disp = []; A.vigia(roteiro([-50, -60]), [{ id: 8, m, ativo: T.n, venc, forcar: "alvo" }], { aoDisparar: (e) => disp.push(e) });
  confere("vigia: regra que já disparou num fechamento (forcar) sai na primeira cotação executável", disp.length === 1 && disp[0].regra === "alvo" && Math.abs(disp[0].r + 50) < 0.05, disp); }
{ const disp = []; A.vigia(roteiro([0, 10]), [{ id: 9, m, ativo: T.n, venc: "2026-11-25" }], { aoDisparar: (e) => disp.push(e) });
  confere("vigia: prazo de saída (7 dias antes do vencimento) dispara na abertura", disp.length === 1 && disp[0].regra === "prazo", disp); }
{ const pv = achar("alta_com_caixa", 1e6), disp = [];
  if (!pv) confere("put vendida monta em algum ativo", false);
  else { const [[, x]] = pv.m.pernas, qq = 100 * pv.m.lotes;   // put vendida: recompra pelo melhor vendedor; prêmio < 0 (crédito)
    const f = { abrir(p, receber) { for (const r of [0, pv.m.stop - 5]) { const ac = (-pv.m.premio - r) / (qq * (1 + 0.00134)); receber(x.s, [ac - 0.1, ac], new Date("2026-11-20T15:00:00-03:00")); } return () => {}; } };
    A.vigia(f, [{ id: 10, m: pv.m, ativo: pv.n, venc }], { aoDisparar: (e) => disp.push(e) });
    confere("vigia: put vendida sai no limite pelo preço de recompra", disp.length === 1 && disp[0].regra === "limite" && disp[0].r <= pv.m.stop, [disp, pv.m.stop]); } }

// ---------- 3. fonte simulada ----------
const base = Object.fromEntries(T.x.chain.map((o) => [o.s, [o.b, o.a]]));
const pedidos = m.pernas.map(([, x]) => ({ s: x.s, ativo: T.n, k: x.k, t: x.t, venc }));
const rodar = (semente, n) => new Promise((ok) => { const out = []; const f = A.simulada({ base, spot: { [T.n]: T.x.S }, passo: 5, semente, rumo: 0.2 });
  const fe = f.abrir(pedidos, (s, p) => { out.push([s, ...p]); if (out.length >= n) { fe(); ok(out); } }); });
(async () => {
  const [a1, a2, b1] = await Promise.all([rodar(42, 60), rodar(42, 60), rodar(43, 60)]);
  confere("simulada: a mesma semente dá o mesmo pregão; outra semente, outro", JSON.stringify(a1) === JSON.stringify(a2) && JSON.stringify(a1) !== JSON.stringify(b1));
  confere("simulada: compra < venda, preços positivos, quantidades em lotes de 100", a1.every(([, b, a, qb, qa]) => b > 0 && a > b && qb % 100 === 0 && qa % 100 === 0));
  const prim = a1.filter(([s]) => s === longa.s)[0];
  confere("simulada: a primeira cotação parte do fechamento (perto do preço médio)", Math.abs((prim[1] + prim[2]) / 2 - meio(longa)) < 0.1 * meio(longa) + 0.05, [prim, meio(longa)]);
  confere("simulada: volatilidade implícita do fechamento recupera o preço (Black-Scholes)", (() => { const T_ = 30 / 365, iv = A.volImplicita(1.5, 30, 30, T_, 0.11, "C"); return iv && Math.abs(A.bs(30, 30, T_, 0.11, iv, "C") - 1.5) < 1e-6; })());
  await app();
  console.log(falhas ? `\n${falhas} falha(s)` : "\nTudo certo."); process.exit(falhas ? 1 : 0);
})();
function meio(o) { return (o.b + o.a) / 2; }

// ---------- 4. app servido por HTTP, com a fonte simulada ----------
async function app() {
  const { chromium } = require("playwright");
  const porta = 8900 + Math.floor(Math.random() * 90), dir = path.join(RAIZ, "pwa");
  const srv = spawn("python3", ["-m", "http.server", String(porta), "--bind", "127.0.0.1", "--directory", dir], { stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 800));
  const b = await chromium.launch();
  try {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, locale: "pt-BR", timezoneId: "America/Sao_Paulo" });
    await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
    const p = await ctx.newPage(), erros = []; p.on("pageerror", (e) => erros.push(e.message));
    const prep = (achou) => p.evaluate((n) => { S.data = SNAP.data; S.ativo = n; S.perda = 500; S.capital = 20000;
      for (const v of vencs()) { S.venc = v.iso; S.prazo = v.d; if (typeof montagem("alta") !== "string") break; }
      const m = montagem("alta"), x = M.execucao(m, { lotes: m.lotes, precos: m.pernas.map(([l, o]) => l > 0 ? o.a : o.b) });
      save("estado", S); localStorage.setItem("historico", JSON.stringify([{ m, ativo: n, data: S.data, id: 1 },
        { m: x, ativo: n, data: S.data, id: 2, real: { data: S.data, custos: null, montada: { premio: m.premio, perdaMax: m.perdaMax, lotes: m.lotes } } }])); return m.alvo; }, achou);
    // sem fonte: nada ao vivo
    await p.goto(`http://127.0.0.1:${porta}/index.html?teste=1`); await p.waitForSelector("#nav"); await p.evaluate(() => localStorage.clear());
    await p.reload(); await p.waitForSelector("#nav"); await prep(T.n); await p.reload(); await p.waitForSelector("#nav");
    await p.evaluate(() => { selId = null; tela = "acomp"; render(); }); await p.waitForTimeout(1500);
    confere("app sem fonte: sem selo ao vivo, sem 'se encerrar agora'", (await p.locator(".vivo").count()) === 0 && (await p.locator("[data-agora]").count()) === 0);
    // com a fonte simulada, subindo: a simulada sai no alvo e a real avisa
    await p.goto(`http://127.0.0.1:${porta}/index.html?teste=1&aovivo=sim&semente=5&passo=60&rumo=0.4`); await p.waitForSelector("#nav");
    await p.evaluate(() => { selId = null; tela = "acomp"; render(); });
    await p.waitForSelector(".vivo"); await p.waitForFunction(() => document.querySelectorAll("[data-agora]").length === 2 && [...document.querySelectorAll("[data-agora]")].every((e) => /R\$/.test(e.textContent)), null, { timeout: 15000 }).catch(() => {});
    confere("app ao vivo: selo 'Ao vivo (simulado)' e 'se encerrar agora' nas duas operações", /Ao vivo \(simulado\)/.test(await p.locator(".vivo").first().innerText()) && (await p.locator("[data-agora]").count()) === 2);
    const ok = await p.waitForFunction(() => { const h = load("historico", []); return h.every((o) => o.vivo); }, null, { timeout: 90000 }).then(() => true).catch(() => false);
    const hs = await p.evaluate(() => load("historico", []));
    confere("app ao vivo: as duas atingem o alvo e o momento fica guardado (regra, data, hora, resultado, ordem)", ok && hs.every((o) => o.vivo.regra === "alvo" && o.vivo.d && /^\d\d:\d\d$/.test(o.vivo.hora) && o.vivo.ordem.length === 2), hs.map((o) => o.vivo));
    confere("app ao vivo: aviso na tela", (await p.locator("#aviso-vivo").count()) === 1 && /Alvo atingido/.test(await p.locator("#aviso-vivo").innerText()));
    await p.waitForTimeout(300);
    const lista = await p.locator("#app").innerText();
    confere("app ao vivo: a simulada sai de Em aberto; a real fica, com 'alvo atingido às'", (await p.locator('[data-op="1"]').count()) === 0 && (await p.locator('[data-op="2"]').count()) === 1 && /alvo atingido às \d\d:\d\d/.test(lista));
    confere("app ao vivo: nada de 'próximo pregão'", !/próximo pregão|pregão seguinte/.test(await p.locator("#app").textContent()));
    await p.evaluate(() => { aviso = null; mostrarAviso(); desTipo = "sim"; render(); });
    { const [ok, t] = await p.evaluate(() => { const o = load("historico", []).find((x) => x.id === 1), t = document.getElementById("app").textContent; return [/saiu no alvo/.test(t) && t.includes(sgn(o.vivo.r)), t.slice(0, 900) + " | " + sgn(o.vivo.r)]; });
      confere("app ao vivo: o Desempenho das simuladas conta a saída no alvo, com o resultado do momento", ok, t); }
    await p.evaluate(() => { selId = 2; slider = null; tela = "acomp"; render(); }); await p.waitForTimeout(400);
    const real = await p.locator("#app").innerText();
    confere("app ao vivo: a real mostra 'Se encerrar agora', o aviso e a ordem pronta (vender e comprar, perna a perna)",
      /Se encerrar agora/.test(real) && /Alvo atingido às \d\d:\d\d/.test(real) && /Vender\s+\d+ \S+\s+a R\$/.test(real) && /Comprar\s+\d+ \S+\s+a R\$/.test(real), real.slice(0, 400));
    await p.evaluate(() => { selId = 1; slider = null; tela = "acomp"; render(); }); await p.waitForTimeout(300);
    const sim = await p.locator("#app").innerText();
    confere("app ao vivo: a simulada mostra a saída executada (Vendeu, Recomprou) e a hora", /Saiu no alvo em \d\d\/\d\d\/\d{4}, às \d\d:\d\d/.test(sim) && /Vendeu/.test(sim) && /Recomprou/.test(sim), sim.slice(0, 300));
    // ao reabrir o app, a real que já avisou não avisa de novo
    await p.reload(); await p.waitForSelector("#nav"); await p.waitForTimeout(1500);
    confere("app ao vivo: depois de reabrir, sem aviso repetido", (await p.locator("#aviso-vivo").count()) === 0);
    confere("app: sem erros de página", erros.length === 0, erros);
  } finally { await b.close(); srv.kill(); }
}
