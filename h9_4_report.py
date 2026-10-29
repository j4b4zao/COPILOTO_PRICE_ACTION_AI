import hashlib, json
from pathlib import Path

root=Path('C:/COPILOTO_PRICE_ACTION_AI')
before=json.loads((root/'h9_4_before.json').read_text(encoding='utf-8-sig'))
checked=0; changed=[]; unavailable=[]
for name,expected in before.items():
    if not expected: unavailable.append(name); continue
    try:
        actual=hashlib.file_digest(open(name,'rb'),'sha256').hexdigest().upper()
        checked+=1
        if actual!=expected: changed.append(name)
    except OSError: unavailable.append(name)
verification={'checked':checked,'changed':changed,'unavailable':unavailable}
(root/'h9_4_preservation.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
user=json.loads((root/'h9_4_user_evidence.json').read_text(encoding='utf-8-sig'))
sandbox=json.loads((root/'h9_4_evidence.json').read_text(encoding='utf-8-sig'))
files=['h9_4_diag.py','test_h9_4_diag.py','h9_4_report.py','h9_4_before.json','h9_4_evidence.json','h9_4_user_evidence.json','h9_4_preservation.json']
hashes='\n'.join(f'{f}: {hashlib.sha256((root/f).read_bytes()).hexdigest()}' for f in files)
text=f'''PROJETO: COPILOTO_PRICE_ACTION_AI
ETAPA: RC7.13.23-H.9.4 — DIAGNÓSTICO EXCEL COM/ROT
DIRETÓRIO DE ENTREGA: C:\\COPILOTO_GIT_SYNC
RESULTADO FINAL: ATTACHMENT_AVAILABLE
Data: {user['timestamp']}
live_certified=False; orders_allowed=False

1. DIAGNÓSTICO E CAUSA
Mesmo Excel PID 10152 antes/depois, sessão Windows 1, proprietário
DESKTOP-158793C\\jb, x64 (0x8664), não elevado, integridade média (8192).
Python 3.13 x64, mesmo executável nas duas execuções.
Sandbox: usuário CodexSandboxOffline, sessão 1, não elevado, integridade 8192.
GetActiveObject falhou 0x800401E3; ROT visível vazio; nenhuma janela Excel visível.
Consulta WMI negada 0x80041003; inventário alternativo e tokens foram acessíveis.
Fora do sandbox: usuário jb, sessão 1, não elevado, integridade 8192.
GetActiveObject funcionou no mesmo PID; ROT expôs os três arquivos e dois CLSIDs.
Causa operacional identificada por comparação: isolamento de contexto/usuário
do sandbox limita visibilidade COM/ROT e janelas. Não foi diferença de arquitetura,
sessão ou elevação nos processos examinados. O mecanismo específico interno de
isolamento (desktop/logon/token/ROT) não foi individualizado.
PID da H.9.3 (17452) é histórico; processo atual é 10152.

2. ATTACHMENT E WORKBOOKS
Método: pythoncom.GetActiveObject('Excel.Application'), objeto já existente.
Application.Hwnd={user['attachments'][0]['hwnd']}; PID correspondente=10152.
Workbooks.Count=3. FullName confirmados em memória:
'''+'\n'.join(user['attachments'][0]['workbooks'])+f'''
Sem duplicados ou ausências dos três nomes esperados.
ROT.GetObject somente para monikers já registrados; nenhum BindToObject.
OBJID_NATIVEOM em janelas EXCEL7 também consultado com timeout; zero erros no
contexto jb. Resultado principal registrado é GetActiveObject, sem dependência
desse método alternativo. Não houve leitura de células ou cotações.

3. TESTES OFFLINE
10 testes unittest aprovados, zero falhas, inclusive após ajuste de cleanup:
Excel acessível; ROT indisponível; privilégios diferentes; outra sessão;
múltiplas instâncias; workbook ausente; duplicado; falha de conexão;
cleanup sem Quit/Close; nenhum processo Excel.
São testes de classificação com dados sintéticos e liberação de referências;
não certificam todos os comportamentos Win32. Diagnóstico real separado anexado.
Comando: python.exe -B test_h9_4_diag.py.
Primeira execução apresentou aviso de liberação de IUnknown após CoUninitialize.
Corrigido no módulo novo: referências locais ROT/moniker/contexto/objeto são
liberadas antes de CoUninitialize. Execução seguinte sem esse aviso.

4. MENOR CORREÇÃO SEGURA
Executar o Python de attachment como jb na sessão interativa 1, sem elevação,
ou mediante execução fora do sandbox autorizada. Essa alternativa já foi testada
com sucesso, sem alterar registro, ACLs, permissões ou iniciar outro Excel.
Não é necessário reiniciar Excel ou Profit, nem instalar biblioteca adicional.
Para utilização futura: validar PID/Hwnd e FullName, bloquear ambiguidades,
manter getters somente leitura e liberar referências sem Quit/Close/Save.
Este diagnóstico não autoriza nem inicia Collector/Capture ou sessão observacional.

5. PRESERVAÇÃO E LIMITES
{checked} arquivos preexistentes tiveram SHA256 comparado antes/depois.
Arquivos divergentes: {changed}.
Sem modificação intencional de qualquer módulo preexistente/certificado.
Três workbooks em uso não puderam ser hasheados pelo contexto sandbox;
preservação byte a byte deles não é declarada. Nenhum workbook foi escrito,
salvo, fechado ou aberto pelo diagnóstico; fórmulas RTD não foram acessadas.
WINV26 preservado; WINZ26 apenas próximo contrato informado pelo usuário.
Contrato atual e atualização de preços são contexto confirmado pelo usuário,
não uma verificação de células nesta etapa. Nenhuma coleta real executada.
Mesma lista de PIDs Excel antes/depois nas duas execuções.
Não houve criação/encerramento de Excel, DispatchEx, Dispatch com ProgID,
Collector, Capture, ordens, sessão observacional, registro/ACL, commit/push
ou remoção de históricos. Alterações preexistentes no Git foram preservadas.

6. ARQUIVOS CRIADOS E SHA256
Arquivos de trabalho em C:\\COPILOTO_PRICE_ACTION_AI e cópias idênticas entregues
em C:\\COPILOTO_GIT_SYNC (arquivos novos H.9.4 somente):
{hashes}
saida_codex_h9_4.txt: hash final informado separadamente após gravação;
um relatório não pode incorporar seu próprio SHA256 definitivo.

7. REFERÊNCIAS TÉCNICAS
https://learn.microsoft.com/en-us/dotnet/fundamentals/runtime-libraries/system-runtime-interopservices-marshal-getactiveobject
https://learn.microsoft.com/en-us/previous-versions/office/troubleshoot/office-developer/use-visual-c-automate-run-program-instance
https://learn.microsoft.com/en-us/windows/win32/winauto/using-objid-nativeom-to-expose-a-native-object-model-interface-for-a-window

RESULTADO FINAL: ATTACHMENT_AVAILABLE (contexto jb); sandbox permanece bloqueado.
NENHUMA CERTIFICAÇÃO LIVE.
'''
(root/'saida_codex_h9_4.txt').write_text(text,encoding='utf-8')
print(json.dumps(verification,ensure_ascii=False))
print('REPORT_SHA256',hashlib.sha256((root/'saida_codex_h9_4.txt').read_bytes()).hexdigest())
