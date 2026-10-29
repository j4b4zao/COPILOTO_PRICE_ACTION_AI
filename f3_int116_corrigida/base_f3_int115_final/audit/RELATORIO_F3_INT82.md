# F3-INT-82

Importacao atomica de testemunhos vinculados a pacotes: verifica ZIP, caminho, pin e replay antes de atualizar registro canonico. Falha em qualquer item preserva identidade do registro e nao expoe vinculos parciais; duplicatas canonicas entre pacotes sao rejeitadas.

Testes novos: 13/13. Regressao integral da auditoria isolada: 958/958.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-83: propostas concorrentes de importacao sobre snapshots compartilhados do registro.
