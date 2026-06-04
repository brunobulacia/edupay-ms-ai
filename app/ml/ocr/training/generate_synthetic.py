import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BANKS = [
    "BANCO NACIONAL DE BOLIVIA",
    "BANCO MERCANTIL SANTA CRUZ",
    "BANCO FIE",
    "BANCO BISA",
    "BANCO ECONOMICO",
    "TIGO MONEY",
]
CONCEPTS = [
    "MENSUALIDAD OCTUBRE",
    "CUOTA ESCOLAR MENSUAL",
    "PAGO COLEGIATURA",
    "MENSUALIDAD NOVIEMBRE",
    "CUOTA MENSUAL",
]


def _draw_receipt(bank: str, amount: float, date: str, time: str, reference: str, concept: str) -> Image.Image:
    img = Image.new("RGB", (600, 820), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_med = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        font_large = ImageFont.load_default()
        font_med = font_large
        font_small = font_large

    # Header
    draw.rectangle([(0, 0), (600, 80)], fill="#003399")
    draw.text((30, 20), bank, fill="white", font=font_large)

    draw.text((30, 100), "COMPROBANTE DE PAGO", fill="black", font=font_med)
    draw.line([(30, 130), (570, 130)], fill="black", width=1)

    # Fields
    rows = [
        ("MONTO:", f"Bs. {amount:.2f}"),
        ("FECHA:", date),
        ("HORA:", time),
        ("REFERENCIA:", reference),
        ("CONCEPTO:", concept),
    ]
    y = 150
    for label, value in rows:
        draw.text((30, y), label, fill="#555555", font=font_small)
        draw.text((200, y), value, fill="black", font=font_med)
        draw.line([(30, y + 30), (570, y + 30)], fill="#eeeeee", width=1)
        y += 50

    draw.text((30, y + 20), "Transacción procesada exitosamente", fill="#008800", font=font_small)
    draw.rectangle([(0, 780), (600, 820)], fill="#003399")
    draw.text((30, 793), "www.edupay.bo", fill="white", font=font_small)

    return img


def generate_receipt(seed: int | None = None) -> tuple[Image.Image, dict]:
    if seed is not None:
        random.seed(seed)

    bank = random.choice(BANKS)
    amount = round(random.uniform(300, 2500), 2)
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(2024, 2025)
    date = f"{day:02d}/{month:02d}/{year}"
    time = f"{random.randint(8,18):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
    reference = str(random.randint(10**9, 10**10 - 1))
    concept = random.choice(CONCEPTS)

    img = _draw_receipt(bank, amount, date, time, reference, concept)
    meta = {
        "bank": bank,
        "amount": amount,
        "date": date,
        "time": time,
        "reference": reference,
        "concept": concept,
    }
    return img, meta


def generate_dataset(n: int = 300, out_dir: str = "app/ml/ocr/data/synthetic"):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    import json

    annotations = []
    for i in range(n):
        img, meta = generate_receipt(seed=i)
        img_path = f"{out_dir}/receipt_{i:04d}.jpg"
        img.save(img_path, "JPEG", quality=90)
        annotations.append({"image": f"receipt_{i:04d}.jpg", **meta})

    with open(f"{out_dir}/annotations.json", "w") as f:
        json.dump(annotations, f, indent=2, ensure_ascii=False)

    print(f"[OCR-DATA] Generated {n} synthetic receipts in {out_dir}")


if __name__ == "__main__":
    generate_dataset(300)
