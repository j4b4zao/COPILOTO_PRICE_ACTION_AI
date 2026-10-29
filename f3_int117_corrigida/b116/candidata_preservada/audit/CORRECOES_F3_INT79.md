# Fixture de alias corrigida

A pre-validacao inicial teve 12 testes, 1 falha em test_source_alias. A fixture
adicionava TOOLS/model.py a um ZIP que ja continha tools/model.py. A verificacao
de portabilidade rejeitava a colisao antes do inventario, como esperado pela
ordem dos contratos. O caso de alias passou a usar TOOLS/alias.py, e um teste
separado conserva a contraprova de colisao. Nenhuma aceitacao foi relaxada.
