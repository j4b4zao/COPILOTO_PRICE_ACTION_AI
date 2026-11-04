#requires -Version 7.0
param(
    [string]$Repo = 'C:\COPILOTO_PRICE_ACTION_AI',
    [string]$Head = '302937f33f1dfe5ba22e28f170fb5964046f4e13'
)

$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path -LiteralPath $Repo).Path

function Invoke-LocalGit {
    param([string[]]$GitArgs)
    $result = git -c "safe.directory=$($Repo.Replace('\', '/'))" -C $Repo @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "Git falhou: $GitArgs" }
    $result
}

$operacao = [ordered]@{
    f3 = 'OPEN'
    offline = $true
    simulation_only = $true
    certification = $false
    real_operations_authorized = $false
    production_api_changed = $false
}

function Test-Manifesto($manifesto, [int]$etapa, [string]$parent) {
    $fase = if ($etapa -eq 12) { "A14.$etapa" } else { "F3-INT-121 A14.$etapa" }
    $campoFase = if ($etapa -eq 12) { 'stage' } elseif ($etapa -le 20) { 'phase' } else { 'etapa' }
    if ($manifesto[$campoFase] -cne $fase) { throw "FASE_DIVERGENTE A14.$etapa" }

    if ($etapa -ge 13) {
        $campoPai = if ($etapa -le 20) { 'parent_commit' } else { 'commit_base' }
        if ($manifesto[$campoPai] -cne $parent) { throw "PARENT_DIVERGENTE A14.$etapa" }
    }

    $estado = switch ($etapa) {
        21 { $manifesto.estado_operacional }
        22 { $manifesto.operacao }
        23 { $manifesto.estado_operacional }
        default { $manifesto }
    }
    if ($null -eq $estado) { throw "ESTADO_AUSENTE A14.$etapa" }
    $ausentes = @()
    foreach ($chave in $operacao.Keys) {
        $esperado = $operacao[$chave]
        $ausenciaLegada = $etapa -eq 12 -or ($etapa -eq 13 -and $chave -in @('f3', 'production_api_changed'))
        if (-not $estado.Contains($chave) -and $ausenciaLegada) {
            $ausentes += $chave
            continue
        }
        $valor = $estado[$chave]
        if ($null -eq $valor -or $valor.GetType() -ne $esperado.GetType() -or $valor -cne $esperado) {
            throw "ESTADO_DIVERGENTE A14.$etapa $chave"
        }
    }
    [ordered]@{ campos_verificados = 6 - $ausentes.Count; campos_legados_ausentes = $ausentes }
}

$commit = Invoke-LocalGit @('rev-parse', '--verify', "$Head^{commit}")
$auditoria = foreach ($etapa in 23..12) {
    $data = if ($etapa -le 19) { '20261103' } else { '20261104' }
    $pasta = "checkpoints/F3_INT121_A14_${etapa}_$data"
    $manifestos = @(Invoke-LocalGit @('ls-tree', '-r', '--name-only', $commit, '--', $pasta) |
        Where-Object { $_ -cmatch "^$pasta/MANIFESTO[^/]*\.json$" })
    if ($manifestos.Count -ne 1) { throw "QUANTIDADE_MANIFESTOS A14.$etapa" }

    $parent = Invoke-LocalGit @('rev-parse', '--verify', "$commit^")
    $introduzidos = @(Invoke-LocalGit @('diff-tree', '--no-commit-id', '--name-only', '--diff-filter=A', '-r', $parent, $commit, '--', $pasta))
    if ($manifestos[0] -cnotin $introduzidos) { throw "MANIFESTO_FORA_DO_COMMIT A14.$etapa" }
    $manifesto = (Invoke-LocalGit @('show', "${commit}:$($manifestos[0])") | Out-String) | ConvertFrom-Json -AsHashtable
    $resultado = Test-Manifesto $manifesto $etapa $parent
    [ordered]@{
        etapa = "A14.$etapa"
        commit = $commit
        parent = $parent
        manifesto = $manifestos[0]
        campos_verificados = $resultado.campos_verificados
        campos_legados_ausentes = $resultado.campos_legados_ausentes
    }
    $commit = $parent
}

# Contraprovas em memoria sobre o manifesto A14.23.
$base = $auditoria[0]
$original = Invoke-LocalGit @('show', "$($base.commit):$($base.manifesto)") | Out-String
$contraprovas = foreach ($caso in @(
    @{ chave = 'etapa'; valor = 'F3-INT-121 A14.22'; erro = 'FASE_DIVERGENTE' },
    @{ chave = 'commit_base'; valor = $base.commit; erro = 'PARENT_DIVERGENTE' },
    @{ chave = 'offline'; valor = 'true'; erro = 'ESTADO_DIVERGENTE' },
    @{ chave = 'real_operations_authorized'; valor = $true; erro = 'ESTADO_DIVERGENTE' },
    @{ chave = 'production_api_changed'; remover = $true; erro = 'ESTADO_DIVERGENTE' }
)) {
    $copia = $original | ConvertFrom-Json -AsHashtable
    if ($caso.chave -in @('etapa', 'commit_base')) {
        $copia[$caso.chave] = $caso.valor
    } elseif ($caso.remover) {
        $copia.estado_operacional.Remove($caso.chave)
    } else {
        $copia.estado_operacional[$caso.chave] = $caso.valor
    }
    try {
        $null = Test-Manifesto $copia 23 $base.parent
        throw "CONTRAPROVA_ACEITA $($caso.chave)"
    } catch {
        if ($_.Exception.Message -cnotlike "$($caso.erro) *") { throw }
    }
    [ordered]@{ campo = $caso.chave; resultado = 'REJEITADO'; motivo = $caso.erro }
}

[ordered]@{
    etapa = 'F3-INT-121 A14.27'
    commit_base = $base.commit
    escopo = 'Fase, introducao no Git, pai declarado e estado operacional dos manifestos versionados A14.12 a A14.23'
    estado_operacional = $operacao
    manifestos = $auditoria
    contraprovas = $contraprovas
} | ConvertTo-Json -Depth 8
