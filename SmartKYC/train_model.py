"""Reproducible synthetic demonstration; not a real fraud benchmark."""
import csv
import json
import math
import random
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.model_selection import train_test_split
from risk import FEATURES, vector

ROOT = Path(__file__).parent


def train():
    rng = random.Random(42)
    rows, x, y = [], [], []
    true_weights = [2.7, 3.2, 1.3, 2.6, 1.7, 2.0, 1.15, 2.4, 2.1, 2.8, 2.0]
    for i in range(5000):
        f = dict(name_match=int(rng.random() > .16), dob_match=int(rng.random() > .1),
                 address_match=int(rng.random() > .2), document_valid=int(rng.random() > .15),
                 ocr_confidence=round(rng.uniform(.5, 1), 2), document_anomaly=int(rng.random() < .1),
                 device_known=int(rng.random() > .3), failed_attempts=rng.choices([0, 1, 2, 3, 5], [65, 15, 10, 7, 3])[0],
                 previous_flags=rng.choices([0, 1, 2, 3], [85, 9, 4, 2])[0],
                 duplicate_identity=int(rng.random() < .08), behavior_score=rng.choices([0, 20, 50, 80, 100], [65, 15, 10, 7, 3])[0])
        values = vector(f)
        z = -4.5 + sum(a*b for a, b in zip(values, true_weights))
        target = int(rng.random() < 1 / (1 + math.exp(-z)))
        rows.append({"customer_id": f"SYN-{i:05}", **f, "synthetic_risk_label": target})
        x.append(values)
        y.append(target)
    a, b, c, d = train_test_split(x, y, test_size=.2, random_state=42, stratify=y)
    model = LogisticRegression(C=10, max_iter=1000, random_state=42).fit(a, c)
    report = {"training_rows": len(a), "held_out_rows": len(b), "seed": 42,
              "synthetic_only": True, "auc": round(roc_auc_score(d, model.predict_proba(b)[:, 1]), 4),
              "accuracy_at_0_5": round(accuracy_score(d, model.predict(b)), 4),
              "limitation": "Synthetic labels are sampled from a hand-designed logistic formula. Metrics measure recovery of that formula, not real-world fraud detection.",
              "ocr_confidence": "Field-completeness proxy, not calibrated OCR confidence.",
              "split": "80/20 stratified split; independent generated records, no repeated customer identities."}
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "ml").mkdir(exist_ok=True)
    with (ROOT / "data/synthetic_dataset.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (ROOT / "ml/model.json").write_text(json.dumps({"kind": "LogisticRegression", "features": FEATURES,
        "coefficients": model.coef_[0].tolist(), "intercept": float(model.intercept_[0]), "report": report}, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    train()
