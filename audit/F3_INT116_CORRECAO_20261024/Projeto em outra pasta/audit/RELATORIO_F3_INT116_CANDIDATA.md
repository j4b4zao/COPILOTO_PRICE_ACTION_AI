# F3-INT-116 - candidata para revisao

Base exclusiva: C:/COPILOTO_F3_INT115_FINAL. Trabalho: C:/COPILOTO_PRICE_ACTION_AI/f3_int116_work/audit.
F3 OPEN; sete flags false; offline e simulation_only; certification false; nenhuma promocao FINAL.

## Integridade da base

874/874 arquivos do manifesto F3-INT-115 FINAL conferidos por SHA-256. ULTIMO_MARCO e CHECKPOINT_F3_INT115_FINAL identicos.
Todos os 875 arquivos encontrados na extracao foram copiados e verificados antes e depois, na origem e na copia. Nenhum arquivo herdado alterado.
Logs de aprovacao Windows conferidos com os hashes do checkpoint. Hashes locais nao autenticam a execucao nem constituem custodia independente.
O ZIP de distribuicao FINAL nao foi fornecido nesta pasta: CRC e SHA-256 do arquivo ZIP externo nao foram verificados. A verificacao cobre a arvore extraida e seu manifesto.

## Alteracoes

- tools/f3_int116_commit_recovery.py: sonda offline com erros antes/depois de commit e recusa de COMMIT pelo authorizer SQLite; sem alteracao do armazenamento herdado.
- tests/test_f3_int116_commit_recovery.py: oito testes de erro, controle sem falha, contencao real por leitor, reabertura, integrity_check, ancoras, replay e seguranca.
- tools/f3_int116_run_audit.py: verificacao da base, testes especificos antes da regressao, supervisao por Job Object, inventarios e manifesto; nunca promove.

## Resultados

- ESPECIFICOS: 8 testes; 8 aprovados; 0 skips; 0 falhas; 0 erros; exit code 0; 13.851 s. Limpeza confirmada; zero processos ativos e threads IPC remanescentes.
- REGRESSAO_COMPLETA: 1429 testes; 1428 aprovados; 1 skips; 0 falhas; 0 erros; exit code 0; 530.26 s. Limpeza confirmada; zero processos ativos e threads IPC remanescentes.

Skip: ["test_symlink_rejected (test_f3_int112_snapshot_inventory.InventoryTests.test_symlink_rejected) ... skipped 'Symlink not permitted'"]

Erro antes do commit, recusa pelo SQLite e SQLITE_BUSY real no commit deixaram o estado anterior integro apos fechamento e reabertura. Erro injetado apos commit deixou o estado novo integro, apesar do retorno STORE_ERROR; a reconciliacao observou o commit, sem autorizar retry.
Replay com ancora antiga: STATE_ANCHOR_MISMATCH. Replay com ancora atual: STALE_CHAIN_REVISION. Estado conferido novamente apos as rejeicoes. Ancora divergente: RECONCILIATION_UNRESOLVED. Banco ausente nao recriado.

## Limites

- Nao houve morte induzida dentro do motor SQLite. As falhas novas sao controladas na fronteira da chamada; o bloqueio por leitor produz erro real de commit.
- Nao comprova perda de energia, durabilidade fisica, custodia autenticada, entrega exatamente uma vez ou garantias entre computadores.
- Sonda usa patch local de processo e destina-se apenas a testes isolados sem concorrencia de threads.
- Um skip de symlink permanece por falta de permissao no Windows.
- Nenhuma operacao real autorizada; ULTIMO_MARCO continua F3-INT-115 FINAL.

## Evidencias e hashes

Execucao supervisionada: EVIDENCIAS_F3_INT116/RESULTADO.json, logs e respectivos execution.json. ANTES.json fixa os inventarios.
MANIFESTO_F3_INT116_CANDIDATA.json registra SHA-256 das adicoes, fontes e evidencias; seu proprio hash fica no sidecar para evitar autorreferencia.
ESPECIFICOS_F3_INT116.log registra a primeira execucao de desenvolvimento (8/8); a execucao supervisionada posterior usa a versao final das assercoes.
REVISAO PENDENTE. Nenhum checkpoint FINAL da etapa 116 foi criado.
