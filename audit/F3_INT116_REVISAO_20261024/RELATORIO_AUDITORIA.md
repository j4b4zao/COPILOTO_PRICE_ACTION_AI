# Auditoria tecnica F3-INT-116 CANDIDATA — 24/10/2026

Parecer: evidencias favoraveis no escopo offline ensaiado; revisao humana pendente. Sem promocao automatica. F3 OPEN, sete flags false, offline e simulation_only; certification false. ULTIMO_MARCO continua F3-INT-115 FINAL.

## Integridade e alteracoes

874/874 entradas do manifesto da base FINAL verificadas. Todos os 875 arquivos da arvore extraida foram preservados byte a byte antes e depois dos testes, na base e na candidata. Zero arquivos herdados modificados ou removidos. Manifesto da candidata: 12/12 entradas corretas; sidecar SHA-256 correto. Sao 14 adicoes, listadas em ALTERACOES.json; tres sao fontes: audit/tools/f3_int116_commit_recovery.py, audit/tools/f3_int116_run_audit.py e audit/tests/test_f3_int116_commit_recovery.py. As outras 11 sao relatorio, manifestos e evidencias.

## Testes reexecutados

- ESPECIFICOS: 8 testes, 8 aprovados, 0 skipped, 0 falhas, 0 erros; 29.496 s; exit code 0.
- REGRESSAO_COMPLETA: 1429 testes, 1428 aprovados, 1 skipped, 0 falhas, 0 erros; 591.498 s; exit code 0.

Sem enfraquecimento ou alteracao de testes. Supervisao Windows com Job Object e identidades de processo: cleanup confirmado nas duas execucoes, zero processos ativos no Job e zero threads de IPC remanescentes. Essa evidencia cobre os descendentes supervisionados, nao uma afirmacao sobre todos os processos do computador.

## Recuperacao, atomicidade e replay

Controle normal confirma gravacao. Erro antes do commit, recusa COMMIT pelo authorizer SQLite e SQLITE_BUSY real provocado por leitor mantiveram o estado anterior integral apos fechamento e reabertura. Erro apos commit retornou STORE_ERROR, mas a reconciliacao observou o estado novo integral. Ambos os estados passam PRAGMA integrity_check e comparacao integral do payload. Replay com ancora antiga: STATE_ANCHOR_MISMATCH; com ancora atual: STALE_CHAIN_REVISION, sem mudar o estado. Ancora after divergente: RECONCILIATION_UNRESOLVED. Banco ausente nao e recriado. Retry permanece false; sete flags false e F3 OPEN sao conferidos nos resultados exercitados.

## Achados e limitacoes

- Nenhuma falha funcional ou regressao detectada no escopo executado; nenhuma correcao foi aplicada a candidata.
- Runner usa assert para invariantes e aprovacao de execucao. python -O remove essas verificacoes. A execucao desta auditoria foi sem -O; recomenda-se substituir por verificacoes explicitas numa futura revisao, sem alterar a candidata auditada.
- Runner depende do caminho absoluto C:/COPILOTO_F3_INT115_FINAL e recusa sobrescrever EVIDENCIAS_F3_INT116. Reexecucao exige pasta nova ou harness separado; esta auditoria usou harness separado preservado no pacote.
- Patch de _connect e global no processo: uso apenas em testes isolados sem concorrencia de threads.
- As falhas controladas na fronteira da chamada nao demonstram morte dentro do motor SQLite. O caso de leitor demonstra erro real de commit, sem comprovar resistencia a perda de energia ou durabilidade fisica.
- STORE_ERROR nao determina sozinho se houve commit. Reconciliacao exige ancoras retidas previamente; nao autoriza retry. Restaurar banco e ancoras juntos pode derrotar deteccao de rollback.
- Hashes locais e ancoras do mesmo usuario nao constituem custodia autenticada, procedencia independente, entrega exatamente uma vez ou garantia entre computadores.
- Um teste de symlink permanece skipped por falta de permissao no Windows; nao foi contornado.
- A base disponivel e a arvore extraida: nenhum ZIP original FINAL foi fornecido para verificar sua origem/CRC/hash.

## Pacote

ZIP inclui toda a arvore f3_int116_work (889 arquivos), todas as novas evidencias desta revisao e os dois scripts desta auditoria. Nao inclui arquivos alheios da raiz do projeto. MANIFESTO_PACOTE.json fixa cada arquivo do payload; o ZIP e reaberto, testado por CRC e cada membro comparado por SHA-256. O hash do ZIP fica em sidecar externo, evitando autorreferencia.

Status: CANDIDATA; aguardar revisao antes de qualquer promocao para FINAL. Nenhuma operacao real autorizada.
