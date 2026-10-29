# Retomada da auditoria F3 isolada

Leia ULTIMO_MARCO.json e o CHECKPOINT correspondente antes de alterar codigo.
O ultimo marco so e registrado pelo fluxo quando testes novos e regressao passam.
Confirme tambem a existencia do ZIP e seu arquivo .zip.sha256 fora desta pasta.

Origem: PACOTE_AUDITORIA_F3_INT49_CHAT.zip em Downloads. Seu manifesto de
183 arquivos foi conferido sem divergencias. ORIGEM_F3_INT49.json registra o hash.
Nenhum arquivo recebido dessa origem foi alterado neste ciclo.

F3=OPEN. Preserve em false: orders_allowed, live_certified, flow_complete,
f3_resolved, native_prototype_authorized, strict_deadline_guaranteed,
authenticated_witness_verified. Nao conecte rede, Profit, Excel, RTD/DDE,
adaptadores reais, testemunhas reais ou sistemas de ordens.

A regressao integral aqui significa todos os testes do pacote isolado em tests/.
A suite operacional do repositorio pai nao pertence a este fluxo.
Os estados, historicos, votos, pins e digests sao fixtures do chamador; podem ser
substituidos pelo chamador. Nao ha certificacao, autenticacao, consenso real,
persistencia confiavel ou fencing nativo. Testes com exploracao limitada nao sao
prova de exaustividade. Os limites de tempo historicos influenciam a cobertura.

Na F3-INT-53, implementar intercalacoes adversariais de recuperacoes concorrentes
sobre o mesmo snapshot simulado. Exercitar propostas concorrentes, commit sobre
snapshot obsoleto, conflito de ramo, rejeicao atomica e limites de exploracao.
Nao tratar igualdade de snapshots como protecao real contra concorrencia.

Use o Python local disponivel nesta maquina:
C:\Users\jb\AppData\Local\Programs\Python\Python313\python.exe

Execute os testes a partir desta pasta. O utilitario tools/f3_audit_lifecycle.py
recebe numero de etapa, descricao e proxima etapa; executa testes especificos e
toda a regressao, exige ausencia de falhas/erros/skips, gera relatorio, checkpoint,
logs, manifesto e ZIP, e confere o manifesto dentro do ZIP. Execute-o apenas
depois de implementar o modulo e os testes da etapa seguinte. Nao execute scripts
operacionais do repositorio pai. Preserve os ZIPs das etapas anteriores.

Falhas corrigidas neste ciclo estao documentadas em CORRECOES_F3_INT51.md e
CORRECOES_F3_INT52.md, com os logs iniciais preservados.
