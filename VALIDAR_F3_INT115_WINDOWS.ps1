param([string]$AuditPath = (Join-Path $PSScriptRoot 'audit'))
$ErrorActionPreference = 'Stop'
if (-not (Test-Path (Join-Path $AuditPath 'tests'))) { throw "Pasta audit/tests nao encontrada: $AuditPath" }
$AuditPath = (Resolve-Path $AuditPath).Path
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$folder = Join-Path $AuditPath "RESULTADOS_F3_INT115_CHAT_$stamp"
New-Item -ItemType Directory -Path $folder | Out-Null
Push-Location $AuditPath
try {
  $summary = @()
  $cases = @(
    @{ Name='IDENTIDADE_CONTROLE'; Args=@('-B','-m','unittest','tests.test_f3_int115_process_identity','tests.test_f3_int115_process_control','-v') },
    @{ Name='REGRESSAO_COMPLETA'; Args=@('-B','-m','unittest','discover','-s','tests','-p','test_*.py') }
  )
  foreach ($case in $cases) {
    $log = Join-Path $folder ($case.Name + '.log')
    "COMANDO: python $($case.Args -join ' ')" | Set-Content -LiteralPath $log -Encoding UTF8
    & python @($case.Args) 2>&1 | Out-File -LiteralPath $log -Append -Encoding UTF8
    $exit = $LASTEXITCODE
    $summary += [pscustomobject]@{ teste=$case.Name; exit_code=$exit; log=$log }
    Write-Host "$($case.Name): exit code $exit"
    if ($exit -ne 0) { Write-Warning "Falha detectada. Regressao adicional nao sera executada."; break }
  }
  $summary | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $folder 'RESUMO.json') -Encoding UTF8
  Write-Host "RESULTADOS: $folder"
  if (($summary | Where-Object exit_code -ne 0).Count -gt 0) { exit 1 }
} finally { Pop-Location }
