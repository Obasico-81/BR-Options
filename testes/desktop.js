// Layout de computador (a partir de 1024px): menu lateral, Início com as quatro operações lado a lado, telas em duas
// colunas, Minhas operações e Desempenho em tabela, Ajustes em duas colunas. Mesmos números do celular; sem rolagem
// lateral de 1024 a 1920px; ao estreitar a janela, volta o layout de celular.
// App servido por HTTP com o preço do dia do snapshot (para "Se encerrar hoje").
// Uso: python3 build.py && python3 build_pwa.py && node testes/desktop.js
const path = require("path"), fs = require("fs"), os = require("os"), { spawn } = require("child_process");
const { chromium } = require("playwright");
const RAIZ = path.join(__dirname, ".."), snap = require(path.join(RAIZ, "snapshot.json"));
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };

(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "desktop-"));
  for (const f of fs.readdirSync(path.join(RAIZ, "pwa"))) if (fs.statSync(path.join(RAIZ, "pwa", f)).isFile()) fs.copyFileSync(path.join(RAIZ, "pwa", f), path.join(dir, f));
  fs.mkdirSync(path.join(dir, "precos"));
  const op = {}; for (const a of Object.values(snap.ativos)) for (const o of a.chain) op[o.s] = [o.b, o.a];
  fs.writeFileSync(path.join(dir, "precos", `${snap.data}.json`), JSON.stringify({ data: snap.data, op }));
  const porta = 8900 + Math.floor(Math.random() * 90);
  const srv = spawn("python3", ["-m", "http.server", String(porta), "--bind", "127.0.0.1"], { cwd: dir, stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 800));
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 1366, height: 768 }, serviceWorkers: "block", locale: "pt-BR" });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  const p = await ctx.newPage(), erros = []; p.on("pageerror", (e) => erros.push(e.message)); p.on("dialog", (d) => d.accept());
  const caixa = (sel) => p.locator(sel).first().boundingBox();
  const semRolagemLateral = () => p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
  const larguras = async (nome) => { for (const w of [1024, 1280, 1366]) { await p.setViewportSize({ width: w, height: 800 }); confere(`sem rolagem lateral em ${w}px (${nome})`, await semRolagemLateral()); } await p.setViewportSize({ width: 1366, height: 768 }); };
  try {
    await p.goto(`http://127.0.0.1:${porta}/`); await p.waitForSelector("#nav");
    // perfil largo o bastante para as operações montarem; o ativo com mais operações disponíveis
    await p.evaluate(() => { localStorage.clear(); S.perda = 3000; S.capital = 30000;
      let melhor = null, n = -1; for (const at of Object.keys(SNAP.ativos)) { S.ativo = at; const k = TESES.filter((t) => typeof montagem(t.k) !== "string").length; if (k > n) { n = k; melhor = at; } }
      S.ativo = melhor; save("estado", S); });
    await p.reload(); await p.waitForSelector("#nav");

    // ---------- menu lateral ----------
    const nav = await caixa("#nav"), navTxt = await p.innerText("#nav");
    confere("menu lateral: à esquerda, de cima a baixo, com 240px", nav.x === 0 && nav.y === 0 && Math.round(nav.width) === 240 && nav.height >= 760, nav);
    confere("menu lateral: marca, as quatro telas e o dia dos preços", /Montador de Opções/.test(navTxt) && /Início/.test(navTxt) && /Desempenho/.test(navTxt) && navTxt.includes(`Preços de ${snap.data.split("-").reverse().join("/")}`), navTxt);

    // ---------- Início: ativo e perfil à esquerda; as quatro operações lado a lado ----------
    const ini = await p.evaluate(() => ({ cards: [...document.querySelectorAll(".cmp [data-tese]")].map((b) => ({ k: b.dataset.tese, ok: !b.disabled, txt: b.innerText })),
      esperado: TESES.map((t) => { const m = montagem(t.k); return typeof m === "string" ? null : { risco: brl(m.perdaMax), chance: pct(m.probImplicita) }; }) }));
    confere("Início: quatro cartões de operação lado a lado", ini.cards.length === 4 && (await p.locator(".cmp").count()) === 1);
    const disp = ini.cards.map((c, i) => [c, ini.esperado[i]]).filter(([c]) => c.ok);
    confere("Início: pelo menos uma operação disponível para conferir", disp.length > 0);
    confere("Início: cada disponível mostra risco máximo e chance iguais aos da montagem", disp.every(([c, e]) => c.txt.includes("Risco máximo") && c.txt.includes(e.risco) && c.txt.includes("Chance implícita") && c.txt.includes(e.chance)), disp.map(([c]) => c.txt.slice(0, 200)));
    const lista = await caixa("#atvL"), cmp = await caixa(".cmp");
    confere("Início: lista de ativos sempre aberta, à esquerda das operações", lista && lista.height > 100 && lista.x + lista.width <= cmp.x, { lista, cmp });
    confere("Início: perfil aberto, sem botão de fechar", (await p.locator("#capital").count()) === 1 && (await p.locator('[data-perfil="0"]').count()) === 0);
    await larguras("Início"); await p.setViewportSize({ width: 1920, height: 1080 }); confere("sem rolagem lateral em 1920px (Início)", await semRolagemLateral()); await p.setViewportSize({ width: 1366, height: 768 });

    // ---------- cartão e cenários em duas colunas, com o gráfico ----------
    await p.click(`.cmp [data-tese="${disp[0][0].k}"]`);
    const cart = await p.evaluate(() => { const c = document.querySelectorAll(".cols > .col"); return { cols: c.length, esq: c[0] && c[0].innerText, graf: !!(c[1] && c[1].querySelector("svg.payoff")) }; });
    confere("cartão: duas colunas, números e 'O que fazer' à esquerda, gráfico à direita", cart.cols === 2 && /risco máximo/i.test(cart.esq) && /O que fazer/.test(cart.esq) && cart.graf, cart);
    confere("cartão: chance implícita uma vez só (o gráfico não repete)", ((await p.innerText("#app")).match(/Chance implícita/g) || []).length === 1);
    await larguras("cartão");
    await p.click("text=Ver cenários");
    const cen = await p.evaluate(() => { const c = document.querySelectorAll(".cols > .col"); return { graf: !!(c[0] && c[0].querySelector("svg.payoff")), chk: !!(c[1] && c[1].querySelector("#ciente")) }; });
    confere("cenários: gráfico à esquerda; tabela, risco e confirmação à direita", cen.graf && cen.chk, cen);
    await larguras("cenários");
    await p.check("#ciente"); await p.click("#confirmar"); await p.waitForTimeout(800); await p.evaluate(() => render());

    // ---------- sua operação: gráfico com o controle de preço, em duas colunas ----------
    const det = await p.evaluate(() => { const c = document.querySelectorAll(".cols > .col"); return { sl: !!(c[0] && c[0].querySelector("#sl")), sair: c[1] && /Quando sair/.test(c[1].innerText) }; });
    confere("sua operação: gráfico e controle à esquerda, 'Quando sair' à direita", det.sl && det.sair, det);
    const antes = await p.innerText("#rv");
    await p.evaluate(() => { const s = document.getElementById("sl"); s.value = s.max; s.dispatchEvent(new Event("input")); });
    confere("sua operação: mover o preço muda o resultado e redesenha o gráfico", (await p.innerText("#rv")) !== antes && (await p.locator("#payoff svg.payoff").count()) === 1);
    await larguras("sua operação");

    // ---------- Minhas operações: tabela ----------
    // mais uma, já vencida (entrada 90 dias antes do último pregão, 30 dias de prazo), para o Desempenho
    await p.evaluate(() => { const hs = load("historico", []), o = hs[0], f = Object.keys(SNAP.fechamentos[o.ativo]).sort(), d0 = f[Math.max(0, f.length - 90)];
      hs.push({ ...o, m: { ...o.m, dias: 30 }, data: d0, id: 7 }); save("historico", hs); });
    await p.click('#nav [data-nav="acomp"]'); await p.waitForTimeout(500); await p.evaluate(() => render());
    const tab = await p.evaluate(() => ({ linhas: document.querySelectorAll("table.tab tbody tr[data-op]").length, txt: document.querySelector("table.tab") && document.querySelector("table.tab").innerText,
      cab: [...document.querySelectorAll("table.tab th")].map((t) => t.innerText) }));
    confere("Minhas operações: tabela com a operação em aberto", tab.linhas === 1 && /Simulada/.test(tab.txt) && tab.cab.includes("Se encerrar hoje") && tab.cab.includes("Risco máx."), tab);
    confere("Minhas operações: 'Se encerrar hoje' com valor (preço do dia carregado)", /[+−]?R\$ \d/.test(tab.txt.split("\n")[1] || ""), tab.txt);
    confere("Minhas operações: sem o '‹ Início' (o menu lateral já leva lá)", !(await p.isVisible('[data-ini]')));
    await larguras("Minhas operações");
    await p.focus("table.tab tbody tr[data-op]"); await p.keyboard.press("Enter");
    confere("Minhas operações: Enter na linha abre a operação", await p.evaluate(() => tela === "acomp" && selId !== null && !!document.getElementById("sl")));

    // ---------- Desempenho: período e resultado lado a lado; operações em tabela ----------
    await p.click('#nav [data-nav="desemp"]'); await p.click('[data-tipo="sim"]'); await p.click('[data-per="tudo"]'); await p.waitForTimeout(300);
    const des = await p.evaluate(() => ({ cols: document.querySelectorAll(".cols > .col").length, linhas: [...document.querySelectorAll("table.tab tbody tr")].map((r) => r.innerText) }));
    confere("Desempenho: período e resultado lado a lado; a operação vencida na tabela", des.cols === 2 && des.linhas.length === 1 && /venceu|saiu/.test(des.linhas[0]), des);
    await larguras("Desempenho");

    // ---------- Ajustes: duas colunas ----------
    await p.click('#nav [data-nav="cad"]');
    const aj = await p.evaluate(() => [...document.querySelectorAll(".ajustes > .coluna")].map((c) => ({ x: c.getBoundingClientRect().x, n: c.querySelectorAll("section").length })));
    confere("Ajustes: cartões em duas colunas", aj.length === 2 && aj[0].x < aj[1].x && aj[0].n + aj[1].n === 6, aj);
    await larguras("Ajustes");

    // ---------- tela de entrar: sem menu, coluna estreita no meio ----------
    await p.click("#conta-entrar");
    const lg = await p.evaluate(() => ({ nav: document.getElementById("nav").style.display, pad: getComputedStyle(document.body).paddingLeft, w: document.getElementById("app").getBoundingClientRect().width }));
    confere("entrar: sem menu lateral e coluna de até 460px", lg.nav === "none" && lg.pad === "0px" && lg.w <= 460, lg);
    await p.click('[data-go="cad"]');

    // ---------- janela estreita: volta o celular ----------
    await p.setViewportSize({ width: 390, height: 844 }); await p.waitForTimeout(200);
    await p.click('#nav [data-nav="obj"]');
    const cel = await p.evaluate(() => ({ cols: document.querySelectorAll(".cols").length, cmp: document.querySelectorAll(".cmp").length, nav: document.getElementById("nav").getBoundingClientRect(), marca: getComputedStyle(document.querySelector("#nav .marca")).display }));
    confere("janela estreita: menu embaixo, sem colunas nem cartões lado a lado", cel.cols === 0 && cel.cmp === 0 && cel.nav.y > 700 && cel.nav.width === 390 && cel.marca === "none", cel);
    confere("sem rolagem lateral em 390px", await semRolagemLateral());
    confere("sem erros na página", erros.length === 0, erros);
  } finally { await b.close(); srv.kill(); fs.rmSync(dir, { recursive: true, force: true }); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
