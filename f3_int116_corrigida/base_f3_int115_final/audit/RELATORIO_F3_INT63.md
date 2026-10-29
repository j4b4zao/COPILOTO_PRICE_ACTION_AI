# F3-INT-63

Contraprova offline: replay rejeitado com snapshot mantido e aceito apos reposicao integral de versao e estado pelo chamador; resets parciais nao bastam. Limitacao demonstrada, nao mitigacao de persistencia real.

Testes novos: 12/12. Regressao integral da auditoria isolada: 717/717.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-64: monitor independente de condicoes necessarias nas transicoes de snapshot.
