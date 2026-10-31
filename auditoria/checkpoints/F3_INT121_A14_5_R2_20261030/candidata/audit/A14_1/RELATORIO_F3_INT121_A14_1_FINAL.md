# F3-INT-121 A14.1 — Fechamento documental (29/10/2026)

**Estado:** FINAL DOCUMENTAL, F3=OPEN, simulação offline. Nenhuma operação real autorizada.

## Evidências recebidas do Windows
- Regressão normal: 170 testes, 311,906 s, OK.
- Regressão Python -O: 170 testes, 424,319 s, OK.
- Contraprova A13: `negative_control_detected=true` em ambas as execuções.
- A14.1: antes do commit de consumo e depois do ACK local, `active_processes_before_safety=0`, `safety_cleanup_confirmed=true` em ambas.

## Escopo e limites
Os resultados foram **informados por logs do usuário**, não reexecutados de forma independente neste ambiente. A14.1 reutiliza as fronteiras A12; não demonstra cobertura exaustiva de corridas, durabilidade física, autenticação externa ou prontidão operacional. O manifesto de SHA-256 protege contra alterações relativas ao próprio pacote, sem autenticar sua origem.

## Continuação proposta
A14.2: revisar o escopo de detecção de sobrevivência indevida dos descendentes e preparar testes isolados. Implementação futura requer validação; preservar o código operacional.
