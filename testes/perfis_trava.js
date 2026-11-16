// Perfis da trava (Lucro maior, Equilibrada, Lucro frequente): no cartão da trava de alta e de baixa, com a mesma regra
// da compra simples. Confere contra o montador (M.montar com perfil), a ordem da chance e do ganho em relação ao risco,
// o perfil guardado (S.pfTrava) valendo no Início e na Vitrine, o perfil indisponível e a volta à trava de sempre.
// Uso: python3 build.py && python3 build_pwa.py && node testes/perfis_trava.js CAMINHO/pwa/index.html
const { chromium } = require("playwright");
const arq = "file://" + process.argv[2];
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };

(async () => {
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 390, height: 844 }, locale: "pt-BR" });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  const p = await ctx.newPage(), erros = []; p.on("pageerror", (e) => erros.push(e.message));
  try {
    await p.goto(arq); await p.waitForSelector("#nav");
    // ativo e trava em que os três perfis montam e são diferentes entre si
    const alvo = await p.evaluate(() => { localStorage.clear(); S.perda = 1e5; S.capital = 1e6;
      for (const at of Object.keys(SNAP.por_data[S.data])) { S.ativo = at; for (const t of ["alta", "baixa"]) if (["maior", "eq", "freq"].every((k) => pftDisp(t, k))) { save("estado", S); return { at, t }; } }
      return null; });
    if (!alvo) { console.log("aviso: nenhum ativo com os três perfis hoje; testa o que houver");
      await p.evaluate(() => { S.ativo = Object.keys(SNAP.por_data[S.data]).find((at) => { S.ativo = at; return pftDisp("alta", "eq"); }); save("estado", S); }); }
    const t = alvo ? alvo.t : "alta";
    await p.evaluate((t) => { render(); }, t);
    await p.click(`[data-tese="${t}"]`);
    confere("cartão da trava: seletor com os três perfis, Equilibrada marcada", (await p.locator("[data-pft]").count()) === 3 && (await p.locator('[data-pft="eq"][aria-pressed="true"]').count()) === 1);
    const eq = await p.evaluate(() => montagem(tese));
    const eqM = await p.evaluate((t) => { const a = dia(); const m = M.montar(t, a.S, a.chain, a.iv, S.perda, { prazoAlvo: vencSel().d, caixa: S.capital }); return m; }, t);
    confere("Equilibrada: a mesma trava de sempre (montador sem perfil)", JSON.stringify(eq.pernas) === JSON.stringify(eqM.pernas));
    if (alvo) {
      const R = {};
      for (const k of ["maior", "eq", "freq"]) { await p.click(`[data-pft="${k}"]`); R[k] = await p.evaluate(() => { const m = montagem(tese); return { prob: m.probImplicita, gr: m.ganhoMax / m.perdaMax, pernas: m.pernas.map(([, o]) => o.s).join("/") }; });
        R[k].tela = await p.innerText("#app"); }
      confere("chance: Lucro maior < Equilibrada < Lucro frequente", R.maior.prob < R.eq.prob && R.eq.prob < R.freq.prob, { maior: R.maior.prob, eq: R.eq.prob, freq: R.freq.prob });
      confere("ganho em relação ao risco: Lucro maior > Equilibrada > Lucro frequente", R.maior.gr > R.eq.gr && R.eq.gr > R.freq.gr, { maior: R.maior.gr, eq: R.eq.gr, freq: R.freq.gr });
      confere("cada perfil com séries diferentes", new Set([R.maior.pernas, R.eq.pernas, R.freq.pernas]).size === 3);
      confere("texto do perfil escolhido aparece", /quando perde, perde mais do que costuma ganhar/.test(R.freq.tela) && /o ganho é maior que o risco/.test(R.maior.tela));
      confere("perfil guardado: S.pfTrava = freq e o Início monta com ele", await p.evaluate((t) => S.pfTrava === "freq" && montagem(t).pernas.map(([, o]) => o.s).join("/") === pernasDe(travaMont(t, "freq")), t));
      await p.click('#nav [data-nav="vitrine"]');
      const linha = await p.evaluate(([at, t]) => { const b = document.querySelector(`[data-exp="${at}|${t}"]`); return b && b.innerText; }, [alvo.at, t]);
      confere("Vitrine: a linha da trava mostra 'Lucro frequente'", !!linha && /Lucro frequente/.test(linha), linha);
    }
    // perfil escolhido que não monta num ativo: vale a trava de sempre
    const volta = await p.evaluate(() => { S.pfTrava = "freq"; for (const at of Object.keys(SNAP.por_data[S.data])) { S.ativo = at; for (const t of ["alta", "baixa"]) if (pftDisp(t, "eq") && !pftDisp(t, "freq")) return { at, t, cur: pftAtual(t), igual: pernasDe(montagem(t)) === pernasDe(travaMont(t, "eq")) }; } return null; });
    confere("perfil indisponível no ativo: vale a trava de sempre (Equilibrada)", !volta || (volta.cur === "eq" && volta.igual), volta);
    confere("sem erros na página", erros.length === 0, erros);
  } finally { await b.close(); }
  console.log(falhas ? `\n${falhas} falha(s)` : "\ntodos os casos passaram"); process.exit(falhas ? 1 : 0);
})();
