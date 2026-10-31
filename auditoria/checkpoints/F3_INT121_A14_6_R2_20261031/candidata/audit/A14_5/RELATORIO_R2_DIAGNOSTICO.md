# F3-INT-121 A14.5-R2 — diagnóstico da corrida de encerramento

## Evidência de origem
Regressão A14.5 (modo normal): 180 testes, 1 falha na repetição 3 de near_simultaneous, 342.989s. A asserção anterior exigia que gate ou bridge permanecesse ativo depois de worker e supervisor terem sido encerrados. Essa exigência não é garantida pela topologia: gate/bridge podem terminar por conta própria quando o worker encerra e os pipes fecham. Não é prova de falha na limpeza externa.

## Alteração controlada
- A14.4 mantém a exigência estrita original (observational=False por padrão), preservando os 3 testes anteriores e suas garantias.
- A14.5 usa observational=True: classifica o estado real de cada handle após as terminações, sem presumir sobrevivência em toda repetição.
- Capturas de estado em quatro pontos (inicial, após pedido de terminação, antes da limpeza) e evidência de limpeza externa.
- O objetivo da A14.5-R2 é **repetibilidade de observação e limpeza**, não prova de sobrevivência em todas as ordenações. A contraprova estrita de sobrevivência permanece coberta por A13/A14.2 e A14.4.
- Não há alterações em código de produção, nem autorização de operações reais.

## Limitações e aceite
Esta candidata NÃO foi executada no Windows pelo assistente. Os novos testes classificatórios não podem ser interpretados como aprovação de detecção obrigatória de sobreviventes; somente como consistência da coleta e da limpeza. Para o aceite, executar testes específicos em ambos os modos, depois regressão integral. Se um teste estrito da A14.4 falhar intermitentemente, investigar separadamente, sem suprimi-lo.
