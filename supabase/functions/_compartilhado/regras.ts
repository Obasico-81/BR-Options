// Regras da assinatura do Vaglio Pro, sem dependência de servidor (testadas em testes/assinatura_regras.mjs).
// Preço e teste decididos em 20/11/2026: R$ 49,90 por mês ou R$ 479 por ano, 7 dias grátis na primeira assinatura.

export const DIAS_TESTE = 7;
export const CARENCIA = 3;   // dias de Pro depois do vencimento, enquanto o pagamento compensa ou é refeito
export const PLANOS = {
  mensal: { valor: 49.90, ciclo: "MONTHLY", meses: 1, nome: "Vaglio Pro mensal" },
  anual: { valor: 479, ciclo: "YEARLY", meses: 12, nome: "Vaglio Pro anual" },
} as const;
export type Plano = keyof typeof PLANOS;

export type Linha = {
  user_id: string; status: string; plano: string | null; forma: string | null; pro_ate: string | null; teste_ate: string | null;
  asaas_cliente: string | null; asaas_assinatura: string | null; asaas_checkout: string | null;
};

export const addDias = (iso: string, n: number): string => {
  const d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10);
};
export const addMeses = (iso: string, n: number): string => {
  const [a, m, d] = iso.split("-").map(Number), alvo = new Date(Date.UTC(a, m - 1 + n, 1, 12));
  const ult = new Date(Date.UTC(alvo.getUTCFullYear(), alvo.getUTCMonth() + 1, 0, 12)).getUTCDate();   // 31/01 + 1 mês = 28 ou 29/02
  alvo.setUTCDate(Math.min(d, ult)); return alvo.toISOString().slice(0, 10);
};
// data de hoje no fuso de São Paulo
export const hojeSP = (agora = new Date()): string => new Date(agora.getTime() - 3 * 3600e3).toISOString().slice(0, 10);
const maior = (a: string | null, b: string): string => (a && a > b ? a : b);

// CPF: 11 dígitos com os dois verificadores certos (o Asaas recusa CPF inválido; conferir antes poupa uma ida e volta)
export function cpfValido(v: string): boolean {
  const c = String(v || "").replace(/\D/g, "");
  if (c.length !== 11 || /^(\d)\1{10}$/.test(c)) return false;
  const dv = (n: number) => { let s = 0; for (let i = 0; i < n; i++) s += Number(c[i]) * (n + 1 - i); const r = (s * 10) % 11; return r === 10 ? 0 : r; };
  return dv(9) === Number(c[9]) && dv(10) === Number(c[10]);
}

// Primeira cobrança: daqui a 7 dias na primeira assinatura da conta (teste grátis); hoje, se a conta já usou o teste.
export function primeiraCobranca(linha: Linha | null, hoje: string): { data: string; comTeste: boolean } {
  const comTeste = !linha || !linha.teste_ate;
  return { data: comTeste ? addDias(hoje, DIAS_TESTE) : hoje, comTeste };
}

// Já tem o Pro em vigor (não deixa assinar de novo por cima)
export const temPro = (linha: Linha | null, hoje: string): boolean =>
  !!linha && !!linha.pro_ate && linha.pro_ate >= hoje && ["teste", "ativa", "atrasada"].includes(linha.status);

// Que linha um evento do Asaas atualiza: pela sessão de checkout (cartão), pela assinatura ou pelo cliente (Pix Automático)
// deno-lint-ignore no-explicit-any
export function ondeEvento(ev: any): { coluna: "asaas_checkout" | "asaas_assinatura" | "asaas_cliente"; valor: string } | null {
  const t = ev && ev.event;
  if (t === "SUBSCRIPTION_CREATED" && ev.subscription?.checkoutSession) return { coluna: "asaas_checkout", valor: ev.subscription.checkoutSession };
  if (t && t.startsWith("SUBSCRIPTION_") && ev.subscription?.id) return { coluna: "asaas_assinatura", valor: ev.subscription.id };
  if (t && t.startsWith("PAYMENT_") && ev.payment?.subscription) return { coluna: "asaas_assinatura", valor: ev.payment.subscription };
  if (t && t.startsWith("PIX_AUTOMATIC_RECURRING_AUTHORIZATION_") && ev.authorization?.customerId) return { coluna: "asaas_cliente", valor: ev.authorization.customerId };
  return null;
}

// Assinatura criada por um checkout sem conta correspondente (a conta foi excluída depois de abrir o pagamento):
// devolve o id para cancelar no Asaas, senão haveria cobrança sem dono. Só o caso do checkout: a assinatura por Pix é
// criada pela própria função assinar, e o aviso pode chegar antes de a linha ser gravada.
// deno-lint-ignore no-explicit-any
export const orfaParaCancelar = (ev: any, linha: Linha | null): string | null =>
  !linha && ev?.event === "SUBSCRIPTION_CREATED" && ev.subscription?.checkoutSession && ev.subscription?.id ? ev.subscription.id : null;

// O que muda na linha com o evento. null: nada a fazer.
// deno-lint-ignore no-explicit-any
export function aplicarEvento(ev: any, linha: Linha, hoje: string): Partial<Linha> | null {
  const t = ev.event, plano = PLANOS[(linha.plano as Plano) || "mensal"] || PLANOS.mensal;
  const iniciarTeste = (): Partial<Linha> => linha.teste_ate
    ? { status: "aguardando" }   // conta que já usou o teste: só vira Pro quando a cobrança for paga
    : { status: "teste", teste_ate: addDias(hoje, DIAS_TESTE), pro_ate: maior(linha.pro_ate, addDias(hoje, DIAS_TESTE)) };
  switch (t) {
    case "SUBSCRIPTION_CREATED":   // cartão: o checkout terminou e o Asaas criou a assinatura (cartão guardado)
      if (!ev.subscription?.checkoutSession) return null;
      return { asaas_assinatura: ev.subscription.id, asaas_cliente: ev.subscription.customer ?? linha.asaas_cliente, ...(linha.status === "aguardando" ? iniciarTeste() : {}) };
    case "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_ACTIVATED":   // Pix: o cliente autorizou o débito automático no banco
      return linha.status === "aguardando" ? iniciarTeste() : null;
    case "PAYMENT_CONFIRMED": case "PAYMENT_RECEIVED": {   // período pago: até o próximo vencimento, mais a carência
      const venc = ev.payment?.dueDate || hoje;
      return { status: "ativa", pro_ate: maior(linha.pro_ate, addDias(addMeses(venc, plano.meses), CARENCIA)) };
    }
    case "PAYMENT_OVERDUE": return linha.status === "cancelada" ? null : { status: "atrasada" };
    case "PAYMENT_REFUNDED": case "PAYMENT_CHARGEBACK_REQUESTED": return { status: "estornada", pro_ate: hoje };
    case "SUBSCRIPTION_DELETED": case "SUBSCRIPTION_INACTIVATED": return { status: "cancelada" };   // Pro até o fim do que foi pago
    default: return null;
  }
}
