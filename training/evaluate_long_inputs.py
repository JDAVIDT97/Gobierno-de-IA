"""Development diagnostics of boundaries; report failures without hiding them."""
import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=False)
    from api.engine import DlpEngine
    e=DlpEngine();records=[]
    for size in [3199,3200,3399,3400,4096,10000]:
        filler=('material descriptivo sin nombres ni identificadores. '*300)[:size]
        for boundary in [0,200,3200,3400,size]:
            secret=" password = 'ClaveSinteticaAEGIS2026' "
            pos=min(boundary,len(filler));text=filler[:pos]+secret+filler[pos:]
            chunks=[text[i:i+3400] for i in range(0,len(text),3200)]
            results=[e.evaluate(c) for c in chunks]
            action='BLOCK' if any(r['action']=='BLOCK' for r in results) else 'ALLOW'
            tokens=e.tokenizer(text,add_special_tokens=False)['input_ids']
            windows=e.tokenizer(text,truncation=True,max_length=256,stride=32,return_overflowing_tokens=True)['input_ids']
            recovered=[]
            for i,window in enumerate(windows):recovered.extend(window[1:-1] if i==0 else window[33:-1])
            records.append(dict(case_id=f'explicit_{size}_{pos}',chars=len(text),tokens=len(tokens),windows=len(windows),chunks=len(chunks),
                input=text,expected='BLOCK',observed=action,passed=action=='BLOCK',token_coverage_exact=recovered==tokens,
                scope='Chunk pipeline evaluated locally; no upload or provider traffic; expected label is generated, not human validated.'))
    for distance in [180,220,800,3400]:
        # The credential key and value become separated. This probes a known limitation;
        # it does not assume the encoder can reason across unrelated windows.
        text='password = '+(' '*distance)+"'ClaveSinteticaAEGIS2026'"
        chunks=[text[i:i+3400] for i in range(0,len(text),3200)]
        results=[e.evaluate(c) for c in chunks]
        action='BLOCK' if any(r['action']=='BLOCK' for r in results) else 'ALLOW'
        records.append(dict(case_id=f'distributed_{distance}',chars=len(text),tokens='',windows='',chunks=len(chunks),input=text,
            expected='BLOCK',observed=action,passed=action=='BLOCK',token_coverage_exact='',scope='Distributed synthetic credential diagnostic; not independent human evidence.'))
    with (a.output_dir/'results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    summary={'n':len(records),'passed':sum(r['passed'] for r in records),'failed':sum(not r['passed'] for r in records),'failed_ids':[r['case_id'] for r in records if not r['passed']],
        'scope':'Known-structure synthetic development diagnostics. Any failed distributed case must remain a limitation; not a general semantic-coverage claim.'}
    (a.output_dir/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary))
if __name__=='__main__':main()
