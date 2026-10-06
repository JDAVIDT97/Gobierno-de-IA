"""Restore the losslessly compressed serving model shipped with the repository."""
import gzip
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path


class PartReader(io.RawIOBase):
    def __init__(self, parts):
        self.parts = iter(parts)
        self.current = None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.current is None:
                try:
                    self.current = next(self.parts).open('rb')
                except StopIteration:
                    return 0
            count = self.current.readinto(buffer)
            if count:
                return count
            self.current.close()
            self.current = None

    def close(self):
        if self.current is not None:
            self.current.close()
        super().close()


def restore_model(model_dir=None):
    model_dir = Path(model_dir or Path(__file__).resolve().parents[1] / 'models/dlp_slm')
    target = model_dir / 'model.onnx'
    manifest_path = model_dir / 'bundle/manifest.json'
    if not manifest_path.exists():
        return target
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if target.exists() and target.stat().st_size == manifest['size']:
        return target
    parts = []
    for item in manifest['parts']:
        part = manifest_path.parent / item['name']
        if not part.is_file() or hashlib.sha256(part.read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError(f'Model bundle missing or corrupt: {part}. Download the complete repository.')
        parts.append(part)
    print('Restoring Aegis ONNX model from repository bundle...', flush=True)
    fd, temporary = tempfile.mkstemp(prefix='model-', suffix='.tmp', dir=model_dir)
    try:
        digest = hashlib.sha256()
        size = 0
        with os.fdopen(fd, 'wb') as output, PartReader(parts) as raw:
            with io.BufferedReader(raw) as buffered, gzip.GzipFile(fileobj=buffered) as compressed:
                while block := compressed.read(1024 * 1024):
                    output.write(block)
                    digest.update(block)
                    size += len(block)
        if size != manifest['size'] or digest.hexdigest() != manifest['sha256']:
            raise RuntimeError('Restored ONNX model failed SHA-256 verification.')
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


if __name__ == '__main__':
    print(restore_model())
