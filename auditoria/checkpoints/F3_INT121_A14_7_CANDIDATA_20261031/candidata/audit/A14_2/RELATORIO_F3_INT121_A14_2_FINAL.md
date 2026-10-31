# F3-INT-121 A14.2 — FINAL DOCUMENTAL (29/10/2026)

Base: pacote candidato A14.2. Evidências de execução Windows fornecidas pelo usuário, sem reexecução independente nesta consolidação.

- Testes específicos: 3/3 em Python normal (23,474 s), 3/3 em Python -O (22,566 s).
- Regressão completa: 173/173 normal (468,135 s), 173/173 otimizada (533,540 s). Sem falhas/erros informados.
- Contraprovas negativas: duas repetições detectaram sobreviventes quando proteção interna KILL_ON_JOB_CLOSE ausente.
- Controle positivo: 0 processos ativos antes da limpeza de segurança, proteção interna ativa.
- Escopo não coberto: falha/atraso de limpeza do Job externo, autenticação independente e garantias físicas.

Próxima etapa: A14.3, sem autorização operacional. F3=OPEN; operações reais bloqueadas.
