# F3-INT-118 — Relatorio candidato de auditoria

## Classificacao
CANDIDATA — nao FINAL.

Ultimo checkpoint FINAL: F3-INT-117 R2.
F3: OPEN.
Operacoes reais: BLOQUEADAS.

## Evidencias exploratorias reportadas

- SQLite journal_mode DELETE e synchronous FULL.
- Rejeicao de journal WAL incompativel.
- Digest divergente: STATE_ANCHOR_MISMATCH.
- Digest vazio, None ou invalido: INVALID_STATE_ANCHOR.
- Digest correto: STORE_FIXTURE_UNAUTHENTICATED.
- PRAGMA integrity_check: ok.
- PRAGMA foreign_key_check: lista vazia.
- Arquivo SQLite corrompido: STORE_ERROR.
- Arquivo corrompido preservado durante verificacao.
- Regressao F3-INT-115/116/117: 37 passed em 128.89s.

## Limitacoes

Os resultados acima foram reportados pelo operador e nao
constituem autenticacao independente das evidencias.

Os testes nao comprovam durabilidade apos falha fisica de
energia, atomicidade entre commit SQLite e atualizacao do
digest externo, nem protecao contra restauracao conjunta
do banco e da ancora externa.

Nao existe autorizacao para operacoes reais.

## Decisao

Consolidacao candidata para revisao.
Nenhuma promocao automatica para FINAL.
Checkpoint F3-INT-117 R2 deve permanecer preservado.