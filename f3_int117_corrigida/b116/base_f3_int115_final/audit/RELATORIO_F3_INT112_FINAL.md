# F3-INT-112 FINAL — aprovação offline com ressalva Windows

Base definitiva: F3-INT-111 FINAL, preservada. Candidato F3-INT-112 não teve código ou testes alterados durante a consolidação.

## Evidência

- Log Windows `RESULTADO_F3_INT112.txt`: `Ran 1357 tests in 757.715s` / `OK (skipped=1)`; 1.356 aprovados, 1 ignorado, zero falhas e erros.
- O único teste ignorado foi `test_symlink_rejected`, por `Symlink not permitted` no Windows.
- Os 12 testes novos foram executados localmente em Linux nesta consolidação: 12 aprovados, incluindo `test_symlink_rejected`. Esse resultado não substitui teste em Windows com permissões para symlink.
- Hashes dos dois arquivos novos de código/testes conferidos com o checkpoint candidato. Todos os 761 arquivos da F3-INT-111 FINAL estão presentes, byte a byte, no candidato F3-INT-112.
- O log não contém um atestado independente do hash do código realmente executado nem o código de saída do processo; por isso não prova a identidade entre execução Windows e ZIP.

## Limites e decisão

Checkpoint FINAL **somente da etapa de inventário offline**, com ressalva documentada para o skip Windows. O resultado MATCH_UNAUTHENTICATED não autentica proveniência. Inventário e arquivos podem ser trocados juntos; TOCTOU, referências externas, concorrência real multiprocesso, perda de ACK, atomicidade entre hosts e durabilidade física continuam pendentes. F3 permanece OPEN, sete locks `false`, sem operações reais.
