# F3-INT-115 — correção da verificação de PID (candidata)

Diagnóstico: o log Windows registra PID do processo lançado diferente do PID comunicado pelo worker em 17 casos. O motivo exato da divergência não está estabelecido. Igualdade numérica não demonstra contenção; removê-la sem substituição seria inseguro.

Correção: após receber o evento `ready`, o teste exige PID inteiro positivo, diferente do processo de teste, abre um HANDLE do processo comunicado, confirma `IsProcessInJob` no Job Object específico do `Peer`, captura a identidade do processo (PID e instante de criação) e retém o HANDLE até a limpeza. Processo externo, PID inválido, erro de acesso ou worker já encerrado causam falha fechada. O teste não presume que o worker é filho direto do launcher.

**Limitações:** não executamos testes Windows neste ambiente. A presença no Job não é prova de identidade do executável, custódia independente ou durabilidade física. A investigação da divergência de PID permanece aberta.

**Estado:** F3 OPEN; sete flags false; sem rede, ordens reais ou promoção FINAL.

**Windows (PowerShell na raiz do projeto):**

```powershell
python -B -m unittest -v tests.test_f3_int115_multiprocess_recovery *> audit\RESULTADO_F3_INT115_PID_ESPECIFICOS.txt
$LASTEXITCODE
python -B -m unittest discover -s audit/tests -p 'test_*.py' -v *> audit\RESULTADO_F3_INT115_PID_REGRESSAO.txt
$LASTEXITCODE
```

Se a suíte usa um runner próprio para o projeto, mantenha o mesmo comando da regressão anterior. Anexe os logs completos.
