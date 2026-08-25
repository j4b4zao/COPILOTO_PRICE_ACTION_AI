# Profit RTD RC14 — Live preflight

Objetivo: verificar a prontidão da fonte Times & Trades RTD antes de uma sessão real, sem ativar flags automaticamente.

O preflight deve retornar `READY` somente quando:

- o ativo solicitado coincide com o workbook RTD;
- a fonte é `PROFIT_RTD`;
- existe ao menos um negócio válido na janela atual;
- a fonte permanece `observational_only=True`;
- `score_influence_allowed=False`;
- `order_execution_allowed=False`;
- o experimento `ENABLE_ORDER_FLOW_SCORE` permanece desligado.

Falhas de Excel, workbook, layout, ativo, ausência de negócios ou contrato de segurança resultam em `NOT_READY` com razões explícitas.

Mesmo com `READY`, o preflight não altera `ENABLE_PROFIT_RTD_ORDER_FLOW`, não muda o Score e não executa ordens. A ativação da fonte RTD continua sendo uma ação manual e opt-in do operador conforme o runbook RC13.
