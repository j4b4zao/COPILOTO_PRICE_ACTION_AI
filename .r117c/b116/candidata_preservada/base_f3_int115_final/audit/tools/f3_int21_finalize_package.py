"""Package F3-INT-21 audit artifacts without modifying audited sources or tests."""
from hashlib import sha256
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def fingerprint(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    iso = read('RESULTADO_F3_INT21_ISOLATED.json')
    reg = read('RESULTADO_F3_INT21_REGRESSION.json')
    exp = read('RESULTADO_F3_INT21_EXPLORE.json')
    first = read('auditoria_f3_int21_tentativa01/RESULTADO_F3_INT21_REGRESSION.json')
    for record in (iso, reg, exp):
        if not record['complete_runner'] or not record['protected_unchanged']:
            raise ValueError('Incomplete execution or source changes: review before packaging')
    protected = reg['protected_sha256_after']
    for name, expected in protected.items():
        if fingerprint(ROOT / name) != expected:
            raise ValueError('Preexisting protected file changed: ' + name)
    new = [
        'tools/f3_int21_adversarial_support.py',
        'tools/f3_int21_bounded_explorer.py',
        'tools/f3_int21_run_audit.py',
        'tools/f3_int21_finalize_package.py',
        'tests/test_f3_int21_adversarial_recovery.py',
        'TESTE_F3_INT21.txt', 'REGRESSAO_F3_INT21.txt',
        'RESULTADO_F3_INT21_ISOLATED.json', 'RESULTADO_F3_INT21_REGRESSION.json',
        'RESULTADO_F3_INT21_EXPLORE.json',
        'CONTRAEXEMPLOS_F3_INT21_ISOLATED.json', 'CONTRAEXEMPLOS_F3_INT21_REGRESSION.json',
        'EXPLORACAO_F3_INT21.json',
        'auditoria_f3_int21_tentativa01/TESTE_F3_INT21.txt',
        'auditoria_f3_int21_tentativa01/RESULTADO_F3_INT21_ISOLATED.json',
        'auditoria_f3_int21_tentativa01/CONTRAEXEMPLOS_F3_INT21_ISOLATED.json',
        'auditoria_f3_int21_tentativa01/REGRESSAO_F3_INT21.txt',
        'auditoria_f3_int21_tentativa01/RESULTADO_F3_INT21_REGRESSION.json',
        'auditoria_f3_int21_tentativa01/CONTRAEXEMPLOS_F3_INT21_REGRESSION.json',
        'auditoria_f3_int21_tentativa01/f3_int21_adversarial_support.py',
        'RELATORIO_F3_INT21.md', 'CHECKPOINT_F3_INT21.md',
    ]
    manifest_name = 'SHA256_F3_INT21.txt'
    zip_name = 'PACOTE_AUDITORIA_F3_INT21.zip'
    for name in ('RELATORIO_F3_INT21.md', 'CHECKPOINT_F3_INT21.md', manifest_name, zip_name):
        if (ROOT / name).exists():
            raise FileExistsError('Refusing to overwrite final artifact: ' + name)
    old_rows = []
    log_text = (ROOT / 'REGRESSAO_F3_INT21.txt').read_text(encoding='utf-8')
    for match in re.finditer(r'F3_INT(\d+)_REPORT=(\{[^\n]*\})', log_text):
        r = json.loads(match.group(2))
        states = r.get('distinct_states', r.get('states', 'não informado'))
        depth = r.get('depth_effective', 'prefixos canônicos')
        elapsed = r.get('elapsed_seconds', 'não informado')
        stop = r.get('stop_reason', 'cobertura canônica limitada')
        old_rows.append(f'| INT{match.group(1)} | {r["attempted"]} | {states} | {depth} | {elapsed} | {stop} |')
    old_table = '\n'.join(old_rows)
    listing = '\n'.join('- C:\\COPILOTO_GIT_SYNC\\' + n.replace('/', '\\') for n in new + [manifest_name, zip_name])
    checkpoint = f'''# Checkpoint manual — F3-INT-21

Data: 2026-10-20, America/Sao_Paulo. Diretório exclusivo: C:\\COPILOTO_GIT_SYNC.

Auditoria concluída, com achados abertos. Não declarar aprovação integral do modelo F3-INT-20.
- Isolada final: {iso['tests_run']} testes, {iso['failures']} falhas, {iso['errors']} erros, {iso['skipped']} ignorados; exit {iso['exit_code']}.
- Regressão final: {reg['tests_run']} testes, {reg['failures']} falhas, {reg['errors']} erros, {reg['skipped']} ignorados; exit {reg['exit_code']}. Os 127 anteriores concluíram sem falhas; os 24 novos têm 15 aprovações e 9 falhas de expectativa, classificadas no relatório.
- Exploração: {exp['unique_states']} estados distintos, {exp['transitions_completed']} transições completas, {exp['max_extra_depth_reached']} ações extras de profundidade; {exp['elapsed_search_seconds']} s de busca. Parada {exp['stop_reason']}, fronteira {exp['remaining_frontier']}; {exp['violation_edges']} transições com fechamento usando observações obsoletas; zero exceções. Não exaustiva.

Ler RELATORIO_F3_INT21.md, CONTRAEXEMPLOS_F3_INT21_ISOLATED.json, EXPLORACAO_F3_INT21.json e SHA256_F3_INT21.txt. ZIP: C:\\COPILOTO_GIT_SYNC\\{zip_name}. O hash externo do ZIP é informado na resposta final; ZIP e manifesto não se auto-hasheiam.

Prioridade de retomada: rever os cinco achados de fechamento F/P/H/J/L no caminho normal add/reconcile/qualify/close; classificar vereditos relevantes desconhecidos e impedir que sejam aceitos/ignorados. Rever particionamento do inventário por tentativa (bloqueio excessivo). Depois delimitar a API de resolve e decidir como representar commit atômico no simulador. Os três testes de fronteira (A20–A22) não demonstram falha dentro da premissa de chamadas completas atômicas e do chamador confiável.

Nenhuma correção foi feita no modelo F3-INT-20, no Architecture C ou na especificação F3-INT-19. Futuras correções devem ter escopo próprio, preservar os contraexemplos e reexecutar a suíte; não mudar o contrato para fazer os testes passarem. Evidências e resultados F3-INT-20 permanecem byte a byte intactos. Logs iniciais e fixture H anterior foram preservados em auditoria_f3_int21_tentativa01; a versão final H afirma explicitamente NOT_CONTAINED, associated=False, suspended=False e escape_excluded=False.

Reprodução manual, usando Python 3.13.5 disponível:
```
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int21_run_audit.py isolated
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int21_run_audit.py explore
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int21_run_audit.py regression
```
Esses comandos retornam exit 1 quando reproduzem as falhas; isso é resultado da auditoria, não aprovação. Sobrescrevem somente os resultados novos de INT21: preservar versões anteriores e regenerar manifesto/ZIP antes de compartilhar uma reexecução. O finalizador recusa sobrescrever os quatro artefatos finais. A allowlist não executa descoberta geral do projeto.

F3=OPEN. orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false. Nenhuma autorização operacional concedida. Nenhuma API nativa, integração, X3/X4, Profit, Excel, RTD/DDE ou ordem. Não acessar/modificar C:\\COPILOTO_PRICE_ACTION_AI. Resultados e contraexemplos são exclusivamente simulados.
'''
    report = f'''# F3-INT-21 — Auditoria adversarial do modelo simulado de recuperação

Data: 2026-10-20 (America/Sao_Paulo). Auditoria concluída com achados: NÃO há aprovação integral do modelo. F3=OPEN. Nenhuma prova de segurança nativa.

## Escopo e preservação

Foram inspecionados integralmente tools/f3_int20_evidence_recovery_model.py e seus testes, RELATORIO_F3_INT20.md, CHECKPOINT_F3_INT20.md e ESPECIFICACAO_F3_INT19.md. A busca de AGENTS.md no diretório de trabalho não encontrou instruções adicionais. Nenhum código, teste, relatório ou resultado anterior foi alterado. O Architecture C e a especificação permaneceram intactos. O hash do modelo auditado é 4ce2ef2b4461441a6195bec9921cf4f727fa4bae61b5617b73cad8bf671463bc; o da especificação é 13687959d5cf12c200ed3803cd429f72701aa2e0c1ffa4953b88627efa2fa060.

A auditoria adiciona código apenas para testes, exploração, registro e empacotamento. Reutiliza o Harness sintético de INT20 para construir fixtures, mas usa asserções adversariais e obrigações externas de invalidação para julgar o fechamento, sem tomar evaluate().eligible como prova da própria correção. Não há coletor, adaptador operacional, criptografia real, persistência real ou threads/processos concorrentes.

## Resultados reais

| Execução final | Quantidade | Aprovados | Falhas | Erros / ignorados | Exit | Tempo do executor |
|---|---:|---:|---:|---|---:|---:|
| Isolada adversarial | {iso['tests_run']} | {iso['tests_run'] - iso['failures'] - iso['errors']} | {iso['failures']} | {iso['errors']} / {iso['skipped']} | {iso['exit_code']} | {iso['elapsed_runner_seconds']} s |
| Regressão combinada | {reg['tests_run']} | {reg['tests_run'] - reg['failures'] - reg['errors']} | {reg['failures']} | {reg['errors']} / {reg['skipped']} | {reg['exit_code']} | {reg['elapsed_runner_seconds']} s |

A regressão contém os 89 testes anteriores de Architecture C, os 38 testes INT20 e os 24 novos: 151 no total. Os 127 anteriores concluíram sem falhas; as nove falhas estão somente nos testes novos A06, A09–A13 e A20–A22. Nenhuma foi marcada como expectedFailure, ignorada, removida ou convertida em aprovação. A conclusão da execução não significa aprovação de seus resultados. Os JSONs registram IDs, hashes antes/depois, versão do Python, domínio e flags.

Foram realizadas cinco execuções de testes/busca nesta etapa: isolada inicial, exploração limitada, regressão inicial, isolada final e regressão final. A isolada inicial tinha as mesmas nove falhas e zero erros; a regressão inicial executou 151 testes com nove falhas em {first['elapsed_runner_seconds']} s de executor. Seus seis logs/JSONs e a versão anterior do auxiliar foram preservados em auditoria_f3_int21_tentativa01.

A única revisão dos testes após as primeiras execuções tornou H explicitamente contraditório: o primeiro cenário tinha CONTAINED com escape_excluded=False, que poderia ser lido como cobertura insuficiente em vez de negação. O cenário final usa NOT_CONTAINED, associated=False, suspended=False e escape_excluded=False. A falha permaneceu. O contrato e os modelos não foram alterados. A exploração não usa esse ramo H, portanto seu percurso não mudou e não foi repetido apenas por essa revisão da fixture dirigida.

## Achados no caminho normal de evidências e fechamento

Os cinco casos abaixo usam add, reconcile, qualify e close em chamadas completas, sem edição de Store, monkeypatch ou interleaving interno. Todas as evidências adversariais estão registradas no verificador sintético, com fonte independente, identidade/generation corretas e bytes íntegros. Autenticação simulada não resolve contradição semântica.

| ID / teste | Evidência nova | Observado | Exigência conservadora violada |
|---|---|---|---|
| CONFLICT_F / A09 | F: SESSION=UNFENCED por segunda fonte | Sem X; novas J/L permitem CLOSED_RECOVERED apesar da oposição a FENCED | Contradição material de fencing precisa ser rejeitada ou resolvida independentemente antes de fechar |
| CONFLICT_P / A10 | P: mesmo processo=ALIVE, após EXIT conhecido | Sem X; novas J/L permitem fechar | A identidade completa é a mesma; não escolher a saída favorável ignorando a alegação oposta |
| CONFLICT_H / A11 | H: NOT_CONTAINED, associação/suspensão negadas e escape não excluído | Sem X; antiga prova H positiva continua suficiente | Histórico conflitante/incompleto não pode ser superado por snapshot atual de Job vazio |
| J_NONEMPTY_STALE_BARRIER / A12 | J: JOB=NONEMPTY após EMPTY/L e elegibilidade | Depois de START/RECONCILE, QUALIFY/CLOSE reutilizam J/L antigos, sem novas observações | Observação material negativa deve invalidar J e L e impedir fechamento com a barreira anterior |
| L_FAILED_STALE_BARRIER / A13 | L: RESOURCES=FAILED após RELEASED/elegibilidade | Mesmo reuso de J/L; fecha sem cleanup novo | Evidência de falha de limpeza não equivale ao método cleanup_failed: o caminho de mensagens precisa ser igualmente conservador |

Localização no modelo preservado: add trata J/L como OBSERVATION incrementando revision, mas sem incrementar material_revision (linha 448). evaluate agrupa conflitos semânticos apenas para C/U (linhas 518–522). Os demais predicados escolhem provas positivas, e J/L antigos continuam vinculados ao mesmo challenge material. O ticket original já não fecha após mudança de revision; o contraexemplo obtém um ticket NOVO com provas VELHAS. Portanto não é só replay direto de ticket: é requalificação de evidência obsoleta.

Os vereditos negativos não têm enum fechado na implementação. Mesmo que um consumidor os considere fora do vocabulário esperado, aceitá-los como fixtures válidas e ignorar seu significado relevante, permitindo fechamento, não é uma política de rejeição conservadora. Esta auditoria não propõe autorizar novos vereditos na especificação; documenta que o receptor atual não fecha essa fronteira.

## Bloqueio excessivo e fronteiras de abstração

| ID / teste | Resultado | Classificação |
|---|---|---|
| A06_PARTITION_AVAILABILITY / A06 | Duas tentativas com inventários completos e disjuntos, saídas e H completos: C=False | Limitação conservadora de recuperabilidade; não é fechamento inseguro. O código exige todos os known_processes em C de cada tentativa (linha 545), em vez da união/vínculo por tentativa |
| INTRALINE_DOUBLE_COMMIT / A20 | Dois closes retornam True quando o segundo é agendado após as verificações do primeiro e antes da atribuição | Fronteira de atomicidade; não é contraexemplo sob a premissa de que cada método inteiro é uma transição indivisível |
| INTRALINE_STALE_COMMIT / A21 | Segundo recuperador adquire geração 2 na mesma janela; primeiro grava ticket da geração 1 | Mesma fronteira: atomicidade de método não implementa exclusão real ou commit indivisível entre processos |
| DIRECT_RESOLVE_BYPASS / A22 | resolve recebe diretamente prova sem receipt registrado, não incluída no ledger, e remove conflito; depois o fluxo normal fecha | Fronteira da API/chamador confiável. Helper público não exige verify/add/lease e pode registrar ID de resolução que evaluate não encontra no conjunto de evidências |
| CLONED_LEDGER_BOUNDARY / A23 | Cópia isolada de ledger elegível fecha ticket antigo mesmo após geração avançar no ledger vivo | Caracterização aprovada de limite já documentado: não há persistência/autoridade compartilhada entre Stores isolados; não é contabilizada como falha nova |

A20/A21 usam somente sys.settrace para agendar duas sequências Python na linha 623, imediatamente antes de self.s.closure = ticket, sem alterar o arquivo auditado, criar threads ou chamar APIs nativas. O tracer é removido em finally. Essa agenda deliberadamente relaxa a premissa de métodos atômicos; os resultados demonstram por que o simulador não pode certificar concorrência real. A18/A19 verificam que chamadas completas serializadas têm um único vencedor e rejeitam geração obsoleta.

A22 não muda os objetos internos do modelo. Chama um helper sem proteção como API Python; a F3-INT-20 declarou o chamador confiável. Logo o resultado exige delimitar essa superfície, e não alegar invasão do modelo dentro de sua premissa de chamador disciplinado. Nenhuma dessas fronteiras elimina os cinco achados do caminho normal.

## Exploração limitada de estados/transições

| Métrica | Resultado |
|---|---|
| Sementes explícitas | {exp['seeds']} |
| Estados distintos registrados | {exp['unique_states']} |
| Nós selecionados para expansão (ver ressalva abaixo) | {exp['expanded_states']} |
| Transições tentadas / completadas | {exp['transitions_attempted']} / {exp['transitions_completed']} |
| Duplicatas de estado | {exp['duplicate_states']} |
| Exceções | {exp['exceptions']} |
| Profundidade extra efetiva / limite | {exp['max_extra_depth_reached']} / {exp['limits']['max_extra_depth']} |
| Busca / preparação / total | {exp['elapsed_search_seconds']} / {exp['elapsed_setup_seconds']} / {exp['elapsed_total_seconds']} s |
| Motivo de interrupção | {exp['stop_reason']} |
| Fronteira restante | {exp['remaining_frontier']} |
| Arestas com violação / contraexemplos salvos | {exp['violation_edges']} / {exp['saved_counterexamples']} |

Limites configurados: 900 transições, 650 estados, profundidade extra 3, 25 segundos de busca. A busca parou por TRANSITION_LIMIT, não por timeout. A profundidade 3 NÃO foi atingida. Há trabalho não explorado na fronteira; não foi declarada aprovação integral ou exaustividade.

As nove sementes cobrem BLOCKED vazio, COLLECTING, RECONCILED, elegível, fechado, contestado, múltiplas tentativas incompletas e os dois cenários de J/L obsoletos já reconciliados. Os checkpoints completos e os passos de preparação de cada semente constam do JSON. Os dois contraexemplos partem dessas sementes adversariais e têm QUALIFY -> CLOSE como duas ações extras. Sua preparação não é contada como profundidade extra nem como transições da busca; os números não são profundidade absoluta ou contagem total de todas as chamadas de preparação.

O contador expanded_states registra 51 nós selecionados para expansão; o último foi retirado da fila quando o orçamento já estava esgotado e não produziu arestas. Logo 50 nós tiveram transições avaliadas, e o último desses consumiu 18 arestas. Cada transição é uma ação primitiva do scheduler, embora uma ação possa preparar uma fixture antes de chamar add. A chave de deduplicação inclui Store, evidências, receipts, fontes, histórico/audit, token/lease, ticket, serial e obrigações externas de renovação. Exclui somente endereço de objetos e prefixes diagnósticos do Harness. Não se somam esses estados aos dos exploradores anteriores como estados globais únicos.

EXPLORACAO_F3_INT21.json conserva os nove checkpoints, limites, ações, tempos, motivo de parada, fronteira e dois snapshots/percursos violadores. Os casos dirigidos adicionais de conflito, inventários e fronteiras de concorrência não estão todos abrangidos por essa pequena busca.

## Cobertura dos dez eixos solicitados

| Eixo | Exercício realizado e resultado |
|---|---|
| Reinício durante coleta/fechamento | A01/A02 com mesmo ledger preservam dados e ticket; A23 caracteriza snapshot isolado sem durabilidade |
| Replay/gerações obsoletas | A03/A04/A19; replay idêntico idempotente, lease antigo e evidência reidentificada de geração antiga rejeitados; A21 mostra limite de agenda intramétodo |
| Múltiplas criações/inventário | A05/A07: duas falhas definitivas recuperam e incompleto bloqueia; A06 encontra bloqueio excessivo com particionamento completo |
| Conflitos autenticados simulados | A08 confirma bloqueio C/U mesmo com repetição; A09–A11 falham para F/P/H |
| Recuperadores/commits simultâneos | A18/A19 passam sob serialização; A20/A21 falham na agenda intramétodo e delimitam a abstração |
| Invalidação de J/limpeza | A14 passa usando cleanup_failed; A12/A13 falham pelo caminho de evidências |
| Tardios entre elegibilidade e fechamento | A15 filho tardio aborta ticket e conserva X; mensagens J/L negativas produzem os contraexemplos |
| Contestação após CLOSED_RECOVERED | A16 conserva ticket/fase terminal e registra contestação externa, confiança=false |
| Revogação/admissão | Harness.check e checagens de cada transição verificam sessão original imutável, revoked/admission_closed verdadeiros e flags false |
| Falha/cancelamento/timeout versus sucesso | A17 cobre FAILED/CANCELLED/TIMEOUT/COMPLETED; resultados preservados, aggregate_success=false e nenhuma autorização de execução |

Não foram observadas alterações de autorização ou dos sete flags nos percursos executados, inclusive nos contraexemplos de fechamento documental. Isso não compensa fechamento documental indevido nem prova invariantes em estados não explorados.

## Regressão anterior e interrupções

A linha de base anterior foi efetivamente reexecutada pelo runner INT21, que não sobrescreve nenhum log de INT20. A regressão combinada completou; não houve interrupção do executor geral. Exploradores antigos mantêm seus próprios limites internos: o INT13 pode parar por DURATION_LIMIT a 40 segundos sem que o unittest deixe de concluir. Nesta regressão final, os números efetivamente impressos foram:

| Explorador | Tentativas | Estados reportados | Profundidade publicada | Tempo publicado (s) | Parada |
|---|---:|---|---|---|---|
{old_table}

INT13 interrompeu sua exploração por DURATION_LIMIT, sem esgotar o orçamento de 180000 transições; os outros testes e o executor geral concluíram. Os relatórios JSON impressos estão integralmente em REGRESSAO_F3_INT21.txt; esse limite não deve ser confundido com aprovação exaustiva da linha de base ou com um timeout global da auditoria. Não foi alterado qualquer orçamento antigo para obter um resultado favorável.

As cinco execuções usaram Python 3.13.5 com -B. Comandos: tools/f3_int21_run_audit.py isolated (duas vezes), explore (uma vez) e regression (duas vezes), todos a partir de C:\\COPILOTO_GIT_SYNC. Exit 1 foi esperado como resultado real das asserções adversariais falhas e da busca que achou violações; não foi mascarado. Zero erros de execução nos testes novos e zero exceções na busca.

## Entrega e integridade

Arquivos novos completos, incluindo versões intermediárias preservadas:

{listing}

Nenhum arquivo preexistente foi alterado. O manifesto usa caminhos relativos portáveis e inclui todos os arquivos do pacote exceto ele próprio; o ZIP inclui o manifesto. O ZIP preserva a estrutura relativa e contém também os 25 artefatos de referência de INT20 necessários à revisão/reprodução (modelos, testes, runner, especificação, relatórios, resultados e manifesto anterior). Não inclui um ZIP anterior dentro de outro.

O empacotador compara cada entrada descomprimida aos bytes de origem, testa CRC e verifica novamente os hashes protegidos. O SHA-256 externo do ZIP e o hash do manifesto são informados na saída final, evitando auto-referência circular. Não há assinatura de procedência; hashes verificam consistência dos bytes.

F3=OPEN; orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false. Nenhuma integração, API nativa de supervisão/contenção, X3/X4, Profit, Excel, RTD/DDE ou ordens foi executada. C:\\COPILOTO_PRICE_ACTION_AI não foi acessado nem modificado. Todos os achados são do domínio SIMULATED.

## Retomada

Auditoria F3-INT-21 concluída, correções não implementadas. Há achados abertos que impedem declarar validação integral do modelo. Retomar pelo CHECKPOINT_F3_INT21.md e pelos contraexemplos; decidir correções sob escopo próprio sem reduzir as guardas da F3-INT-19. Preservar as evidências e restrições. Nenhum passo operacional está autorizado.
'''
    (ROOT / 'RELATORIO_F3_INT21.md').write_text(report, encoding='utf-8')
    (ROOT / 'CHECKPOINT_F3_INT21.md').write_text(checkpoint, encoding='utf-8')
    names = sorted(set(protected) | set(new))
    before = {n: fingerprint(ROOT / n) for n in names}
    (ROOT / manifest_name).write_text(''.join(before[n] + '  ' + n + '\n' for n in names), encoding='utf-8')
    names.append(manifest_name)
    before[manifest_name] = fingerprint(ROOT / manifest_name)
    with zipfile.ZipFile(ROOT / zip_name, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name in names:
            package.write(ROOT / name, arcname=name)
    with zipfile.ZipFile(ROOT / zip_name, 'r') as package:
        if package.namelist() != names or package.testzip() is not None:
            raise ValueError('ZIP names/CRC verification failed')
        for name in names:
            if sha256(package.read(name)).hexdigest() != before[name] or fingerprint(ROOT / name) != before[name]:
                raise ValueError('Byte mismatch during packaging: ' + name)
    for name, expected in protected.items():
        if fingerprint(ROOT / name) != expected:
            raise ValueError('Protected artifact changed after packaging: ' + name)
    print(json.dumps({'zip': str(ROOT / zip_name), 'sha256_zip': fingerprint(ROOT / zip_name),
                      'sha256_manifest': before[manifest_name], 'zip_entries': len(names),
                      'zip_bytes': (ROOT / zip_name).stat().st_size, 'all_entries_verified': True,
                      'protected_unchanged': True, 'F3': 'OPEN', 'audit_approved': False}, indent=2))


if __name__ == '__main__':
    main()