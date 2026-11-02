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
  console.log(erros.length ? `\n${erros.length} erro(s)` : '\nsem erros');
  await b.close(); process.exit(erros.length ? 1 : 0);
})();
