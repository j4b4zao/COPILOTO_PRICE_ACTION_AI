# F3-INT-113 — escopo preliminar

Objetivo: aprofundar verificação de identidade e custódia do snapshot executado, com referências externas independentes e resultados conservadores.

1. Registrar manifestos de execução e hashes verificáveis antes/depois da regressão, sem atribuir autenticidade a hashes autogerados.
2. Criar testes offline de troca conjunta de código e manifesto, revogação, divergência e pin ausente.
3. Testar cenário de symlink no Windows com permissão, quando disponível, sem remover skip por artifício.
4. Priorizar concorrência real, ACK perdido e durabilidade como lacunas abertas; não prometer solução sem implementação/teste.
5. Preservar F3 OPEN, sete locks `false`, nenhuma integração com Profit, Excel, RTD, broker ou rede.
