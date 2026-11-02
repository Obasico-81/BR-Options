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
2. Em *Settings → Pages*, escolha *Source: GitHub Actions*.
3. Em *Actions → Atualizar dados e publicar o app → Run workflow*, preencha `ano` com o ano atual (ex.: `2026`)
   para completar os fechamentos desde o último dia do `snapshot.json`. Esse arquivo anual é grande (dezenas de MB).
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

## Limites conhecidos

- Só BOVA11, PETR4 e VALE3. Para incluir outro papel, edite `ATIVOS` em `atualizar_dados.py`.
- A cotação vem do fechamento do dia (melhor oferta de compra e venda no encerramento), não do preço ao vivo.
- Os dados do usuário (cadastro, operações simuladas) ficam só no aparelho.
- O app é uma calculadora: não indica o que operar e não promete resultado.
