"""Recover original bytes and require exact agreement with model preflight."""
import argparse, hashlib, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--preflight',type=Path,required=True);a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=False)
    preflight=json.loads(a.preflight.read_text(encoding='utf8'));report={'preflight':preflight,'splits':{}}
    for split in ['train','val','test']:
        src=a.data_dir/f'{split}.jsonl';lines=src.read_bytes().splitlines(keepends=True)
        kept=[line for line in lines if json.loads(line).get('source')!='aegis/adversarial-regressions-es-v6']
        target=a.output_dir/src.name;target.write_bytes(b''.join(kept))
        sha=hashlib.sha256(target.read_bytes()).hexdigest()
        # Preflight layouts differ by historical version. Require the recovered digest to occur verbatim.
        if sha not in json.dumps(preflight):raise RuntimeError(f'{split}: hash absent from original preflight: {sha}')
        report['splits'][split]={'active_n':len(lines),'historical_n':len(kept),'excluded_n':len(lines)-len(kept),'sha256':sha,'preflight_match':True}
    (a.output_dir/'corpus_lineage.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report['splits'],indent=2))

if __name__=='__main__':main()
