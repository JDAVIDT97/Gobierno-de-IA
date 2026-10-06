"""Data integrity preflight, separate from model accuracy and release gates."""
import argparse
from collections import Counter
import json
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.deployment_gate import CLASSES
from training.build_corpus_v5 import normalized


def inspect_corpus(base):
    errors, gaps, groups, texts = [], [], {}, {}
    fingerprints = {}
    counts = {}
    for split in ('train', 'val', 'test'):
        path = base / (split + '.jsonl')
        if not path.exists():
            errors.append(f'Missing {path.name}')
            continue
        fingerprints[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        rows = [json.loads(line) for line in path.read_text(encoding='utf8').split('\n') if line.strip()]
        groups[split], texts[split] = set(), set()
        counts[split] = Counter()
        for row in rows:
            category, label = row.get('label_name'), row.get('label')
            if category not in CLASSES or not isinstance(label, int) or label != CLASSES.index(category):
                errors.append(f'{split}: inconsistent label')
                continue
            counts[split][category] += 1
            text = row.get('text', '')
            if not text.strip() or 'Caso sintético de entrenamiento' in text or any(c in text for c in CLASSES):
                errors.append(f'{split}: empty text or target leakage')
            if row.get('label_quality') in ('weak_mapping', None):
                errors.append(f'{split}: undocumented/weak category mapping')
            if row.get('split') != split:
                errors.append(f'{split}: inconsistent split provenance')
            if row.get('original_split') in ('val', 'test') and row['original_split'] != split:
                errors.append(f'{split}: source holdout moved')
            if not row.get('source_id') or not row.get('source_revision') or not row.get('group_id'):
                errors.append(f'{split}: missing provenance')
            if row.get('action') != ('ALLOW' if label == 0 else 'BLOCK'):
                errors.append(f'{split}: inconsistent action')
            key = normalized(text)
            if key in texts[split]:
                errors.append(f'{split}: duplicate normalized text')
            groups[split].add(row.get('group_id'))
            texts[split].add(key)
        for category in CLASSES:
            required = 30 if split != 'train' else 100
            if counts[split][category] < required:
                gaps.append(f'{split}/{category}: {counts[split][category]} < {required}')
        if counts[split] and max(counts[split].values()) / min(counts[split].values()) > 1.5:
            gaps.append(f'{split}: class imbalance exceeds 1.5x')
    for first, second in (('train', 'val'), ('train', 'test'), ('val', 'test')):
        if groups.get(first, set()) & groups.get(second, set()) or texts.get(first, set()) & texts.get(second, set()):
            errors.append(f'Overlap between {first} and {second}')
    quality = base / 'quality_report.json'
    if not quality.exists():
        gaps.append('Missing curation/quality report')
    else:
        report = json.loads(quality.read_text(encoding='utf8'))
        if not report.get('ready_for_training', False):
            gaps.extend(report.get('blockers', ['Curation not approved']))
    ready = not errors and not gaps
    return dict(integrity_passed=not errors, errors=sorted(set(errors)),
                coverage_gaps=sorted(set(gaps)), ready_for_training=ready,
                ready_for_production_training=ready and report.get('ready_for_production_training', False),
                counts=counts, dataset_files_sha256=fingerprints)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data/intent_curated_v5')
    parser.add_argument('--experimental', action='store_true', help='Check integrity only; never grants release approval')
    args = parser.parse_args()
    report = inspect_corpus(args.data_dir)
    print(json.dumps(report, indent=2))
    passed = report['integrity_passed'] if args.experimental else report['ready_for_training']
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
