"""Reproducible candidate benchmark; individual timings and unique output."""
import argparse,csv,json,time,sys,uuid,hashlib,platform,os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np,requests
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE))
def main():
 p=argparse.ArgumentParser();p.add_argument('--data-file',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--samples',type=int,default=1000);p.add_argument('--repetitions',type=int,default=3);p.add_argument('--warmup',type=int,default=20);p.add_argument('--concurrency',type=int,default=1);p.add_argument('--endpoint');p.add_argument('--classifier-only',action='store_true');a=p.parse_args()
 a.output_dir.mkdir(parents=True,exist_ok=False)
 rows=[json.loads(l) for l in a.data_file.read_text(encoding='utf8').splitlines() if l.strip()];values=[r['text'] for r in rows]
 if a.endpoint:
  def runner(text):
   r=requests.post(a.endpoint,json={'user_id':str(uuid.uuid4()),'prompt':text,'destination':'https://chatgpt.com'},timeout=30);r.raise_for_status();result=r.json();result['_http_status']=r.status_code;return result
 else:
  from api.engine import DlpEngine
  e=DlpEngine();runner=e._predict_proba if a.classifier_only else e.evaluate
 lengths=[len(text) for text in values]
 metadata={'command':sys.argv,'dataset_sha256':hashlib.sha256(a.data_file.read_bytes()).hexdigest(),'platform':platform.platform(),'python':sys.version,
  'clock':'perf_counter from before request/inference to response/decision; excludes provider and browser',
  'chars':{'min':min(lengths),'median':float(np.median(lengths)),'max':max(lengths)},'class_counts':{str(k):sum(r['label']==k for r in rows) for k in sorted(set(r['label'] for r in rows))},
  'uuid_policy':'new UUID per HTTP request bypasses the per-user production rate limit; not a single user throughput estimate',
  'load_conditions':'shared workstation; execution overlap and process scope must be reported; no isolated-machine guarantee'}
 (a.output_dir/'run_config.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
 output=[];summary=[]
 for run in range(a.repetitions):
  for i in range(a.warmup):runner(values[i%len(values)])
  def timed(i):
   st=time.perf_counter();error='';route='classifier';status=''
   try:
    r=runner(values[i%len(values)])
    if isinstance(r,dict):
     route='model' if any(x.startswith('ML_MODEL') for x in r.get('matched_rules',[])) else 'rule';status=r.get('_http_status','')
   except Exception as exc:
    error=type(exc).__name__;route='error';status=getattr(getattr(exc,'response',None),'status_code','')
   return {'run':run+1,'sample':i,'latency_ms':(time.perf_counter()-st)*1000,'error':error,'http_status':status,'route':route}
  st=time.perf_counter()
  with ThreadPoolExecutor(max_workers=a.concurrency) as pool:batch=list(pool.map(timed,range(a.samples)))
  seconds=time.perf_counter()-st;output.extend(batch);v=[x['latency_ms'] for x in batch]
  errors=sum(bool(x['error']) for x in batch)
  summary.append({'run':run+1,'n':a.samples,'warmup':a.warmup,'unique_texts':len(values),'concurrency':a.concurrency,'mean_ms':float(np.mean(v)),'p50_ms':float(np.percentile(v,50)),'p95_ms':float(np.percentile(v,95)),'p99_ms':float(np.percentile(v,99)),'throughput':(a.samples-errors)/seconds,'attempted_throughput':a.samples/seconds,'completed':a.samples-errors,'errors':errors,'model_routes':sum(x['route']=='model' for x in batch)})
 with (a.output_dir/'latencies.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
 (a.output_dir/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
