# Lançamento do Vaglio

Estado em 22/11/2026. Este branch (`lancamento`) junta `assinatura` (app com Pro, pagamento e tempo real),
`dominio` (site em vaglio.com.br) e `lp` (páginas). Publicar = levar este branch para `main`, e só com o
"pode publicar" do dono.

## Pronto

- **Domínio.** vaglio.com.br na Cloudflare (servidores byron e kia.ns.cloudflare.com; registros "somente DNS",
  sem proxy). GitHub Pages do BR-Options com domínio personalizado e HTTPS imposto (certificado Let's Encrypt até
  20/02/2027). www → raiz. O endereço antigo (obasico-81.github.io/BR-Options/…) redireciona para o domínio.
- **Site** (`build_site.py`): `/` institucional · `/bolsa-brasileira/` campanha · `/instalar/` como instalar (QR do
  próprio endereço) · `/app/` o app · dados do dia também na raiz (APK antigo). A raiz manda para `/app/` quem chega
  com parâmetro do app (`?teste=1`, `?assinatura=ok`…) ou pelo app instalado; `utm_*`/`fbclid` ficam na página.
- **Páginas:** textos revisados por especialista em copy; perfis "Ganho maior · Equilibrada · Chance maior"; telas
  com ativos variados; botões por aparelho (computador: app no navegador; Android: APK; iPhone: Safari).
- **APK de produção:** id `br.com.vaglio.app`, assinado com a chave de produção (segredos `ANDROID_KEYSTORE_BASE64`,
  `ANDROID_KEYSTORE_SENHA`, `ANDROID_CHAVE_ALIAS`, `ANDROID_CHAVE_SENHA`, cadastrados em 22/11), sem depuração, em
  `releases/download/android/vaglio.apk`. Quem tem o APK de teste fica com dois apps (ids diferentes) e apaga o antigo.
- **Testes:** a bateria do `testes.yml` passou localmente neste branch (o `deno check` das funções roda no GitHub).
- **Rotina noturna** (claude.ai, "Reserva atualização BR-Options") dispara `atualizar.yml` se o agendamento do
  GitHub não rodar.

## Falta antes de publicar (dono)

1. **Tempo real.** Publicado em 22/11 com "Em breve" no que depende do fornecedor de dados: avisos 2 e 3 do hero,
   Acompanhe ("Em breve, durante o pregão…"), itens 3 e 4 do Pro em Planos e na tela do Pro do app; a pergunta "Preciso
   de corretora?" sem "ao vivo"; rodapé sem "por distribuidor autorizado". Com o fornecedor ligado, desfazer os commits
   "LPs: tempo real marcado como Em breve" (branch lp) e "Pro: em breve…" (assinatura).
2. **Asaas em produção.** Conta aprovada. No Supabase (Edge Functions → Secrets): `ASAAS_API_KEY` de produção,
   `ASAAS_WEBHOOK_TOKEN`, `ASAAS_AMBIENTE=producao`, `APP_URL=https://vaglio.com.br/app/`. Na conta de produção do
   Asaas: webhook para `https://xoljwckdiedcfoygbiij.supabase.co/functions/v1/asaas-webhook`, com o mesmo token,
   envio sequencial e os eventos `PAYMENT_*`, `SUBSCRIPTION_*`, `CHECKOUT_*` e `PIX_AUTOMATIC_RECURRING_*`.
3. **Supabase no plano pago** (o grátis pausa o projeto e tem limites baixos para tráfego de anúncio).
4. **Twilio:** saldo para os SMS de login. Pendente: remetente com a marca no RCS (chamado no suporte).
5. **Pixel da Meta** (se for medir anúncios): ID do pixel para instalar nas três páginas; a política de privacidade
   passa a mencioná-lo.
6. **Revisão jurídica** (CVM: operação montada, ordem pronta, publicidade).

## Publicar (com o "pode publicar")

1. Trazer para cá o que entrou em `main` desde 20/11 (commits "Dados do pregão …"): `git merge origin/main`.
2. Levar `lancamento` para `main` (PR ou merge) e enviar.
3. O push dispara o *App nativo* (APK de produção; no log: "Com a chave de produção: APK assinado, sem depuração")
   e os testes. O site sai pelo *Atualizar dados e publicar o app*: disparar manualmente (Actions → Run workflow).
4. Conferir em produção: `/`, `/bolsa-brasileira/`, `/instalar/`, `/app/`, `/?teste=1` → `/app/`; login por SMS;
   uma assinatura real (e o cancelamento); baixar e instalar o APK.
5. Divulgar com links UTM por canal. Texto dos anúncios sem "aposta"/"bet" (a revisão da Meta classifica como jogo).

## Ferramentas

`ferramentas/telas-lp/`: scripts das telas das páginas, dos números dos avisos do hero e da imagem de compartilhamento.
