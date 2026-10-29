# RELATÓRIO F3-INT-39

Escopo: simulação isolada de rotação de chaves, sem criptografia real, APIs nativas, acesso a Profit/Excel, ordens ou ambiente operacional.

## Resultado
- 12 novos testes adversariais: 12 aprovados.
- Regressão integral: 298/298 aprovados em 28,277 s.
- Modelo operacional e recuperação central: inalterados.
- Explorações limitadas legadas executadas na regressão, sem novos contraexemplos reportados; não são provas exaustivas.

## Cobertura
Ativação e substituição de chave; revogação e comprometimento durante rotação; evidência futura; sequência ou tempo fora de ordem; duplicação de sequência; reativação de chave aposentada; geração inferior ao piso; ausência de ativação; expiração.

## Limitações e riscos remanescentes
O simulador usa tempo, eventos e credenciais fornecidos como fixtures; não autentica assinaturas, não garante origem, atomicidade, relógio confiável, durabilidade ou concorrência entre processos. Não há integração nativa. Os resultados não autorizam recuperação operacional ou negociação.

F3=OPEN. Flags `orders_allowed`, `live_certified`, `flow_complete`, `f3_resolved`, `native_prototype_authorized`, `strict_deadline_guaranteed`, `authenticated_witness_verified` permanecem false.
