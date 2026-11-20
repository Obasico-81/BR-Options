// Regras da assinatura (supabase/functions/_compartilhado/regras.ts): teste grátis, períodos pagos, carência,
// cancelamento, estorno e de que linha cada aviso do Asaas trata.
// Uso: node --experimental-strip-types testes/assinatura_regras.mjs
import * as R from "../supabase/functions/_compartilhado/regras.ts";
let falhas = 0;
const confere = (nome, ok, extra) => { console.log((ok ? "OK    " : "FALHA ") + nome + (ok || extra === undefined ? "" : "  -> " + JSON.stringify(extra))); if (!ok) falhas++; };
const hoje = "2026-11-20";
const base = { user_id: "u1", status: "aguardando", plano: "mensal", forma: "CREDIT_CARD", pro_ate: null, teste_ate: null, asaas_cliente: null, asaas_assinatura: null, asaas_checkout: "ck1" };

confere("preços: R$ 49,90 por mês e R$ 479 por ano (20% abaixo de 12 meses)", R.PLANOS.mensal.valor === 49.9 && R.PLANOS.anual.valor === 479 && Math.abs(1 - 479 / (49.9 * 12) - 0.2) < 0.001);
confere("datas: +7 dias, +1 mês no fim do mês, +12 meses", R.addDias(hoje, 7) === "2026-11-27" && R.addMeses("2027-01-31", 1) === "2027-02-28" && R.addMeses("2026-11-27", 12) === "2027-11-27");
confere("CPF: válido, dígito errado, repetido", R.cpfValido("529.982.247-25") && !R.cpfValido("529.982.247-24") && !R.cpfValido("111.111.111-11"));
confere("primeira cobrança: em 7 dias na primeira assinatura; hoje se a conta já usou o teste",
  JSON.stringify(R.primeiraCobranca(null, hoje)) === JSON.stringify({ data: "2026-11-27", comTeste: true }) && R.primeiraCobranca({ ...base, teste_ate: "2026-10-01" }, hoje).data === hoje);

// cartão: checkout concluído -> assinatura criada -> teste de 7 dias
const criada = { event: "SUBSCRIPTION_CREATED", subscription: { id: "sub1", customer: "cus1", checkoutSession: "ck1" } };
confere("aviso de assinatura criada pelo checkout acha a linha pela sessão de checkout", JSON.stringify(R.ondeEvento(criada)) === JSON.stringify({ coluna: "asaas_checkout", valor: "ck1" }));
const t1 = R.aplicarEvento(criada, base, hoje);
confere("cartão guardado: teste até 27/11, Pro até 27/11, assinatura e cliente ligados", t1.status === "teste" && t1.teste_ate === "2026-11-27" && t1.pro_ate === "2026-11-27" && t1.asaas_assinatura === "sub1" && t1.asaas_cliente === "cus1", t1);
const noTeste = { ...base, ...t1 };
// primeira cobrança paga no fim do teste
const pago = { event: "PAYMENT_CONFIRMED", payment: { subscription: "sub1", dueDate: "2026-11-27" } };
confere("cobrança acha a linha pela assinatura", JSON.stringify(R.ondeEvento(pago)) === JSON.stringify({ coluna: "asaas_assinatura", valor: "sub1" }));
const p1 = R.aplicarEvento(pago, noTeste, "2026-11-27");
confere("mensal pago em 27/11: ativa, Pro até 27/12 + 3 dias de carência", p1.status === "ativa" && p1.pro_ate === "2026-12-30", p1);
const p2 = R.aplicarEvento(pago, { ...noTeste, plano: "anual" }, "2026-11-27");
confere("anual pago em 27/11: Pro até 27/11/2027 + 3 dias", p2.pro_ate === "2027-11-30", p2);
confere("aviso repetido de pagamento não encurta o Pro", R.aplicarEvento({ event: "PAYMENT_RECEIVED", payment: { subscription: "sub1", dueDate: "2026-10-27" } }, { ...noTeste, ...p1 }, hoje).pro_ate === "2026-12-30");
// atraso, cancelamento e estorno
confere("atraso: status atrasada, Pro não muda", JSON.stringify(R.aplicarEvento({ event: "PAYMENT_OVERDUE", payment: { subscription: "sub1" } }, { ...noTeste, ...p1 }, hoje)) === JSON.stringify({ status: "atrasada" }));
confere("cancelada: Pro continua até o fim do período", JSON.stringify(R.aplicarEvento({ event: "SUBSCRIPTION_DELETED", subscription: { id: "sub1" } }, { ...noTeste, ...p1 }, hoje)) === JSON.stringify({ status: "cancelada" }));
confere("estorno: Pro termina hoje", JSON.stringify(R.aplicarEvento({ event: "PAYMENT_REFUNDED", payment: { subscription: "sub1" } }, { ...noTeste, ...p1 }, hoje)) === JSON.stringify({ status: "estornada", pro_ate: hoje }));
// Pix: autorização do Pix Automático inicia o teste; a conta acha a linha pelo cliente
const pixLinha = { ...base, forma: "PIX", asaas_checkout: null, asaas_assinatura: "sub2", asaas_cliente: "cus2" };
const aut = { event: "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_ACTIVATED", authorization: { customerId: "cus2", status: "ACTIVE" } };
confere("autorização do Pix Automático acha a linha pelo cliente", JSON.stringify(R.ondeEvento(aut)) === JSON.stringify({ coluna: "asaas_cliente", valor: "cus2" }));
const a1 = R.aplicarEvento(aut, pixLinha, hoje);
confere("Pix autorizado: teste de 7 dias", a1.status === "teste" && a1.teste_ate === "2026-11-27", a1);
confere("Pix autorizado de novo (já em teste): nada muda", R.aplicarEvento(aut, { ...pixLinha, ...a1 }, hoje) === null);
// a conta não ganha um segundo teste
const jaTestou = { ...base, teste_ate: "2026-10-01", status: "aguardando" };
const s2 = R.aplicarEvento(criada, jaTestou, hoje);
confere("conta que já usou o teste: assinatura criada não dá Pro até pagar", s2.status === "aguardando" && !s2.pro_ate && !s2.teste_ate, s2);
// Pro em vigor e eventos ignorados
confere("Pro em vigor: teste e atrasada dentro do prazo; vencido ou cancelado, não", R.temPro({ ...noTeste }, hoje) && R.temPro({ ...noTeste, status: "atrasada" }, hoje) && !R.temPro({ ...noTeste, pro_ate: "2026-11-19" }, hoje) && !R.temPro({ ...noTeste, status: "cancelada" }, hoje));
confere("assinatura criada pela API (Pix, sem checkout) não mexe na linha", R.aplicarEvento({ event: "SUBSCRIPTION_CREATED", subscription: { id: "sub2" } }, pixLinha, hoje) === null);
confere("evento sem relação (ex.: transferência) é ignorado", R.ondeEvento({ event: "TRANSFER_DONE", transfer: { id: "t" } }) === null);
console.log(falhas ? `\n${falhas} falha(s)` : "\nTudo certo."); process.exit(falhas ? 1 : 0);
