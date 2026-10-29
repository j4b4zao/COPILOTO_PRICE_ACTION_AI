# F3-INT-111 — escopo preliminar (não implementado)

Objetivo: revisar adversarialmente a reconciliação offline F3-INT-110 e sua dependência de pins externos.

1. Reproduzir restauração conjunta de DB e pins e documentar impossibilidade de detecção sem referência independente.
2. Testar pins ausentes, trocados, reutilizados, desatualizados e derivados do próprio DB.
3. Testar transição concorrente entre consulta e decisão e repetição após ACK perdido.
4. Testar corrupção, interrupções e fronteiras de durabilidade com respostas fail-closed.
5. Preservar F3 OPEN, sete flags false e todos os checkpoints anteriores.
6. Não alegar autenticação de origem, garantias distribuídas, fencing ou certificação operacional.

Somente candidato após contraexemplos e testes novos.
