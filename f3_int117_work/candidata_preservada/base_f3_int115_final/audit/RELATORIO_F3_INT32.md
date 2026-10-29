# Relatório F3-INT-32 — workers simulados e registro compartilhado

## Resultado
- 5 testes novos aprovados; regressão completa: **244/244**, 0 falhas, 28,152 s (unittest).
- Código do modelo de recuperação inalterado.
- 16 escalonamentos determinísticos de 4 tentativas de fechamento, com dois objetos Recovery apontando ao **mesmo** Store: apenas o primeiro fechamento vence.
- Reinício representado pela reconstrução do objeto Recovery com a mesma instância Store e FixtureVerifier.
- Rotação de geração por outro worker invalida tickets anteriores.
- Novos fatos negativos de Job/limpeza e conflito invalidam tickets antigos.
- Cópia profunda do Store **não** representa autoridade compartilhada. Não existe prova de exclusão entre instâncias independentes.

## Limites e segurança
Simulação Python em memória; sem threads reais, processos, disco, atomicidade nativa, persistência ou consenso distribuído. A exclusão observada decorre de um dicionário compartilhado no mesmo processo. Os resultados não certificam reinício de workers reais. F3=OPEN; sete flags operacionais false; nenhuma ordem ou execução real autorizada.

## Próximo passo sugerido
F3-INT-33: modelar explicitamente perda de persistência, dois registros independentes e falha de publicação, sempre como contraexemplos de *limites* do simulador, sem alegar solução nativa.
