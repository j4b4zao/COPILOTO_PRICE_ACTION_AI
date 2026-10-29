# Relatório F3-INT-33 — limites de isolamento

Escopo: modelo de recuperação exclusivamente simulado. Nenhuma API nativa, disco persistente, worker real ou operação de negociação.

## Execução
- 4/4 testes novos passaram.
- Regressão: 248/248 em 30.002 segundos, sem falhas.
- Modelo principal: inalterado.
- Explorações legadas: INT13 encerrou por limite de 180000 transições sem contraexemplos; INT14 por limite de 30000 arestas, sem violações. Não são provas exaustivas.

## Resultados
- Cópia profunda de Store tem gate independente e não compartilha autoridade.
- Rotação de geração em cópia não propaga para Store original.
- Fechamento em Store original não propaga para cópia.
- Dois workers sobre a mesma Store serializam a aceitação duplicada no modelo.

## Limites e riscos
As cópias independentes podem divergir; isto demonstra ausência de coordenação, não um protocolo de consenso. Não foram testados fsync, crash/restart real, persistência, multi-processo, comunicação ou falhas de rede. Nenhum resultado certifica execução nativa.

F3=OPEN. orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false.

Próximo: F3-INT-34 — especificar barreiras para autoridade única persistente e simular falhas de gravação, sem implementação operacional.
