# Relatório F3-INT-31 — múltiplos tickets e gerações (somente simulação)

## Escopo
Ampliação dos testes adversariais de tickets de fechamento, mutações intercaladas, evidências J/L posteriores, conflitos e trocas de geração. Nenhum arquivo do modelo principal foi modificado; apenas um novo módulo de testes foi adicionado.

## Resultados
- Testes novos: **4/4 aprovados** (casos parametrizados: 8 + 12 + 6 + 6 = 32 cenários).
- Regressão integral: **239/239 aprovados**, **27,470 segundos**.
- Exploração herdada INT13: 180.000 transições, limite atingido, zero contraexemplos relatados.
- Arquivos de prova: `TESTES_F3_INT31_ESPECIFICOS.txt`, `REGRESSAO_F3_INT31.txt`.

## Observação sobre requalificação
O harness `eligible()` insere novas observações positivas J=EMPTY e L=RELEASED. Uma observação negativa anterior invalida o ticket antigo; uma qualificação posterior com evidência fresca pode gerar um ticket novo aceito, se todos os demais guardas forem satisfeitos. As primeiras expectativas dos testes foram corrigidas para refletir essa semântica documentada. Isso não comprova validade temporal ou independência de testemunhas reais.

## Limitações
Os testes exercitam um modelo Python simulado e não certificam atomicidade, persistência ou autenticação nativa. Explorações são limitadas e não constituem prova exaustiva. **F3=OPEN**. Permanecem false: `orders_allowed`, `live_certified`, `flow_complete`, `f3_resolved`, `native_prototype_authorized`, `strict_deadline_guaranteed`, `authenticated_witness_verified`.
