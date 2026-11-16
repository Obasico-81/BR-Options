# Regras de saída do app × segurar até o vencimento — resultado

Run 43979567501 (pesquisa/regras_saida.py, commit 9430d82). COTAHIST_A2015 a COTAHIST_A2026; 11.496 operações com regra
de saída (travas nos três perfis, strangle, put vendida) e vencimento até 13/11/2026. Regra conferida como o app confere
(preço médio do fechamento, nunca abaixo do risco máximo). Resultado em % do risco máximo, depois das taxas da B3.
Disparos sem pregão seguinte com preço antes do vencimento (ficam como segurar): prazo 809, alvo 90.
(O run 43978863637 saiu com a série da Selic incompleta — 4.152 operações, sem 2015–2020 — e foi descartado.)

## 1. Por que regra saiu

| operação | operações | alvo | limite | prazo | vencimento |
|---|---|---|---|---|---|
| Trava de alta · Lucro maior | 1400 | 43% | 0% | 40% | 17% |
| Trava de alta · Equilibrada | 1995 | 50% | 0% | 35% | 15% |
| Trava de alta · Lucro frequente | 780 | 69% | 0% | 24% | 8% |
| Trava de baixa · Lucro maior | 924 | 28% | 0% | 55% | 17% |
| Trava de baixa · Equilibrada | 1531 | 37% | 0% | 45% | 17% |
| Trava de baixa · Lucro frequente | 503 | 56% | 0% | 35% | 9% |
| Strangle comprado | 1951 | 0% | 0% | 64% | 36% |
| Put vendida coberta | 2412 | 82% | 0% | 14% | 4% |

## 2. Seguindo as regras: com lucro e resultado médio

| operação | com lucro: pior lado / médio / pregão seguinte | segurar: com lucro | resultado médio: pior lado / médio / pregão seguinte | segurar |
|---|---|---|---|---|
| Trava de alta · Lucro maior | 37% / 50% / 44% | 40% | -27.3% / +13.1% / -0.4% | -2.2% |
| Trava de alta · Equilibrada | 33% / 56% / 45% | 45% | -37.9% / +7.8% / -12.2% | -12.0% |
| Trava de alta · Lucro frequente | 21% / 74% / 48% | 59% | -37.3% / +12.0% / -9.3% | -14.5% |
| Trava de baixa · Lucro maior | 23% / 37% / 30% | 29% | -47.7% / +1.5% / -19.1% | -12.1% |
| Trava de baixa · Equilibrada | 26% / 47% / 37% | 37% | -48.2% / +21.4% / -16.0% | -11.3% |
| Trava de baixa · Lucro frequente | 25% / 63% / 45% | 50% | -45.7% / +5.5% / -18.0% | -17.7% |
| Strangle comprado | 34% / 36% / 37% | 38% | +12.7% / +19.1% / +18.1% | +16.3% |
| Put vendida coberta | 84% / 85% / 84% | 79% | -0.7% / -0.3% / -0.5% | -0.5% |

## 3. Diferença por operação: regra (preço médio do pregão seguinte) − segurar

| operação | diferença média | IC 95% | 2015–2020 | 2021–2026 | H3 |
|---|---|---|---|---|---|
| Trava de alta · Lucro maior | +1.8% | [-5.1%; +9.1%] | +5.3% | +0.4% | não passa |
| Trava de alta · Equilibrada | -0.1% | [-5.5%; +5.2%] | -4.3% | +1.6% | não passa |
| Trava de alta · Lucro frequente | +5.2% | [-0.3%; +10.7%] | -0.9% | +7.5% | não passa |
| Trava de baixa · Lucro maior | -7.0% | [-16.8%; +2.7%] | +4.1% | -9.3% | não passa |
| Trava de baixa · Equilibrada | -4.7% | [-11.0%; +1.6%] | -4.6% | -4.8% | não passa |
| Trava de baixa · Lucro frequente | -0.4% | [-7.4%; +6.4%] | -9.9% | +0.7% | não passa |
| Strangle comprado | +1.8% | [-0.7%; +4.3%] | +1.7% | +1.8% | não passa |
| Put vendida coberta | +0.1% | [-0.3%; +0.4%] | +0.1% | +0.0% | não passa |

## Leitura

- Seguir as regras do app não muda o resultado médio em relação a segurar até o vencimento, em nenhuma operação
  (todos os IC incluem zero). Confirma o replay de 05/11 (seção 2a do RESULTADO_REPLAY.md) com os perfis e a Selic do dia.
- O preço médio do fechamento do disparo (como o app marca "Se encerrar hoje" e o Desempenho) dá resultado bem melhor
  que o realista: na trava de alta Lucro frequente, 74% com lucro e +12,0% no médio × 48% e −9,3% saindo no pregão
  seguinte. O Desempenho do app tende a mostrar as operações simuladas melhores do que seriam na corretora.
