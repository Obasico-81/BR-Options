# Reteste fora da amostra com 2026 — perfis por delta e gregas

Rodado em 02/11/2026 pelo workflow *Pesquisa fora da amostra (2026)* (run 41517843105), com
`pesquisa_perfis.py` e `pesquisa_gregas.py` **sem mudar hipóteses, filtros nem cortes**. Nenhuma
variação nova foi testada. Base: COTAHIST anuais 2015–2026 da B3 (`montar_base.py`), seis papéis
(BOVA11, PETR4, VALE3, BBAS3, BBDC4, ITUB4); entradas a cada 3 dias, compra de call/put de 30–60 dias
no preço de venda, spread ≤ 10%, quantidade ≥ 1.000, custos B3 0,134% + R$ 2 por ordem, resultado
no vencimento. IC 95% por bootstrap em blocos mensais.

## 1. A linha de base reproduz o sandbox?

Sim, nas conclusões e no único número registrado no handoff:

| Medida | Sandbox (handoff) | Agora (base do COTAHIST) |
|---|---|---|
| Movimento necessário / esperado, diferença terço alto − baixo | −24 pp, IC [−55, +7] | −22,3 pp, IC [−53,2, +11,0] |
| Mesmo sinal nos dois períodos? | sim | sim (−26,7 em 2015-20; −18,9 em 2021-25) |
| Theta, vega, gama, IV/RV | sem sinal confiável | ICs incluem zero; sinal muda entre períodos |
| Perfis por delta | nenhum com retorno melhor | todos os ICs incluem zero (tabela abaixo) |

Perfis, entradas 2015–2025 (retorno sobre o prêmio, %):

| faixa de delta | n | acerto % | retorno médio | IC 95% |
|---|---|---|---|---|
| 0–0,15 | 1.867 | 7,3 | −15,4 | [−61,1, 52,4] |
| 0,15–0,25 | 3.371 | 15,7 | −15,4 | [−35,8, 7,5] |
| 0,25–0,35 | 3.635 | 24,4 | 6,4 | [−10,7, 25,9] |
| 0,35–0,50 | 5.327 | 31,8 | 5,4 | [−6,9, 19,4] |
| 0,50–0,65 | 3.647 | 37,4 | 3,2 | [−11,3, 18,8] |
| 0,65–0,80 | 1.813 | 41,3 | −3,6 | [−14,4, 7,6] |
| 0,80–1,00 | 1.503 | 41,1 | −1,4 | [−11,4, 10,2] |

Por período o sinal se inverte em todas as faixas (2015-20 positivo, 2021-25 negativo): o resultado
acompanha a direção do mercado, não o perfil.

## 2. Fora da amostra: entradas em 2026 (1.647 operações, 9 meses)

Perfis:

| faixa de delta | n | acerto % | retorno médio | IC 95% |
|---|---|---|---|---|
| 0–0,15 | 156 | 10,3 | −27,7 | [−81,0, 21,1] |
| 0,15–0,25 | 243 | 27,2 | 75,0 | [−26,0, 207,1] |
| 0,25–0,35 | 255 | 27,5 | 34,8 | [−18,7, 84,4] |
| 0,35–0,50 | 423 | 35,0 | 44,5 | [−15,2, 109,3] |
| 0,50–0,65 | 286 | 53,1 | 85,5 | [−3,3, 183,7] |
| 0,65–0,80 | 123 | 56,1 | 52,3 | [−12,6, 122,7] |
| 0,80–1,00 | 161 | 57,8 | 24,6 | [−11,6, 55,6] |

Gregas (diferença de retorno entre o terço alto e o baixo do sinal, mesmos cortes walk-forward):

| sinal | 2015–2025 | 2026 | IC 95% 2026 |
|---|---|---|---|
| theta / prêmio | −3,5 | +24,3 | [−116,6, 180,5] |
| vega / prêmio | +16,3 | +25,7 | [−69,5, 128,0] |
| gama relativo | +20,6 | +21,6 | [−68,9, 116,6] |
| movimento necessário / esperado | −22,3 | **+26,7** | [−156,3, 208,5] |
| IV / vol. realizada 60d | −4,0 | +10,2 | [−120,4, 101,0] |

## 3. Conclusão

- **Nenhuma hipótese se confirmou fora da amostra.** Todos os intervalos de 2026 incluem zero.
- Em 2026 a compra de opções deu retorno médio positivo em quase todas as faixas, calls e puts. É o
  retrato de um ano de movimentos grandes (alta forte até outubro e queda de cerca de 14% em 26/10,
  depois do 2º turno): a volatilidade realizada ficou acima da implícita. Em 2021–2025 foi o oposto.
  Isso é regime de mercado, não vantagem do perfil; não serve de base para nenhuma afirmação no app.
- O único sinal que tinha o mesmo lado nos dois períodos da linha de base (movimento necessário /
  esperado) **trocou de lado** em 2026. Continua só como informação na tela, sem veredito.
- Vale a regra de negócio do handoff: o app é régua, não vantagem.

## 4. Limitações

- 2026 tem só 9 meses de entradas com vencimento já ocorrido; com blocos mensais, o bootstrap tem
  9 blocos e os intervalos são muito largos.
- As observações se sobrepõem (entradas a cada 3 dias, prazos de 30–60 dias).
- A base vem do COTAHIST, não do CSV do rb3; a reprodução da linha de base é por conclusão e pelo
  número registrado, não linha a linha (o handoff não registrou os n do sandbox).
- Juro fixo de 10% a.a. no Black-Scholes, como no sandbox; sem dividendos.
- 12 comparações (7 faixas + 5 sinais) sem correção para múltiplas comparações; nenhuma passa nem
  sem correção.
