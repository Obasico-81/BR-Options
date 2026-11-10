Rodado em 10/11/2026 (run 42734375210, `pesquisa/hilo.py --fase explorar`), COTAHIST anuais de 2015 a 2026, nos 8 papéis do app. Sinais de 2015 a 2021; 2022 em diante guardado para confirmação (não rodada: nenhuma combinação se destacou).

# Resultado — setup HiLo + candle de força + Fibonacci — fase: explorar (sinais de 2015 a 2021)

Papéis: BOVA11, PETR4, VALE3, BBDC4, BBAS3, MGLU3, ITUB4, B3SA3. HiLo (3, 5, 8, 13), candle de força com corpo ≥ 60%, 70%, 80% do tamanho; níveis de 61,8%, 100% e 161,8% do tamanho a partir da máxima (mínima). Principal: HiLo 3, corpo ≥ 70%. IC 95% por bootstrap em blocos mensais.

## 1. Toque nos níveis de Fibonacci — combinação principal (HiLo 3, corpo ≥ 70%)

### Sinais de alta (call): 449 · distância mediana do fechamento: 61,8% → 2.5%, 100% → 3.9%, 161,8% → 6.2%
| nível | prazo | tocou (setup) | dia qualquer, mesma distância | diferença [IC 95%] |
|---|---|---|---|---|
| 61.8% | 5 pregões | 55.2% | 58.4% | -3.2 pp [-8.5, +2.1] |
| 61.8% | 10 pregões | 68.8% | 70.2% | -1.4 pp [-6.9, +3.9] |
| 61.8% | 20 pregões | 76.2% | 78.8% | -2.7 pp [-8.4, +2.7] |
| 61.8% | até o HiLo virar de volta | 57.7% | — | — |
| 100.0% | 5 pregões | 40.3% | 42.0% | -1.7 pp [-7.1, +3.8] |
| 100.0% | 10 pregões | 53.9% | 56.6% | -2.7 pp [-8.9, +3.2] |
| 100.0% | 20 pregões | 66.8% | 68.6% | -1.8 pp [-8.0, +4.3] |
| 100.0% | até o HiLo virar de volta | 44.1% | — | — |
| 161.8% | 5 pregões | 22.0% | 24.7% | -2.6 pp [-7.6, +2.3] |
| 161.8% | 10 pregões | 35.9% | 39.2% | -3.3 pp [-8.8, +2.4] |
| 161.8% | 20 pregões | 49.4% | 54.2% | -4.8 pp [-11.6, +2.1] |
| 161.8% | até o HiLo virar de volta | 30.1% | — | — |

### Sinais de baixa (put): 461 · distância mediana do fechamento: 61,8% → 2.4%, 100% → 3.8%, 161,8% → 6.0%
| nível | prazo | tocou (setup) | dia qualquer, mesma distância | diferença [IC 95%] |
|---|---|---|---|---|
| 61.8% | 5 pregões | 56.2% | 52.4% | +3.8 pp [-3.2, +10.7] |
| 61.8% | 10 pregões | 68.1% | 63.7% | +4.4 pp [-2.7, +11.1] |
| 61.8% | 20 pregões | 75.9% | 72.1% | +3.8 pp [-2.3, +9.7] |
| 61.8% | até o HiLo virar de volta | 59.4% | — | — |
| 100.0% | 5 pregões | 35.6% | 36.8% | -1.2 pp [-7.5, +4.9] |
| 100.0% | 10 pregões | 50.3% | 49.9% | +0.5 pp [-6.3, +7.1] |
| 100.0% | 20 pregões | 62.9% | 60.9% | +2.0 pp [-5.1, +8.8] |
| 100.0% | até o HiLo virar de volta | 44.0% | — | — |
| 161.8% | 5 pregões | 19.1% | 21.0% | -1.9 pp [-6.2, +2.8] |
| 161.8% | 10 pregões | 32.1% | 33.1% | -1.0 pp [-6.7, +5.2] |
| 161.8% | 20 pregões | 45.8% | 45.8% | -0.1 pp [-7.6, +7.1] |
| 161.8% | até o HiLo virar de volta | 29.7% | — | — |

## 2. Toque em 161,8% em 10 pregões, por combinação (setup × viradas sem força × força sem virada × dia qualquer)

| HiLo | corpo ≥ | direção | setup: sinais / tocou | dia qualquer | virada sem força | força sem virada |
|---|---|---|---|---|---|---|
| 3 | 60% | alta | 591 / 35.7% | 39.7% | 40.4% | 45.1% |
| 3 | 60% | baixa | 632 / 33.1% | 33.8% | 35.2% | 33.8% |
| 3 | 70% | alta | 449 / 35.9% | 39.2% | 39.1% | 45.4% |
| 3 | 70% | baixa | 461 / 32.1% | 33.1% | 35.4% | 33.0% |
| 3 | 80% | alta | 274 / 34.7% | 38.9% | 38.8% | 45.0% |
| 3 | 80% | baixa | 283 / 27.9% | 32.8% | 36.2% | 31.4% |
| 5 | 60% | alta | 469 / 35.8% | 39.4% | 39.7% | 44.4% |
| 5 | 60% | baixa | 486 / 29.0% | 33.0% | 34.9% | 34.8% |
| 5 | 70% | alta | 358 / 35.5% | 39.2% | 39.0% | 44.7% |
| 5 | 70% | baixa | 359 / 28.1% | 31.8% | 34.0% | 34.1% |
| 5 | 80% | alta | 229 / 33.2% | 38.6% | 39.1% | 44.7% |
| 5 | 80% | baixa | 241 / 24.9% | 31.3% | 34.1% | 32.4% |
| 8 | 60% | alta | 372 / 32.5% | 37.8% | 40.4% | 44.7% |
| 8 | 60% | baixa | 378 / 29.9% | 32.0% | 35.2% | 34.5% |
| 8 | 70% | alta | 285 / 33.7% | 37.4% | 37.4% | 44.7% |
| 8 | 70% | baixa | 280 / 30.4% | 31.6% | 33.3% | 33.4% |
| 8 | 80% | alta | 193 / 33.7% | 38.0% | 36.6% | 44.1% |
| 8 | 80% | baixa | 187 / 27.8% | 31.4% | 33.8% | 31.3% |
| 13 | 60% | alta | 290 / 34.8% | 37.1% | 35.6% | 43.8% |
| 13 | 60% | baixa | 287 / 30.0% | 31.8% | 37.0% | 34.2% |
| 13 | 70% | alta | 230 / 34.3% | 37.1% | 35.9% | 44.0% |
| 13 | 70% | baixa | 215 / 29.8% | 30.9% | 35.2% | 33.3% |
| 13 | 80% | alta | 151 / 35.1% | 37.0% | 35.2% | 43.2% |
| 13 | 80% | baixa | 140 / 28.6% | 29.7% | 34.5% | 30.9% |

## 3. A operação com opções (preços reais): compra no fechamento do sinal, strike mais perto do alvo de 161,8%

Entrada pela oferta de venda. Saída: alvo tocado pela ação (realista: oferta de compra no fechamento; otimista: máxima da opção no dia), ou 20º pregão, ou vencimento (valor intrínseco). "Dia qualquer": a mesma compra, à distância mediana do alvo dos sinais principais, a cada 5 pregões sem sinal. Retorno sobre o prêmio pago.

| combinação | direção | operações (sem opção) | com lucro (realista) | retorno médio realista [IC 95%] | mediana | retorno médio otimista | tocou o alvo |
|---|---|---|---|---|---|---|---|
| dia qualquer | alta | 1935 (469) | 32.9% | -29% [-38%, -18%] | -77% | +1% | 50.2% |
| HiLo 3, corpo ≥ 60% | alta | 456 (113) | 30.0% | -36% [-47%, -25%] | -92% | -8% | 43.2% |
| HiLo 3, corpo ≥ 70% | alta | 345 (87) | 32.2% | -33% [-45%, -22%] | -89% | -4% | 45.5% |
| HiLo 3, corpo ≥ 80% | alta | 209 (58) | 31.1% | -34% [-48%, -20%] | -93% | -5% | 44.0% |
| HiLo 5, corpo ≥ 60% | alta | 368 (81) | 32.3% | -33% [-45%, -20%] | -90% | -7% | 43.5% |
| HiLo 5, corpo ≥ 70% | alta | 279 (64) | 34.4% | -30% [-44%, -15%] | -89% | -5% | 44.4% |
| HiLo 5, corpo ≥ 80% | alta | 178 (45) | 31.5% | -34% [-50%, -16%] | -92% | -9% | 42.7% |
| HiLo 8, corpo ≥ 60% | alta | 296 (60) | 30.1% | -40% [-52%, -29%] | -93% | -12% | 40.2% |
| HiLo 8, corpo ≥ 70% | alta | 223 (49) | 32.7% | -35% [-49%, -21%] | -92% | -5% | 43.5% |
| HiLo 8, corpo ≥ 80% | alta | 153 (35) | 30.7% | -39% [-53%, -24%] | -94% | -9% | 42.5% |
| HiLo 13, corpo ≥ 60% | alta | 228 (51) | 32.9% | -34% [-46%, -22%] | -90% | -5% | 43.0% |
| HiLo 13, corpo ≥ 70% | alta | 184 (38) | 33.7% | -32% [-47%, -16%] | -89% | +0% | 45.1% |
| HiLo 13, corpo ≥ 80% | alta | 120 (28) | 32.5% | -35% [-53%, -16%] | -93% | -5% | 42.5% |
| HiLo 3, corpo ≥ 70% · saída quando o HiLo vira (vídeo) | alta | 357 (87) | 21.0% | -30% [-37%, -22%] | -49% | -11% | 26.9% |
| dia qualquer | baixa | 1780 (576) | 20.2% | -49% [-57%, -40%] | -95% | -19% | 42.1% |
| HiLo 3, corpo ≥ 60% | baixa | 441 (163) | 20.9% | -45% [-58%, -27%] | -94% | -10% | 43.5% |
| HiLo 3, corpo ≥ 70% | baixa | 313 (125) | 21.4% | -50% [-61%, -39%] | -94% | -17% | 43.5% |
| HiLo 3, corpo ≥ 80% | baixa | 188 (77) | 18.6% | -53% [-65%, -40%] | -96% | -24% | 40.4% |
| HiLo 5, corpo ≥ 60% | baixa | 337 (127) | 19.6% | -54% [-65%, -43%] | -97% | -23% | 39.8% |
| HiLo 5, corpo ≥ 70% | baixa | 242 (97) | 20.2% | -53% [-65%, -41%] | -97% | -25% | 40.5% |
| HiLo 5, corpo ≥ 80% | baixa | 159 (65) | 17.6% | -55% [-68%, -38%] | -96% | -26% | 41.5% |
| HiLo 8, corpo ≥ 60% | baixa | 265 (94) | 23.4% | -47% [-61%, -31%] | -97% | -15% | 41.5% |
| HiLo 8, corpo ≥ 70% | baixa | 195 (69) | 25.6% | -44% [-59%, -26%] | -96% | -9% | 44.1% |
| HiLo 8, corpo ≥ 80% | baixa | 128 (46) | 25.0% | -47% [-62%, -30%] | -95% | -20% | 43.8% |
| HiLo 13, corpo ≥ 60% | baixa | 213 (55) | 22.5% | -47% [-62%, -30%] | -95% | -13% | 41.3% |
| HiLo 13, corpo ≥ 70% | baixa | 161 (42) | 21.7% | -49% [-64%, -34%] | -95% | -12% | 41.6% |
| HiLo 13, corpo ≥ 80% | baixa | 106 (26) | 21.7% | -47% [-63%, -30%] | -95% | -12% | 42.5% |
| HiLo 3, corpo ≥ 70% · saída quando o HiLo vira (vídeo) | baixa | 328 (125) | 14.3% | -42% [-49%, -35%] | -59% | -21% | 29.0% |

Limitações: só pregões completos (o sinal é conferido no fechamento; na prática a decisão é um pouco antes); a saída no alvo usa o preço de fechamento da opção no dia do toque (realista) ou a máxima do dia (otimista, pode não ter sido possível); opções sem oferta no dia do sinal ficam de fora (coluna "sem opção"); muitas combinações na exploração: escolher a melhor e conferir só uma vez na fase de confirmação.