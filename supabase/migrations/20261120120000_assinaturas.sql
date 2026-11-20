-- Assinatura do Vaglio Pro (Asaas). Uma linha por conta. O app só lê a própria linha; quem escreve são as Edge
-- Functions (assinar, cancelar-assinatura, asaas-webhook), com a chave de serviço.
--   status: aguardando (pagamento aberto, sem autorização), teste (7 dias grátis), ativa, atrasada, cancelada, estornada
--   pro_ate: até que dia (inclusive) a conta tem o Pro. É o que o app consulta.
--   teste_ate: fim do teste grátis; preenchido uma vez só (a conta não ganha um segundo teste).
create table if not exists public.assinaturas (
  user_id uuid primary key references auth.users (id) on delete cascade,
  status text not null default 'aguardando'
    check (status in ('aguardando', 'teste', 'ativa', 'atrasada', 'cancelada', 'estornada')),
  plano text check (plano in ('mensal', 'anual')),
  forma text check (forma in ('PIX', 'CREDIT_CARD')),
  pro_ate date,
  teste_ate date,
  asaas_cliente text,
  asaas_assinatura text unique,
  asaas_checkout text unique,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index if not exists assinaturas_asaas_cliente on public.assinaturas (asaas_cliente);

alter table public.assinaturas enable row level security;
drop policy if exists "assinatura: dono lê" on public.assinaturas;
create policy "assinatura: dono lê" on public.assinaturas
  for select to authenticated using ((select auth.uid()) = user_id);
-- sem políticas de insert/update/delete: só a chave de serviço escreve

-- Avisos do Asaas já processados (o Asaas pode reenviar o mesmo evento): a chave é o id do evento.
create table if not exists public.asaas_eventos (
  id text primary key,
  tipo text not null,
  recebido_em timestamptz not null default now(),
  payload jsonb not null
);
alter table public.asaas_eventos enable row level security;
-- sem políticas: ninguém além da chave de serviço lê ou escreve
