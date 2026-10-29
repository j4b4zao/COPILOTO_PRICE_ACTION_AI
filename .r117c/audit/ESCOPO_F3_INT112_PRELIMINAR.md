# F3-INT-112 — escopo preliminar, não implementado

Base: F3-INT-111 FINAL, F3 OPEN, sete bloqueios false.

1. Definir identidade e cadeia de custódia da referência independente (pin), inclusive provisionamento, revogação, recuperação e falhas; sem pressupor origem autenticada.
2. Construir contraexemplos offline para falha de retenção de pin após commit, ACK perdido e recuperação conservadora, sem duplicação de consumo.
3. Explorar contenção multiprocesso SQLite, TOCTOU e fronteiras entre consulta e consumo; explicitar ausência de fencing entre hosts.
4. Separar crash de processo, desligamento e perda física de armazenamento; documentar limites de evidência offline.
5. Verificar correspondência entre pacote e arquivos testados via inventário reproduzível; hash isolado não autentica executor.

Nenhuma alteração operacional; nenhuma certificação; não marcar FINAL sem regressão completa.
