# BookDiagnostics RC28 — Non-Invasive Core Receivers

RC28 adiciona receptores reais para os contratos RC27 de `EVIDENCE`, `CONTEXT` e `CHECKLIST`.

Objetivos:
- armazenar contratos tipados em estruturas de leitura;
- expor snapshot para dashboard/assistente;
- contar cautelas e bloqueios de checklist apenas como informação;
- manter `readonly=True` e `affects_decision=False` como invariantes obrigatórias;
- rejeitar qualquer origem que não seja RC27;
- manter `RISK` explicitamente bloqueado.

RC28 não escreve em Strategy, Score, Risk, Decision ou Alert. Os receptores são read models não invasivos e podem ser limpos sem alterar o núcleo operacional.
