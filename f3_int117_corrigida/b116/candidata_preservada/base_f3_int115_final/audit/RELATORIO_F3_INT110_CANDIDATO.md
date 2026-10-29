# F3-INT-110 — candidato offline

Base definitiva: F3-INT-109, regressão histórica reportada no Windows 1322/1322.

## Lacuna reproduzível da etapa 109
`consume_chain` retorna `COMMIT_OUTCOME_UNKNOWN` quando a confirmação se perde depois do commit, sem oferecer consulta tipada do resultado. Tentar novamente com a âncora anterior é rejeitado por divergência; derivar uma âncora do banco observado não é uma reconciliação confiável.

## Escopo da implementação
Novo módulo isolado `tools/f3_int110_offline_reconciliation.py`: consulta observacional fail-closed usando digests anterior e posterior e digest da cadeia, **fornecidos por um contexto independente e confiável**. Compara estado SQLite canônico com os pins; informa `COMMITTED_OBSERVED_UNAUTHENTICATED`, `NOT_COMMITTED_OBSERVED_UNAUTHENTICATED` ou `RECONCILIATION_UNRESOLVED`. Nunca autoriza repetição automática nem operação real. Não altera os módulos 105–109.

## Limites explícitos
Não resolve restauração conjunta de banco e âncora; não implementa atomicidade distribuída, fencing, durabilidade física ou autenticação de origem. Os dois pins precisam existir independentemente antes da consulta: um pin posterior inventado com base no banco observado não oferece garantia. Uma confirmação observada não garante entrega ao chamador. A regressão integral de Windows permanece pendente.

## Validação local
11 testes novos aprovados (Linux), sem alteração dos testes anteriores. F3=OPEN e sete bloqueios permanecem false. Não atualizar ULTIMO_MARCO antes de regressão Windows.
