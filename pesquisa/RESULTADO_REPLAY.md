# Replay do app no histórico (2015–2026)

`pesquisa/replay.py`, run 41945176708 (05/11/2026). As operações que o montador.py monta, refeitas a cada 5 pregões
com a cadeia do dia (mesma filtragem do atualizador), nos 11 papéis do app: 14.063 operações com vencimento até
04/11/2026 (trava de alta 2.221, trava de baixa 1.645, strangle 2.146, put vendida 2.793, call comprada 2.892, put
comprada 2.366). Execução no pior lado na entrada; taxas da B3; sem corretagem; no vencimento, o strike do último pregão
da série (ajustes da B3 por proventos: 5.397 operações). IC 95% por bootstrap em blocos mensais.

## 1. "Chance implícita no preço"

A conta da tela não tinha o juro (a volatilidade implícita é tirada com juro). Sem ele, a chance fica baixa nas
operações de alta e alta nas de baixa:

| estrutura | tela | com juro (11%) | terminou além do equilíbrio |
|---|---|---|---|
| Trava de alta | 37,0 | 42,0 | 44,6 |
| Trava de baixa | 43,3 | 38,1 | 37,1 |
| Strangle comprado | 31,9 | 32,4 | 37,3 |
| Put vendida coberta | 74,6 | 78,2 | 79,2 |
| Call comprada | 28,4 | 33,0 | 36,1 |
| Put comprada | 35,8 | 31,0 | 29,3 |

Por faixa, com o juro: 30–40% → 35,8% [34,2; 37,6]; 40–50% → 43,4% [40,7; 46,2]; 70–80% → 76,5%; 80–90% → 83,6%.
Sem o juro, a faixa 40–50% dava 38,0%. A sobra nas chances baixas (10–30%: 4 a 7 pontos) é o mercado do período
(movimentos maiores que o implícito); não deve ser "corrigida" (seria previsão). Lucro depois das taxas ≈ além do
equilíbrio (as taxas da B3 são pequenas).

## 2. Marcação diária e regra de saída

O app confere "Se encerrar hoje" e a regra de saída no pior lado do fechamento (vende pela melhor compra, recompra pela
melhor venda). Nas séries pouco negociadas a oferta do fim do dia fica longe do preço justo:

- 58% das travas de alta e 67% das de baixa tiveram algum dia com "Se encerrar hoje" pior que o risco máximo.
- Regra completa no pior lado: trava de alta com lucro em 13,8% e resultado médio −94,7% do risco (segurar: 44,4% e
  −12,8%); 82% saem no limite.

Cada parte da regra, conferida no preço médio (resultado médio em % do risco; saída no médio / no pior lado):

| estrutura | completa | sem limite (alvo + prazo) | sem alvo (limite + prazo) | só prazo | segurar |
|---|---|---|---|---|---|
| Trava de alta | −14,3 / −75,2 | +9,4 / −40,9 | −43,6 / −107,8 | −12,2 / −50,1 | −12,8 |
| Trava de baixa | −4,9 / −81,1 | +23,1 / −49,5 | −38,1 / −96,2 | −12,7 / −49,2 | −11,7 |
| Strangle comprado | +14,8 / +8,1 | +15,9 / +9,2 | +14,8 / +8,1 | +15,9 / +9,2 | +12,7 |
| Put vendida coberta | −0,2 / −0,6 | −0,3 / −0,7 | −0,2 / −0,7 | −0,3 / −0,7 | −0,4 |

- O **limite** (sair em −70% do risco) piora as travas em todas as hipóteses de execução: a trava já tem o risco
  fechado no prêmio, e o limite realiza a perda em dias de preço ruim.
- O **alvo** (50% do ganho máximo) depende de como se sai: no preço médio melhora; saindo no pior lado, piora. Sem
  conclusão até medir uma execução realista e conferir por período.
- Sair antes custa o spread de novo: na entrada o spread já custa 17% do risco da trava, em média.

## 3. Uma operação por vez (segurando até o vencimento)

Maior sequência de perdas seguidas, por papel: trava de alta 3 a 11; trava de baixa 2 a 12; strangle 4 a 10; call
comprada 3 a 10; put comprada 4 a 12; put vendida 1 a 3 (mas o risco dela é o caixa inteiro). Maior queda acumulada:
até 20× o risco de uma operação na trava de alta (MGLU3, USIM5) e 32× na trava de baixa (PETR4).

## Limitações

Observações sobrepostas; preço de fechamento (melhor oferta do fim do dia), não o do meio do pregão; sem corretagem;
se o código da série mudar no ajuste da B3, fica o strike da entrada; o resultado por período muda com o mercado
(2015–2020 de alta, 2021–2025 sem direção, 2026 de movimentos grandes).
