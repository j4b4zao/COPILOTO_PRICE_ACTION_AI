# F3-INT-59

Oraculo independente baseado apenas na primeira acao commit em fixtures simetricas sobre snapshot vazio; familias de 1 a 4 atores, incluindo 2520 agendas com 630 vencedores por ator, sem alegacao de fairness real.

Testes novos: 9/9. Regressao integral da auditoria isolada: 657/657.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-60: integridade adversarial de pacotes, manifestos, checkpoints e evidencias de testes.
