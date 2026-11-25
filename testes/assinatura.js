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
      const p = await (await b.newContext({ viewport: vp, locale: "pt-BR", timezoneId: "America/Sao_Paulo", serviceWorkers: "block" })).newPage(), erros = [];
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
        confere(`${nome}: Pro sem conta — R$ 49,90 por mês e R$ 479 por ano (R$ 39,92 por mês), anual marcado, 7 dias grátis, "Entrar para começar"`,
          /R\$ 49,90/.test(t1) && /R\$ 479/.test(t1) && /R\$ 39,92 por mês/.test(t1) && /Entrar para começar/.test(t1) && /7 dias grátis, depois R\$ 479 por ano/.test(t1) && (await p.locator('[data-plano-esc="anual"]').getAttribute("aria-pressed")) === "true", t1.slice(0, 600));
        await p.click('[data-plano-esc="mensal"]');
        confere(`${nome}: Pro — escolher o mensal muda o preço depois do teste`, /depois R\$ 49,90 por mês/.test(await txt())); }
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
      await p.evaluate(() => { tese = "alta"; voltaPro = "cartao"; tela = "pro"; render(); }); await p.click("#pro-teste"); await p.waitForTimeout(300);
      confere(`${nome}: "Liberar o Pro (teste)" liga o Pro e volta à operação, agora com as opções`, await p.evaluate(() => PRO() && tela === "cartao") && (await pernas()).length === 2, await pernas());
      await p.evaluate(() => { selId = null; tela = "acomp"; render(); }); await p.waitForSelector(".vivo", { timeout: 8000 }).catch(() => {});
      confere(`${nome}: Pro — tempo real liga`, (await p.locator(".vivo").count()) >= 1);
      await p.evaluate(() => { tela = "cad"; render(); }); await p.click("#plano-gratis");
      confere(`${nome}: voltar ao grátis desliga o tempo real`, await p.evaluate(() => !PRO() && VIVO === null));
      // ---------- com conta: assinar pelo Asaas (Supabase e funções simulados) ----------
      const SBU = "https://xoljwckdiedcfoygbiij.supabase.co", pedidos = []; let linha = null, consultas = 0, urlCheckout = `http://127.0.0.1:${porta}/index.html?teste=1&assinatura=ok`;
      await p.route(SBU + "/**", async (r) => { const u = r.request().url(), m = r.request().method();
        if (u.includes("/rest/v1/assinaturas")) { consultas++; return r.fulfill({ json: linha ? [linha] : [] }); }
        if (u.includes("/functions/v1/assinar")) { pedidos.push(JSON.parse(r.request().postData() || "{}")); return r.fulfill({ json: { url: urlCheckout, comTeste: true } }); }
        if (u.includes("/functions/v1/cancelar-assinatura")) { linha = { ...linha, status: "cancelada" }; return r.fulfill({ json: { ok: true } }); }
        return r.fulfill({ json: [] }); });
      await p.evaluate(() => { delete S.plano; save("estado", S); localStorage.setItem("sessao", JSON.stringify({ access_token: "t", refresh_token: "r", expires_at: Math.floor(Date.now() / 1000) + 3600, uid: "u1", email: "a@b.com" })); });
      await abrir(); await p.waitForTimeout(400);
      confere(`${nome}: com conta e sem assinatura, é grátis`, await p.evaluate(() => !PRO() && ASSIN && !ASSIN.status));
      await abrir("&plano=pro"); await p.waitForTimeout(300);
      confere(`${nome}: botão do Pro nas páginas (?plano=pro) abre a tela do Pro, com o botão de assinar`, await p.evaluate(() => tela === "pro" && !/plano=pro/.test(location.search)) && (await p.locator("#assinar").count()) === 1);
      await p.evaluate(() => { voltaPro = "obj"; tela = "pro"; render(); });
      confere(`${nome}: com conta — Pix marcado, pede nome e CPF`, (await p.locator("#pag-nome").count()) === 1 && (await p.locator("#pag-cpf").count()) === 1 && /Começar 7 dias grátis/.test(await p.locator("#assinar").innerText()));
      await p.fill("#pag-nome", "Maria Teste"); await p.fill("#pag-cpf", "529.982.247-24"); await p.click("#assinar");
      confere(`${nome}: CPF inválido não chama o pagamento`, pedidos.length === 0 && /Confira o CPF/.test(await p.locator("#app").innerText()));
      confere(`${nome}: o erro aparece na tela, sem voltar ao topo`, await p.locator('#app [role="alert"]').evaluate((e) => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }) && await p.evaluate(() => tela === "pro"));
      linha = { status: "teste", plano: "anual", forma: "PIX", pro_ate: "2099-01-01", teste_ate: "2099-01-01" };
      await p.fill("#pag-cpf", "529.982.247-25");
      await Promise.all([p.waitForURL(/assinatura=ok|index\.html\?teste=1$/, { timeout: 10000 }).catch(() => {}), p.click("#assinar")]);
      confere(`${nome}: pedido ao servidor com plano anual, Pix, nome e CPF`, pedidos.length === 1 && pedidos[0].plano === "anual" && pedidos[0].forma === "PIX" && pedidos[0].nome === "Maria Teste" && pedidos[0].cpf === "529.982.247-25", pedidos);
      await p.waitForSelector("#nav"); await p.waitForTimeout(800);
      confere(`${nome}: de volta do pagamento, a assinatura em teste dá o Pro e a tela do Pro mostra o teste`,
        await p.evaluate(() => PRO() && tela === "pro") && /Teste grátis até 01\/01\/2099/.test(await p.locator("#app").innerText()) && !/assinatura=/.test(p.url()));
      await p.evaluate(() => { tela = "cad"; render(); });
      confere(`${nome}: Ajustes mostra Vaglio Pro, o teste e "Cancelar assinatura"`, /Vaglio Pro/.test(await p.locator("#app").innerText()) && (await p.locator("#cancelar-assin").count()) === 1);
      p.once("dialog", (d) => d.accept()); await p.click("#cancelar-assin"); await p.waitForTimeout(500);
      confere(`${nome}: cancelar chama o servidor; o Pro continua até o fim do período`, linha.status === "cancelada" && await p.evaluate(() => PRO()) && /Cancelada\. O Pro continua até 01\/01\/2099/.test(await p.locator("#app").innerText()));
      // ---------- no APK: o Capacitor manda o checkout para o navegador do celular, e o app fica onde está ----------
      // (o endereço do checkout responde 204, que não tira a página do lugar, como faz o Capacitor)
      linha = null; urlCheckout = "https://checkout.teste/c1"; await p.route("https://checkout.teste/**", (r) => r.fulfill({ status: 204 }));
      await abrir(); await p.waitForTimeout(400);
      await p.evaluate(() => { window.Capacitor = { isNativePlatform: () => true, Plugins: {} }; pag.forma = "CREDIT_CARD"; voltaPro = "obj"; tela = "pro"; render(); });
      await p.click("#assinar"); await p.waitForTimeout(600);
      confere(`${nome}: no APK — o pagamento abre fora e o app fica na tela do Pro, com o aviso para voltar e o botão livre`,
        pedidos.length === 2 && pedidos[1].forma === "CREDIT_CARD" && !/checkout\.teste/.test(p.url()) && await p.evaluate(() => tela === "pro" && pag.fora && !document.getElementById("assinar").disabled) && /abriu no navegador do celular/.test(await p.locator("#app").innerText()), pedidos);
      { const antes = consultas; await p.evaluate(() => { document.getElementById("assinar").dataset.marca = "1"; }); await p.waitForTimeout(3500);
        confere(`${nome}: no APK — o app confere a assinatura sozinho, sem redesenhar a tela enquanto nada muda`, consultas > antes && await p.evaluate(() => document.getElementById("assinar")?.dataset.marca === "1"), { antes, consultas }); }
      linha = { status: "teste", plano: "anual", forma: "CREDIT_CARD", pro_ate: "2099-01-01", teste_ate: "2099-01-01" };
      await p.evaluate(() => document.dispatchEvent(new Event("visibilitychange"))); await p.waitForTimeout(800);
      confere(`${nome}: no APK — de volta ao app, o Pro aparece sem reabrir`, await p.evaluate(() => PRO() && tela === "pro") && /Você assina o Vaglio Pro/.test(await p.locator("#app").innerText()));
      await p.unroute("https://checkout.teste/**");
      // ---------- no navegador, sem conta: a volta do pagamento feito pelo APK manda voltar ao app ----------
      // (sem conta e sem plano, os testes automáticos começam no Pro; o grátis marcado mostra a tela de quem não assina)
      await p.evaluate(() => { localStorage.removeItem("sessao"); S.plano = "gratis"; save("estado", S); }); await abrir("&assinatura=ok"); await p.waitForTimeout(300);
      confere(`${nome}: volta do pagamento no navegador sem conta — manda voltar ao app do celular`, await p.evaluate(() => tela === "pro" && !sessao) && /volte ao app/.test(await p.locator("#app").innerText()));
      await p.unroute(SBU + "/**");
      confere(`${nome}: sem erros de página`, erros.length === 0, erros);
    }
  } finally { await b.close(); srv.kill(); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\nTudo certo."); process.exit(falhas ? 1 : 0);
})();
