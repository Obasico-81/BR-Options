// Marcação diária: contas do montador (resultadoNoDia, regraDeSaida) e o app servido por HTTP com preços sintéticos.
// Uso: node testes/marcacao.js   (precisa de python3 e do Playwright; gera pwa/index.html antes: python3 build.py && python3 build_pwa.py)
const path = require("path"), fs = require("fs"), os = require("os"), { spawn } = require("child_process");
const RAIZ = path.join(__dirname, ".."), M = require(path.join(RAIZ, "montador.js")), snap = require(path.join(RAIZ, "snapshot.json"));
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };

// ---------- 1. contas ----------
const a = snap.ativos.PETR4;
const m = M.montar("alta", a.S, a.chain, a.iv, 500, { caixa: 12000 });   // trava de alta: +1 call, -1 call
const [[, longa], [, curta]] = m.pernas;
// preços que dão um resultado-alvo r: v·100·lotes − prêmio = r  =>  compra da longa = v + venda da curta
const precosPara = (r) => { const v = (r + m.premio) / (100 * m.lotes), vendaCurta = 1.0; return { [longa.s]: [+(v + vendaCurta).toFixed(4), +(v + vendaCurta + 0.05).toFixed(4)], [curta.s]: [0.95, vendaCurta] }; };
confere("resultadoNoDia: desfazer no dia da entrada custa o spread das duas pernas",
  M.resultadoNoDia(m, Object.fromEntries(a.chain.map((o) => [o.s, [o.b, o.a]]))) === Math.round(((longa.b - curta.a) * 100 * m.lotes - m.premio) * 100) / 100);
confere("resultadoNoDia: preço que leva a +R$ 200 dá +R$ 200", Math.abs(M.resultadoNoDia(m, precosPara(200)) - 200) < 0.01, M.resultadoNoDia(m, precosPara(200)));
confere("resultadoNoDia: perna sem preço no dia -> null", M.resultadoNoDia(m, { [longa.s]: [1, 1.1] }) === null);
const venc = "2026-12-18";
confere("regraDeSaida: alvo", JSON.stringify(M.regraDeSaida(m, [{ d: "2026-10-01", r: 50 }, { d: "2026-10-02", r: null }, { d: "2026-10-05", r: m.alvo + 1 }], venc)) === JSON.stringify({ regra: "alvo", d: "2026-10-05", r: m.alvo + 1 }));
confere("regraDeSaida: limite antes do alvo", M.regraDeSaida(m, [{ d: "2026-10-01", r: m.stop - 1 }, { d: "2026-10-05", r: m.alvo + 1 }], venc)?.regra === "limite");
confere("regraDeSaida: prazo (7 dias antes do vencimento)", JSON.stringify(M.regraDeSaida(m, [{ d: "2026-12-10", r: 10 }, { d: "2026-12-11", r: 20 }], venc)) === JSON.stringify({ regra: "prazo", d: "2026-12-11", r: 20 }));
confere("regraDeSaida: dia sem preço e dias no/após o vencimento são ignorados", M.regraDeSaida(m, [{ d: "2026-10-01", r: null }, { d: venc, r: m.alvo + 1 }], venc) === null);
const compra = M.montarAposta("alta", a.S, a.chain, a.iv, 2000);
confere("regraDeSaida: compra simples não tem regra (só vencimento)", typeof compra !== "string" && M.regraDeSaida(compra, [{ d: "2026-10-01", r: 99999 }, { d: "2026-12-17", r: -99999 }], venc) === null);

// ---------- 2. app servido por HTTP, com preços sintéticos ----------
(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "marcacao-"));
  for (const f of fs.readdirSync(path.join(RAIZ, "pwa"))) if (fs.statSync(path.join(RAIZ, "pwa", f)).isFile()) fs.copyFileSync(path.join(RAIZ, "pwa", f), path.join(dir, f));
  fs.mkdirSync(path.join(dir, "precos"));
  const grava = (d, r) => fs.writeFileSync(path.join(dir, "precos", d + ".json"), JSON.stringify({ data: d, op: precosPara(r) }));
  const f = snap.fechamentos.PETR4, dias = Object.keys(f).filter((d) => d > "2026-09-30" && d <= snap.data).sort();
  const dAlvo = dias[5], dFim = snap.data;   // um pregão no meio de outubro e o último dia
  // valores a partir do alvo da montagem do dia (o alvo muda com a cadeia): abaixo do alvo, no alvo, abaixo do alvo
  const rAlvo = Math.max(200, Math.ceil(m.alvo)), rHoje = Math.min(120, Math.floor(m.alvo / 2)), rAntes = Math.min(50, Math.floor(m.alvo / 4));
  const fmt = (v) => "+R$ " + v.toLocaleString("pt-BR");
  grava(dias[1], rAntes); grava(dAlvo, rAlvo); grava(dFim, rHoje);
  const porta = 8700 + Math.floor(Math.random() * 200);
  const srv = spawn("python3", ["-m", "http.server", String(porta), "--bind", "127.0.0.1", "--directory", dir], { stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 800));
  const { chromium } = require("playwright");
  const b = await chromium.launch(); const p = await b.newPage(); const erros = []; p.on("pageerror", (e) => erros.push(e.message));
  try {
    await p.goto(`http://127.0.0.1:${porta}/index.html`); await p.waitForSelector("#nav");
    const dias1 = Math.round((Date.parse(venc) - Date.parse("2026-09-30")) / 864e5), dias2 = Math.round((Date.parse(venc) - Date.parse("2026-10-20")) / 864e5);
    await p.evaluate(([m, d1, d2]) => {
      localStorage.setItem("historico", JSON.stringify([{ m: { ...m, dias: d1 }, ativo: "PETR4", data: "2026-09-30", id: 1 }, { m: { ...m, dias: d2 }, ativo: "PETR4", data: "2026-10-20", id: 2 }]));
    }, [m, dias1, dias2]);
    await p.reload(); await p.waitForSelector("#nav"); await p.waitForTimeout(800);   // marcação em segundo plano
    await p.click('#nav [data-nav="desemp"]'); await p.click('[data-per="tudo"]'); await p.waitForTimeout(300);
    const desemp = await p.innerText("#app");
    const dBR = (iso) => iso.split("-").reverse().join("/");
    confere(`Desempenho: a operação 1 sai no alvo no dia certo, com ${fmt(rAlvo)}`, desemp.includes(`saiu no alvo em ${dBR(dAlvo)}`) && desemp.includes(fmt(rAlvo)), desemp.slice(0, 600));
    confere("Desempenho: a operação 2 (em aberto) fica fora do resultado", /1 operação ainda está em aberto/.test(desemp));
    await p.click('#nav [data-nav="acomp"]'); await p.waitForTimeout(200);
    const lista = await p.innerText("#app");
    confere("Minhas operações: só a operação 2 continua aberta", /\b1 simulada\b/.test(lista) && (lista.match(/Trava de alta/g) || []).length === 1, lista.slice(0, 300));
    await p.click('[data-op="2"]'); await p.waitForTimeout(300);
    const sua = await p.innerText("#app");
    confere(`Sua operação: "Se encerrar hoje" com ${fmt(rHoje)} no fechamento do último dia`, sua.includes("Se encerrar hoje") && sua.includes(fmt(rHoje)) && sua.includes(dBR(dFim)), sua.slice(0, 400));
    confere("sem erros na página", erros.length === 0, erros);
  } finally { await b.close(); srv.kill(); fs.rmSync(dir, { recursive: true, force: true }); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
