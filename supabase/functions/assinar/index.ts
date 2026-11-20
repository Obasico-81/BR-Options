// Começa a assinatura do Vaglio Pro e devolve o endereço onde o cliente autoriza o pagamento.
//   POST {plano: "mensal" | "anual", forma: "CREDIT_CARD" | "PIX", nome?, cpf?}   (exige login)
//   Cartão: checkout hospedado pelo Asaas com recorrência; o cartão é guardado lá (nunca passa pelo Vaglio).
//   Pix: assinatura com a primeira cobrança em 7 dias; na fatura, o banco do cliente oferece o Pix Automático
//   (agendar e autorizar). Pix pede nome e CPF, que o Asaas exige para o cliente.
//   O teste grátis começa quando o Asaas avisa que o cartão foi guardado ou que o Pix Automático foi autorizado.
import { APP_URL, ASAAS_SITE, ErroAsaas, CORS, asaas, banco, resposta, usuario } from "../_compartilhado/asaas.ts";
import { PLANOS, type Plano, type Linha, cpfValido, hojeSP, primeiraCobranca, temPro } from "../_compartilhado/regras.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return resposta({ erro: "método" }, 405);
  const u = await usuario(req);
  if (!u) return resposta({ erro: "Entre na sua conta para assinar." }, 401);
  let b: { plano?: string; forma?: string; nome?: string; cpf?: string };
  try { b = await req.json(); } catch { return resposta({ erro: "Pedido inválido." }, 400); }
  const plano = PLANOS[b.plano as Plano];
  if (!plano) return resposta({ erro: "Plano inválido." }, 400);
  if (b.forma !== "CREDIT_CARD" && b.forma !== "PIX") return resposta({ erro: "Forma de pagamento inválida." }, 400);
  const nome = String(b.nome || "").trim(), cpf = String(b.cpf || "").replace(/\D/g, "");
  if (b.forma === "PIX" && (nome.length < 3 || !cpfValido(cpf))) return resposta({ erro: "Confira o nome e o CPF." }, 400);

  const db = banco(), hoje = hojeSP();
  const { data: linha } = await db.from("assinaturas").select("*").eq("user_id", u.id).maybeSingle<Linha>();
  if (temPro(linha, hoje)) return resposta({ erro: "Você já tem o Vaglio Pro." }, 409);
  const { data: primeira, comTeste } = primeiraCobranca(linha, hoje);
  const desc = comTeste ? `${plano.nome}, com 7 dias grátis` : plano.nome;

  try {
    // pedido anterior ainda sem autorização: a assinatura antiga no Asaas sai, para não gerar cobrança em dobro
    if (linha && linha.status === "aguardando" && linha.asaas_assinatura) await asaas("DELETE", `/subscriptions/${linha.asaas_assinatura}`).catch(() => {});
    if (b.forma === "CREDIT_CARD") {
      const ck = await asaas("POST", "/checkouts", {
        billingTypes: ["CREDIT_CARD"], chargeTypes: ["RECURRENT"], minutesToExpire: 60,
        callback: { successUrl: APP_URL + "?assinatura=ok", cancelUrl: APP_URL + "?assinatura=cancelada", expiredUrl: APP_URL + "?assinatura=expirada" },
        items: [{ name: plano.nome, description: desc, quantity: 1, value: plano.valor }],
        subscription: { cycle: plano.ciclo, nextDueDate: primeira + " 12:00:00" },
        externalReference: u.id,
      });
      const { error } = await db.from("assinaturas").upsert({ user_id: u.id, status: "aguardando", plano: b.plano, forma: "CREDIT_CARD", asaas_checkout: ck.id, asaas_assinatura: null, atualizado_em: new Date().toISOString() });
      if (error) throw error;
      return resposta({ url: `${ASAAS_SITE}/checkoutSession/show?id=${ck.id}`, comTeste, primeiraCobranca: primeira });
    }
    // Pix: cliente (reaproveita o da conta) e assinatura; a primeira fatura carrega a oferta do Pix Automático
    const cliente = linha?.asaas_cliente || (await asaas("POST", "/customers", { name: nome, cpfCnpj: cpf, email: u.email, externalReference: u.id, notificationDisabled: false })).id;
    const sub = await asaas("POST", "/subscriptions", { customer: cliente, billingType: "PIX", value: plano.valor, nextDueDate: primeira, cycle: plano.ciclo, description: desc, externalReference: u.id });
    const cob = await asaas("GET", `/subscriptions/${sub.id}/payments`);
    const fatura = cob?.data?.[0]?.invoiceUrl;
    const { error } = await db.from("assinaturas").upsert({ user_id: u.id, status: "aguardando", plano: b.plano, forma: "PIX", asaas_cliente: cliente, asaas_assinatura: sub.id, asaas_checkout: null, atualizado_em: new Date().toISOString() });
    if (error) throw error;
    return resposta({ url: fatura, comTeste, primeiraCobranca: primeira, pixAutomatico: sub.pixAutomaticAuthorizationMode === "OPTIONAL" });
  } catch (e) {
    console.error("assinar", e instanceof ErroAsaas ? JSON.stringify(e.detalhe) : e);
    return resposta({ erro: "Não foi possível abrir o pagamento agora. Tente de novo em instantes." }, 502);
  }
});
