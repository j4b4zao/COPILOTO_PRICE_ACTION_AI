# Correcoes F3-INT-52

A primeira execucao encontrou 1 falha entre 23 testes: o teste de elo novo
invalido esperava BASE_BROKEN_EPOCH_LINK, mas as camadas 49 e 50 preservam
BASE_BASE_BROKEN_EPOCH_LINK. A camada 52 propaga o resultado existente.
Corrigida a expectativa do teste, preservando a rejeicao e a identidade do estado.
O log inicial permanece em LOG_F3_INT52_NOVOS_PRIMEIRA_EXECUCAO.txt.
