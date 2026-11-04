#requires -Version 7.4
param(
    [Parameter(Mandatory)][string]$Repo,
    [string]$Base = '9601475f2fa7f492ff5b4fb7e65f4d3e6d476404'
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$folders = @{}
foreach ($stage in 19..24) {
    $date = if ($stage -eq 19) { '20261103' } else { '20261104' }
    $folders[$stage] = "checkpoints/F3_INT121_A14_${stage}_$date"
}

function Read-Entry($zip, [string]$path) {
    $entries = @($zip.Entries | Where-Object { $_.FullName -ceq $path })
    if ($entries.Count -ne 1) { throw "ENTRADA_AUSENTE_OU_DUPLICADA $path" }
    $stream = $entries[0].Open()
    $buffer = [IO.MemoryStream]::new()
    try {
        $stream.CopyTo($buffer)
        return ,$buffer.ToArray()
    } finally {
        $stream.Dispose()
        $buffer.Dispose()
    }
}

function Get-Sha([byte[]]$bytes) {
    [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
}

function Confirm-Binding([byte[]]$gitBytes, [byte[]]$zipBytes, [string]$hash, $size, [string]$path) {
    if ((Get-Sha $zipBytes) -cne $hash -or ($null -ne $size -and $zipBytes.Length -ne $size)) {
        throw "DECLARACAO_DIVERGENTE $path"
    }
    if ((Get-Sha $gitBytes) -ceq $hash) { return 'IDENTICO' }
    $encoding = [Text.Encoding]::Latin1
    $normalized = $encoding.GetBytes($encoding.GetString($zipBytes).Replace("`r`n", "`n"))
    if ((Get-Sha $gitBytes) -cne (Get-Sha $normalized)) { throw "BLOB_DIVERGENTE $path" }
    'ZIP_CRLF_GIT_LF'
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("a14_25_" + [guid]::NewGuid() + '.zip')
function Read-Blob([string]$path) {
    git -C $Repo cat-file blob "${Base}:$path" > $tmp
    return ,[IO.File]::ReadAllBytes($tmp)
}
$packages = @{}
try {
    $resolved = git -C $Repo rev-parse --verify "$Base^{commit}"
    if ($resolved -cne $Base) { throw 'BASE_DIVERGENTE' }
    $manifests = @{}
    $manifestResults = [Collections.Generic.List[object]]::new()
    foreach ($stage in 19..23) {
        $dir = $folders[$stage]
        $date = $dir.Split('_')[-1]
        $name = "MANIFESTO_A14_${stage}_$date.json"
        $pack = Read-Blob "$dir/F3_INT121_A14_${stage}_VALIDACAO_$date.zip"
        $packages[$stage] = [IO.Compression.ZipArchive]::new([IO.MemoryStream]::new($pack))
        $bytes = Read-Blob "$dir/$name"
        $packed = Read-Entry $packages[$stage] $name
        try {
            $status = Confirm-Binding $bytes $packed (Get-Sha $packed) $null "$dir/$name"
        } catch {
            if ($_.Exception.Message -cnotlike 'BLOB_DIVERGENTE *') { throw }
            $status = 'BLOB_DIVERGENTE'
        }
        $manifestResults.Add([ordered]@{ caminho = "$dir/$name"; sha256_zip = Get-Sha $packed; sha256_git = Get-Sha $bytes; resultado = $status })
        $manifests[$stage] = [Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json -AsHashtable
    }

    $refs = @(
        foreach ($stage in 19..20) {
            foreach ($file in $manifests[$stage].files.GetEnumerator()) {
                @{ origem = $stage; destino = $stage; nome = $file.Key; hash = $file.Value.sha256; bytes = $file.Value.bytes }
            }
        }
        foreach ($file in $manifests[21].scripts) {
            @{ origem = 21; destino = 21; nome = $file.arquivo; hash = $file.sha256 }
        }
        @{ origem = 21; destino = 20; nome = 'auditoria_a14_20.py'; hash = $manifests[21].auditor_a14_20_sha256 }
        @{ origem = 21; destino = 19; nome = 'a14_19_manifestos_referencias.json'; hash = $manifests[21].referencias_a14_19_sha256 }
        @{ origem = 22; destino = 22; nome = $manifests[22].script.arquivo; hash = $manifests[22].script.sha256 }
    )

    $results = foreach ($ref in $refs) {
        if ($ref.nome -cnotmatch '^[A-Za-z0-9_.-]+\.(json|py)$' -or $ref.hash -cnotmatch '^[0-9a-f]{64}$') {
            throw "REFERENCIA_INVALIDA A14.$($ref.origem)"
        }
        $path = "$($folders[$ref.destino])/$($ref.nome)"
        $blob = Read-Blob $path
        $entry = Read-Entry $packages[$ref.destino] $ref.nome
        try {
            $status = Confirm-Binding $blob $entry $ref.hash $ref.bytes $path
        } catch {
            if ($_.Exception.Message -cnotmatch '^(BLOB_DIVERGENTE|DECLARACAO_DIVERGENTE) ') { throw }
            $status = $_.Exception.Message.Split(' ')[0]
        }
        [ordered]@{ origem = "A14.$($ref.origem)"; caminho = $path; sha256_declarado = $ref.hash; sha256_zip = Get-Sha $entry; sha256_git = Get-Sha $blob; resultado = $status }
    }

    $legacy = Read-Blob "$($folders[24])/EVIDENCIA_A14_24_20261104.json"
    $previous = [Text.Encoding]::UTF8.GetString($legacy) | ConvertFrom-Json -AsHashtable
    $script = Read-Blob "$($folders[24])/auditoria_a14_24.ps1"
    if ((Get-Sha $script) -cne $previous.reproducao.sha256_script) { throw 'SCRIPT_A14_24_DIVERGENTE' }

    $controls = foreach ($case in @(
        @{ nome = 'hash_incorreto'; git = [byte[]]@(65); zip = [byte[]]@(65); hash = '0' * 64; size = 1; error = 'DECLARACAO_DIVERGENTE' },
        @{ nome = 'tamanho_incorreto'; git = [byte[]]@(65); zip = [byte[]]@(65); hash = Get-Sha ([byte[]]@(65)); size = 2; error = 'DECLARACAO_DIVERGENTE' },
        @{ nome = 'blob_trocado'; git = [byte[]]@(66); zip = [byte[]]@(65); hash = Get-Sha ([byte[]]@(65)); size = 1; error = 'BLOB_DIVERGENTE' }
    )) {
        try {
            $null = Confirm-Binding $case.git $case.zip $case.hash $case.size $case.nome
            throw "CONTRAPROVA_ACEITA $($case.nome)"
        } catch {
            if ($_.Exception.Message -cne "$($case.error) $($case.nome)") { throw }
        }
        $case.nome
    }

    [ordered]@{
        etapa = 'F3-INT-121 A14.25'
        commit_base = $Base
        estado_operacional = $previous.estado_operacional
        manifestos_git_zip = @($manifestResults.ToArray())
        sha256_script_a14_24 = Get-Sha $script
        referencias = @($results)
        contraprovas_rejeitadas = @($controls)
    } | ConvertTo-Json -Depth 8
} finally {
    foreach ($package in $packages.Values) { $package.Dispose() }
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp }
}
