# -*- coding: utf-8 -*-
"""
Registra formalmente los 90 prompts del benchmark en la base de datos de auditoría
(audit_logs.db) a través del endpoint oficial /v1/audit de FastAPI.
Distribuye equitativamente los 90 casos entre las 10 IAs soportadas.
"""

import sys
import json
import uuid
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from api.main import app
from api.database import SessionLocal, AuditLog

DESTINATIONS = [
    {"name": "ChatGPT", "url": "https://chatgpt.com/"},
    {"name": "Claude", "url": "https://claude.ai/"},
    {"name": "Gemini", "url": "https://gemini.google.com/"},
    {"name": "Copilot", "url": "https://copilot.microsoft.com/"},
    {"name": "Perplexity", "url": "https://www.perplexity.ai/"},
    {"name": "DeepSeek", "url": "https://chat.deepseek.com/"},
    {"name": "Mistral", "url": "https://chat.mistral.ai/"},
    {"name": "Grok", "url": "https://grok.com/"},
    {"name": "Poe", "url": "https://poe.com/"},
    {"name": "You.com", "url": "https://you.com/"}
]

def main():
    benchmark_json = ROOT_DIR / "artifacts" / "benchmark_90_prompts.json"
    if not benchmark_json.exists():
        print("[!] No se encontró artifacts/benchmark_90_prompts.json")
        return

    with open(benchmark_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data["results"]
    print(f"[*] Cargados {len(results)} prompts del benchmark.")

    # Agrupar por categoría real (0 a 8)
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["ground_truth_idx"]].append(r)

    client = TestClient(app)
    
    # Obtener conteo previo de la DB
    db = SessionLocal()
    initial_count = db.query(AuditLog).count()
    db.close()
    print(f"[*] Registros previos en la bitácora SQLite: {initial_count}")

    print("\n[*] Enviando los 90 prompts a través del endpoint oficial /v1/audit...")
    successful_audits = 0
    by_provider_stats = defaultdict(lambda: {"total": 0, "BLOCK": 0, "ALLOW": 0})
    by_category_stats = defaultdict(lambda: {"total": 0, "BLOCK": 0, "ALLOW": 0})

    # Para cada categoría (0..8) y para cada índice (0..9) asignamos una IA
    for cat_idx in range(9):
        items = by_cat[cat_idx]
        for dest_idx, item in enumerate(items):
            dest = DESTINATIONS[dest_idx % len(DESTINATIONS)]
            user_session_id = str(uuid.uuid4())
            
            payload = {
                "user_id": user_session_id,
                "prompt": item["text"],
                "destination": dest["url"]
            }

            resp = client.post("/v1/audit", json=payload)
            if resp.status_code == 200:
                body = resp.json()
                action = body["action"]
                category = body["category"]
                successful_audits += 1

                by_provider_stats[dest["name"]]["total"] += 1
                by_provider_stats[dest["name"]][action] += 1

                by_category_stats[category]["total"] += 1
                by_category_stats[category][action] += 1
            else:
                print(f"[!] Error en {item['sample_code']}: {resp.status_code} - {resp.text}")

    # Verificar conteo final en DB
    db = SessionLocal()
    final_count = db.query(AuditLog).count()
    new_records = final_count - initial_count
    
    # Obtener los últimos 5 logs insertados como muestra
    recent_logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(5).all()
    db.close()

    print("\n" + "="*70)
    print("        INYECCIÓN EN BITÁCORA OFICIAL COMPLETADA EXITOSAMENTE")
    print("="*70)
    print(f"Auditorías ejecutadas vía API: {successful_audits} / {len(results)}")
    print(f"Nuevos registros persistidos en audit_logs.db: {new_records}")
    print(f"Total acumulado en bitácora SQLite: {final_count}")

    print("\n" + "-"*70)
    print("DISTRIBUCIÓN DE EVENTOS REGISTRADOS POR PROVEEDOR (10 IAs):")
    print("-" * 70)
    for p in DESTINATIONS:
        name = p["name"]
        st = by_provider_stats[name]
        print(f"  - {name:<12}: {st['total']} eventos auditados ({st['BLOCK']} Bloqueados, {st['ALLOW']} Permitidos)")

    print("\n" + "-"*70)
    print("MUESTRA DE ÚLTIMOS EVENTOS PERSISTIDOS EN SQLITE:")
    print("-" * 70)
    for l in reversed(recent_logs):
        print(f"  [ID {l.id}] {l.timestamp[:19]} | Destino: {l.destination:<26} | {l.action:<5} | Cat: {l.category:<22} | Latencia: {l.inference_time_ms} ms")
        print(f"       Hash SHA-256: {l.prompt_hash[:32]}... | Resumen: {l.prompt_redacted}")

if __name__ == "__main__":
    main()
