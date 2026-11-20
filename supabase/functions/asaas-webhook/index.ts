// Avisos do Asaas (Webhook). Configurar no Asaas: URL = https://<projeto>.supabase.co/functions/v1/asaas-webhook,
// authToken = o mesmo valor do segredo ASAAS_WEBHOOK_TOKEN, eventos de cobrança, assinatura, checkout e Pix Automático.
// Publicar sem exigir login do Supabase (o Asaas não tem sessão): verify_jwt = false. A segurança é o authToken.
// Cada evento é processado uma vez (tabela asaas_eventos); o que muda na assinatura está em _compartilhado/regras.ts.
import { asaas, banco } from "../_compartilhado/asaas.ts";
import { type Linha, aplicarEvento, hojeSP, ondeEvento, orfaParaCancelar } from "../_compartilhado/regras.ts";

const iguais = (a: string, b: string) => {   // comparação sem atalho (não vaza o token pelo tempo de resposta)
  if (!a || !b || a.length !== b.length) return false;
  let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0;
};

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("método", { status: 405 });
  if (!iguais(req.headers.get("asaas-access-token") || "", Deno.env.get("ASAAS_WEBHOOK_TOKEN") || "")) return new Response("token", { status: 401 });
  // deno-lint-ignore no-explicit-any
  let ev: any; try { ev = await req.json(); } catch { return new Response("json", { status: 400 }); }
  const db = banco();
  const id = String(ev.id || `${ev.event}:${ev.payment?.id || ev.subscription?.id || ev.authorization?.id || ev.checkout?.id}:${ev.dateCreated}`);
  const { error: dup } = await db.from("asaas_eventos").insert({ id, tipo: String(ev.event || "?"), payload: ev });
  if (dup) return new Response(dup.code === "23505" ? "repetido" : "erro", { status: dup.code === "23505" ? 200 : 500 });

  const onde = ondeEvento(ev);
  if (!onde) return new Response("ignorado", { status: 200 });
  let { data: linha, error } = await db.from("assinaturas").select("*").eq(onde.coluna, onde.valor).maybeSingle<Linha>();
  if (error) { await db.from("asaas_eventos").delete().eq("id", id); return new Response("erro", { status: 500 }); }   // o Asaas reenvia
  // Cartão: o Asaas avisa da cobrança antes de avisar da assinatura criada pelo checkout. Sem dono pela assinatura,
  // pergunta ao Asaas de que checkout ela veio e liga as duas (senão um pagamento na hora, sem teste, se perderia).
  if (!linha && onde.coluna === "asaas_assinatura") {
    const sub = await asaas("GET", `/subscriptions/${onde.valor}`).catch(() => null);
    if (sub?.checkoutSession) {
      const r = await db.from("assinaturas").select("*").eq("asaas_checkout", sub.checkoutSession).maybeSingle<Linha>();
      if (r.data) {
        linha = { ...r.data, asaas_assinatura: sub.id, asaas_cliente: sub.customer ?? r.data.asaas_cliente };
        await db.from("assinaturas").update({ asaas_assinatura: linha.asaas_assinatura, asaas_cliente: linha.asaas_cliente }).eq("user_id", linha.user_id);
      }
    }
  }
  if (!linha) {
    const orfa = orfaParaCancelar(ev, linha);
    if (orfa) await asaas("DELETE", `/subscriptions/${orfa}`).catch((e) => console.error("órfã", orfa, e));
    return new Response(orfa ? "órfã cancelada" : "sem assinatura", { status: 200 });
  }
  const campos = aplicarEvento(ev, linha, hojeSP());
  if (!campos) return new Response("sem mudança", { status: 200 });
  const { error: e2 } = await db.from("assinaturas").update({ ...campos, atualizado_em: new Date().toISOString() }).eq("user_id", linha.user_id);
  if (e2) { await db.from("asaas_eventos").delete().eq("id", id); return new Response("erro", { status: 500 }); }
  return new Response("ok", { status: 200 });
});
