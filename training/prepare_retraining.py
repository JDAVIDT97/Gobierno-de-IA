"""Sanitize legacy corpus and split by normalized prompt family, never row ID.

External nine-way labels remain weak labels; this script records that limitation.
It does not claim that a binary source supplied nine human-reviewed categories.
"""
import hashlib
import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.build_dataset import generate_pii_sample, generate_code_sample, generate_business_secret_sample

DEST = ROOT / 'data' / 'intent_clean_v4'

def family(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = re.sub(r'\d+', '#', text)
    return re.sub(r'\W+', ' ', text).strip()

def main():
    rng = random.Random(42)
    rows = []
    for name in ('train', 'val', 'test'):
        rows.extend(json.loads(line) for line in (ROOT / 'data/dataset_hybrid' / (name + '.jsonl')).read_text(encoding='utf8').split('\n') if line.strip())
    clean = {}
    conflicts = set()
    for row in rows:
        text = re.sub(r'\s*Caso sintético de entrenamiento [\w-]+\.\s*$', '', row['text']).strip()
        if not text:
            continue
        key = family(text)
        if key in clean and clean[key]['label'] != row['label']:
            conflicts.add(key)
        row = dict(row, text=text, group_id=hashlib.sha256(key.encode()).hexdigest(),
                   label_quality='weak_mapping' if row['source'].startswith('aplominski/') else 'synthetic')
        clean.setdefault(key, row)
    rows = [row for key, row in clean.items() if key not in conflicts]
    splits = {name: [] for name in ('train', 'val', 'test')}
    by_label = defaultdict(list)
    for row in rows:
        by_label[row['label']].append(row)
    for label, group in sorted(by_label.items()):
        rng.shuffle(group)
        # Tiny seed classes stay in training and are explicitly reported as
        # lacking independent support, rather than duplicating examples.
        nval = max(1, len(group)//10) if len(group) >= 5 else 0
        ntest = nval
        splits['val'].extend(group[:nval])
        splits['test'].extend(group[nval:nval+ntest])
        splits['train'].extend(group[nval+ntest:])
    # Restore varied synthetic literal-data examples from the original builder.
    # Only add these to training: numeric variants are not independent tests.
    generators = {1: generate_pii_sample, 2: generate_code_sample, 3: generate_business_secret_sample}
    random.seed(42)
    for label, generator in generators.items():
        category = by_label[label][0]['label_name']
        for _ in range(150):
            text = generator()
            splits['train'].append(dict(text=text, label=label, label_name=category,
                                        action='BLOCK', source='synthetic_literal_train_only',
                                        group_id='literal-'+str(label), label_quality='synthetic'))
    DEST.mkdir(exist_ok=True)
    for name, values in splits.items():
        rng.shuffle(values)
        (DEST / (name+'.jsonl')).write_text(''.join(json.dumps(row, ensure_ascii=True)+'\n' for row in values), encoding='utf8')
    groups = {name: {row['group_id'] for row in values} for name, values in splits.items()}
    assert not groups['train'] & groups['val']
    assert not groups['train'] & groups['test']
    assert not groups['val'] & groups['test']
    stats = dict(splits={name: len(values) for name, values in splits.items()},
                 counts={name: dict(Counter(row['label_name'] for row in values)) for name, values in splits.items()},
                 conflicting_families_removed=len(conflicts),
                 limitations=['Public nine-class mappings are weak labels.', 'Literal-data classes have training-only synthetic augmentation.', 'Normalized families prevent exact/numeric duplicates, not all semantic near-duplicates.'])
    (DEST / 'quality_report.json').write_text(json.dumps(stats, indent=2), encoding='utf8')
    print(json.dumps(stats, indent=2))

if __name__ == '__main__':
    main()
