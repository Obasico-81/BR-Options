// Site no domínio (build_site.py): app em /app/, raiz leva ao app, endereços antigos sem /app/ vão para /app/ e os
// dados do dia também na raiz (APK antigo). Servidor local que imita o GitHub Pages (pasta → index.html; o que não
// existe → 404.html com status 404).
// Uso: python3 build.py && python3 build_pwa.py && python3 build_site.py && node testes/site.js
const http = require("http"), fs = require("fs"), path = require("path"), { chromium } = require("playwright");
const RAIZ = path.join(__dirname, "..", "site");
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };
const TIPOS = { ".html": "text/html; charset=utf-8", ".json": "application/json", ".js": "text/javascript", ".webmanifest": "application/manifest+json", ".png": "image/png" };
const srv = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname), f = path.join(RAIZ, p);
  if (!f.startsWith(RAIZ)) { res.writeHead(400); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404, { "Content-Type": TIPOS[".html"] }); return res.end(fs.readFileSync(path.join(RAIZ, "404.html"))); }
  res.writeHead(200, { "Content-Type": TIPOS[path.extname(f)] || "application/octet-stream", "Access-Control-Allow-Origin": "*" }); res.end(fs.readFileSync(f));
});
(async () => {
  confere("site gerado: app, raiz, 404 e dados na raiz", ["app/index.html", "app/manifest.webmanifest", "app/sw.js", "index.html", "404.html", "snapshot.json"].every((f) => fs.existsSync(path.join(RAIZ, f))));
  await new Promise((r) => srv.listen(0, "127.0.0.1", r)); const B = `http://127.0.0.1:${srv.address().port}`;
  const b = await chromium.launch(), p = await (await b.newContext({ serviceWorkers: "block" })).newPage(), erros = [];
  p.on("pageerror", (e) => erros.push(e.message));
  try {
    await p.goto(B + "/"); await p.waitForURL(/\/app\/$/); await p.waitForSelector("#nav");
    confere("raiz leva ao app (/app/)", new URL(p.url()).pathname === "/app/");
    await p.goto(B + "/?teste=1"); await p.waitForURL(/\/app\/\?teste=1$/); await p.waitForSelector("#nav");
    confere("raiz mantém ?teste=1", p.url().endsWith("/app/?teste=1"));
    await p.goto(B + "/termos.html"); await p.waitForURL(/\/app\/termos\.html$/);
    confere("link antigo sem /app/ (termos) vai para /app/termos.html", new URL(p.url()).pathname === "/app/termos.html");
    const snapRaiz = await (await fetch(B + "/snapshot.json")).json(), snapApp = await (await fetch(B + "/app/snapshot.json")).json();
    confere("dados do dia na raiz (APK antigo) e em /app/ (APK novo), iguais", snapRaiz.data && snapRaiz.data === snapApp.data && snapRaiz.atualizado_em === snapApp.atualizado_em, [snapRaiz.data, snapApp.data]);
    const dia = fs.readdirSync(path.join(RAIZ, "precos")).sort().pop();
    confere("preços diários na raiz e em /app/", (await fetch(`${B}/precos/${dia}`)).status === 200 && (await fetch(`${B}/app/precos/${dia}`)).status === 200, dia);
    const man = await (await fetch(B + "/app/manifest.webmanifest")).json();
    confere("app instalável em /app/ (manifest com início e escopo relativos)", man.start_url === "./" && man.scope === "./");
    confere("sem erros de página", erros.length === 0, erros);
  } finally { await b.close(); srv.close(); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
