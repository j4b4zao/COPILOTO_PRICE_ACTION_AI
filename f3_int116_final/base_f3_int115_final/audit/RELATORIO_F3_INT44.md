# F3-INT-44 — Auditoria simulada de composição de testemunhas

- 16 novos testes; regressão total 368/368.
- Simulados: conjunto fixado por época, mudanças de composição, duplicatas, testemunhas não membros, comprometimento declarado, suspeita de conluio e limiar de votos.
- Limitação essencial: identidades, suspeitas, independência e âncora de época são metadados controlados pelo chamador. Um quorum simulado não demonstra autenticidade, independência real, consenso ou durabilidade.
- Nenhuma integração operacional, negociação, certificação nativa ou fechamento. F3=OPEN; sete flags de segurança false.
