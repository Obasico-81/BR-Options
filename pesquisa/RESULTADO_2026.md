# Reteste fora da amostra com 2026 — perfis por delta e gregas

Refeito em 03/11/2026 (run 41705971426) com a base corrigida; a primeira rodada (02/11/2026, run 41517843105)
misturava opções de outro papel com o mesmo prefixo. `pesquisa_perfis.py` e `pesquisa_gregas.py` rodaram
**sem mudar hipóteses, filtros nem cortes**; nenhuma variação nova foi testada. Base: COTAHIST anuais 2015–2026
da B3 (`montar_base.py`), seis papéis (BOVA11, PETR4, VALE3, BBAS3, BBDC4, ITUB4); entradas a cada 3 dias,
compra de call/put de 30–60 dias no preço de venda, spread ≤ 10%, quantidade ≥ 1.000, custos B3 0,134% + R$ 2
por ordem, resultado no vencimento. IC 95% por bootstrap em blocos mensais.

## 0. A correção de 03/11/2026

O prefixo de 4 letras do código da opção não identifica o papel-objeto: PETR traz opções de PETR3 e PETR4,
BBDC de BBDC3 e BBDC4, ITUB de ITUB3 e ITUB4, e VALE trazia as da VALE5 (preferencial, convertida em VALE3 em
2017). `montar_base.py` passou a aceitar só a opção cujo CODISI é o ISIN do papel da pesquisa. Linhas
descartadas (antes dos filtros de liquidez): PETR 89.812, VALE 91.964, BBDC 78.520, ITUB 4.847, BOVA 0, BBAS 0.
**As conclusões não mudam** (seção 3); os números abaixo são os da base corrigida, com a rodada anterior ao lado
onde mudou.

## 1. A linha de base reproduz o sandbox?

Nas conclusões, sim; o número registrado no handoff (−24 pp) era reproduzido pela base misturada (−22,3) e
na base corrigida fica em −14,2. O handoff não diz como o sandbox separava os papéis.

| Medida | Sandbox (handoff) | Base corrigida (antes: misturada) |
|---|---|---|
| Movimento necessário / esperado, diferença terço alto − baixo | −24 pp, IC [−55, +7] | −14,2 pp, IC [−46,0, +17,4] (antes −22,3 [−53,2, +11,0]) |
| Mesmo sinal nos dois períodos? | sim | **não mais**: +0,7 em 2015-20; −18,4 em 2021-25 (antes −26,7 e −18,9) |
| Theta, vega, gama | sem sinal confiável | ICs incluem zero; sinal muda entre períodos |
| IV / vol. realizada 60d | sem sinal confiável | IC inclui zero; mesmo sinal nos dois períodos (+11,1 e +16,5) |
| Perfis por delta | nenhum com retorno melhor | todos os ICs incluem zero (tabela abaixo) |

Perfis, entradas 2015–2025 (retorno sobre o prêmio, %):

| faixa de delta | n | acerto % | retorno médio | IC 95% | antes (misturada) |
|---|---|---|---|---|---|
| 0–0,15 | 1.821 | 7,3 | −16,5 | [−63,7, 53,1] | −15,4 |
| 0,15–0,25 | 3.237 | 15,8 | −19,5 | [−39,7, 4,8] | −15,4 |
| 0,25–0,35 | 3.548 | 24,2 | 2,4 | [−14,7, 21,1] | 6,4 |
| 0,35–0,50 | 5.235 | 31,9 | 2,6 | [−9,4, 16,4] | 5,4 |
| 0,50–0,65 | 3.584 | 37,4 | 0,4 | [−13,6, 15,3] | 3,2 |
| 0,65–0,80 | 1.790 | 41,4 | −4,5 | [−15,6, 7,0] | −3,6 |
| 0,80–1,00 | 1.490 | 40,9 | −6,0 | [−14,2, 3,2] | −1,4 |

Por período, o sinal se inverte em 6 das 7 faixas (2015-20 positivo, 2021-25 negativo; a faixa 0,15–0,25 é
negativa nos dois): o resultado acompanha a direção do mercado, não o perfil.

## 2. Fora da amostra: entradas em 2026 (1.643 operações, 9 meses)

Perfis (praticamente iguais à rodada anterior):

| faixa de delta | n | acerto % | retorno médio | IC 95% |
|---|---|---|---|---|
| 0–0,15 | 156 | 10,3 | −27,7 | [−76,1, 19,7] |
| 0,15–0,25 | 243 | 27,2 | 75,0 | [−25,1, 215,7] |
| 0,25–0,35 | 253 | 27,7 | 35,9 | [−20,1, 87,4] |
| 0,35–0,50 | 421 | 34,9 | 44,9 | [−12,8, 109,1] |
| 0,50–0,65 | 286 | 53,1 | 85,5 | [−2,9, 183,1] |
| 0,65–0,80 | 123 | 56,1 | 52,3 | [−12,5, 122,7] |
| 0,80–1,00 | 161 | 57,8 | 24,6 | [−10,8, 55,0] |

Gregas (diferença de retorno entre o terço alto e o baixo do sinal, mesmos cortes walk-forward):

| sinal | 2015–2025 | 2026 | IC 95% 2026 |
|---|---|---|---|
| theta / prêmio | −11,0 | +24,2 | [−113,5, 178,2] |
| vega / prêmio | +8,3 | +24,9 | [−67,3, 125,0] |
| gama relativo | +12,1 | +18,9 | [−77,1, 118,8] |
| movimento necessário / esperado | −14,2 | **+24,5** | [−161,4, 201,3] |
| IV / vol. realizada 60d | +7,8 | +16,1 | [−85,1, 99,0] |

## 3. Conclusão

- **Nenhuma hipótese se confirmou fora da amostra.** Todos os intervalos de 2026 incluem zero, e todos os da
  linha de base também.
- Em 2026 a compra de opções deu retorno médio positivo em quase todas as faixas, calls e puts. É o retrato de
  um ano de movimentos grandes (alta forte até outubro e queda de cerca de 14% em 26/10, depois do 2º turno): a
  volatilidade realizada ficou acima da implícita. Em 2021–2025 foi o oposto. Isso é regime de mercado, não
  vantagem do perfil; não serve de base para nenhuma afirmação no app.
- O movimento necessário / esperado ficou mais fraco com a base corrigida: perdeu o mesmo lado nos dois períodos
  da linha de base e trocou de lado em 2026. Continua só como informação na tela, sem veredito.
- IV / vol. realizada teve o mesmo lado (positivo) em 2015-20, 2021-25 e 2026, mas com intervalos que incluem
  zero nos três: não confirma nada e não foi testado como hipótese nova.
- Vale a regra de negócio do handoff: o app é régua, não vantagem.

## 4. Limitações

- 2026 tem só 9 meses de entradas com vencimento já ocorrido; com blocos mensais, o bootstrap tem 9 blocos e os
  intervalos são muito largos.
- As observações se sobrepõem (entradas a cada 3 dias, prazos de 30–60 dias).
- A base vem do COTAHIST, não do CSV do rb3; a comparação com o sandbox é por conclusão e pelo único número
  registrado (o handoff não registrou os n do sandbox).
- Juro fixo de 10% a.a. no Black-Scholes, como no sandbox; sem dividendos.
- 12 comparações (7 faixas + 5 sinais) sem correção para múltiplas comparações; nenhuma passa nem sem correção.
