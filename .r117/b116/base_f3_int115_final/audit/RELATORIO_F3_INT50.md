# F3-INT-50

Recuperacao com epocas concorrentes, deteccao de equivoco, replay, digest divergente e entradas limitadas.

Testes novos: 26/26. Regressao integral da auditoria isolada: 478/478.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-51: sequencias de recuperacao com memoria simulada de replay e rollback entre rodadas.
