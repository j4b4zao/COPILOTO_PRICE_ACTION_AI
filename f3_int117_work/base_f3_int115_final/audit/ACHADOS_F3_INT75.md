# Inventario fechado de fontes

A pre-revisao identificou que source_path no marco 74 exclui nomes de mais de
512 caracteres e so reconhece prefixos tests/ e tools/ e extensao .py exatos.
Omitir silenciosamente esses nomes do inventario permitiria alteracoes sem delta
nessas entradas. As contraprovas sinteticas cobrem caminho longo, TOOLS/ e .PY.

O marco 75 adiciona verify_guarded_lineage, que rejeita essas entradas antes da
verificacao 74. Nao altera o verificador historico nem afirma regras universais
de importacao ou de filesystem. Use a fachada guardada nas verificacoes novas.
Razoes declaradas continuam sendo anotacoes do chamador, nao autorizacao real.
