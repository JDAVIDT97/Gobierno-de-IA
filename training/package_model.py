"""Losslessly gzip the active ONNX model into GitHub-compatible 40 MiB parts."""
import gzip
import hashlib
import json
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def main():
    model = BASE / 'models/dlp_slm/model.onnx'
    bundle = model.parent / 'bundle'
    bundle.mkdir(exist_ok=True)
    digest = hashlib.sha256()
    with tempfile.TemporaryFile() as packed:
        with gzip.GzipFile(fileobj=packed, mode='wb', compresslevel=6, mtime=0, filename='') as compressed:
            with model.open('rb') as source:
                while block := source.read(1024 * 1024):
                    digest.update(block)
                    compressed.write(block)
        packed.seek(0)
        parts = []
        while block := packed.read(40 * 1024 * 1024):
            name = f'model.onnx.gz.part{len(parts) + 1:03d}'
            (bundle / name).write_bytes(block)
            parts.append({'name': name, 'size': len(block), 'sha256': hashlib.sha256(block).hexdigest()})
        manifest = {'format': 'gzip-split-v1', 'file': model.name, 'size': model.stat().st_size,
                    'sha256': digest.hexdigest(), 'parts': parts}
        (bundle / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'original_bytes': manifest['size'], 'compressed_bytes': sum(p['size'] for p in parts), 'parts': len(parts)}))


if __name__ == '__main__':
    main()
