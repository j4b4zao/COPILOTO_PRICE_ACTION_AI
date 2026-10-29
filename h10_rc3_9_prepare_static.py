"""Static preparation only. Reads source as text/AST, never imports project code.
Does not execute prepared tests, constructors, engines or previous auditors.
"""
import ast
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path('C:/COPILOTO_GIT_SYNC')
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'h10_rc3_8_auditoria_20261013_154502/h10_rc3_8_transitive.json'
ENGINES={
 'market_structure':('analysis/market_structure.py','MarketStructure','structure'),
 'price_action':('analysis/price_action/price_action.py','PriceAction','price_action'),
 'strategy':('strategies/strategy_engine.py','StrategyEngine','strategy'),
 'score':('ai/score_engine.py','ScoreEngine','score'),
 'risk':('risk/risk_manager.py','RiskManager','risk'),
 'decision':('decision/decision_engine.py','DecisionEngine','decision'),
 'alert':('alerts/alert_manager.py','AlertManager','alert'),
}
ORDER=['decision','market_structure','risk','alert','score','strategy','price_action']
POLICY={'decision':'WAIT','orders_allowed':False,'live_certified':False,'flow_complete':False}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def expr(node): return ast.unparse(node)
def imports(tree):
    out=[]
    def visit(node,scope):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): scope=scope+'.'+node.name
        if isinstance(node,ast.Import):
            out.extend({'module':a.name,'symbol':None,'line':node.lineno,'scope':scope,'level':0} for a in node.names)
        if isinstance(node,ast.ImportFrom):
            out.extend({'module':node.module or '', 'symbol':a.name,'line':node.lineno,'scope':scope,'level':node.level} for a in node.names)
        for child in ast.iter_child_nodes(node): visit(child,scope)
    visit(tree,'module'); return out

def local(module):
    base=ROOT.joinpath(*module.split('.'))
    for p in (base.with_suffix('.py'),base/'__init__.py'):
        if p.is_file(): return p.relative_to(ROOT).as_posix()
    return None

def runtime_contract(tree):
    aliases={'context':'context'}
    # Symbolic alias approximation, no evaluation of any expression.
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Attribute) and isinstance(node.value.value,ast.Name) and node.value.value.id=='context':
            for target in node.targets:
                if isinstance(target,ast.Name): aliases[target.id]='context.'+node.value.attr
    reads=set(); writes=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Attribute):
            text=expr(node); first,_,rest=text.partition('.')
            if first in aliases:
                canonical=aliases[first]+('.'+rest if rest else '')
                if isinstance(node.ctx,ast.Store): writes.append({'field':canonical,'line':node.lineno})
                else: reads.add(canonical)
    return {'context_references_static':sorted(reads),'context_writes_static':writes,'alias_map':aliases,
            'limitations':'Alias approximation; getattr/setattr and helper effects require method review. Not a complete runtime contract.'}

def top_expressions(tree):
    calls=[]
    def expression_calls(item,scope):
        class Visitor(ast.NodeVisitor):
            def visit_Call(self,node):
                calls.append({'line':node.lineno,'scope':scope,'call':expr(node.func)})
                self.generic_visit(node)
            def visit_Lambda(self,node):
                # Lambda body is deferred; only defaults execute at creation.
                for default in [*node.args.defaults,*[n for n in node.args.kw_defaults if n]]: self.visit(default)
        Visitor().visit(item)
    def visit_statements(statements,scope):
        for node in statements:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                items=[*node.decorator_list,*node.args.defaults,*[n for n in node.args.kw_defaults if n]]
                for item in items: expression_calls(item,scope)
            elif isinstance(node,ast.ClassDef):
                for item in [*node.decorator_list,*node.bases,*[k.value for k in node.keywords]]:
                    expression_calls(item,scope+'.'+node.name)
                visit_statements(node.body,scope+'.'+node.name)
            elif isinstance(node,(ast.Import,ast.ImportFrom)): continue
            elif isinstance(node,ast.If) and '__name__' in expr(node.test) and '__main__' in expr(node.test): visit_statements(node.orelse,scope)
            else: expression_calls(node,scope)
    visit_statements(tree.body,'module'); return calls

def scenarios():
    return {
      'market_structure':['not-ready: preserve context/WAIT','5 candles: insufficient closed confirmation','6 candles symmetric swing: expected SIDEWAYS, high15/low5','forming candle invariance','equal highs/lows: no strict swing','HH/HL and LH/LL/BOS/CHOCH with closed fixtures','previous-result reuse/clear behavior'],
      'price_action':['not-ready early return','neutral structure and synthetic candles','known candlestick pattern','forming candle invariance per helper contract','direction NONE for SIDEWAYS/UNKNOWN','score threshold and reset','all returned dynamics fields match slotted result'],
      'strategy':['all synthetic context results invalid: no setup','registry classes/priority deterministic','disabled setup ignored','in-memory fake setups: highest valid score wins','tie retains first result','context.strategy replacement identity','setup constructor effects and default readiness'],
      'score':['explicit enable_order_flow=False and weight=0','invalid strategy keeps score invalid','normalization 0..100 and confidence','70 boundary distinct from settings MIN_SCORE=80','invalid weight/nonfinite/range rejected','Order Flow disabled contributes zero','repeat execution clears prior score'],
      'risk':['invalid strategy: approved=False','invalid direction','zero entry/no stop rejected','BUY/SELL structural stop boundaries','zero/negative SELL targets and fallback','structural target with RR<1.5 rejected rather than fallback','max stop distance500','synthetic-only positive cases separately approved'],
      'decision':['invalid setup -> WAIT','risk unapproved -> WAIT','invalid score -> WAIT','direction NONE -> WAIT','MTF conflict/opposite -> WAIT','stale decision reset','positive BUY/SELL remains out of initial neutral suite'],
      'alert':['unapproved decision -> no valid alert','clear prior alert','clock controlled before positive timestamp test','capture stdout without output sinks','approved property depends on action, not valid flag','Order Flow metadata optional path','positive alert only after separate approval']}

def main():
    draft_mode='w' if '--replace-current-draft' in sys.argv else 'x'
    prior_hash_before=sha(PRIOR)
    prior=json.loads(PRIOR.read_text(encoding='utf-8-sig'))
    paths=set(prior['modules']); package_files=set()
    for relative in list(paths):
        parent=(ROOT/relative).parent
        while parent!=ROOT:
            init=parent/'__init__.py'
            if init.is_file(): package_files.add(init.relative_to(ROOT).as_posix())
            parent=parent.parent
    paths|=package_files
    trees={}; dependency_inventory={}; external=set(); unresolved=[]
    pending=list(paths)
    while pending:
        relative=pending.pop()
        if relative in trees: continue
        tree=ast.parse((ROOT/relative).read_text(encoding='utf-8-sig'),filename=relative); trees[relative]=tree
        edges=[]
        for entry in imports(tree):
            module=entry['module']
            if entry['level']:
                pkg=relative.removesuffix('.py').replace('/','.').rpartition('.')[0].split('.')
                module='.'.join(pkg[:len(pkg)-entry['level']+1]+([module] if module else []))
            target=local(module)
            if target:
                edges.append(target); pending.append(target)
                if entry['symbol'] and (child:=local(module+'.'+entry['symbol'])): edges.append(child); pending.append(child)
                parent=(ROOT/target).parent
                while parent!=ROOT:
                    init=parent/'__init__.py'
                    if init.is_file():
                        package=init.relative_to(ROOT).as_posix()
                        package_files.add(package)
                        if package!=relative: edges.append(package); pending.append(package)
                    parent=parent.parent
            elif module.split('.')[0] in sys.stdlib_module_names: external.add(module.split('.')[0])
            else: unresolved.append(dict(entry,path=relative))
        calls=[{'call':expr(n.func),'line':n.lineno} for n in ast.walk(tree) if isinstance(n,ast.Call)]
        dynamic=[c for c in calls if c['call'] in ('__import__','exec','eval','importlib.import_module','importlib.util.spec_from_file_location')]
        effect_calls=[c for c in calls if c['call']=='print' or c['call'].endswith(('.publish','.speak','.write_text','.write_bytes','.open','.sleep','.unlink','.replace','.mkdir')) or c['call'].startswith(('subprocess.','urllib.','socket.')) or c['call'] in ('open','datetime.now','time.monotonic','build_opener','urlopen')]
        dependency_inventory[relative]={'sha256':sha(ROOT/relative),'imports':imports(tree),'local_dependencies':sorted(set(edges)),
            'top_level_calls':top_expressions(tree),'dynamic_import_or_execution_calls':dynamic,'potential_runtime_effect_calls':effect_calls}
    hashes={p:sha(ROOT/p) for p in sorted(trees)}
    prior_changed=[p for p,m in prior['modules'].items() if hashes[p]!=m['sha256']]
    engine_reports={}; plans=scenarios()
    for key,(path,klass,target) in ENGINES.items():
        cls=next(n for n in trees[path].body if isinstance(n,ast.ClassDef) and n.name==klass)
        methods=[n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        constructor=next((n for n in methods if n.name=='__init__'),None)
        metadata={}
        for n in cls.body:
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
                try: metadata[n.targets[0].id]=ast.literal_eval(n.value)
                except (ValueError,TypeError): pass
        closure=set(); todo=[path]
        while todo:
            p=todo.pop()
            if p in closure: continue
            closure.add(p); todo.extend(dependency_inventory[p]['local_dependencies'])
        engine_reports[key]={'path':path,'class':klass,'sha256':hashes[path],'metadata':metadata,
            'constructor':{'signature':'('+expr(constructor.args)+')' if constructor else '() inherited object initialization through EngineBase',
                           'line':constructor.lineno if constructor else None,
                           'calls':[expr(n.func) for n in ast.walk(constructor) if isinstance(n,ast.Call)] if constructor else [],
                           'imports':imports(constructor) if constructor else []},
            'public_methods':[{'name':n.name,'line':n.lineno,'signature':'('+expr(n.args)+')','returns_annotation':expr(n.returns) if n.returns else None} for n in methods if not n.name.startswith('_')],
            'inherited_public_methods':['before_execute(context)','after_execute(context)','enabled()','priority()','metadata()'],
            'private_helpers':[n.name for n in methods if n.name.startswith('_') and n.name!='__init__'],
            'input_output':dict(runtime_contract(cls),return_contract='Same AnalysisContext object with mutated result; Strategy may replace context.strategy',result_slot=target),
            'local_dependency_closure':sorted(closure),'synthetic_test_aptitude':'STATICALLY_PREPARABLE_CONDITIONAL_ON_USER_AUTHORIZATION',
            'runtime_safety_certified':False,'future_scenarios':plans[key]}
    context=next(n for n in trees['core/analysis_context.py'].body if isinstance(n,ast.ClassDef) and n.name=='AnalysisContext')
    fields=[{'name':n.target.id,'annotation':expr(n.annotation),'default_expression':expr(n.value) if n.value else None} for n in context.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name)]
    new=['h10_rc3_9_prepare_static.py','h10_rc3_9_future_suite.py','h10_rc3_9_synthetic_fixtures.json','h10_rc3_9_preparation_report.json','h10_rc3_9_preparation_report.txt','h10_rc3_9_hashes.json']
    # Parse prepared future code WITHOUT importing or running it.
    ast.parse((OUT/'h10_rc3_9_future_suite.py').read_text(encoding='utf-8'))
    fixture=json.loads((OUT/'h10_rc3_9_synthetic_fixtures.json').read_text(encoding='utf-8'))
    after_changed=[p for p,h in hashes.items() if sha(ROOT/p)!=h]
    report={'version':'H.10 RC3.9','status':'ISOLATED_TESTS_PREPARED_NOT_EXECUTED',**POLICY,
      'generated_at':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),'analysis_mode':'SOURCE_TEXT_AND_AST_ONLY',
      'engines_imported':False,'engines_instantiated':False,'engines_executed':False,'tests_executed':False,'app_main_executed':False,
      'excel_profit_dde_rtd_used':False,'operational_integration':False,'dependencies_installed':False,
      'prior_audit':{'path':str(PRIOR),'sha256':sha(PRIOR),'modules':prior['modules_scanned'],'blockers':prior['blockers'],'warnings':prior['warnings'],'current_source_mismatches':prior_changed},
      'engines':engine_reports,'recommended_order':ORDER,'analysis_context_fields':fields,
      'shared_dependency_notes':['All engines import EngineBase -> AnalysisContext, broad shared model/state/psychology imports',
       'Prior 81-module graph omitted package initializer execution edges; added economic_context/psychology imports expand the actual static preparation graph',
       'Package imports expose dormant HTTP, filesystem exporters and subprocess SAPI/TTS; these must not be instantiated or invoked in tests',
       'AnalysisContext dataclass has slots=True: mocks cannot invent arbitrary attributes',
       'default_factory calls execute on Context construction; decorators/field declarations execute on imports',
       'trader_psychology=None: runtime/voice publisher classes imported but not instantiated by this default',
       'ScoreEngine imports config.settings inside constructor even with explicit arguments',
       'StrategyEngine constructor loads and instantiates TrendPullback/TrendBreakout/LiquiditySweep',
       'DecisionResult.approved derives from action BUY/SELL; does not independently require valid flag',
       'AlertManager uses naive datetime.now and stdout; positive timestamp tests need local clock substitution'],
      'dependency_inventory':dependency_inventory,'stdlib_dependencies_static':sorted(external),'unresolved_external_dependencies':unresolved,
      'package_initializers_additionally_reviewed':sorted(package_files),'source_hashes':hashes,
      'preservation':{'files_checked':len(hashes),'changed_during_preparation':after_changed,'modified_originals':[],
                      'prior_report_unchanged':sha(PRIOR)==prior_hash_before},
      'files_created':new,'files_modified':[],'prepared_executable_cases':8,
      'cases_status':'DRAFT_NOT_EXECUTED; 7 neutral engine cases plus MarketStructure closed-candle invariance',
      'pre_execution_requirements':['Explicit user authorization for one engine, not all seven at once',
       'Fresh offline Python process; no app.main, Excel, Profit, Collector, Capture or order adapters',
       'Validate source hashes and context/model contracts before import; stop if changed',
       'Use independent synthetic context, capture stdout, no event bus/voice sinks',
       'Prepared best-effort I/O traps wrap imports/execution: HTTP/socket/subprocess/file writes denied; traps themselves not executed/validated yet',
       'Hard duration/resource/file/network constraints must be reviewed before broader positive-path tests',
       'No installation or change to settings; score explicit experiment disabled/weight0',
       'Keep project envelope WAIT and all permission flags false; runtime success never grants integration'],
      'limitations':['AST review does not prove runtime safety, fixture expectations or test pass status',
       'Static alias contracts may overapproximate reads and omit dynamic getattr/setattr fields',
       'Prepared suite opt-in/hash checks are accidental-execution guards, not a security sandbox',
       '8 drafted tests do not cover every planned scenario; expand only after staged authorization',
       'No imports used to validate availability of external packages; resolved stdlib classification is static'],
      'next_action':'Await user authorization for isolated DecisionEngine neutral WAIT case, then assess results before next engine'}
    if prior_changed or after_changed: report['status']='PREPARATION_REVIEW_REQUIRED_SOURCE_CHANGED'
    with (OUT/'h10_rc3_9_preparation_report.json').open(draft_mode,encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2)
    lines=[f"H.10 RC3.9 — PREPARAÇÃO DE TESTES ISOLADOS",f"Status: {report['status']}",
      'decision=WAIT; orders_allowed=False; live_certified=False; flow_complete=False',
      'Motores importados/instanciados/executados: 0. Testes executados: 0.',
      'Não houve conexão Excel/Profit/DDE/RTD, app.main, integração ou dependências instaladas.',
      f"Auditoria anterior: {prior['modules_scanned']} módulos, {len(prior['blockers'])} bloqueios, {len(prior['warnings'])} avisos.",
      f"Fontes/initializers lidos nesta preparação: {len(hashes)}; divergências H.10 RC3.8: {prior_changed}; alterações durante leitura: {after_changed}.",
      '', 'MOTORES APTOS ESTATICAMENTE PARA PREPARAÇÃO CONDICIONAL (não certificados em runtime):']
    for key in ORDER:
        e=engine_reports[key]
        lines += ['',f"{key}: {e['path']} / {e['class']}",f"Construtor: {e['constructor']['signature']}; chamadas: {e['constructor']['calls']}",
                  f"Públicos próprios: {e['public_methods']}",f"Entrada: executar(context), AnalysisContext; saída alterada: context.{e['input_output']['result_slot']}; mesmo contexto.",
                  f"Subcontextos/atributos (aproximação): {e['input_output']['context_references_static']}",
                  f"Casos planejados: {'; '.join(e['future_scenarios'])}"]
    lines += ['', 'ORDEM RECOMENDADA: '+' -> '.join(ORDER),
      'Decision neutral WAIT primeiro: regras determinísticas sem construtor próprio; só testar retorno negativo inicialmente.',
      'MarketStructure em seguida: OHLC sintético e candle em formação excluído; Risk só setup inválido inicialmente.',
      'Alert exige isolamento de stdout/relógio em casos positivos; Score lê settings; Strategy instancia setups; PriceAction reúne muitos helpers.',
      '', 'PENDÊNCIAS E RISCOS:',*report['shared_dependency_notes'],
      'Imports externos não resolvidos: '+str(unresolved),'Stdlib estática: '+str(sorted(external)),
      'Imports tardios e chamadas possíveis estão detalhados no JSON; chamadas de publicação/voz de dependências não são autorizadas.',
      'Mapa anterior não incluía imports executados por initializers economic_context/psychology: a ampliação revela HTTP, exporters e subprocess SAPI/TTS dormentes.',
      'Barreiras futuras de I/O foram PREPARADAS para bloquear socket/HTTP/subprocess/escrita durante import e execução; não executadas nem certificadas.',
      'settings contém caminhos Excel apenas como dados; não são lidos/ativados pela preparação.',
      'AnalysisContext cria modelos/default factories; validar construtores e slots antes de resultados positivos.',
      'ScoreEngine.MIN_SCORE=70 e config.settings.MIN_SCORE=80 são limites distintos; não alterar nem equiparar.',
      'Strategy pode substituir context.strategy: não assumir identidade desse resultado após seleção.',
      'As dependências externas requirements incluem bibliotecas operacionais, mas a closure inspecionada usa somente stdlib identificado.',
      'Nenhuma dependência foi importada para confirmar disponibilidade. Nenhuma dependência será instalada automaticamente.',
      '', 'ARQUIVOS CRIADOS:',*new,
      'Arquivos originais modificados: nenhum. Testes antigos e relatórios preexistentes preservados.',
      'h10_rc3_9_future_suite.py: oito casos futuros, sem import de projeto no topo; gate por motor + hashes.',
      'h10_rc3_9_synthetic_fixtures.json: OHLCV sintético fixo; não provém de Excel/Profit.',
      'h10_rc3_9_prepare_static.py foi executado APENAS como gerador estático; não é teste de motor.',
      'Os testes preparados não foram executados, nem sequer coletados/importados.',
      'Manifesto h10_rc3_9_hashes.json contém SHA256 dos artefatos e fontes; manifesto não inclui próprio hash.',
      '', 'LIMITAÇÕES:',*report['limitations'],
      '', 'PRÓXIMA AÇÃO: autorização explícita para um motor por vez, começando pelo DecisionEngine com cenário WAIT.',
      'Comando FUTURO somente após autorização: em PowerShell normal,',
      "$env:H10_RC3_9_AUTHORIZED_ENGINE = 'decision'",
      '& "C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" -B .\\h10_rc3_9_future_suite.py FutureNeutralTests.test_decision_neutral',
      'Remove-Item Env:H10_RC3_9_AUTHORIZED_ENGINE',
      'Esse comando NÃO foi executado. Token de ambiente não substitui autorização do usuário.',
      'Sem Profit, RTD, DDE, ordens, config operacional alterada, app.main, commits ou integração.',
      'A auditoria estática anterior e esta preparação NÃO certificam segurança em tempo de execução.']
    with (OUT/'h10_rc3_9_preparation_report.txt').open(draft_mode,encoding='utf-8') as f: f.write('\n'.join(lines)+'\n')
    manifest={'artifact_sha256':{name:sha(OUT/name) for name in new if name!='h10_rc3_9_hashes.json'},'source_sha256':hashes,**POLICY}
    with (OUT/'h10_rc3_9_hashes.json').open(draft_mode,encoding='utf-8') as f: json.dump(manifest,f,indent=2)
    print(json.dumps({'status':report['status'],'sources':len(hashes),'engines_prepared':len(ENGINES),'tests_executed':False,'unresolved':unresolved,'prior_hash_mismatches':prior_changed,'changed':after_changed},ensure_ascii=False))

if __name__=='__main__': main()
