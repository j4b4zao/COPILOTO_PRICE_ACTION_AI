# Limites explicitos de envelopes

Os verificadores historicos 60 a 77 conservam suas regras e limites. O marco 78
introduz um verificador integrado com resultado imutavel e EnvelopePolicy:
default de 512 arquivos, teto configuravel de 2048, no maximo 64MiB de bytes ZIP
e de tamanhos descomprimidos somados. A contagem de testes da evidencia fica
limitada a dez milhoes. Tipos bool em limites e contagens sao rejeitados.

O marco 79 verifica ate 128 pacotes e 128MiB agregados sem perder a comparacao
de fontes entre pacotes. As alteracoes declaradas exigem hashes antes/depois,
etapa e caminho exatos; remocoes permanecem rejeitadas. Razoes nao autorizam
operacoes. O verificador de envelopes mantem JSON/logs estritos, nomes portaveis,
manifesto integral, inventario fechado e os sete flags false.

A copia de entregaveis usa politica explicita de 1024 arquivos por pacote para
permitir crescimento do arquivo historico da auditoria. Esse parametro consta
em VERIFICACAO_LINHAGEM.json. Nao representa ampliacao de permissao operacional,
autenticacao de origem ou certificacao. Os limites nao sao garantias de prazo.
