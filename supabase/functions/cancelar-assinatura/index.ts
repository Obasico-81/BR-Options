// Cancela a assinatura no Asaas (nenhuma cobrança nova). O Pro continua até o fim do período já pago, ou do teste.
//   POST {}   (exige login)
import { ErroAsaas, CORS, asaas, banco, resposta, usuario } from "../_compartilhado/asaas.ts";
import type { Linha } from "../_compartilhado/regras.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return resposta({ erro: "método" }, 405);
  const u = await usuario(req);
  if (!u) return resposta({ erro: "Entre na sua conta." }, 401);
  const db = banco();
  const { data: linha } = await db.from("assinaturas").select("*").eq("user_id", u.id).maybeSingle<Linha>();
  if (!linha || !linha.asaas_assinatura || linha.status === "cancelada") return resposta({ erro: "Nenhuma assinatura para cancelar." }, 404);
  try { await asaas("DELETE", `/subscriptions/${linha.asaas_assinatura}`); }
  catch (e) { if (!(e instanceof ErroAsaas && e.status === 404)) { console.error("cancelar", e); return resposta({ erro: "Não foi possível cancelar agora. Tente de novo em instantes." }, 502); } }
  await db.from("assinaturas").update({ status: "cancelada", atualizado_em: new Date().toISOString() }).eq("user_id", u.id);
  return resposta({ ok: true, proAte: linha.pro_ate });
});
