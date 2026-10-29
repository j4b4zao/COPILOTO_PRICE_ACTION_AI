# Correcoes F3-INT-51

A primeira execucao encontrou 1 falha entre 25 testes: o resultado de particao
recebia o prefixo BASE_ duas vezes ao atravessar as camadas 49, 50 e 51.
A camada 51 agora preserva o prefixo existente. A rejeicao continuava conservadora;
nenhum bloqueio operacional foi alterado. O log original foi preservado em
LOG_F3_INT51_NOVOS_PRIMEIRA_EXECUCAO.txt. Os logs finais registram a reexecucao.
