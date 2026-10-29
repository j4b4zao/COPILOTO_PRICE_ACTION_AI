# F3-INT-115 FINAL — conclusão de regressão offline Windows

Data: 2026-10-23. Base: F3-INT-114 FINAL, preservada.

## Evidência fornecida
- Testes multiprocesso: 17/17 OK, 74.124 s.
- Regressão Windows: 1.421 testes executados, 1.420 aprovados, 1 ignorado, 0 falhas, 0 erros, 804.052 s.
- O teste de symlink foi ignorado por permissões do Windows.
- Logs originais incorporados sem alteração; hashes no checkpoint.
- A saída do PowerShell contém NativeCommandError de stderr; o unittest terminou em OK. O código de saída de Python não foi fornecido independentemente.

## Escopo da conclusão
Este FINAL é **somente um marco de regressão offline**, não certificação operacional. Os logs foram fornecidos pelo usuário e não contêm atestação autenticada que vincule a execução ao SHA-256 dos arquivos empacotados. Não se infere custódia independente, durabilidade física, segurança entre máquinas nem liberação de ordens. A causa da divergência PID launcher/worker continua em aberto, apesar de os testes verificarem membership no Job Object.

## Invariantes
F3=OPEN, sete flags de segurança=false; sem operações reais. F3-INT-114 FINAL permanece preservada em `audit/PRESERVADO_F3_INT115_PRE_FINAL_20261023/`.
