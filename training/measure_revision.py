"""Measure HTTP after the verified test run, retaining server resource samples."""
import argparse,datetime,json,os,subprocess,sys,threading,time,importlib.metadata,platform
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence-root',type=Path,required=True);p.add_argument('--server-pid',type=int,required=True);a=p.parse_args();out=a.evidence_root
    marker=out/'final_verified/execution.json'
    while not marker.exists():time.sleep(5)
    if json.loads(marker.read_text())['exit_code']!=0:raise RuntimeError('Final tests failed; benchmark not started')
    process=psutil.Process(a.server_pid);samples=[];stop=threading.Event()
    def sample():
        while not stop.is_set():
            try:samples.append({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'server_pid':process.pid,'rss_bytes':process.memory_info().rss,'cpu_seconds':sum(process.cpu_times()[:2])})
            except psutil.Error:break
            stop.wait(.25)
    thread=threading.Thread(target=sample);thread.start()
    try:
        for concurrency in [1,4]:
            cmd=[sys.executable,str(ROOT/'training/benchmark_inference.py'),'--data-file',str(out/'historical_corpus/test.jsonl'),'--output-dir',str(out/f'http_c{concurrency}'),'--endpoint','http://127.0.0.1:8017/v1/audit','--concurrency',str(concurrency),'--repetitions','3','--samples','1000','--warmup','20']
            with (out/f'http_c{concurrency}.log').open('w',encoding='utf8') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    finally:
        stop.set();thread.join()
        (out/'server_resources.json').write_text(json.dumps({'scope':'Entire HTTP server process, includes model and framework; sampling is not a proof of absolute peak memory','samples':samples},indent=2),encoding='utf8')
    env={'python':sys.version,'platform':platform.platform(),'logical_processors':os.cpu_count(),'ram_bytes':psutil.virtual_memory().total,'versions':{n:importlib.metadata.version(n) for n in ['torch','transformers','onnxruntime','numpy','scikit-learn','fastapi','playwright']},'conditions':'Shared workstation. HTTP c1 and c4 executed sequentially after test runner completed; unrelated user processes were not terminated.'}
    (out/'environment.json').write_text(json.dumps(env,indent=2),encoding='utf8')
    print('HTTP protocol completed: 6000 timed requests plus warmups; inspect summaries and errors.')
if __name__=='__main__':main()
