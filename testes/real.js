// Operação real (nível 1): registrar o que foi executado, acompanhar, registrar o encerramento e o Desempenho.
// App servido por HTTP com o preço do dia do snapshot (a cadeia do próprio snapshot). Confere as contas da tela contra
// o montador (execucao, resultadoNoDia) e que a operação real não sai sozinha pela regra nem some com o histórico simulado.
// Uso: python3 build.py && python3 build_pwa.py && node testes/real.js
const path = require("path"), fs = require("fs"), os = require("os"), { spawn } = require("child_process");
const { chromium } = require("playwright");
const RAIZ = path.join(__dirname, ".."), M = require(path.join(RAIZ, "montador.js")), snap = require(path.join(RAIZ, "snapshot.json"));
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };
const r2 = (x) => Math.round(x * 100) / 100, br = (n) => n.toFixed(2).replace(".", ",");

(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "real-"));
  for (const f of fs.readdirSync(path.join(RAIZ, "pwa"))) if (fs.statSync(path.join(RAIZ, "pwa", f)).isFile()) fs.copyFileSync(path.join(RAIZ, "pwa", f), path.join(dir, f));
  fs.mkdirSync(path.join(dir, "precos"));
  const op = {}; for (const a of Object.values(snap.ativos)) for (const o of a.chain) op[o.s] = [o.b, o.a];
  fs.writeFileSync(path.join(dir, "precos", `${snap.data}.json`), JSON.stringify({ data: snap.data, op }));
  const srv = spawn("python3", ["-m", "http.server", "8766", "--bind", "127.0.0.1"], { cwd: dir, stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 800));
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: "block", locale: "pt-BR" });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  const p = await ctx.newPage(), erros = []; p.on("pageerror", (e) => erros.push(e.message));
  try {
    await p.goto("http://127.0.0.1:8766/"); await p.waitForSelector("#nav");
    // primeira trava que monta no dia (risco até R$ 3.000), em qualquer ativo
    const esc = await p.evaluate(() => { localStorage.clear(); S.perda = 3000; S.capital = 30000;
      for (const at of Object.keys(SNAP.ativos)) { S.ativo = at; for (const t of ["alta", "baixa"]) { const m = montagem(t); if (typeof m !== "string") { save("estado", S); return { at, t }; } } } return null; });
    if (!esc) throw new Error("nenhuma trava monta no snapshot");
    await p.reload(); await p.waitForSelector("#nav");
    const m0 = await p.evaluate((t) => { tese = t; tela = "cen"; render(); return montagem(t); }, esc.t);
    // preço do dia que leva a operação ao limite já no dia da execução: perna comprada quase sem valor, vendida cara
    for (const [l, x] of m0.pernas) op[x.s] = l > 0 ? [0.01, 0.02] : [r2(x.a * 1.5), r2(x.a * 1.6)];
    fs.writeFileSync(path.join(dir, "precos", `${snap.data}.json`), JSON.stringify({ data: snap.data, op }));
    await p.click("text=Já executei na corretora");
    const ini = await p.evaluate(() => ({ qtd: realF.qtd, precos: realF.precos.slice(), tela }));
    confere("registrar: abre com a quantidade e os preços da montagem", ini.tela === "real" && ini.qtd === m0.lotes * 100 && JSON.stringify(ini.precos) === JSON.stringify(m0.pernas.map(([l, x]) => (l > 0 ? x.a : x.b))), ini);
    // quantidade inválida: botão desligado e motivo na tela
    await p.fill("#rqtd", "150"); await p.dispatchEvent("#rqtd", "change");
    confere("registrar: quantidade fora de lote de 100 não registra", (await p.isDisabled("#registrar")) && (await p.locator("text=múltipla de 100").count()) === 1);
    // execução: 1 lote a mais, compra 5% mais cara, venda 5% mais barata, custos de R$ 10,00
    const lotes = m0.lotes + 1, precos = m0.pernas.map(([l, x]) => r2(l > 0 ? x.a * 1.05 : x.b * 0.95));
    await p.fill("#rdata", snap.data); await p.dispatchEvent("#rdata", "change");
    await p.fill("#rqtd", String(lotes * 100)); await p.dispatchEvent("#rqtd", "change");
    for (let i = 0; i < precos.length; i++) { await p.fill(`#rpreco${i}`, br(precos[i])); await p.dispatchEvent(`#rpreco${i}`, "change"); }
    await p.fill("#rcustos", "10,00"); await p.dispatchEvent("#rcustos", "change");
    const esp = M.execucao(m0, { lotes, precos });
    const resumo = await p.innerText("#app");
    confere("registrar: resumo com os preços executados", resumo.includes(`R$ ${esp.perdaMax.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`), { esperado: esp.perdaMax });
    await p.click("#registrar"); await p.waitForTimeout(800); await p.evaluate(() => render());
    const hs = await p.evaluate(() => load("historico", []));
    const o = hs[0];
    confere("registrar: grava a operação real com a montagem refeita", hs.length === 1 && o.real && o.real.data === snap.data && o.real.custos === 10 && o.m.lotes === lotes && o.m.premio === esp.premio && o.m.perdaMax === esp.perdaMax && o.m.alvo === esp.alvo && o.m.stop === esp.stop, o && { real: o.real, lotes: o.m.lotes, premio: o.m.premio });
    // acompanhamento pelo preço do dia da execução
    const hoje = M.resultadoNoDia(esp, op);
    const sua = await p.innerText("#app");
    confere("Sua operação: etiqueta de operação real e 'Se encerrar hoje' pelo preço executado", sua.includes("Operação real") && sua.includes("Se encerrar hoje") && sua.includes((hoje > 0 ? "+" : hoje < 0 ? "−" : "") + "R$ " + Math.abs(Math.round(hoje)).toLocaleString("pt-BR")), { hoje, trecho: sua.slice(0, 260) });
    const vencISO = (() => { const d = new Date(snap.data + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + esp.dias); return d.toISOString().slice(0, 10); })();
    const regraEsp = M.regraDeSaida(esp, [{ d: snap.data, r: hoje }], vencISO), regraApp = await p.evaluate((id) => STATUS.get(id)?.saida || null, o.id);
    confere("regra de saída conta o fechamento do dia da execução (limite atingido)", regraEsp && regraEsp.regra === "limite" && JSON.stringify(regraApp) === JSON.stringify(regraEsp), { regraApp, regraEsp });
    const lst = await p.evaluate(() => { tela = "acomp"; selId = null; render(); return document.getElementById("app").innerText; });
    confere("operação real com a regra atingida continua em aberto, marcada na lista", /1 real/.test(lst) && lst.includes("regra atingida"), lst.slice(0, 200));
    await p.click(`[data-op="${o.id}"]`); await p.waitForTimeout(300);
    // uma simulada junto; a lista separa as duas
    await p.evaluate((t) => { tese = t; ciente = true; tela = "cen"; render(); }, esc.t); await p.click("#confirmar"); await p.waitForTimeout(500);
    await p.click('#nav [data-nav="acomp"]'); await p.waitForTimeout(300);
    const lista = await p.innerText("#app");
    confere("Minhas operações: reais e simuladas separadas", /1 real · 1 simulada/.test(lista) && lista.includes("Reais") && lista.includes("Simuladas"), lista.slice(0, 200));
    // encerramento: sugere o fechamento do dia (venda pela compra, recompra pela venda); custos de saída R$ 10,00
    await p.click(`[data-op="${o.id}"]`); await p.waitForTimeout(500); await p.click("#ir-sair");
    const sug = await p.evaluate(() => saidaF.precos.slice());
    const sugEsp = esp.pernas.map(([l, x]) => (l > 0 ? op[x.s][0] : op[x.s][1]));
    confere("encerramento: sugere o fechamento do dia de cada perna", JSON.stringify(sug) === JSON.stringify(sugEsp), { sug, sugEsp });
    await p.fill("#scustos", "10,00"); await p.dispatchEvent("#scustos", "change");
    const resEsp = r2(M.resultadoNoDia(esp, Object.fromEntries(esp.pernas.map(([l, x], i) => [x.s, [sugEsp[i], sugEsp[i]]]))) - 20);
    await p.click("#registrar-saida"); await p.waitForTimeout(300);
    const fech = await p.evaluate((id) => load("historico", []).find((x) => x.id === id).real.saida, o.id);
    confere("encerramento: resultado = preços de saída − prêmio − custos de entrada e saída", fech && fech.res === resEsp, { fech, resEsp });
    await p.click('#nav [data-nav="acomp"]'); await p.waitForTimeout(300);
    const lista2 = await p.innerText("#app");
    confere("Minhas operações: a real encerrada sai da lista; a simulada continua", !lista2.includes("Reais") && /1 simulada/.test(lista2), lista2.slice(0, 200));
    await p.click('#nav [data-nav="desemp"]'); await p.waitForTimeout(300);
    const des = await p.innerText("#app");
    const fmt = (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + "R$ " + Math.abs(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    confere("Desempenho: abre nas reais, com o resultado registrado", des.includes("Operações reais") && des.includes(fmt(resEsp)), { esperado: fmt(resEsp), trecho: des.slice(0, 400) });
    // apagar o histórico simulado não apaga a real
    await p.click('[data-tipo="sim"]'); p.once("dialog", (d) => d.accept()); await p.click("#limpar-hist"); await p.waitForTimeout(200);
    const resto = await p.evaluate(() => load("historico", []).map((x) => !!x.real));
    confere("Apagar histórico simulado mantém as operações reais", JSON.stringify(resto) === "[true]", resto);
    confere("sem erros na página", erros.length === 0, erros);
  } catch (e) { confere("fluxo sem exceção", false, e.message.split("\n")[0]); }
  await b.close(); srv.kill(); fs.rmSync(dir, { recursive: true, force: true });
  console.log(falhas ? `\n${falhas} caso(s) falharam` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
