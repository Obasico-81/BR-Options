# Lançamento do Vaglio

Estado em 25/11/2026. Leia este arquivo primeiro ao continuar o trabalho em outra sessão (local ou na nuvem).

## Como o repositório está organizado

| Branch | O que tem |
|---|---|
| `assinatura` | o app (`template.html`, funções do Supabase em `supabase/functions/`, testes em `testes/`) |
| `lp` | as páginas (`lp/`: institucional, `bolsa-brasileira/` = campanha, `instalar/`) |
| `lancamento` | junta `assinatura` + `lp` + `main` (dados do dia). É daqui que se publica. |
| `main` | o que está no ar. O workflow noturno grava nela os "Dados do pregão AAAA-MM-DD". |

Mudança no app: commit em `assinatura` → merge em `lancamento`. Mudança nas páginas: commit em `lp` → merge em
`lancamento`. Antes de publicar: `git merge origin/main` no `lancamento` (traz os dados do dia).

**Publicar** (só com o "pode publicar" do dono): levar `lancamento` para `main` (fast-forward:
`git push origin lancamento:main`) e disparar *Atualizar dados e publicar o app* (`atualizar.yml`, Actions → Run
workflow). O push também dispara o *App nativo* (APK de produção) e os testes. Conferir no ar: `/`,
`/bolsa-brasileira/`, `/instalar/`, `/app/`.

**Gerar e testar localmente:** `python build.py && python build_pwa.py` (app em `pwa/`), `python build_site.py`
(site completo em `site/`, precisa de `pip install segno==1.6.6`). Testes: `node testes/assinatura.js`,
`node testes/site.js`, `node testes/smoke.js "$PWD/pwa/index.html"` etc. (lista completa em
`.github/workflows/testes.yml`; precisam de `npm install playwright` e do Chromium do Playwright).

## No ar

- **vaglio.com.br** (Cloudflare, só DNS; GitHub Pages com HTTPS). `/` institucional · `/bolsa-brasileira/` campanha
  · `/instalar/` · `/app/` o app. A raiz manda para `/app/` quem chega com parâmetro do app ou pelo app instalado.
- **APK de produção** (`br.com.vaglio.app`, chave de produção nos segredos do GitHub) em
  `releases/download/android/vaglio.apk`.
- **Tempo real "Em breve"** no que depende do fornecedor de dados. Com o fornecedor ligado, desfazer os commits
  "LPs: tempo real marcado como Em breve" (`lp`) e "Pro: em breve…" (`assinatura`) e devolver ao rodapé a frase
  "No Pro, cotações da B3 em tempo real, por distribuidor autorizado."
- Correção de 23/11: na tela do Pro, o erro do pagamento aparece acima do botão (antes a tela pulava para o topo e
  parecia voltar ao Início).

## Pronto no `lancamento`, esperando o "pode publicar"

- **`?plano=pro`**: o app abre direto na tela do Pro (sem conta, pede para entrar e volta ao Pro). Nas duas páginas,
  "Testar 7 dias grátis" leva a `https://vaglio.com.br/app/?plano=pro` em qualquer aparelho (antes abria o app no
  Início e quem queria assinar não achava onde). Testes novos em `testes/assinatura.js`; `testes/site.js` passa.

## Asaas: falta ligar a produção

O que aconteceu: a configuração foi feita na conta **sandbox** (sandbox.asaas.com, testes, sem dinheiro de verdade),
mas o Supabase foi posto em `ASAAS_AMBIENTE=producao`. O Asaas respondeu ao `assinar`: `invalid_environment` — "A
chave de API informada não pertence a este ambiente". Em 24-25/11 o dono criou a conta de **produção**
(www.asaas.com, conta separada, com login, chave e webhook próprios).

Passos (o dono faz; chave e token nunca no chat):
1. Asaas produção → Minha conta → Informações → **Site** `https://vaglio.com.br` (o Asaas só devolve o cliente,
   depois do pagamento, para endereços do site cadastrado).
2. Integrações → Chaves de API → gerar chave (começa com `$aact_prod_`) → Supabase, Edge Functions → Secrets
   (`https://supabase.com/dashboard/project/xoljwckdiedcfoygbiij/functions/secrets`) → `ASAAS_API_KEY`.
3. Token do webhook: aleatório, gerado pelo dono (ex.: PowerShell com `RandomNumberGenerator`, 32 bytes em hex).
4. Integrações → Webhooks → criar: URL `https://xoljwckdiedcfoygbiij.supabase.co/functions/v1/asaas-webhook`, API
   v3, o token, ativo, fila de sincronização ativa, envio sequencial, eventos `PAYMENT_*`, `SUBSCRIPTION_*`,
   `CHECKOUT_*` e `PIX_AUTOMATIC_RECURRING_*`.
5. O mesmo token em `ASAAS_WEBHOOK_TOKEN`.
6. `ASAAS_AMBIENTE` = `producao` (o digest no painel começa com `9ed87f9b8b22`; `sandbox` começa com
   `b7ad567477c8`). `APP_URL` = `https://vaglio.com.br/app/` (já está).

Depois, o teste real: app → Ajustes → Conhecer o Pro → Cartão → Começar 7 dias grátis, com o cartão do dono (nada é
cobrado nos 7 dias). Conferir: logs do Supabase (`function_logs` da função `assinar`, sem erro do Asaas), tabela
`assinaturas` (linha com `status = teste` e `teste_ate`) e `asaas_eventos` (eventos recebidos, sem 401 no
`asaas-webhook`). Depois cancelar em Ajustes e conferir `status = cancelada`.

Enquanto a produção não estiver ligada, **não divulgar**: quem tentar assinar recebe erro (ou, no sandbox, cai numa
página de teste do Asaas).

## Ainda antes de divulgar

- **Supabase no plano pago** (o grátis pausa o projeto e tem limites baixos para tráfego de anúncio).
- **Twilio:** saldo para os SMS de login. Pendente: remetente com a marca no RCS (chamado no suporte).
- **Pixel da Meta** (se for medir anúncios): ID do pixel para instalar nas três páginas; a política de privacidade
  passa a mencioná-lo.
- **Revisão jurídica** (CVM: operação montada, ordem pronta, publicidade).
- Texto dos anúncios sem "aposta"/"bet" (a revisão da Meta classifica como jogo). Links com UTM por canal.
- Pagamento dentro do APK: abrir o checkout do Asaas no navegador do celular (hoje o botão do Pro das páginas manda
  para o app no navegador, que funciona).

## Atualização noturna

O agendamento do GitHub (`atualizar.yml`, 01:17 e 12:17 UTC) falha com frequência. A rotina "Reserva atualização
BR-Options" (claude.ai, ~02:00 UTC) confere e dispara o workflow se ele não rodou. Às vezes o passo
`actions/deploy-pages` falha com "No artifacts named github-pages" (problema do GitHub, o arquivo foi enviado):
esperar alguns minutos e rodar de novo só o job que falhou — desde que a execução seja do commit que está na
`main`; se ela gravou dados novos, disparar uma execução nova em vez de repetir a antiga.

## Ferramentas

`ferramentas/telas-lp/`: scripts das telas das páginas, dos números dos avisos do hero e da imagem de compartilhamento.
