"""RC3.11 source/AST preparation. No project imports and no test execution."""
import ast
import hashlib
import json
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path('C:/COPILOTO_GIT_SYNC'); OUT=Path(__file__).resolve().parent
FILES=['h10_rc3_11_prepare_static.py','h10_rc3_11_future_suite.py','h10_rc3_11_synthetic_fixtures.json',
       'h10_rc3_11_preparation_report.json','h10_rc3_11_preparation_report.txt','h10_rc3_11_hashes.json']
SAFETY={'decision':'WAIT','orders_allowed':False,'live_certified':False,'flow_complete':False}
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name,value):
    target=OUT/name
    if isinstance(value,str): text=value
    else: text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    with target.open('x',encoding='utf-8') as f: f.write(text)

def build_cases():
    candles={}; cases=[]
    def bars(name,highs,lows,close_override=None):
        values=[]
        for i,(h,l) in enumerate(zip(highs,lows)):
            middle=(h+l)/2
            values.append({'open':middle,'high':h,'low':l,'close':middle,'volume':100,
                'timestamp':(datetime(2026,1,1,10,tzinfo=ZoneInfo('America/Sao_Paulo'))+timedelta(minutes=i)).isoformat()})
        if close_override:
            values[-2].update(close_override)
            values[-2]['open']=(values[-2]['high']+values[-2]['low'])/2
        candles[name]=values
    up_h=[12,13,20,14,13,15,25,16,15,17,18]; up_l=[9,8,5,8,9,10,7,10,11,12,13]
    bars('up',up_h,up_l); bars('down',[100-v for v in up_l],[100-v for v in up_h])
    side_h=list(up_h); side_l=list(up_l); side_h[6]=20; side_l[6]=5; bars('sideways',side_h,side_l)
    bars('bos_up',up_h,up_l,{'high':30,'low':15,'close':28})
    bars('bos_down',[100-v for v in up_l],[100-v for v in up_h],{'high':85,'low':70,'close':72})
    bars('choch',up_h,up_l,{'high':13,'low':3,'close':4})
    bars('forming',up_h[:-1]+[999],up_l[:-1]+[0]); bars('insufficient',[12]*4,[8]*4)
    bars('pa',[102]*6,[98]*6)
    def case(id,engine,label,input=None,expected=None,candle=None,bounds=None,blocked=None):
        row={'id':id,'engine':engine,'scenario':label,'status':'BLOCKED_BY_CONTRACT' if blocked else 'PREPARED_NOT_EXECUTED',
             'input':input or {},'expected':expected or {},'reason':blocked or 'Expectativa derivada estaticamente; ainda não executada.'}
        if candle: row['candles']=candle
        if bounds: row['bounds']=bounds
        cases.append(row)
    for id,label,candle,expected in [
      ('ms_up','Tendência de alta','up',{'structure.trend':'$Trend.UP','structure.valid':True}),
      ('ms_down','Tendência de baixa','down',{'structure.trend':'$Trend.DOWN','structure.valid':True}),
      ('ms_sideways','Mercado lateral','sideways',{'structure.trend':'$Trend.SIDEWAYS','structure.valid':True}),
      ('ms_hh_hl','HH e HL','up',{'structure.hh':True,'structure.hl':True}),
      ('ms_lh_ll','LH e LL','down',{'structure.lh':True,'structure.ll':True}),
      ('ms_bos_up','BOS de alta','bos_up',{'structure.bos_up':True}),
      ('ms_bos_down','BOS de baixa','bos_down',{'structure.bos_down':True}),
      ('ms_choch','CHOCH após HH/HL','choch',{'structure.choch':True}),
      ('ms_forming','Candle em formação ignorado','forming',{'structure.trend':'$Trend.UP','structure.swing_high':25,'structure.swing_low':7}),
      ('ms_insufficient','Histórico insuficiente','insufficient',{'structure.valid':False})]: case(id,'market_structure',label,expected=expected,candle=candle)
    for side,trend in [('buy','UP'),('sell','DOWN')]:
        case('pa_'+side,'price_action','Sinal '+side,{'structure.trend':'$Trend.'+trend},
             {'price_action.bias':side.upper(),'price_action.valid':True},'pa',{'price_action.score':[30,100]})
    case('pa_none','price_action','Ausência de sinal',{'structure.trend':'$Trend.SIDEWAYS'},{'price_action.bias':'NONE','price_action.valid':False},'pa')
    case('pa_insufficient','price_action','Histórico insuficiente',expected={'price_action.valid':False},candle='insufficient')
    case('pa_conflict','price_action','Bloqueio por padrões conflitantes',blocked='Bias deriva da tendência; padrões somam score. Não há veto geral por conflito de padrões.')
    strat_buy={'context.valid':True,'context.bias':'BUY','structure.trend':'$Trend.UP','structure.valid':True,'structure.bos_up':True,
       'order_block.bullish':True,'fair_value_gap.bullish':True,'price_action.breakout':True,'volume.high':True}
    strat_sell={'context.valid':True,'context.bias':'SELL','structure.trend':'$Trend.DOWN','structure.valid':True,'structure.bos_down':True,
       'order_block.bearish':True,'fair_value_gap.bearish':True,'price_action.breakout':True,'volume.high':True}
    case('strategy_buy','strategy','Setup comprador válido',strat_buy,{'strategy.valid':True,'strategy.signal':'BUY','strategy.name':'Trend Breakout'})
    case('strategy_sell','strategy','Setup vendedor válido',strat_sell,{'strategy.valid':True,'strategy.signal':'SELL','strategy.name':'Trend Breakout'})
    case('strategy_invalid','strategy','Setup inválido',expected={'strategy.valid':False,'strategy.signal':'NONE'})
    case('strategy_no_confluence','strategy','Ausência de confluências',{'context.valid':True,'context.bias':'BUY'}, {'strategy.valid':False})
    case('strategy_conflict','strategy','Veto de setups opostos',blocked='Seleciona maior score; empate mantém primeiro pela prioridade. Não existe veto direcional geral.')
    tie=dict(strat_buy); tie.update({'price_action.breakout':False,'price_action.pullback':True,'price_action.hammer':True,'price_action.shooting_star':True,
      'liquidity.valid':True,'liquidity.sell_side':True,'volume.valid':True,'order_block.valid':True,'order_block.bearish':True,'fair_value_gap.valid':True,'fair_value_gap.bearish':True})
    case('strategy_tie_observed','strategy','Seleção observável no empate oposto',tie,{'strategy.signal':'BUY','strategy.name':'Trend Pullback','strategy.score':100})
    high={'structure.valid':True,'structure.trend':'$Trend.UP','structure.bos_up':True,'structure.hh':True,'structure.choch':True,'structure.confidence':1,
          'price_action.valid':True,'price_action.score':100,'liquidity.valid':True,'liquidity.confidence':100,'volume.valid':True,'volume.strength':1,
          'order_block.valid':True,'order_block.strength':1,'fair_value_gap.valid':True,'fair_value_gap.strength':1,'context.valid':True,'context.score':100,
          'strategy.valid':True,'strategy.signal':'BUY','strategy.score':100}
    threshold={k:v for k,v in high.items() if not k.startswith(('structure.','volume.'))}
    case('score_minimum','score','Pontuação mínima zero',expected={'score.total':0,'score.valid':False})
    case('score_threshold','score','Limiar funcional 70',threshold,{'score.total':70,'score.valid':True})
    case('score_intermediate','score','Pontuação intermediária 30',{'strategy.valid':True,'strategy.score':100,'price_action.valid':True,'price_action.score':100},{'score.total':30,'score.valid':False})
    for id,label in [('score_high','Pontuação elevada'),('score_favorable','Confluências favoráveis'),('score_of_disabled','Order Flow desabilitado')]:
        case(id,'score',label,high,{'score.total':100,'score.valid':True,'score.order_flow_applied':False},bounds={'score.total':[0,100]})
    conflicting=dict(high); conflicting['structure.trend']='$Trend.DOWN'
    case('score_conflicting','score','Confluências conflitantes sem veto presumido',conflicting,{'score.total':100,'score.bias':'BUY'})
    capped=dict(high); capped['price_action.score']=1000; capped['strategy.score']=1000
    case('score_bounded','score','Score limitado 0..100',capped,{'score.total':100},bounds={'score.total':[0,100]})
    risk_buy={'market.last_price':1000,'strategy.valid':True,'strategy.signal':'BUY','strategy.score':100,'structure.trend':'$Trend.UP','structure.bos_up':True,
      'structure.swing_high':1200,'structure.last_high':1200,'order_block.valid':True,'order_block.bullish':True,'order_block.low':900,
      'fair_value_gap.valid':True,'fair_value_gap.bullish':True,'fair_value_gap.low':900,'volume.high':True,'liquidity.buy_side':True}
    case('risk_valid_stop','risk','Stop válido',risk_buy,{'risk.stop_loss':900,'risk.approved':True,'risk.valid':True})
    bad_stop=dict(risk_buy); bad_stop['order_block.low']=1100; bad_stop['fair_value_gap.low']=1100
    case('risk_invalid_stop','risk','Stop inválido',bad_stop,{'risk.approved':False,'risk.valid':False})
    case('risk_valid_target','risk','Alvo válido',risk_buy,{'risk.take_profit':1200,'risk.risk_reward':2,'risk.approved':True})
    weak=dict(risk_buy); weak['structure.swing_high']=1100; weak['structure.last_high']=1100
    for id,label in [('risk_rr_below','RR abaixo de 1.5'),('risk_no_bad_fallback','Rejeição sem fallback indevido')]:
        case(id,'risk',label,weak,{'risk.take_profit':1100,'risk.risk_reward':1,'risk.approved':False,'risk.valid':False})
    case('risk_rr_above','risk','RR acima do mínimo',risk_buy,{'risk.risk_reward':2,'risk.approved':True})
    case('risk_invalid_target','risk','Rejeição obrigatória de nível de alvo inválido',blocked='Candidatos fora do lado/zerados são filtrados; ausência de estrutura válida permite fallback 2R. Não existe veto geral por nível inválido.')
    fallback=dict(risk_buy); fallback['structure.swing_high']=0; fallback['structure.last_high']=0
    case('risk_fallback_absent','risk','Fallback permitido somente sem candidato estrutural',fallback,{'risk.take_profit':1200,'risk.risk_reward':2,'risk.approved':True})
    decision={'strategy.valid':True,'strategy.signal':'BUY','strategy.name':'SYNTHETIC','risk.approved':True,'risk.valid':True,'risk.entry_price':1000,
       'risk.stop_loss':900,'risk.take_profit':1200,'risk.risk_reward':2,'score.valid':True,'score.total':80,'score.confidence':.8}
    case('decision_buy','decision','BUY aprovado em memória',decision,{'decision.action':'BUY','decision.valid':True,'decision.entry':1000})
    sell=dict(decision); sell.update({'strategy.signal':'SELL','risk.stop_loss':1100,'risk.take_profit':800})
    case('decision_sell','decision','SELL aprovado em memória',sell,{'decision.action':'SELL','decision.valid':True})
    case('decision_wait_evidence','decision','WAIT por setup ausente',expected={'decision.action':'WAIT','decision.valid':False})
    rejected=dict(decision); rejected['risk.approved']=False
    case('decision_wait_risk','decision','WAIT por risco rejeitado',rejected,{'decision.action':'WAIT','decision.valid':False})
    conflict=dict(decision); conflict.update({'multi_timeframe_analysis.valid':True,'multi_timeframe_analysis.conflict':True,'multi_timeframe_analysis.alignment':'BUY'})
    case('decision_wait_conflict','decision','WAIT por conflito MTF',conflict,{'decision.action':'WAIT','decision.valid':False})
    invalid=dict(decision); invalid['score.valid']=False
    case('decision_wait_invalid','decision','WAIT por flag score inválido',invalid,{'decision.action':'WAIT','decision.valid':False})
    case('decision_invalid_raw','decision','WAIT por dados brutos inválidos com flags aprovadas',blocked='Não valida candles, freshness, NaN ou preços diretamente. Só gates strategy/risk/score/direction/MTF.')
    for side in ('BUY','SELL'):
        case('alert_'+side.lower(),'alert','Alerta '+side+' coerente',{'decision.action':side,'decision.direction':side,'decision.signal':side,'decision.setup':'SYNTHETIC','decision.score':80,'decision.confidence':.8},
          {'alert.valid':True,'alert.action':side,'alert.direction':side,'alert.signal':side,'alert.timestamp':'01/01/2026 10:00:00'})
    case('alert_wait','alert','Nenhum alerta em WAIT',expected={'alert.valid':False})
    case('alert_unapproved','alert','Decisão não aprovada',{'decision.action':'NONE'},{'alert.valid':False})
    case('alert_inconsistent','alert','Bloqueio de alerta inconsistente',blocked='DecisionResult.approved depende apenas de action BUY/SELL; AlertManager não verifica valid/coerência de direction/signal/preços.')
    return {'version':'H.10 RC3.11','status':'PREPARED_NOT_EXECUTED',**SAFETY,'data_origin':'SYNTHETIC_ONLY','candles':candles,'cases':cases}

def main():
    old=json.loads((ROOT/'h10_rc3_9_hashes.json').read_text(encoding='utf-8'))
    baseline={}; differences=[]
    for category,entries in [('source',old['source_sha256']),('artifact_rc3_9',old['artifact_sha256'])]:
        for name,expected in entries.items():
            actual=sha(ROOT/name) if (ROOT/name).is_file() else None; baseline[name]=actual
            if actual!=expected: differences.append({'path':name,'category':category,'expected':expected,'actual':actual})
    old_manifest_hash=sha(ROOT/'h10_rc3_9_hashes.json')
    if differences:
        report={'status':'SOURCE_CHANGED_REQUIRES_REVIEW',**SAFETY,'differences':differences,'tests_executed':False,'engines_imported':False,
                'executable_tests_prepared':False,'sources_verified':len(old['source_sha256'])}
        write(FILES[3],report); write(FILES[4],'SOURCE_CHANGED_REQUIRES_REVIEW\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(report['status']); return
    trees={p:ast.parse((ROOT/p).read_text(encoding='utf-8-sig'),filename=p) for p in old['source_sha256']}
    prior=json.loads((ROOT/'h10_rc3_9_preparation_report.json').read_text(encoding='utf-8'))
    fixtures=build_cases()
    # Verify fixture fields against real slotted model schemas via AST only.
    annotations={}
    for p,tree in trees.items():
        for cls in [n for n in tree.body if isinstance(n,ast.ClassDef)]:
            annotations[cls.name]={'fields':{n.target.id for n in cls.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name)},
                'bases':[ast.unparse(b) for b in cls.bases]}
    def fieldset(name):
        value=annotations.get(name,{}); fields=set(value.get('fields',set()))
        for base in value.get('bases',[]): fields|=fieldset(base)
        return fields
    context_types={n.target.id:ast.unparse(n.annotation).split(' | ')[0] for n in next(n for n in trees['core/analysis_context.py'].body if isinstance(n,ast.ClassDef) and n.name=='AnalysisContext').body if isinstance(n,ast.AnnAssign)}
    for case in fixtures['cases']:
        for field in case['input']:
            context_slot,attribute=field.split('.')
            if attribute not in fieldset(context_types[context_slot]): raise ValueError('FIXTURE_FIELD_NOT_DECLARED:'+field)
    ast.parse((OUT/FILES[1]).read_text(encoding='utf-8'))  # No import, collection or execution.
    contracts={}
    statements={
      'market_structure':'ready e >=6 candles; exclui último. Swings estritos ±2. UP=HH+HL; DOWN=LH+LL; caso restante com swing SIDEWAYS. Sem swing valid=False. BOS pelo último close fechado; CHOCH cruza swing anterior. Early return não limpa resultado antigo.',
      'price_action':'ready; clear/cópia structure.trend. UP->BUY, DOWN->SELL, demais NONE; valid=bias BUY/SELL e score>=30. Padrões somam pontos sem veto geral de conflito; _detect_patterns usa market.last_candle (pode estar em formação), enquanto helpers usam candles fechados.',
      'strategy':'Construtor carrega 3 setups reais. executar limpa strategy, ignora setups desabilitados/inválidos e seleciona maior score; empate mantém primeiro. Pode substituir context.strategy. Breakout BUY/SELL exige context.valid/bias, Trend/BOS/OB/FVG/breakout e filtros volume/liquidez; não exige todos os flags valid auxiliares.',
      'score':'Construtor(enable_order_flow=None,order_flow_weight=None), import tardio settings mesmo com parâmetros; peso finito 0..10. Pesos 20/20/15/10/10/10/5/10, total 0..100; valid=strategy.valid e total>=70; bias=strategy.signal. Confiança=total/100; sem veto geral direcional. OF explicitamente desabilitado/peso0.',
      'risk':'Entrada positiva; strategy.valid/signal BUY ou SELL; stop protetor no lado correto, distância<=500; RR>=1.5; risk_score>=70 aprova e valid=approved. Alvo estrutural RR insuficiente rejeita sem fallback; somente ausência de candidato permite 2R. Não oferece validação geral de NaN/freshness.',
      'decision':'Clear; WAIT se setup inválido, risco não aprovado, score inválido, direção inválida ou conflito/oposição MTF válido. Demais caminhos copiam níveis/score e geram BUY/SELL valid=True. Não recalcula risco, evidence, candles ou freshness.',
      'alert':'Clear; retorna se decision.approved=False. approved é action BUY/SELL; não depende de decision.valid. Copia ação/direção/sinal/setup/score/confiança, datetime.now sem timezone, valid=True e print. Não há validação de coerência; relógio futuro será fixado localmente.'}
    for key,e in prior['engines'].items():
        cls=next(n for n in trees[e['path']].body if isinstance(n,ast.ClassDef) and n.name==e['class'])
        contracts[key]={'source':e['path'],'constructor':e['constructor'],'public_methods':e['public_methods'],'input_output':e['input_output'],
          'demonstrated_contract':statements[key],
          'conditions_ast':[{'line':n.lineno,'condition':ast.unparse(n.test)} for n in ast.walk(cls) if isinstance(n,ast.If)],
          'output_assignments_ast':[{'line':n.lineno,'target':ast.unparse(t),'value':ast.unparse(n.value)} for n in ast.walk(cls) if isinstance(n,ast.Assign) for t in n.targets if isinstance(t,ast.Attribute)]}
    prepared=[c for c in fixtures['cases'] if c['status']=='PREPARED_NOT_EXECUTED']; blocked=[c for c in fixtures['cases'] if c['status']=='BLOCKED_BY_CONTRACT']
    changed=[p for p,h in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    if changed or sha(ROOT/'h10_rc3_9_hashes.json')!=old_manifest_hash: raise RuntimeError('SOURCES_CHANGED_DURING_PREPARATION')
    write(FILES[2],fixtures)
    report={'version':'H.10 RC3.11','status':'FUNCTIONAL_TESTS_PREPARED_NOT_EXECUTED',**SAFETY,
       'generated_at':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),'source_files_verified':len(old['source_sha256']),
       'prior_artifacts_verified':len(old['artifact_sha256']),'prior_manifest_verified':True,'total_integrity_files':len(baseline)+1,
       'hash_differences':[],'previous_hashes_updated':False,'contracts':contracts,'scenarios':fixtures['cases'],
       'scenario_count':len(fixtures['cases']),'executable_scenarios_prepared':len(prepared),'blocked_scenarios':len(blocked),
       'source_sha256':old['source_sha256'],'rc3_9_manifest_sha256':old_manifest_hash,'files_created':FILES,'original_files_modified':[],
       'engines_imported':False,'engines_instantiated':False,'engines_executed':False,'functional_tests_executed':False,
       'suite_imported_or_collected':False,'static_only':True,'excel_profit_dde_rtd_accessed':False,
       'runtime_dependencies_between_engines':['Structure -> PriceAction','Structure/PA/Liquidity/Volume/Context/OB/FVG -> Strategy',
         'Synthetic precomputed components -> Score','Synthetic Strategy/Structure/Liquidity/Volume/OB/FVG -> Risk','Strategy/Risk/Score/MTF -> Decision','Decision/Score/OrderFlow -> Alert'],
       'dependency_notes':['146 source files include package initializer imports; HTTP/filesystem/SAPI modules are dormant but present',
         'Models and default factories are real on future execution; slots verified statically for fixture inputs',
         'No third-party unresolved import in RC3.9 map; availability not probed by importing project code'],
       'artifact_sha256':{p:sha(OUT/p) for p in FILES[:3]},
       'limitations':['Draft expectations derived from source, not validated by running; no case claimed passed',
         'I/O traps do not sandbox native code, cached aliases, alternate import paths or arbitrary callbacks',
         'No hard process timeout in this prepared suite; future single-case run requires external duration control',
         'Synthetic BUY/SELL is in-memory only; operational envelope stays WAIT, no order adapter or runtime pipeline',
         'Blocked desired behavior must not be forced by changing engines or asserting undocumented gates',
         'RC3.10 8/8 is user-provided context, not a new test result of RC3.11'],
       'next_action':'User review and explicit authorization for decision_wait_conflict; one case only, no pipeline.'}
    write(FILES[3],report)
    lines=['H.10 RC3.11 — PREPARAÇÃO DOS TESTES FUNCIONAIS CONTROLADOS',
      'STATUS: FUNCTIONAL_TESTS_PREPARED_NOT_EXECUTED',
      'decision=WAIT; orders_allowed=False; live_certified=False; flow_complete=False','',
      f"INTEGRIDADE: {len(old['source_sha256'])} fontes + {len(old['artifact_sha256'])} artefatos RC3.9 + manifesto = {len(baseline)+1} arquivos.",
      'SHA256: zero divergências antes/depois; nenhum hash anterior atualizado.',
      'Auditoria exclusivamente texto/AST. Motores importados/instanciados/executados: 0.',
      'Testes funcionais executados: 0. Suíte não importada nem coletada.',
      'RC3.10 8/8 é contexto informado; não é resultado desta etapa.','',
      'CONTRATOS IDENTIFICADOS (todas as entradas são AnalysisContext; retorno é o mesmo contexto):']
    for key in ('market_structure','price_action','strategy','score','risk','decision','alert'):
        e=contracts[key]; signature=e['constructor']['signature']
        lines += [f"- {key}: construtor {signature}; executar(self, context). {statements[key]}"]
    lines += ['',f"CENÁRIOS: {len(fixtures['cases'])} mapeados; {len(prepared)} preparados; {len(blocked)} BLOCKED_BY_CONTRACT."]
    for c in fixtures['cases']:
        lines.append(f"- {c['id']}: {c['scenario']} — {c['status']}"+((' — '+c['reason']) if c['status']=='BLOCKED_BY_CONTRACT' else ''))
    lines += ['', 'As expectativas e entradas completas estão no fixtures JSON; condições/linhas/saídas AST no relatório JSON.',
      'Os bloqueios são lacunas dos contratos desejados, não reprovações em execução. O status global descreve preparação parcial: nenhum bloqueado é executável.',
      '', 'DEPENDÊNCIAS E EFEITOS:',
      'Todos importam EngineBase -> AnalysisContext; initializers trazem HTTP, exporters e SAPI dormentes.',
      'Strategy instancia três setups; Score lê settings mesmo com parâmetros explícitos.',
      'AnalysisContext cria modelos via default_factory; slots das entradas foram verificados por AST.',
      'MarketStructure e Alert imprimem; Alert lê relógio. Resultados/evidence são mutados em memória.',
      'Nenhum teste encadeia os sete motores: predecessores são estados sintéticos explícitos.',
      'Sem instalação, mudanças operacionais, app.main, Profit/Excel/DDE/RTD, ordens, commit/push.',
      '', 'BARREIRAS DA SUÍTE FUTURA:',
      'Sem imports de motores no topo; hashes antigos e novos conferidos antes do import.',
      'Exige --authorize-engine correspondente ao caso e --execute-one; exatamente um teste por comando.',
      'Bloqueados por contrato são recusados antes de importar motores. Estado inicial WAIT obrigatório.',
      'Barreiras de leitura: bloqueiam escrita via open/io.open/Path/os.open e remoção/rename/mkdir.',
      'Bloqueiam sockets, HTTP, subprocessos, comandos shell e imports conhecidos de app/market_data/COM/DDE.',
      'Bytecode desabilitado; stdout capturado; relógio Alert fixado somente no teste em memória.',
      'Essas barreiras NÃO foram executadas nem certificadas; não são sandbox de SO.',
      'Não cobrem código nativo, aliases já capturados, caminhos alternativos ou callbacks arbitrários.',
      'Sem timeout rígido interno: avaliar limite externo antes da execução autorizada.',
      'BUY/SELL sintético não permite ordem e não altera o envelope operacional WAIT.',
      '', 'ARQUIVOS NOVOS (diretório de entrega C:\\COPILOTO_GIT_SYNC):',*['- '+p for p in FILES],
      'Originais, RC3.9, testes antigos e relatórios anteriores modificados: nenhum.',
      'SHA256 dos artefatos: manifesto h10_rc3_11_hashes.json; auto-hash do manifesto fica fora dele.',
      *[p+': '+sha(OUT/p) for p in FILES[:3]],
      'O hash final deste TXT e do JSON será informado separadamente e no manifesto.',
      '', 'PRIMEIRO TESTE FUNCIONAL RECOMENDADO:',
      'decision_wait_conflict: flags sintéticas aprovadas e conflito MTF devem manter WAIT.',
      'Somente após revisão e autorização explícita do usuário:',
      '& "C:\\Users\\jb\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" -B .\\h10_rc3_11_future_suite.py --authorize-engine decision --case decision_wait_conflict --execute-one',
      'Comando NÃO executado. Argumento CLI não substitui autorização humana.',
      'Próxima ação: revisar casos e bloqueios, autorizar somente um caso e analisar seu resultado.',
      'Nenhuma aprovação funcional ou certificação live antecipada. AGUARDANDO REVISÃO E AUTORIZAÇÃO.']
    write(FILES[4],'\n'.join(lines)+'\n')
    write(FILES[5],{'artifact_sha256':{p:sha(OUT/p) for p in FILES if p!=FILES[5]},'source_sha256':old['source_sha256'],
                    'rc3_9_manifest_sha256':old_manifest_hash,**SAFETY})
    print(json.dumps({'status':report['status'],'prepared':len(prepared),'blocked':len(blocked),'verified':len(baseline)+1,'tests_executed':False}))

if __name__=='__main__': main()
