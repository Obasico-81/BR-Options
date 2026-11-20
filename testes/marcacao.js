// Marcação diária: contas do montador (resultadoNoDia, regraDeSaida, saidaDaRegra) e o app servido por HTTP com preços sintéticos.
// Uso: node testes/marcacao.js   (precisa de python3 e do Playwright; gera pwa/index.html antes: python3 build.py && python3 build_pwa.py)
const path = require("path"), fs = require("fs"), os = require("os"), { spawn } = require("child_process");
const RAIZ = path.join(__dirname, ".."), M = require(path.join(RAIZ, "montador.js")), snap = require(path.join(RAIZ, "snapshot.json"));
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };

// ---------- 1. contas ----------
const a = snap.ativos.PETR4;
// trava de alta: +1 call, -1 call. O vencimento de ~45 dias pode estar sem liquidez no dia (ex.: 05/11/2026): tenta outros
// prazos; o vencimento da montagem não importa aqui (as datas do teste vêm de `venc`)
const m = [45, 30, 15, 60, 75, 90].map((p) => M.montar("alta", a.S, a.chain, a.iv, 500, { caixa: 12000, prazoAlvo: p })).find((x) => typeof x !== "string");
if (!m) { console.log("FALHA nenhuma trava de alta de PETR4 monta no snapshot, em nenhum prazo"); process.exit(1); }
const [[, longa], [, curta]] = m.pernas;
// preços que dão um resultado-alvo r pelo preço médio: (médio da longa − médio da curta)·100·lotes − prêmio = r
const precosPara = (r) => { const v = (r + m.premio) / (100 * m.lotes); return { [longa.s]: [+(v + 0.975).toFixed(4), +(v + 1.025).toFixed(4)], [curta.s]: [0.975, 1.025] }; };
const meio = (o) => (o.b + o.a) / 2;
confere("resultadoNoDia: desfazer no dia da entrada, pelo preço médio, custa metade do spread das duas pernas",
  M.resultadoNoDia(m, Object.fromEntries(a.chain.map((o) => [o.s, [o.b, o.a]]))) === Math.round(((meio(longa) - meio(curta)) * 100 * m.lotes - m.premio) * 100) / 100);
confere("resultadoNoDia: nunca abaixo do risco máximo (curta com venda absurda no fechamento)",
  M.resultadoNoDia(m, { [longa.s]: [0.01, 0.02], [curta.s]: [0.5, 99] }) === -m.perdaMax);
confere("resultadoComPrecos: encerramento registrado, sem piso", M.resultadoComPrecos(m, [0.01, 99]) === Math.round(((0.01 - 99) * 100 * m.lotes - m.premio) * 100) / 100);
confere("trava sem limite de perda (só alvo e prazo)", m.stop === null && m.alvo > 0 && m.saidaDias === 7);
confere("resultadoNoDia: preço que leva a +R$ 200 dá +R$ 200", Math.abs(M.resultadoNoDia(m, precosPara(200)) - 200) < 0.01, M.resultadoNoDia(m, precosPara(200)));
confere("resultadoNoDia: perna sem preço no dia -> null", M.resultadoNoDia(m, { [longa.s]: [1, 1.1] }) === null);
const venc = "2026-12-18";
confere("regraDeSaida: alvo", JSON.stringify(M.regraDeSaida(m, [{ d: "2026-10-01", r: 50 }, { d: "2026-10-02", r: null }, { d: "2026-10-05", r: m.alvo + 1 }], venc)) === JSON.stringify({ regra: "alvo", d: "2026-10-05", r: m.alvo + 1 }));
confere("regraDeSaida: trava não sai por perda grande (sem limite); sai no alvo depois", M.regraDeSaida(m, [{ d: "2026-10-01", r: -m.perdaMax }, { d: "2026-10-05", r: m.alvo + 1 }], venc)?.regra === "alvo");
// put vendida: a de PETR4 pode estar sem liquidez no dia (ex.: 13/11/2026); procura em outros prazos e ativos
const pv = Object.values(snap.ativos).flatMap((x) => [45, 30, 60, 15, 75, 90].map((p) => [x, p])).map(([x, p]) => M.montar("alta_com_caixa", x.S, x.chain, x.iv, 1e6, { caixa: 1e6, prazoAlvo: p })).find((x) => typeof x !== "string");
confere("regraDeSaida: put vendida mantém o limite e sai nele antes do alvo", typeof pv !== "string" && pv.stop < 0 && M.regraDeSaida(pv, [{ d: "2026-10-01", r: pv.stop - 1 }, { d: "2026-10-05", r: pv.alvo + 1 }], venc)?.regra === "limite");
confere("regraDeSaida: prazo (7 dias antes do vencimento)", JSON.stringify(M.regraDeSaida(m, [{ d: "2026-12-10", r: 10 }, { d: "2026-12-11", r: 20 }], venc)) === JSON.stringify({ regra: "prazo", d: "2026-12-11", r: 20 }));
confere("regraDeSaida: dia sem preço e dias no/após o vencimento são ignorados", M.regraDeSaida(m, [{ d: "2026-10-01", r: null }, { d: venc, r: m.alvo + 1 }], venc) === null);
// saída de quem segue o app: regra no fechamento, saída no pregão seguinte (o resultado desse pregão)
confere("saidaDaRegra: dispara no alvo e sai no pregão seguinte, com o resultado dele", JSON.stringify(M.saidaDaRegra(m, [{ d: "2026-10-01", r: 50 }, { d: "2026-10-05", r: m.alvo + 1 }, { d: "2026-10-06", r: 30 }], venc)) === JSON.stringify({ regra: "alvo", d: "2026-10-05", dSaida: "2026-10-06", r: 30 }));
confere("saidaDaRegra: pula pregão sem preço depois do disparo", M.saidaDaRegra(m, [{ d: "2026-10-05", r: m.alvo + 1 }, { d: "2026-10-06", r: null }, { d: "2026-10-07", r: 10 }], venc)?.dSaida === "2026-10-07");
confere("saidaDaRegra: sem pregão seguinte ainda -> pendente", JSON.stringify(M.saidaDaRegra(m, [{ d: "2026-10-01", r: 50 }, { d: "2026-10-05", r: m.alvo + 1 }], venc)) === JSON.stringify({ regra: "alvo", d: "2026-10-05", pendente: true }));
confere("saidaDaRegra: o dia do vencimento não serve de saída (fica pendente; o app usa o vencimento)", M.saidaDaRegra(m, [{ d: "2026-12-11", r: 20 }, { d: venc, r: 99 }], venc)?.pendente === true);
confere("saidaDaRegra: nenhuma regra -> null", M.saidaDaRegra(m, [{ d: "2026-10-01", r: 50 }], venc) === null);
// compra simples: a call de PETR4 pode estar sem liquidez no dia (ex.: 19/11/2026); procura em outros ativos e prazos
const compra = Object.values(snap.ativos).flatMap((x) => [45, 30, 60, 15, 75, 90].map((pz) => [x, pz])).map(([x, pz]) => M.montarAposta("alta", x.S, x.chain, x.iv, 2000, { prazoAlvo: pz })).find((x) => typeof x !== "string");
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
  const rAlvo = Math.max(200, Math.ceil(m.alvo)), rHoje = Math.min(120, Math.floor(m.alvo / 2)), rAntes = Math.min(50, Math.floor(m.alvo / 4)), rSeg = rAlvo - 13;
  const dSeg = dias[6];   // pregão seguinte ao disparo do alvo: é nele que a operação 1 sai
  const fmt = (v) => "+R$ " + v.toLocaleString("pt-BR");
  grava(dias[1], rAntes); grava(dAlvo, rAlvo); grava(dSeg, rSeg); grava(dFim, rHoje);
  const porta = 8700 + Math.floor(Math.random() * 200);
  const srv = spawn("python3", ["-m", "http.server", String(porta), "--bind", "127.0.0.1", "--directory", dir], { stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 800));
  const { chromium } = require("playwright");
  // tela de celular, como os outros testes (o layout de computador tem teste próprio: testes/desktop.js)
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 390, height: 844 } }); const erros = []; p.on("pageerror", (e) => erros.push(e.message));
  try {
    await p.goto(`http://127.0.0.1:${porta}/index.html`); await p.waitForSelector("#nav");
    const dias1 = Math.round((Date.parse(venc) - Date.parse("2026-09-30")) / 864e5), dias2 = Math.round((Date.parse(venc) - Date.parse("2026-10-20")) / 864e5);
    await p.evaluate(([m, d1, d2, rHoje]) => {
      // a 3 tem o alvo logo abaixo do resultado do último dia: dispara no último fechamento e fica pendente (sai no próximo pregão)
      localStorage.setItem("historico", JSON.stringify([{ m: { ...m, dias: d1 }, ativo: "PETR4", data: "2026-09-30", id: 1 }, { m: { ...m, dias: d2 }, ativo: "PETR4", data: "2026-10-20", id: 2 },
        { m: { ...m, dias: d2, alvo: rHoje - 1 }, ativo: "PETR4", data: "2026-10-20", id: 3 }]));
    }, [m, dias1, dias2, rHoje]);
    await p.reload(); await p.waitForSelector("#nav"); await p.waitForTimeout(800);   // marcação em segundo plano
    // Operações: desempenho no topo (a 1, encerrada no alvo), as em aberto na sequência (só a 2)
    await p.click('#nav [data-nav="acomp"]'); await p.click('[data-per="tudo"]'); await p.waitForTimeout(300);
    const lista = await p.innerText("#abertas");
    confere("Operações, em aberto: a 2 e a 3 (regra disparada no último fechamento, saída ainda por vir)", /\b2 simuladas\b/.test(lista) && (lista.match(/Trava de alta/g) || []).length === 2 && (lista.match(/regra atingida: sai no próximo pregão/g) || []).length === 1, lista.slice(0, 400));
    await p.click('summary:has-text("Encerradas no período")'); await p.waitForTimeout(150);
    const desemp = await p.innerText("#app");
    const dBR = (iso) => iso.split("-").reverse().join("/");
    confere(`Desempenho (topo de Operações): a operação 1 dispara no alvo e sai no pregão seguinte, com ${fmt(rSeg)}`, desemp.includes(`saiu no alvo em ${dBR(dSeg)}`) && desemp.includes(fmt(rSeg)) && !desemp.includes(fmt(rAlvo)) && /Encerradas no período \(1\)/.test(desemp), desemp.slice(0, 600));
    await p.click('[data-op="2"]'); await p.waitForTimeout(300);
    const sua = await p.innerText("#app");
    confere(`Sua operação: "Se encerrar hoje" com ${fmt(rHoje)} no fechamento do último dia`, sua.includes("Se encerrar hoje") && sua.includes(fmt(rHoje)) && sua.includes(dBR(dFim)), sua.slice(0, 400));
    await p.click('#nav [data-nav="acomp"]'); await p.waitForTimeout(200); await p.click('[data-op="3"]'); await p.waitForTimeout(300);
    const pend = await p.innerText("#app");
    confere("Sua operação 3: regra atingida no último fechamento, saída no próximo pregão", pend.includes("A regra “Sair no alvo” foi atingida") && pend.includes(`no fechamento de ${dBR(dFim)}`) && pend.includes("A saída é no próximo pregão"), pend.slice(0, 600));
    confere("sem erros na página", erros.length === 0, erros);
  } finally { await b.close(); srv.kill(); fs.rmSync(dir, { recursive: true, force: true }); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
