# -*- coding: utf-8 -*-
"""
Script de Evaluación de Muestra Balanceada (10 prompts x 9 categorías = 90 casos)
Extrae los casos del conjunto de prueba independiente test.jsonl con semilla fija,
los audita a través del DlpEngine y genera métricas multiclase, matriz de confusión,
seguridad binaria (FNR/FPR) y un banco de pruebas para las 10 IAs reales.
"""

import os
import sys
import json
import random
import time
from pathlib import Path
from collections import defaultdict
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

TEST_JSONL = ROOT_DIR / "data" / "intent_curated_v5" / "test.jsonl"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

CLASS_NAMES = [
    "Safe_Use",
    "PII_Leak",
    "Proprietary_Code",
    "Business_Secrets",
    "Code_Exploitation",
    "Data_Exfiltration",
    "Social_Engineering",
    "Role_Evasion_Jailbreak",
    "Legal_Misalignment"
]
CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}

def wilson_score_interval(successes, total, confidence=0.95):
    if total == 0:
        return 0.0, (0.0, 0.0)
    z = 1.96 if confidence == 0.95 else 1.645
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    spread = (z * np.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)) / denom
    lower = max(0.0, float(centre - spread))
    upper = min(1.0, float(centre + spread))
    return float(p), (lower, upper)

def load_stratified_sample(k_per_class=10, seed=42):
    random.seed(seed)
    by_class = defaultdict(list)
    with open(TEST_JSONL, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            data = json.loads(line)
            lbl = data["label"]
            by_class[lbl].append({"id": idx, "text": data["text"], "label": lbl})

    sample = []
    for lbl in range(9):
        pool = by_class[lbl]
        if len(pool) < k_per_class:
            raise ValueError(f"No hay suficientes ejemplos para la clase {lbl}: solo {len(pool)}")
        chosen = random.sample(pool, k_per_class)
        for i, item in enumerate(chosen):
            item["sample_code"] = f"CAT{lbl}_{i+1:02d}"
            item["class_name"] = CLASS_NAMES[lbl]
            sample.append(item)
    return sample

def main():
    print(f"[*] Cargando muestra balanceada: 10 prompts x 9 categorías = 90 prompts...")
    sample = load_stratified_sample(k_per_class=10, seed=42)

    # Inicializar DlpEngine
    print(f"[*] Inicializando DlpEngine...")
    from api.engine import DlpEngine
    engine = DlpEngine.get_instance()

    print(f"[*] Evaluando los 90 prompts a través del motor...")
    results = []
    confusion_matrix = [[0 for _ in range(9)] for _ in range(9)]
    
    start_all = time.perf_counter()
    for item in sample:
        gt_idx = item["label"]
        gt_name = CLASS_NAMES[gt_idx]
        text = item["text"]
        code = item["sample_code"]

        t0 = time.perf_counter()
        eval_res = engine.evaluate(text)
        t_elapsed = (time.perf_counter() - t0) * 1000

        pred_name = eval_res.get("category", "Safe_Use")
        pred_idx = CLASS_TO_IDX.get(pred_name, 0)
        action = eval_res.get("action", "ALLOW")
        
        # Ground truth esperado para seguridad binaria
        expected_action = "ALLOW" if gt_idx == 0 else "BLOCK"
        action_correct = (action == expected_action)
        multiclass_correct = (gt_idx == pred_idx)

        # Actualizar matriz de confusión
        confusion_matrix[gt_idx][pred_idx] += 1

        # Detección del mecanismo
        matched_rules = eval_res.get("matched_rules") or []
        mechanism = "SLM_Inference"
        if any("REGEX" in r for r in matched_rules):
            mechanism = "Regex_Pattern"
        elif any("INTENT" in r or "STRICT" in r or "HEURISTIC" in r for r in matched_rules):
            mechanism = "Heuristic_IntentGuard"

        results.append({
            "sample_code": code,
            "ground_truth_idx": gt_idx,
            "ground_truth_name": gt_name,
            "predicted_idx": pred_idx,
            "predicted_name": pred_name,
            "action": action,
            "expected_action": expected_action,
            "action_correct": action_correct,
            "multiclass_correct": multiclass_correct,
            "mechanism": mechanism,
            "risk_score": eval_res.get("risk_score", 0.0),
            "confidence": eval_res.get("confidence", 0.0),
            "inference_time_ms": round(t_elapsed, 2),
            "matched_rules": matched_rules,
            "reason": eval_res.get("reason"),
            "text": text
        })
    total_time = (time.perf_counter() - start_all) * 1000
    print(f"[+] Evaluación completada en {total_time:.2f} ms ({total_time/90:.2f} ms/prompt promedio).")

    # Estadísticas Globales
    total = len(results)
    multiclass_matches = sum(1 for r in results if r["multiclass_correct"])
    multiclass_acc = multiclass_matches / total

    # Seguridad Binaria
    # Clases 1..8 -> Riesgo
    risk_cases = [r for r in results if r["ground_truth_idx"] > 0]
    safe_cases = [r for r in results if r["ground_truth_idx"] == 0]

    # Verdaderos Positivos (Riesgo bloqueado correctamente)
    tp = sum(1 for r in risk_cases if r["action"] == "BLOCK")
    # Falsos Negativos (Riesgo que pasó como ALLOW -> FUGA)
    fn = sum(1 for r in risk_cases if r["action"] == "ALLOW")
    # Verdaderos Negativos (Safe permitido)
    tn = sum(1 for r in safe_cases if r["action"] == "ALLOW")
    # Falsos Positivos (Safe bloqueado erróneamente -> SOBRE-BLOQUEO)
    fp = sum(1 for r in safe_cases if r["action"] == "BLOCK")

    fnr_p, (fnr_low, fnr_high) = wilson_score_interval(fn, len(risk_cases))
    fpr_p, (fpr_low, fpr_high) = wilson_score_interval(fp, len(safe_cases))

    # Guardar JSON con detalle completo
    json_path = ARTIFACTS_DIR / "benchmark_90_prompts.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_prompts": total,
                "multiclass_accuracy": round(multiclass_acc, 4),
                "risk_prompts": len(risk_cases),
                "safe_prompts": len(safe_cases),
                "true_positives": tp,
                "false_negatives": fn,
                "true_negatives": tn,
                "false_positives": fp,
                "fnr": round(fnr_p, 4),
                "fnr_ci95": [round(fnr_low, 4), round(fnr_high, 4)],
                "fpr": round(fpr_p, 4),
                "fpr_ci95": [round(fpr_low, 4), round(fpr_high, 4)],
                "avg_latency_ms": round(total_time / 90, 2)
            },
            "confusion_matrix": confusion_matrix,
            "classes": CLASS_NAMES,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    # Imprimir Reporte en Consola
    print("\n" + "="*70)
    print("           RESULTADOS DEL BENCHMARK DE 90 PROMPTS (10 x CLASE)")
    print("="*70)
    print(f"Exactitud Multiclase Global: {multiclass_acc*100:.1f} % ({multiclass_matches}/{total})")
    print(f"Prompts de Riesgo Evaluados (Cat 1..8): {len(risk_cases)}")
    print(f"  - Bloqueados Correctamente (TP): {tp} ({tp/len(risk_cases)*100:.1f} %)")
    print(f"  - Fugas / Falsos Negativos (FN):  {fn} ({fnr_p*100:.1f} %) [IC 95%: {fnr_low*100:.1f}% - {fnr_high*100:.1f}%]")
    print(f"Prompts Seguros Evaluados (Cat 0 Safe_Use): {len(safe_cases)}")
    print(f"  - Permitidos Correctamente (TN): {tn} ({tn/len(safe_cases)*100:.1f} %)")
    print(f"  - Sobre-bloqueos / Falsos Pos (FP): {fp} ({fpr_p*100:.1f} %) [IC 95%: {fpr_low*100:.1f}% - {fpr_high*100:.1f}%]")
    print(f"Latencia promedio por solicitud: {total_time/90:.2f} ms")

    print("\n" + "-"*70)
    print("MATRIZ DE CONFUSIÓN (Filas: Real, Columnas: Predicción)")
    print("-" * 70)
    header = f"{'Clase Real':<22} | " + " ".join([f"C{i}" for i in range(9)]) + " | Recall"
    print(header)
    print("-" * len(header))
    for i in range(9):
        row = confusion_matrix[i]
        rec = row[i] / sum(row) if sum(row) > 0 else 0
        row_str = " ".join([f"{val:2d}" for val in row])
        print(f"C{i} {CLASS_NAMES[i]:<19} | {row_str} | {rec*100:5.1f}%")

    # Identificar Desvíos y Errores
    discrepancies = [r for r in results if not r["multiclass_correct"] or not r["action_correct"]]
    print(f"\nTotal discrepancias o desvíos: {len(discrepancies)}")
    if discrepancies:
        print("\nDesglose de discrepancias:")
        for d in discrepancies:
            status = "[FUGA_FN]" if (d["ground_truth_idx"] > 0 and d["action"] == "ALLOW") else (
                "[SOBREBLOQUEO_FP]" if (d["ground_truth_idx"] == 0 and d["action"] == "BLOCK") else "[DESVIO_CAT]"
            )
            print(f"  {status} {d['sample_code']}: Real={d['ground_truth_name']} -> Pred={d['predicted_name']} (Accion={d['action']})")
            safe_text = d['text'][:85].encode('ascii', 'replace').decode('ascii')
            print(f"    Texto: \"{safe_text}...\"")
            print(f"    Mecanismo: {d['mechanism']}, Reglas: {d['matched_rules']}")

    # Generar Guía de Pruebas HTML para las 10 IAs
    html_path = ARTIFACTS_DIR / "banco_pruebas_10_ias.html"
    generate_interactive_html(results, html_path)
    print(f"\n[+] Banco interactivo de pruebas generado en: {html_path}")

def generate_interactive_html(results, out_path):
    # Genera una página HTML para probar cómodamente en el navegador
    html = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Banco de Pruebas Aegis DLP (90 Prompts / 10 IAs)</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }
    h1 { color: #38bdf8; font-size: 24px; margin-bottom: 8px; }
    p.sub { color: #94a3b8; font-size: 14px; margin-bottom: 24px; }
    .providers-bar { background: #1e293b; padding: 12px 18px; border-radius: 8px; margin-bottom: 24px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; border: 1px solid #334155; }
    .badge-provider { background: #0284c7; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; text-decoration: none; font-weight: 500; }
    .badge-provider:hover { background: #38bdf8; color: #0f172a; }
    .filter-bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
    .filter-btn { background: #334155; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
    .filter-btn.active { background: #0284c7; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }
    th { background: #0f172a; color: #94a3b8; padding: 12px; text-align: left; font-size: 13px; border-bottom: 1px solid #334155; }
    td { padding: 10px 12px; border-bottom: 1px solid #334155; font-size: 13px; vertical-align: middle; }
    tr:hover { background: #243248; }
    .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .tag-allow { background: #10b98122; color: #34d399; border: 1px solid #10b981; }
    .tag-block { background: #ef444422; color: #f87171; border: 1px solid #ef4444; }
    .tag-cat { background: #6366f122; color: #a5b4fc; border: 1px solid #6366f1; }
    .copy-btn { background: #0284c7; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; }
    .copy-btn:hover { background: #38bdf8; color: #0f172a; }
    .prompt-text { font-family: monospace; font-size: 12px; color: #e2e8f0; max-width: 480px; word-break: break-word; }
  </style>
</head>
<body>
  <h1>🛡️ Aegis DLP — Banco de Pruebas de 90 Prompts</h1>
  <p class="sub">9 Categorías &times; 10 Casos. Haz clic en "Copiar Prompt" y pégalo en la IA deseada para verificar la intercepción de la extensión.</p>

  <div class="providers-bar">
    <strong style="font-size: 13px; color: #38bdf8;">IAs Soportadas:</strong>
    <a class="badge-provider" href="https://chatgpt.com" target="_blank">1. ChatGPT</a>
    <a class="badge-provider" href="https://claude.ai" target="_blank">2. Claude</a>
    <a class="badge-provider" href="https://gemini.google.com" target="_blank">3. Gemini</a>
    <a class="badge-provider" href="https://copilot.microsoft.com" target="_blank">4. Copilot</a>
    <a class="badge-provider" href="https://www.perplexity.ai" target="_blank">5. Perplexity</a>
    <a class="badge-provider" href="https://chat.deepseek.com" target="_blank">6. DeepSeek</a>
    <a class="badge-provider" href="https://chat.mistral.ai" target="_blank">7. Mistral</a>
    <a class="badge-provider" href="https://grok.com" target="_blank">8. Grok</a>
    <a class="badge-provider" href="https://poe.com" target="_blank">9. Poe</a>
    <a class="badge-provider" href="https://you.com" target="_blank">10. You.com</a>
    <a class="badge-provider" style="background: #10b981;" href="http://localhost:8000/sandbox" target="_blank">⚡ Sandbox Local</a>
  </div>

  <table>
    <thead>
      <tr>
        <th>Código</th>
        <th>Categoría Real</th>
        <th>Decisión Aegis</th>
        <th>Cat. Predicha</th>
        <th>Mecanismo</th>
        <th>Prompt</th>
        <th>Acción</th>
      </tr>
    </thead>
    <tbody>
"""
    for r in results:
        act_class = "tag-allow" if r["action"] == "ALLOW" else "tag-block"
        html += f"""      <tr>
        <td><strong>{r['sample_code']}</strong></td>
        <td><span class="tag tag-cat">{r['ground_truth_name']}</span></td>
        <td><span class="tag {act_class}">{r['action']}</span></td>
        <td>{r['predicted_name']}</td>
        <td style="font-size: 11px; color: #94a3b8;">{r['mechanism']}</td>
        <td class="prompt-text">{r['text']}</td>
        <td>
          <button class="copy-btn" onclick="navigator.clipboard.writeText(`{r['text'].replace('`', "'")}`).then(() => alert('¡Prompt {r['sample_code']} copiado al portapapeles! Pégalo en tu IA.'))">Copiar</button>
        </td>
      </tr>
"""
    html += """    </tbody>
  </table>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")

if __name__ == "__main__":
    main()
