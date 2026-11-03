// Cópia dos dados (Ajustes): exportar baixa um JSON com o que o app guarda; importar junta as operações sem duplicar
// nem apagar as do aparelho e só traz os ajustes se o aparelho ainda não tiver os seus; arquivo inválido é recusado.
// Uso: python3 build.py && python3 build_pwa.py && node testes/copia.js
const path = require("path"), fs = require("fs"), os = require("os");
const { chromium } = require("playwright");
const RAIZ = path.join(__dirname, ".."), ARQ = "file://" + path.join(RAIZ, "pwa", "index.html");
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };
(async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "copia-"));
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 390, height: 844 }, acceptDownloads: true });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  const p = await ctx.newPage(), erros = []; p.on("pageerror", (e) => erros.push(e.message));
  const texto = () => p.innerText("#app"), ajustes = async () => { await p.click('#nav [data-nav="cad"]'); await p.waitForTimeout(150); };
  const importa = async (arquivo) => { await p.setInputFiles("#arq-importar", arquivo); await p.waitForTimeout(600); await p.waitForSelector("#nav"); };
  try {
    await p.goto(ARQ); await p.waitForSelector("#nav");
    // duas operações (uma real) e ajustes próprios
    await p.evaluate(() => { localStorage.clear(); S.perda = 3000; S.capital = 30000; S.tema = "claro"; S.cad.corretagem = 4.9;
      let m = null; for (const at of Object.keys(SNAP.ativos)) { S.ativo = at; for (const t of ["alta", "baixa", "forte"]) { m = montagem(t); if (typeof m !== "string") break; } if (typeof m !== "string") break; }
      save("estado", S);
      save("historico", [{ m, ativo: S.ativo, data: S.data, id: 101, cor: 4.9 },
        { m: M.execucao(m, { lotes: m.lotes, precos: m.pernas.map(([l, x]) => (l > 0 ? x.a : x.b)) }), ativo: S.ativo, data: S.data, id: 102, cor: 4.9, real: { data: S.data, custos: 10, montada: {} } }]); });
    await p.reload(); await p.waitForSelector("#nav"); await ajustes();
    confere("Ajustes mostra quantas operações há e que não há cópia ainda", /2 operações neste aparelho \(1 real\) · nenhuma cópia exportada ainda/.test(await texto()));
    const [dl] = await Promise.all([p.waitForEvent("download"), p.click("#exportar")]);
    const arq = path.join(tmp, dl.suggestedFilename()); await dl.saveAs(arq);
    const copia = JSON.parse(fs.readFileSync(arq, "utf8")), local = await p.evaluate(() => ({ h: JSON.parse(localStorage.getItem("historico")), e: JSON.parse(localStorage.getItem("estado")) }));
    confere("exportar: arquivo com app, versão, histórico e ajustes iguais aos do aparelho", /^montador-opcoes-dados-\d{4}-\d{2}-\d{2}\.json$/.test(dl.suggestedFilename()) && copia.app === "montador-opcoes" && copia.versao === 1
      && JSON.stringify(copia.historico) === JSON.stringify(local.h) && JSON.stringify(copia.estado) === JSON.stringify(local.e), dl.suggestedFilename());
    confere("exportar: avisa e guarda a data da última cópia", (await texto()).includes("Cópia exportada") && /última cópia exportada em \d{2}\/\d{2}\/\d{4}/.test(await texto()));
    // aparelho vazio: importar restaura operações e ajustes
    await p.evaluate(() => localStorage.clear()); await p.reload(); await p.waitForSelector("#nav"); await ajustes();
    await importa(arq);
    const rest = await p.evaluate(() => ({ ids: load("historico", []).map((o) => o.id), cor: S.cad.corretagem, tema: document.documentElement.dataset.theme || "", tela }));
    confere("importar em aparelho vazio: operações e ajustes de volta", JSON.stringify(rest.ids) === "[101,102]" && rest.cor === 4.9 && rest.tema === "light", rest);
    confere("importar: mostra o que entrou", /2 operações importadas\. Ajustes do arquivo aplicados\. Cópia de \d{2}\/\d{2}\/\d{4}\./.test(await texto()), (await texto()).slice(0, 400));
    // de novo: não duplica
    await importa(arq);
    confere("importar a mesma cópia de novo não duplica", JSON.stringify(await p.evaluate(() => load("historico", []).map((o) => o.id))) === "[101,102]" && /0 operações importadas; 2 já estavam neste aparelho\./.test(await texto()), (await texto()).slice(0, 300));
    // junta: operação nova no aparelho + cópia antiga sem ela
    await p.evaluate(() => { const h = load("historico", []); h.push(Object.assign({}, h[0], { id: 103 })); save("historico", h.filter((o) => o.id !== 101)); });
    await importa(arq);
    confere("importar junta: mantém a operação nova do aparelho e traz a que faltava", JSON.stringify(await p.evaluate(() => load("historico", []).map((o) => o.id).sort())) === "[101,102,103]");
    // arquivos ruins
    const ruim = path.join(tmp, "ruim.json"); fs.writeFileSync(ruim, "isto não é json");
    await importa(ruim); confere("arquivo que não é JSON é recusado", (await texto()).includes("Este arquivo não é uma cópia do app."));
    const outro = path.join(tmp, "outro.json"); fs.writeFileSync(outro, JSON.stringify({ app: "outro", historico: [] }));
    await importa(outro); confere("JSON de outro app é recusado", (await texto()).includes("Este arquivo não é uma cópia do app."));
    const nova = path.join(tmp, "nova.json"); fs.writeFileSync(nova, JSON.stringify(Object.assign({}, copia, { versao: 99 })));
    await importa(nova); confere("cópia de versão mais nova é recusada", (await texto()).includes("versão mais nova do app"));
    confere("histórico intacto depois dos arquivos ruins", (await p.evaluate(() => load("historico", []).length)) === 3);
    await p.click('#nav [data-nav="obj"]'); await ajustes();
    confere("a mensagem some ao sair de Ajustes", !(await texto()).includes("versão mais nova"));
    confere("sem erros na página", erros.length === 0, erros);
  } catch (e) { confere("fluxo sem exceção", false, e.message.split("\n")[0]); }
  await b.close(); fs.rmSync(tmp, { recursive: true, force: true });
  console.log(falhas ? `\n${falhas} caso(s) falharam` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
