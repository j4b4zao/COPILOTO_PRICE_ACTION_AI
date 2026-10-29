"""Offline F3-INT-115 audit and explicitly authorized final consolidation.

No stage-116 work. Final ZIP is validated before publishing ULTIMO_MARCO.
Local hashes and process tests are not independent attestation or durability.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(ROOT))
from tools.f3_int115_process_control import run_supervised
from tools.f3_int115_run_candidate import source_inventory, summarize, compare_inventories
from tools.f3_int114_custody_recovery import LOCKS

AUDIT = ROOT/'AUDITORIA_F3_INT115_PRE_FINAL_20261023'
RETEST = ROOT/'F3_INT115_REVALIDACAO_FINAL_20261023'
CANDIDATE = ROOT/'F3_INT115_CANDIDATA_CORRIGIDA_20261023'
HISTORY_COPY = 'HISTORICO_ULTIMO_MARCO_F3_INT114_FINAL_20261023.json'
ZIP = WORKSPACE/'PACOTE_AUDITORIA_F3_INT115_FINAL.zip'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True)+'\n').encode('utf8')


def verify(pins, root=ROOT):
    bad = [p for p,d in pins.items() if not (root/p).is_file() or sha((root/p).read_bytes()) != d]
    if bad:
        raise RuntimeError('Hash mismatch: '+repr(bad))
    return len(pins)


def safety(checkpoint, stage, kind):
    assert checkpoint['stage']==stage and checkpoint['checkpoint_type']==kind
    assert checkpoint['f3']=='OPEN' and checkpoint['offline'] is True
    assert checkpoint['simulation_only'] is True and checkpoint['certification'] is False
    assert set(checkpoint['locks'])==set(LOCKS)
    assert all(v is False for v in checkpoint['locks'].values())


def audit():
    pins = json.loads((CANDIDATE/'MANIFESTO_SHA256.json').read_text())
    assert len(pins)==23
    verify(pins)
    history = json.loads((ROOT/'CHECKPOINT_F3_INT115_CANDIDATA.json').read_text())['historical_inventory_before_runner']
    assert len(history)==772
    verify(history)
    safety(json.loads((ROOT/'ULTIMO_MARCO.json').read_text()), 'F3-INT-114', 'FINAL')
    if any((ROOT/name).exists() for name in ('CHECKPOINT_F3_INT115_FINAL.json','RELATORIO_F3_INT115_FINAL.md','MANIFESTO_F3_INT115_FINAL.json',HISTORY_COPY)) or ZIP.exists():
        raise FileExistsError('Final artifact already exists; never overwrite')
    AUDIT.mkdir()
    baseline = {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in ROOT.rglob('*') if p.is_file()}
    before = dict(candidate_hashes=23, historical_hashes=772, candidate_manifest=pins,
                  historical_inventory=history, all_preexisting=baseline,
                  source_inventory=source_inventory(), f3='OPEN', locks=dict.fromkeys(LOCKS,False))
    (AUDIT/'ANTES.json').write_bytes(encoded(before))
    print('VERIFIED 23 candidate hashes and 772 historical hashes; RUNNING REVALIDATION',flush=True)
    result = run_supervised([sys.executable,'-B',str(ROOT/'tools/f3_int115_run_candidate.py'),
                             '--output',RETEST.name],cwd=ROOT,
                             log=AUDIT/'SUPERVISAO_RUNNER.log',timeout=3000)
    verify(baseline)
    verify(pins)
    verify(history)
    evidence = json.loads((RETEST/'CHECKPOINT_CANDIDATA_CORRIGIDA.json').read_text())
    verify(json.loads((RETEST/'MANIFESTO_SHA256.json').read_text()))
    assert evidence['success'] is True
    assert result['exit_code']==0 and not result['exception'] and not result['timed_out']
    assert result['cleanup']['active_processes']==0 and result['cleanup']['live_io_threads']==[]
    assert len(evidence['runs'])==2
    for run, total, skips in zip(evidence['runs'],(28,1416),(0,1)):
        assert run['total']==total and run['skipped']==skips
        assert run['failures']==0 and run['errors']==0 and run['exit_code']==0
        assert run['cleanup']['active_processes']==0 and run['cleanup']['live_io_threads']==[]
        assert not run['sources_changed'] and not run['exception'] and not run['timed_out']
    full=(RETEST/'REGRESSAO_COMPLETA.log').read_text(encoding='utf8',errors='replace')
    skipped=[line for line in full.splitlines() if "... skipped '" in line]
    assert len(skipped)==1 and 'test_symlink_rejected' in skipped[0] and 'Symlink not permitted' in skipped[0]
    for filename in ('ESPECIFICOS.log','REGRESSAO_COMPLETA.log'):
        text=(RETEST/filename).read_text(encoding='utf8',errors='replace')
        assert '"overlap_proven": true' in text and '"holder_release_sent": false' in text
        assert 'test_lost_ack_retry_with_current_anchor_rejects_replay' in text
        assert 'test_job_assignment_failure_never_releases_gate' in text
    assert not compare_inventories(before['source_inventory'], source_inventory())
    approved = dict(approved=True, checkpoint_type='AUDIT_APPROVED_FOR_AUTHORIZED_CONSOLIDATION',
        candidate_hashes_verified=23,historical_hashes_verified=772, source_files_verified=len(before['source_inventory']),
        all_preexisting_verified=len(baseline), runs=evidence['runs'], supervisor=result,
        five_corrections_reviewed=True, overlap_required=True, retry_blocked=True,
        bounded_local_ipc_observed=True, skip_evidence=skipped,
        limits=['Local Windows deadlines depend on OS scheduling; no hard realtime guarantee',
                'No independent custody, executable authentication or physical durability proven',
                'No cross-host fencing or exactly-once delivery claim'],
        f3='OPEN',locks=dict.fromkeys(LOCKS,False))
    (AUDIT/'APROVACAO_AUDITORIA.json').write_bytes(encoded(approved))
    print('AUDIT APPROVED; no promotion performed by audit phase',flush=True)


def validate_zip(path, expected, historical, old_ultimate):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert len(names)==len(set(names)) and set(names)==set(expected)
        for name in names:
            p=PurePosixPath(name)
            assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
            assert sha(z.read(name))==sha(expected[name]),name
        manifest=json.loads(z.read('audit/MANIFESTO_F3_INT115_FINAL.json'))
        assert manifest['checkpoint_type']=='FINAL'
        for name,d in manifest['files_sha256'].items():
            assert sha(z.read(name))==d,name
        ultimate=z.read('audit/ULTIMO_MARCO.json')
        assert ultimate==z.read('audit/CHECKPOINT_F3_INT115_FINAL.json')
        safety(json.loads(ultimate),'F3-INT-115','FINAL')
        assert z.read('audit/'+HISTORY_COPY)==old_ultimate
        safety(json.loads(z.read('audit/'+HISTORY_COPY)),'F3-INT-114','FINAL')
        for name,d in historical.items():
            archived='audit/'+(HISTORY_COPY if name=='ULTIMO_MARCO.json' else name)
            assert sha(z.read(archived))==d,archived
    return dict(crc_ok=True, unique_safe_paths=True, entries=len(expected),
                all_entry_hashes_verified=True, historical_hashes_verified=772,
                historical_ultimate_mapped_to='audit/'+HISTORY_COPY,
                final_checkpoint_and_ultimate_identical=True)


def consolidate():
    before=json.loads((AUDIT/'ANTES.json').read_text())
    approved=json.loads((AUDIT/'APROVACAO_AUDITORIA.json').read_text())
    assert approved['approved'] is True
    verify(before['all_preexisting'])
    verify(before['candidate_manifest'])
    verify(before['historical_inventory'])
    assert not compare_inventories(before['source_inventory'],source_inventory())
    safety(json.loads((ROOT/'ULTIMO_MARCO.json').read_text()),'F3-INT-114','FINAL')
    final_names=('CHECKPOINT_F3_INT115_FINAL.json','RELATORIO_F3_INT115_FINAL.md','MANIFESTO_F3_INT115_FINAL.json',HISTORY_COPY)
    for name in final_names:
        if (ROOT/name).exists():
            raise FileExistsError(name)
    pending=Path(str(ZIP)+'.pending')
    external=WORKSPACE/'VALIDACAO_PACOTE_F3_INT115_FINAL.json'
    sidecar=Path(str(ZIP)+'.sha256')
    for path in (pending, ZIP, external, sidecar):
        if path.exists():
            raise FileExistsError(path)
    old=(ROOT/'ULTIMO_MARCO.json').read_bytes()
    protected={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in ROOT.rglob('*') if p.is_file()}
    checkpoint=dict(stage='F3-INT-115',checkpoint_type='FINAL',date='2026-10-23',
        previous_definitive='F3-INT-114 FINAL',f3='OPEN',offline=True,simulation_only=True,certification=False,
        status='OFFLINE_AUDIT_AND_REGRESSION_APPROVED_WITH_WINDOWS_SYMLINK_SKIP',
        locks=dict.fromkeys(LOCKS,False),new_tests=approved['runs'][0],windows_full_regression=approved['runs'][1],
        audit_approval='AUDITORIA_F3_INT115_PRE_FINAL_20261023/APROVACAO_AUDITORIA.json',
        corrected_candidate_hashes_verified=23,historical_hashes_preserved=772,
        previous_ultimate_preserved=dict(path=HISTORY_COPY,sha256=sha(old)),
        five_corrections_approved=True,limits=approved['limits']+[
            'Symlink test skipped on Windows due to permission',
            'Kill checkpoints do not demonstrate failure inside commit or resistance to power loss',
            'Before/after hashes do not detect transient source changes restored before comparison'],
        final_manifest='MANIFESTO_F3_INT115_FINAL.json',next_step_authorized=False)
    final=encoded(checkpoint)
    report=['# F3-INT-115 FINAL - auditoria e consolidacao offline','',
        'Data: 2026-10-23. Base: C:/COPILOTO_F3_INT114_FINAL.',
        'Consolidacao expressamente autorizada apos auditoria aprovada. F3 permanece OPEN; sete flags false.',
        'FINAL designa este marco offline, sem autorizacao operacional ou certificacao de seguranca real.','',
        '## Auditoria tecnica','',
        '- Relatorio da candidata corrigida lido integralmente; 23/23 hashes coincidentes antes e depois.',
        '- 209 fontes Python da candidata mais o consolidador foram fixados antes e conferidos depois.',
        '- Concorrencia: STORE_BUSY obrigatorio com escritor vivo e retido antes de CONTINUE; execucao serial nao satisfaz o teste.',
        '- IPC: watchdog absoluto, limites de bytes/filas, stdout/stderr drenados e escritores/leitores encerrados.',
        '- Timeout: gate antes de codigo alvo, Job Objects herdados por descendentes e verificacao de limpeza completa.',
        '- SHA-256: inclui fontes 115 e dependencias; mudanca/adicao/exclusao falham fechadas.',
        '- ACK perdido: ancora antiga e atual, retries concorrentes, UNKNOWN e referencias divergentes; sem dupla admissao observada; retry false.',
        '- Os ensaios de bloqueio e timeout comprovaram encerramento local nos casos exercitados; nao garantem prazo estrito sob falha do SO.','',
        '## Novas execucoes','']
    for run in approved['runs']:
        report.append(f"- {run['label']}: {run['total']} testes, {run['passed']} aprovados, {run['failures']} falhas, {run['errors']} erros, {run['skipped']} skips; exit code {run['exit_code']}; {run['seconds']} s; zero processos ativos e threads IPC remanescentes.")
    report+=['','Skip unico: test_symlink_rejected, Symlink not permitted. Nao representa falha de teste; cobertura desse caso continua pendente no Windows.',
        'Logs: audit/F3_INT115_REVALIDACAO_FINAL_20261023/ESPECIFICOS.log e REGRESSAO_COMPLETA.log.',
        'Aprovacao e inventarios: audit/AUDITORIA_F3_INT115_PRE_FINAL_20261023/.','',
        '## Preservacao e publicacao','',
        '- Nenhum codigo candidato alterado nesta auditoria. Relatorios, logs e manifestos anteriores mantidos.',
        '- Unica substituicao autorizada: audit/ULTIMO_MARCO.json, de F3-INT-114 FINAL para F3-INT-115 FINAL.',
        '- Conteudo anterior de ULTIMO_MARCO preservado byte a byte em audit/'+HISTORY_COPY+'.',
        '- Os 772 arquivos do inventario historico sao preservados: 771 nos caminhos originais e o antigo ULTIMO_MARCO na copia historica. O checkpoint F3-INT-114 FINAL preexistente tambem permanece intacto.',
        '- ZIP inclui todo o diretorio audit, sem exclusao de artefatos anteriores, e os novos checkpoint/relatorio/manifesto.',
        '- CRC, nomes, todos os hashes, historicos e checkpoints do ZIP sao conferidos antes de publicar o marco.',
        '- Validacao adicional apos publicacao, hash do ZIP e sidecar ficam fora do proprio ZIP para evitar autorreferencia.',
        '- Manifesto final cobre todos os membros audit exceto seu proprio arquivo; o SHA-256 do ZIP cobre tambem o manifesto.','',
        '## Limites permanentes','',
        '- F3 OPEN; orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed e authenticated_witness_verified permanecem false.',
        '- Sem corretora, Profit, Excel, RTD/DDE, rede ou ordens reais. Nenhum avanco para F3-INT-116.',
        '- Custodia independente, identidade autenticada do executavel e durabilidade fisica nao foram comprovadas.',
        '- Sem validacao entre multiplos computadores ou garantia de entrega exatamente uma vez.',
        '- Falhas induzidas sao locais e em checkpoints; nao demonstram resistencia a perda de energia, midia ou falha dentro de commit.','']
    desired={p.relative_to(WORKSPACE).as_posix():p.read_bytes() for p in ROOT.rglob('*') if p.is_file()}
    desired.update({'audit/ULTIMO_MARCO.json':final,'audit/CHECKPOINT_F3_INT115_FINAL.json':final,
                    'audit/RELATORIO_F3_INT115_FINAL.md':'\n'.join(report).encode('utf8'),
                    'audit/'+HISTORY_COPY:old})
    manifest=dict(stage='F3-INT-115',checkpoint_type='FINAL',f3='OPEN',locks=dict.fromkeys(LOCKS,False),
                  files_sha256={name:sha(data) for name,data in sorted(desired.items())},
                  historical_preservation={name:{'sha256':d,'preserved_path':'audit/'+(HISTORY_COPY if name=='ULTIMO_MARCO.json' else name)}
                                           for name,d in before['historical_inventory'].items()},
                  excluded_self='audit/MANIFESTO_F3_INT115_FINAL.json',
                  external_package_validation=external.name)
    desired['audit/MANIFESTO_F3_INT115_FINAL.json']=encoded(manifest)
    with zipfile.ZipFile(pending,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in sorted(desired.items()):
            z.writestr(name,data)
    validated=validate_zip(pending,desired,before['historical_inventory'],old)
    verify(protected)
    package_sha=sha(pending.read_bytes())
    promoted=False
    try:
        for name in final_names:
            with (ROOT/name).open('xb') as stream:
                stream.write(desired['audit/'+name])
        for name in final_names:
            assert (ROOT/name).read_bytes()==desired['audit/'+name]
        # Publish only after staged ZIP, final files and protected inputs verify.
        pending.rename(ZIP)
        temp=ROOT/'.ULTIMO_MARCO_F3_INT115_PUBLICACAO.tmp'
        with temp.open('xb') as stream:
            stream.write(final)
        os.replace(temp,ROOT/'ULTIMO_MARCO.json')
        promoted=True
        for name,data in desired.items():
            assert (WORKSPACE/name).read_bytes()==data,name
        for name,d in protected.items():
            path=ROOT/(HISTORY_COPY if name=='ULTIMO_MARCO.json' else name)
            assert sha(path.read_bytes())==d,name
        validate_zip(ZIP,desired,before['historical_inventory'],old)
        assert sha(ZIP.read_bytes())==package_sha
        validation=dict(approved=True,stage='F3-INT-115 FINAL',zip=str(ZIP),zip_sha256=package_sha,
                        package_checks=validated,all_preexisting_preserved=len(protected),
                        authorized_change='audit/ULTIMO_MARCO.json',prior_content_copy='audit/'+HISTORY_COPY,
                        f3='OPEN',locks=dict.fromkeys(LOCKS,False),next_stage_started=False)
        external.write_bytes(encoded(validation))
        sidecar.write_text(package_sha+'  '+ZIP.name+'\n',encoding='ascii')
        print(json.dumps(validation),flush=True)
    except BaseException:
        if promoted:
            rollback=ROOT/'.ULTIMO_MARCO_F3_INT115_ROLLBACK.tmp'
            rollback.write_bytes(old)
            os.replace(rollback,ROOT/'ULTIMO_MARCO.json')
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('phase',choices=('audit','consolidate'))
    phase=p.parse_args().phase
    audit() if phase=='audit' else consolidate()
