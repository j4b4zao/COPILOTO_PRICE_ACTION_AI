# F3-INT-121 A14.4 — Escopo técnico proposto

Investigar ordem de encerramento inesperada de supervisor e descendentes no Windows Job Object isolado.

Cenários previstos: (1) supervisor primeiro, (2) descendente primeiro, (3) encerramento quase simultâneo. Exigir referências de processo fixadas, observações de sinalização, detecção de sobreviventes, limpeza externa em finally e ausência de operações reais.

Não confundir encerramento de um processo com prova de encerramento de toda a árvore; validar todos os handles fixados. Não alterar produção, não abrir conexões Profit/RTD/DDE e não liberar F3.

Este documento apenas define escopo; os testes A14.4 ainda não foram implementados.
