import json
from pathlib import Path
import pytest


def test_clean_dataset_has_no_label_suffix_or_family_overlap():
    base = Path('data/intent_clean_v4')
    if not base.exists():
        pytest.skip('Legacy v4 corpus excluded from the distribution; current corpus is tested in test_corpus_v5.py')
    groups = {}
    for split in ('train', 'val', 'test'):
        rows = [json.loads(line) for line in (base / f'{split}.jsonl').read_text(encoding='utf8').split('\n') if line]
        assert rows
        assert all('Caso sintético de entrenamiento' not in row['text'] for row in rows)
        groups[split] = {row['group_id'] for row in rows}
    assert not groups['train'] & groups['val']
    assert not groups['train'] & groups['test']
    assert not groups['val'] & groups['test']
