"""Logistic regression inference without a runtime scikit-learn dependency."""
import json
import math
from settings import ROOT

FEATURES = ["name_match", "dob_match", "address_match", "document_valid", "ocr_confidence",
            "document_anomaly", "device_known", "failed_attempts", "previous_flags", "duplicate_identity", "behavior_score"]
LABELS = ["Name missing or different", "Birth date missing or different", "Address missing or different",
          "Document format / expiry concern", "Incomplete extracted fields", "Document anomaly (supplied)",
          "Unknown device (supplied)", "Previous failed attempts (supplied)", "Previous flags (supplied)",
          "Duplicate identity signal", "Unusual behavior (supplied)"]


def vector(features):
    values = [float(features[k]) for k in FEATURES]
    for i in (0, 1, 2, 3, 4, 6):
        values[i] = 1 - values[i]
    values[7] = min(values[7], 5) / 5
    values[8] = min(values[8], 3) / 3
    values[10] /= 100
    return values


def sigmoid(value):
    return 1 / (1 + math.exp(-max(-40, min(40, value))))


def predict(features, config, verification):
    model = json.loads((ROOT / "ml" / "model.json").read_text())
    terms = [a * b for a, b in zip(vector(features), model["coefficients"])]
    logit = model["intercept"] + sum(terms)
    probability = sigmoid(logit)
    score = round(100 * probability)
    factors = [dict(feature=FEATURES[i], label=LABELS[i], contribution=round(term, 4),
                    points_if_resolved=round(100 * (probability - sigmoid(logit - term)), 1))
               for i, term in enumerate(terms) if abs(term) > .005]
    factors.sort(key=lambda f: f["contribution"], reverse=True)
    level = "LOW" if score <= config["standard_max"] else "MEDIUM" if score <= config["enhanced_max"] else "HIGH"
    route = {"LOW": "Standard", "MEDIUM": "Enhanced", "HIGH": "Manual"}[level]
    overrides = []
    if verification["dob_conflict"]:
        overrides.append("Date of birth conflict requires a reviewer.")
        route = "Manual"
    elif route == "Standard" and any(c["status"] != "pass" for c in verification["checks"]):
        overrides.append("Incomplete baseline checks require additional evidence.")
        route = "Enhanced"
    actions = []
    if not features["name_match"] or not features["dob_match"]:
        actions.append("Compare original ID and applicant details; resolve the identity discrepancy.")
    if not features["address_match"]:
        actions.append("Request a supporting address document.")
    if not features["document_valid"]:
        actions.append("Request a clear, current document and confirm its number and expiry.")
    if not features["device_known"] or features["failed_attempts"] or features["previous_flags"] or features["duplicate_identity"]:
        actions.append("Review the supplied device and application-history signals.")
    if route == "Standard":
        actions = ["Baseline checks passed. Reviewer may complete standard verification."]
    return dict(score=score, level=level, route=route, factors=factors, overrides=overrides,
                next_steps=actions, baseline_score=round(100 * sigmoid(model["intercept"]), 1),
                intercept=model["intercept"], logit=logit,
                explanation="Coefficients × adverse feature values add in log-odds. Point reductions are one-factor counterfactuals and do not add together.")
