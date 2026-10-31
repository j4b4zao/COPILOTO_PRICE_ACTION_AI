# F3-INT-121 A14.2 — candidata (29/10/2026)

Objetivo: repetir a detecção de descendentes sobreviventes na contraprova A13
(duas execuções independentes) e compará-la a um controle positivo A12 com
KILL_ON_JOB_CLOSE ativo (uma execução). Cada repetição usa fixture isolada.

Limites: reutiliza os mecanismos A12/A13; não introduz nova injeção de falha,
não testa atraso ou falha do Job externo, não demonstra resistência a falhas
físicas, nem autenticação independente. A13 já exige limpeza externa confirmada.

Status: CANDIDATA; testes Windows e regressões NÃO EXECUTADOS nesta criação.

Execução no Windows, na raiz extraída:

    python -B -m unittest test_f3_int121_a14_2_survivors -v
    python -O -B -m unittest test_f3_int121_a14_2_survivors -v
    python -B -m unittest discover -s . -p "test_*.py" -q
    python -O -B -m unittest discover -s . -p "test_*.py" -q

Critérios: três testes específicos por modo; regressão integral sem erros,
falhas ou skips inesperados; nenhuma operação real.

F3=OPEN. orders_allowed=false; live_certified=false; flow_complete=false;
f3_resolved=false; native_prototype_authorized=false;
strict_deadline_guaranteed=false; authenticated_witness_verified=false.
