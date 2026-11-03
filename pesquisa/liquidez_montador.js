// Para cada prefixo de cadeias_top.json (gerado por liquidez.py), roda o montador.js do app em cada pregão
// e conta em quantos dias cada estrutura monta dentro do risco máximo do perfil. Mesmas regras do app:
// spread <= 20% (SPREAD_MAX), volume mínimo, prazo-alvo 45 dias, capital R$ 12.000.
// Uso: node pesquisa/liquidez_montador.js PASTA_COM_cadeias_top.json
const path = require("path");
const M = require(path.join(__dirname, "..", "montador.js"));
const dados = require(path.join(path.resolve(process.argv[2]), "cadeias_top.json"));
const TESES = ["alta", "baixa", "forte", "alta_com_caixa"], CAPITAL = 12000;
const cabe = (m, risco) => typeof m !== "string" && m.perdaMax / m.lotes <= risco;   // o app reduz lotes até caber
const linhas = [];
for (const [pf, { papel, por_data }] of Object.entries(dados)) {
  const dias = Object.keys(por_data).sort(); if (!dias.length) continue;
  const r = { pf, papel, dias: dias.length };
  for (const risco of [300, 500, 1000]) {
    const cont = Object.fromEntries([...TESES, "compra_alta", "compra_baixa", "alguma"].map((k) => [k, 0]));
    for (const d of dias) {
      const { S, iv, chain } = por_data[d]; let alguma = false;
      for (const t of TESES) { const m = M.montar(t, S, chain, iv, risco, { prazoAlvo: 45, caixa: CAPITAL }); if (cabe(m, risco)) { cont[t]++; alguma = true; } }
      for (const lado of ["alta", "baixa"]) { const m = M.montarAposta(lado, S, chain, iv, risco); if (cabe(m, risco)) { cont["compra_" + lado]++; alguma = true; } }
      if (alguma) cont.alguma++;
    }
    for (const [k, v] of Object.entries(cont)) r[`${k}_${risco}`] = Math.round((100 * v) / dias.length);
  }
  // tamanho que o papel acrescentaria ao snapshot.json (12 pregões de cadeia, como hoje)
  const ult = dias.slice(-12).map((d) => por_data[d]);
  r.kb_snapshot = Math.round(JSON.stringify(ult).length / 1024);
  linhas.push(r);
}
const col = (r, k) => String(r[k] ?? "").padStart(6);
console.log(`% dos pregões em que monta dentro do risco máximo (prazo-alvo 45 dias, capital R$ ${CAPITAL})`);
for (const risco of [300, 500, 1000]) {
  console.log(`\nRisco máximo por operação: R$ ${risco}`);
  console.log("prefixo papel   dias  alguma  trava↑  trava↓  strang  put_cx  call   put    kB snapshot");
  for (const r of linhas) console.log(`${r.pf.padEnd(8)}${r.papel.padEnd(8)}${String(r.dias).padStart(4)}${col(r, "alguma_" + risco)}%${col(r, "alta_" + risco)}%${col(r, "baixa_" + risco)}%${col(r, "forte_" + risco)}%${col(r, "alta_com_caixa_" + risco)}%${col(r, "compra_alta_" + risco)}%${col(r, "compra_baixa_" + risco)}%${String(r.kb_snapshot).padStart(8)}`);
}
