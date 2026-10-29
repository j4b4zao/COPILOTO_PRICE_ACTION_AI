param([string]$AuditPath = (Join-Path $PSScriptRoot 'audit'))
$ErrorActionPreference = 'Stop'
$Error.Clear()
if (-not (Test-Path (Join-Path $AuditPath 'tests'))) { throw "Pasta audit/tests nao encontrada: $AuditPath" }
$AuditPath = (Resolve-Path $AuditPath).Path
$python = (Get-Command python.exe -ErrorAction Stop).Source
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$folder = Join-Path $AuditPath "RESULTADOS_F3_INT115_CHAT_$stamp"
New-Item -ItemType Directory -Path $folder -Force | Out-Null
Push-Location $AuditPath
try {
  $summary = @()
  $cases = @(
    @{ Name='IDENTIDADE_CONTROLE'; Args=@('-B','-m','unittest','tests.test_f3_int115_process_identity','tests.test_f3_int115_process_control','-v') },
    @{ Name='REGRESSAO_COMPLETA'; Args=@('-B','-m','unittest','discover','-s','tests','-p','test_*.py') }
  )
  foreach ($case in $cases) {
    $log = Join-Path $folder ($case.Name + '.log')
    $stdout = Join-Path $folder ($case.Name + '.stdout.tmp')
    $stderr = Join-Path $folder ($case.Name + '.stderr.tmp')
    $argsList = [string[]]$case.Args
    "COMANDO: python $($argsList -join ' ')" | Set-Content -LiteralPath $log -Encoding UTF8
    $exitCode = -1
    try {
      $proc = Start-Process -FilePath $python -ArgumentList $argsList -WorkingDirectory $AuditPath -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
      $exitCode = $proc.ExitCode
    } catch {
      "ERRO AO INICIAR PROCESSO: $($_.Exception.Message)" | Add-Content -LiteralPath $log
    }
    "`n=== STDOUT ===" | Add-Content -LiteralPath $log
    if (Test-Path $stdout) { Get-Content -LiteralPath $stdout | Add-Content -LiteralPath $log }
    "`n=== STDERR (unittest escreve progresso aqui) ===" | Add-Content -LiteralPath $log
    if (Test-Path $stderr) { Get-Content -LiteralPath $stderr | Add-Content -LiteralPath $log }
    "`nEXIT_CODE=$exitCode" | Add-Content -LiteralPath $log
    Remove-Item -LiteralPath $stdout,$stderr -ErrorAction SilentlyContinue
    $summary += [pscustomobject]@{ teste=$case.Name; exit_code=$exitCode; log=$log }
    Write-Host "$($case.Name): exit code $exitCode"
    if ($exitCode -ne 0) { Write-Warning 'Falha detectada; regressao adicional nao sera executada.'; break }
  }
  @($summary) | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $folder 'RESUMO.json') -Encoding UTF8
  Write-Host "RESULTADOS: $folder"
  if (@($summary | Where-Object { $_.exit_code -ne 0 }).Count -gt 0) { exit 1 }
} finally { Pop-Location }
