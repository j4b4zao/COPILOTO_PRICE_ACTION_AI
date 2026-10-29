# Schema 2 de testemunhos com politica explicita

O formato de referencias schema=2 inclui max_files e max_bytes no snapshot
inicial. Os traces sao reconstruidos pelo modelo 95 e conferidos integralmente,
incluindo a politica. Limites e tipos sao verificados antes da importacao.

O catalogo permanece externo: ate 48 pacotes e 32MiB, com SHA256 e etapa exatos,
sem duplicatas ou registros nao usados. O JSON usa os limites fechados do codec
70 e nao instancia classes fornecidas pelo chamador. Schemas 1 e 2 sao distintos;
o codec historico nao aceita automaticamente este formato.

Os EXEMPLO_* associados sao fixtures sinteticas, nao checkpoints de auditoria.
Politica e pins sao dados do chamador. Consistencia de replay nao autentica
origem, nao implementa fencing e nao autoriza sistemas reais. F3 OPEN e flags false.
