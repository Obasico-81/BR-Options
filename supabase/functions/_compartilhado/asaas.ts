// Acesso ao Asaas e ao banco, comum às Edge Functions. Segredos (Supabase → Edge Functions → Secrets):
//   ASAAS_API_KEY        chave da API do Asaas (sandbox começa com $aact_hmlg_, produção com $aact_prod_)
//   ASAAS_WEBHOOK_TOKEN  o authToken configurado no Webhook do Asaas (chega no header asaas-access-token)
// Opcionais: ASAAS_AMBIENTE = "producao" (padrão: sandbox) e APP_URL (para onde o cliente volta depois de pagar).
// SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY já existem nas Edge Functions.
import { createClient } from "jsr:@supabase/supabase-js@2";

const PROD = Deno.env.get("ASAAS_AMBIENTE") === "producao";
export const ASAAS_API = PROD ? "https://api.asaas.com/v3" : "https://api-sandbox.asaas.com/v3";
export const ASAAS_SITE = PROD ? "https://asaas.com" : "https://sandbox.asaas.com";
export const APP_URL = Deno.env.get("APP_URL") || "https://obasico-81.github.io/BR-Options/";

export const banco = () => createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });

export class ErroAsaas extends Error { constructor(public status: number, public detalhe: unknown) { super("Asaas " + status); } }

// deno-lint-ignore no-explicit-any
export async function asaas(metodo: string, caminho: string, corpo?: unknown): Promise<any> {
  const r = await fetch(ASAAS_API + caminho, {
    method: metodo,
    headers: { "access_token": Deno.env.get("ASAAS_API_KEY") ?? "", "Content-Type": "application/json", "User-Agent": "vaglio" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  const txt = await r.text(); let j: unknown = null; try { j = txt ? JSON.parse(txt) : null; } catch { j = txt; }
  if (!r.ok) throw new ErroAsaas(r.status, j);
  return j;
}

export const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
export const resposta = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), { status, headers: { ...CORS, "Content-Type": "application/json" } });

// A conta de quem chamou, pelo token da sessão (as funções do app exigem login)
export async function usuario(req: Request) {
  const tk = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!tk) return null;
  const { data, error } = await banco().auth.getUser(tk);
  return error ? null : data.user;
}
