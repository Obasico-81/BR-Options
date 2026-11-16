# Histórico das operações do app (2015 até 13/11/2026)

`pesquisa/historico.py`, run 43969519298 (16/11/2026). De todas as vezes que o app montaria cada operação, a cada 5
pregões, nos 8 papéis do app, com a cadeia do dia e a Selic do dia: 22.532 montagens com vencimento até 13/11/2026,
seguradas até o vencimento; lucro depois das taxas da B3, sem corretagem; execução no pior lado na entrada. IC 95% da
frequência de lucro por bootstrap em blocos mensais.

| operação | operações | chance média na tela | terminaram com lucro | IC 95% | resultado médio (% do risco) |
|---|---|---|---|---|---|
| Trava de alta · Lucro maior | 1.400 | 35,2% | 40,1% | [34,8; 45,4] | −2,2% |
| Trava de alta · Equilibrada | 1.995 | 41,7% | 44,8% | [39,3; 50,2] | −12,0% |
| Trava de alta · Lucro frequente | 780 | 57,5% | 59,5% | [53,3; 65,0] | −14,5% |
| Trava de baixa · Lucro maior | 924 | 30,8% | 29,1% | [24,3; 34,5] | −12,1% |
| Trava de baixa · Equilibrada | 1.531 | 38,4% | 37,0% | [31,8; 42,0] | −11,3% |
| Trava de baixa · Lucro frequente | 503 | 53,8% | 50,1% | [42,5; 57,6] | −17,7% |
| Strangle comprado | 1.951 | 32,7% | 38,2% | [34,5; 42,3] | +16,3% |
| Put vendida coberta | 2.412 | 78,3% | 78,9% | [75,4; 82,4] | −0,5% |
| Call comprada · Lucro maior | 2.108 | 15,8% | 19,2% | [15,4; 23,6] | +21,3% |
| Call comprada · Equilibrada | 2.519 | 27,2% | 31,0% | [26,7; 35,5] | +17,5% |
| Call comprada · Lucro frequente | 1.717 | 37,9% | 41,9% | [36,6; 47,2] | +5,8% |
| Put comprada · Lucro maior | 1.994 | 17,2% | 17,1% | [13,8; 20,6] | −5,7% |
| Put comprada · Equilibrada | 1.945 | 31,5% | 30,0% | [25,4; 34,8] | +0,5% |
| Put comprada · Lucro frequente | 753 | 42,8% | 40,8% | [33,9; 47,4] | +2,3% |

Por faixa da chance na tela, a frequência de lucro acompanha a chance (ex.: put vendida 60–70% → 67%; 70–80% → 77%;
80–90% → 83%; 90–100% → 94%). Tabela por faixa e o JSON para o app: saída do run.

## Leitura

- A chance mostrada bate com o que aconteceu, em todas as operações e perfis (diferença de poucos pontos).
- Mais chance não é mais resultado: nas travas, o Lucro frequente ganhou mais vezes (59,5% na de alta) e teve o pior
  resultado médio (−14,5% do risco por operação); o Lucro maior ganhou menos vezes (40,1%) e perdeu menos em média (−2,2%).
- O resultado médio positivo do strangle e das calls compradas é deste período (2015–2026) e não tem IC aqui; não é
  vantagem garantida.
