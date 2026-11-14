// Conta (Supabase): entrar com código por e-mail ou por SMS (celular), cópia das operações e do perfil na nuvem entre
// aparelhos, celular adicionado a uma conta de e-mail, apagar, sair e excluir a conta. O Supabase é simulado (rotas do Playwright), com a mesma regra do banco: cada usuário
// só lê e grava as próprias linhas.
// Uso: node testes/conta.js CAMINHO/pwa/index.html
const { chromium } = require("playwright");
const arq = "file://" + process.argv[2];
const URL_SB = "https://xoljwckdiedcfoygbiij.supabase.co";
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };

// ---------- Supabase simulado ----------
const banco = { usuarios: {}, fones: {}, pendente: {}, emails: {}, operacoes: [], perfis: [], pedidos: [], sms: [] };   // usuarios: email -> id; fones: +55... -> id
const novoId = () => "u" + (Object.keys(banco.usuarios).length + Object.keys(banco.fones).length + 1);
const usuario = (id) => ({ id, email: banco.emails[id] || "", phone: (Object.keys(banco.fones).find((f) => banco.fones[f] === id) || "").replace("+", "") });
const uidDe = (h) => { const m = /^Bearer tok-(.+)$/.exec(h.authorization || ""); return m ? m[1] : null; };
async function servidor(route) {
  const req = route.request(), u = new URL(req.url()), metodo = req.method(), h = req.headers(), corpo = req.postData() ? JSON.parse(req.postData()) : null;
  const json = (status, b) => route.fulfill({ status, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: b === undefined ? "" : JSON.stringify(b) });
  banco.pedidos.push(metodo + " " + u.pathname + u.search);
  if (metodo === "OPTIONS") return route.fulfill({ status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*" } });
  if (!h.apikey) return json(401, { msg: "sem apikey" });
  if (u.pathname === "/auth/v1/otp") {
    if (corpo.phone) {   // SMS pelo provedor (Twilio): só número no formato +55...; um número que o provedor recusa
      if (!/^\+\d{10,15}$/.test(corpo.phone)) return json(400, { code: 400, error_code: "validation_failed", msg: "Invalid phone number format (E.164 required)" });
      if (corpo.phone === "+5511900000000") return json(400, { code: 400, error_code: "sms_send_failed", msg: "Error sending confirmation OTP to provider" });
      banco.sms.push(corpo.phone + " " + corpo.channel); return json(200, {});
    }
    return corpo.email === "limite@teste.dev" ? json(429, { code: 429, error_code: "over_email_send_rate_limit", msg: "email rate limit exceeded" }) : json(200, {});
  }
  if (u.pathname === "/auth/v1/verify") {
    if (corpo.token !== "123456") return json(403, { code: 403, error_code: "otp_expired", msg: "Token has expired or is invalid" });
    let id;
    if (corpo.type === "sms") id = banco.fones[corpo.phone] || (banco.fones[corpo.phone] = novoId());
    else if (corpo.type === "phone_change") { id = uidDe(h); if (!id || banco.pendente[id] !== corpo.phone) return json(403, { code: 403, error_code: "otp_expired", msg: "Token has expired or is invalid" }); banco.fones[corpo.phone] = id; delete banco.pendente[id]; }
    else { id = banco.usuarios[corpo.email] || (banco.usuarios[corpo.email] = novoId()); banco.emails[id] = corpo.email; }
    return json(200, { access_token: "tok-" + id, refresh_token: "ref-" + id, expires_in: 3600, expires_at: Math.floor(Date.now() / 1000) + 3600, user: usuario(id) });
  }
  if (u.pathname === "/auth/v1/token") { const id = (corpo.refresh_token || "").replace("ref-", ""); return json(200, { access_token: "tok-" + id, refresh_token: "ref-" + id, expires_in: 3600, user: { id } }); }
  const uid = uidDe(h);
  if (u.pathname === "/auth/v1/logout") return json(204);
  if (!uid) return json(401, { message: "JWT ausente" });
  if (u.pathname === "/auth/v1/user" && metodo === "PUT") {   // celular novo numa conta: código por SMS para o número
    if (banco.fones[corpo.phone] && banco.fones[corpo.phone] !== uid) return json(422, { code: 422, error_code: "phone_exists", msg: "Phone number already registered by another user" });
    banco.pendente[uid] = corpo.phone; banco.sms.push(corpo.phone + " phone_change"); return json(200, usuario(uid));
  }
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
    for (const f of Object.keys(banco.fones)) if (banco.fones[f] === uid) delete banco.fones[f];
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
  await p.click('#nav [data-nav="cad"]'); await p.click("#conta-entrar"); await p.click('[data-modo="email"]');
  await p.fill("#lg-email", email); await p.click("#lg-enviar"); await p.waitForSelector("#lg-codigo");
  await p.fill("#lg-codigo", codigo); await p.click("#lg-entrar"); await espera(400);
}
async function entrarCel(p, fone, codigo = "123456") {
  await p.click('#nav [data-nav="cad"]'); await p.click("#conta-entrar");
  await p.fill("#lg-fone", fone); await p.click("#lg-enviar"); await p.waitForSelector("#lg-codigo");
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
    confere("tela de entrar: começa pelo celular, com a opção de e-mail", (await A.p.locator("#lg-fone").count()) === 1 && /Receber código por SMS/.test(await texto(A.p)) && (await A.p.locator('[data-modo="email"]').count()) === 1);
    await A.p.click('[data-modo="email"]');
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

    // ---------- celular: entrar por SMS, adicionar o celular numa conta de e-mail ----------
    const E = await aparelho(b);
    await E.p.click('#nav [data-nav="cad"]'); await E.p.click("#conta-entrar");
    await E.p.fill("#lg-fone", "1234"); await E.p.click("#lg-enviar");
    confere("celular inválido: mensagem com o formato", /Confira o número: DDD e celular/.test(await texto(E.p)));
    await E.p.fill("#lg-fone", "(11) 3333-4444"); await E.p.click("#lg-enviar");
    confere("telefone fixo (sem o 9): não envia", /Confira o número/.test(await texto(E.p)) && !banco.sms.some((x) => x.startsWith("+55113333")));
    await E.p.fill("#lg-fone", "(11) 90000-0000"); await E.p.click("#lg-enviar"); await espera(200);
    confere("provedor recusa o envio: mensagem para conferir o número", /Não deu para enviar o SMS/.test(await texto(E.p)));
    await E.p.fill("#lg-fone", "(21) 98888-7777"); await E.p.click("#lg-enviar"); await E.p.waitForSelector("#lg-codigo");
    confere("código por SMS: tela do código com o número e envio em +55, canal sms", /por SMS para \(21\) 98888-7777/.test(await texto(E.p)) && banco.sms.includes("+5521988887777 sms"));
    await E.p.fill("#lg-codigo", "123456"); await E.p.click("#lg-entrar"); await sincronizado(E.p);
    const tE = await texto(E.p);
    confere("entrou pelo celular: Ajustes mostra o número, conta nova e vazia", /\(21\) 98888-7777/.test(tE) && await E.p.evaluate(() => load("historico", []).length === 0 && !!sessao.fone), tE.slice(0, 200));
    confere("conta só de celular: sem o 'Adicionar celular'", (await E.p.locator("#vc-abrir").count()) === 0);
    // maria (e-mail) guarda uma operação e adiciona o celular; depois entra por ele em outro aparelho e recebe tudo
    await C.p.evaluate(() => { let m = null; S.perda = 1e6; S.capital = 1e7; for (const at of Object.keys(SNAP.ativos)) { S.ativo = at; m = montagem("alta"); if (typeof m !== "string") break; } save("historico", [{ m, ativo: S.ativo, data: S.data, id: 301 }]); sincronizar(); });
    await espera(300);
    await C.p.click('#nav [data-nav="cad"]'); await C.p.click("#vc-abrir");
    await C.p.fill("#vc-fone", "(21) 98888-7777"); await C.p.click("#vc-enviar"); await espera(200);
    confere("celular de outra conta: não adiciona e explica", /já está em outra conta/.test(await texto(C.p)) && !banco.pendente[banco.usuarios["maria@teste.dev"]]);
    await C.p.fill("#vc-fone", "31 97777-6666"); await C.p.click("#vc-enviar"); await C.p.waitForSelector("#vc-codigo");
    await C.p.fill("#vc-codigo", "000000"); await C.p.click("#vc-confirmar"); await espera(200);
    confere("adicionar celular: código errado não confirma", /Código errado ou vencido/.test(await texto(C.p)) && !banco.fones["+5531977776666"]);
    await C.p.fill("#vc-codigo", "123456"); await C.p.click("#vc-confirmar"); await espera(300);
    const tC = await texto(C.p);
    confere("adicionar celular: conta com e-mail e celular", banco.fones["+5531977776666"] === banco.usuarios["maria@teste.dev"] && /maria@teste\.dev/.test(tC) && /Celular \(31\) 97777-6666/.test(tC) && (await C.p.locator("#vc-abrir").count()) === 0, tC.slice(0, 250));
    const F = await aparelho(b);
    await entrarCel(F.p, "31977776666"); await sincronizado(F.p);
    confere("entrar pelo celular adicionado: mesma conta, recebe a operação da maria", await F.p.evaluate(() => load("historico", []).map((o) => o.id).join() === "301"));

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

    for (const [n, x] of [["aparelho 1", A], ["aparelho 2", B2], ["outra conta", C], ["celular", E], ["celular adicionado", F], ["boas-vindas", D]]) confere(`sem erros na página (${n})`, x.erros.length === 0, x.erros);
  } finally { await b.close(); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
