# Trading Economics — operação controlada no Windows (RC21)

Este procedimento executa primeiro um pré-voo offline. A primeira chamada externa somente ocorre quando o operador acrescenta `--execute`.

O calendário permanece observacional:

- não altera o `ScoreEngine`;
- não envia nem executa ordens;
- não modifica a psicologia do trader;
- grava somente pacotes sanitizados para replay e avaliação.

## Pré-requisitos

1. Abrir o PowerShell na raiz `C:\COPILOTO_PRICE_ACTION_AI`.
2. Ativar o ambiente Python do projeto.
3. Ter uma chave válida fornecida oficialmente pela Trading Economics.
4. Nunca colar a chave em arquivos, argumentos do Python, prints ou GitHub.

## 1. Ativar o ambiente Python

```powershell
.\ambiente\Scripts\Activate.ps1
```

## 2. Carregar a chave sem gravá-la no histórico

O comando abaixo solicita a chave em campo oculto e a mantém somente no ambiente do processo atual do PowerShell.

```powershell
$SecureTeKey = Read-Host "Trading Economics API key" -AsSecureString
$TeKeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureTeKey)
try {
    $env:COPILOTO_TE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($TeKeyPointer)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($TeKeyPointer)
}
$env:COPILOTO_TE_ENABLED = "true"
```

Não execute `Write-Host $env:COPILOTO_TE_API_KEY` e não tire print da variável.

## 3. Executar somente o pré-voo

Este comando não acessa a internet e não cria o pacote:

```powershell
python -m app.economic_calendar_capture_cli --destination "data\calendar\D1.calendar-replay.json" --session-id "D1" --capture-enabled --json
```

Resultado esperado:

```json
{"status":"APPROVED","package_name":"D1.calendar-replay.json"}
```

O resultado real inclui verificações adicionais, mas nunca deve mostrar a chave nem o caminho completo.

## 4. Executar uma captura controlada

Somente depois de conferir `APPROVED`, repetir o comando acrescentando `--execute`:

```powershell
python -m app.economic_calendar_capture_cli --destination "data\calendar\D1.calendar-replay.json" --session-id "D1" --capture-enabled --execute --json
```

Resultado esperado: `COMPLETED`, quantidade recebida/mapeada e checksum SHA-256.

Cada sessão deve usar um identificador e arquivo novos, por exemplo `D2`, `D3`, `D4` e `D5`. O sistema bloqueia sobrescrita.

## 5. Remover a chave ao terminar

```powershell
Remove-Item Env:COPILOTO_TE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:COPILOTO_TE_ENABLED -ErrorAction SilentlyContinue
Remove-Variable SecureTeKey -ErrorAction SilentlyContinue
Remove-Variable TeKeyPointer -ErrorAction SilentlyContinue
```

Fechar o PowerShell também encerra as variáveis dessa sessão.

## Estados de bloqueio

| Código | Significado |
|---|---|
| `INVALID_CONFIGURATION` | Configuração ou chave ausente/inválida |
| `CONFIG_NOT_READY` | Provedor não foi habilitado |
| `CAPTURE_DISABLED` | Segunda trava não foi aberta |
| `INVALID_SESSION_ID` | Identificador da sessão vazio |
| `INVALID_DESTINATION` | Nome/extensão do pacote inválido |
| `DESTINATION_EXISTS` | Arquivo já existe; sobrescrita bloqueada |
| `UNSAFE_LIMITS` | Timeout ou limite de resposta fora da política |
| `CAPTURE_FAILED` | Falha externa sanitizada; pacote não concluído |

## Resposta a incidentes

Se a chave aparecer em terminal, print, arquivo, commit ou mensagem:

1. interromper a captura;
2. remover a variável de ambiente;
3. revogar/rotacionar a chave no provedor;
4. não reutilizar a chave exposta;
5. verificar `git status` antes de qualquer commit;
6. somente continuar com uma nova credencial.

Os arquivos `.env`, credenciais, chaves privadas e `*.calendar-replay.json` estão bloqueados pelo `.gitignore`.
