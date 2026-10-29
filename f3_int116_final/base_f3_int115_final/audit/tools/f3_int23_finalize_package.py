"""F3-INT-23 evidence packaging. Does not execute tests or edit audited sources."""
import ast
import difflib
from hashlib import sha256
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'tools/f3_int20_evidence_recovery_model.py'
HARNESS = 'tests/test_f3_int20_evidence_recovery.py'
CHANGED = (MODEL, HARNESS)


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def fp(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    before = read('RESULTADO_F3_INT23_BEFORE.json')
    critical = read('RESULTADO_F3_INT23_CRITICAL.json')
    specific = read('RESULTADO_F3_INT23_SPECIFIC.json')
    combined = read('RESULTADO_F3_INT23_COMBINED.json')
    exp = read('RESULTADO_F3_INT23_EXPLORE.json')
    for r in (critical, specific, combined, exp):
        if not r['source_unchanged_during_run'] or not r['prior_test_ast_preserved'] or not r['complete_runner']:
            raise ValueError('Incomplete execution, changes during run or altered prior test methods')
    if before['failures'] != 3 or critical['failures'] or specific['failures']:
        raise ValueError('Critical reproduction/fix not verified')
    if combined['tests_run'] != 197 or combined['failures'] != 1 or combined['errors']:
        raise ValueError('Unexpected final regression; review before packaging')
    if 'test_A06_' not in combined['failed_ids'][0]:
        raise ValueError('An additional defect remains; report must be reviewed')
    prior_zip = 'PACOTE_AUDITORIA_F3_INT22.zip'
    if fp(ROOT / prior_zip) != 'd062d6bf566357c8b41a5147f8e42087e3bb12c72c53482931264de5090a6ef3':
        raise ValueError('Immutable INT22 review package changed')
    protected = combined['sha256_after']
    for name, value in protected.items():
        if fp(ROOT / name) != value:
            raise ValueError('Artifact changed after run: ' + name)
    for r in (critical, specific, combined, exp):
        if r['model_sha256'] != fp(ROOT / MODEL) or r['harness_sha256'] != fp(ROOT / HARNESS):
            raise ValueError('Executions used different final source bytes')
    new = [
        'tools/f3_int23_run_audit.py', 'tools/f3_int23_bounded_explorer.py', 'tools/f3_int23_finalize_package.py',
        'tests/test_f3_int23_commit_resolution.py',
        'auditoria_f3_int23_antes/' + MODEL, 'auditoria_f3_int23_antes/' + HARNESS,
        'TESTE_F3_INT23_BEFORE.txt', 'RESULTADO_F3_INT23_BEFORE.json', 'CONTRAEXEMPLOS_F3_INT23_BEFORE.json',
        'TESTE_F3_INT23_CRITICAL.txt', 'RESULTADO_F3_INT23_CRITICAL.json', 'CONTRAEXEMPLOS_F3_INT23_CRITICAL.json',
        'TESTE_F3_INT23_SPECIFIC.txt', 'RESULTADO_F3_INT23_SPECIFIC.json', 'CONTRAEXEMPLOS_F3_INT23_SPECIFIC.json',
        'TESTE_F3_INT23_COMBINED.txt', 'RESULTADO_F3_INT23_COMBINED.json', 'CONTRAEXEMPLOS_F3_INT23_COMBINED.json',
        'EXPLORACAO_F3_INT23.json', 'RESULTADO_F3_INT23_EXPLORE.json',
        'ALTERACOES_MODELO_F3_INT23.diff', 'ALTERACOES_AUXILIAR_F3_INT23.diff',
        'RELATORIO_F3_INT23.md', 'CHECKPOINT_F3_INT23.md',
    ]
    final_targets = ('RELATORIO_F3_INT23.md', 'CHECKPOINT_F3_INT23.md', 'SHA256_F3_INT23.txt',
                     'PACOTE_AUDITORIA_F3_INT23.zip', 'ALTERACOES_MODELO_F3_INT23.diff', 'ALTERACOES_AUXILIAR_F3_INT23.diff')
    if any((ROOT / name).exists() for name in final_targets):
        raise FileExistsError('Refusing to overwrite final artifact')
    for name, diff_name in zip(CHANGED, ('ALTERACOES_MODELO_F3_INT23.diff', 'ALTERACOES_AUXILIAR_F3_INT23.diff')):
        old = ROOT / 'auditoria_f3_int23_antes' / name
        if fp(old) != before['sha256_before'][name]:
            raise ValueError('Before source snapshot differs')
        delta = ''.join(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True),
                     (ROOT / name).read_text(encoding='utf-8').splitlines(True),
                     fromfile='antes/' + name, tofile='depois/' + name))
        (ROOT / diff_name).write_text(delta, encoding='utf-8')
    listing = '\n'.join('- C:\\COPILOTO_GIT_SYNC\\' + n.replace('/', '\\')
                        for n in new + ['SHA256_F3_INT23.txt', 'PACOTE_AUDITORIA_F3_INT23.zip'])
    metrics = []
    log = (ROOT / 'TESTE_F3_INT23_COMBINED.txt').read_text(encoding='utf-8')
    for match in re.finditer(r'F3_INT(\d+)_REPORT=(\{[^\n]*\})', log):
        r = json.loads(match.group(2))
        metrics.append(f'| INT{match.group(1)} | {r["attempted"]} | '
                       f'{r.get("distinct_states", r.get("states", "não informado"))} | '
                       f'{r.get("depth_effective", "prefixos canônicos")} | '
                       f'{r.get("elapsed_seconds", "não informado")} | '
                       f'{r.get("stop_reason", "cobertura canônica limitada")} |')
    table = '\n'.join(metrics)
    checkpoint = f'''# Checkpoint manual — F3-INT-23

Data: 2026-10-20, America/Sao_Paulo. Workspace exclusivo C:\\COPILOTO_GIT_SYNC.

A20/A21/A22 foram reproduzidos antes das edições (3 testes, 3 falhas, zero erros) e agora passam (3/3). Registros e fonte anteriores preservados. 24/24 testes específicos novos passaram. Regressão completa: 197 testes = 151 originais + 22 INT22 + 24 INT23; 196 aprovações, uma falha A06, zero erros/ignorados; exit 1. Não declarar aprovação integral: A06 permanece separado como bloqueio excessivo do inventário por tentativa.

Busca limitada: {exp['unique_states']} estados distintos; {exp['transitions_completed']} ações completadas; profundidade EXTRA {exp['max_extra_depth_reached']}; {exp['elapsed_search_seconds']} s de busca; {exp['stop_reason']}; fronteira {exp['remaining_frontier']}; zero violações/exceções; quatro agendas intramétodo efetivamente executadas. Sementes e percursos em EXPLORACAO_F3_INT23.json. Não é prova exaustiva.

Correções: Store possui um gate por geração/token/revisão. A decisão COMMIT versus FENCED usa uma única operação dict.setdefault como primitiva indivisível declarada do scheduler simulado. Mudanças materiais e de geração selam o gate antigo antes de alterar estado; somente o vencedor publica o fechamento. Decisão que ganhou antes de evento posterior é preservada e contestada externamente, sem reativação. resolve exige lease atual, bytes previamente admitidos em add, reverificação no oracle, fonte independente autorizada, cobertura, explicação e alvos explícitos. Indicadores booleanos, prova apenas registrada ou helper sem admissão não retiram X.

Dois arquivos preexistentes alterados:
- {MODEL}; hash {combined['model_sha256']}.
- {HARNESS}; hash {combined['harness_sha256']}. Somente Harness.eligible e Harness.finish foram totalizados para retornar false/None quando guardas rejeitam; todos os métodos/asserts dos testes anteriores preservados por comparação AST, e os outros arquivos de teste intactos. A22 já é bloqueado na reconciliação, antes do close, portanto o auxiliar anterior não suportava esse caminho negativo correto.

Ler RELATORIO_F3_INT23.md, os dois diffs ALTERACOES_*_F3_INT23.diff, CONTRAEXEMPLOS_F3_INT23_BEFORE.json, CONTRAEXEMPLOS_F3_INT23_COMBINED.json e SHA256_F3_INT23.txt. ZIP: C:\\COPILOTO_GIT_SYNC\\PACOTE_AUDITORIA_F3_INT23.zip; inclui referências completas e pacote INT22 original imutável. Hash externo do ZIP informado na resposta final, sem auto-referência no manifesto.

Limites: um gate compartilhado por Store em memória, sem persistência, processos ou threads reais, sem prova de atomicidade Windows. Stores clonados não compartilham autoridade; chamador/fixture registry continuam confiáveis. O ponto de linearização é a decisão do gate, não a ordem dos returns. A aquisição de geração posterior ao COMMIT não anula retroativamente decisão já válida, mas contesta a conclusão. F3-INT-19 inalterada; implementação concretiza sua exigência de commit indivisível sem alterar o contrato normativo.

Próxima auditoria: manter A06 aberto; revisar inventário multitentativa e ampliar exploração limitada sob novo escopo. Não afrouxar testes ou contrato para fazer A06 passar. Nenhuma correção operacional autorizada.

Reprodução manual no workspace, Python 3.13.5, -B:
```
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int23_run_audit.py critical
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int23_run_audit.py specific
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int23_run_audit.py combined
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int23_run_audit.py explore
```
combined retorna exit 1 exclusivamente por A06. Preservar resultados antes de repetir, pois o runner sobrescreve somente os resultados INT23; regenerar manifesto/ZIP após reexecução. Runners antigos continuam vinculados aos hashes históricos e devem ser usados apenas em restauração separada do pacote correspondente.

F3=OPEN; orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false. Architecture C, especificação e componentes operacionais intactos. Não executar APIs nativas, ordens, Profit, Excel RTD/DDE, X3/X4 ou protótipos nativos. Não acessar/modificar C:\\COPILOTO_PRICE_ACTION_AI. Simulação não comprova segurança nativa.
'''
    report = f'''# F3-INT-23 — Arbitragem documental e resolução verificada no simulador

Data: 2026-10-20 (America/Sao_Paulo). A20, A21 e A22 corrigidos nos cenários reproduzidos. A06 continua aberto; não há aprovação integral do modelo. F3=OPEN e sete flags operacionais=false.

## Reprodução anterior e causas

A leitura abrangeu o modelo de recuperação INT22, testes e auxiliar de interleaving INT21, checkpoint, relatórios/resultados INT22 e contrato F3-INT-19. A busca de AGENTS.md no workspace não encontrou instruções adicionais. Antes de editar código, os três testes originais foram executados isoladamente com Python 3.13.5 -B: 3 testes, 3 falhas, zero erros/ignorados, {before['elapsed_seconds']} s. Todos os arquivos do manifesto INT22 permaneceram iguais durante a reprodução.

| Caso | Observação anterior | Causa |
|---|---|---|
| A20 | Dois closes retornavam True para o mesmo ticket | Validação e atribuição de closure separadas; nenhuma arbitragem exclusiva na escrita |
| A21 | Geração 2 adquirida na janela de close, mas ticket da geração 1 era gravado | Não havia fencing do ponto final de commit entre verificação e publicação |
| A22 | Prova não registrada, passada diretamente a resolve, removia conflito | Helper sem lease/admissão/verificação podia invalidar evidência; ID de resolução ausente do ledger escapava da revalidação posterior |

Logs e snapshots: TESTE_F3_INT23_BEFORE.txt, RESULTADO_F3_INT23_BEFORE.json e CONTRAEXEMPLOS_F3_INT23_BEFORE.json. Cópias integrais anteriores estão em auditoria_f3_int23_antes/tools/f3_int20_evidence_recovery_model.py (SHA-256 8c491931f80f23f765b35eb69ea0b5dd3071c6aa611dd5b91dcb4f2dfbadbf7b) e auditoria_f3_int23_antes/tests/test_f3_int20_evidence_recovery.py. O pacote INT22 original foi preservado sem alteração.

## A20/A21: ponto de decisão exclusivo

O Store agora contém um gate correspondente a geração, token exclusivo e revisão. A atribuição de closure é protegida: confere fase, inexistência de fechamento, geração/lease/token, revisão, digest e metadados do gate; propõe COMMIT por uma única operação dict.setdefault. Somente o objeto candidato vencedor pode publicar o registro terminal. Tentativas duplicadas, obsoletas ou que encontram FENCED são recusadas com CommitRejected, traduzido pelo close para false.

No scheduler simulado, dict.setdefault é a primitiva indivisível DECLARADA de arbitragem. Não foi implementado lock nativo, thread, processo, transação em banco, persistência ou garantia de runtime Windows. A afirmação verificada é sobre esse modelo em memória sob essa primitiva, não segurança de produção ou concorrência nativa.

Aquisição de nova geração e toda mudança material selam o gate anterior antes de alterar os dados. Adição de evidência nova (inclusive J/L positivas), cleanup falho e aplicação de resolução também cercam commits pendentes. Se FENCED vencer primeiro, uma referência antiga ao gate não consegue publicar. Se COMMIT vencer primeiro, mudanças posteriores ajudam a publicar o mesmo registro terminal e são tratadas como eventos pós-fechamento, com contestação externa; não apagam o fechamento nem reabrem a sessão.

O ponto de linearização é a decisão do gate, não a ordem dos returns. Os testes cobrem geração/interferência antes e depois desse ponto: antes, o close antigo é rejeitado; depois, a decisão já válida é preservada e a conclusão contestada. Apenas comparar a geração no fim, ignorando essa ordem, produziria um oráculo incorreto.

Nenhuma criação, retomada, ordem ou execução passou a ser autorizada. Sessão original, identidade, história, resultado funcional, deadline, revogação e admissão fechada continuam preservados. aggregate_success continua sempre false.

## A22: retirada de conflito depende de prova admitida

resolve agora exige um Evidence/Fact de tipo RESOLVE e lease explícito atual. Os bytes exatos precisam existir uma única vez no ledger, sem invalidação, após admissão pelo caminho add. O verificador sintético é consultado novamente imediatamente antes da aplicação. As guardas anteriores de independência da fonte/domínio de falha, cobertura integral, explicação não vazia, alvos conhecidos e definitividade foram preservadas. A aplicação é mudança material e a evidência permanece para revalidação posterior.

True/False, texto de resolução, prova apenas registrada no oracle, prova sem receipt, lease obsoleto, cache, fonte do próprio domínio de falha ou evidência sem intervalo/explicação suficientes não retiram X. O reenvio idêntico de uma resolução válida é idempotente. Revogação do receipt entre admissão e aplicação é testada e impede excluir a evidência contrária.

A independência, procedência, integridade e ponte de relógio continuam premissas verificadas por fixtures previamente configuradas, e não criptografia real. O reparo fecha o bypass do helper; não transforma authenticated_witness_verified em true.

## Preservação dos 151 testes e ajuste explícito do auxiliar

Os 151 métodos de teste anteriores e suas asserções foram preservados. Os 24 adversariais INT21 permanecem byte a byte intactos. Foi necessário mudar somente dois métodos de suporte em tests/test_f3_int20_evidence_recovery.py: Harness.eligible passa a devolver None quando reconcile rejeita; Harness.finish devolve false quando não há ticket. Antes, eligible fazia assert de sucesso da reconciliação, o que tornaria A22 incapaz de observar a rejeição antecipada CORRETA de uma resolução inválida.

Não foi relaxada uma asserção de segurança nem alterado o comportamento do modelo para fingir reconciliação com X. Testes positivos ainda precisam de true e falham se uma guarda rejeitar; negativos agora conseguem obter false sem abortar a preparação. S22/S23 verificam ambos os caminhos. O runner compara por AST todo o módulo antes/depois, excluindo apenas esses dois métodos de suporte, e protege os demais arquivos por SHA-256. Os diffs completos e as cópias anteriores estão no pacote; essa alteração foi comunicada antes da edição.

Não houve mudança na especificação F3-INT-19 (SHA-256 13687959d5cf12c200ed3803cd429f72701aa2e0c1ffa4953b88627efa2fa060). A implementação concretiza sua regra de commit indivisível e prova independente; não foi identificada divergência normativa. O ajuste é de suporte de teste, não alteração do contrato.

## Execuções e resultados reais

| Execução | Testes | Aprovados | Falhas | Erros / ignorados | Exit | Tempo do executor |
|---|---:|---:|---:|---|---:|---:|
| Reprodução antes da edição | 3 | 0 | 3 | 0 / 0 | 1 | {before['elapsed_seconds']} s |
| Críticos A20–A22 após edição | 3 | 3 | 0 | 0 / 0 | 0 | {critical['elapsed_runner_seconds']} s |
| Específicos novos | 24 | 24 | 0 | 0 / 0 | 0 | {specific['elapsed_runner_seconds']} s |
| Regressão completa | 197 | 196 | 1 | 0 / 0 | 1 | {combined['elapsed_runner_seconds']} s |

A regressão completa contém 151 originais, 22 específicos INT22 e 24 específicos INT23. Os 151 originais tiveram 150 aprovações e somente A06 falho; os 22 INT22 e 24 INT23 passaram. A20/A21/A22 passaram novamente na regressão, com seus testes originais intactos. A06 não foi ignorado, convertido em expectedFailure ou corrigido incidentalmente. O exit 1 da regressão é real e permanece no JSON/log.

Foram realizados quatro comandos de testes e uma exploração nesta etapa: reprodução inline antes de qualquer edição; runner INT23 critical, specific, combined e explore. As fontes finais dos três runs posteriores e da busca têm o mesmo hash, e não mudaram durante as execuções. Combined e explore foram executados em processos Python independentes com logs separados, sem sessão de recuperação compartilhada; isso não é evidência de concorrência real.

Os 24 novos cobrem: agendas originais A20/A21; agendas imediatamente antes/depois de setdefault; um único vencedor; geração antiga cercada; preservação de decisão linearizada anterior; negativo material nas mesmas janelas; fechamento irreversível e replay; ticket forjado sem consumir gate válido; reinício com mesmo ledger; rejeição de booleanos/registro sem admissão/receipt ausente; resolução válida independente; falha de independência; cache; lease/generation obsoletos; explicação/intervalo incompletos; idempotência e perda de receipt; auxiliar negativo/positivo e imutabilidade de outcome/histórico/autoridade.

## Exploração adversarial limitada

| Métrica | Resultado |
|---|---|
| Sementes / ações disponíveis | {exp['seeds']} / {len(exp['actions'])} |
| Estados distintos / expandidos | {exp['unique_states']} / {exp['expanded_states']} |
| Ações tentadas / completas | {exp['transitions_attempted']} / {exp['transitions_completed']} |
| Duplicatas de estado | {exp['duplicate_states']} |
| Agendas intramétodo realmente executadas | {exp['violation_counts'].get('injected_schedules_completed', 0)} |
| Profundidade extra atingida / limite | {exp['max_extra_depth_reached']} / {exp['limits']['max_extra_depth']} |
| Violações / exceções | {exp['violation_edges']} / {exp['exceptions']} |
| Preparação / busca / total interno | {exp['elapsed_setup_seconds']} / {exp['elapsed_search_seconds']} / {exp['elapsed_total_seconds']} s |
| Interrupção / fronteira restante | {exp['stop_reason']} / {exp['remaining_frontier']} |

Limites: 900 ações, 750 estados, profundidade EXTRA 4, 25 segundos de busca. A busca parou por TRANSITION_LIMIT, antes de atingir profundidade 4 ou esgotar a fronteira. Nenhum timeout da busca ou executor geral foi ocultado. A lista de contraexemplos dessa busca está vazia; isso não significa prova exaustiva nem elimina A06.

O explorador novo mantém as 18 ações antigas e acrescenta sete: dois fechamentos na janela original, dois na decisão do gate, geração antes/depois da decisão, resolução bruta, resolução admitida e resolução booleana (as duas variantes de geração e as três de resolução são ações separadas). Há 25 ações no total, conforme o JSON. As quatro agendas intramétodo efetivas são duas de disputa de close e duas de geração. Todas as seis fases do dossiê foram alcançadas. As nove sementes, seus checkpoints e passos de preparação constam de EXPLORACAO_F3_INT23.json.

Uma transição da busca é uma ação do scheduler. Ações de interleaving contêm mais de uma chamada API e pontos de pausa Python, portanto 900 NÃO é contagem de instruções Python ou de todos os eventos internos. Profundidade extra não inclui preparação de sementes; não é profundidade absoluta. A chave contém o Store (incluindo gate e decisão), fontes/receipts, worker/lease/ticket, histórico e oráculo externo de renovação. O gate usa identidade do candidato em memória para reconhecer o vencedor; a serialização não deve ser usada para inferir exclusão entre Stores distintos.

Os exploradores anteriores também foram realmente reexecutados:

| Explorador | Tentativas | Estados reportados | Profundidade publicada | Tempo publicado (s) | Parada |
|---|---:|---|---|---|---|
{table}

INT13 pode parar por seu DURATION_LIMIT de 40 segundos dentro da regressão sem esgotar 180000 transições. O resultado real acima e o log integral são a cobertura obtida nesta execução; não reutilizar contagens históricas como se tivessem sido atingidas agora. Nenhum orçamento antigo foi alterado.

## Pendência A06 e limitações

Falha final: {combined['failed_ids'][0]}.

A06 permanece como bloqueio excessivo conservador do inventário completo repartido por tentativa. Não é um commit inseguro, e não foi incluído nas correções A20–A22. CONTRAEXEMPLOS_F3_INT23_COMBINED.json preserva sua expectativa, observado e snapshot, junto às observações críticas agora atendidas e à caracterização de ledger clonado. As evidências anteriores dos três achados também permanecem disponíveis.

Gate compartilhado em memória não é armazenamento durável. Um clone de Store tem autoridade separada, conforme A23. Chamador e fixture registry continuam confiáveis; não há isolamento contra edição hostil de objetos internos. dict.setdefault é assumido indivisível no scheduler, não foi certificado para threads, runtimes alternativos ou kernel. Não foram implementados protótipo nativo, lock Windows ou integração operacional. Zero violações na exploração limitada não autoriza retirar A06 nem declarar segurança nativa.

## Arquivos modificados, entrega e integridade

Preexistentes modificados:
- C:\\COPILOTO_GIT_SYNC\\{MODEL.replace('/', chr(92))} — SHA-256 {combined['model_sha256']}.
- C:\\COPILOTO_GIT_SYNC\\{HARNESS.replace('/', chr(92))} — SHA-256 {combined['harness_sha256']}; somente os dois métodos de suporte descritos, sem alterações nos testes/asserts.

Novos arquivos completos:

{listing}

Architecture C, especificação F3-INT-19, outros testes e artefatos anteriores ficaram intactos. Manifestos INT20/21/22 são históricos e mantêm seus pins antigos; não são modificados para aparentar integridade da árvore revisada. O manifesto corrente é INT23. O pacote inclui referências completas e o ZIP INT22 imutável, para restauração anterior em diretório separado.

O empacotador verifica hashes de origem, nomes/CRC do ZIP e igualdade SHA-256 de cada entrada descomprimida. O manifesto usa caminhos relativos, inclui todas as fontes/resultados necessários e exclui apenas ele próprio e o ZIP para evitar auto-referência. O ZIP contém o manifesto. Hashes externos do ZIP e do manifesto constam da saída final.

F3=OPEN; orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false. Nenhuma API nativa Windows, X3/X4, Profit, Excel RTD/DDE, ordens ou protótipo nativo foi executado. C:\\COPILOTO_PRICE_ACTION_AI e componentes operacionais não foram acessados ou modificados.

## Continuidade

A20/A21/A22 encerrados como achados simulados nos cenários executados; A06 separado e aberto. Retomar por CHECKPOINT_F3_INT23.md e snapshots/manifests. Não há aprovação integral enquanto A06 persistir, e nenhum resultado altera F3 ou os flags. A próxima correção de inventário deve ter escopo próprio, manter asserções e publicar novamente os limites de busca.
'''
    (ROOT / 'RELATORIO_F3_INT23.md').write_text(report, encoding='utf-8')
    (ROOT / 'CHECKPOINT_F3_INT23.md').write_text(checkpoint, encoding='utf-8')
    names = sorted(set(protected) | set(new) | {prior_zip})
    hashes = {name: fp(ROOT / name) for name in names}
    (ROOT / 'SHA256_F3_INT23.txt').write_text(''.join(hashes[n] + '  ' + n + '\n' for n in names), encoding='utf-8')
    names.append('SHA256_F3_INT23.txt')
    hashes['SHA256_F3_INT23.txt'] = fp(ROOT / 'SHA256_F3_INT23.txt')
    archive = ROOT / 'PACOTE_AUDITORIA_F3_INT23.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name in names:
            package.write(ROOT / name, arcname=name)
    with zipfile.ZipFile(archive) as package:
        if package.namelist() != names or package.testzip() is not None:
            raise ValueError('ZIP names or CRC mismatch')
        for name in names:
            if sha256(package.read(name)).hexdigest() != hashes[name] or fp(ROOT / name) != hashes[name]:
                raise ValueError('Byte mismatch: ' + name)
    print(json.dumps({'zip': str(archive), 'sha256_zip': fp(archive),
                      'sha256_manifest': hashes['SHA256_F3_INT23.txt'], 'entries': len(names),
                      'zip_bytes': archive.stat().st_size, 'all_entries_verified': True,
                      'modified_preexisting': CHANGED, 'model_sha256': combined['model_sha256'],
                      'prior_test_ast_preserved': True, 'A06_open': True, 'F3': 'OPEN',
                      'audit_fully_approved': False}, indent=2))


if __name__ == '__main__':
    main()