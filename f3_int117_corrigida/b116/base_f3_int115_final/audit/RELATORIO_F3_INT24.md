# F3-INT-24 — Reconciliação de inventários multitentativa (simulada)

## Origem
Base: PACOTE_AUDITORIA_F3_INT23.zip, extraído previamente em f3_int23_verify. Alteração apenas em tools/f3_int20_evidence_recovery_model.py; novo tests/test_f3_int24_multicreation_inventory.py. Outros módulos de teste e Architecture C preservados na cópia.

## Diagnóstico
A06 falhava porque cada C(attempt) exigia todos os processos conhecidos da sessão, não apenas os pertencentes àquela tentativa. A primeira correção excessivamente estrita rejeitou descendentes descobertos (teste anterior de inventário de descendentes). A versão final aceita a cobertura de descendentes vinculados às provas e exige que cada processo originalmente conhecido apareça ao menos uma vez, que nenhum processo seja atribuído a duas tentativas e que todas as tentativas tenham C completa e settled. P/H continuam obrigatórios para todos os processos reconciliados; V/I/F/U/J/L, conflitos e gates de commit permanecem intactos.

## Testes executados nesta sessão
- Regressão integral simulada: 203/203 PASS, 0 falhas, 0 erros; 19.733 s.
- Seis testes novos INT24: 6/6 PASS, 0 falhas, 0 erros.
- A06 histórico incluído nos 203 e aprovado.
- Exploração limitada anterior INT10/13/14/15 foi executada dentro da regressão; resultados detalhados no log. Nenhuma exploração nova especificamente de INT24 foi criada.

## Limites e risco residual
As provas de completude por tentativa continuam sendo premissas de fixtures simuladas. O modelo não verifica descoberta nativa de processos nem autenticação criptográfica real; processos adicionais podem aparecer como descendentes se a prova sintética C for marcada completa. A exclusão de processos inesperados depende da confiabilidade da evidência e da validação de P/H, não de enumeração nativa. Nenhuma certificação de Windows, Job Object, testemunha ou deadline. Não executar em negociação real.

F3=OPEN; orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false.
