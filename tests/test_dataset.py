import json
from collections import Counter
from pathlib import Path
import pytest


def read(name):
    return [json.loads(x) for x in Path("data/dataset_hybrid", name).read_text(encoding="utf-8").splitlines() if x]


def test_balanced_stratified_and_no_overlap():
    if not Path('data/dataset_hybrid').exists():
        pytest.skip('Legacy hybrid corpus excluded from the distribution; current corpus is tested in test_corpus_v5.py')
    splits = {name: read(f"{name}.jsonl") for name in ("train", "val", "test")}
    labels = sorted({row["label"] for rows in splits.values() for row in rows})
    assert len(labels) >= 4
    assert all(Counter(r["label"] for r in rows) == Counter({label: len(rows)//len(labels) for label in labels})
               for rows in splits.values())
    assert all("intent_family" in row and "policy_methods" in row for rows in splits.values() for row in rows)
    texts = {name: {r["text"] for r in rows} for name, rows in splits.items()}
    assert not texts["train"] & texts["val"]
    assert not texts["train"] & texts["test"]
    assert not texts["val"] & texts["test"]
    assert Path("data/dataset_hf/dataset_dict.json").exists()
