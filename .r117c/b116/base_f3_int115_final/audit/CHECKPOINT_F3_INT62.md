# F3-INT-62

Verificacao estrita de JSON sem chaves duplicadas ou numeros nao finitos, duracoes validas e logs sem sumarios duplicados ou contradicoes de falha. Integridade de fixtures nao autentica origem.

Testes novos: 14/14. Regressao integral da auditoria isolada: 705/705.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-63: demonstracao adversarial de replay apos reset integral do snapshot pelo chamador.
