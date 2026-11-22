// Telas da LP com ativos diferentes: hero PETR4 (montada), passo 1 VALE3 (Início), passo 2 ITUB4 (ordens), passo 3 BBAS3 (cenários).
const { chromium } = require("playwright");
const out = process.argv[2], URL = "http://localhost:8765/index.html?teste=1";
const prep = ([ativo, perda]) => { S.plano = "pro"; S.perda = perda; S.capital = 50000; S.data = SNAP.data; S.ativo = ativo; S.pfTrava = "maior";
  for (const v of vencs()) { S.venc = v.iso; S.prazo = v.d; if (typeof montagem("alta") !== "string") break; }
  const m = montagem("alta"); save("estado", S); return typeof m === "string" ? m : `${ativo} ${m.lotes} lotes risco ${m.perdaMax} ganho ${m.ganhoMax}`; };
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1, locale: "pt-BR", timezoneId: "America/Sao_Paulo" });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  const p = await ctx.newPage(), erros = []; p.on("pageerror", (e) => erros.push(e.message));
  await p.goto(URL); await p.waitForSelector("#nav"); await p.evaluate(() => localStorage.clear()); await p.reload(); await p.waitForSelector("#nav");
  const tela = async (ativo, perda, fn, arq, rolar) => {
    console.log(arq, await p.evaluate(prep, [ativo, perda])); await p.reload(); await p.waitForSelector("#nav");
    await p.evaluate(fn); await p.waitForTimeout(500);
    if (rolar) { await p.evaluate(rolar); await p.waitForTimeout(300); }
    await p.screenshot({ path: `${out}/${arq}.png` });
  };
  await tela("PETR4", 2000, () => { tese = "alta"; voltaCartao = "obj"; tela = "cartao"; render(); }, "pc-montada");
  await tela("VALE3", 2000, () => { tela = "obj"; render(); }, "pc-inicio");
  await tela("ITUB4", 2000, () => { tese = "alta"; voltaCartao = "obj"; tela = "cartao"; render(); }, "pc-ordens", () => window.scrollTo(0, document.body.scrollHeight));
  await tela("BBAS3", 2000, () => { tese = "alta"; voltaCartao = "obj"; tela = "cen"; render(); }, "pc-cenarios");
  console.log("erros", erros); await ctx.close(); await b.close();
})();
