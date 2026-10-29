"""Release only a hash-verified corrected candidate, never a FINAL checkpoint."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
WORK=Path(__file__).resolve().parent
SOURCE=WORK/'f3_int117_corrigida'
OLD=WORK/'f3_int117_work'
FINAL=WORK/'f3_int116_final'
OUT=WORK/'audit/F3_INT117_CORRECAO_20261024'
MOVED=WORK/'.r117c'
ZIP=WORK/'audit/F3_INT117_CANDIDATA_CORRIGIDA_COMPLETA_20261024.zip'

def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}
def check(pins,root):
    for n,h in pins.items():require((root/n).is_file() and sha(root/n)==h,'Integrity mismatch: '+str(root/n))
def test_ids(path):
    tree=ast.parse(path.read_text())
    return {path.stem+'.'+c.name+'.'+n.name for c in tree.body if isinstance(c,ast.ClassDef)
            for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}

def main():
    before=json.loads((OUT/'ANTES.json').read_bytes())
    e=MOVED/'audit/EVIDENCIAS_F3_INT117_CORRECAO'
    a=json.loads((e/'ANTES.json').read_bytes());r=json.loads((e/'RESULTADO.json').read_bytes())
    require(r['success'] is True and r['exception'] is None and r['optimized'] is True and
            r['historical_integrity_verified_after'] is True,'Corrected optimized audit failed')
    require([v['total'] for v in r['runs']]==[35,1473],'Unexpected test totals')
    for run in r['runs']:
        require(run['exit_code']==0 and run['exception'] is None and not run['timed_out'] and
                run['failures']==run['errors']==0,'Test failure')
        c=run['cleanup'];require(c['confirmed'] is True and c['active_processes']==0 and c['live_io_threads']==[],'Cleanup failed')
        record=json.loads((e/(run['label']+'.log.execution.json')).read_bytes())
        require(all(run.get(k)==v for k,v in record.items()),'Execution metadata mismatch')
    for root in (SOURCE,SOURCE/'b116',MOVED,MOVED/'b116',FINAL):check(before['final_before'],root)
    check(before['corrected_before'],SOURCE);check(before['corrected_before'],MOVED)
    check(before['previous_candidate_before'],OLD);check(before['workspace_markers'],WORK)
    check(before['release_hashes'],WORK/'audit')
    sources={n:h for n,h in inventory(SOURCE/'audit').items() if n.endswith('.py')}
    require(sources==a['sources_before']==r['sources_before'],'Executed sources mismatch')
    old_ids=set();new_ids=set()
    for p in (OLD/'audit/tests').glob('test_f3_int117_*.py'):old_ids|=test_ids(p)
    for p in (SOURCE/'audit/tests').glob('test_f3_int117_*.py'):new_ids|=test_ids(p)
    require(len(old_ids)==21 and len(new_ids)==35 and old_ids<=new_ids,'Existing test IDs removed')
    require(sha(SOURCE/'audit/tests/test_f3_int117_sqlite_write_faults.py')==
            sha(OLD/'audit/tests/test_f3_int117_sqlite_write_faults.py'),'Original 12 tests changed')
    for p in (SOURCE/'audit/tools').glob('f3_int117_*.py'):
        require(not any(isinstance(n,ast.Assert) for n in ast.walk(ast.parse(p.read_text()))),'Critical assert found')
    text=(e/'ESPECIFICOS.log').read_text(encoding='utf8')
    records=[]
    for line in text.splitlines():
        start=line.find('{')  # unittest's verbose method prefix can precede print.
        if start>=0:
            try:
                records.append(json.loads(line[start:]))
            except json.JSONDecodeError:
                continue
    rejection=[x for x in records if x.get('boundary')==4096]
    acceptance=[x for x in records if x.get('boundary')==4095]
    require(len(rejection)==len(acceptance)==1,'Missing boundary evidence')
    rejected=rejection[0];accepted=acceptance[0]
    require(rejected['attempt']['status']=='HISTORY_CAPACITY_EXHAUSTED' and rejected['attempt']['committed'] is False
            and rejected['observer']['updates_authorized']==rejected['observer']['commits_authorized']==0,'Capacity guard not proven')
    require(accepted['attempt']['committed'] is True and accepted['accepted']==4096,'Boundary acceptance not proven')
    optimized=[x for x in records if x.get('boundary_optimized') is True]
    require(len(optimized)==1 and optimized[0]['tests']==6 and optimized[0]['exit_code']==0,'Boundary -O evidence missing')
    native=[x for x in records if 'independent_native' in x]
    require(len(native)==2,'Missing independent native controls')
    for x in native:
        code=13 if x['independent_native']=='full' else 8
        require(x['writer_calls']==1 and x['observer']['connections']==1 and
                x['observer']['updates_authorized']==1 and x['observer']['commits_authorized']==0 and
                x['attempt']['error']['primary_code']==code and x['attempt']['error']['phase']=='UPDATE','Native behavior changed')
    shutil.copytree(e,SOURCE/'audit/EVIDENCIAS_F3_INT117_CORRECAO')
    report=['# F3-INT-117 CANDIDATA CORRIGIDA - 24/10/2026','',
        'Status: CANDIDATA, aguardando nova auditoria. F3 OPEN; sete flags false; offline/simulation_only true; certification false. Operacoes reais bloqueadas, retry_allowed false e nenhuma promocao.', '',
        '## Causa raiz e regra original','',
        'O escritor independente reutilizava _load e verify_typed_chain, que aceitam um historico inicial com ate 4096 entradas. Faltava a barreira adicional de consume_chain da F3-INT-109: apos uma cadeia valida, se len(consumed) >= 4096, devolver HISTORY_CAPACITY_EXHAUSTED antes de construir/gravar o novo estado. Sem essa barreira, append gerava 4097 entradas e commit de um estado que o leitor rejeitava.',
        'Ordem original preservada: ancora -> escopo -> dominio de revisao -> verificacao da cadeia (incluindo piso e digest consumido) -> capacidade -> transicao -> UPDATE -> commit. A capacidade nao e antecipada para mascarar erros de ancora, escopo ou cadeia. Nenhum historico e truncado, limpo ou reinicializado.', '',
        '## Correcao e arquivos','',
        '- audit/tools/f3_int117_sqlite_write_faults.py: barreira de capacidade na propria write_once, status de rejeicao conservadores e mesma precedencia da base; modos desconhecidos recusados tambem nos auxiliares. Erros nativos continuam registrados com codigo/fase. Connection observer e writer explicitos permitem verificacao local, sem patches globais.',
        '- audit/tools/f3_int117_run_audit.py: lista fixa ampliada para os 35 IDs, 1473 testes esperados na regressao e output novo EVIDENCIAS_F3_INT117_CORRECAO.',
        '- audit/tests/test_f3_int117_runner.py: ajuste apenas do nome de output e da contagem de testes na fixture negativa simulada; mesmos nove IDs e mesmas assercoes. Contagem valida evita que um erro de resumo mascare o erro de execucao/limpeza que o teste pretende exercitar.',
        '- Novo audit/tests/test_f3_int117_capacity_boundary.py: 14 testes adicionais, com fixtures novas por teste e comparacao direta com consume_chain original.',
        '- Relatorio, manifesto, sidecar e evidencias atualizados. Versoes substituidas arquivadas em audit/PRESERVADO_117_PRE_CORRECAO. Nenhum arquivo FINAL foi editado.', '',
        '## Fronteiras e verificacoes independentes','',
        '| Cenario | Resultado observado | SQL da conexao da sonda |',
        '|---|---|---|',
        '| 4095 entradas, cadeia nova valida | Inclusao ate 4096; estado reaberto igual ao original | 1 UPDATE e 1 COMMIT autorizados |',
        '| 4096 entradas, cadeia nova valida | HISTORY_CAPACITY_EXHAUSTED; mesmos bytes e estado | 0 UPDATEs e 0 COMMITs autorizados |',
        '| Mesma fixture, encher e tentar operacao seguinte | Primeiro commit valido; proxima inclusao recusada | Segunda conexao sem escrita/commit |',
        '| Ancora/escopo/cadeia invalidos no limite | Mesmos status prioritarios do original | Nenhuma escrita |',
        '| Revisao esgotada | REVISION_DOMAIN_EXHAUSTED antes da cadeia/capacidade | Nenhuma escrita |',
        '| Digest consumido com piso permissivo | CHAIN_ALREADY_CONSUMED antes da capacidade | Nenhuma escrita |',
        '| After-state fornecido inconsistente | ProbeError antes de UPDATE | Nenhuma escrita |', '',
        'As observacoes independentes usam set_authorizer e set_trace_callback na conexao explicitamente entregue ao teste; os callbacks permitem as operacoes e registram comandos/preparacoes. Nao substituem sqlite3.connect, _connect, consume_chain ou qualquer global. Valores BLOB de traces sao resumidos no log, sem perder tipo e contagem dos comandos.',
        'Hashes dos bytes, PRAGMA integrity_check e leitura canonica por conexao nova sao conferidos apos rejeicao. Os replays usam ancoras realmente retidas antes/depois de um commit do proprio teste. A referencia e lida do arquivo retido antes da reconciliacao. A tentativa que excederia o limite mantem o before-state observado e retry_allowed false; o digest after nesse caso descreve apenas a proposta rejeitada, nunca um estado declarado admitido.',
        'Seis verificacoes selecionadas de fronteira, ordem, historico consumido e reconciliacao/replay foram executadas novamente por subprocesso -O com verificacao explicita de __debug__. stdout/stderr desse subprocesso constam do registro boundary_optimized nos logs.', '',
        '## Preservacao dos erros SQLite','',
        'SQLITE_FULL=13 e SQLITE_READONLY=8 continuam sendo erros nativos no UPDATE, antes de commit. O controle comprova crescimento de duas para tres paginas e o limite e aplicado na mesma conexao. Dois controles adicionais usam fixtures novas e contam externamente a entrada no writer: uma chamada, uma conexao observada, uma preparacao de UPDATE e nenhum COMMIT. Nenhuma operacao que falhou foi automaticamente repetida.',
        'O campo legado automatic_retries=0 foi preservado para compatibilidade, mas deixou de ser a unica verificacao: os novos testes contam chamadas fora do escritor e registram operacoes da conexao. O campo isolado nao e tratado como prova independente.', '',
        '## Testes e regressao','',
        'Os 21 IDs anteriores foram mantidos e os 12 testes de escrita anteriores permanecem byte a byte. Os 14 novos IDs se somam aos existentes. A fixture negativa do runner foi atualizada para o numero correto, sem remover assercoes ou aceitar falhas/skips extras. O runner foi executado com -O em .r117c, pasta relocalizada; as suites do supervisor herdado rodam em modo normal e possuem subprocessos -O explicitos.', '']
    for run in r['runs']:
        report.append(f"- {run['label']}: {run['total']} testes, {run['passed']} aprovados, {run['skipped']} skipped, {run['failures']} falhas, {run['errors']} erros; exit code 0; supervisao {run['seconds']} s; cleanup confirmado, zero processos ativos e threads IPC remanescentes.")
    report += ['',
        '## Evidencias de integridade','',
        f"Base F3-INT-116 FINAL: {len(before['final_before'])} arquivos conferidos antes/depois na origem, no projeto e em b116, incluindo as copias relocalizadas. Candidata reprovada: {len(before['previous_candidate_before'])} arquivos preservados. Marcadores, checkpoints e ZIPs anteriores mantiveram os hashes.",
        f"{len(sources)} fontes Python inventariados, incluindo fontes historicos arquivados, coincidem em ANTES, RESULTADO, copia relocalizada e distribuicao. Esses inventarios fixam arquivos; nao afirmam que cada arquivo historico foi importado ou executado.",
        'Logs da versao corrigida: audit/EVIDENCIAS_F3_INT117_CORRECAO. Logs EVIDENCIAS_F3_INT117 sao historicos da versao reprovada e nao sao usados como aprovacao desta correcao. O manifesto candidato antigo se aplica a raiz historico117/ do ZIP; o novo manifesto fixa a candidata corrigida inteira, sem autorreferencia.',
        'O ZIP inclui projeto corrigido completo, base b116, candidato reprovado completo em historico117/ e artefatos de preparacao/validacao. CRC, nomes e hashes de cada membro conferidos apos escrita. Hash do ZIP fica em sidecar externo.', '',
        '## Limitacoes remanescentes','',
        '- Os 12 testes legados ainda compartilham tres resultados em setUpClass; foram mantidos para nao remover cobertura. Os 14 testes novos nao compartilham os bancos de fronteira; FULL e READONLY adicionais usam fixtures novas e contadores independentes.',
        '- A barreira CHAIN_ALREADY_CONSUMED agora e isolada com piso permissivo numa fixture sintetica. Isso demonstra a precedencia do verificador; nao autentica a origem de cada entrada. Replay com ancoras reais before/after de um commit separado tambem e exercitado.',
        '- O escritor continua sendo uma sonda independente, nao substituto de consume_chain. Resultados/erros de fixture fora do dominio exercitado podem ter formas diferentes do StoreResult original. Nao se declara equivalencia integral de todas as rotas internas.',
        '- Observadores sao locais a conexao e a verificacao de chamadas e externa ao writer, mas nao e uma atestacao autenticada contra codigo malicioso. Sem patch global e sem autorizacao de retry.',
        '- Persiste um skip de symlink do Windows por permissao. As falhas FULL/READONLY observadas sao no UPDATE, nao no interior do commit. Limite de paginas nao e disco fisico cheio e mode=ro nao e ACL do Windows.',
        '- Sem IOERR/VFS, custodia autenticada, resistencia comprovada a perda de energia, durabilidade fisica, exactly-once ou garantia entre computadores. Hashes antes/depois nao detectam alteracoes transitorias restauradas.',
        '- A limpeza confirmada cobre os Jobs supervisionados e as fixtures usadas, nao todos os processos/temporarios da maquina.', '',
        'Aguardar nova auditoria. ULTIMO_MARCO continua F3-INT-116 FINAL. Nao foi criado checkpoint F3-INT-117 FINAL.']
    report_text='\n'.join(report)+'\n'
    (SOURCE/'audit/RELATORIO_F3_INT117_CANDIDATA.md').write_text(report_text,encoding='utf8')
    (OUT/'RELATORIO_CORRECAO.md').write_text(report_text,encoding='utf8')
    summary=dict(stage='F3-INT-117',status='CANDIDATA_CORRIGIDA',promoted=False,f3='OPEN',locks=r['locks'],
        modified_sources=before['modified_sources'],new_tests=14,old_test_ids_preserved=21,
        executed_source_inventory_count=len(sources),original_final_files_verified=len(before['final_before']),
        previous_candidate_files_preserved=len(before['previous_candidate_before']),boundary_rejection=rejected,
        boundary_acceptance=accepted,independent_native=native,
        runs=[{k:v[k] for k in ('label','total','passed','skipped','failures','errors','seconds')} for v in r['runs']])
    (OUT/'VERIFICACAO.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    excluded={'audit/MANIFESTO_F3_INT117_CANDIDATA.json','audit/MANIFESTO_F3_INT117_CANDIDATA.json.sha256'}
    pins={n:h for n,h in inventory(SOURCE).items() if n not in excluded}
    manifest=SOURCE/'audit/MANIFESTO_F3_INT117_CANDIDATA.json'
    manifest.write_text(json.dumps(dict(stage='F3-INT-117',checkpoint_type='CANDIDATE_FOR_REVIEW',
        correction='HISTORY_CAPACITY_EXHAUSTED',f3='OPEN',locks=r['locks'],offline=True,simulation_only=True,
        certification=False,promoted=False,retry_allowed=False,files_sha256=pins),indent=2)+'\n',encoding='utf8')
    Path(str(manifest)+'.sha256').write_text(sha(manifest)+'  '+manifest.name+'\n',encoding='ascii')
    check(pins,SOURCE)
    files={'f3_int117_corrigida/'+p.relative_to(SOURCE).as_posix():p for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update({'historico117/'+p.relative_to(OLD).as_posix():p for p in OLD.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in OUT.iterdir():
        if p.is_file():files['correction_build/'+p.name]=p
    for name in ('prepare_f3_int117_correction_20261024.py','package_f3_int117_correction_20261024.py'):
        files['correction_build/'+name]=WORK/name
    package_pins={n:sha(p) for n,p in sorted(files.items())}
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
        z.writestr('MANIFESTO_PACOTE.json',json.dumps(dict(stage='F3-INT-117',status='CANDIDATA_CORRIGIDA',promoted=False,files_sha256=package_pins),indent=2))
    with zipfile.ZipFile(ZIP) as z:
        require(z.testzip() is None,'ZIP CRC failure')
        require(len(z.namelist())==len(set(z.namelist()))==len(package_pins)+1,'ZIP count mismatch')
        for n,h in package_pins.items():
            require(not Path(n).is_absolute() and '..' not in Path(n).parts and '\\' not in n,'Unsafe ZIP path')
            require(hashlib.sha256(z.read(n)).hexdigest()==h,'ZIP member hash mismatch: '+n)
    check(before['final_before'],FINAL);check(before['previous_candidate_before'],OLD)
    check(before['workspace_markers'],WORK);check(before['release_hashes'],WORK/'audit')
    digest=sha(ZIP)
    Path(str(ZIP)+'.sha256').write_text(digest+'  '+ZIP.name+'\n',encoding='ascii')
    (OUT/'PACOTE_VERIFICADO.json').write_text(json.dumps(dict(zip=str(ZIP),sha256=digest,
        manifest_entries=len(pins),zip_members=len(package_pins)+1,crc_ok=True,all_member_hashes_ok=True,
        final116_unchanged=True,previous_candidate_unchanged=True,workspace_markers_unchanged=True),indent=2),encoding='utf8')
    print(ZIP);print(digest)

if __name__=='__main__':main()
