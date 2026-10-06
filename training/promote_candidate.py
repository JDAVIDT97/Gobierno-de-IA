"""Promote an accepted local candidate with a recoverable backup."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
MODELS = (ROOT / 'models').resolve()
ACTIVE = MODELS / 'dlp_slm'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    if candidate.parent != MODELS or candidate == ACTIVE:
        parser.error('Candidate must be a direct child of the project models directory.')
    report = json.loads((candidate / 'acceptance_report.json').read_text(encoding='utf8'))
    if not report.get('approved_for_local_testing'):
        parser.error('Candidate has not passed the local acceptance gate.')
    required = ('model.onnx', 'pytorch_model.bin', 'config.json', 'aegis_config.json',
                'tokenizer_config.json', 'evaluation_report.json', 'corpus_preflight.json')
    missing = [name for name in required if not (candidate / name).exists()]
    if missing:
        parser.error('Missing candidate artifacts: ' + ', '.join(missing))
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    staging = MODELS / ('dlp_slm_staging_' + stamp)
    backup = MODELS / 'backups' / ('dlp_slm_' + stamp)
    backup.parent.mkdir(exist_ok=True)
    shutil.copytree(candidate, staging, ignore=shutil.ignore_patterns('checkpoints', '*.rejected.onnx', 'model.int8.onnx'))
    policy_path = staging / 'aegis_config.json'
    policy = json.loads(policy_path.read_text(encoding='utf8'))
    policy.update(version='5.0', deployment_scope='local_testing', quantization='fp32')
    policy_path.write_text(json.dumps(policy, indent=2), encoding='utf8')
    backed_up = False
    try:
        if ACTIVE.exists():
            shutil.copytree(ACTIVE, backup)
            backed_up = True
            # Exact stale artifacts would otherwise override the FP32 candidate.
            for stale in ('model.int8.onnx', 'model.joblib'):
                path = ACTIVE / stale
                if path.exists():
                    path.unlink()
        ACTIVE.mkdir(exist_ok=True)
        shutil.copytree(staging, ACTIVE, dirs_exist_ok=True)
    except Exception:
        if backed_up and backup.exists():
            ACTIVE.mkdir(exist_ok=True)
            shutil.copytree(backup, ACTIVE, dirs_exist_ok=True)
        raise
    print(json.dumps({'promoted': str(candidate), 'active': str(ACTIVE),
                      'backup': str(backup) if backed_up else None,
                      'scope': 'local_testing', 'onnx': 'FP32'}, indent=2))


if __name__ == '__main__':
    main()
