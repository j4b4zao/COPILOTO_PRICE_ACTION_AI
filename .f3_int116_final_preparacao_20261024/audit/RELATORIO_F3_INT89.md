# F3-INT-89

Codec fechado schema1 por referencias, sem embutir ZIPs no JSON: catalogo limitado, hashes e etapas exatos, sem duplicatas ou entradas nao usadas, replay completo e digests de traces. Exemplos sinteticos identificados.

Testes novos: 14/14. Regressao integral da auditoria isolada: 1048/1048.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-90: bundle fechado autocontido de referencias JSON e catalogo para replay offline.
