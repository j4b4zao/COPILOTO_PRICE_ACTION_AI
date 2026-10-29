"""Package verified offline 117 candidate without changing FINAL or markers."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

WORK=Path(__file__).resolve().parent
SOURCE=WORK/'f3_int117_work'
FINAL=WORK/'f3_int116_final'
OUT=WORK/'audit/F3_INT117_CANDIDATA_20261024'
RELOCATED=WORK/'.r117'
ZIP=WORK/'audit/F3_INT117_CANDIDATA_COMPLETA_20261024.zip'

def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}
def check(pins,root):
    for n,h in pins.items():require((root/n).is_file() and sha(root/n)==h,'Integrity mismatch: '+str(root/n))

def main():
    before=json.loads((OUT/'ANTES.json').read_bytes())
    e=RELOCATED/'audit/EVIDENCIAS_F3_INT117'
    a=json.loads((e/'ANTES.json').read_bytes()); r=json.loads((e/'RESULTADO.json').read_bytes())
    require(r['success'] is True and r['exception'] is None and r['optimized'] is True and r['historical_integrity_verified_after'] is True,'Relocated optimized audit failed')
    require(len(r['runs'])==2 and [v['total'] for v in r['runs']]==[21,1459],'Unexpected runs/counts')
    for run in r['runs']:
        require(run['exit_code']==0 and run['exception'] is None and run['timed_out'] is False and run['failures']==run['errors']==0,'Failed run')
        cleanup=run['cleanup'];require(cleanup['confirmed'] is True and cleanup['active_processes']==0 and cleanup['live_io_threads']==[],'Process cleanup failed')
        x=json.loads((e/(run['label']+'.log.execution.json')).read_bytes())
        require(all(run.get(k)==v for k,v in x.items()),'Execution metadata mismatch')
    check(before['final_before'],FINAL)
    check(before['final_before'],SOURCE)
    check(before['final_before'],SOURCE/'b116')
    check(before['candidate_before'],SOURCE)
    check(before['candidate_before'],RELOCATED)
    check(before['workspace_markers'],WORK)
    src={n:h for n,h in inventory(SOURCE/'audit').items() if n.endswith('.py')}
    require(a['sources_before']==r['sources_before']==src,'Executed source mismatch')
    for name in ('f3_int117_sqlite_write_faults.py','f3_int117_run_audit.py'):
        tree=ast.parse((SOURCE/'audit/tools'/name).read_text())
        require(not any(isinstance(n,ast.Assert) for n in ast.walk(tree)),'Critical assert present')
        require(not any(isinstance(n,ast.ImportFrom) and n.module=='unittest.mock' for n in ast.walk(tree)),'Global mock instrumentation present')
    specific=(e/'ESPECIFICOS.log').read_text(encoding='utf8')
    experiments=[json.loads(line) for line in specific.splitlines() if line.startswith('{"experiment": "F3-INT-117"')]
    require(len(experiments)==3 and {x['mode'] for x in experiments}=={'normal','full','readonly'},'Missing native experiment evidence')
    for x in experiments:
        if x['mode']!='normal':
            expected=13 if x['mode']=='full' else 8
            require(x['attempt']['error']['primary_code']==expected and x['attempt']['error']['phase']=='UPDATE','Native error/phase mismatch')
            require(x['database_unchanged_on_failure'] is True,'Failure changed database')
        require(x['growth_control']['pages_after']>x['growth_control']['pages_before'],'No real growth control')
        require(x['fixture_removed'] is True and x['automatic_retries']==0 and x['retry_allowed'] is False,'Unsafe cleanup/retry')
    shutil.copytree(e,SOURCE/'audit/EVIDENCIAS_F3_INT117')
    report=['# F3-INT-117 CANDIDATA — 24/10/2026','',
        'Status: CANDIDATA PARA AUDITORIA. Base F3-INT-116 FINAL. Nenhuma promocao. F3 OPEN; sete flags false; offline/simulation_only true, certification false, retry_allowed false. Nenhuma operacao real.', '',
        '## Arquivos criados e preservacao','',
        'Quatro fontes novos; nenhum fonte herdado modificado:',
        *['- '+name for name in before['added_sources']],
        '- audit/EVIDENCIAS_F3_INT117/: inventarios, logs e metadados das duas execucoes supervisionadas.',
        '- audit/RELATORIO_F3_INT117_CANDIDATA.md, audit/MANIFESTO_F3_INT117_CANDIDATA.json e sidecar.',
        '- Scripts de preparacao/empacotamento e inventario externo preservados em candidate_build/ no ZIP.', '',
        f"Todos os {len(before['final_before'])} arquivos da base FINAL foram conferidos antes/depois na origem, na candidata e em b116/. Os marcadores do workspace e o checkpoint F3-INT-116 FINAL continuam inalterados. Os 1438 testes herdados nao foram editados. A copia da base e somente insumo de auditoria; nunca recebe escrita dos experimentos.", '',
        '## Implementacao e resultados SQLite','',
        'A sonda usa apenas conexoes proprias e diretorios TemporaryDirectory. Nao substitui store._connect, consume_chain, sqlite3.connect nem outros globais. O escritor offline independente reutiliza _load/_encode/_digest e verify_typed_chain da base; nao e uma nova instrumentacao de consume_chain. Reconciliacao e replay usam os modulos herdados inalterados.',
        'Fixtures contem historico canonico sintetico, explicitamente nao autenticado. Ancoras before/after sao calculadas e retidas antes da tentativa. Uma calibracao limitada prepara copias independentes, comprova crescimento real no controle e exige identidade dos bytes iniciais entre controle e alvo.', '',
        '| Cenario | Resultado nativo | Fase observada | Estado reaberto |',
        '|---|---|---|---|',
        '| Controle sem limite | Commit concluido | COMMIT retornou | after-state integral |',
        '| Limite de paginas | SQLITE_FULL (13) | UPDATE | before-state integral |',
        '| Conexao URI mode=ro | SQLITE_READONLY (8) | UPDATE | before-state integral |', '',
        'O controle cresceu de 2 para 3 paginas de 512 bytes. FULL aplicou e leu de volta max_page_count=2 na mesma conexao usada pelo escritor. A tentativa falhou antes de entrar em commit. READONLY usou acesso ro com query_only=0; o codigo veio do motor, nao de excecao Python fabricada. As duas falhas mantiveram tambem o hash dos bytes do banco.',
        'Apos fechamento/reabertura: integrity_check=ok, estado canonico comparado integralmente, ancoras preservadas e reconciliacao NOT_COMMITTED_OBSERVED_UNAUTHENTICATED nas falhas; COMMITTED_OBSERVED_UNAUTHENTICATED no controle. Referencias divergentes retornaram RECONCILIATION_UNRESOLVED; ancora ausente retornou INVALID_RECONCILIATION_PIN. Nenhum desses estados concede retry.',
        'Replay de cadeia ja registrada: STATE_ANCHOR_MISMATCH com ancora antiga e STALE_CHAIN_REVISION com ancora atual. No controle positivo, a cadeia recem-gravada tambem foi rejeitada nas duas modalidades. A operacao cuja escrita falhou nao e falsamente declarada consumida: ela nao foi repetida; automatic_retries=0. As tentativas explicitas de replay exercitam cadeias ja consumidas, nao um retry automatico da operacao que falhou.', '',
        '## Execucoes e integridade dos fontes','',
        'Runner independente executado com python -O -B em .r117, outra pasta, com cwd na raiz do workspace. Os testes tambem verificam relocacao com espacos. O supervisor herdado executa suites em modo normal; os testes novos lancam subprocessos -O reais e exercitam FULL/READONLY sob otimizacao. Ambos os novos modulos de ferramentas possuem zero assert critico.',
        'Os 21 IDs novos foram fixados antes da execucao, e todos aparecem exatamente uma vez em cada suite. O runner rejeita ausencias/duplicatas, resumo divergente, erros, skips inesperados, mudanca de fonte e limpeza nao confirmada. Falha no primeiro conjunto impede iniciar regressao. Antes/depois e RESULTADO fixam os mesmos fontes da versao empacotada.', '']
    for run in r['runs']:
        report.append(f"- {run['label']}: {run['total']} testes, {run['passed']} aprovados, {run['skipped']} skipped, {run['failures']} falhas, {run['errors']} erros; exit code {run['exit_code']}; supervisao {run['seconds']} s. Cleanup confirmado, zero processos ativos e threads IPC remanescentes.")
    report += ['',
        'Os 21 testes novos cobrem erros nativos, crescimento comprovado e limite efetivo, fase exata da API, controle positivo, integridade/estado reaberto, reconciliacao, replay, referencias invalidas, ausencia de patches globais, remocao das fixtures, flags, entradas invalidas, -O, portabilidade, output historico e falhas do runner. Testes de metadados de erro/limpeza usam dependencia supervisor explicita; a execucao completa usa Job Objects e resultados reais.', '',
        '## Problemas e limitacoes','',
        '- Durante desenvolvimento foram corrigidos somente detalhes de binding de referencia de funcao e captura da classe AuditError em modulos de teste relocalizados. O primeiro log de desenvolvimento nao e evidencia de aprovacao; a aprovacao candidata depende das novas suites supervisionadas da versao final.',
        '- Um skip herdado de symlink no Windows permanece por falta de permissao. Nenhum teste foi relaxado para eliminar esse skip.',
        '- FULL por limite de paginas nao significa disco fisico cheio. READONLY por URI nao testa ACLs do Windows. Nao houve SQLITE_IOERR, VFS customizado, morte dentro do motor ou perda de energia.',
        '- A fase registrada e a chamada da API SQLite (UPDATE nos dois casos), nao um ponto interno do motor nem falha durante commit.',
        '- Este escritor de ensaio independente nao comprova que todas as rotas internas de consume_chain foram exercitadas por esses dois erros. As rotas herdadas de consumo/replay/reconciliacao continuam cobertas pela regressao e pelos replays explicitos.',
        '- Fixtures/ancoras/hashes locais nao constituem custodia autenticada, proveniencia independente, exactly-once ou garantia entre computadores. Rollback conjunto de banco e ancoras continua um limite.',
        '- Cleanup confirmado cobre os Jobs supervisionados e as fixtures dos ensaios bem-sucedidos, nao todos os processos ou temporarios do computador. Comparacoes antes/depois nao detectam alteracoes transitorias restauradas.', '',
        '## Pacote e reexecucao','',
        'ZIP inclui toda a arvore f3_int117_work, base b116 completa, todos os historicos herdados, fontes novos, evidencias e artefatos de preparacao. Manifesto fixa todo o projeto exceto ele proprio e seu sidecar. CRC, caminhos e SHA-256 de cada membro verificados depois da escrita. Hash do ZIP e validacao final ficam fora do proprio pacote para evitar autorreferencia.',
        'Reexecucao em pasta nova: python -O -B <projeto>/audit/tools/f3_int117_run_audit.py --output EVIDENCIAS_NOVAS. --base e relativo a raiz do projeto; default b116. Nenhum output existente e sobrescrito.', '',
        'Aguardar auditoria antes de qualquer promocao para FINAL.']
    text='\n'.join(report)+'\n'
    (SOURCE/'audit/RELATORIO_F3_INT117_CANDIDATA.md').write_text(text,encoding='utf8')
    (OUT/'RELATORIO_TECNICO.md').write_text(text,encoding='utf8')
    summary=dict(stage='F3-INT-117',status='CANDIDATA',promoted=False,f3='OPEN',locks=r['locks'],
        original_final_files_verified=len(before['final_before']),inherited_files_modified=[],
        executed_sources_verified=len(src),new_specific_tests=21,
        native_failures=[dict(mode=x['mode'],error=x['attempt']['error'],growth=x['growth_control']) for x in experiments],
        runs=[{k:run[k] for k in ('label','total','passed','skipped','failures','errors','seconds')} for run in r['runs']],
        source_sha256=src)
    (OUT/'VERIFICACAO.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    excluded={'audit/MANIFESTO_F3_INT117_CANDIDATA.json','audit/MANIFESTO_F3_INT117_CANDIDATA.json.sha256'}
    pins={n:h for n,h in inventory(SOURCE).items() if n not in excluded}
    mf=SOURCE/'audit/MANIFESTO_F3_INT117_CANDIDATA.json'
    mf.write_text(json.dumps(dict(stage='F3-INT-117',checkpoint_type='CANDIDATE_FOR_REVIEW',
        f3='OPEN',locks=r['locks'],offline=True,simulation_only=True,certification=False,promoted=False,
        retry_allowed=False,files_sha256=pins),indent=2)+'\n',encoding='utf8')
    Path(str(mf)+'.sha256').write_text(sha(mf)+'  '+mf.name+'\n',encoding='ascii')
    check(pins,SOURCE)
    files={'f3_int117_work/'+p.relative_to(SOURCE).as_posix():p for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in OUT.iterdir():
        if p.is_file():files['candidate_build/'+p.name]=p
    for name in ('prepare_f3_int117_candidate_20261024.py','package_f3_int117_candidate_20261024.py'):
        files['candidate_build/'+name]=WORK/name
    payload={n:sha(p) for n,p in sorted(files.items())}
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
        z.writestr('MANIFESTO_PACOTE.json',json.dumps(dict(stage='F3-INT-117',status='CANDIDATA',promoted=False,files_sha256=payload),indent=2))
    with zipfile.ZipFile(ZIP) as z:
        require(z.testzip() is None,'ZIP CRC failure')
        require(len(z.namelist())==len(set(z.namelist()))==len(payload)+1,'ZIP member count mismatch')
        for name,digest in payload.items():
            require(not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name,'Unsafe ZIP path')
            require(hashlib.sha256(z.read(name)).hexdigest()==digest,'ZIP SHA mismatch: '+name)
    check(before['final_before'],FINAL);check(before['workspace_markers'],WORK)
    digest=sha(ZIP)
    Path(str(ZIP)+'.sha256').write_text(digest+'  '+ZIP.name+'\n',encoding='ascii')
    (OUT/'PACOTE_VERIFICADO.json').write_text(json.dumps(dict(zip=str(ZIP),sha256=digest,
        manifest_entries=len(pins),zip_members=len(payload)+1,crc_ok=True,all_hashes_ok=True,
        final116_unchanged=True,workspace_markers_unchanged=True),indent=2),encoding='utf8')
    print(ZIP);print(digest)

if __name__=='__main__':main()
