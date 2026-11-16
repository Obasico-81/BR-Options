// Vitrine: tudo o que dá para montar hoje com o perfil, em todos os ativos ("Ver vitrine" no fim do Início, no lugar
// do "Tenho um sinal pronto"). Confere o menu e o link, a lista contra as montagens do app
// (montagem() de cada ativo), o filtro, as ordens, a ida ao cartão e a volta, os ativos sem operação com o motivo, o
// perfil editado na própria Vitrine e o perfil pequeno demais.
// Uso: python3 build.py && python3 build_pwa.py && node testes/vitrine.js CAMINHO/pwa/index.html
const { chromium } = require("playwright");
const arq = "file://" + process.argv[2];
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };

(async () => {
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 390, height: 844 }, locale: "pt-BR" });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  const p = await ctx.newPage(), erros = []; p.on("pageerror", (e) => erros.push(e.message));
  const texto = () => p.innerText("#app");
  try {
    await p.goto(arq); await p.waitForSelector("#nav");
    await p.evaluate(() => { localStorage.clear(); S.perda = 3000; S.capital = 30000; save("estado", S); render(); });
    const ini = await texto();
    const abas = await p.evaluate(() => [...document.querySelectorAll("#nav [data-nav]")].map((b) => b.innerText.trim()));
    confere("menu: quatro abas, sem a Vitrine; o Início sem o 'Tenho um sinal pronto'", abas.join() === "Início,Operações,Desempenho,Ajustes" && !/Tenho um sinal pronto/.test(ini), abas);
    const link = await p.evaluate(() => { const L = [...document.querySelectorAll("#app > *")], v = document.querySelector('[data-go="vitrine"]'); return { ultimo: L[L.length - 1] === v, txt: v && v.innerText, classe: v && v.className }; });
    confere("Início: 'Ver vitrine' no fim, como link de texto (o lugar do antigo sinal)", link.ultimo && link.txt === "Ver vitrine" && link.classe === "btn sec2", link);
    await p.click('[data-go="vitrine"]');
    confere("Vitrine: abre em tela própria, com a aba Início acesa", await p.evaluate(() => tela === "vitrine" && document.querySelector('#nav [data-nav="obj"]').getAttribute("aria-current") === "page") && /^Vitrine$/m.test(await texto()));
    // o que o app monta em cada ativo, com o perfil (as mesmas montagens do Início)
    const esperado = async () => p.evaluate((f) => { const salvo = S.ativo, L = [];
      for (const n of Object.keys(SNAP.por_data[S.data]).sort()) { S.ativo = n;
        for (const t of ["alta", "baixa", "forte", "alta_com_caixa"]) { if (f !== "tudo" && f !== t) continue; const m = montagem(t);
          if (typeof m !== "string") L.push({ k: n + "|" + t, risco: brl(m.perdaMax), chance: pct(m.probImplicita), r: m.perdaMax, c: m.probImplicita }); } }
      S.ativo = salvo; return L; }, await p.evaluate(() => expFiltro));
    const linhas = () => p.evaluate(() => [...document.querySelectorAll("[data-exp]")].map((b) => ({ k: b.dataset.exp, txt: b.innerText })));
    let E = await esperado(), L = await linhas();
    confere("lista: as mesmas operações que o app monta em cada ativo", E.length > 0 && JSON.stringify(E.map((x) => x.k)) === JSON.stringify(L.map((x) => x.k)), { E: E.map((x) => x.k), L: L.map((x) => x.k) });
    confere("lista: risco máximo e chance implícita iguais aos da montagem", L.every((x, i) => x.txt.includes(E[i].risco) && x.txt.includes(E[i].chance)));
    confere("lista: ordem padrão por ativo (A a Z)", L.map((x) => x.k.split("|")[0]).join() === L.map((x) => x.k.split("|")[0]).sort().join());
    const nAtivos = await p.evaluate(() => Object.keys(SNAP.por_data[S.data]).length), comOp = new Set(E.map((x) => x.k.split("|")[0])).size;
    const semTxt = (await texto()).split("Sem operação no seu perfil hoje")[1] || "";
    confere("ativos sem operação: listados com o motivo", nAtivos === comOp ? !/Sem operação no seu perfil hoje/.test(await texto()) : (semTxt.match(/\n[A-Z0-9]{5,6}\n/g) || []).length === nAtivos - comOp, { nAtivos, comOp, semTxt: semTxt.slice(0, 300) });

    // ordens
    await p.selectOption("#exp-ordem", "risco"); L = await linhas();
    const rs = L.map((x) => E.find((e) => e.k === x.k).r);
    confere("ordem por menor risco máximo", rs.every((v, i) => i === 0 || rs[i - 1] <= v), rs);
    await p.selectOption("#exp-ordem", "chance"); L = await linhas();
    const cs = L.map((x) => E.find((e) => e.k === x.k).c);
    confere("ordem por maior chance implícita", cs.every((v, i) => i === 0 || cs[i - 1] >= v), cs);
    await p.selectOption("#exp-ordem", "mov"); L = await linhas();
    const ms = await p.evaluate((ks) => ks.map((k) => { const [n, t] = k.split("|"), salvo = S.ativo; S.ativo = n; const m = montagem(t), v = movEquilibrio(m, dia().S); S.ativo = salvo; return v; }), L.map((x) => x.k));
    confere("ordem por menor movimento até o equilíbrio", ms.every((v, i) => i === 0 || ms[i - 1] <= v + 1e-12), ms);
    await p.selectOption("#exp-ordem", "ativo");

    // filtro
    await p.click('[data-expf="baixa"]'); E = await esperado(); L = await linhas();
    confere("filtro 'Cair': só travas de baixa, as mesmas da montagem", L.length === E.length && L.every((x) => x.k.endsWith("|baixa")), L.map((x) => x.k));
    await p.click('[data-expf="tudo"]');

    // ida ao cartão e volta
    const alvo = (await linhas())[0].k, [an, at] = alvo.split("|");
    await p.click(`[data-exp="${alvo}"]`);
    confere("tocar na operação: abre o cartão daquele ativo e daquela operação", await p.evaluate(([n, t]) => tela === "cartao" && S.ativo === n && tese === t, [an, at]) && /Operação montada/.test(await texto()));
    confere("cartão aberto pela Vitrine: a aba Início continua acesa", await p.evaluate(() => document.querySelector('#nav [data-nav="obj"]').getAttribute("aria-current") === "page"));
    await p.click('.top [data-go="vitrine"]');
    confere("'Voltar' do cartão: volta à Vitrine", await p.evaluate(() => tela === "vitrine"));
    await p.click(`[data-exp="${alvo}"]`); await p.click("text=Não agora");
    confere("'Não agora': volta à Vitrine", await p.evaluate(() => tela === "vitrine"));
    await p.click('#nav [data-nav="obj"]'); await p.click("[data-tese]:not([disabled])");
    confere("cartão aberto pelo Início: 'Voltar' continua indo ao Início", (await p.locator('.top [data-go="obj"]').count()) === 1);
    await p.click('#nav [data-nav="obj"]'); await p.click('[data-go="vitrine"]');

    // perfil pequeno: nada cabe, e cada ativo aparece com o motivo
    await p.evaluate(() => { S.perda = 10; save("estado", S); render(); });
    const t2 = await texto();
    confere("perfil pequeno: nenhuma operação, aviso e o motivo de cada ativo", (await p.locator("[data-exp]").count()) === 0 && /nenhuma operação/.test(t2) && (t2.match(/risco máximo precisaria ser|Não há opções com liquidez|exige reservar/g) || []).length === nAtivos, t2.slice(0, 500));
    await p.click('[data-perfil="1"]');
    confere("'Editar' o perfil: abre ali mesmo, na Vitrine", await p.evaluate(() => tela === "vitrine" && !!document.getElementById("perda")));
    await p.fill("#perda", "3000"); await p.dispatchEvent("#perda", "change");
    confere("perfil mudado na Vitrine: a lista refaz na hora", await p.evaluate(() => tela === "vitrine" && S.perda === 3000) && (await p.locator("[data-exp]").count()) > 0);
    confere("sem erros na página", erros.length === 0, erros);
  } finally { await b.close(); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
