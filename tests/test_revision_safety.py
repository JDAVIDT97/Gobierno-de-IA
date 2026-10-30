"""Failure injection without contacting a real provider or using original logs."""
import numpy as np
import pytest
from fastapi.testclient import TestClient
from api.engine import DlpEngine
from api.main import app

@pytest.fixture
def engine():
    e=object.__new__(DlpEngine);e.model=None;e.backend='test';e.version='test';return e

def test_absent_model_cannot_authorize(engine):
    with pytest.raises(RuntimeError):engine.evaluate('Una entrada neutral sin reglas particulares')

def test_corrupt_onnx_at_startup_cannot_authorize(tmp_path,monkeypatch):
    import shutil
    from pathlib import Path
    import api.engine as module
    import api.model_bundle as bundle
    original=Path(module.__file__).resolve().parents[1]/'models/dlp_slm'
    for name in ['tokenizer.json','tokenizer_config.json','spm.model','special_tokens_map.json','added_tokens.json','config.json','aegis_config.json']:
        if (original/name).exists():shutil.copy2(original/name,tmp_path/name)
    (tmp_path/'model.onnx').write_bytes(b'corrupt synthetic model')
    monkeypatch.setattr(module,'MODEL_DIR',tmp_path)
    monkeypatch.setattr(module,'MODEL_PATH',tmp_path/'absent.joblib')
    monkeypatch.setattr(bundle,'restore_model',lambda path:None)
    candidate=DlpEngine()
    assert candidate.model is None
    with pytest.raises(RuntimeError):candidate.evaluate('Una entrada neutral sin reglas particulares')

@pytest.mark.parametrize('mode',['error','nan','bad_shape'])
def test_failed_inference_cannot_authorize(engine,mode):
    engine.model=object()
    def predict(text):
        if mode=='error':raise ValueError('injected')
        return np.array([float('nan')]*9 if mode=='nan' else [1.0,0.0])
    engine._predict_proba=predict
    with pytest.raises(RuntimeError):engine.evaluate('Una entrada neutral sin reglas particulares')

def test_api_maps_inference_failure_to_503(engine,monkeypatch):
    monkeypatch.setattr(DlpEngine,'get_instance',classmethod(lambda cls:engine))
    response=TestClient(app).post('/v1/audit',json={'user_id':'a3f9632a-978d-4c3c-9f69-33e6d38cd375','prompt':'Una entrada neutral sin reglas particulares','destination':'https://chatgpt.com'})
    assert response.status_code==503

def test_sqlite_failure_retains_send(engine,monkeypatch):
    from api.database import get_db
    class FailingSession:
        def add(self,row):pass
        def commit(self):raise OSError('injected database failure')
        def rollback(self):pass
    monkeypatch.setattr(DlpEngine,'get_instance',classmethod(lambda cls:engine))
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db]=lambda:FailingSession()
    try:
        response=TestClient(app).post('/v1/audit',json={'user_id':'a3f9632a-978d-4c3c-9f69-33e6d38cd375','prompt':"password = 'ClaveSinteticaAEGIS2026'",'destination':'https://chatgpt.com'})
        assert response.status_code==503
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)

def test_token_windows_cover_end_of_long_text(engine):
    # The production tokenizer is not mocked: check complete token-stream
    # coverage, overlap and encoder cap independently of predicted labels.
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained('models/dlp_slm',local_files_only=True)
    text=('Texto público con letras ñ y datos de ejemplo. '*400)+' final reservado'
    ids=tokenizer(text,add_special_tokens=False)['input_ids']
    windows=tokenizer(text,truncation=True,max_length=256,stride=32,return_overflowing_tokens=True)['input_ids']
    recovered=[]
    for i,window in enumerate(windows):
        assert len(window)<=256
        recovered.extend(window[1:-1] if i==0 else window[33:-1])
    assert recovered==ids
