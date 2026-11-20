// Plano grátis × Vaglio Pro: no grátis, nenhuma opção da operação (símbolo ou strike) aparece na tela, "Já executei" e
// "Copiar parâmetros" levam ao Pro e não há tempo real; no Pro, tudo aparece. "Assinar" no ?teste=1 liga o Pro.
// Uso: node testes/assinatura.js   (precisa de python3 e do Playwright; gera pwa/index.html antes: python3 build.py && python3 build_pwa.py)
const path = require("path"), { spawn } = require("child_process"), { chromium } = require("playwright");
const RAIZ = path.join(__dirname, "..");
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };
(async () => {
  const porta = 8990 + Math.floor(Math.random() * 9);
  const srv = spawn("python3", ["-m", "http.server", String(porta), "--bind", "127.0.0.1", "--directory", path.join(RAIZ, "pwa")], { stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 800));
  const b = await chromium.launch();
  try {
    for (const [nome, vp] of [["celular", { width: 390, height: 844 }], ["computador", { width: 1440, height: 900 }]]) {
      const p = await (await b.newContext({ viewport: vp, locale: "pt-BR", timezoneId: "America/Sao_Paulo" })).newPage(), erros = [];
      p.on("pageerror", (e) => erros.push(e.message));
      const abrir = async (q) => { await p.goto(`http://127.0.0.1:${porta}/index.html?teste=1${q || ""}`); await p.waitForSelector("#nav"); };
      await abrir(); await p.evaluate(() => localStorage.clear()); await abrir();
      confere(`${nome}: os testes automáticos começam no Pro`, await p.evaluate(() => PRO()));
      // uma trava de alta que monte em algum ativo e vencimento do dia; vira operação simulada
      const ok = await p.evaluate(() => { S.plano = "gratis"; S.data = SNAP.data;
        for (const a of Object.keys(SNAP.por_data[S.data])) { S.ativo = a; for (const v of vencs()) { S.venc = v.iso; S.prazo = v.d; const m = montagem("alta");
          if (typeof m !== "string") { save("estado", S); localStorage.setItem("historico", JSON.stringify([{ m, ativo: a, data: S.data, id: 1 }])); return true; } } } return false; });
      if (!ok) { confere(`${nome}: alguma trava de alta monta no dia`, false); continue; }
      await abrir();
      const pernas = () => p.evaluate(() => { const m = montagem("alta"), t = document.getElementById("app").innerHTML; return m.pernas.filter(([, x]) => t.includes(x.s) || t.includes(brl(x.k, 2))).map(([, x]) => x.s); });
      await p.evaluate(() => { tese = "alta"; tela = "cartao"; render(); });
      confere(`${nome}: grátis — operação montada sem símbolo nem strike das opções`, (await pernas()).length === 0, await pernas());
      confere(`${nome}: grátis — os números continuam (risco, ganho, equilíbrio)`, await p.evaluate(() => { const m = montagem("alta"), t = document.getElementById("app").textContent; return t.includes(brl(m.perdaMax)) && t.includes(brl(m.ganhoMax)) && t.includes(brl(m.equilibrio[0], 2)); }));
      await p.click('[data-go="pro"]');
      confere(`${nome}: grátis — "Ver as opções" abre o Vaglio Pro, e o Voltar volta à operação`, (await p.locator("h1").innerText()) === "Vaglio Pro" && /Operação/.test(await p.locator(".back").first().innerText()));
      { const txt = () => p.locator("#app").innerText();
        const t1 = await txt();
        confere(`${nome}: Pro — R$ 49,90 por mês e R$ 479 por ano (R$ 39,92 por mês), anual marcado, 7 dias grátis`,
          /R\$ 49,90/.test(t1) && /R\$ 479/.test(t1) && /R\$ 39,92 por mês/.test(t1) && /Começar 7 dias grátis/.test(t1) && /Depois, R\$ 479 por ano/.test(t1) && (await p.locator('[data-plano-esc="anual"]').getAttribute("aria-pressed")) === "true", t1.slice(0, 600));
        await p.click('[data-plano-esc="mensal"]');
        confere(`${nome}: Pro — escolher o mensal muda o aviso de cobrança`, /Depois, R\$ 49,90 por mês/.test(await txt())); }
      await p.evaluate(() => { tela = "cen"; render(); });
      confere(`${nome}: grátis — cenários sem strike`, (await pernas()).length === 0 && !/Strike/.test(await p.locator("#app").textContent()));
      confere(`${nome}: grátis — "Já executei" leva ao Pro`, (await p.locator("button", { hasText: "Já executei" }).getAttribute("data-go")) === "pro");
      await p.evaluate(() => { selId = 1; slider = null; tela = "acomp"; render(); }); await p.waitForTimeout(300);
      confere(`${nome}: grátis — Sua operação sem as opções, com "Copiar parâmetros" levando ao Pro e o convite ao vivo`,
        (await pernas()).length === 0 && (await p.locator("button", { hasText: "Copiar parâmetros" }).getAttribute("data-go")) === "pro" && (await p.locator(".tease").count()) === 1);
      // tempo real: só no Pro
      await abrir("&aovivo=sim&passo=100&semente=3"); await p.evaluate(() => { selId = null; tela = "acomp"; render(); }); await p.waitForTimeout(1500);
      confere(`${nome}: grátis — sem tempo real mesmo com fonte (sem selo, sem "se encerrar agora")`, (await p.locator(".vivo").count()) === 0 && (await p.locator("[data-agora]").count()) === 0 && await p.evaluate(() => VIVO === null));
      confere(`${nome}: grátis — Ajustes mostra o plano e o caminho para o Pro`, await p.evaluate(() => { tela = "cad"; render(); return /Plano\s*Grátis/.test(document.getElementById("app").innerText) && !!document.querySelector('#app [data-go="pro"]'); }));
      // assinar (teste) liga o Pro: opções na tela e tempo real
      await p.evaluate(() => { tese = "alta"; voltaPro = "cartao"; tela = "pro"; render(); }); await p.click("#assinar"); await p.waitForTimeout(300);
      confere(`${nome}: "Assinar" no teste liga o Pro e volta à operação, agora com as opções`, await p.evaluate(() => PRO() && tela === "cartao") && (await pernas()).length === 2, await pernas());
      await p.evaluate(() => { selId = null; tela = "acomp"; render(); }); await p.waitForSelector(".vivo", { timeout: 8000 }).catch(() => {});
      confere(`${nome}: Pro — tempo real liga`, (await p.locator(".vivo").count()) >= 1);
      await p.evaluate(() => { tela = "cad"; render(); }); await p.click("#plano-gratis");
      confere(`${nome}: voltar ao grátis desliga o tempo real`, await p.evaluate(() => !PRO() && VIVO === null));
      confere(`${nome}: sem erros de página`, erros.length === 0, erros);
    }
  } finally { await b.close(); srv.kill(); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\nTudo certo."); process.exit(falhas ? 1 : 0);
})();
