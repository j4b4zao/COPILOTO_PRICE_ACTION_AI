# F3-INT-121 A14.3 — Candidata isolada

Dois testes Windows: (1) atraso limitado de 350 ms antes do fechamento do Job externo, com descendentes sobreviventes detectados; (2) falha injetada **antes** da chamada de limpeza, seguida de recuperação com Peer.close real. Em ambos, a limpeza real é obrigatória em finally e são verificados handles retidos, ausência de processos ativos e threads de I/O.

**Limitação:** a falha injetada é na orquestração de teste, não uma falha real de TerminateJobObject, CloseHandle ou Peer.close. Portanto, a etapa não demonstra tolerância a falhas nativas do Windows nem falha interna do Job externo. Atraso é deliberadamente limitado, não uma simulação de falha indefinida.

Ambiente: Windows offline isolado, sem Profit/Excel/RTD/DDE, sem rede operacional, sem ordens. F3 OPEN, simulation_only true. Não executado em Windows na preparação; regressões anteriores 173/173 por modo derivam de logs do usuário.
