// Avisos no celular (app nativo): com o componente de notificações do Capacitor simulado no navegador, confere que o
// app pede permissão só ao registrar uma operação real, agenda prazo de saída e vencimento às 10h (fuso de São Paulo),
// não duplica ao reabrir, cancela ao encerrar e mostra o estado no cartão "Avisos neste celular".
// O componente de verdade só roda no celular; aqui vale a lógica do app. Uso: python3 build.py && python3 build_pwa.py && node testes/avisos.js
const path = require("path"), { spawn } = require("child_process");
const { chromium } = require("playwright");
// servido por HTTP: aberto como arquivo local, o navegador às vezes não mantém o sessionStorage entre recarregamentos
const RAIZ = path.join(__dirname, ".."), ARQ = "http://127.0.0.1:8767/", snap = require(path.join(RAIZ, "snapshot.json"));
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };
const addDias = (iso, n) => { const d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const dBR = (iso) => iso.split("-").reverse().join("/");

(async () => {
  const srv = spawn("python3", ["-m", "http.server", "8767", "--bind", "127.0.0.1"], { cwd: path.join(RAIZ, "pwa"), stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 800));
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 390, height: 844 }, timezoneId: "America/Sao_Paulo", serviceWorkers: "block" });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  // componente simulado; o estado sobrevive a recarregar (sessionStorage), como as notificações agendadas no celular
  await ctx.addInitScript(() => {
    const st = JSON.parse(sessionStorage.getItem("__ln") || '{"perm":"prompt","negar":false,"pend":[],"calls":[]}');
    const salva = () => sessionStorage.setItem("__ln", JSON.stringify(st));
    // configuração do teste numa chave à parte, que o componente nunca regrava (chamadas atrasadas da página anterior
    // podem regravar "__ln" depois que o teste mudou o estado)
    const cfg = JSON.parse(sessionStorage.getItem("__ln_cfg") || "null"); if (cfg) { Object.assign(st, cfg); sessionStorage.removeItem("__ln_cfg"); salva(); }
    window.Capacitor = { isNativePlatform: () => true, Plugins: { LocalNotifications: {
      checkPermissions: async () => { st.calls.push(["check"]); salva(); return { display: st.perm }; },
      requestPermissions: async () => { st.calls.push(["request"]); st.perm = st.negar ? "denied" : "granted"; salva(); return { display: st.perm }; },
      getPending: async () => ({ notifications: st.pend.map((n) => ({ id: n.id })) }),
      schedule: async ({ notifications }) => { st.calls.push(["schedule", notifications.map((n) => n.id)]);
        for (const n of notifications) st.pend = st.pend.filter((x) => x.id !== n.id).concat([{ id: n.id, title: n.title, body: n.body, at: n.schedule.at.getTime(), dia: n.extra && n.extra.dia }]);
        salva(); return { notifications: notifications.map((n) => ({ id: n.id })) }; },
      cancel: async ({ notifications }) => { st.calls.push(["cancel", notifications.map((n) => n.id)]); const ids = new Set(notifications.map((n) => n.id)); st.pend = st.pend.filter((x) => !ids.has(x.id)); salva(); },
    } } };
  });
  const p = await ctx.newPage(), erros = []; p.on("pageerror", (e) => erros.push(e.message));
  const ln = () => p.evaluate(() => JSON.parse(sessionStorage.getItem("__ln")));
  const espera = (ms) => p.waitForTimeout(ms);
  try {
    await p.goto(ARQ); await p.waitForSelector("#nav");
    const esc = await p.evaluate(() => { localStorage.clear(); S.perda = 3000; S.capital = 30000;
      for (const at of Object.keys(SNAP.ativos)) { S.ativo = at; for (const t of ["alta", "baixa"]) { const m = montagem(t); if (typeof m !== "string") { save("estado", S); return { t, at }; } } } return null; });
    if (!esc) throw new Error("nenhuma trava monta no snapshot");
    await p.reload(); await p.waitForSelector("#nav"); await espera(300);
    let st = await ln();
    confere("ao abrir sem operação real: confere a permissão e não pede", st.calls.some((c) => c[0] === "check") && !st.calls.some((c) => c[0] === "request"), st.calls);
    const registrar = async () => { await p.evaluate((t) => { tese = t; tela = "cen"; realF = null; render(); }, esc.t); await p.click("text=Já executei na corretora");
      await p.fill("#rdata", snap.data); await p.dispatchEvent("#rdata", "change"); await p.click("#registrar");
      await p.waitForFunction(() => avisosEstado !== null, null, { timeout: 5000 }); await espera(200); };
    await registrar();
    st = await ln();
    const o = await p.evaluate(() => load("historico", []).find((x) => x.real));
    const venc = addDias(o.data, o.m.dias), prazo = addDias(venc, -o.m.saidaDias), ids = [(Math.floor(o.id / 1000) % 1e9) * 2, (Math.floor(o.id / 1000) % 1e9) * 2 + 1];
    confere("registrar a operação real pede a permissão uma vez", st.calls.filter((c) => c[0] === "request").length === 1, st.calls);
    const horas = await p.evaluate((pend) => pend.map((n) => { const d = new Date(n.at); return [d.getHours(), d.getMinutes(), `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`]; }), st.pend);
    confere("agenda prazo de saída e vencimento às 10h do dia certo", JSON.stringify(st.pend.map((n) => n.id).sort()) === JSON.stringify(ids)
      && JSON.stringify(horas.map((h) => h.join("|")).sort()) === JSON.stringify([`10|0|${prazo}`, `10|0|${venc}`].sort()), { pend: st.pend, horas, prazo, venc });
    const textos = st.pend.map((n) => n.title + " / " + n.body).join(" || ");
    confere("textos dos avisos com a estrutura e o ativo", textos.includes("Prazo de saída hoje") && textos.includes("Vencimento hoje") && textos.includes(`${o.m.estrutura} · ${o.ativo}`), textos);
    const card = await p.innerText("#app");
    confere("Sua operação mostra os avisos agendados", card.includes("Avisos neste celular") && card.includes(`Prazo de saída: ${dBR(prazo)} às 10h`) && card.includes(`Vencimento: ${dBR(venc)} às 10h`), card.slice(0, 600));
    await p.reload(); await p.waitForSelector("#nav");
    await p.waitForFunction(() => JSON.parse(sessionStorage.getItem("__ln")).calls.filter((c) => c[0] === "schedule").length >= 2, null, { timeout: 5000 }).catch(() => {});
    st = await ln();
    confere("reabrir o app reagenda sem duplicar", st.pend.length === 2 && st.calls.filter((c) => c[0] === "request").length === 1, st.pend.map((n) => n.id));
    // encerrar cancela
    await p.evaluate((id) => { selId = id; tela = "acomp"; render(); }, o.id); await espera(300); await p.click("#ir-sair");
    for (let i = 0; i < o.m.pernas.length; i++) { await p.fill(`#spreco${i}`, "1,00"); await p.dispatchEvent(`#spreco${i}`, "change"); }
    await p.click("#registrar-saida");
    await p.waitForFunction(() => JSON.parse(sessionStorage.getItem("__ln")).pend.length === 0, null, { timeout: 5000 }).catch(() => {});
    st = await ln();
    confere("registrar o encerramento cancela os avisos da operação", st.pend.length === 0 && st.calls.some((c) => c[0] === "cancel" && JSON.stringify(c[1].slice().sort()) === JSON.stringify(ids)), st.calls.slice(-3));
    // permissão negada
    await p.evaluate(() => sessionStorage.setItem("__ln_cfg", JSON.stringify({ perm: "prompt", negar: true, calls: [] })));
    await p.reload(); await p.waitForSelector("#nav"); await espera(300); await registrar();
    st = await ln();
    confere("permissão negada: não agenda e avisa como ligar", !st.calls.some((c) => c[0] === "schedule") && (await p.innerText("#app")).includes("Avisos desligados"), st.calls);
    confere("sem erros na página", erros.length === 0, erros);
  } catch (e) { confere("fluxo sem exceção", false, e.message.split("\n")[0]); }
  await b.close(); srv.kill();
  console.log(falhas ? `\n${falhas} caso(s) falharam` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
