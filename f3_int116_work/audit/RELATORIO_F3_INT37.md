# Relatório F3-INT-37 — ataque coordenado à âncora

Escopo: simulação Python em memória, isolada. Nenhuma autenticação real, durabilidade, consenso, certificação nativa ou autorização de negociação.

## Alterações
- Novo `tools/f3_int37_coordinated_attack_simulator.py`: demonstra reescrita coordenada de registro e âncora com hash válido, valida referência fornecida sem alegar sua autenticação, enumera requisitos para uma futura fonte autenticada.
- Novo `tests/test_f3_int37_coordinated_anchor_attacks.py`: oito testes de ataque e de invariantes de não promoção.
- Núcleo de recuperação e módulos anteriores inalterados.

## Resultados
- Testes isolados: 8/8.
- Regressão completa: 276/276; 27.244 segundos; zero falhas.
- Explorações limitadas anteriores reexecutadas, incluindo INT13 180000 transições e INT14 30000 arestas; nenhum contraexemplo reportado dentro dos limites.

## Limitações e próximos passos
- O parâmetro `trusted_reference` é apenas uma hipótese de teste, não um certificado ou âncora autenticada.
- A igualdade entre âncora e registro não impede ataque coordenado, replay ou falsificação de emissor sem raiz de confiança independente.
- F3 permanece OPEN. Os sete bloqueios operacionais permanecem false.
- F3-INT-38: especificar e testar política fail-closed diante de expiração, revogação e comprometimento simulado de chave, sem criar autoridade nativa.
