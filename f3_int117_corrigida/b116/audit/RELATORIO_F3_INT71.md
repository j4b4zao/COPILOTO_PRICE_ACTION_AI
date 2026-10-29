# F3-INT-71

Corpus deterministico limitado de 43 casos sobre o codec: duas normalizacoes validas aceitas e mutacoes estruturais, digests, eventos, tipos e bytes invalidos rejeitadas; truncamento de cobertura explicito.

Testes novos: 6/6. Regressao integral da auditoria isolada: 822/822.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-72: ingestao atomica de lotes de testemunhos com registro canonico local contra replay.
