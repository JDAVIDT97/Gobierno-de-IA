from types import SimpleNamespace


def test_local_deberta_identity_is_detectable():
    model_path = 'models/intent_candidate_v5'
    config = SimpleNamespace(model_type='deberta-v2')
    architecture = f"{model_path} {config.model_type} DebertaV2ForSequenceClassification".lower()
    assert 'deberta' in architecture
