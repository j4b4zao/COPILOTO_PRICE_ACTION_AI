# BookDiagnostics RC17 — Candidate Registry

O Candidate Registry registra, de forma persistente e auditável, a evolução de cada `book_state` experimental após o Promotion Evidence Report RC16.

Estados de governança:
- `RESEARCHING`: evidência ainda insuficiente ou inconclusiva;
- `REJECTED`: evidência quantitativa ou revisão manual rejeitou o candidato;
- `MANUAL_REVIEW`: RC16 reuniu evidência suficiente para revisão humana;
- `APPROVED_FOR_SHADOW`: aprovado manualmente apenas para futura observação em Shadow Mode.

Nenhum status altera `AnalysisContext`, Strategy, Score, Risk, Decision ou execução. `APPROVED_FOR_SHADOW` não significa promoção operacional: apenas autoriza uma próxima etapa passiva de comparação em tempo real.

O registro mantém histórico de evidências, amostras, Promotion Gate, walk-forward, notas manuais e timestamps. Também pode ser salvo/carregado em JSON para continuidade entre sessões de pesquisa.
