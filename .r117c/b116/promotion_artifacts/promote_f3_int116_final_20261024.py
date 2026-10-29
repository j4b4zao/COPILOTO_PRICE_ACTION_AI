"""Explicitly authorized offline FINAL publication, preserving every input."""
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

WORK = Path(__file__).resolve().parent
SOURCE = WORK / 'f3_int116_corrigida'
ROOT = SOURCE / 'audit'
FINAL = WORK / 'f3_int116_final'
STAGING = WORK / '.f116_stage'
OUT = WORK / 'audit/PROMOCAO_F3_INT116_FINAL_20261024_V2'
ZIP = WORK / 'audit/F3_INT116_FINAL_COMPLETA_20261024.zip'
PENDING = Path(str(ZIP) + '.pending')
LOCKS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed', 'authenticated_witness_verified')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf8')


def read(path):
    return json.loads(path.read_bytes())


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def verify(pins, root):
    for name, digest in pins.items():
        path = root / name
        require(path.is_file() and sha(path.read_bytes()) == digest, 'Integrity mismatch: ' + str(path))


def safe(value, stage=None):
    require(value['f3'] == 'OPEN' and set(value['locks']) == set(LOCKS) and
            all(v is False for v in value['locks'].values()), 'Unsafe F3 or safety flags')
    if stage:
        require(value['stage'] == stage, 'Unexpected stage')


def preflight():
    pins = inventory(SOURCE)
    candidate = read(ROOT / 'MANIFESTO_F3_INT116_CANDIDATA.json')
    safe(candidate, 'F3-INT-116')
    require(len(candidate['files_sha256']) == 898, 'Unexpected candidate inventory')
    verify(candidate['files_sha256'], ROOT)
    require(sha((ROOT / 'MANIFESTO_F3_INT116_CANDIDATA.json').read_bytes()) ==
            (ROOT / 'MANIFESTO_F3_INT116_CANDIDATA.json.sha256').read_text().split()[0], 'Candidate sidecar mismatch')
    candidate_zip = WORK / 'audit/F3_INT116_CANDIDATA_CORRIGIDA_COMPLETA_20261024.zip'
    require(sha(candidate_zip.read_bytes()) == '4af6d6d84195532a6fd013a3ba894b2e1684f5368526266c7c580d9526c42b0f', 'Approved candidate ZIP changed')
    with zipfile.ZipFile(candidate_zip) as z:
        require(z.testzip() is None, 'Candidate ZIP CRC failure')
        for name, digest in pins.items():
            require(sha(z.read('f3_int116_corrigida/' + name)) == digest, 'Candidate ZIP/source mismatch: ' + name)
    evidence = ROOT / 'EVIDENCIAS_F3_INT116_CORRECAO'
    before = read(evidence / 'ANTES.json')
    result = read(evidence / 'RESULTADO.json')
    sources = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(ROOT.rglob('*.py'))
               if '__pycache__' not in p.parts and p.is_file()}
    require(len(sources) == 225 and sources == before['sources_before'] == result['sources_before'], 'Executed source mismatch')
    require(result['success'] is True and result['exception'] is None and result['optimized'] is True and
            result['historical_integrity_verified_after'] is True, 'Audit was not successful')
    safe(before); safe(result)
    require(before['offline'] is True and result['offline'] is True and result['simulation_only'] is True
            and result['certification'] is False and result['promoted'] is False, 'Invalid audit constraints')
    require(len(result['runs']) == 2, 'Missing supervised run')
    for run, label, total, skipped in zip(result['runs'], ('ESPECIFICOS', 'REGRESSAO_COMPLETA'), (17, 1438), (0, 1)):
        require(run['label'] == label and run['total'] == total and run['passed'] == total - skipped and
                run['skipped'] == skipped and run['failures'] == run['errors'] == 0, 'Invalid test counts')
        execution = read(evidence / (label + '.log.execution.json'))
        require(all(run.get(k) == v for k, v in execution.items()), 'Execution record mismatch')
        require(execution['exit_code'] == 0 and execution['exception'] is None and execution['timed_out'] is False,
                'Invalid execution result')
        cleanup = execution['cleanup']
        require(cleanup['confirmed'] is True and cleanup['active_processes'] == 0 and cleanup['live_io_threads'] == [],
                'Process/IPC cleanup unconfirmed')
        text = (evidence / (label + '.log')).read_text(encoding='utf8')
        require(re.findall(r'^Ran (\d+) tests in [\d.]+s$', text, re.M) == [str(total)], 'Log count mismatch')
        require(re.search(r'^OK' + (r' \(skipped=1\)' if skipped else '') + r'\s*$', text, re.M), 'Log outcome mismatch')
        require(len(re.findall(r'^test_.*\(test_f3_int116_runner\.PortableRunnerTests\.', text, re.M)) == 9,
                'Corrected runner tests missing from log')
    require(not any(isinstance(n, ast.Assert) for n in ast.walk(ast.parse((ROOT / 'tools/f3_int116_run_audit.py').read_text()))),
            'Runner has assert')
    base = SOURCE / 'base_f3_int115_final'
    final115 = read(base / 'audit/MANIFESTO_F3_INT115_FINAL.json')
    require(len(final115['files_sha256']) == 874, 'Unexpected FINAL base inventory')
    verify(final115['files_sha256'], base)
    verify(before['historical_files'], base)
    verify(before['historical_files'], SOURCE)
    require(sha((base / 'audit/MANIFESTO_F3_INT115_FINAL.json').read_bytes()) == result['base_manifest_sha256'],
            'FINAL base manifest mismatch')
    previous = (ROOT / 'ULTIMO_MARCO.json').read_bytes()
    require(previous == (ROOT / 'CHECKPOINT_F3_INT115_FINAL.json').read_bytes() ==
            (base / 'audit/ULTIMO_MARCO.json').read_bytes(), 'Prior FINAL checkpoint mismatch')
    safe(json.loads(previous), 'F3-INT-115')
    protected = {}
    for directory in (WORK, WORK / 'audit'):
        for path in directory.glob('*FINAL*'):
            if path.is_file():
                protected[path.relative_to(WORK).as_posix()] = sha(path.read_bytes())
    return pins, sources, before, result, previous, protected


def main():
    aliases = (WORK / 'ULTIMO_MARCO.json', WORK / 'audit/ULTIMO_MARCO.json')
    outputs = (FINAL, STAGING, OUT, ZIP, PENDING, Path(str(ZIP) + '.sha256'),
               WORK / 'CHECKPOINT_F3_INT116_FINAL.json', WORK / 'audit/CHECKPOINT_F3_INT116_FINAL.json',
               WORK / 'audit/MANIFESTO_F3_INT116_FINAL.json')
    require(not any(p.exists() for p in outputs), 'FINAL output already exists; refusing overwrite')
    pins, sources, before, result, previous, protected = preflight()
    alias_history = {p.relative_to(WORK).as_posix(): p.read_bytes() for p in aliases}
    OUT.mkdir()
    precheck = dict(approved=True, candidate_files=len(pins), candidate_manifest_entries=898,
        executed_sources_verified=len(sources), base_manifest_entries=874, historical_files_verified=875,
        corrected_test_logs_consistent=True, prior_consistency_audit=dict(passed=51,total=51,verdict='APROVADO',
        provenance='Prior local consistency audit, confirmed by user'), candidate_inventory=pins,
        safety_locks=dict.fromkeys(LOCKS, False), f3='OPEN')
    (OUT / 'VERIFICACAO_PRE_PROMOCAO.json').write_bytes(encode(precheck))
    historical_ultimate = 'audit/HISTORICO_ULTIMO_MARCO_F3_INT115_FINAL_20261024.json'
    evidence_pins = {name: digest for name, digest in pins.items() if name.startswith('audit/EVIDENCIAS_F3_INT116_CORRECAO/')}
    checkpoint = dict(stage='F3-INT-116', checkpoint_type='FINAL', date='2026-10-24',
        last_completed='F3-INT-116', previous_definitive='F3-INT-115 FINAL',
        status='OFFLINE_AUDIT_AND_REGRESSION_APPROVED_WITH_WINDOWS_SYMLINK_SKIP',
        f3='OPEN', locks=dict.fromkeys(LOCKS, False), offline=True, simulation_only=True, certification=False,
        real_operations_authorized=False, promotion_authorized=True,
        authorization='Explicit user instruction: ETAPA 1 — PROMOCAO F3-INT-116 FINAL',
        consistency_audit=precheck['prior_consistency_audit'],
        approved_candidate_zip='F3_INT116_CANDIDATA_CORRIGIDA_COMPLETA_20261024.zip',
        approved_candidate_zip_sha256='4af6d6d84195532a6fd013a3ba894b2e1684f5368526266c7c580d9526c42b0f',
        project_relative_path='f3_int116_final', evidence_paths_relative_to='FINAL project directory',
        executed_sources_sha256={'audit/' + n:d for n,d in sources.items()}, evidence_sha256=evidence_pins,
        windows_specific_tests={k:v for k,v in result['runs'][0].items() if k != 'cleanup'},
        windows_full_regression={k:v for k,v in result['runs'][1].items() if k != 'cleanup'},
        process_cleanup=dict(confirmed=True,active_processes=0,live_io_threads=[]),
        previous_ultimate_preserved=dict(path=historical_ultimate,sha256=sha(previous)),
        final_manifest='audit/MANIFESTO_F3_INT116_FINAL.json',
        next_step='F3-INT-117: scope proposal and review only', next_stage_implementation_authorized=False,
        limitations=['Local evidence does not authenticate custody or provenance',
            'No proven power-loss resistance or physical durability',
            'One Windows symlink test skipped for lack of permission',
            'No exactly-once or cross-host guarantee',
            'Commit faults are controlled; no induced death demonstrated inside SQLite commit',
            'Historical source checks before/after cannot detect transient restored changes'])
    safe(checkpoint, 'F3-INT-116')
    final_bytes = encode(checkpoint)
    payload = {n:(SOURCE / n).read_bytes() for n in pins}
    # Full runnable candidate snapshot keeps its original manifests valid.
    payload.update({'candidata_preservada/' + n:data for n,data in list(payload.items())})
    payload[historical_ultimate] = previous
    payload['audit/CHECKPOINT_F3_INT116_FINAL.json'] = final_bytes
    payload['audit/ULTIMO_MARCO.json'] = final_bytes
    payload['promotion_artifacts/VERIFICACAO_PRE_PROMOCAO.json'] = encode(precheck)
    payload['promotion_artifacts/promote_f3_int116_final_20261024.py'] = Path(__file__).read_bytes()
    for name,data in alias_history.items():
        filename = 'HISTORICO_ULTIMO_MARCO_' + ('RAIZ' if '/' not in name else 'AUDIT') + '_PRE_F3_INT116.json'
        payload['promotion_artifacts/' + filename] = data
        (OUT / filename).write_bytes(data)
    report = '''# Promocao F3-INT-116 FINAL — 24/10/2026

Promocao expressamente autorizada pelo usuario apos parecer APROVADO (51/51 verificacoes de consistencia). FINAL identifica o marco offline aprovado; F3 continua OPEN, sete flags false, offline/simulation_only true, certification false. Nenhuma operacao real autorizada.

## Base aprovada e testes

Base: F3_INT116_CANDIDATA_CORRIGIDA_COMPLETA_20261024.zip, SHA-256 4af6d6d84195532a6fd013a3ba894b2e1684f5368526266c7c580d9526c42b0f. Os 898 pins da candidata, 225 fontes executados e conteudo do ZIP foram reconferidos antes da promocao. Nenhum codigo ou teste da candidata foi alterado.

Resultados reutilizados da execucao aprovada, sem nova execucao das suites nesta promocao de metadados: especificos 17/17; regressao 1438 testes, 1437 aprovados, 1 skipped, zero falhas/erros, exit code 0. Runner principal com -O em pasta relocalizada; supervisor herdado executou suites sem -O; nove testes novos exercitam subprocessos -O. Limpeza dos Jobs confirmada, zero processos ativos e threads IPC remanescentes no escopo supervisionado.

## Publicacao e preservacao

Projeto FINAL: f3_int116_final. audit/ULTIMO_MARCO.json e audit/CHECKPOINT_F3_INT116_FINAL.json possuem bytes identicos. Manifesto oficial: audit/MANIFESTO_F3_INT116_FINAL.json. Todos os 225 fontes e logs aprovados permanecem identicos.

Os checkpoints FINAL anteriores nao foram modificados. O antigo audit/ULTIMO_MARCO (F3-INT-115 FINAL) foi preservado byte a byte em audit/HISTORICO_ULTIMO_MARCO_F3_INT115_FINAL_20261024.json. O projeto candidato original permanece intacto e tambem esta integralmente em candidata_preservada/, onde seus manifestos continuam validos e seu runner pode ser reexecutado com nome novo de output. A base F3-INT-115 FINAL permanece integral em base_f3_int115_final/.

Na arvore ativa FINAL, manifestos anteriores que fixam ULTIMO_MARCO sao historicos: o manifesto candidato se aplica ao snapshot candidata_preservada/audit; o manifesto F3-INT-115 FINAL se aplica a base_f3_int115_final. O manifesto novo fixa o estado FINAL atual e inclui esses snapshots. Esse mapeamento evita confundir o marcador autorizado novo com alteracao de checkpoint anterior.

Os antigos marcadores do workspace (raiz F3-INT-98 e audit F3-INT-114) foram preservados em promotion_artifacts/HISTORICO_ULTIMO_MARCO_RAIZ_PRE_F3_INT116.json e HISTORICO_ULTIMO_MARCO_AUDIT_PRE_F3_INT116.json. Apos validar o ZIP, os dois aliases do workspace e seus novos checkpoints serao publicados com os mesmos bytes do checkpoint FINAL, e a publicacao sera conferida em registro externo.

O ZIP e preparado antes da publicacao: CRC, nomes unicos seguros, hash de cada membro, manifesto, fontes, evidencias, historicos e checkpoint sao verificados. Validacao pos-publicacao e hash do ZIP ficam fora do pacote para evitar autorreferencia. O manifesto exclui somente ele proprio e seu sidecar; o hash externo do ZIP cobre ambos.

## Limites

Sem custodia autenticada, procedencia independente ou resistencia comprovada a perda de energia. Permanece o skip de symlink do Windows. Nao ha garantia de durabilidade fisica, entrega exatamente uma vez ou entre computadores. Comparacoes locais antes/depois nao detectam alteracao transitoria restaurada. O runner 116 e preservado como auditor da candidata sobre a base 115; sua reexecucao deve usar o snapshot candidato, pois a arvore FINAL tem ULTIMO_MARCO legitimamente atualizado.

F3-INT-117: somente inspecao e proposta apos verificacao desta promocao; implementacao nao autorizada.
'''.encode('utf8')
    payload['audit/RELATORIO_F3_INT116_FINAL.md'] = report
    preservation = {n:dict(sha256=d,preserved_path=historical_ultimate if n=='audit/ULTIMO_MARCO.json' else n)
                    for n,d in pins.items()}
    manifest = dict(stage='F3-INT-116',checkpoint_type='FINAL',f3='OPEN',locks=dict.fromkeys(LOCKS,False),
        offline=True,simulation_only=True,certification=False,
        files_sha256={n:sha(data) for n,data in sorted(payload.items())},
        preservation_of_approved_candidate=preservation,
        historical_manifest_scopes={'audit/MANIFESTO_F3_INT116_CANDIDATA.json':'candidata_preservada/audit',
            'audit/MANIFESTO_F3_INT115_FINAL.json':'base_f3_int115_final'},
        excluded_self='audit/MANIFESTO_F3_INT116_FINAL.json',
        excluded_sidecar='audit/MANIFESTO_F3_INT116_FINAL.json.sha256')
    payload['audit/MANIFESTO_F3_INT116_FINAL.json'] = encode(manifest)
    payload['audit/MANIFESTO_F3_INT116_FINAL.json.sha256'] = (
        sha(payload['audit/MANIFESTO_F3_INT116_FINAL.json'])+'  MANIFESTO_F3_INT116_FINAL.json\n').encode('ascii')
    STAGING.mkdir()
    for name,data in sorted(payload.items()):
        p = STAGING / name
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as stream:
            stream.write(data)
    verify({n:sha(data) for n,data in payload.items()}, STAGING)
    expected = {'f3_int116_final/'+n:data for n,data in payload.items()}
    with zipfile.ZipFile(PENDING,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(expected.items()):
            z.writestr(name,data)
    with zipfile.ZipFile(PENDING) as z:
        require(z.testzip() is None,'FINAL ZIP CRC error')
        require(len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected),'ZIP members mismatch')
        for name in z.namelist():
            p=PurePosixPath(name)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in name,'Unsafe ZIP path')
            require(sha(z.read(name))==sha(expected[name]),'ZIP hash mismatch: '+name)
    verify(pins,SOURCE)
    verify(protected,WORK)
    for name,data in alias_history.items():
        require((WORK/name).read_bytes()==data,'Workspace marker changed during staging')
    digest=sha(PENDING.read_bytes())
    STAGING.rename(FINAL)
    PENDING.rename(ZIP)
    published=[]
    try:
        for location in (WORK/'CHECKPOINT_F3_INT116_FINAL.json',WORK/'audit/CHECKPOINT_F3_INT116_FINAL.json'):
            with location.open('xb') as stream:stream.write(final_bytes)
        with (WORK/'audit/MANIFESTO_F3_INT116_FINAL.json').open('xb') as stream:
            stream.write(payload['audit/MANIFESTO_F3_INT116_FINAL.json'])
        for alias in aliases:
            temp=OUT/(alias.parent.name+'_ULTIMO_MARCO.pending')
            with temp.open('xb') as stream:stream.write(final_bytes)
            os.replace(temp,alias)
            published.append(alias)
        require(all(p.read_bytes()==final_bytes for p in aliases),'Published marker mismatch')
        require(all((WORK/n).read_bytes()==final_bytes for n in ('CHECKPOINT_F3_INT116_FINAL.json','audit/CHECKPOINT_F3_INT116_FINAL.json')),'Published checkpoint mismatch')
        verify({n:sha(data) for n,data in payload.items()},FINAL)
        verify(pins,SOURCE)
        verify(protected,WORK)
        verify(before['historical_files'],FINAL/'base_f3_int115_final')
        for n,item in preservation.items():
            require(sha((FINAL/item['preserved_path']).read_bytes())==item['sha256'],'Historical preservation mismatch')
        require(sha(ZIP.read_bytes())==digest,'FINAL ZIP changed')
        validation=dict(approved=True,promoted=True,stage='F3-INT-116 FINAL',zip=str(ZIP),sha256=digest,
            crc_ok=True,unique_safe_members=True,zip_members=len(expected),manifest_entries=len(manifest['files_sha256']),
            all_member_hashes_ok=True,source_files_unchanged=len(sources),candidate_files_preserved=len(pins),
            previous_final_files_preserved=875,workspace_previous_final_artifacts_preserved=len(protected),
            workspace_markers_published=True,checkpoint_and_ultimo_identical=True,
            f3='OPEN',locks=dict.fromkeys(LOCKS,False),real_operations_authorized=False,
            stage117_implemented=False)
        (OUT/'VALIDACAO_PROMOCAO_FINAL.json').write_bytes(encode(validation))
        (OUT/'RELATORIO_PROMOCAO.md').write_bytes(report)
        with Path(str(ZIP)+'.sha256').open('x',encoding='ascii') as stream:stream.write(digest+'  '+ZIP.name+'\n')
        print(json.dumps(validation,indent=2),flush=True)
    except BaseException:
        for alias in published:
            temp=OUT/(alias.parent.name+'_ULTIMO_MARCO.rollback')
            temp.write_bytes(alias_history[alias.relative_to(WORK).as_posix()])
            os.replace(temp,alias)
        raise


if __name__=='__main__':
    main()
