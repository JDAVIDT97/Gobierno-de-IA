from training.deployment_gate import CLASSES, release_failures


def fixture():
    evaluation = {'overall_metrics': {'f1_macro': .95},
                  'per_class_metrics': {c: {'recall': .95, 'support': 40} for c in CLASSES},
                  'confusion_matrix_counts': [[40] + [0] * 8] +
                                             [[0 if j == 0 else (40 if i == j else 0) for j in range(9)]
                                              for i in range(1, 9)]}
    cases = [dict(expected_block=b, passed=True, parity=True) for b in (True, False)]
    return evaluation, cases


def test_complete_candidate_passes_numeric_gate():
    assert not release_failures(*fixture())


def test_missing_class_support_blocks_release():
    evaluation, cases = fixture()
    evaluation['per_class_metrics']['PII_Leak']['support'] = 0
    assert release_failures(evaluation, cases)


def test_false_negative_blocks_release():
    evaluation, cases = fixture()
    cases[0]['passed'] = False
    assert release_failures(evaluation, cases)


def test_nan_metrics_and_empty_tests_block_release():
    evaluation, cases = fixture()
    evaluation['overall_metrics']['f1_macro'] = float('nan')
    assert release_failures(evaluation, cases)
    assert release_failures({}, [])


def test_unsafe_allowed_blocks_release_even_with_good_taxonomy_summary():
    evaluation, cases = fixture()
    evaluation['confusion_matrix_counts'][1][1] = 36
    evaluation['confusion_matrix_counts'][1][0] = 4
    assert any('BLOCK recall' in failure for failure in release_failures(evaluation, cases))


def test_block_to_block_taxonomy_confusion_is_not_a_leak():
    evaluation, cases = fixture()
    evaluation['per_class_metrics']['Data_Exfiltration']['recall'] = .875
    assert not release_failures(evaluation, cases)
