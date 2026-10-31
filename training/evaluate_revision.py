"""Evaluate classifier and hybrid separately, preserving individual predictions."""
import argparse,csv,hashlib,json,os,platform,sys,time,importlib.metadata
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report,confusion_matrix,accuracy_score,f1_score
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def savecsv(path,rows):
    if not rows:return
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def wilson(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;d=1+z*z/n
    center=(p+z*z/(2*n))/d;delta=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,float(center-delta)),min(1,float(center+delta))]

def main():
    p=argparse.ArgumentParser();p.add_argument('--data-file',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=False)
    from api.engine import DlpEngine,CLASS_NAMES
    engine=DlpEngine(); rows=[json.loads(l) for l in a.data_file.read_text(encoding='utf8').splitlines() if l.strip()]
    truth=np.array([r['label'] for r in rows]); predictions=[]; summary={}
    for mode in ['classifier','hybrid']:
        preds=[];actions=[]
        for i,row in enumerate(rows):
            start=time.perf_counter();error='';route='classifier';pred=-1;action='RETAIN'
            try:
                if mode=='classifier':
                    probs=engine._predict_proba(row['text']);pred=int(np.argmax(probs));action='ALLOW' if pred==0 else 'BLOCK'
                else:
                    result=engine.evaluate(row['text']);pred=CLASS_NAMES.index(result['category']);action=result['action'];route='|'.join(result['matched_rules'])
            except Exception as exc:error=type(exc).__name__
            preds.append(pred);actions.append(action)
            predictions.append(dict(component=mode,sample_id=i,text=row['text'],truth=CLASS_NAMES[row['label']],prediction=CLASS_NAMES[pred] if pred>=0 else '',action=action,route=route,error=error,latency_ms=(time.perf_counter()-start)*1000))
        pred=np.array(preds);valid=pred>=0;safe=int(sum(truth==0));restricted=int(sum(truth>0))
        fp=int(sum((truth==0)&(pred>0)));fn=int(sum((truth>0)&(pred==0)));correct=int(sum(truth==pred))
        per=classification_report(truth[valid],pred[valid],labels=range(9),target_names=CLASS_NAMES,output_dict=True,zero_division=0)
        summary[mode]={'n':len(rows),'correct':correct,'accuracy':correct/len(rows),'macro_f1_valid':f1_score(truth[valid],pred[valid],labels=range(9),average='macro'),
            'TP':int(sum((truth>0)&(pred>0))),'TN':int(sum((truth==0)&(pred==0))),'FP':fp,'FN':fn,'safe_n':safe,'restricted_n':restricted,
            'retained_errors':int(sum(~valid)),'FPR':fp/safe,'FNR':fn/restricted,'accuracy_wilson95':wilson(correct,len(rows)),
            'FPR_wilson95':wilson(fp,safe),'FNR_wilson95':wilson(fn,restricted),'confusion_matrix':confusion_matrix(truth[valid],pred[valid],labels=range(9)).tolist(),
            'per_class':per,'uncertainty_limit':'Wilson assumes independent Bernoulli trials. Synthetic family dependence restricts interpretation; these are development diagnostics.'}
        savecsv(a.output_dir/f'{mode}_per_class.csv',[dict(category=k,**v) for k,v in per.items() if k in CLASS_NAMES])
    savecsv(a.output_dir/'predictions.csv',predictions);savecsv(a.output_dir/'errors.csv',[r for r in predictions if r['truth']!=r['prediction']])
    summary['provenance']={'dataset_sha256':hashlib.sha256(a.data_file.read_bytes()).hexdigest(),'model_sha256':hashlib.sha256((ROOT/'models/dlp_slm/model.onnx').read_bytes()).hexdigest(),
       'platform':platform.platform(),'python':sys.version,'versions':{name:importlib.metadata.version(name) for name in ['torch','transformers','onnxruntime','numpy','scikit-learn','fastapi']},
       'scope':'Known historical development data. No independent human validation, real-provider traffic or new generalization claim.'}
    (a.output_dir/'metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:{m:v for m,v in r.items() if m in ['n','accuracy','macro_f1_valid','FP','FN','retained_errors']} for k,r in summary.items() if k!='provenance'},indent=2),flush=True)

if __name__=='__main__':main()
