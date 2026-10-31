"""Check minimization, access and purge against synthetic data only."""
import argparse,datetime,json,sqlite3,subprocess,sys,uuid
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=False)
    headers={'Authorization':'Bearer synthetic-review-admin'};base='http://127.0.0.1:8017'
    text="Prueba sintética de privacidad password = 'SoloPruebaAEGIS2026'"
    response=requests.post(base+'/v1/audit',json={'user_id':str(uuid.uuid4()),'prompt':text,'destination':'https://chatgpt.com'},timeout=30)
    response.raise_for_status();body=response.json()
    report={'audit_http':response.status_code,'preview_is_marker':body['redacted_preview'].startswith('[BLOCKED_CONTENT_NOT_RETAINED:'),
      'secret_absent_from_response':'SoloPruebaAEGIS2026' not in json.dumps(body),'access':{}}
    for endpoint in ['/v1/logs','/v1/kpis','/v1/export-csv','/v1/export-pdf']:
        report['access'][endpoint]={'without_token':requests.get(base+endpoint,timeout=15).status_code,'with_token':requests.get(base+endpoint,headers=headers,timeout=15).status_code}
    logs=requests.get(base+'/v1/logs?limit=200',headers=headers,timeout=15).json()
    report['secret_absent_from_latest_records']='SoloPruebaAEGIS2026' not in json.dumps(logs)
    db=a.output_dir/'retention_synthetic.sqlite';now=datetime.datetime.now(datetime.timezone.utc)
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, timestamp TEXT, prompt_redacted TEXT)')
        for age in [45,1]:conn.execute('INSERT INTO audit_logs(timestamp,prompt_redacted) VALUES (?,?)',((now-datetime.timedelta(days=age)).isoformat(),'[SYNTHETIC]'))
    command=[sys.executable,str(ROOT/'training/purge_audit.py'),'--database',str(db),'--days','30']
    report['retention_dry_run']=json.loads(subprocess.check_output(command,text=True))
    with sqlite3.connect(db) as conn:report['rows_after_dry_run']=conn.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0]
    report['retention_apply']=json.loads(subprocess.check_output(command+['--apply'],text=True))
    with sqlite3.connect(db) as conn:report['rows_after_apply']=conn.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0]
    report['retention_note']='30 days is only a synthetic test parameter; no institutional retention period or ethics approval is asserted.'
    report['passed']=report['preview_is_marker'] and report['secret_absent_from_response'] and report['secret_absent_from_latest_records'] and report['rows_after_dry_run']==2 and report['rows_after_apply']==1 and all(v['without_token']==401 and v['with_token']==200 for v in report['access'].values())
    (a.output_dir/'results.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
