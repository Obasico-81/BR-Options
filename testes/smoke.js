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
  // custos em "Detalhes da operação": fechado por padrão; margem de R$ 4 por ordem sem corretagem, corretagem cadastrada
  // com ela; por ordem (não cresce com os lotes); operação antiga sem os campos novos não mostra o bloco nem quebra
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
    const f = []; if (!r.soma) f.push('total ≠ soma das partes'); if (r.fixo !== 16 || r.fixo5 !== 20) f.push(`fixo da trava ${r.fixo} / ${r.fixo5} (esperado 16 / 20, com ${r.lotes} lotes)`);
    if (!r.sem || r.sem.aberto || !/Margem fixa \(4 ordens × R\$\s4,00\)/.test(r.sem.txt)) f.push('sem corretagem: ' + JSON.stringify(r.sem));
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
  console.log(erros.length ? `\n${erros.length} erro(s)` : '\nsem erros');
  await b.close(); process.exit(erros.length ? 1 : 0);
})();
