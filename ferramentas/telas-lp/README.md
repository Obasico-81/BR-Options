# Telas e números das páginas (LPs)

Scripts usados para gerar as imagens de `lp/img/` e os valores dos avisos do hero. Rodam a partir da raiz do
repositório, com o app gerado (`python3 build.py && python3 build_pwa.py`) e o Playwright instalado.

Para as telas, sirva o app em `http://localhost:8765` antes:

```
cd pwa && python3 -m http.server 8765
```

| Script | O que gera |
|---|---|
| `telas-plataforma.js <pasta>` | `pc-montada` (hero, PETR4, perfil Ganho maior, limite R$ 2.000), `pc-inicio` (passo 1, VALE3), `pc-ordens` (passo 2, ITUB4) e `pc-cenarios` (passo 3, BBAS3), em PNG 1600×1000. Converter para WebP (qualidade 82) e copiar para `lp/img/`. |
| `celular-operacoes.js <pasta>` | `app-operacoes-n.png`: aba Operações ao vivo no celular (fonte simulada, `?aovivo=sim&semente=11`), com 4 operações reais e 1 simulada e o aviso de alvo. Reduzir para 780×1688, WebP qualidade 85 → `lp/img/cel-operacoes.webp`. |
| `avisos-hero.js` | Os números dos três avisos do hero, pelo motor do app (fechamento de 19/11/2026 em `pwa/snapshot.json`, vol implícita do fechamento, preço executável com taxas): PETR4 montada (22 lotes, risco R$ 1.936, ganho máximo R$ 3.014), VALE3 +3% no mesmo dia (+R$ 430) e ITUB4 +7% depois de 20 dias (+R$ 1.701, acima do alvo do app). |
| `imagem-compartilhar.js imagem-compartilhar.html <saída.png>` | `lp/img/compartilhar.png` (1200×630), a imagem do link no WhatsApp e nas redes. |

Os avisos e as telas usam cotações simuladas: as páginas dizem isso ao lado do celular ("Imagem ilustrativa, com
cotações simuladas.").
