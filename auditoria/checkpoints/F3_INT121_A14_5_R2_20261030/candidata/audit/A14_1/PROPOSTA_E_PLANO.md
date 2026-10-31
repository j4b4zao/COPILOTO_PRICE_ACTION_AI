# F3-INT-121 A14.1 — Candidata de repetição de interrupções (29/10/2026)

## Escopo autorizado
Primeira implementação isolada da A14: repetir a morte do supervisor em duas fronteiras distintas já instrumentadas pela A12: antes do commit de consumo e depois do commit do ACK local. Cada teste usa uma fixture A12 nova, diretório SQLite independente e handles retidos. A14.1 não acrescenta novos pontos de injeção, nem pretende cobrir todas as interleavings de escalonamento.

## Critérios
Os dois testes novos precisam passar em Python normal e otimizado, confirmar contenção antes da limpeza externa, limpeza confirmada e bloqueios operacionais falsos. Regressão completa do pacote sem erros, falhas ou skips não justificados. Evidências geradas no Windows devem ser revisadas antes de qualquer checkpoint final.

## Restrições
F3=OPEN. Somente fixtures offline; nenhuma operação real, rede operacional, Profit, Excel, RTD/DDE ou certificação. Não substituir arquivos do projeto principal. A13 permanece como último marco FINAL. Não há autorização de promoção da A14.1 até validar Windows.

## Execução
Extraia o ZIP em pasta NOVA, fora do projeto operacional. Na raiz extraída:

`python -B -m unittest test_f3_int121_a14_1_supervisor_phases -v`

`python -O -B -m unittest test_f3_int121_a14_1_supervisor_phases -v`

Após aprovação dos específicos, executar regressão normal e otimizada:

`python -B -m unittest discover -s . -p "test_*.py" -q`

`python -O -B -m unittest discover -s . -p "test_*.py" -q`

Não execute simultaneamente as suítes: A12 usa índices de evidências compartilhados por processo.
