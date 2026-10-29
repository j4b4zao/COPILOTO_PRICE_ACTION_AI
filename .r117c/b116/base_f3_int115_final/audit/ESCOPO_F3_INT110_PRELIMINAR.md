# F3-INT-110 — escopo preliminar, sem implementação

Base proposta: F3-INT-109 definitivo. F3=OPEN; sete bloqueios false.
Este escopo não inicia a implementação nem autoriza uso operacional.

1. Restauração conjunta de banco e âncora: reproduzir o replay já permitido
   quando ambos voltam ao passado. Especificar fronteira de confiança e âncora
   independente não restaurável junto do banco. Contador, hash ou cópia no mesmo
   backup não são proteção antirrollback. Se a independência não for assegurada,
   declarar o caso indetectável; não simular uma garantia real inexistente.
2. Reconciliação após confirmação perdida: modelar estados preparado,
   confirmado e desconhecido, consulta de resultado e identificação idempotente.
   Cobrir commit seguido de morte do processo e falha de retenção da âncora.
   Não aceitar recomputação da âncora a partir de estado não confiável como prova.
   Reconciliar sem duplicar consumo, reduzir piso ou esvaziar histórico.
3. Limites do consumo atômico: separar transação no mesmo SQLite de cópias do
   banco, múltiplos processos, hosts e estados externos. Avaliar contenção,
   repetição, pontos de falha e eventuais requisitos de fencing independente.
   Não alegar exatamente uma entrega ao chamador a partir de commit local.
4. Durabilidade: distinguir recuperação após morte de processo de falha de
   energia, disco, controladora e filesystem. Definir evidências necessárias
   e limites dos modelos offline; FULL/DELETE solicitado não comprova hardware.
5. Autenticação de origem: especificar identidade, distribuição confiável de
   pins, gestão de chaves e revogação antes de avaliar mecanismos. Hashes,
   âncoras locais e assinaturas autodeclaradas não autenticam uma origem confiável.

Critérios propostos: contraexemplos reproduzíveis antes de alterações; correções
isoladas justificadas; testes positivos e adversariais de reinício, rollback,
reconciliação e concorrência; compatibilidade com 105–109; regressão integral.
Não alterar checkpoints definitivos durante exploração. Não implementar nesta
consolidação. Sem rede operacional, Profit, Excel, RTD, DDE, corretora ou ordens.
orders_allowed, live_certified, flow_complete, f3_resolved,
native_prototype_authorized, strict_deadline_guaranteed e
authenticated_witness_verified permanecem false. Sem certificação operacional.
