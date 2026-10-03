import json
import math
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from settings import ROOT, load_config
from verification import verify, normalize
from risk import predict, sigmoid
from ocr import extract, prepare_image, OCRError


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.demos = json.loads((ROOT / "data/demo/cases.json").read_text())
        self.config = load_config()

    def score(self, case):
        checks = verify(case["applicant"], case["fields"], case["signals"], date(2026, 10, 3))
        return predict(checks["features"], self.config, checks)

    def test_three_routes(self):
        for key, expected in (("standard", "Standard"), ("enhanced", "Enhanced"), ("manual", "Manual")):
            result = self.score(self.demos[key])
            self.assertEqual(expected, result["route"])

    def test_explanation_reconstructs_score(self):
        risk = self.score(self.demos["enhanced"])
        reconstructed = 100 * sigmoid(risk["intercept"] + sum(f["contribution"] for f in risk["factors"]))
        self.assertAlmostEqual(reconstructed, 100*sigmoid(risk["logit"]), places=2)

    def test_missing_fields_never_standard(self):
        case = self.demos["standard"]
        case["fields"]["dob"] = None
        self.assertNotEqual(self.score(case)["route"], "Standard")

    def test_date_formats_and_normalization(self):
        case = self.demos["standard"]
        case["fields"]["dob"] = "12/04/1998"
        case["applicant"]["name"] = "  AARAV   SHARMA "
        self.assertEqual(self.score(case)["route"], "Standard")

    def test_expired_date_and_future_dob(self):
        case = self.demos["standard"]
        case["fields"]["expiry_date"] = "2020-01-01"
        self.assertNotEqual(self.score(case)["route"], "Standard")
        case["fields"]["dob"] = case["applicant"]["dob"] = "2040-01-01"
        self.assertNotEqual(self.score(case)["route"], "Standard")

    def test_bad_image(self):
        with self.assertRaises(OCRError):
            prepare_image(b"not an image")

    @patch("ocr.health", return_value={"ready": False, "message": "Ollama is not reachable"})
    def test_ollama_offline(self, mock):
        with self.assertRaisesRegex(OCRError, "not reachable"):
            extract(b"test", self.config)

    @patch("ocr.health", return_value={"ready": True})
    @patch("ocr.request_json", return_value={"message": {"content": "not JSON"}})
    def test_bad_model_json(self, mock, mock_health):
        with self.assertRaisesRegex(OCRError, "unreadable fields"):
            extract(b"test", self.config)

    @patch("ocr.health", return_value={"ready": True})
    @patch("ocr.request_json", return_value={"message": {"content": "{}"}})
    def test_no_identity_extracted(self, mock, mock_health):
        with self.assertRaisesRegex(OCRError, "No identity"):
            extract(b"test", self.config)


if __name__ == "__main__":
    unittest.main()
