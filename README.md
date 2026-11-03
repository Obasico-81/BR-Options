# Montador de Opções — app instalável com dados diários

Ferramenta que monta operações com opções (custo, perda máxima, equilíbrio e cenários). Modo simulado.
Funciona no navegador do celular e pode ser instalada na tela inicial (PWA).

## Como funciona a atualização diária

1. Todo dia útil à noite, o GitHub Actions (`.github/workflows/atualizar.yml`) baixa da B3 o arquivo
   `COTAHIST_Dddmmaaaa.ZIP` (cotações do pregão) e roda `atualizar_dados.py`.
2. O script lê preço de fechamento e melhor compra/venda das opções de BOVA11, PETR4 e VALE3,
   calcula a volatilidade implícita e grava `snapshot.json`.
3. `build.py` embute o snapshot e `montador.js` em um único `index.html`; `build_pwa.py` gera `pwa/index.html`.
4. A pasta `pwa/` é publicada no GitHub Pages (endereço HTTPS público), de onde o celular instala o app.
5. Se o dado ficar com mais de 5 dias, o app mostra "Preços desatualizados" e bloqueia a cópia dos parâmetros.

## Colocar no ar (uma vez)

1. Crie um repositório no GitHub e envie estes arquivos.
2. Em *Settings → Pages*, escolha *Source: GitHub Actions*. No plano gratuito do GitHub, o Pages só funciona em
   repositório **público**; repositório privado exige plano pago (Pro, Team ou Enterprise).
3. Em *Actions → Atualizar dados e publicar o app → Run workflow*, marque `validar` e preencha `ano` com o ano atual
   (ex.: `2026`). `validar` baixa o arquivo real de 30/12/2025 e roda `--validar` antes de gravar qualquer coisa: se der
   DIFERENTE, o job para e nada é publicado. `ano` completa os fechamentos desde o último dia do `snapshot.json`
   (arquivo anual grande, dezenas de MB). `validar` só funciona enquanto o snapshot ainda tiver o dia 30/12/2025,
   ou seja, antes de 12 pregões novos.
4. O endereço do app aparece no fim da execução. Abra no celular e instale:
   - Android (Chrome): menu → *Instalar app*.
   - iPhone (Safari): *Compartilhar → Adicionar à Tela de Início*.

## Conferir antes de confiar (importante)

O leitor do arquivo da B3 foi escrito a partir do layout oficial de posição fixa, mas **ainda não foi testado com um
arquivo real**: o ambiente em que foi criado não alcança o site da B3. Antes de confiar nos números:

```
# baixe COTAHIST_D30122025.ZIP no site da B3 (Séries Históricas) e rode:
python atualizar_dados.py --validar COTAHIST_D30122025.ZIP
```

O snapshot atual tem esse dia (30/12/2025, gerado por outra ferramenta, o rb3). O comando compara preço, número de
opções e volatilidade implícita de cada papel e imprime IGUAL ou DIFERENTE. Se algum papel vier DIFERENTE, não publique:
as posições dos campos em `CAMPOS` precisam ser revistas.

## Uso local

```
python atualizar_dados.py                      # pregão mais recente
python atualizar_dados.py --arquivo ARQ.ZIP    # arquivo já baixado
python build.py && python build_pwa.py         # gera index.html e pwa/index.html
python -m http.server -d pwa 8000              # testar em http://localhost:8000
```

Modo teste (escolher o dia dos preços): abra o app com `?teste=1` no endereço.

## Testes (sem acesso à B3)

```
python3 build.py && python3 build_pwa.py
python3 paridade.py                          # montador.py × montador.js no snapshot atual (esperado: 0 falha(s))
python3 -I testes/teste_atualizador.py .     # atualizador contra um servidor local que imita a B3
node testes/smoke.js "$PWD/pwa/index.html"   # abre o app (Playwright) e percorre as telas
node testes/marcacao.js                      # marcação diária: contas e app servido por HTTP com preços sintéticos
```

**Preços diários.** O atualizador grava `pwa/precos/AAAA-MM-DD.json` (melhor compra e venda no fechamento de cada série
dos ativos do app, 5 a 100 dias), um arquivo novo por pregão, publicado com o app. O app usa esses arquivos para marcar
cada operação simulada: "Se encerrar hoje" em *Sua operação* e, no *Desempenho*, a saída pela primeira regra atingida
(alvo, limite ou prazo) no fechamento de cada dia, ou o vencimento. `--ano` grava os dias que faltam do ano inteiro.

`paridade.py` compara `montador.py` e `montador.js` em todos os ativos do snapshot: as 4 estruturas, o sinal (trava e
put), a compra simples no caminho padrão e nos 3 perfis (Lucro maior · Equilibrada · Lucro frequente) com o theta, tudo
sem e com corretagem cadastrada, o movimento necessário × oscilação de 60 pregões (`volReal60` / `movimentoNecessario`) e a
marcação diária: "Se encerrar hoje" e as regras de saída (`resultadoNoDia` / `regraDeSaida`).
O workflow *Testes* roda tudo isso a cada mudança de código; a atualização noturna roda a paridade com o dado do dia
sem bloquear a publicação.
Os scripts de `pesquisa/` leem dados que não estão no repositório (histórico de opções 2015–2025 em CSV e séries de
preço em pickle, em `/tmp/claude-0/`).

`teste_atualizador.py` gera arquivos COTAHIST sintéticos e cobre: `--validar`, feriado, pregão perdido (recupera o
fechamento), buraco maior que uma semana (avisa para rodar `--ano`), B3 respondendo 403 ou HTML (falha visível em vez
de "nada a fazer"), dia incompleto e a sequência `--ano` + execução diária do workflow. Os arquivos sintéticos usam o
mesmo layout do leitor; **não substituem** o `--validar` com o arquivo real.

## Pesquisa (reteste fora da amostra)

*Actions → Pesquisa fora da amostra (2026) → Run workflow* baixa os COTAHIST anuais (DE a ATE), monta a base com
`pesquisa/montar_base.py` (mesmo leitor do atualizador) e roda `pesquisa_perfis.py` e `pesquisa_gregas.py` sem mudar
hipóteses, filtros nem cortes. Cada script imprime a linha de base 2015-2025 e, separado, o resultado das entradas
de 2026. Os resultados ficam no log e no artefato `pesquisa-DE-ATE`. Para rodar local: `DADOS=pasta SUF=1526 python
pesquisa_perfis.py` dentro de `pesquisa/`, depois de montar a base.

## Limites conhecidos

- Ativos: BOVA11, PETR4, VALE3, BBDC4, BBAS3, MGLU3, WEGE3, ITUB4, USIM5 e B3SA3 (`ATIVOS` em `atualizar_dados.py`; os 7 últimos entraram em 02/11/2026 por montarem em >= 60% dos pregões, ver `pesquisa/liquidez.py`). BOVA11, PETR4 e VALE3 são obrigatórios: se um deles vier incompleto, nada é gravado; um dos outros que vier com menos de 20 opções fica de fora só naquele dia.
- A cotação vem do fechamento do dia (melhor oferta de compra e venda no encerramento), não do preço ao vivo.
- Os dados do usuário (cadastro, operações simuladas) ficam só no aparelho.
- O app é uma calculadora: não indica o que operar e não promete resultado.
