"""Generate conspicuously fictional document images for live OCR rehearsals."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent


def font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def main():
    folder = ROOT / "data/demo"
    folder.mkdir(parents=True, exist_ok=True)
    fields = dict(name="Aarav Sharma", dob="1998-04-12", document_number="DEMO482901",
                  address="24 Lake Road, New Delhi 110001", document_type="Prototype ID", expiry_date="2032-12-31")
    base = dict(device_known=True, failed_attempts=0, previous_flags=0, duplicate_identity=False,
                document_anomaly=False, behavior_score=0)
    cases = {}
    for key in ("standard", "enhanced", "manual"):
        extracted, signals = dict(fields), dict(base)
        applicant = {k: fields[k] for k in ("name", "dob", "address")}
        if key == "enhanced":
            applicant["name"] = "Arjun Sharma"
            signals["device_known"] = False
            signals["failed_attempts"] = 1
        if key == "manual":
            applicant["dob"] = "1995-08-21"
            extracted["expiry_date"] = "2023-12-31"
            signals.update(device_known=False, failed_attempts=2)
        image = Image.new("RGB", (1400, 850), "#faf8f2")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1400, 130), fill="#193e37")
        draw.text((60, 37), "PRAMAAN / PROTOTYPE ID", font=font(44), fill="white")
        draw.text((60, 157), "FICTIONAL SAMPLE - NOT A VALID IDENTITY DOCUMENT", font=font(29), fill="#a1392a")
        for i, (label, field) in enumerate((("NAME", "name"), ("DATE OF BIRTH", "dob"), ("DOCUMENT NUMBER", "document_number"),
                                          ("ADDRESS", "address"), ("EXPIRY DATE", "expiry_date"))):
            y = 235 + i * 105
            draw.text((60, y), label, font=font(21), fill="#54605b")
            draw.text((60, y+31), extracted[field], font=font(36), fill="#152c26")
        draw.text((60, 785), "Synthetic hackathon sample | No government affiliation", font=font(25), fill="#63736b")
        image.save(folder / f"{key}.png")
        cases[key] = dict(applicant=applicant, fields=extracted, signals=signals, image=f"{key}.png")
    (folder / "cases.json").write_text(json.dumps(cases, indent=2))
    print("Created three fictional document samples and expected fields.")


if __name__ == "__main__":
    main()
