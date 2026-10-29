# F3-INT-113 FINAL — consolidação offline com ressalva

- Base: F3-INT-112 FINAL; todos os 770 arquivos anteriores preservados byte a byte.
- 13/13 testes específicos aprovados localmente.
- Regressão Windows informada: 1370 testes, 1369 aprovados, 1 ignorado, 0 falhas, 0 erros, 580.917 segundos.
- Teste ignorado: `test_symlink_rejected` (criação de link simbólico não permitida no Windows). O cenário foi executado no Linux na etapa anterior; não foi validado no Windows.
- Evidência recebida: `RESULTADO_F3_INT113.txt`, SHA-256 `36576ab9a50ba2fcd3629044a6e304c61029379ef1a689547ba9f2357687127a`.
- Hashes do código: {"tools/f3_int113_execution_snapshots.py": "25c843e17e345fbbf3a55ce11823e4085b0483d9d4a71cec84009141fb9502da", "tests/test_f3_int113_execution_snapshots.py": "81b1dcd3f75a9ff7d1ae7fb2165197bf72e839f0db5ca3e13dd267f882f49414"}.
- Não há código de saída do processo nem atestado independente de correspondência entre arquivos executados e pacote.
- F3 OPEN; sete bloqueios false; nenhuma autorização de operação real.
- Conclusão: FINAL apenas para o escopo de testes offline, sem autenticação, custódia externa, garantia de durabilidade, fencing entre hosts ou certificação live.
