# Referencias JSON e catalogo de pacotes

O JSON schema=1 referencia pacotes por etapa e SHA256; os bytes sao fornecidos em
catalogo separado. O catalogo e limitado a 48 registros e 32MiB, sem hashes
duplicados ou registros nao utilizados. Cada referencia exige correspondencia
exata com o registro. Os eventos sao reexecutados e os traces completos conferidos.

O exemplo JSON acompanha EXEMPLO_CATALOGO_F3_INT89.json e dois arquivos .package,
que sao bytes ZIP de fixtures sinteticas. As contagens internas dessas fixtures
nao sao os checkpoints reais da auditoria. Use apenas como dados de teste.

Este formato cobre o modelo de importacao 83 com seu limite padrao. Nao implica
serializacao automatica de outros modelos de politica. Nao carrega classes ou
abre caminhos de pacote no filesystem. Pins e catalogo sao controlados pelo
chamador, sem autenticacao de origem ou certificacao.
