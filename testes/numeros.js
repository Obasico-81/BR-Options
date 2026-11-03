// Uso: node testes/numeros.js [caminho do pwa/index.html]
// Digitação no formato brasileiro nos campos numéricos (navegador em pt-BR).
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ locale: 'pt-BR', viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 }); const p = await ctx.newPage();
  const erros = []; p.on('pageerror', e => erros.push(e.message));
  await p.goto('file://' + (process.argv[2] || require('path').join(__dirname, '..', 'pwa', 'index.html'))); await p.waitForSelector('#nav'); await p.evaluate(() => localStorage.clear()); await p.reload(); await p.waitForSelector('#nav');
  const digita = async (sel, txt) => { await p.fill(sel, ''); await p.click(sel); await p.keyboard.type(txt); await p.press(sel, 'Tab'); await p.waitForTimeout(120); };
  const casos = [];
  await p.click('#nav [data-nav="cad"]');
  for (const [txt, esp] of [['4,90', 4.9], ['4.90', 4.9], ['R$ 5,5', 5.5], ['', null], ['abc', null]]) { await digita('#ccorrtg', txt); casos.push(['corretagem "' + txt + '"', await p.evaluate(() => S.cad.corretagem), esp]); }
  await digita('#ccorrtg', '4,90'); casos.push(['campo mostra', await p.inputValue('#ccorrtg'), '4,90']);
  await p.click('#nav [data-nav="obj"]'); await p.click('[data-perfil="1"]');
  for (const [sel, txt, chave, esp] of [['#capital', '12.000', 'capital', 12000], ['#capital', '15000', 'capital', 15000], ['#perda', '1.500', 'perda', 1500], ['#perda', '500', 'perda', 500], ['#perda', 'xyz', 'perda', 500]]) {
    if (!(await p.$(sel))) await p.click('[data-perfil="1"]'); await digita(sel, txt); casos.push([sel + ' "' + txt + '"', await p.evaluate((k) => S[k], chave), esp]);
  }
  casos.push(['capital mostra', await p.inputValue('#capital'), '15.000']);
  if (process.argv[3]) await p.screenshot({ path: process.argv[3] + '/perfil.png' });
  await p.evaluate(() => { tela = 'sinal'; render(); }); await p.waitForTimeout(150);
  await digita('#sentrada', '50,10'); casos.push(['sinal entrada "50,10"', await p.evaluate(() => S.sinal.entrada), 50.1]);
  await digita('#salvo', '58.5'); casos.push(['sinal alvo "58.5"', await p.evaluate(() => S.sinal.alvo), 58.5]);
  let falhas = 0; for (const [n, v, e] of casos) { const ok = v === e; if (!ok) falhas++; console.log((ok ? 'OK    ' : 'FALHA ') + n + ' -> ' + JSON.stringify(v) + (ok ? '' : ' (esperado ' + JSON.stringify(e) + ')')); }
  console.log(erros.length ? 'ERROS ' + erros.join(' | ') : 'sem erros na página', '|', falhas ? falhas + ' falha(s)' : 'todos passaram'); await b.close(); process.exit(falhas || erros.length ? 1 : 0);
})();
