import json
from pathlib import Path
import pytest

from training.build_corpus_v5 import local_rows, map_public, reconcile, make_row
from training.validate_corpus import inspect_corpus
from training.deployment_gate import CLASSES
from data.adversarial_regressions_v6 import adversarial_rows


def test_binary_negative_is_not_dlp_safe():
    assert map_public('prompt_injection', 0) is None
    assert map_public('general_content_safety', 'safe') is None
    assert map_public('general_content_safety', 'unsafe') is None
    assert map_public('prompt_injection', 1) == 'Role_Evasion_Jailbreak'


def test_all_nine_classes_in_spanish_in_all_splits():
    rows = local_rows()
    for split in ('train', 'val', 'test'):
        assert {r['label_name'] for r in rows if r['split'] == split} == set(CLASSES)
    assert all(r['language'] == 'es' for r in rows)
    assert all('not_human' in r['label_quality'] for r in rows)


def test_conflicts_quarantined_not_arbitrarily_resolved():
    a = make_row('Texto 123', 'Safe_Use', 's', '1', 'train', 'reviewed')
    b = make_row('Texto 456', 'PII_Leak', 's', '2', 'test', 'reviewed')
    kept, rejected = reconcile([a, b])
    assert not kept
    assert len(rejected) == 2


def test_duplicate_cannot_pull_source_test_into_training():
    a = make_row('Texto 123', 'Safe_Use', 's', '1', 'train', 'reviewed')
    b = make_row('Texto 456', 'Safe_Use', 's', '2', 'test', 'reviewed')
    kept, rejected = reconcile([a, b])
    assert kept == [b]
    assert len(rejected) == 1


def test_generated_corpus_integrity_and_honest_readiness():
    report = inspect_corpus(Path('data/intent_curated_v5'))
    assert report['integrity_passed'], report['errors']
    assert report['ready_for_training']
    assert not report['ready_for_production_training']
    assert not report['coverage_gaps']


def test_legacy_keyword_mapping_disabled():
    from data.build_intent_dataset import map_external_intent, row, build
    with pytest.raises(RuntimeError):
        map_external_intent('I need legal advice', True)
    with pytest.raises(RuntimeError):
        row('Safe_Use', 1)
    with pytest.raises(RuntimeError):
        build(100)


def test_prompt_columns_do_not_contain_label_metadata():
    base = Path('data/intent_curated_v5')
    for split in ('train', 'val', 'test'):
        rows = [json.loads(line) for line in (base / f'{split}.jsonl').read_text().splitlines()]
        assert all(not any(category in r['text'] for category in CLASSES) for r in rows)
        assert all('audit_features' in r and 'source_revision' in r for r in rows)


def test_public_review_is_traceable_and_can_correct_source_label():
    base = Path('data/intent_curated_v5')
    rows = [json.loads(line) for line in (base / 'test.jsonl').read_text().splitlines()]
    row = next(r for r in rows if r['source_id'] == '3e234eb0b48e4b53aa85cd6ae20729e8')
    assert row['original_label'] == 'unsafe'
    assert row['label_name'] == 'Safe_Use'
    assert row['review_rationale'] and row['reviewed_text_sha256']
    assert row['label_quality'] == 'agent_reviewed_not_human_reviewed'


def test_adversarial_v6_covers_every_class_and_obfuscating_wrapper():
    rows = list(adversarial_rows())
    assert {row[0] for row in rows} == set(CLASSES)
    assert {row[3] for row in rows} == {
        'direct', 'fiction', 'academic', 'roleplay', 'authorized', 'hypothetical',
        'research', 'translation', 'indirect', 'urgent', 'quoted', 'uppercase',
    }
    assert len(rows) == 9 * 9 * 12


def test_adversarial_semantic_families_never_cross_splits():
    family_splits = {}
    for _category, split, family_id, _transform, _text in adversarial_rows():
        family_splits.setdefault(family_id, set()).add(split)
    assert all(len(splits) == 1 for splits in family_splits.values())


def test_reported_false_negative_families_are_in_adversarial_source():
    prompts = [row[4].casefold() for row in adversarial_rows() if row[3] == 'direct']
    assert any('suplantar la identidad' in prompt for prompt in prompts)
    assert any('planta de agua automatizada' in prompt for prompt in prompts)
    assert any('información de mis chats privados' in prompt for prompt in prompts)
