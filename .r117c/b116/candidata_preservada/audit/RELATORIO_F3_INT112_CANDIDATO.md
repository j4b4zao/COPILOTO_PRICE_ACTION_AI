# F3-INT-112 CANDIDATO — inventário offline

Base: F3-INT-111 FINAL (não alterada). F3 OPEN; sete bloqueios false.

Entregue: módulo read-only `tools/f3_int112_snapshot_inventory.py` e 12 testes adversariais. Inventário compara hashes SHA-256, detecta arquivos ausentes, extras, alterados e links simbólicos; não autentica origem nem comprova identidade do executável no Windows. Contraexemplo: substituição coordenada de arquivos e inventário gera MATCH_UNAUTHENTICATED. O inventário deve ser retido e verificado independentemente; hashes derivados do mesmo pacote não são evidência independente. Há janela TOCTOU, não existe snapshot atômico contra escritor malicioso.

Resultado local: 12/12 testes novos aprovados em Linux. Regressão Windows completa pendente. Este marco é parcial: custódia, revogação de pin, ACK perdido, contenção multiprocesso, durabilidade física e autenticidade de origem permanecem abertos. Não há certificação ou autorização de ordens.
