# Retomada da auditoria F3 isolada

Leia ULTIMO_MARCO.json e o CHECKPOINT correspondente. last_completed identifica
o ultimo marco concluido; next_step indica a continuacao proposta. O ciclo so
atualiza o checkpoint apos testes novos e regressao sem falhas, erros ou skips.
Regressao integral significa todos os testes em tests/ deste pacote, nao a suite
operacional do repositorio pai.

## Origem desta continuacao

PACOTE_AUDITORIA_F3_INT52_LOCAL.zip foi copiado para area isolada no workspace.
Os 215 hashes do manifesto 52 foram conferidos e a base passou novamente em
526/526 testes. ORIGEM_F3_INT53.json registra SHA256 e origem. O pacote 53 do chat
nao estava acessivel: o marco 53 foi implementado novamente sobre o 52, com
22 testes novos e regressao de 548 testes. Nao e recuperacao dos arquivos do
marco 53 originalmente mencionado no chat. ZIPs novos preservam cada marco.

## Restricoes permanentes

F3=OPEN. Preserve false em orders_allowed, live_certified, flow_complete,
f3_resolved, native_prototype_authorized, strict_deadline_guaranteed e
authenticated_witness_verified. Apenas fixtures offline e simuladas. Sem Profit,
Excel, RTD/DDE, rede operacional, adaptadores reais, testemunhas reais ou ordens.
Sem certificacao. Nao execute scripts operacionais do repositorio pai.

Pins, snapshots, votos, historicos, propostas e geracoes sao controlados pelo
chamador. Igualdade de snapshots e contadores locais nao oferecem fencing nativo,
autenticacao, persistencia confiavel ou consenso real. Reposicao integral de
estado pelo chamador pode tornar replay indetectavel. Limites de exploracao nao
sao garantias de prazo ou exaustividade. Monitores de invariantes verificam
condicoes necessarias; nao substituem replay nem autenticam testemunhos.

## Execucao e evidencias

Python usado: C:\Users\jb\AppData\Local\Programs\Python\Python313\python.exe

Na raiz extraida, tools/f3_audit_lifecycle.py recebe numero de etapa, descricao e
proxima etapa. Executa testes test_f3_intN*.py e todos os test*.py. Gera logs,
relatorio, checkpoints, manifesto SHA256 e ZIP na pasta pai, com .zip.sha256.
Verifica CRC do ZIP e hashes internos. Copie ZIP e sidecar para outputs/ apos
concluir o ciclo. Preserve pacotes anteriores.

Fachadas de ingestao limitada: marcos 56 e 58. Pontos legados continuam disponiveis
sem esses limites globais; use as fachadas para entradas adversariais. Contagem
de nos limita o percurso, nao a alocacao previa do chamador. Ver NOTA_F3_INT56.md.

Verificadores de pacote: 60 (integridade), 61 (portabilidade de nomes),
62 (JSON e logs estritos). SHA256 confere integridade contra o digest fornecido;
nao autentica origem nem atesta veracidade independente de logs.

Correcoes de expectativas e chamadas de pre-validacao estao em CORRECOES_F3_INT*.md.
Logs oficiais do ciclo sao as evidencias de cada checkpoint. Pre-validacoes em
copias temporarias nao concluem marcos.
