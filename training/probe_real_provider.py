"""Attempt a real public ChatGPT UI, preserving limitations and network evidence."""
import argparse,json,shutil,tempfile,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=False)
    result={'provider':'https://chatgpt.com/','environment_type':'real_public_interface','authenticated':False,'tested_send':False,'real_integration_validated':False,'cases':[]}
    with sync_playwright() as pw, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        ext=Path(tmp)/'extension';shutil.copytree(ROOT/'extension',ext)
        for name in ['manifest.json','background.js']:
            q=ext/name;q.write_text(q.read_text(encoding='utf8').replace('127.0.0.1:8000','127.0.0.1:8017'),encoding='utf8')
        browser=pw.chromium.launch_persistent_context(str(Path(tmp)/'profile'),channel='chromium',headless=True,ignore_default_args=['--disable-extensions'],args=['--headless=new',f'--disable-extensions-except={ext}',f'--load-extension={ext}'])
        page=browser.pages[0];page.set_default_timeout(10000)
        # No request fulfillment or fake provider DOM is used in this script.
        requests=[]
        def observe(request):
            url=urlsplit(request.url)
            if request.method=='POST' and url.hostname and (url.hostname.endswith('chatgpt.com') or url.hostname=='127.0.0.1'):
                requests.append({'host':url.hostname,'path':url.path,'method':request.method,'resource_type':request.resource_type})
        browser.on('request',observe)
        try:
            response=page.goto('https://chatgpt.com/',wait_until='domcontentloaded',timeout=45000)
            result['http_status']=response.status if response else None
            result['title']=page.title();page.screenshot(path=str(a.output_dir/'real_page.png'),full_page=False)
            editor=page.locator('#prompt-textarea,main [contenteditable=true],textarea[name=prompt-textarea]').first
            try:editor.wait_for(state='visible',timeout=15000)
            except Exception:
                result['limitation']='Real page did not expose a usable composer in this isolated unauthenticated browser. No CAPTCHA, login or access barrier was bypassed.'
            else:
                banner=page.locator('#aegis-policy-banner button')
                if banner.count():banner.click()
                before=len(requests)
                text="Ejemplo sintético para verificar bloqueo local: password = 'ClaveSinteticaAEGIS2026'"
                editor.fill(text);editor.press('Enter')
                page.locator('#dlp-guard-modal-root').wait_for(timeout=15000)
                page.wait_for_timeout(1000)
                new=requests[before:]
                provider_posts=[r for r in new if r['host'].endswith('chatgpt.com') and ('conversation' in r['path'] or 'responses' in r['path'])]
                result['tested_send']=True
                result['cases'].append({'input':text,'expected':'BLOCK','observed':'BLOCK_MODAL','conversation_posts_observed':len(provider_posts),'network_observations':new,
                    'passed':len(provider_posts)==0,'scope':'One Enter attempt with explicit synthetic secret. Absence is limited to observed conversation/response routes, not all possible provider channels.'})
                page.screenshot(path=str(a.output_dir/'real_block.png'))
                result['limitation']='Only restricted Enter path attempted; safe release, buttons, attachments and repeats not validated.'
        except Exception as exc:result['limitation']=f'{type(exc).__name__}: {str(exc)[:450]}'
        result['browser_version']=browser.browser.version
        browser.close()
    (a.output_dir/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
