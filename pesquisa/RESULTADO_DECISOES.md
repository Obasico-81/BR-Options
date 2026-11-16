# Decisões do cliente com vantagem estatística — resultado

Run 43980845154 (pesquisa/decisoes.py, commit a9f8652). COTAHIST_A2015 a COTAHIST_A2026; 22.532 operações. Diferença por
operação (mesmo papel e dia), em pontos do risco máximo, depois das taxas da B3. IC 95% conjunto (Bonferroni pelo número de
comparações da família; bootstrap em blocos mensais, 4000 reamostras). Passa: IC inteiro de um lado do zero e o mesmo sinal
em 2015–2020 e 2021–2026 (critério fixado antes de rodar).

## D1. Perfil (segurando até o vencimento; 12 comparações)

| comparação | pares | diferença média | IC 95% conjunto | 2015–2020 | 2021–2026 | passa |
|---|---|---|---|---|---|---|
| Trava de alta: Lucro maior − Lucro frequente | 603 | +18.2 | [+0.0; +37.7] | +15.3 | +19.3 | PASSA (no limite) |
| Trava de alta: Lucro maior − Equilibrada | 1324 | +7.3 | [+1.8; +13.4] | +5.1 | +8.1 | PASSA |
| Trava de alta: Equilibrada − Lucro frequente | 761 | +8.6 | [-2.6; +19.9] | +10.5 | +7.9 | não |
| Trava de baixa: Lucro maior − Lucro frequente | 317 | +2.6 | [-18.9; +27.3] | +21.7 | +0.3 | não |
| Trava de baixa: Lucro maior − Equilibrada | 876 | -0.5 | [-8.3; +8.2] | +9.1 | -2.3 | não |
| Trava de baixa: Equilibrada − Lucro frequente | 472 | +11.5 | [-1.1; +26.7] | +3.4 | +12.4 | não |
| Call comprada: Lucro maior − Lucro frequente | 1326 | +27.0 | [-11.5; +82.8] | +31.6 | +25.0 | não |
| Call comprada: Lucro maior − Equilibrada | 1819 | +8.3 | [-13.1; +43.0] | +8.6 | +8.1 | não |
| Call comprada: Equilibrada − Lucro frequente | 1538 | +15.1 | [+0.1; +35.2] | +16.8 | +14.5 | PASSA (no limite) |
| Put comprada: Lucro maior − Lucro frequente | 626 | -13.5 | [-43.9; +37.2] | +95.6 | -31.9 | não |
| Put comprada: Lucro maior − Equilibrada | 1521 | -6.2 | [-20.0; +12.9] | +36.0 | -15.9 | não |
| Put comprada: Equilibrada − Lucro frequente | 664 | +0.2 | [-13.2; +18.3] | +19.8 | -2.8 | não |

## D2. Segurar até o vencimento − desfazer 3, 7 ou 15 dias depois (preço médio do fechamento; 42 comparações)

Nenhuma passa. Diferenças médias de −5 a +27 pontos, todos os IC conjuntos incluem zero (tabela completa no log do run).

## Leitura

- Única escolha com vantagem pelo critério: o perfil na trava de alta (Lucro maior acima da Equilibrada, +7 pontos por
  operação, nos dois períodos; acima do Lucro frequente, +18, no limite) e, no limite, a call comprada Equilibrada acima
  da Lucro frequente (+15). Vantagem relativa: o resultado médio do Lucro maior continua incerto (IC de −16 a +12).
- Nenhuma estrutura tem resultado médio positivo com segurança; seguir as regras de saída do app ou desfazer antes não
  muda o resultado médio de forma detectável.
