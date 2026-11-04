// Abre pwa/index.html, percorre as telas e testa uma operação salva cuja data de entrada saiu de por_data.
const { chromium } = require('playwright');
const arq = 'file://' + process.argv[2];
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  const p = await ctx.newPage();
  const erros = [];
  p.on('pageerror', e => erros.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error' && !/ERR_FAILED|fonts/.test(m.text())) erros.push('console: ' + m.text()); });
  await p.goto(arq);
  const passo = async (nome, fn) => { const n = erros.length; try { await fn(); } catch (e) { erros.push(nome + ': ' + e.message.split('\n')[0]); } console.log((erros.length === n ? 'OK   ' : 'ERRO ') + nome + (erros.length > n ? ' -> ' + erros.slice(n).join(' | ') : '')); };
  await passo('carregar', async () => { await p.waitForSelector('#nav'); });
  console.log('     banner defasado:', await p.locator('text=Preços desatualizados').count() > 0);
  for (const t of ['acomp', 'desemp', 'cad', 'obj']) await passo('tela ' + t, async () => { await p.click(`#nav [data-nav="${t}"]`); await p.waitForTimeout(150); });
  // operação salva num dia que existe em fechamentos, mas não em por_data (é o que acontece depois de 12 pregões)
  await passo('injetar operação antiga', async () => {
    await p.evaluate(() => {
      // procura qualquer ativo/objetivo que monte com os preços do snapshot
      let m = null, ativo = null;
      for (const perda of [S.perda, 1000, 6000, 20000]) { S.perda = perda; S.capital = Math.max(S.capital, perda);
        for (const at of Object.keys(SNAP.ativos)) { S.ativo = at;
          for (const t of ['alta','baixa','forte','alta_com_caixa']) { m = montagem(t); if (typeof m !== 'string') { ativo = at; break; } }
          if (ativo) break; }
        if (ativo) break; }
      if (!ativo) throw new Error('nenhum ativo/objetivo monta com os preços do snapshot: ' + m);
      // entrada no pregão mais recente que tem fechamento mas já não tem cadeia em por_data (ainda não venceu)
      const data = Object.keys(SNAP.fechamentos[ativo]).filter(d => !SNAP.por_data[d]).sort().pop();
      localStorage.setItem('historico', JSON.stringify([{ m, ativo, data, id: 1 }]));
    });
    await p.reload(); await p.waitForSelector('#nav');
  });
  await passo('Operações: lista', async () => { await p.click('#nav [data-nav="acomp"]'); await p.waitForTimeout(150); });
  await passo('Operações: abrir a operação antiga', async () => { await p.click('[data-op="1"]', { timeout: 3000 }); await p.waitForTimeout(200); if (!(await p.locator('text=Sua operação').count())) throw new Error('tela "Sua operação" não abriu'); });
  await passo('Desempenho com a operação', async () => { await p.click('#nav [data-nav="desemp"]'); await p.waitForTimeout(150); });
  // custos em "Detalhes da operação": fechado por padrão; sem corretagem cadastrada, nada de corretagem; com ela, por ordem
  // (não cresce com os lotes); operação antiga sem os campos novos não mostra o bloco nem quebra
  await passo('Detalhes da operação (custos)', async () => {
    const r = await p.evaluate(() => {
      const ver = () => { const d = document.querySelector('details.det'); return d && { aberto: d.open, txt: d.textContent }; };
      let m = null; S.perda = 6000; S.capital = Math.max(S.capital, 6000);
      for (const at of Object.keys(SNAP.ativos)) { S.ativo = at; for (const t of ['alta','baixa']) { const x = montagem(t); if (typeof x !== 'string' && x.lotes > 1) { m = x; tese = t; break; } } if (m) break; }
      if (!m) return 'nenhuma trava com mais de 1 lote';
      const out = { lotes: m.lotes, soma: Math.abs(m.custoSpread + m.custoTaxas + m.custoFixo - m.custoTotal) < 0.011, fixo: m.custoFixo };
      tela = 'cartao'; render(); out.sem = ver();
      S.cad.corretagem = 5; M.setCorretagem(5); render(); out.com = ver(); out.fixo5 = montagem(tese).custoFixo;
      S.cad.corretagem = null; M.setCorretagem(null);
      const velho = JSON.parse(JSON.stringify(m)); for (const k of ['custoSpread','custoTaxas','custoFixo']) delete velho[k];
      const data = Object.keys(SNAP.fechamentos[S.ativo]).sort().pop();
      localStorage.setItem('historico', JSON.stringify([{ m: velho, ativo: S.ativo, data, id: 2 }])); selId = 2; tela = 'acomp'; render(); out.velho = ver();
      return out;
    });
    if (typeof r === 'string') throw new Error(r);
    const f = []; if (!r.soma) f.push('total ≠ soma das partes'); if (r.fixo !== 0 || r.fixo5 !== 20) f.push(`corretagem da trava ${r.fixo} / ${r.fixo5} (esperado 0 / 20, com ${r.lotes} lotes)`);
    if (!r.sem || r.sem.aberto || !/Corretagemnão cadastrada/.test(r.sem.txt) || !/Risco máximo com taxas da B3/.test(r.sem.txt)) f.push('sem corretagem: ' + JSON.stringify(r.sem));
    if (!r.com || !/Corretagem \(4 ordens × R\$\s5,00\)/.test(r.com.txt) || !/R\$ 20,00/.test(r.com.txt)) f.push('com corretagem: ' + JSON.stringify(r.com));
    if (r.velho) f.push('operação antiga mostrou o bloco');
    if (f.length) throw new Error(f.join(' | '));
  });
  // ativo salvo que não existe no dia carregado (papel novo que ficou de fora num pregão): cai para PETR4 sem quebrar
  await passo('ativo salvo ausente no dia', async () => {
    await p.evaluate(() => { localStorage.setItem('estado', JSON.stringify({ ativo: 'XXXX3' })); localStorage.removeItem('historico'); });
    await p.reload(); await p.waitForSelector('#nav');
    const at = await p.evaluate(() => S.ativo); if (at !== 'PETR4') throw new Error('ativo depois do reload: ' + at);
  });
  // perfil padrão de quem abre o app pela primeira vez
  await passo('perfil padrão (PETR4, risco R$ 500)', async () => {
    await p.evaluate(() => localStorage.clear()); await p.reload(); await p.waitForSelector('#nav');
    const v = await p.evaluate(() => [S.ativo, S.perda]); if (v[0] !== 'PETR4' || v[1] !== 500) throw new Error('padrão: ' + v);
  });
  // minigráfico: variação dos últimos 60 pregões (cor pela faixa de ±3%) no cartão do ativo e em cada linha da lista
  await passo('minigráfico dos últimos 60 pregões', async () => {
    await p.evaluate(() => { localStorage.clear(); }); await p.reload(); await p.waitForSelector('#nav');
    const r = await p.evaluate(() => Object.keys(SNAP.ativos).map(n => { const f = SNAP.fechamentos[n], ds = Object.keys(f).filter(d => d <= S.data).sort().slice(-60), vr = f[ds[ds.length - 1]] / f[ds[0]] - 1, g = miniGrafico(n);
      const cor = vr > 0.03 ? 'good' : vr < -0.03 ? 'bad' : 'warn'; return { n, ok: g && g.n === Math.min(60, ds.length) && Math.abs(g.vr - vr) < 1e-12 && g.cor.includes(cor), g: g && [g.n, g.txt, g.cor] }; }));
    const ruins = r.filter(x => !x.ok); if (ruins.length) throw new Error('variação/cor: ' + JSON.stringify(ruins));
    if (!(await p.locator('#atvBtn svg.mini').count())) throw new Error('sem gráfico no cartão do ativo');
    await p.click('#atvBtn'); const linhas = await p.locator('#atvL [data-ativo]').count(), comG = await p.locator('#atvL [data-ativo] svg.mini').count();
    if (linhas !== comG) throw new Error(`lista: ${comG} gráficos em ${linhas} linhas`);
    await p.click('#atvBtn');
  });
  // Sobre o app: termos de uso e política de privacidade abrem em Ajustes e voltam; as páginas do site existem
  await passo('Ajustes: termos de uso e política de privacidade', async () => {
    const f = [];
    await p.click('#nav [data-nav="cad"]'); await p.click('[data-doc="termos"]'); await p.waitForTimeout(100);
    let t = await p.innerText('#app'); if (!t.includes('Termos de uso') || !t.includes('não recomenda ativo, direção nem momento') && !t.includes('Não recomenda ativo, direção nem momento')) f.push('termos: ' + t.slice(0, 120));
    await p.click('text=‹ Ajustes'); await p.click('[data-doc="privacidade"]'); await p.waitForTimeout(100);
    t = await p.innerText('#app'); if (!t.includes('Política de privacidade') || !t.includes('não coleta dados pessoais')) f.push('privacidade: ' + t.slice(0, 120));
    if (!(await p.evaluate(() => document.querySelector('#nav [aria-current="page"]')?.dataset.nav === 'cad'))) f.push('menu não marca Ajustes');
    const fs = require('fs'), path = require('path'), dir = path.dirname(process.argv[2]);
    for (const [arq, h1] of [['termos.html', 'Termos de uso'], ['privacidade.html', 'Política de privacidade']]) {
      const html = fs.existsSync(path.join(dir, arq)) ? fs.readFileSync(path.join(dir, arq), 'utf8') : '';
      if (!html.includes(`<h1>${h1}</h1>`) || /https?:\/\/fonts\./.test(html)) f.push('página ' + arq);
    }
    if (/https?:\/\/fonts\./.test(fs.readFileSync(process.argv[2], 'utf8'))) f.push('o app ainda pede a fonte a outro servidor');
    if (f.length) throw new Error(f.join(' | '));
  });
  // tema: escuro por padrão (mesmo com o aparelho no claro); "Claro" em Ajustes vale, fica guardado; apagar os dados volta ao escuro
  await passo('tema escuro por padrão e opção Claro em Ajustes', async () => {
    const fundo = () => p.evaluate(() => [document.documentElement.dataset.theme || '', getComputedStyle(document.body).backgroundColor]);
    await p.emulateMedia({ colorScheme: 'light' });
    await p.evaluate(() => localStorage.clear()); await p.reload(); await p.waitForSelector('#nav');
    const f = []; let v = await fundo(); if (v[0] !== '' || v[1] !== 'rgb(30, 30, 32)') f.push('padrão: ' + v);
    await p.click('#nav [data-nav="cad"]'); if (!(await p.locator('h1', { hasText: 'Ajustes' }).count())) f.push('título "Ajustes" não apareceu');
    await p.click('[data-tema="claro"]'); v = await fundo(); if (v[0] !== 'light' || v[1] !== 'rgb(227, 227, 224)') f.push('claro: ' + v);
    await p.reload(); await p.waitForSelector('#nav'); v = await fundo(); if (v[0] !== 'light') f.push('claro depois do reload: ' + v);
    p.once('dialog', d => d.accept()); await p.click('#nav [data-nav="cad"]'); await p.click('#apagar-tudo'); await p.waitForLoadState('load'); await p.waitForSelector('#nav');
    v = await fundo(); if (v[0] !== '') f.push('depois de apagar os dados: ' + v);
    if (f.length) throw new Error(f.join(' | '));
  });
  console.log(erros.length ? `\n${erros.length} erro(s)` : '\nsem erros');
  await b.close(); process.exit(erros.length ? 1 : 0);
})();
