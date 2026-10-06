"""Benchmark the local inference engine or a running /v1/audit endpoint."""
import argparse
import json
import statistics
import time
import uuid
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))


def prompts(limit):
    rows = [json.loads(x) for x in (BASE / "data/dataset_hybrid/test.jsonl").read_text(encoding="utf-8").splitlines() if x]
    values = [r["text"] for r in rows]
    return (values * (limit // len(values) + 1))[:limit]


def benchmark(samples=1000, endpoint=None, concurrency=1):
    values = prompts(samples)
    if endpoint:
        runner = lambda text: requests.post(endpoint, json={"user_id": str(uuid.uuid4()), "prompt": text,
            "destination": "https://chatgpt.com"}, timeout=10).raise_for_status()
        mode = "full_http_endpoint_with_inference_and_sqlite"
    else:
        from api.engine import DlpEngine
        engine = DlpEngine.get_instance()
        runner = lambda text: engine.evaluate(text)
        mode = f"local_engine_{engine.backend}"
    for text in values[:20]: runner(text)
    def timed(text):
        started = time.perf_counter(); runner(text); return (time.perf_counter() - started) * 1000
    wall_started = time.perf_counter()
    if endpoint and concurrency > 1:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            times = list(pool.map(timed, values))
    else:
        times = [timed(text) for text in values]
    wall_seconds = time.perf_counter() - wall_started
    result = {"mode": mode, "num_samples": samples, "mean_latency_ms": round(statistics.mean(times), 3),
              "p50_latency_ms": round(float(np.percentile(times, 50)), 3),
              "p95_latency_ms": round(float(np.percentile(times, 95)), 3),
              "p99_latency_ms": round(float(np.percentile(times, 99)), 3),
              "concurrency": concurrency, "throughput_req_per_sec": round(samples / wall_seconds, 1),
              "meets_latency_rnf": bool(np.percentile(times, 95) < 50),
              "meets_throughput_rnf": bool(samples / wall_seconds >= 100)}
    (BASE / "training/benchmark_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2)); return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--endpoint", help="Example: http://127.0.0.1:8000/v1/audit")
    parser.add_argument("--concurrency", type=int, default=1)
    args = parser.parse_args(); benchmark(args.samples, args.endpoint, args.concurrency)
