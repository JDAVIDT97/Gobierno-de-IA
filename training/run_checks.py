"""Keep native test return code and output independently of the terminal pipe."""
import argparse,json,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);p.add_argument('tests',nargs='*');a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=False)
    command=[sys.executable,'-m','pytest',*(a.tests or ['tests']),'-q',f'--junitxml={a.output_dir / "junit.xml"}']
    with (a.output_dir/'pytest.log').open('w',encoding='utf8') as output:
        result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
    report={'command':command,'exit_code':result.returncode}
    (a.output_dir/'execution.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
    raise SystemExit(result.returncode)
if __name__=='__main__':main()
