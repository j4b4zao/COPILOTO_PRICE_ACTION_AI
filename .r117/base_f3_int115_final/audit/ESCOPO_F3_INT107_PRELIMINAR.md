# F3-INT-107 — escopo preliminar

Revisar os contratos de evidências tipadas (F3-INT-105/106) e os vínculos de contexto (F3-INT-103/104) antes de implementar novas validações.

Priorizar uma lacuna comprovada por testes adversariais; evitar duplicar verificações de identidade, hash, ordem e limite de lote.

Qualquer implementação futura deve ser offline, determinística, sem I/O operacional, sem autenticação presumida e sem alterar flags.

Estado F3=OPEN; os sete bloqueios permanecem false.
