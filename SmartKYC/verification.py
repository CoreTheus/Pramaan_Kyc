import re
import unicodedata
from datetime import date, datetime


def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKC", str(value or "")).casefold() if c.isalnum())


def parse_date(value):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(str(value or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


def verify(applicant, fields, signals, today=None):
    today = today or date.today()
    checks = []

    def check(key, label, status, detail):
        checks.append(dict(key=key, label=label, status=status, detail=detail))

    matches = {}
    for key, label in (("name", "Name match"), ("dob", "Date of birth match"), ("address", "Address match")):
        a, b = applicant.get(key), fields.get(key)
        left, right = (parse_date(a), parse_date(b)) if key == "dob" else (normalize(a), normalize(b))
        valid_dob = key != "dob" or (right is not None and date(1900, 1, 1) <= right <= today)
        matches[key] = bool(left and right and left == right and valid_dob)
        status = "pass" if matches[key] else ("fail" if left and right else "unknown")
        check(key, label, status, "Matches applicant details" if matches[key] else
              "Applicant and document differ" if status == "fail" else "Missing or unreadable value")

    number = normalize(fields.get("document_number"))
    number_valid = bool(re.fullmatch(r"[a-z0-9]{6,20}", number))
    check("number", "Document number format", "pass" if number_valid else "fail",
          "Basic format only; not checked with an issuing authority" if number_valid else "Missing or outside basic 6–20 character format")
    doc_type = normalize(fields.get("document_type"))
    no_expiry = doc_type in ("aadhaar", "aadhar", "aadhaarcard", "pan", "pancard", "permanentaccountnumber")
    expiry = parse_date(fields.get("expiry_date"))
    expired = bool(expiry and expiry < today)
    expiry_valid = bool((expiry and expiry >= today) or (no_expiry and not fields.get("expiry_date")))
    check("expiry", "Document expiry", "pass" if expiry_valid else "fail" if expired else "unknown",
          "Expired on " + expiry.isoformat() if expired else "No expiry expected for this document type" if no_expiry and not expiry else
          "Valid through " + expiry.isoformat() if expiry_valid else "Expiry missing or unreadable; reviewer must check")
    check("type", "Document type", "pass" if doc_type else "unknown", fields.get("document_type") or "Type not extracted")

    required = ("name", "dob", "document_number", "address", "document_type")
    completeness = sum(bool(fields.get(k)) for k in required) / len(required)
    missing_core = any(not fields.get(k) for k in ("name", "dob", "document_number"))
    features = {
        "name_match": int(matches["name"]), "dob_match": int(matches["dob"]),
        "address_match": int(matches["address"]),
        "document_valid": int(number_valid and expiry_valid and bool(doc_type)),
        # Completeness is a transparent proxy, NOT measured OCR confidence.
        "ocr_confidence": completeness,
        "document_anomaly": int(signals.get("document_anomaly", False)),
        "device_known": int(signals.get("device_known", False)),
        "failed_attempts": int(signals.get("failed_attempts", 0)),
        "previous_flags": int(signals.get("previous_flags", 0)),
        "duplicate_identity": int(signals.get("duplicate_identity", False)),
        "behavior_score": float(signals.get("behavior_score", 0))
    }
    return {"checks": checks, "features": features, "completeness": completeness,
            "missing_core": missing_core, "expired": expired,
            "dob_conflict": bool(parse_date(applicant.get("dob")) and parse_date(fields.get("dob")) and not matches["dob"])}
