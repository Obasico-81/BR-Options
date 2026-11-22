// Print do app no celular (tela Operações, ao vivo, com o aviso de alvo) para a seção de acompanhamento das LPs.
const { chromium } = require("playwright");
const out = process.argv[2];
(async () => {
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, locale: "pt-BR", timezoneId: "America/Sao_Paulo", serviceWorkers: "block" });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  await ctx.addInitScript(() => { const D = Date, off = new D("2026-11-20T14:31:05-03:00") - D.now(); class F extends D { constructor(...a) { super(...(a.length ? a : [D.now() + off])); } static now() { return D.now() + off; } } window.Date = F; });
  const p = await ctx.newPage(), erros = []; p.on("pageerror", (e) => erros.push(e.message));
  const URL = "http://localhost:8765/index.html?teste=1&aovivo=sim&semente=11&passo=250&minutos=5&rumo=0.15";
  await p.goto(URL); await p.waitForSelector("#nav"); await p.evaluate(() => localStorage.clear()); await p.reload(); await p.waitForSelector("#nav");
  console.log(await p.evaluate(() => { S.plano = "pro"; S.perda = 2000; S.capital = 50000; S.data = SNAP.data;
    const pega = (ativo, t, pf) => { S.ativo = ativo; S.pfTrava = pf || "eq"; tese = t; for (const v of [...vencs()].sort((p, q) => Math.abs(p.d - 29) - Math.abs(q.d - 29))) { S.venc = v.iso; S.prazo = v.d; const m = montagem(t); if (typeof m !== "string") return m; } return null; };
    const realDe = (m, ativo, id) => ({ m: M.execucao(m, { lotes: m.lotes, precos: m.pernas.map(([l, x]) => l > 0 ? x.a : x.b) }), ativo, data: S.data, id, real: { data: S.data, custos: null, montada: { premio: m.premio, perdaMax: m.perdaMax, lotes: m.lotes } } });
    const hs = [], ops = [["ITUB4", "alta", "eq", 3, true], ["VALE3", "alta", "maior", 2, true], ["PETR4", "alta", "maior", 4, true], ["BOVA11", "baixa", "eq", 1, true], ["BBAS3", "forte", null, 5, false]];
    for (const [ativo, t, pf, id, real] of ops) { const m = pega(ativo, t, pf); if (!m) continue; hs.push(real ? realDe(m, ativo, id) : { m, ativo, data: S.data, id }); }
    save("estado", S); localStorage.setItem("historico", JSON.stringify(hs)); return hs.map((o) => o.id + " " + o.ativo + " " + o.m.estrutura + (o.real ? " real" : " sim")).join(" | "); }));
  await p.reload(); await p.waitForSelector("#nav");
  await p.evaluate(() => { selId = null; tela = "acomp"; render(); });
  await p.waitForFunction(() => load("historico", []).some((o) => o.real && o.vivo && o.vivo.regra === "alvo"), null, { timeout: 150000 });
  await p.waitForFunction(() => load("historico", []).every((o) => AGORA.get(o.id) && AGORA.get(o.id).r !== null && AGORA.get(o.id).r !== undefined), null, { timeout: 150000, polling: 50 });
  await p.evaluate(() => { VIVO.fechar(); VIVO.fonte = "Fornecedor"; const o = load("historico", []).find((x) => x.real && x.vivo && x.vivo.regra === "alvo");
    aviso = { id: o.id, txt: `${REGRA_CURTA[o.vivo.regra]} · ${esc(o.m.estrutura)} · ${o.ativo}`, r: AGORA.get(o.id).r, sim: false }; render(); pintarAgora(); mostrarAviso(); clearTimeout(mostrarAviso.t);
    // para o print: só a parte "Em aberto" (o Desempenho fica acima, fora da imagem), com espaço para o aviso no topo
    const ab = document.getElementById("abertas"); let n = ab.previousElementSibling; while (n) { const x = n.previousElementSibling; n.style.display = "none"; n = x; }
    document.getElementById("app").style.paddingTop = "96px"; window.scrollTo(0, 0); });
  await p.waitForTimeout(700);
  await p.screenshot({ path: `${out}/app-operacoes-n.png` });
  console.log("erros", erros); await b.close();
})();
