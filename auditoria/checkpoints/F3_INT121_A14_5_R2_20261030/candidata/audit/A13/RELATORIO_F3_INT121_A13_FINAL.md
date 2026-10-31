# F3-INT-121 A13 — Fechamento documental da contraprova (29/10/2026)

## Escopo
Pacote isolado de testes offline Windows. A13 realiza contraprova controlada da ausência de KILL_ON_JOB_CLOSE no Job interno, preservando a contenção externa. Correção de descoberta de unittest: importação do módulo A12 em lugar da classe de testes no namespace A13.

## Evidências recebidas do usuário
- Execução normal da suíte corrigida: `Ran 168 tests in 309.455s`, `OK`.
- Execução com `python -O`: `Ran 168 tests in 351.003s`, `OK`.
- Ambas registram `negative_control_detected: true`; `optimization: 0` e `optimization: 1`, respectivamente.
- 336 execuções de testes registradas em duas passagens, não 336 testes distintos.
- Os logs resumidos não informam explicitamente número de skips; não se afirma zero skips.

## Limites de comprovação
Logs Windows são evidências fornecidas pelo usuário, não execução independente neste ambiente. A verificação de integridade dos arquivos do ZIP e do manifesto não autentica a origem nem garante resistência a adulteração externa. A regressão abrange apenas os 168 testes descobertos na pasta do pacote, não o repositório operacional completo.

## Estado
F3=OPEN; orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false. Somente offline/simulação. Nenhuma autorização para ordens reais.

## Continuação
A14: propor escopo e critérios de aceitação antes de implementar; não há autorização implícita para desenvolvimento ou promoção operacional.
