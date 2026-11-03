// Carregador do app nativo (build_nativo.py): dados do site, cópia guardada no aparelho e snapshot embutido.
// Dois servidores locais: um serve o app (como o Capacitor) e outro imita o site publicado (outra origem, com CORS).
// Uso: python3 build.py && node testes/nativo.js
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), os = require('os'), path = require('path'), { execFileSync } = require('child_process');
const RAIZ = path.join(__dirname, '..'), EMB = JSON.parse(fs.readFileSync(path.join(RAIZ, 'snapshot.json'), 'utf8'));
const comData = (d) => { const s = JSON.parse(JSON.stringify(EMB)); s.por_data = { [d]: s.por_data[EMB.data] }; s.data = d; return s; };
const NOVO = comData('2099-01-02'), VELHO = comData('2000-01-03');
let modo = 'novo'; const pedidos = [];
const site = http.createServer((q, r) => {
  pedidos.push(q.url); const cab = { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json' };
  if (q.url.startsWith('/precos/')) { r.writeHead(200, cab); return r.end(JSON.stringify({ data: 'x', op: {} })); }
  if (q.url !== '/snapshot.json') { r.writeHead(404, cab); return r.end(); }
  if (modo === 'fora') { r.writeHead(500, cab); return r.end(); }
  if (modo === 'lento') return setTimeout(() => { r.writeHead(200, cab); r.end(JSON.stringify(NOVO)); }, 8000);
  r.writeHead(200, cab); r.end(JSON.stringify(modo === 'velho' ? VELHO : NOVO));
});
const www = fs.mkdtempSync(path.join(os.tmpdir(), 'nativo-'));
const app = http.createServer((q, r) => { r.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); r.end(fs.readFileSync(path.join(www, 'index.html'))); });
const ouvir = (s) => new Promise((ok) => s.listen(0, '127.0.0.1', () => ok(s.address().port)));
(async () => {
  const pSite = await ouvir(site), pApp = await ouvir(app);
  execFileSync('python3', ['build_nativo.py', '--base', `http://127.0.0.1:${pSite}/`, '--saida', www], { cwd: RAIZ });
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  const p = await ctx.newPage(), erros = []; let falhas = 0;
  p.on('pageerror', (e) => erros.push(e.message));
  const abrir = async () => { const t0 = Date.now(); await p.goto(`http://127.0.0.1:${pApp}/`);
    await p.waitForFunction(() => document.getElementById('nav').innerHTML.length > 0, null, { timeout: 15000 });
    return { data: await p.evaluate(() => SNAP.data), ms: Date.now() - t0 }; };
  const caso = (nome, ok, info) => { console.log((ok ? 'OK    ' : 'FALHA ') + nome + (ok ? '' : '  -> ' + JSON.stringify(info))); if (!ok) falhas++; };
  let r;
  modo = 'novo'; r = await abrir();
  caso('site com dados novos: usa os do site', r.data === NOVO.data && (await p.evaluate(() => BASE_DADOS)) === `http://127.0.0.1:${pSite}/`, r);
  await p.evaluate(() => precosDia(SNAP.data)); await p.waitForTimeout(300);
  caso('preços diários vêm do site', pedidos.includes(`/precos/${NOVO.data}.json`), pedidos.slice(-3));
  modo = 'fora'; r = await abrir();
  caso('sem internet: usa a cópia guardada no aparelho', r.data === NOVO.data, r);
  await p.evaluate(() => new Promise((ok) => { const q = indexedDB.deleteDatabase('montador'); q.onsuccess = q.onerror = q.onblocked = () => ok(); }));
  r = await abrir();
  caso('sem internet e sem cópia: usa o snapshot embutido', r.data === EMB.data, r);
  modo = 'velho'; r = await abrir();
  caso('site com dados mais velhos que os embutidos: usa os embutidos', r.data === EMB.data, r);
  modo = 'lento';
  const t0 = Date.now(); const nav = p.goto(`http://127.0.0.1:${pApp}/`); await nav;
  const carregando = await p.locator('text=Carregando preços').count();
  await p.waitForFunction(() => document.getElementById('nav').innerHTML.length > 0, null, { timeout: 15000 });
  const ms = Date.now() - t0, d = await p.evaluate(() => SNAP.data);
  caso('site lento: mostra "Carregando preços…" e segue em ~5 s com o que tem', carregando === 1 && ms >= 4500 && ms < 8000 && d === EMB.data, { carregando, ms, d });
  caso('sem erros na página', erros.length === 0, erros);
  await b.close(); site.close(); app.close(); fs.rmSync(www, { recursive: true, force: true });
  console.log(falhas ? `\n${falhas} caso(s) falharam` : '\ntodos os casos passaram'); process.exit(falhas ? 1 : 0);
})();
