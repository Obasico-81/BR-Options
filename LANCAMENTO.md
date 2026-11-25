# Lançamento do Vaglio

Estado em 25/11/2026 (Asaas de produção ligado e testado). Leia este arquivo primeiro ao continuar o trabalho em outra sessão (local ou na nuvem).

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

## Asaas: produção ligada (25/11/2026)

A configuração inicial tinha sido feita na conta **sandbox** (sandbox.asaas.com, testes); a conta de **produção**
(www.asaas.com, conta separada) foi criada e ligada em 25/11. Segredos no Supabase (Edge Functions → Secrets):
`ASAAS_API_KEY` (chave de produção, `$aact_prod_…`), `ASAAS_WEBHOOK_TOKEN` (o mesmo token do webhook "Vaglio" da
conta de produção), `ASAAS_AMBIENTE=producao` (digest `9ed87f9b8b22…`), `APP_URL=https://vaglio.com.br/app/`
(digest `776fe7a847cf…`). Site da conta no Asaas: `https://vaglio.com.br`.

Teste real em 25/11, com cartão, plano anual: `assinar` abriu o checkout em asaas.com; avisos recebidos com 200
(CHECKOUT_CREATED, PAYMENT_CREATED de R$ 479 pendente para 01/12, CHECKOUT_PAID, SUBSCRIPTION_CREATED); assinatura em
`teste` até 01/12. Cancelado em Ajustes: SUBSCRIPTION_DELETED e PAYMENT_DELETED (a cobrança de 01/12 saiu), status
`cancelada`. Pix não testado em produção (testar com outra conta, que ainda tenha direito aos 7 dias grátis).

Erros do Asaas já vistos e o que significam (log da função `assinar` no Supabase): `invalid_environment` = chave de
um ambiente e `ASAAS_AMBIENTE` do outro; `invalid_access_token` = chave inválida (colada incompleta, sem o `$`, ou
desativada). `asaas-webhook` com 401 = token do webhook no Asaas diferente de `ASAAS_WEBHOOK_TOKEN`; corrigido o
token, reativar a fila do webhook no Asaas se ela tiver sido pausada.

## Marca e dados legais (25/11/2026)

- **E-mail:** `contato@vaglio.com.br` funciona pelo Email Routing da Cloudflare (encaminha para o e-mail do dono,
  verificado). Para isso saíram do DNS o MX nulo (`0 .`) e o TXT `v=spf1 -all`, que recusavam todo e-mail; o
  `_dmarc` (`p=reject`) ficou.
- **Asaas:** e-mail comercial trocado para `contato@vaglio.com.br` e logo do Vaglio enviado para a fatura (os dois
  passam por análise do Asaas). O nome da empresa e o CNPJ não saem da fatura (regra do Asaas). Para aparecer
  "Vaglio" no lugar da razão social: registrar Vaglio como nome fantasia do CNPJ na Receita (contador) e ativar no
  Asaas. Separação completa só com CNPJ próprio do Vaglio. Checkout transparente foi descartado: não esconde a
  empresa (Pix e fatura do cartão mostram quem recebe) e faria o cartão passar pelos servidores do Vaglio (PCI).
- **Textos legais publicados:** Termos e Política de privacidade com o responsável (Excel Solutions, CNPJ,
  endereço) e `contato@vaglio.com.br` (`textos/contato.json`), descrevendo conta por celular, sincronização,
  assinatura pelo Asaas e direitos da LGPD; rodapé das três páginas com nome empresarial, CNPJ e endereço (Decreto
  7.962/2013). Falta a revisão jurídica.
- **Testes do Pix e do cartão em produção (25/11):** as duas contas de teste estão canceladas.

## Ainda antes de divulgar

- **Supabase no plano pago** (o grátis pausa o projeto e tem limites baixos para tráfego de anúncio).
- **Twilio:** saldo para os SMS de login (em 25/11 um código levou alguns minutos para chegar). Pendente: remetente com a marca no RCS (chamado no suporte).
- **Pixel da Meta** (se for medir anúncios): ID do pixel para instalar nas três páginas; a política de privacidade
  passa a mencioná-lo.
- **Revisão jurídica** (CVM: operação montada, ordem pronta, publicidade).
- Texto dos anúncios sem "aposta"/"bet" (a revisão da Meta classifica como jogo). Links com UTM por canal.
- Pagamento dentro do APK: abrir o checkout do Asaas no navegador do celular (hoje o botão do Pro das páginas manda
  para o app no navegador, que funciona).

## Atualização noturna

O agendamento do GitHub (`atualizar.yml`, 01:17 e 12:17 UTC) falha com frequência. A tarefa agendada "Reserva atualização
Vaglio" (claude.ai, 02:02 UTC de terça a sábado) roda na sessão de nuvem "Reserva atualização Vaglio", que tem o
repositório (não arquivar essa sessão); ela confere e dispara o workflow se ele não rodou. A rotina antiga, presa ao
chat de desenvolvimento, foi desligada em 25/11. Às vezes o passo
`actions/deploy-pages` falha com "No artifacts named github-pages" (problema do GitHub, o arquivo foi enviado):
esperar alguns minutos e rodar de novo só o job que falhou — desde que a execução seja do commit que está na
`main`; se ela gravou dados novos, disparar uma execução nova em vez de repetir a antiga.

## Ferramentas

`ferramentas/telas-lp/`: scripts das telas das páginas, dos números dos avisos do hero e da imagem de compartilhamento.
