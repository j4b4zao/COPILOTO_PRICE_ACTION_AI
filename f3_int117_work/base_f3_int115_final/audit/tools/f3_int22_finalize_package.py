"""F3-INT-22 report/manifest/package builder; no test execution or model edits."""
import difflib
from hashlib import sha256
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'tools/f3_int20_evidence_recovery_model.py'
OLD = 'auditoria_f3_int22_antes/' + MODEL


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def fp(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    initial = read('RESULTADO_F3_INT22_BEFORE.json')
    first = read('RESULTADO_F3_INT22_FIVE.json')
    specific = read('RESULTADO_F3_INT22_SPECIFIC.json')
    intermediate = read('auditoria_f3_int22_intermediario/RESULTADO_F3_INT22_SPECIFIC.json')
    combined = read('RESULTADO_F3_INT22_COMBINED.json')
    explored = read('RESULTADO_F3_INT22_EXPLORE.json')
    for r in (initial, first, specific, intermediate, combined, explored):
        if not r['complete_runner'] or not r['source_unchanged_during_run']:
            raise ValueError('Run incomplete or source mutated while executing')
    if initial['failures'] != 5 or first['failures'] or specific['failures'] or combined['tests_run'] != 151:
        raise ValueError('Unexpected results; review before packaging')
    if fp(ROOT / OLD) != '4ce2ef2b4461441a6195bec9921cf4f727fa4bae61b5617b73cad8bf671463bc':
        raise ValueError('Before snapshot does not match audited model')
    previous_zip = 'PACOTE_AUDITORIA_F3_INT21.zip'
    if fp(ROOT / previous_zip) != '5c1c00a34090bb3c02fbffe23b5414d4f230d99920c261a684962d83c07a8ffb':
        raise ValueError('Original INT21 review package differs')
    protected = combined['sha256_after']
    for name, value in protected.items():
        if fp(ROOT / name) != value:
            raise ValueError('Artifact changed after regression: ' + name)
    model_hash = fp(ROOT / MODEL)
    if model_hash != specific['model_sha256'] or model_hash != explored['model_sha256']:
        raise ValueError('Final tests/search used different model bytes')
    targets = ('RELATORIO_F3_INT22.md', 'CHECKPOINT_F3_INT22.md', 'SHA256_F3_INT22.txt',
               'PACOTE_AUDITORIA_F3_INT22.zip', 'ALTERACOES_F3_INT22.diff')
    if any((ROOT / n).exists() for n in targets):
        raise FileExistsError('A final INT22 artifact already exists; do not overwrite')
    delta = ''.join(difflib.unified_diff((ROOT / OLD).read_text(encoding='utf-8').splitlines(True),
                 (ROOT / MODEL).read_text(encoding='utf-8').splitlines(True),
                 fromfile='antes/' + MODEL, tofile='depois/' + MODEL))
    (ROOT / 'ALTERACOES_F3_INT22.diff').write_text(delta, encoding='utf-8')
    old_metrics = []
    for match in re.finditer(r'F3_INT(\d+)_REPORT=(\{[^\n]*\})',
                             (ROOT / 'TESTE_F3_INT22_COMBINED.txt').read_text(encoding='utf-8')):
        r = json.loads(match.group(2))
        old_metrics.append(f'| INT{match.group(1)} | {r["attempted"]} | '
                           f'{r.get("distinct_states", r.get("states", "não informado"))} | '
                           f'{r.get("depth_effective", "prefixos canônicos")} | '
                           f'{r.get("elapsed_seconds", "não informado")} | '
                           f'{r.get("stop_reason", "cobertura canônica limitada")} |')
    old_table = '\n'.join(old_metrics)
    new = [
        'tools/f3_int22_run_audit.py', 'tools/f3_int22_finalize_package.py',
        'tests/test_f3_int22_conservative_recovery.py', 'DIAGNOSTICO_F3_INT22_ANTES.md', OLD,
        'TESTE_F3_INT22_BEFORE.txt', 'RESULTADO_F3_INT22_BEFORE.json', 'CONTRAEXEMPLOS_F3_INT22_BEFORE.json',
        'TESTE_F3_INT22_FIVE.txt', 'RESULTADO_F3_INT22_FIVE.json', 'CONTRAEXEMPLOS_F3_INT22_FIVE.json',
        'auditoria_f3_int22_intermediario/TESTE_F3_INT22_SPECIFIC.txt',
        'auditoria_f3_int22_intermediario/RESULTADO_F3_INT22_SPECIFIC.json',
        'auditoria_f3_int22_intermediario/CONTRAEXEMPLOS_F3_INT22_SPECIFIC.json',
        'auditoria_f3_int22_intermediario/f3_int20_evidence_recovery_model.py',
        'CONTRAEXEMPLOS_F3_INT22_GERACOES_INTERMEDIARIO.json',
        'TESTE_F3_INT22_SPECIFIC.txt', 'RESULTADO_F3_INT22_SPECIFIC.json', 'CONTRAEXEMPLOS_F3_INT22_SPECIFIC.json',
        'TESTE_F3_INT22_COMBINED.txt', 'RESULTADO_F3_INT22_COMBINED.json', 'CONTRAEXEMPLOS_F3_INT22_COMBINED.json',
        'EXPLORACAO_F3_INT22.json', 'RESULTADO_F3_INT22_EXPLORE.json', 'ALTERACOES_F3_INT22.diff',
        'RELATORIO_F3_INT22.md', 'CHECKPOINT_F3_INT22.md',
    ]
    listing = '\n'.join('- C:\\COPILOTO_GIT_SYNC\\' + n.replace('/', '\\')
                        for n in new + ['SHA256_F3_INT22.txt', 'PACOTE_AUDITORIA_F3_INT22.zip'])
    remainder = '\n'.join('- ' + n for n in combined['failed_ids'])
    checkpoint = f'''# Checkpoint manual — F3-INT-22

Data: 2026-10-20, America/Sao_Paulo. Workspace exclusivo: C:\\COPILOTO_GIT_SYNC.

Etapa concluída: os cinco fechamentos indevidos A09–A13 foram reproduzidos antes da edição e corrigidos conservadoramente. Não há aprovação integral: quatro falhas remanescentes estão abertas.

Resultados reais:
- Antes: 5 testes / 5 falhas / 0 erros; modelo SHA-256 {initial['model_sha256']}.
- Primeira correção: A09–A13 5/5; testes novos 20/22, com duas falhas de preservação entre gerações. Logs, fonte intermediária e quatro snapshots foram preservados.
- Final: 22/22 testes específicos; 151 originais reexecutados, 147 aprovados e 4 falhas (A06, A20, A21, A22), zero erros/ignorados. Os 127 anteriores à INT21 passaram; os 24 adversariais originais agora têm 20 aprovações e 4 falhas, sem alterações de arquivo/expectativa.
- Busca final: {explored['unique_states']} estados, {explored['transitions_completed']} transições, profundidade extra {explored['max_extra_depth_reached']}, {explored['elapsed_search_seconds']} s; {explored['stop_reason']}; fronteira {explored['remaining_frontier']}; zero exceções/violações nos percursos executados. Não exaustiva.

Único arquivo preexistente modificado: tools/f3_int20_evidence_recovery_model.py. Hash final: {model_hash}. Architecture C, especificação F3-INT-19, todos os testes anteriores e relatórios/logs de INT20/21 intactos. Fonte anterior: {OLD}. Diferença completa: ALTERACOES_F3_INT22.diff.

Correções: conflitos por scope em F/C/U/P/H sobre histórico admitido não invalidado (inclusive gerações antigas); grupos conflitantes não satisfazem predicados; vereditos desconhecidos rejeitados; mensagens J/L negativas ou incompletas mudam revisão material e invalidam ambas as observações; L FAILED conserva CLEANUP_FAILED; J nova deve suceder causalmente as dependências negativas, mesmo de gerações anteriores; L nova depende de J atualmente válida; ticket antigo conserva rejeição por fase/revisão/digest/lease. Sessão original, deadline, histórico, identidade, resultado e revogação não são reescritos.

Retomar por RELATORIO_F3_INT22.md, CONTRAEXEMPLOS_F3_INT22_COMBINED.json e SHA256_F3_INT22.txt. ZIP: C:\\COPILOTO_GIT_SYNC\\PACOTE_AUDITORIA_F3_INT22.zip. Contém a fonte atual, testes, logs, snapshots, diff e pacote INT21 original imutável para reproduzir a situação anterior separadamente. Manifestos INT20/21 referem-se à fonte ANTIGA; o manifesto corrente é INT22. Os runners legados rejeitam corretamente a árvore revisada por seu pin antigo: usar o runner INT22.

Falhas pendentes:
{remainder}

A06 é bloqueio excessivo do inventário por tentativa. A20/A21 expõem a premissa de chamadas atômicas, não concorrência nativa demonstrada. A22 ainda permite resolução por helper público sem verificação/caminho add; é uma fronteira de chamador confiável ainda aberta. Não corrigidas neste escopo; preserve as expectativas e os snapshots antes de propor sua próxima correção.

Reprodução manual posterior (Python 3.13.5, -B):
```
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int22_run_audit.py specific
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int22_run_audit.py combined
& 'C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe' -B tools/f3_int22_run_audit.py explore
```
combined retorna exit 1 pelas quatro falhas conhecidas; não as tratar como aprovação. Estes comandos sobrescrevem resultados INT22: preservar versões e regenerar manifesto/ZIP após nova execução. O modo before é intencionalmente recusado na árvore corrigida; os contraexemplos iniciais já estão integralmente registrados e o ZIP INT21 permite reprodução em extração separada, sem substituir a fonte atual. O finalizador recusa sobrescrever artefatos finais.

F3=OPEN; orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false. Nenhuma integração/ordem, API nativa ou componente operacional foi executado. Não acessar/modificar C:\\COPILOTO_PRICE_ACTION_AI, Architecture C, X3/X4, Profit, Excel ou RTD/DDE. Nenhuma comprovação de segurança nativa.
'''
    report = f'''# F3-INT-22 — Correções conservadoras de fechamento no modelo simulado

Data: 2026-10-20 (America/Sao_Paulo). Os cinco achados de fechamento A09–A13 foram corrigidos. Quatro outras falhas persistem; NÃO há aprovação integral do modelo. F3=OPEN, sete flags operacionais=false, domínio SIMULATED.

## Diagnóstico reproduzido antes de editar

Foram inspecionados o modelo, os testes adversariais originais, RELATORIO_F3_INT21.md, CHECKPOINT_F3_INT21.md, seus snapshots e o contrato F3-INT-19. A busca no workspace não encontrou AGENTS.md. A reprodução foi executada antes de qualquer alteração no código do modelo: 5 testes, 5 falhas, zero erros/ignorados, exit 1, {initial['elapsed_runner_seconds']} s de executor. Todos os cinco snapshots mostram observed=True para fechamento quando expected=False.

| Original | Reprodução e causa |
|---|---|
| A09 / CONFLICT_F | F UNFENCED aceito junto a FENCED; detector agrupava apenas C/U e selecionava prova F favorável |
| A10 / CONFLICT_P | ALIVE e EXIT para a mesma identidade não geravam X |
| A11 / CONFLICT_H | NOT_CONTAINED e negações de associação/suspensão coexistiam com H positiva sem bloqueio |
| A12 / J_NONEMPTY_STALE_BARRIER | NONEMPTY não alterava material_revision; ticket novo podia usar J/L antigos |
| A13 / L_FAILED_STALE_BARRIER | Mensagem FAILED de cleanup não invalidava como cleanup_failed e permitia a mesma requalificação obsoleta |

Registros anteriores integrais: DIAGNOSTICO_F3_INT22_ANTES.md, TESTE_F3_INT22_BEFORE.txt, RESULTADO_F3_INT22_BEFORE.json, CONTRAEXEMPLOS_F3_INT22_BEFORE.json. A cópia de fonte anterior foi gravada antes da reprodução em {OLD}, com SHA-256 {initial['model_sha256']}. Não foi substituída ou reconstruída depois da correção.

Não houve divergência normativa que exigisse mudar a F3-INT-19. As alterações implementam suas regras existentes de conflitos X, causalidade, geração, revisão consistente e encerramento conservador. A especificação permanece com SHA-256 13687959d5cf12c200ed3803cd429f72701aa2e0c1ffa4953b88627efa2fa060.

## Correções realizadas

1. O agrupamento de alegações incompatíveis passou de C/U para F/C/U/P/H, por obrigação e subject. Não é contagem de testemunhas ou escolha por recência. Um grupo conflitante deixa de satisfazer o predicado positivo. Provas semanticamente idênticas de fontes diferentes não criam conflito artificial.
2. O agrupamento consulta todo o histórico admitido e ainda não invalidado, preservando conflitos entre gerações. Uma geração nova renova a autoridade de recuperação, mas não apaga contradição antiga. Evidência histórica pode bloquear sem se tornar prova positiva da geração atual. A resolução independente existente preserva bytes e precisa excluir explicitamente a alegação inválida.
3. Vereditos não reconhecidos são rejeitados conservadoramente com UNSUPPORTED_VERDICT e mantidos entre rejeições/pendências. O vocabulário implementado não concede autoridade nem altera a especificação. Isso impede que uma afirmação relevante desconhecida seja aceita e depois ignorada em favor de outra prova.
4. Mensagens J/L negativas, incompletas ou não definitivas são mudanças materiais: incrementam material_revision e revision, invalidando a barreira antiga. Seu ID fica preservado em negative_dependencies, também vinculado ao digest. L FAILED acrescenta CLEANUP_FAILED ao histórico de falhas sem modificar o resultado funcional original.
5. J nova exige revisão/challenge atual, admissão após RECONCILED, cobertura das provas base e relação causal com cada observação negativa não invalidada, inclusive de gerações anteriores. A relação pode vir de pais explícitos autenticados com ponte de relógio simulada, ou sequência/tempo monotônicos da mesma fonte/epoch/clock. Ordem de chegada ou timestamp de parede entre fontes não bastam. L deve suceder uma J atualmente válida; uma L nova baseada em J antiga não qualifica.
6. O controle já existente de fase, revisão, digest e lease do ticket foi preservado. Não basta fabricar um ticket com a revisão nova: predicados e observações devem continuar elegíveis. Uma mudança material conserva o bloqueio do ticket antigo.

A primeira edição fez A09–A13 passarem, mas os testes novos N21/N22 encontraram perda de conflitos e de obrigações causais na troca de geração. Essa revisão intermediária foi arquivada com seus logs e SHA-256 {first['model_sha256']}. Foram capturados quatro snapshots adicionais (F/P/H e dívida causal J) em CONTRAEXEMPLOS_F3_INT22_GERACOES_INTERMEDIARIO.json antes de corrigir o histórico entre gerações. A suíte final passou sem mudar suas expectativas. Esses resultados intermediários não foram apagados.

Não houve alteração em criação, retomada, execução, outcome, deadline, identidade, revogação ou admissão da sessão original. Nenhuma integração, adaptação de kernel, lock nativo ou persistência real foi implementada. O único código preexistente alterado é tools/f3_int20_evidence_recovery_model.py. Fonte final SHA-256: {model_hash}. O diff completo está em ALTERACOES_F3_INT22.diff.

## Execuções realmente realizadas

Python 3.13.5, com -B para não gerar bytecode; workspace C:\\COPILOTO_GIT_SYNC. Allowlist explícita; nenhuma descoberta geral do projeto.

| Execução | Testes | Aprovados | Falhas | Erros / ignorados | Exit | Tempo de executor |
|---|---:|---:|---:|---|---:|---:|
| before, fonte original | 5 | 0 | 5 | 0 / 0 | 1 | {initial['elapsed_runner_seconds']} s |
| five, primeira correção | 5 | 5 | 0 | 0 / 0 | 0 | {first['elapsed_runner_seconds']} s |
| specific, revisão intermediária | 22 | 20 | 2 | 0 / 0 | 1 | {intermediate['elapsed_runner_seconds']} s |
| specific, fonte final | 22 | 22 | 0 | 0 / 0 | 0 | {specific['elapsed_runner_seconds']} s |
| combined, fonte final | 151 | 147 | 4 | 0 / 0 | 1 | {combined['elapsed_runner_seconds']} s |

Esses cinco comandos unittest e uma execução de busca limitada foram realizados nesta etapa, além da captura diagnóstica dos quatro snapshots intermediários. O comando combined contém exatamente os 151 originais (89 Architecture C + 38 INT20 + 24 INT21), sem incluir silenciosamente os 22 novos na sua contagem. Os 22 específicos foram executados separadamente. A busca e a regressão finais foram iniciadas em processos Python independentes sobre os mesmos bytes de código, com logs distintos; não compartilham estado de sessão e isso não é teste de concorrência real do recuperador.

Comparação com a F3-INT-21: seus 151 testes tinham 142 aprovações e nove falhas. Agora são 147 aprovações e quatro falhas: os cinco achados-alvo deixaram de falhar na fonte final. Os 127 anteriores à INT21 continuam aprovados, e os 24 adversariais originais, byte a byte intactos, têm 20 aprovações e quatro falhas. Nenhuma expectativa foi enfraquecida, nenhum teste virou expectedFailure e nenhum foi ignorado. O resultado de combined é corretamente exit 1.

### Regressões novas

N01–N03 verificam F/P/H em ambas as ordens de chegada. N04 verifica provas equivalentes. N05 cobre negativos, incompletos e indefinitivos de J/L. N06/N07 demonstram recuperação somente com J/L novas, preservando falha de cleanup. N08–N11 cobrem revisão sem ponte causal, sequência da mesma fonte, ponte de relógio indisponível e múltiplas dependências negativas. N12 cobre mudança em prova base. N13 cobre resolução independente de F/P/H. N14 rejeita vereditos desconhecidos em sete obrigações. N15/N16 preservam contestação terminal e rejeitam ticket remontado. N17–N20 cobrem idempotência, histórico/outcome/deadline/autoridade e incompletude H. N21/N22 garantem que trocar geração não apaga conflitos ou a exigência causal. São 22 métodos unittest com variantes; não foram contados como estados únicos.

## Exploração adversarial limitada

Foi reutilizado, sem alteração, tools/f3_int21_bounded_explorer.py, com o mesmo conjunto de ações, nove sementes e oráculo externo de dívida de renovação. Assim os números são comparáveis, sem prometer igualdade de cobertura entre implementações diferentes.

| Métrica | INT21 anterior | INT22 atual |
|---|---:|---:|
| Estados distintos | 618 | {explored['unique_states']} |
| Transições tentadas / completas | 900 / 900 | {explored['transitions_attempted']} / {explored['transitions_completed']} |
| Profundidade extra atingida | 2 | {explored['max_extra_depth_reached']} |
| Duplicatas de estado | 291 | {explored['duplicate_states']} |
| Violações em arestas / exceções | 2 / 0 | {explored['violation_edges']} / {explored['exceptions']} |
| Fronteira restante | 567 | {explored['remaining_frontier']} |
| Tempo de busca | 3,837254 s | {explored['elapsed_search_seconds']} s |
| Interrupção | TRANSITION_LIMIT | {explored['stop_reason']} |

Limites: 900 transições, 650 estados, profundidade EXTRA 3 e 25 segundos de busca. Preparação: {explored['elapsed_setup_seconds']} s; busca: {explored['elapsed_search_seconds']} s; total interno: {explored['elapsed_total_seconds']} s. O limite de transições interrompeu a busca antes de atingir profundidade 3 ou esgotar a fronteira. Não houve timeout da busca. Os 51 nós em expanded_states são selecionados para expansão; o último não produziu arestas após esgotar o orçamento, de modo que 50 nós tiveram transições avaliadas. Sementes e passos de preparação não estão incluídos na profundidade extra ou nos 900 passos de busca.

EXPLORACAO_F3_INT22.json conserva checkpoints das sementes, métricas, ações e a lista de contraexemplos (vazia nesta busca). Zero violações nesse percurso é um resultado limitado, não prova de ausência de defeitos; os quatro testes dirigidos remanescentes continuam falhando fora desse pequeno espaço de busca. A função de hash de estado, fronteira e motivos de interrupção constam do JSON.

Os exploradores antigos também foram realmente reexecutados dentro dos 151 testes, com seus limites preservados:

| Explorador | Tentativas | Estados publicados | Profundidade publicada | Tempo publicado (s) | Parada |
|---|---:|---|---|---|---|
{old_table}

Se INT13 informa DURATION_LIMIT, essa exploração parcial não é apresentada como orçamento exaurido de 180000 arestas ou como prova exaustiva. A regressão unittest como um todo concluiu e seus quatro testes falhos estão registrados integralmente em TESTE_F3_INT22_COMBINED.txt.

## Falhas remanescentes e evidências

{remainder}

- A06: bloqueio excessivo conservador ao repartir processos conhecidos entre múltiplas tentativas. Não é fechamento inseguro; a correção de inventário por tentativa não fez parte dos cinco achados-alvo.
- A20: dois commits podem retornar sucesso sob interleaving Python intramétodo. A21: uma geração nova pode ser adquirida entre verificação e gravação do close antigo. São fronteiras da premissa de chamadas completas atômicas, não demonstração de concorrência nativa.
- A22: chamada direta ao helper público resolve com prova não registrada ainda pode excluir conflito e permitir fechamento posterior. A superfície de chamador confiável permanece aberta; não foi ocultada nem corrigida incidentalmente.

CONTRAEXEMPLOS_F3_INT22_COMBINED.json contém as dez observações dirigidas finais: cinco fechamentos-alvo agora bloqueados, quatro expectativas remanescentes violadas (incluindo A06) e a caracterização aprovada de ledger clonado A23. Cada observação contém trace, esperado, observado, snapshot completo, fontes, receipts, sessão original e avaliação. Os snapshots antigos e intermediários também foram preservados. Não há aprovação integral do modelo.

## Integridade, arquivos e pacote

Arquivo preexistente modificado (e somente este): C:\\COPILOTO_GIT_SYNC\\tools\\f3_int20_evidence_recovery_model.py.

Arquivos novos completos:

{listing}

Architecture C, todos os testes anteriores (incluindo os 24 adversariais), auxiliares/explorador INT21, relatórios/logs e especificação permaneceram byte a byte iguais aos respectivos manifestos. Os JSONs de execução conferem os hashes antes/depois. O manifesto INT22 usa caminhos relativos e hash de todos os arquivos de revisão exceto ele próprio e o ZIP. O ZIP inclui o manifesto, os arquivos completos atuais, snapshots e o ZIP original INT21 imutável como referência separada de reprodução anterior. O empacotador confere nomes, CRC, hash de cada entrada descomprimida e bytes de origem após a criação. Hash externo do ZIP e do manifesto são informados na saída final, sem referência circular.

Os manifestos INT20/21 continuam intocados como registros históricos, mas seu hash do modelo não corresponde à fonte atual intencionalmente corrigida. Os runners legados fazem pin desse hash antigo e não devem ser alterados para mascarar isso: o runner INT22 permite exclusivamente a alteração autorizada do modelo e protege os demais arquivos. A fonte original também existe na cópia anterior e no pacote INT21 para comparação independente.

F3=OPEN. orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false. Todos os testes/checkpoints avaliados preservam a sessão original, revogação e admissão fechada; aggregate_success continua false. Nenhuma API nativa do Windows de supervisão/contenção, Profit, Excel, RTD/DDE, X3/X4, ordem, protótipo nativo ou integração operacional foi executado. C:\\COPILOTO_PRICE_ACTION_AI e os componentes operacionais não foram acessados ou modificados.

## Continuidade

O escopo F3-INT-22 foi concluído com as cinco correções demonstradas e quatro achados remanescentes explícitos. Retomar por CHECKPOINT_F3_INT22.md, contraexemplos finais e manifesto. Qualquer próxima correção deve preservar os testes e o contrato, com escopo próprio para inventário, helper de resolução e atomicidade simulada. Não converter este resultado em segurança nativa ou em fechamento de F3.
'''
    (ROOT / 'RELATORIO_F3_INT22.md').write_text(report, encoding='utf-8')
    (ROOT / 'CHECKPOINT_F3_INT22.md').write_text(checkpoint, encoding='utf-8')
    names = sorted(set(protected) | set(new) | {'SHA256_F3_INT21.txt', previous_zip})
    hashes = {n: fp(ROOT / n) for n in names}
    (ROOT / 'SHA256_F3_INT22.txt').write_text(''.join(hashes[n] + '  ' + n + '\n' for n in names), encoding='utf-8')
    names.append('SHA256_F3_INT22.txt')
    hashes['SHA256_F3_INT22.txt'] = fp(ROOT / 'SHA256_F3_INT22.txt')
    zip_path = ROOT / 'PACOTE_AUDITORIA_F3_INT22.zip'
    with zipfile.ZipFile(zip_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name in names:
            package.write(ROOT / name, arcname=name)
    with zipfile.ZipFile(zip_path) as package:
        if package.namelist() != names or package.testzip() is not None:
            raise ValueError('Archive names/CRC failed')
        for name in names:
            if sha256(package.read(name)).hexdigest() != hashes[name] or fp(ROOT / name) != hashes[name]:
                raise ValueError('Packaged bytes differ: ' + name)
    print(json.dumps({'zip': str(zip_path), 'sha256_zip': fp(zip_path),
                      'sha256_manifest': hashes['SHA256_F3_INT22.txt'], 'entries': len(names),
                      'zip_bytes': zip_path.stat().st_size, 'all_entries_verified': True,
                      'modified_preexisting': [MODEL], 'model_sha256': model_hash,
                      'audit_fully_approved': False, 'F3': 'OPEN'}, indent=2))


if __name__ == '__main__':
    main()