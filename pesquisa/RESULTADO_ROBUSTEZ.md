# Robustez do histórico e saídas antecipadas — resultado

Run 43973520201 (pesquisa/robustez.py, commit 1d0af97). COTAHIST_A2015 a COTAHIST_A2026; 22532 operações com vencimento até
2026-11-13. Resultado médio por operação, em % do risco máximo, depois das taxas da B3; IC 95% por bootstrap em blocos mensais
(2000 reamostras). Saídas em dias corridos depois da entrada (primeiro pregão a partir da data, com preço nas duas pontas em
até 3 pregões). Sem preço para sair: 772 (3 dias), 760 (7 dias), 965 (15 dias) operações, fora das médias das saídas.
Corretagem: R$ 5 por ordem numa operação de até R$ 500 de risco.

## 1. Segurando até o vencimento

| operação | operações | resultado médio | IC 95% | 2015–2020 | 2021–2026 | ativos com média positiva | com corretagem |
|---|---|---|---|---|---|---|---|
| Trava de alta · Lucro maior | 1400 | -2.2% | [-15.6%; +12.4%] | +9.2% | -7.0% | 4 de 8 | -4.4% |
| Trava de alta · Equilibrada | 1995 | -12.0% | [-22.0%; -1.8%] | +0.0% | -17.0% | 1 de 8 | -14.3% |
| Trava de alta · Lucro frequente | 780 | -14.5% | [-21.8%; -7.7%] | -2.2% | -19.0% | 0 de 6 | -16.8% |
| Trava de baixa · Lucro maior | 924 | -12.1% | [-28.2%; +5.0%] | -25.8% | -9.3% | 4 de 8 | -14.3% |
| Trava de baixa · Equilibrada | 1531 | -11.3% | [-24.1%; +2.0%] | -34.3% | -6.4% | 2 de 8 | -13.5% |
| Trava de baixa · Lucro frequente | 503 | -17.7% | [-29.7%; -5.7%] | -33.1% | -16.0% | 1 de 6 | -20.0% |
| Strangle comprado | 1951 | +16.3% | [-1.1%; +37.4%] | +41.9% | +7.5% | 6 de 8 | +13.9% |
| Put vendida coberta | 2412 | -0.5% | [-1.5%; +0.2%] | +0.2% | -0.8% | 6 de 8 | -0.8% |
| Call comprada · Lucro maior | 2108 | +21.3% | [-14.4%; +62.5%] | +24.1% | +19.9% | 6 de 8 | +20.3% |
| Call comprada · Equilibrada | 2519 | +17.5% | [-5.9%; +40.3%] | +33.6% | +9.9% | 7 de 8 | +16.4% |
| Call comprada · Lucro frequente | 1717 | +5.8% | [-8.2%; +21.8%] | +19.2% | +0.8% | 6 de 8 | +4.6% |
| Put comprada · Lucro maior | 1994 | -5.7% | [-33.3%; +34.4%] | +32.7% | -18.3% | 2 de 8 | -6.8% |
| Put comprada · Equilibrada | 1945 | +0.5% | [-17.7%; +21.4%] | -1.6% | +1.1% | 2 de 8 | -0.6% |
| Put comprada · Lucro frequente | 753 | +2.3% | [-15.3%; +22.0%] | +10.0% | +1.0% | 5 de 7 | +1.2% |

## 2. Saída antecipada, no pior lado do fechamento (vende pela compra, recompra pela venda)

| operação | 3 dias: média [IC 95%] · com lucro | 7 dias: média [IC 95%] · com lucro | 15 dias: média [IC 95%] · com lucro | vencimento: com lucro |
|---|---|---|---|---|
| Trava de alta · Lucro maior | -45.2% [-48.8%; -41.9%] · 14% | -45.8% [-49.8%; -41.8%] · 17% | -40.6% [-45.9%; -35.7%] · 24% | 40% |
| Trava de alta · Equilibrada | -58.8% [-64.5%; -53.7%] · 9% | -56.9% [-62.0%; -52.7%] · 11% | -58.1% [-63.7%; -53.0%] · 18% | 45% |
| Trava de alta · Lucro frequente | -60.4% [-66.0%; -55.0%] · 2% | -60.6% [-66.2%; -55.1%] · 4% | -57.9% [-63.5%; -52.7%] · 8% | 59% |
| Trava de baixa · Lucro maior | -58.8% [-63.2%; -54.8%] · 8% | -63.1% [-70.0%; -56.5%] · 12% | -59.2% [-64.9%; -52.7%] · 15% | 29% |
| Trava de baixa · Equilibrada | -65.6% [-70.6%; -61.1%] · 5% | -67.4% [-74.8%; -61.3%] · 10% | -69.6% [-76.9%; -63.4%] · 12% | 37% |
| Trava de baixa · Lucro frequente | -65.3% [-72.3%; -58.8%] · 4% | -66.6% [-74.0%; -60.2%] · 5% | -68.4% [-78.1%; -60.1%] · 7% | 50% |
| Strangle comprado | -18.9% [-20.8%; -16.8%] · 13% | -19.0% [-21.7%; -15.9%] · 15% | -16.7% [-22.0%; -10.4%] · 21% | 38% |
| Put vendida coberta | -0.6% [-0.8%; -0.5%] · 39% | -0.6% [-0.9%; -0.4%] · 49% | -0.4% [-0.7%; -0.2%] · 61% | 79% |
| Call comprada · Lucro maior | -20.0% [-23.6%; -15.8%] · 22% | -19.1% [-24.7%; -12.6%] · 24% | -13.0% [-24.8%; +0.8%] · 25% | 19% |
| Call comprada · Equilibrada | -17.2% [-20.0%; -14.1%] · 25% | -17.3% [-21.3%; -13.3%] · 28% | -13.3% [-21.2%; -4.1%] · 30% | 31% |
| Call comprada · Lucro frequente | -22.0% [-24.0%; -20.1%] · 19% | -22.0% [-24.9%; -19.0%] · 24% | -22.5% [-26.9%; -17.6%] · 28% | 42% |
| Put comprada · Lucro maior | -26.2% [-28.7%; -23.6%] · 17% | -27.3% [-30.8%; -23.4%] · 19% | -30.9% [-36.9%; -25.2%] · 20% | 17% |
| Put comprada · Equilibrada | -23.8% [-26.4%; -20.8%] · 17% | -24.7% [-27.8%; -21.2%] · 20% | -28.5% [-35.3%; -21.0%] · 21% | 30% |
| Put comprada · Lucro frequente | -26.5% [-29.1%; -23.8%] · 15% | -26.6% [-31.7%; -20.4%] · 18% | -29.2% [-36.8%; -19.1%] · 21% | 41% |

## 3. Saída antecipada no preço médio (limite otimista) e com corretagem (pior lado)

| operação | 3 dias, médio | 7 dias, médio | 15 dias, médio | 3 dias, pior lado + corretagem | 7 dias, pior lado + corretagem | 15 dias, pior lado + corretagem |
|---|---|---|---|---|---|---|
| Trava de alta · Lucro maior | -13.1% | -10.8% | -10.9% | -49.6% | -50.2% | -45.0% |
| Trava de alta · Equilibrada | -18.2% | -17.8% | -19.4% | -63.4% | -61.5% | -62.7% |
| Trava de alta · Lucro frequente | -17.8% | -18.4% | -12.1% | -64.9% | -65.2% | -62.4% |
| Trava de baixa · Lucro maior | -18.7% | -21.0% | -20.9% | -63.1% | -67.4% | -63.5% |
| Trava de baixa · Equilibrada | -18.9% | -14.3% | -21.9% | -70.1% | -71.9% | -74.1% |
| Trava de baixa · Lucro frequente | -15.5% | -20.1% | -21.5% | -70.0% | -71.3% | -73.2% |
| Strangle comprado | -4.6% | -4.9% | -4.2% | -23.6% | -23.7% | -21.4% |
| Put vendida coberta | -0.1% | -0.1% | +0.0% | -1.1% | -1.1% | -0.9% |
| Call comprada · Lucro maior | -4.5% | -5.3% | +0.5% | -22.1% | -21.2% | -15.1% |
| Call comprada · Equilibrada | -5.3% | -5.3% | -1.8% | -19.5% | -19.6% | -15.6% |
| Call comprada · Lucro frequente | -7.4% | -8.6% | -8.2% | -24.4% | -24.3% | -24.8% |
| Put comprada · Lucro maior | -8.6% | -9.5% | -14.9% | -28.3% | -29.5% | -33.0% |
| Put comprada · Equilibrada | -8.3% | -9.1% | -13.3% | -26.2% | -27.0% | -30.8% |
| Put comprada · Lucro frequente | -8.1% | -9.5% | -11.3% | -28.8% | -28.9% | -31.5% |

## Hipóteses (fixadas antes de rodar)

- H1 Strangle comprado: NÃO PASSA (média +16.3%, IC [-1.1%; +37.4%], 2015–2020 +41.9%, 2021–2026 +7.5%)
- H1 Call comprada · Lucro maior: NÃO PASSA (média +21.3%, IC [-14.4%; +62.5%], 2015–2020 +24.1%, 2021–2026 +19.9%)
- H1 Call comprada · Equilibrada: NÃO PASSA (média +17.5%, IC [-5.9%; +40.3%], 2015–2020 +33.6%, 2021–2026 +9.9%)
- H1 Call comprada · Lucro frequente: NÃO PASSA (média +5.8%, IC [-8.2%; +21.8%], 2015–2020 +19.2%, 2021–2026 +0.8%)
- H2 trava de alta: PASSA (2015–2020: com lucro 66% × 45%, média -2.2% × +9.2%; 2021–2026: com lucro 57% × 38%, média -19.0% × -7.0%, Lucro frequente × Lucro maior)
- H2 trava de baixa: PASSA (2015–2020: com lucro 44% × 25%, média -33.1% × -25.8%; 2021–2026: com lucro 51% × 30%, média -16.0% × -9.3%, Lucro frequente × Lucro maior)

## Leitura

- H2 se mantém nos dois períodos e nos dois lados: o perfil que termina com lucro mais vezes tem resultado médio menor.
- H1 falha em todas: os resultados positivos do strangle e da call comprada dependem de poucas operações muito boas
  (IC cruza zero) e caem muito de 2015–2020 para 2021–2026. Não comunicar rentabilidade dessas operações.
- Saída em 3, 7 ou 15 dias: pior que segurar até o vencimento em todas as operações, no pior lado e no preço médio
  (única exceção: call comprada · Lucro maior em 15 dias no preço médio, +0,5%). A diferença entre pior lado e preço
  médio é o spread de saída; nas travas ela chega a 40–50 pontos do risco.
