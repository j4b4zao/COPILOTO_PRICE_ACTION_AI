# F3-INT-109 — escopo preliminar, sem implementação

Base proposta: F3-INT-108 definitivo, F3=OPEN e sete bloqueios false.
Este documento não inicia a etapa nem autoriza uso operacional.

1. Persistência confiável: especificar um armazenamento offline para pins,
   pisos de revisão e consumo; separar estados preparados e confirmados;
   modelar interrupções antes/depois de cada gravação, recuperação e corrupção.
   Avaliar durabilidade real do backend escolhido; arquivo JSON e hash isolados
   não comprovam persistência confiável.
2. Restauração de estados antigos: demonstrar rollback conjunto de cadeia,
   pin, piso e histórico. Definir uma âncora independente do estado restaurável
   e explicitar o que acontece se essa âncora também puder ser restaurada.
   Contador local, versão ou hash dentro do mesmo backup não impedem rollback.
3. Consumo atômico: especificar transação que valide a referência esperada,
   rejeite consumo anterior, registre o consumo e avance o piso em uma unidade.
   Modelar dois consumidores, reinício, commit perdido, repetição e idempotência.
   Bloqueio apenas em memória ou check-then-write não garante exclusão durável.
4. Autenticação de origem: separar integridade de autenticidade. Definir ameaça,
   confiança na distribuição dos pins, identidade, gestão de chaves, revogação
   e verificação independente antes de avaliar qualquer mecanismo futuro.
   Hash, cadeia e assinatura autodeclarada não estabelecem origem confiável.

Critérios propostos: primeiro reproduzir falhas offline; depois criar testes
positivos/adversariais de reinício, crash, concorrência, rollback e corrupção;
preservar contratos 105–108; registrar limites do modelo e regressão completa.
Nenhuma persistência real, autenticação ou consumo atômico foi implementado
nesta consolidação. Sem Profit, Excel, RTD, DDE, corretora ou ordens.
F3 permanece OPEN. orders_allowed, live_certified, flow_complete, f3_resolved,
native_prototype_authorized, strict_deadline_guaranteed e
authenticated_witness_verified permanecem false.
