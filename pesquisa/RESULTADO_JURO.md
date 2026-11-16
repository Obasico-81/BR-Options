# Juro do Black-Scholes: Selic do dia × 11% fixo

`pesquisa/juro.py`, run 43808793824 (16/11/2026). As operações que o montador.py monta a cada 5 pregões, de 2015 até
13/11/2026, nos 8 papéis do app e nas 6 estruturas, seguradas até o vencimento: 12.438 operações em cada versão (as
mesmas séries nas duas). Selic: meta do Copom por dia (Banco Central, SGS 432), de 2,00% a 15,00% nos dias de entrada
(média 10,50%). Fixo: 11% a.a. Em cada versão, a volatilidade implícita e a chance usam o mesmo juro. IC 95% por
bootstrap em blocos mensais.

## Calibração por faixa (tudo)

| chance na tela | ops | fixo: chance média | fixo: além do equilíbrio | Selic: chance média | Selic: além do equilíbrio |
|---|---|---|---|---|---|
| 20–30% | 1.673 / 1.690 | 26,7 | 33,1 | 26,8 | 31,7 |
| 30–40% | 5.764 / 5.815 | 34,6 | 36,3 | 34,7 | 36,5 |
| 40–50% | 2.380 / 2.337 | 43,1 | 43,6 | 43,1 | 44,0 |
| 60–70% | 371 / 418 | 66,6 | 68,7 | 66,6 | 67,0 |
| 70–80% | 1.029 / 1.021 | 75,2 | 75,9 | 74,9 | 77,4 |
| 80–90% | 717 / 695 | 84,1 | 84,0 | 84,2 | 82,9 |
| 90–100% | 287 / 270 | 94,5 | 90,6 | 94,4 | 93,7 |

Erro de calibração (|chance média − frequência| por faixa, ponderado): **fixo 2,1 pontos; Selic do dia 2,1 pontos.**

## Brier nas mesmas operações

Fixo 0,21907; Selic do dia 0,21865; diferença −0,00042, IC 95% [−0,00197; +0,00116]: sem diferença.

| Selic no dia da entrada | operações | erro de calibração fixo | erro Selic do dia | Brier (Selic − fixo) | IC 95% |
|---|---|---|---|---|---|
| abaixo de 7% | 3.318 | 3,1 | 1,9 | −0,00084 | [−0,00665; +0,00449] |
| 7% a 11% | 1.947 | 3,9 | 4,1 | +0,00104 | [−0,00039; +0,00267] |
| 11% ou mais | 7.173 | 2,8 | 3,3 | −0,00062 | [−0,00149; +0,00035] |

## Leitura

No histórico, a Selic do dia e o fixo de 11% acertam igual: o mesmo erro de calibração e Brier sem diferença, em
todos os níveis da Selic. A média da Selic no período (10,5%) é quase o fixo, e o efeito do juro na chance é pequeno
perto da incerteza do resultado de cada operação. A Selic do dia é a conta certa pela teoria (o preço das opções já
embute o juro do dia) e não piora a calibração; no pregão de 13/11/2026 (Selic 13,75%), ela muda a chance das travas
de alta em +1,0 ponto, das de baixa em −2,0, do strangle em −1,0 e da put vendida em +1,4, em média, e a volatilidade
implícita cai cerca de 0,8 ponto.

A consulta ao Banco Central funcionou no runner do GitHub (4.369 dias da série), o mesmo ambiente do atualizador.
