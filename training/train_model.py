"""Fine-tune and evaluate the Aegis intent-safety SLM.

Default: microsoft/deberta-v3-small + LoRA. A classical backend is retained only
as an explicit low-resource fallback; production metadata always records which
backend produced the artifact.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
from sklearn.metrics import (accuracy_score, confusion_matrix,
                             precision_recall_fscore_support, roc_auc_score)

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "dataset_hybrid"
OUT = BASE / "models" / "dlp_slm"
REPORT = BASE / "training" / "evaluation_report.json"
def dataset_classes():
    rows = [json.loads(line) for line in (DATA / "train.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    return [next(row["label_name"] for row in rows if row["label"] == label) for label in range(max(row["label"] for row in rows) + 1)]

CLASSES = []


def load_jsonl(name: str):
    rows = [json.loads(line) for line in (DATA / name).read_text(encoding="utf-8").splitlines() if line.strip()]
    return [row["text"] for row in rows], np.asarray([row["label"] for row in rows]), rows


def metrics_report(y_true, y_pred, y_score, texts, architecture, train_seconds):
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=range(len(CLASSES)), zero_division=0)
    pma, rma, fma, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    pwt, rwt, fwt, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    try:
        auc = float(roc_auc_score(y_true, y_score, multi_class="ovr", average="weighted"))
    except ValueError:
        auc = None
    cases = []
    for idx, (truth, pred, scores, text) in enumerate(zip(y_true, y_pred, y_score, texts)):
        if truth != pred:
            cases.append({"sample_index": idx, "true_class": CLASSES[int(truth)],
                          "pred_class": CLASSES[int(pred)], "confidence": float(max(scores)),
                          "prompt_snippet": text[:300]})
    if len(cases) < 20:
        margins = np.sort(y_score, axis=1)[:, -1] - np.sort(y_score, axis=1)[:, -2]
        for idx in np.argsort(margins):
            if any(c["sample_index"] == int(idx) for c in cases):
                continue
            cases.append({"sample_index": int(idx), "true_class": CLASSES[int(y_true[idx])],
                          "pred_class": CLASSES[int(y_pred[idx])], "confidence_margin": float(margins[idx]),
                          "prompt_snippet": texts[idx][:300]})
            if len(cases) == 20:
                break
    safe_total = int(np.sum(y_true == 0))
    unsafe_total = int(np.sum(y_true != 0))
    safe_allowed = int(np.sum((y_true == 0) & (y_pred == 0)))
    unsafe_blocked = int(np.sum((y_true != 0) & (y_pred != 0)))
    return {
        "model_version": "dlp-slm-v2.0", "architecture": architecture,
        "train_time_sec": round(train_seconds, 3),
        "overall_metrics": {"accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "f1_weighted": round(float(fwt), 4), "f1_macro": round(float(fma), 4),
            "precision_weighted": round(float(pwt), 4), "recall_weighted": round(float(rwt), 4),
            "roc_auc_ovr": None if auc is None else round(auc, 4)},
        "policy_decision_metrics": {
            "safe_allow_recall": round(safe_allowed / safe_total, 4),
            "block_recall": round(unsafe_blocked / unsafe_total, 4),
            "unsafe_requests_allowed": int(np.sum((y_true != 0) & (y_pred == 0))),
            "safe_requests_blocked": int(np.sum((y_true == 0) & (y_pred != 0))),
        },
        "per_class_metrics": {CLASSES[i]: {"precision": round(float(precision[i]), 4),
            "recall": round(float(recall[i]), 4), "f1_score": round(float(f1[i]), 4),
            "support": int(support[i])} for i in range(len(CLASSES))},
        "confusion_matrix_normalized": confusion_matrix(y_true, y_pred, labels=range(len(CLASSES)), normalize="true").tolist(),
        "confusion_matrix_counts": confusion_matrix(y_true, y_pred, labels=range(len(CLASSES))).tolist(),
        "error_analysis_top_cases": cases[:20],
    }


def export_onnx(model, tokenizer, max_length: int, quantize_int8: bool = False):
    import torch
    model.eval().cpu()
    encoded = tokenizer("Aegis DLP ONNX export", return_tensors="pt", truncation=True,
                        padding="max_length", max_length=max_length)
    inputs = (encoded["input_ids"], encoded["attention_mask"])
    torch.onnx.export(model, inputs, str(OUT / "model.onnx"), input_names=["input_ids", "attention_mask"],
                      output_names=["logits"], dynamic_axes={"input_ids": {0: "batch", 1: "sequence"},
                      "attention_mask": {0: "batch", 1: "sequence"}, "logits": {0: "batch"}},
                      opset_version=17, do_constant_folding=True)
    int8_path = OUT / 'model.int8.onnx'
    if int8_path.exists() and not quantize_int8:
        int8_path.unlink()
    if not quantize_int8:
        print('[+] ONNX FP32 exported; INT8 disabled because release requires explicit parity validation.')
        return
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
        try:
            quantize_dynamic(str(OUT / "model.onnx"), str(OUT / "model.int8.onnx"), weight_type=QuantType.QInt8)
        except PermissionError:
            # ONNX Runtime on Windows can retain its inferred intermediate briefly.
            quantize_dynamic(str(OUT / "model-inferred.onnx"), str(OUT / "model.int8.onnx"), weight_type=QuantType.QInt8)
    except Exception as exc:
        print(f"[!] ONNX INT8 quantization unavailable: {exc}")


def train_transformer(args):
    import torch
    from datasets import Dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              DataCollatorWithPadding, EarlyStoppingCallback, Trainer, TrainingArguments)

    from transformers import set_seed
    set_seed(42)  # Before tokenizer, classifier head and LoRA initialization.
    train_x, train_y, _ = load_jsonl("train.jsonl")
    val_x, val_y, _ = load_jsonl("val.jsonl")
    test_x, test_y, _ = load_jsonl("test.jsonl")
    if args.max_train_samples and args.max_train_samples < len(train_x):
        rng = np.random.default_rng(42)
        per_class = args.max_train_samples // len(CLASSES)
        selected = np.concatenate([rng.choice(np.flatnonzero(train_y == label), per_class, replace=False)
                                   for label in range(len(CLASSES))])
        rng.shuffle(selected)
        train_x = [train_x[int(i)] for i in selected]
        train_y = train_y[selected]
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.model_revision)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model, revision=args.model_revision, num_labels=len(CLASSES), id2label={i: c for i, c in enumerate(CLASSES)},
        label2id={c: i for i, c in enumerate(CLASSES)})
    if args.lora:
        architecture = f"{args.model} {getattr(model.config, 'model_type', '')} {model.__class__.__name__}".lower()
        targets = ["query_proj", "key_proj", "value_proj"] if "deberta" in architecture else ["query", "key", "value"]
        model = get_peft_model(model, LoraConfig(task_type=TaskType.SEQ_CLS, r=8, lora_alpha=16,
                              lora_dropout=.1, target_modules=targets, modules_to_save=["classifier", "pooler"]))

    def make_ds(texts, labels):
        ds = Dataset.from_dict({"text": texts, "labels": labels.tolist()})
        return ds.map(lambda batch: tokenizer(batch["text"], truncation=True, max_length=args.max_length), batched=True,
                      remove_columns=["text"])

    train_ds, val_ds, test_ds = make_ds(train_x, train_y), make_ds(val_x, val_y), make_ds(test_x, test_y)

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        pred = np.argmax(logits, axis=-1)
        return {"accuracy": accuracy_score(labels, pred),
                "f1_weighted": precision_recall_fscore_support(labels, pred, average="weighted", zero_division=0)[2]}

    train_args = TrainingArguments(output_dir=str(OUT / "checkpoints"), learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size, per_device_eval_batch_size=max(args.batch_size, 16),
        num_train_epochs=args.epochs, weight_decay=.01, warmup_ratio=.1, eval_strategy="epoch",
        save_strategy="epoch", logging_dir=str(BASE / "runs" / args.run_name), logging_steps=10, load_best_model_at_end=True,
        metric_for_best_model="f1_weighted", greater_is_better=True, save_total_limit=2,
        fp16=torch.cuda.is_available(), report_to=["tensorboard"], seed=42, data_seed=42)
    trainer = Trainer(model=model, args=train_args, train_dataset=train_ds, eval_dataset=val_ds,
                      processing_class=tokenizer, data_collator=DataCollatorWithPadding(tokenizer),
                      compute_metrics=compute_metrics, callbacks=[EarlyStoppingCallback(early_stopping_patience=2)])
    run_config = {"arguments": {k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()},
                  "resolved_base_revision": getattr(model.config, "_commit_hash", None),
                  "training_arguments": train_args.to_dict(), "classes": CLASSES,
                  "seed_before_model_initialization": 42}
    (OUT / "run_config.json").write_text(json.dumps(run_config, indent=2, default=str), encoding="utf8")
    started = time.perf_counter(); trainer.train(); duration = time.perf_counter() - started
    trainer.save_state()
    prediction = trainer.predict(test_ds)
    logits = prediction.predictions
    scores = torch.softmax(torch.tensor(logits), dim=-1).numpy()
    pred = np.argmax(scores, axis=1)
    final_model = trainer.model.merge_and_unload() if args.lora else trainer.model
    OUT.mkdir(parents=True, exist_ok=True)
    final_model.save_pretrained(OUT, safe_serialization=False)
    tokenizer.save_pretrained(OUT)
    export_onnx(final_model, tokenizer, args.max_length, args.quantize_int8)
    return metrics_report(test_y, pred, scores, test_x,
                          f"{args.model} sequence classifier{' + LoRA' if args.lora else ''}", duration)


def train_classical():
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    train_x, train_y, _ = load_jsonl("train.jsonl")
    test_x, test_y, _ = load_jsonl("test.jsonl")
    model = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 3), max_features=50000, sublinear_tf=True,
                                                 strip_accents="unicode")),
                      ("clf", LogisticRegression(C=8, max_iter=1500, class_weight="balanced", random_state=42))])
    started = time.perf_counter(); model.fit(train_x, train_y); duration = time.perf_counter() - started
    OUT.mkdir(parents=True, exist_ok=True); joblib.dump(model, OUT / "model.joblib")
    scores = model.predict_proba(test_x); pred = np.argmax(scores, axis=1)
    return metrics_report(test_y, pred, scores, test_x, "TF-IDF + LogisticRegression fallback", duration)


def main():
    global DATA, OUT, REPORT, CLASSES
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["transformer", "classical"], default="transformer")
    parser.add_argument("--data-dir", type=Path, default=BASE / 'data/intent_curated_v5')
    parser.add_argument("--output-dir", type=Path, default=BASE / 'models/intent_candidate_v5')
    parser.add_argument('--experimental-data', action='store_true',
                        help='Allow insufficient coverage for experiments; does not approve deployment')
    parser.add_argument('--quantize-int8', action='store_true',
                        help='Also export INT8; it must independently pass parity before serving')
    parser.add_argument("--model", default="microsoft/deberta-v3-small")
    parser.add_argument("--model-revision", help="Pinned model base revision or commit")
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4,
                        help="LoRA default; use 2e-5 with --no-lora full fine-tuning")
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--max-train-samples", type=int, default=4000,
                        help="Balanced training cap for CPU; use 0 for the full 16k split")
    parser.add_argument("--run-name", default="intent_transformer_3epochs",
                        help="TensorBoard subdirectory for this training run")
    parser.add_argument("--version", default="5.0", help="Candidate policy/model version")
    parser.add_argument("--no-lora", dest="lora", action="store_false")
    parser.set_defaults(lora=True)
    args = parser.parse_args()
    DATA = args.data_dir.resolve()
    OUT = args.output_dir.resolve()
    from validate_corpus import inspect_corpus
    preflight = inspect_corpus(DATA)
    if not preflight['integrity_passed'] or (not args.experimental_data and not preflight['ready_for_training']):
        parser.error('Corpus preflight failed: ' + json.dumps(preflight, ensure_ascii=True))
    if OUT == (BASE / 'models/dlp_slm').resolve():
        parser.error('Train into a candidate directory, never overwrite the serving model.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'corpus_preflight.json').write_text(json.dumps(preflight, indent=2), encoding='utf8')
    REPORT = OUT / "evaluation_report.json"
    CLASSES = dataset_classes()
    report = train_transformer(args) if args.backend == "transformer" else train_classical()
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    config = {"model_type": "aegis-dlp", "backend": args.backend, "version": args.version, "classes": CLASSES,
              "decision_rule": "argmax", "max_seq_length": args.max_length if args.backend == "transformer" else 4096}
    # Preserve the Hugging Face configuration needed to reload PyTorch weights.
    if args.backend == "classical":
        (OUT / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (OUT / "aegis_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(json.dumps(report["overall_metrics"], indent=2))


if __name__ == "__main__":
    main()
