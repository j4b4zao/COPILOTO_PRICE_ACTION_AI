# Bundle de replay offline

EXEMPLO_BUNDLE_F3_INT90.witnessbundle contem bytes ZIP com witness.json,
bundle_manifest.json e um catalogo fechado de pacotes. Nada e extraido em disco.
Extensao distinta evita aninhar automaticamente ZIPs historicos no empacotador.
O sidecar .sha256 registra o digest do bundle; hashes sao pins do chamador.

A ordem de gravacao e os metadados do ZIP externo sao fixos, incluindo timestamp
1980-01-01. Isso permite repetibilidade local dos bytes, sem atestar data real de
criacao e sem prometer igualdade entre todas as versoes de compressao.

O decoder limita arquivos, bytes ZIP/descomprimidos e tamanho dos JSONs; rejeita
entradas inesperadas, duplicadas, links, criptografia, caminhos fora do esquema
e cobertura incompleta. Verifica hashes antes do replay completo. O corpus de
mutacoes e finito e nao prova ausencia de todas as falhas de parser.
