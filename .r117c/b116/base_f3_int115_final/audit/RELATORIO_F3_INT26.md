# F3-INT-26 — Auditoria de falhas combinadas (somente simulação)

Data: 2026-10-20. Base: PACOTE_AUDITORIA_F3_INT25_CHAT.zip.

## Escopo e alterações
- Criado `tests/test_f3_int26_combined_faults.py` com oito cenários combinados.
- Nenhum arquivo de modelo (`tools/*.py`) foi modificado.
- Sem integração operacional, chamadas nativas Windows, Profit, Excel, ordens ou protótipos.

## Cenários novos
1. Job NONEMPTY tardio invalida ticket de fechamento.
2. Falha de limpeza tardia invalida ticket e preserva falha.
3. Conflito de criação tardio combinado a nova geração impede fechamento.
4. Tentativa desconhecida combinada a Job NONEMPTY bloqueia.
5. Processo duplicado entre tentativas combinado a falha de limpeza bloqueia.
6. Descendente sem prova de saída e Job NONEMPTY bloqueiam.
7. Lease de geração antiga não consegue adicionar evidência.
8. Conflito material pós-fechamento abre contestação externa sem reabrir a sessão.

## Execução independente no ambiente isolado
- Novos testes: 8/8, zero falhas, 0.111 s.
- Regressão: 219/219, zero falhas, 20.323 s, código de saída 0.
- Explorações históricas executadas como parte da regressão: INT10 12.000 transições; INT13 180.000 transições, 80.651 estados; INT14 30.000 transições; INT15 4.692 transições e 207 pares fase-evento. Nenhum contraexemplo reportado por esses exploradores em seus limites.
- Explorações são limitadas, não prova exaustiva nem comprovação de segurança nativa.

## Limites e estado
- Os testes não exercem concorrência real, criptografia real, APIs Windows nem contenção nativa.
- F3=OPEN. Flags orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed e authenticated_witness_verified permanecem false.
- Próxima etapa proposta: F3-INT-27, explorar combinações geradas de forma sistemática e reduzir contraexemplos, ainda em simulação.
