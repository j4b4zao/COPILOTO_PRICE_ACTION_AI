# Retomada F3-INT-115 pelo chat — candidato de correção

## Evidências existentes no ZIP recebido
- `ULTIMO_MARCO.json`: F3-INT-114 FINAL. Não foi promovido.
- Investigação mais recente `F3_INT115_INVESTIGACAO_IDENTIDADE_20261023/RESUMO_ANTES_DA_CORRECAO.json`: 50 repetições do teste antigo, 22 falhas e 6 erros; 100 sondagens de identidade pinada, 99 observações de corrida de término no mesmo handle; nenhuma reutilização de PID observada; handles pinados terminaram posteriormente.
- A base contém implementação posterior de Job Object + JobTracker + ProcessRef, ainda não aprovada por regressão Windows.

## Correções pontuais feitas nesta retomada
1. `audit/tests/test_f3_int115_process_identity.py`: removido trecho de string malformada e redundante que impedia o módulo de compilar. Preservado o programa de teste multiline já existente.
2. `audit/tests/test_f3_int115_process_control.py`: duas asserções pós-limpeza baseadas em PID solto foram substituídas por exigência de `cleanup.confirmed` e prova de término por identidade retida (`exit_confirmed`), além de `active_processes == 0` já verificado. O teste ainda exige a execução real do descendente e do supervisor; nenhuma falha de limpeza é tolerada.

## Limites
- O ambiente de execução desta revisão é Linux; os módulos de Windows Job Objects não podem ser executados aqui.
- Compilação sintática local das fontes Python ativas foi verificada. Isso não substitui a regressão Windows.
- F3 OPEN; todas as sete flags continuam false; sem operações reais, rede ou autorização de execução live.

## Validação exigida no Windows (PowerShell)
Abra a pasta `audit` do pacote extraído e execute:

```powershell
python -B -m unittest tests.test_f3_int115_process_identity tests.test_f3_int115_process_control -v 2>&1 | Tee-Object -FilePath .\RESULTADO_F3_INT115_IDENTIDADE_WINDOWS.txt
$LASTEXITCODE
python -B -m unittest discover -s tests -p 'test_*.py' 2>&1 | Tee-Object -FilePath .\RESULTADO_F3_INT115_REGRESSAO_CHAT_WINDOWS.txt
$LASTEXITCODE
```

**Atenção:** se o comando de testes do projeto usar argumentos adicionais ou outro runner, seguir as instruções locais do runner e preservar os logs completos. Não promover para FINAL antes de obter exit code 0 e analisar todas as evidências.
