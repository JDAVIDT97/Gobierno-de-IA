"""Visible console monitor for a running Hugging Face/TensorBoard training job."""
from __future__ import annotations

import time
from pathlib import Path

from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

RUN = Path(__file__).resolve().parents[1] / "runs" / "intent_transformer_3epochs"
TOTAL_STEPS = 507

print("AEGIS DLP | MONITOR DE ENTRENAMIENTO TRANSFORMER", flush=True)
print("Actualización cada 5 segundos. Cierra esta ventana solo para detener el monitor.", flush=True)

while True:
    try:
        event_file = max(RUN.glob("events.out.tfevents.*"), key=lambda path: path.stat().st_mtime)
        events = EventAccumulator(str(event_file)); events.Reload()
        epochs = events.Scalars("train/epoch")
        losses = events.Scalars("train/loss")
        if epochs:
            step = epochs[-1].step
            epoch = epochs[-1].value
            loss = losses[-1].value if losses else float("nan")
            print(f"Paso {step:>3}/{TOTAL_STEPS} | avance {step / TOTAL_STEPS:>6.2%} | época {epoch:.3f}/3 | pérdida {loss:.4f}", flush=True)
        else:
            print("Preparando primer lote y métricas...", flush=True)
    except Exception as error:
        print(f"Esperando métricas: {error}", flush=True)
    time.sleep(5)
