# Dias com operação disponível, por papel — 2025 a 05/11/2026

Rodado em 06/11/2026 (run 42198092012, `pesquisa/disponibilidade.py`), COTAHIST anuais de 2025 e 2026, cadeia do
atualizador e montador.py do app, nas quatro operações do Início.

- **liquidez**: alguma monta em algum vencimento, sem limite de risco nem de caixa
- **padrão**: alguma cabe no perfil de quem abre o app (risco R$ 500, capital R$ 12.000) no vencimento que o app escolhe (o mais perto de 45 dias)
- **qualquer**: alguma cabe no perfil padrão em algum vencimento (o usuário troca o vencimento)

## 2026 (211 pregões)

| papel | % liquidez | % padrão | % qualquer | maior sequência sem (liquidez) | maior sequência sem (padrão) | sequência atual sem (liquidez) |
|---|---|---|---|---|---|---|
| BOVA11 | 100% | 97% | 100% | 0 | 1 | 0 |
| PETR4 | 100% | 96% | 100% | 1 | 1 | 0 |
| VALE3 | 100% | 87% | 100% | 1 | 3 | 0 |
| BBAS3 | 100% | 94% | 99% | 0 | 2 | 0 |
| BBDC4 | 97% | 62% | 90% | 1 | 10 | 0 |
| ITUB4 | 94% | 49% | 83% | 1 | 15 | 0 |
| B3SA3 | 87% | 41% | 70% | 3 | 8 | 1 |
| MGLU3 | 86% | 57% | 83% | 4 | 8 | 0 |
| PRIO3 | 81% | 31% | 56% | 3 | 17 | 1 |
| WEGE3 | 75% | 31% | 54% | 8 | 31 | 0 |
| USIM5 | 69% | 28% | 48% | 9 | 28 | 2 |

2025 (250 pregões), % qualquer: BOVA11, PETR4, VALE3 100%; BBDC4 97%; BBAS3 97%; MGLU3 91%; ITUB4 75%; B3SA3 61%;
PRIO3 59%; WEGE3 55%; USIM5 44%.

Últimos 30 pregões (liquidez; █ monta, · não):

- USIM5 `·██·██████·█·███████████████··`
- B3SA3 `·██████████████████████·█████·`
- PRIO3 `█·███████·█████████████·██·██·`
- WEGE3 `████·█·█·██·███·████·█·███████`

## Leitura

- Nenhum papel está numa sequência longa sem liquidez: USIM5 está há 2 pregões, B3SA3 e PRIO3 há 1. Os vazios são
  intermitentes (dias isolados), não uma liquidez que acabou.
- No perfil padrão e no vencimento que o app escolhe, WEGE3, USIM5 e PRIO3 têm operação em cerca de 30% dos pregões,
  com até 28 a 31 pregões seguidos sem nenhuma. Trocando o vencimento, sobem para 48% a 56%.
- O corte usado para incluir papéis (montar em 60% ou mais dos pregões) contava a compra simples, que não está no
  Início. Aplicado só às quatro operações do Início e em qualquer vencimento, ficam abaixo de 60% em 2025 e 2026:
  USIM5 (44%, 48%), WEGE3 (55%, 54%) e PRIO3 (59%, 56%).
