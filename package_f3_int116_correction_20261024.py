"""Verify preservation, publish candidate manifest and verify a complete ZIP."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

WORK=Path(__file__).resolve().parent
OUT=WORK/'audit/F3_INT116_CORRECAO_20261024'
SOURCE=WORK/'f3_int116_corrigida'
MOVED=OUT/'Projeto em outra pasta'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}
def require(ok,message):
    if not ok:raise RuntimeError(message)
def check(pins,root):
    require(all((root/n).is_file() and sha(root/n)==h for n,h in pins.items()),'Integrity mismatch: '+str(root))

def main():
    before=json.loads((OUT/'ANTES.json').read_bytes())
    evidence=MOVED/'audit/EVIDENCIAS_F3_INT116_CORRECAO'
    result=json.loads((evidence/'RESULTADO.json').read_bytes())
    require(result['success'] is True and result['exception'] is None and result['optimized'] is True,'Optimized relocated run did not pass')
    require(len(result['runs'])==2,'Missing run')
    require([r['total'] for r in result['runs']]==[17,1438],'Unexpected test count')
    for r in result['runs']:
        require(r['exit_code']==0 and not r['exception'] and not r['timed_out'] and r['failures']==r['errors']==0,'Test failure')
        require(r['cleanup']['confirmed'] is True and r['cleanup']['active_processes']==0 and r['cleanup']['live_io_threads']==[],'Orphan/IPC cleanup failure')
    check(before['original_candidate'],WORK/'f3_int116_work')
    check(before['base_final'],SOURCE/'base_f3_int115_final')
    check(before['base_final'],MOVED/'base_f3_int115_final')
    check(before['base_final'],SOURCE)
    check(before['base_final'],MOVED)
    check(before['corrected_before'],SOURCE)
    check(before['corrected_before'],MOVED)
    runner=SOURCE/'audit/tools/f3_int116_run_audit.py'
    require(not any(isinstance(n,ast.Assert) for n in ast.walk(ast.parse(runner.read_text()))),'Runner contains assert')
    shutil.copytree(evidence,SOURCE/'audit/EVIDENCIAS_F3_INT116_CORRECAO')
    history=SOURCE/'audit/PRESERVADO_F3_INT116_PRE_CORRECAO'
    require(sha(history/'f3_int116_run_audit.py')==before['original_candidate']['audit/tools/f3_int116_run_audit.py'],'Original runner not retained')
    lines=['# F3-INT-116 CANDIDATA CORRIGIDA — 24/10/2026','',
        'Correcao concluida; revisao pendente. Nao houve promocao. F3 OPEN, sete flags false, offline e simulation_only; certification false.', '',
        '## Arquivos e portabilidade','',
        '- Modificado: audit/tools/f3_int116_run_audit.py. Nao ha caminhos absolutos fixos nem instrucoes assert. Caminhos resolvidos a partir de __file__, independentes do cwd.',
        '- Adicionado: audit/tests/test_f3_int116_runner.py, com nove testes novos. Os oito testes de commit existentes foram preservados sem alteracao.',
        '- Base FINAL incluida em base_f3_int115_final, relativa a raiz do projeto. --base aceita somente caminhos internos relativos; --output aponta uma pasta nova relativa a audit. Saidas existentes e escapes sao rejeitados.',
        '- Verificacoes explicitas lancam AuditError para invariantes invalidas; arquivos ausentes ou dados malformados propagam excecoes e encerram com erro. Falhas durante os testes registram success=false e exception; nao iniciam a etapa seguinte.',
        '- O runner nao altera manifestos nem checkpoints ao rodar; manifesto de distribuicao atualizado separadamente apos validacao para evitar sobrescrever evidencias historicas.', '',
        '## Testes e relocacao','',
        'Runner completo executado com python -O -B em audit/F3_INT116_CORRECAO_20261024/Projeto em outra pasta, com cwd na raiz do workspace. A copia relocalizada foi comparada por SHA-256 antes/depois. O supervisor herdado executa as suites sem -O; os nove testes novos lancam subprocessos -O reais, e o runner principal esteve sob -O durante toda a auditoria.', '']
    for r in result['runs']:
        lines.append(f"- {r['label']}: {r['total']} testes; {r['passed']} aprovados; {r['skipped']} skipped; zero falhas/erros; exit code 0; {r['seconds']} s.")
    lines += ['',
        'Novos testes cobrem -O, todos os sete locks, estado F3/offline/simulacao/certificacao, checkpoint divergente, evidencia adulterada, erro/timeout/exit code, processos e IPC remanescentes, contagem incompleta/skips, inventario adulterado, escape de caminho, base ausente, saida historica existente, relocacao independente do cwd e interrupcao do fluxo principal apos rejeicao. O teste do fluxo principal usa resultados simulados para falhas; a execucao relocalizada usa supervisao e suites reais.',
        'Limpeza real confirmada nos dois Jobs: zero processos ativos e nenhuma thread IPC remanescente. A afirmacao cobre os processos supervisionados.', '',
        '## Preservacao e integridade','',
        'Os 875 arquivos da base extraida FINAL permanecem identicos na base e em ambas as copias do projeto. Os 874 pins do manifesto FINAL foram conferidos pelo runner. Os 889 arquivos da candidata anterior continuam intactos em f3_int116_work. Runner anterior, relatorio e manifestos anteriores tambem foram arquivados em PRESERVADO_F3_INT116_PRE_CORRECAO. Nenhum checkpoint FINAL anterior foi alterado.',
        'Manifesto atualizado inclui todos os arquivos de audit, exceto ele proprio e seu sidecar; ambos evitam autorreferencia. O manifesto de pacote cobre todo o payload, incluindo a base FINAL portatil, candidato anterior e evidencias. CRC e SHA-256 de cada membro do ZIP verificados apos a escrita.', '',
        '## Limites','',
        'Um skip de symlink por permissao do Windows permanece. Hashes e ancoras locais nao autenticam custodia ou procedencia. Nao ha resistencia comprovada a perda de energia, exatamente uma vez ou garantia entre computadores. O patch de commit continua restrito a testes isolados. A base distribuida e a arvore extraida, nao o ZIP FINAL original. Nenhuma operacao real autorizada.', '',
        '## Reexecucao','',
        'A partir de qualquer cwd: python -O -B <projeto>/audit/tools/f3_int116_run_audit.py --output EVIDENCIAS_NOVA_REVISAO. Usar sempre nome novo para preservar a evidencia existente.', '',
        'Aguardar revisao antes de promover para FINAL.']
    report='\n'.join(lines)+'\n'
    (SOURCE/'audit/RELATORIO_F3_INT116_CANDIDATA.md').write_text(report,encoding='utf8')
    (OUT/'RELATORIO_CORRECAO.md').write_text(report,encoding='utf8')
    verification=dict(original_candidate_files=len(before['original_candidate']),base_final_files=len(before['base_final']),
        previous_candidate_unchanged=True,final_files_unchanged=True,relocation_hashes_ok=True,
        runner_assert_count=0,optimized_runner=True,supervised_cleanup_confirmed=True,
        modified=['audit/tools/f3_int116_run_audit.py','audit/RELATORIO_F3_INT116_CANDIDATA.md',
                  'audit/MANIFESTO_F3_INT116_CANDIDATA.json','audit/MANIFESTO_F3_INT116_CANDIDATA.json.sha256'],
        new_tests=9,runs=[{k:r[k] for k in ('label','total','passed','skipped','failures','errors','seconds')} for r in result['runs']])
    (OUT/'VERIFICACAO.json').write_text(json.dumps(verification,indent=2),encoding='utf8')
    root=SOURCE/'audit'
    excluded={'MANIFESTO_F3_INT116_CANDIDATA.json','MANIFESTO_F3_INT116_CANDIDATA.json.sha256'}
    pins={n:h for n,h in inventory(root).items() if n not in excluded}
    manifest=root/'MANIFESTO_F3_INT116_CANDIDATA.json'
    manifest.write_text(json.dumps(dict(stage='F3-INT-116',checkpoint_type='CANDIDATE_FOR_REVIEW',f3='OPEN',
        locks=result['locks'],offline=True,simulation_only=True,certification=False,promoted=False,
        files_sha256=pins),indent=2)+'\n',encoding='utf8')
    Path(str(manifest)+'.sha256').write_text(sha(manifest)+'  '+manifest.name+'\n',encoding='ascii')
    check(pins,root)
    files={f'f3_int116_corrigida/{p.relative_to(SOURCE).as_posix()}':p for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    original=WORK/'f3_int116_work'
    files.update({f'historico_f3_int116_anterior/{p.relative_to(original).as_posix()}':p for p in original.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in OUT.iterdir():
        if p.is_file():files['revisao_correcao/'+p.name]=p
    for name in ('prepare_f3_int116_correction_20261024.py','package_f3_int116_correction_20261024.py'):
        files['revisao_correcao/'+name]=WORK/name
    all_pins={n:sha(p) for n,p in sorted(files.items())}
    target=WORK/'audit/F3_INT116_CANDIDATA_CORRIGIDA_COMPLETA_20261024.zip'
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
        z.writestr('MANIFESTO_PACOTE.json',json.dumps(dict(stage='F3-INT-116',status='CANDIDATA',promoted=False,f3='OPEN',files_sha256=all_pins),indent=2))
    with zipfile.ZipFile(target) as z:
        require(z.testzip() is None,'ZIP CRC error')
        require(len(z.namelist())==len(all_pins)+1,'ZIP member count mismatch')
        for n,h in all_pins.items():require(hashlib.sha256(z.read(n)).hexdigest()==h,'ZIP member mismatch: '+n)
    digest=sha(target)
    Path(str(target)+'.sha256').write_text(digest+'  '+target.name+'\n',encoding='ascii')
    (OUT/'PACOTE_VERIFICADO.json').write_text(json.dumps(dict(zip=str(target),sha256=digest,payload_files=len(all_pins),crc_ok=True,all_hashes_ok=True),indent=2),encoding='utf8')
    print(target);print(digest)

if __name__=='__main__':main()
