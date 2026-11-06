# Testes de previsão — volatilidade, direção e caudas, 2015–2026

Rodado em 06/11/2026 (run 42157065960, `pesquisa/previsao.py`) com os COTAHIST anuais da B3 de 2015 a 05/11/2026, nos
11 papéis do app (B3SA3 a partir de 03/2018, PRIO3 de 06/2015). Hipóteses, modelos e parâmetros fixados antes de rodar.
IC 95% por bootstrap em blocos mensais. Desdobramentos e grupamentos ajustados nos testes 1 e 2 (os mesmos do teste da
tendência); proventos não. Cadeia de opções a cada 5 pregões (588 dias).

## 1. Volatilidade dos 20 pregões seguintes (4.900 dias×papel, 2016–2026)

| previsão | QLIKE (menor é melhor) | diferença × implícita [IC 95%] | erro (pp de vol. anual) | viés | faixa ±1σ (esperado 68,3%) | faixa ±2σ (esperado 95,4%) |
|---|---|---|---|---|---|---|
| implícita (a do app) | 0,407 | — | 9,6 | +4% | 66,1% | 92,1% |
| últimos 20 pregões | 0,439 | +0,033 [−0,045, +0,100] | 11,8 | +1% | 64,4% | 90,9% |
| últimos 60 pregões | 0,449 | +0,043 [+0,004, +0,088] | 12,0 | +7% | 67,9% | 92,8% |
| EWMA (0,94) | 0,405 | −0,002 [−0,064, +0,053] | 11,5 | +5% | 66,7% | 92,1% |
| HAR (máxima/mínima) | 0,310 | −0,096 [−0,215, −0,014] | 11,3 | +22% | 73,3% | 95,6% |
| implícita × HAR | 0,316 | −0,091 [−0,159, −0,041] | 9,7 | +12% | 69,3% | 94,3% |

Por período (diferença de QLIKE da implícita × HAR contra a implícita): 2016–2020 −0,211 [−0,404, −0,088];
2021–2025 −0,025 [−0,046, −0,009]; 2026 −0,009 [−0,045, +0,040]. Em 2026 todas as previsões ficaram estreitas (faixa
±1σ da implícita: 57,7%).

- A implícita do app é a melhor previsão isolada em erro (9,6 pp) e quase sem viés. A faixa do gráfico de payoff
  acerta 66% (esperado 68%) e 92% (esperado 95%): um pouco estreita, principalmente nos movimentos grandes.
- Combinar a implícita com o HAR erra menos pela QLIKE (que pune mais prever oscilação baixa demais) e deixa a faixa
  mais perto do esperado (69% e 94%). O ganho vem quase todo de 2016–2020 (a queda de 2020); em 2021–2025 é pequeno,
  e em 2026 não aparece.
- Os históricos simples (20, 60 pregões, EWMA) não ganham da implícita.

## 2. Direção em 5 e 20 pregões (26.224 dias×papel testados, 2017–2026; 18 variáveis)

| modelo | prazo | acerto | "mais comum" (repetir a direção mais frequente no treino) | diferença [IC 95%] | AUC (0,5 = moeda) [IC 95%] |
|---|---|---|---|---|---|
| gradient boosting | 5 pregões | 50,6% | 52,8% | −2,2 pp [−4,4, −0,2] | 0,498 [0,482, 0,517] |
| regressão logística | 5 pregões | 51,9% | 52,8% | −0,8 pp [−2,0, +0,4] | 0,513 [0,494, 0,530] |
| gradient boosting | 20 pregões | 51,9% | 53,9% | −2,0 pp [−5,3, +1,2] | 0,521 [0,495, 0,547] |
| regressão logística | 20 pregões | 53,0% | 53,9% | −0,9 pp [−3,6, +1,8] | 0,537 [0,508, 0,566] |

- Nenhum modelo acerta mais que repetir "alta" todo dia; o gradient boosting acerta menos.
- A única AUC acima de 0,5 com IC que não inclui 0,5 (logística, 20 pregões, 0,537) vem de 2017–2020 (0,569) e
  some depois: 0,500 em 2021–2025 e 0,447 em 2026. Com 16 comparações, um resultado assim é esperado por acaso.
- Retorno médio nos dias "alta" menos nos dias "queda": nenhum IC exclui zero no período todo.

## 3. Caudas: chance de terminar além do strike, opções fora do dinheiro (201.128 opções×dia, 2016–2026)

Distância em desvios: |ln(K/S)| ÷ (implícita do dinheiro × √prazo).

| lado | distância | real [IC 95%] | app | caudas históricas |
|---|---|---|---|---|
| abaixo (put) | 0–0,5 | 36,6% [32,5, 41,0] | 38,2% | 32,2% |
| abaixo (put) | 0,5–1 | 20,8% [17,7, 24,2] | 21,6% | 14,9% |
| abaixo (put) | 1–1,5 | 10,8% [8,5, 13,1] | 10,0% | 6,4% |
| abaixo (put) | 1,5–2 | 4,7% [3,5, 6,2] | 3,8% | 2,7% |
| abaixo (put) | 2–3 | 1,8% [1,2, 2,8] | 0,8% | 1,2% |
| acima (call) | 0–0,5 | 44,9% [40,6, 49,2] | 41,7% | 41,1% |
| acima (call) | 0,5–1 | 28,1% [24,6, 31,7] | 24,5% | 19,1% |
| acima (call) | 1–1,5 | 14,4% [11,9, 17,4] | 12,0% | 7,5% |
| acima (call) | 1,5–2 | 6,5% [4,8, 8,5] | 4,8% | 2,7% |
| acima (call) | 2–3 | 1,8% [1,1, 2,8] | 1,2% | 0,8% |

Brier (todas): app 0,1380; caudas históricas 0,1410 (+0,0030 [+0,0021, +0,0040], pior). Na amostra com spread de até
50% (103.678), o sorriso (implícita da própria opção) empata com o app (+0,0001 [−0,0006, +0,0008]) e exagera as quedas
fortes: 9,8% previsto contra 4,7% real a 1,5–2 desvios, 5,8% contra 1,8% a 2–3.

- A chance do app (lognormal com a implícita do dinheiro) é a melhor das três. Perto do dinheiro, do lado da queda,
  está calibrada.
- Longe do dinheiro, na queda (2–3 desvios), o real foi o dobro do app (1,8% contra 0,8%), em números pequenos.
- Do lado da alta, o app ficou 2 a 4 pp abaixo do real em todas as distâncias. Isso é a alta das ações no período
  (a chance do app usa a deriva do juro, não a do mercado); como o teste 2 mostra que a direção não se prevê, não é
  algo para corrigir.
- O modelo de caudas históricas, como especificado, falhou: padronizar pela volatilidade passada e escalar pela
  implícita achata o miolo da distribuição e subestima as chances de 0,5 a 2 desvios.

## Conclusão

- **Direção: fechada.** Aprendizado de máquina com 18 variáveis de preço, volume e mercado não acerta mais que
  repetir "alta". Não há base para prever preço com estes dados.
- **Volatilidade: dá para melhorar pouco.** A implícita do app já é a melhor previsão isolada; a combinação com o HAR
  deixa a faixa do payoff mais perto do esperado (+3 pp a ±1σ, +2 pp a ±2σ), com o ganho concentrado em 2016–2020.
- **Chance: fica como está.** É a melhor das três; o desvio conhecido é a queda muito forte, que acontece cerca de
  duas vezes mais que o calculado (1,8% contra 0,8%).

## Limitações

- Janelas sobrepostas; o IC por meses cobre a dependência entre dias próximos.
- Proventos não ajustados nos testes 1 e 2 (a queda do dia ex entra na volatilidade e no retorno de todas as previsões).
- No teste 3, as opções de cada dia entram com peso igual (papéis com mais strikes pesam mais); a chance do sorriso usa
  N(d2) com a implícita da própria opção (aproximação).
- Muitas comparações sem correção para múltiplas comparações.
