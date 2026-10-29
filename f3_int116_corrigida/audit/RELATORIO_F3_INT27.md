# F3-INT-27 — Exploração combinatória limitada

Data: 2026-10-20. Escopo: simulação pura, sem APIs nativas nem integração operacional.

Base: PACOTE_AUDITORIA_F3_INT26_CHAT.zip. Modelo de recuperação e Architecture C preservados sem alterações.

## Execução

- Novos testes: 4/4 aprovados; 17 variantes por subtestes (6 permutações com J negativo, 6 com duplicidade/tentativa desconhecida, 4 tipos de invalidação de ticket, 1 contestação terminal).
- Regressão: 223/223 aprovados em 22,292 s, exit code 0.
- Explorações limitadas anteriores foram incluídas na regressão. Seus orçamentos e limites constam da saída integral.
- Sem contraexemplos finais nos cenários verificados. Isto não é prova exaustiva, nativa ou criptográfica.

## Histórico de correção do teste

Na primeira execução, 6 subtestes exigiam incorretamente que uma observação negativa de Job bloqueasse para sempre o encerramento, mesmo após nova prova válida J/L. Corrigiu-se apenas a expectativa do teste: a observação antiga continua insuficiente, mas nova prova pode permitir fechamento. Nenhuma linha do modelo foi alterada.

## Limitações

A cobertura é combinatória limitada e determinística; não há minimizador automatizado de contraexemplos nem verificação formal de todas as interleavings. A simulação não comprova atomicidade real, autenticação, contenção Windows ou deadlines estritos.

F3=OPEN. orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false.
