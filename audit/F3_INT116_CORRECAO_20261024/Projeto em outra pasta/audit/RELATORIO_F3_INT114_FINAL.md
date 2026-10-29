# F3-INT-114 FINAL — auditoria offline

Consolidado em 2026-10-23 a partir do pacote salvo em 2026-10-22.

- Regressão Windows: 1.388 testes, 1.387 aprovados, 1 ignorado, zero falhas e zero erros; 572,490 s.
- F3-INT-114: 18/18 testes novos aprovados no Windows e 18/18 anteriormente aprovados localmente.
- O único skip: `test_symlink_rejected` — Windows não permitiu criação do symlink.
- Saída original mantida byte a byte em `RESULTADO_F3_INT114_WINDOWS_20261022.txt`; SHA-256 registrado no checkpoint.
- Dois arquivos novos de implementação e testes preservados com SHA-256 igual ao checkpoint candidato.
- O código executado não foi atestado de forma independente, e não houve registro do exit code do PowerShell.
- Testes de concorrência e durabilidade são modelos; não são validação SQLite multiprocesso real nem resistência a falha física.
- Custódia independente e tratamento conclusivo de ACK perdido seguem pendentes.

F3 OPEN, simulação/offline, sete travas `false`, sem autorização para operações reais.

## Próxima etapa F3-INT-115

Priorizar evidências reais e limitadas de concorrência SQLite multiprocesso, retenção independente de referências e lacunas de identidade do executável. Não promover autoridade operacional.
