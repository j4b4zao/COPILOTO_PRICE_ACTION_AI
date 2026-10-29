# F3-INT-56

Fachada bounded_prepare/bounded_commit com rejeicao previa de arvores profundas, entradas mutaveis, objetos desconhecidos e excesso de nos/strings; pontos legados permanecem sem estes limites globais. Ver NOTA_F3_INT56.md.

Testes novos: 20/20. Regressao integral da auditoria isolada: 612/612.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-57: tentativas limitadas com commits concorrentes interpostos e revalidacao sobre snapshot recente.
