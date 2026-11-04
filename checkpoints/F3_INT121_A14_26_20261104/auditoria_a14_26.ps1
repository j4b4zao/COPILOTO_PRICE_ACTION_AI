#requires -Version 7.4
param(
    [Parameter(Mandatory)][string]$Repo,
    [string]$Base = 'a8048d1afb713fe6ec3c310a3da803e5a7944027'
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$temp = Join-Path ([IO.Path]::GetTempPath()) ("a14_26_" + [guid]::NewGuid())

function Read-Blob([string]$path) {
    git -C $Repo cat-file blob "${Base}:$path" > $temp
    return ,[IO.File]::ReadAllBytes($temp)
}

function Get-Sha([byte[]]$bytes) {
    [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
}

function Get-Entries($archive) {
    $entries = [Collections.Generic.Dictionary[string,IO.Compression.ZipArchiveEntry]]::new([StringComparer]::Ordinal)
    foreach ($entry in $archive.Entries) {
        if (-not $entries.TryAdd($entry.FullName, $entry)) {
            throw "ENTRADA_DUPLICADA $($entry.FullName)"
        }
    }
    return ,$entries
}

function Test-Entry($entries, [string]$name, [string]$hash, $size) {
    if ($hash -cnotmatch '^[0-9a-f]{64}$') { throw "HASH_INVALIDO $name" }
    if (-not $entries.ContainsKey($name)) { return 'ENTRADA_AUSENTE' }
    $entry = $entries[$name]
    $stream = $entry.Open()
    try {
        $actual = (Get-FileHash -InputStream $stream -Algorithm SHA256).Hash.ToLowerInvariant()
    } finally {
        $stream.Dispose()
    }
    if ($actual -cne $hash) { return 'HASH_DIVERGENTE' }
    if ($null -ne $size -and $entry.Length -ne $size) { return 'TAMANHO_DIVERGENTE' }
    'CONFIRMADO'
}

try {
    if ((git -C $Repo rev-parse --verify "$Base^{commit}") -cne $Base) { throw 'BASE_DIVERGENTE' }
    $audits = foreach ($stage in 12..18) {
        $dir = "checkpoints/F3_INT121_A14_${stage}_20261103"
        $name = "F3_INT121_A14_${stage}_VALIDACAO_20261103.zip"
        $manifestBytes = Read-Blob "$dir/MANIFESTO_A14_${stage}_20261103.json"
        $manifest = [Text.Encoding]::UTF8.GetString($manifestBytes) | ConvertFrom-Json -AsHashtable
        $bytes = Read-Blob "$dir/$name"
        $sha = Get-Sha $bytes
        $sidecar = [Text.Encoding]::UTF8.GetString((Read-Blob "$dir/$name.sha256")).Trim().TrimStart([char]0xFEFF)
        if ($sidecar -notmatch '^([0-9a-f]{64})(?:\s+\*?(.+))?$' -or $Matches[1].ToLowerInvariant() -cne $sha -or ($Matches[2] -and $Matches[2] -cne $name)) {
            throw "SIDECAR_DIVERGENTE A14.$stage"
        }
        if ($stage -gt 12 -and ($manifest.zip.sha256 -cne $sha -or $manifest.zip.name -cne $name -or $manifest.zip.bytes -ne $bytes.Length)) {
            throw "PACOTE_DIVERGENTE A14.$stage"
        }

        $archive = [IO.Compression.ZipArchive]::new([IO.MemoryStream]::new($bytes))
        try {
            $entries = Get-Entries $archive
            $refs = if ($stage -eq 12) {
                foreach ($item in $manifest.files_sha256.GetEnumerator()) {
                    @{ name = $item.Key; sha256 = $item.Value }
                }
            } else {
                $manifest.files
            }

            $checks = foreach ($item in $refs) {
                [ordered]@{
                    caminho = $item.name
                    sha256_declarado = $item.sha256
                    resultado = Test-Entry $entries $item.name $item.sha256 $item.bytes
                }
            }
            if ($stage -eq 12) {
                $known = 'A6_FIXTURE_PROVENANCE.json'
                $hash = $manifest.files_sha256[$known]
                $controls = [ordered]@{
                    caminho_incorreto = Test-Entry $entries 'ausente_teste_a14_26.json' $hash $null
                    hash_incorreto = Test-Entry $entries $known ('0' * 64) $null
                    tamanho_incorreto = Test-Entry $entries $known $hash 0
                }
                if ($controls.caminho_incorreto -cne 'ENTRADA_AUSENTE' -or $controls.hash_incorreto -cne 'HASH_DIVERGENTE' -or $controls.tamanho_incorreto -cne 'TAMANHO_DIVERGENTE') {
                    throw 'CONTRAPROVA_FALHOU'
                }
            }
            [ordered]@{ etapa = "A14.$stage"; zip = $name; sha256_zip = $sha; total_entradas_zip = $entries.Count; referencias = @($checks) }
        } finally {
            $archive.Dispose()
        }
    }

    $previousBytes = Read-Blob 'checkpoints/F3_INT121_A14_25_20261104/EVIDENCIA_A14_25_20261104.json'
    $previous = [Text.Encoding]::UTF8.GetString($previousBytes) | ConvertFrom-Json -AsHashtable
    [ordered]@{
        etapa = 'F3-INT-121 A14.26'
        commit_base = $Base
        estado_operacional = $previous.estado_operacional
        pacotes = @($audits)
        contraprovas = $controls
    } | ConvertTo-Json -Depth 8
} finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp }
}
