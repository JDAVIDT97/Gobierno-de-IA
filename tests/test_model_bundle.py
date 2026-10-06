import gzip
import hashlib
import json

import pytest

from api.model_bundle import restore_model


def make_bundle(directory):
    payload = b'ONNX test payload' * 1000
    compressed = gzip.compress(payload, mtime=0)
    bundle = directory / 'bundle'
    bundle.mkdir()
    parts = []
    for index, start in enumerate(range(0, len(compressed), 17)):
        block = compressed[start:start + 17]
        name = f'part{index:03d}'
        (bundle / name).write_bytes(block)
        parts.append({'name': name, 'sha256': hashlib.sha256(block).hexdigest()})
    (bundle / 'manifest.json').write_text(json.dumps({
        'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'parts': parts,
    }))
    return payload, bundle


def test_restores_split_gzip_and_reuses_model(tmp_path):
    payload, _ = make_bundle(tmp_path)
    target = restore_model(tmp_path)
    assert target.read_bytes() == payload
    assert restore_model(tmp_path) == target


def test_rejects_corrupt_part_without_creating_model(tmp_path):
    _, bundle = make_bundle(tmp_path)
    (bundle / 'part000').write_bytes(b'corrupt')
    with pytest.raises(RuntimeError, match='missing or corrupt'):
        restore_model(tmp_path)
    assert not (tmp_path / 'model.onnx').exists()
