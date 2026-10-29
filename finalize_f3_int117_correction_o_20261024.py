"""Add full -O evidence; preserve the first corrected ZIP and every source."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
WORK=Path(__file__).resolve().parent
SOURCE=WORK/'f3_int117_corrigida'
OLD=WORK/'f3_int117_work'
OUT=WORK/'audit/F3_INT117_CORRECAO_20261024'
TARGET=WORK/'audit/F3_INT117_CANDIDATA_CORRIGIDA_COMPLETA_20261024_R2.zip'

def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}
def check(pins,root):
    for n,h in pins.items():require((root/n).is_file() and sha(root/n)==h,'Integrity mismatch: '+str(root/n))

def main():
    before=read(OUT/'ANTES.json');extra=read(OUT/'VALIDACAO_TODOS_O.json')
    require(extra['counts']==dict(total=35,passed=35,failures=0,errors=0,skipped=0),'Full optimized specifics failed')
    x=extra['execution'];require(x['exit_code']==0 and x['exception'] is None and not x['timed_out'],'Optimized execution failed')
    require(x['cleanup']['confirmed'] and x['cleanup']['active_processes']==0 and x['cleanup']['live_io_threads']==[],'Optimized cleanup failed')
    e=SOURCE/'audit/EVIDENCIAS_F3_INT117_CORRECAO'
    result=read(e/'RESULTADO.json')
    check(result['sources_before'],SOURCE/'audit')
    check(before['final_before'],WORK/'f3_int116_final');check(before['final_before'],SOURCE)
    check(before['previous_candidate_before'],OLD);check(before['workspace_markers'],WORK)
    check(before['release_hashes'],WORK/'audit')
    previous=read(OUT/'PACOTE_VERIFICADO.json')
    require(sha(Path(previous['zip']))==previous['sha256'],'First corrected ZIP changed')
    mf=SOURCE/'audit/MANIFESTO_F3_INT117_CANDIDATA.json'
    manifest=read(mf);check(manifest['files_sha256'],SOURCE)
    text=(OUT/'ESPECIFICOS_TODOS_O.log').read_text(encoding='utf8')
    ids=re.findall(r'^test_\w+ \((test_f3_int117_[^)]+)\) \.\.\.',text,re.M)
    require(len(ids)==35 and set(ids)==set(result['expected_test_ids']),'Optimized IDs mismatch')
    supplemental=e/'O'
    supplemental.mkdir(exist_ok=False)
    for name in ('ESPECIFICOS_TODOS_O.log','ESPECIFICOS_TODOS_O.log.execution.json','VALIDACAO_TODOS_O.json'):
        shutil.copy2(OUT/name,supplemental/name)
    paragraph=('\n## Validacao integral adicional com python -O\n\n'
        'Todos os 35 testes especificos da mesma versao foram executados integralmente em um interpretador real -O: '
        '35 aprovados, zero skips, falhas ou erros; exit code 0. Cleanup do Job confirmado, zero processos ativos e threads IPC remanescentes. '
        'Esta execucao adicional cobre tambem os casos de precedencia e auxiliares alem dos seis cenarios selecionados ja incorporados aos testes. '
        'Evidencias completas: audit/EVIDENCIAS_F3_INT117_CORRECAO/O/. Nenhum fonte foi alterado entre a regressao de 1473 testes e esta execucao; '
        'os mesmos hashes dos 233 fontes inventariados foram reconferidos. A regressao nao precisou ser repetida, pois nao houve mudanca de codigo.\n\n'
        'Entrega R2 inclui essas evidencias suplementares. O primeiro ZIP corrigido foi preservado com SHA-256 '+previous['sha256']+'. '
        'R2 altera somente relatorio, manifesto e inclusao das evidencias -O; codigo e testes sao os mesmos. Status CANDIDATA para nova auditoria.\n')
    report=SOURCE/'audit/RELATORIO_F3_INT117_CANDIDATA.md'
    report.write_text(report.read_text(encoding='utf8')+paragraph,encoding='utf8')
    (OUT/'RELATORIO_CORRECAO.md').write_bytes(report.read_bytes())
    verification=read(OUT/'VERIFICACAO.json')
    verification['all_specifics_optimized']=extra['counts']
    verification['first_corrected_zip_sha256']=previous['sha256']
    (OUT/'VERIFICACAO.json').write_text(json.dumps(verification,indent=2),encoding='utf8')
    exclude={'audit/MANIFESTO_F3_INT117_CANDIDATA.json','audit/MANIFESTO_F3_INT117_CANDIDATA.json.sha256'}
    pins={n:h for n,h in inventory(SOURCE).items() if n not in exclude}
    manifest['files_sha256']=pins
    manifest['package_revision']='R2_FULL_SPECIFICS_O'
    mf.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    Path(str(mf)+'.sha256').write_text(sha(mf)+'  '+mf.name+'\n',encoding='ascii')
    check(pins,SOURCE);check(result['sources_before'],SOURCE/'audit')
    files={'f3_int117_corrigida/'+p.relative_to(SOURCE).as_posix():p for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update({'historico117/'+p.relative_to(OLD).as_posix():p for p in OLD.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in OUT.iterdir():
        if p.is_file():
            name='VALIDACAO_PACOTE_R1.json' if p.name=='PACOTE_VERIFICADO.json' else p.name
            files['correction_build/'+name]=p
    for name in ('prepare_f3_int117_correction_20261024.py','package_f3_int117_correction_20261024.py','finalize_f3_int117_correction_o_20261024.py'):
        files['correction_build/'+name]=WORK/name
    package_pins={n:sha(p) for n,p in sorted(files.items())}
    with zipfile.ZipFile(TARGET,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
        z.writestr('MANIFESTO_PACOTE.json',json.dumps(dict(stage='F3-INT-117',status='CANDIDATA_CORRIGIDA',revision='R2',promoted=False,files_sha256=package_pins),indent=2))
    with zipfile.ZipFile(TARGET) as z:
        require(z.testzip() is None,'ZIP CRC failure')
        require(len(z.namelist())==len(set(z.namelist()))==len(package_pins)+1,'ZIP member count mismatch')
        for n,h in package_pins.items():
            require(not Path(n).is_absolute() and '..' not in Path(n).parts and '\\' not in n,'Unsafe ZIP path')
            require(hashlib.sha256(z.read(n)).hexdigest()==h,'ZIP member mismatch: '+n)
    check(before['final_before'],WORK/'f3_int116_final');check(before['workspace_markers'],WORK)
    check(before['previous_candidate_before'],OLD);check(before['release_hashes'],WORK/'audit')
    digest=sha(TARGET)
    Path(str(TARGET)+'.sha256').write_text(digest+'  '+TARGET.name+'\n',encoding='ascii')
    (OUT/'PACOTE_VERIFICADO_R2.json').write_text(json.dumps(dict(zip=str(TARGET),sha256=digest,
        manifest_entries=len(pins),zip_members=len(package_pins)+1,crc_ok=True,all_member_hashes_ok=True,
        all_35_specifics_optimized=True,final116_unchanged=True,workspace_markers_unchanged=True,
        previous_candidate_unchanged=True,promoted=False),indent=2),encoding='utf8')
    print(TARGET);print(digest)

if __name__=='__main__':main()
