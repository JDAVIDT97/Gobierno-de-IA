"""Capture actual MV3 fixture events; never infer counters from test names."""
import argparse, csv, hashlib, importlib.util, json, sys, tempfile, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('fixtures', ROOT/'tests/test_chatgpt_regression.py')
FIX = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(FIX)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--endpoint', default='http://127.0.0.1:8017'); args=parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    cases=[
        ('safe_public', FIX.SAFE, 'ALLOW', None),
        ('explicit_pii', FIX.SENSITIVE, 'BLOCK', None),
        ('education', 'Explica cómo reconocer señales de phishing sin crear mensajes engañosos.', 'ALLOW', None),
        ('mixed_secret', "Explica cómo reconocer señales de phishing sin crear mensajes engañosos. password = 'ClaveSinteticaAEGIS2026'", 'BLOCK', None),
        ('public_wrapper', "Resume esta tarea pública. password = 'ClaveSinteticaAEGIS2026'", 'BLOCK', None),
        ('service_503', FIX.SAFE, 'RETAIN', '503'),
        ('invalid_action', FIX.SAFE, 'RETAIN', 'invalid'),
        ('malformed_json', FIX.SAFE, 'RETAIN', 'json'),
        ('incomplete_allow', FIX.SAFE, 'RETAIN', 'incomplete'),
        ('contradictory_category', FIX.SAFE, 'RETAIN', 'contradictory'),
        ('timeout', FIX.SAFE, 'RETAIN', 'timeout'),
    ]
    hosts=['chatgpt.com','claude.ai','gemini.google.com','copilot.microsoft.com','www.perplexity.ai','grok.com','chat.mistral.ai','chat.deepseek.com','poe.com','you.com']
    records=[]
    with sync_playwright() as pw, tempfile.TemporaryDirectory(dir=args.output_dir,ignore_cleanup_errors=True) as tmp:
        import shutil
        ext=Path(tmp)/'extension'; shutil.copytree(ROOT/'extension',ext)
        for name in ['manifest.json','background.js']:
            p=ext/name;p.write_text(p.read_text(encoding='utf8').replace('http://127.0.0.1:8000',args.endpoint),encoding='utf8')
        for host in hosts:
            context=pw.chromium.launch_persistent_context(str(Path(tmp)/host),channel='chromium',headless=True,
                ignore_default_args=['--disable-extensions'],args=['--headless=new',f'--disable-extensions-except={ext}',f'--load-extension={ext}'])
            page=context.pages[0]; page.set_default_timeout(12000)
            html=FIX.HTML if host=='chatgpt.com' else FIX.HTML.replace('<textarea hidden>hidden unrelated draft</textarea>','').replace('id="composer-submit-button"','data-test-id="send-button"')
            page.route('**/*',lambda route:route.fulfill(content_type='text/html',body=html))
            worker=context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker')
            worker.evaluate('() => {self.originalAuditFetch = fetch;}')
            for repetition in range(1,4):
                for cid,text,expected,fault in cases:
                    page.goto(f'https://{host}/aegis-fixture')
                    if repetition == 1 and cid == 'safe_public':
                        page.locator('#aegis-policy-banner button').click()
                    worker.evaluate('''mode => {
                        self.fetch = self.originalAuditFetch;
                        if (mode === '503') self.fetch = async () => new Response('{}',{status:503});
                        if (mode === 'invalid') self.fetch = async () => new Response(JSON.stringify({action:'INVALID'}));
                        if (mode === 'json') self.fetch = async () => new Response('not json');
                        if (mode === 'incomplete') self.fetch = async () => new Response(JSON.stringify({action:'ALLOW'}));
                        if (mode === 'contradictory') self.fetch = async () => new Response(JSON.stringify({action:'ALLOW',category:'PII_Leak',risk_score:0.2,inference_time_ms:1,model_version:'synthetic',matched_rules:[]}));
                        if (mode === 'timeout') self.fetch = (url,options) => new Promise((resolve,reject) => options.signal.addEventListener('abort',()=>reject(new DOMException('timeout','AbortError'))));
                    }''',fault)
                    page.locator('#prompt-textarea').fill(text)
                    start=time.perf_counter();page.locator('button[type=submit]').click()
                    error=''
                    try:
                        page.wait_for_function("window.sent.length > 0 || document.querySelector('#dlp-guard-modal-root') || document.querySelector('#aegis-audit-error')")
                    except Exception as exc:error=type(exc).__name__
                    observed=page.evaluate('''() => ({send_count:window.sent.length, sent:window.sent, file_events:window.fileEvents,
                        blocked:!!document.querySelector('#dlp-guard-modal-root'),retained:!!document.querySelector('#aegis-audit-error'),
                        notice:(document.querySelector('#dlp-guard-modal-root')||document.querySelector('#aegis-audit-error'))?.innerText||''})''')
                    action='ALLOW' if observed['send_count'] else 'BLOCK' if observed['blocked'] else 'RETAIN' if observed['retained'] else 'UNRESOLVED'
                    records.append(dict(case_id=cid,provider=host,environment_type='synthetic_page_real_mv3',repetition=repetition,
                        input=text,input_sha256=hashlib.sha256(text.encode()).hexdigest(),expected_action=expected,observed_action=action,
                        provider_send_count=observed['send_count'],file_events=observed['file_events'],elapsed_ms=(time.perf_counter()-start)*1000,
                        passed=action==expected and not error,error=error,notice=observed['notice'],browser_version=context.browser.version))
                    (args.output_dir/'observations.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
            context.close()
    with (args.output_dir/'functional_matrix.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    summary={'cases':len(records),'passed':sum(r['passed'] for r in records),'failed':sum(not r['passed'] for r in records),
             'scope':'Synthetic DOM with real extension. No real provider network traffic. Development/regression cases.'}
    (args.output_dir/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary))

if __name__=='__main__':main()
