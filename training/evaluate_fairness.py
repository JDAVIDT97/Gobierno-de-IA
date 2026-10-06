"""Small fixed bilingual/code disparity suite; appends transparent subgroup metrics."""
import json
import sys
from pathlib import Path

from sklearn.metrics import f1_score

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from api.engine import DlpEngine, CLASS_NAMES
SUITES = {
    "language_spanish": [
        ("Explica de forma sencilla qué es una API", 0),
        ("DNI: 12345678 correo: persona@example.com", 1),
        ("Contraseña='secreto-corporativo-123'", 2),
        ("Planilla confidencial\nNombre,Salario,Margen,Cuenta\nAna,9000,25%,001", 3),
    ],
    "language_english": [
        ("Explain in simple terms what a public API is", 0),
        ("Passport: 123456789 email person@example.com", 1),
        ("api_key='sk-test-abcdefghijklmnopqrstuvwxyz1234'", 2),
        ("Confidential payroll\nName,Salary,Margin,Account\nAna,9000,25%,001", 3),
    ],
    "code_python": [
        ("Explain a public Python for loop", 0),
        ("DATABASE_URL='postgresql://admin:secret@internal:5432/prod'", 2),
    ],
    "code_java": [
        ("Explain a public Java for loop", 0),
        ("String password = \"internal-secret-123\"; // confidential Java service", 2),
    ],
}


def main():
    engine = DlpEngine.get_instance(); results = {}
    for name, rows in SUITES.items():
        truth = [label for _, label in rows]
        pred = [CLASS_NAMES.index(engine.evaluate(text)["category"]) for text, _ in rows]
        results[name] = {"samples": len(rows), "accuracy": sum(a == b for a, b in zip(truth, pred)) / len(rows),
                         "f1_macro": f1_score(truth, pred, average="macro", zero_division=0)}
    results["max_accuracy_gap"] = max(v["accuracy"] for v in results.values()) - min(v["accuracy"] for v in results.values())
    path = BASE / "training/evaluation_report.json"
    report = json.loads(path.read_text(encoding="utf-8")); report["subgroup_fairness_smoke_test"] = results
    report["fairness_limitations"] = "Small fixed smoke suite; production requires larger independently labeled groups."
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__": main()
