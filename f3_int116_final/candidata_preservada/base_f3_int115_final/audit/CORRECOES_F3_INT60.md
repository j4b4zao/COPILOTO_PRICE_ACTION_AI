# Pre-validacao do verificador

A primeira pre-validacao teve 22 testes, 1 falha: test_unsafe_paths esperava
UNSAFE_OR_DUPLICATE_ARCHIVE_NAME e recebeu MANIFEST_COVERAGE_MISMATCH para
a fixture com barra invertida. O construtor ZipInfo no Windows normalizava
o nome antes de grava-lo. A fixture foi corrigida para definir filename
diretamente e preservar o caminho adversarial. O verificador tambem compara
orig_filename e filename, rejeitando nomes normalizados durante a leitura.

A primeira chamada de pre-validacao do marco 57 foi feita a partir do workspace,
fora da raiz da copia preview: falhou em importar tools, antes de executar os
testes. A chamada foi corrigida para usar work/preview como diretorio. Nenhum
checkpoint foi produzido por essa tentativa. As execucoes oficiais de cada marco
usam a raiz work/audit e sao as evidencias nos logs de ciclo correspondentes.
