# Tendência do minigráfico — back-test 2015–2026

Rodado em 04/11/2026 (run 41929842137, `pesquisa/tendencia.py`) com os COTAHIST anuais da B3 de 2015 a 2026, nos 11
papéis do app (B3SA3 a partir de 03/2018). Para cada dia de cada papel: a cor pela janela de 150 pregões até o dia (como
no app) e a direção do fechamento 20 pregões depois. Desdobramentos e grupamentos ajustados (BBAS3 2024; MGLU3 2017,
2020 e 2024; WEGE3 2015 e 2021; B3SA3 2021; PRIO3 2016, 2019 e 2021); bonificações e proventos não. IC 95% por
bootstrap em blocos mensais (todos os papéis juntos). Hipótese e medida fixadas antes de rodar.

## Resultado (2015–2026, 29.542 dias×papel; em um dia qualquer o papel subiu em 54,3% e caiu em 45,5%)

| regra | cor | % dos dias | seguiu na direção | dia qualquer | diferença | IC 95% |
|---|---|---|---|---|---|---|
| médias 21/50 + ADX (sem IFR) | verde | 25,1 | 56,5% | 54,3% | +2,2 pp | [−2,0, +6,1] |
| médias 21/50 + ADX (sem IFR) | vermelho | 16,5 | 43,1% | 45,5% | −2,4 pp | [−7,2, +2,3] |
| a mesma com IFR | verde | 25,1 | 56,5% | 54,3% | +2,2 pp | [−2,1, +6,0] |
| a mesma com IFR | vermelho | 16,5 | 43,1% | 45,5% | −2,4 pp | [−7,1, +2,2] |
| faixa de ±3% em 60 pregões (publicada) | verde | 49,3 | 53,4% | 54,3% | −0,8 pp | [−3,4, +1,7] |
| faixa de ±3% em 60 pregões (publicada) | vermelho | 36,8 | 43,8% | 45,5% | −1,8 pp | [−5,0, +1,4] |

Por período (sem IFR, diferença em pp): verde +1,9 (2015–20), +0,3 (2021–25), +1,0 (2026); vermelho −2,2, −3,2, −8,5.
Retorno médio 20 pregões depois de um dia vermelho: +2,5%, igual ao de um dia qualquer (+2,4%).

## Conclusão

- **Nenhuma das regras antecipa os 20 pregões seguintes**: todos os intervalos incluem zero. A cor descreve o
  passado, como a faixa de ±3%; não serve de base para nenhuma afirmação sobre o futuro no app.
- **O IFR não muda nada**: altera a cor em 12 de 7.422 dias verdes e 11 de 4.872 vermelhos (0,2%). Fica fora
  (decisão do Joe: se não ajudar, não usa).
- O vermelho seguiu em queda menos vezes que um dia qualquer nos três períodos (não significativo): depois de uma
  tendência de queda, o papel mais se recuperou do que continuou caindo.
- A regra por médias e ADX pinta menos dias (58% amarelo, contra 14% na faixa de ±3%) e demora a virar depois de um
  movimento brusco: em 03/11/2026, depois da queda de 26/10, 9 dos 11 papéis ficam amarelos (BBDC4 está 29% abaixo da
  média de 21, mas a de 21 ainda está acima da de 50).

## Limitações

- Observações sobrepostas (cada dia entra, prazo de 20 pregões).
- Bonificações e proventos não ajustados (a queda do dia ex entra no retorno, igual para a cor e para a linha de base).
- Papéis medidos juntos, com peso pelo número de dias; 6 comparações sem correção para múltiplas comparações.
