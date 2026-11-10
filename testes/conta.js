// Conta (Supabase): entrar com código por e-mail, cópia das operações e do perfil na nuvem entre dois aparelhos,
// apagar, sair e excluir a conta. O Supabase é simulado (rotas do Playwright), com a mesma regra do banco: cada usuário
// só lê e grava as próprias linhas.
// Uso: node testes/conta.js CAMINHO/pwa/index.html
const { chromium } = require("playwright");
const arq = "file://" + process.argv[2];
const URL_SB = "https://xoljwckdiedcfoygbiij.supabase.co";
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };

// ---------- Supabase simulado ----------
const banco = { usuarios: {}, operacoes: [], perfis: [], pedidos: [] };   // usuarios: email -> id
const uidDe = (h) => { const m = /^Bearer tok-(.+)$/.exec(h.authorization || ""); return m ? m[1] : null; };
async function servidor(route) {
  const req = route.request(), u = new URL(req.url()), metodo = req.method(), h = req.headers(), corpo = req.postData() ? JSON.parse(req.postData()) : null;
  const json = (status, b) => route.fulfill({ status, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: b === undefined ? "" : JSON.stringify(b) });
  banco.pedidos.push(metodo + " " + u.pathname + u.search);
  if (metodo === "OPTIONS") return route.fulfill({ status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*" } });
  if (!h.apikey) return json(401, { msg: "sem apikey" });
  if (u.pathname === "/auth/v1/otp") return corpo.email === "limite@teste.dev" ? json(429, { code: 429, error_code: "over_email_send_rate_limit", msg: "email rate limit exceeded" }) : json(200, {});
  if (u.pathname === "/auth/v1/verify") {
    if (corpo.token !== "123456") return json(403, { code: 403, error_code: "otp_expired", msg: "Token has expired or is invalid" });
    const id = banco.usuarios[corpo.email] || (banco.usuarios[corpo.email] = "u" + (Object.keys(banco.usuarios).length + 1));
    return json(200, { access_token: "tok-" + id, refresh_token: "ref-" + id, expires_in: 3600, expires_at: Math.floor(Date.now() / 1000) + 3600, user: { id, email: corpo.email } });
  }
  if (u.pathname === "/auth/v1/token") { const id = (corpo.refresh_token || "").replace("ref-", ""); return json(200, { access_token: "tok-" + id, refresh_token: "ref-" + id, expires_in: 3600, user: { id } }); }
  const uid = uidDe(h);
  if (u.pathname === "/auth/v1/logout") return json(204);
  if (!uid) return json(401, { message: "JWT ausente" });
  const tabela = u.pathname === "/rest/v1/operacoes" ? "operacoes" : u.pathname === "/rest/v1/perfis" ? "perfis" : null;
  if (tabela && metodo === "GET") return json(200, banco[tabela].filter((r) => r.user_id === uid).map(({ user_id, ...r }) => r));
  if (tabela && metodo === "POST") {
    if (corpo.some((r) => r.user_id !== uid)) return json(403, { message: "new row violates row-level security policy" });
    for (const r of corpo) {
      const i = banco[tabela].findIndex((x) => x.user_id === uid && (tabela === "perfis" || x.id === r.id));
      if (i >= 0) banco[tabela][i] = { ...banco[tabela][i], ...r }; else banco[tabela].push({ ...r });
    }
    return json(201);
  }
  if (u.pathname === "/rest/v1/rpc/excluir_minha_conta") {
    banco.operacoes = banco.operacoes.filter((r) => r.user_id !== uid); banco.perfis = banco.perfis.filter((r) => r.user_id !== uid);
    for (const e of Object.keys(banco.usuarios)) if (banco.usuarios[e] === uid) delete banco.usuarios[e];
    return json(204);
  }
  return json(404, { message: "rota não simulada: " + u.pathname });
}

async function aparelho(b) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  await ctx.route(URL_SB + "/**", servidor);
  const p = await ctx.newPage(), erros = [];
  p.on("pageerror", (e) => erros.push(e.message));
  p.on("dialog", (d) => d.accept());
  await p.goto(arq); await p.waitForSelector("#nav");
  return { p, erros, ctx };
}
const texto = (p) => p.innerText("#app");
const espera = (ms) => new Promise((r) => setTimeout(r, ms));
async function entrar(p, email, codigo = "123456") {
  await p.click('#nav [data-nav="cad"]'); await p.click("#conta-entrar");
  await p.fill("#lg-email", email); await p.click("#lg-enviar"); await p.waitForSelector("#lg-codigo");
  await p.fill("#lg-codigo", codigo); await p.click("#lg-entrar"); await espera(400);
}
const sincronizado = (p) => p.waitForFunction(() => !sinc.rodando && sinc.ultima, null, { timeout: 5000 });

(async () => {
  const b = await chromium.launch();
  try {
    // ---------- aparelho 1: duas operações e perfil antes de entrar ----------
    const A = await aparelho(b);
    await A.p.evaluate(() => {
      let m = null; S.perda = 1e6; S.capital = 1e7;
      for (const at of Object.keys(SNAP.ativos)) { S.ativo = at; m = montagem("alta"); if (typeof m !== "string") break; }
      save("historico", [{ m, ativo: S.ativo, data: S.data, id: 101 }, { m, ativo: S.ativo, data: S.data, id: 102 }]);
      S.capital = 7777; S.perda = 333; save("estado", S); render();
    });
    await A.p.click('#nav [data-nav="cad"]');
    confere("Ajustes sem conta: botão Entrar ou criar conta", /Entrar ou criar conta/.test(await texto(A.p)));
    await A.p.click("#conta-entrar");
    confere("tela de entrar: sem a barra de navegação", await A.p.evaluate(() => document.getElementById("nav").style.display === "none"));
    await A.p.fill("#lg-email", "sem-arroba"); await A.p.click("#lg-enviar");
    confere("e-mail inválido: mensagem", /Confira o e-mail digitado/.test(await texto(A.p)));
    await A.p.fill("#lg-email", "limite@teste.dev"); await A.p.click("#lg-enviar"); await espera(200);
    confere("limite de envio (429): mensagem de esperar", /Espere alguns minutos/.test(await texto(A.p)));
    await A.p.fill("#lg-email", "Joao@Teste.dev"); await A.p.click("#lg-enviar"); await A.p.waitForSelector("#lg-codigo");
    confere("código enviado: tela do código com o e-mail", /joao@teste\.dev/.test(await texto(A.p)));
    confere("reenviar bloqueado no começo", await A.p.isDisabled("#lg-reenviar"));
    await A.p.fill("#lg-codigo", "999999"); await A.p.click("#lg-entrar"); await espera(200);
    confere("código errado: mensagem", /Código errado ou vencido/.test(await texto(A.p)));
    await A.p.fill("#lg-codigo", "123 456"); await A.p.click("#lg-entrar"); await sincronizado(A.p);
    const tA = await texto(A.p);
    confere("entrou: volta a Ajustes com o e-mail e a sincronização", /joao@teste\.dev/.test(tA) && /Sincronizado às/.test(tA), tA.slice(0, 300));
    const u1 = banco.usuarios["joao@teste.dev"];
    confere("as 2 operações do aparelho subiram para a conta", banco.operacoes.filter((r) => r.user_id === u1 && !r.apagada).map((r) => r.id).sort().join() === "101,102");
    confere("o perfil subiu (capital e risco)", banco.perfis.some((r) => r.user_id === u1 && r.dados.capital === 7777 && r.dados.perda === 333));

    // ---------- aparelho 2: vazio; ao entrar, recebe tudo ----------
    const B2 = await aparelho(b);
    await entrar(B2.p, "joao@teste.dev"); await sincronizado(B2.p);
    const h2 = await B2.p.evaluate(() => load("historico", []).map((o) => o.id).join());
    confere("aparelho 2: recebeu as 2 operações", h2 === "101,102", h2);
    confere("aparelho 2: recebeu o perfil", await B2.p.evaluate(() => S.capital === 7777 && S.perda === 333));

    // ---------- apagar no aparelho 2 chega ao aparelho 1; mudar no 1 chega ao 2 ----------
    await B2.p.evaluate(() => save("historico", load("historico", []).filter((o) => o.id !== 102)));
    await B2.p.evaluate(() => sincronizar()); await sincronizado(B2.p);
    confere("apagada no aparelho 2: marcada na conta", banco.operacoes.some((r) => r.id === 102 && r.apagada));
    await espera(20);
    await A.p.evaluate(() => { const h = load("historico", []); h[0].real = { data: S.data, custos: 1 }; save("historico", h); });
    await A.p.evaluate(() => sincronizar()); await espera(300);
    const h1 = await A.p.evaluate(() => load("historico", []).map((o) => o.id + (o.real ? "r" : "")).join());
    confere("aparelho 1: a apagada sumiu e a mudança daqui ficou", h1 === "101r", h1);
    await B2.p.evaluate(() => sincronizar()); await espera(300);
    confere("aparelho 2: recebeu a mudança do aparelho 1", await B2.p.evaluate(() => { const h = load("historico", []); return h.length === 1 && !!h[0].real; }));

    // ---------- outro usuário não vê nada do primeiro ----------
    const C = await aparelho(b);
    await entrar(C.p, "maria@teste.dev"); await sincronizado(C.p);
    confere("outra conta: começa vazia", await C.p.evaluate(() => load("historico", []).length === 0));

    // ---------- sessão vencida: renova sozinha ----------
    await A.p.evaluate(() => { sessao.expires_at = 0; });
    const antes = banco.pedidos.length;
    await A.p.evaluate(() => sincronizar()); await espera(300);
    confere("sessão vencida: renova e sincroniza", banco.pedidos.slice(antes).some((x) => x.startsWith("POST /auth/v1/token")) && await A.p.evaluate(() => !sinc.erro));

    // ---------- sair e excluir ----------
    await A.p.click('#nav [data-nav="cad"]'); await A.p.click("#conta-sair"); await espera(200);
    confere("saiu: volta o botão de entrar e as operações ficam no aparelho", /Entrar ou criar conta/.test(await texto(A.p)) && await A.p.evaluate(() => load("historico", []).length === 1));
    await B2.p.click('#nav [data-nav="cad"]'); await B2.p.click("#conta-excluir"); await espera(300);
    confere("excluiu: a conta e as operações saem do banco", !banco.usuarios["joao@teste.dev"] && !banco.operacoes.some((r) => r.user_id === u1) && !banco.perfis.some((r) => r.user_id === u1));
    confere("excluiu: o aparelho volta a não ter conta", /Entrar ou criar conta/.test(await texto(B2.p)));

    // ---------- boas-vindas: "Continuar sem conta" ----------
    const D = await aparelho(b);
    await D.p.evaluate(() => { tela = "login"; login.volta = "inicio"; render(); });
    confere("boas-vindas: tem Continuar sem conta", /Continuar sem conta/.test(await texto(D.p)));
    await D.p.click("#lg-sem");
    confere("Continuar sem conta: vai ao Início e não pergunta de novo", await D.p.evaluate(() => tela === "obj" && localStorage.getItem("semConta") === "1"));

    for (const [n, x] of [["aparelho 1", A], ["aparelho 2", B2], ["outra conta", C], ["boas-vindas", D]]) confere(`sem erros na página (${n})`, x.erros.length === 0, x.erros);
  } finally { await b.close(); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
