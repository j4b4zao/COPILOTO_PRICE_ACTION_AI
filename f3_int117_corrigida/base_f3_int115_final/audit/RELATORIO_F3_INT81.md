# F3-INT-81

Vinculo entre pacote verificado, caminho JSON, bytes do testemunho e pin canonico, com replay completo antes da entrega de payload; formatacao diferente preserva identidade canonica. Pins continuam fixtures do chamador.

Testes novos: 10/10. Regressao integral da auditoria isolada: 945/945.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-82: importacao atomica de lotes de testemunhos vinculados a pacotes.
