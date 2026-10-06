"""Reproducible corpus with explicit source tasks, no keyword relabeling.

Only prompt-injection positives have a direct public nine-class mapping.
Binary safety and injection-negative labels are auxiliary, never Safe_Use.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.intent_policy_v5 import SCENARIOS
from data.intent_compositional_v5 import generated_scenarios
from data.adversarial_regressions_v6 import adversarial_rows
from data.public_reviews_v5 import REVIEWS
from training.deployment_gate import CLASSES

OUT = ROOT / 'data/intent_curated_v5'
SOURCES = {
    'deepset/prompt-injections': {
        'license': 'Card conflict: top-level Apache-2.0; dataset_info CC-BY-4.0. Retain attribution; review before redistribution.',
        'task': 'prompt_injection',
    },
    'nvidia/Aegis-AI-Content-Safety-Dataset-2.0': {
        'license': 'CC-BY-4.0', 'task': 'general_content_safety',
    },
}


def normalized(text):
    value = unicodedata.normalize('NFKC', text).casefold()
    value = re.sub(r'\d+', '#', value)
    return re.sub(r'\W+', ' ', value).strip()


def digest(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def jsonl(path, values):
    path.write_text(''.join(json.dumps(v, ensure_ascii=True) + '\n' for v in values), encoding='utf8')


def map_public(task, original_label):
    # Absence of an injection is not absence of PII, secrets or other harm.
    if task == 'prompt_injection' and original_label == 1:
        return 'Role_Evasion_Jailbreak'
    return None


def features(text):
    low = text.casefold()
    # Audit-only lexical indicators. Never generate the target or train on them.
    return {
        'mentions_private_material': any(x in low for x in ('privad', 'confidencial', 'reservad', 'secreto')),
        'mentions_external_destination': any(x in low for x in ('extern', 'internet', 'públic', 'publica')),
        'mentions_credentials': any(x in low for x in ('contraseña', 'credencial', 'token', 'password')),
        'mentions_academic_context': any(x in low for x in ('tarea', 'ensayo', 'clase', 'práctica')),
        'mentions_authorization': any(x in low for x in ('autoriz', 'permiso', 'consentimiento')),
    }


def make_row(text, category, source, source_id, split, quality, language='und', **extra):
    return dict(text=text, label=CLASSES.index(category), label_name=category,
                action='ALLOW' if category == 'Safe_Use' else 'BLOCK', source=source,
                source_id=str(source_id), group_id=digest(normalized(text)),
                split=split, label_quality=quality, language=language,
                audit_features=features(text), **extra)


def local_rows():
    rows = []
    for category in CLASSES:
        prompts = SCENARIOS[category].splitlines()
        assert len(prompts) == len(set(prompts))
        order = list(range(len(prompts)))
        random.Random(42).shuffle(order)
        for position, index in enumerate(order):
            split = 'test' if position < 3 else 'val' if position < 6 else 'train'
            rows.append(make_row(prompts[index], category, 'aegis/authored-es-v5',
                                 f'{category}:{index}', split, 'synthetic_authored_not_human_reviewed',
                                 language='es', original_label=category, source_revision='v5'))
        for split, source_id, text in generated_scenarios(category):
            rows.append(make_row(text, category, 'aegis/compositional-es-v5', source_id,
                                 split, 'synthetic_policy_components_reviewed_not_human',
                                 language='es', original_label=category, source_revision='v5.1',
                                 semantic_family=source_id))
    for category, split, family_id, transform, text in adversarial_rows():
        rows.append(make_row(
            text, category, 'aegis/adversarial-regressions-es-v6',
            f'{family_id}:{transform}', split, 'synthetic_adversarial_not_human_reviewed',
            language='es', original_label=category, source_revision='v6.0',
            semantic_family=family_id, adversarial_transform=transform,
        ))
    return rows


def snapshot_source(repo, offline):
    import requests
    from huggingface_hub import hf_hub_download
    folder = OUT / 'sources' / repo.replace('/', '__')
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = folder / 'snapshot.json'
    if offline:
        return json.loads(snapshot.read_text(encoding='utf8'))
    response = requests.get('https://huggingface.co/api/datasets/' + repo, timeout=60)
    response.raise_for_status()
    info = response.json()
    revision = info['sha']
    card_path = Path(hf_hub_download(repo, 'README.md', repo_type='dataset', revision=revision))
    card = card_path.read_text(encoding='utf8')
    (folder / 'README.source.md').write_text(card, encoding='utf8')
    records, checksums = [], {}
    for item in info['siblings']:
        name = item['rfilename']
        if repo.startswith('deepset/'):
            if not name.endswith('.parquet'):
                continue
            split = 'test' if '/test-' in name else 'train'
        else:
            if name not in ('train.json', 'validation.json', 'test.json'):
                continue  # Exclude generated response/refusal datasets.
            split = {'validation': 'val'}.get(Path(name).stem, Path(name).stem)
        path = Path(hf_hub_download(repo, name, repo_type='dataset', revision=revision))
        checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if name.endswith('.parquet'):
            import pyarrow.parquet as pq
            values = pq.read_table(path).to_pylist()
        else:
            values = json.loads(path.read_text(encoding='utf8'))
        for index, value in enumerate(values):
            text = value.get('text', value.get('prompt', ''))
            if not text or text == 'REDACTED':
                continue
            records.append(dict(text=text, source=repo, source_id=str(value.get('id', index)),
                                source_file=name, source_revision=revision, original_split=split,
                                original_label=value.get('label', value.get('prompt_label')),
                                original_categories=value.get('violated_categories'),
                                label_source=value.get('prompt_label_source', 'dataset_annotation')))
    result = dict(repository=repo, revision=revision, files_sha256=checksums,
                  card_sha256=digest(card), records=records, **SOURCES[repo])
    snapshot.write_text(json.dumps(result, ensure_ascii=True), encoding='utf8')
    return result


def reconcile(rows):
    """Keep evaluation membership on collisions; quarantine contradictory labels."""
    groups = defaultdict(list)
    for row in rows:
        groups[row['group_id']].append(row)
    kept, rejected = [], []
    priority = {'test': 0, 'val': 1, 'train': 2}
    for key in sorted(groups):
        group = groups[key]
        if len({r['label'] for r in group}) > 1:
            rejected.extend(dict(group_id=key, source=r['source'], source_id=r['source_id'],
                                 reason='conflicting_labels') for r in group)
            continue
        selected = sorted(group, key=lambda r: priority[r['split']])[0]
        kept.append(selected)
        rejected.extend(dict(group_id=key, source=r['source'], source_id=r['source_id'],
                             reason='duplicate_normalized_family') for r in group if r is not selected)
    return kept, rejected


def legacy_quarantine():
    rows = []
    for path in sorted((ROOT / 'data/dataset_hybrid').glob('*.jsonl')):
        for index, line in enumerate(path.read_text(encoding='utf8').split('\n')):
            if line.strip():
                row = json.loads(line)
                rows.append(dict(source_file=path.relative_to(ROOT).as_posix(), line=index+1,
                                 text_sha256=digest(row['text']), original_label=row['label'],
                                 reason='legacy_keyword_labels_or_label_leaking_templates'))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Rebuild using pinned local snapshots')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows, auxiliary, manifest = local_rows(), [], []
    mapped_counts = Counter()
    for repo in SOURCES:
        print('Reading source:', repo, flush=True)
        source = snapshot_source(repo, args.offline)
        manifest.append({k: v for k, v in source.items() if k != 'records'})
        reviews = {item[0]: item for item in REVIEWS} if repo.startswith('nvidia/') else {}
        found_reviews = set()
        for record in source['records']:
            category = map_public(source['task'], record['original_label'])
            review = reviews.get(record['source_id'])
            if review:
                if record['text'] != review[2]:
                    raise ValueError('Source text changed; review invalid: ' + record['source_id'])
                category = review[1]
                found_reviews.add(record['source_id'])
            split = record['original_split']
            if category:
                # Original test stays test. Derive validation only from original train.
                if split == 'train' and int(digest(normalized(record['text']))[:8], 16) % 10 == 0:
                    split = 'val'
                cap_key = (repo, category, split)
                # Public single-task corpora add linguistic variety, but never
                # dominate the local nine-way policy distribution.
                if not review and mapped_counts[cap_key] >= 15:
                    auxiliary.append(dict(record, task=source['task'], category_mapping=category,
                                          reason='Eligible mapping held out by per-source class/split balance cap'))
                    continue
                mapped_counts[cap_key] += 1
                extra = {k: v for k, v in record.items() if k not in ('text', 'source', 'source_id')}
                if review:
                    extra.update(review_rationale=review[3], reviewed_text_sha256=digest(review[2]))
                rows.append(make_row(record['text'], category, repo, record['source_id'], split,
                                     'agent_reviewed_not_human_reviewed' if review else 'source_task_mapping',
                                     language='en' if review else 'und', **extra))
            else:
                auxiliary.append(dict(record, task=source['task'], category_mapping=None,
                                      reason='Original task does not establish a nine-class DLP label'))
        if set(reviews) != found_reviews:
            raise ValueError('Reviewed source IDs disappeared: ' + str(set(reviews) - found_reviews))
    rows, rejected = reconcile(rows)
    splits = {s: [r for r in rows if r['split'] == s] for s in ('train', 'val', 'test')}
    for split, values in splits.items():
        jsonl(OUT / (split + '.jsonl'), values)
    jsonl(OUT / 'auxiliary_original_labels.jsonl', auxiliary)
    jsonl(OUT / 'quarantine.jsonl', legacy_quarantine() + rejected)
    (OUT / 'sources_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    counts = {s: dict(Counter(r['label_name'] for r in values)) for s, values in splits.items()}
    balance = {s: round(max(v.values()) / min(v.values()), 4) for s, v in counts.items()}
    required = {'train': 100, 'val': 30, 'test': 30}
    gaps = [f'{split}/{category}: {counts[split].get(category, 0)} < {minimum}'
            for split, minimum in required.items() for category in CLASSES
            if counts[split].get(category, 0) < minimum]
    training_blockers = list(gaps)
    deployment_review_blockers = [
        'Synthetic Spanish scenarios still require independent human review for production deployment.',
        'Public English/de injection labels do not evaluate all DLP categories.',
        'Source license discrepancy requires review before redistribution.',
        'Semantic paraphrase overlap and residual personal data require review.',
    ]
    report = dict(version=5, splits={s: len(v) for s, v in splits.items()}, counts=counts,
                  languages={s: dict(Counter(r['language'] for r in v)) for s, v in splits.items()},
                  auxiliary_rows=len(auxiliary), legacy_rows_quarantined=len(legacy_quarantine()),
                  duplicate_or_conflict_rows=len(rejected), ready_for_training=not training_blockers,
                  ready_for_production_training=False,
                  blockers=training_blockers, class_balance_max_min_ratio=balance,
                  deployment_review_blockers=deployment_review_blockers,
                  model_input_columns=['text'], target_column='label',
                  no_automatic_translation=True)
    (OUT / 'quality_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
