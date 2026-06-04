import re

BANK_KEYWORDS = [
    "BANCO NACIONAL DE BOLIVIA",
    "BANCO MERCANTIL SANTA CRUZ",
    "BANCO FIE",
    "BANCO BISA",
    "BANCO ECONOMICO",
    "TIGO MONEY",
]


def extract_fields(raw_text: str) -> dict:
    text = raw_text.upper()

    bank = _extract_bank(text)
    amount = _extract_amount(text)
    date = _extract_date(text)
    time_ = _extract_time(text)
    reference = _extract_reference(text)
    concept = _extract_concept(text)

    found = sum(v is not None for v in [bank, amount, date, reference])
    confidence = round(found / 4, 2)

    return {
        "bank": bank,
        "amount": amount,
        "currency": "BOB",
        "date": date,
        "time": time_,
        "reference": reference,
        "concept": concept,
        "confidence": confidence,
    }


def _extract_bank(text: str) -> str | None:
    for kw in BANK_KEYWORDS:
        if kw in text:
            return kw.title()
    return None


def _extract_amount(text: str) -> float | None:
    patterns = [
        r"BS\.?\s*([\d,]+\.?\d*)",
        r"MONTO:?\s*([\d,]+\.?\d*)",
        r"IMPORTE:?\s*([\d,]+\.?\d*)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _extract_date(text: str) -> str | None:
    m = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    if m:
        day, month, year = m.group(1).split("/")
        return f"{year}-{month}-{day}"
    m = re.search(r"FECHA:?\s*(\d{2}/\d{2}/\d{4})", text)
    if m:
        day, month, year = m.group(1).split("/")
        return f"{year}-{month}-{day}"
    return None


def _extract_time(text: str) -> str | None:
    m = re.search(r"HORA:?\s*(\d{2}:\d{2}:\d{2})", text)
    if m:
        return m.group(1)
    m = re.search(r"(\d{2}:\d{2}:\d{2})", text)
    return m.group(1) if m else None


def _extract_reference(text: str) -> str | None:
    m = re.search(r"REFERENCIA:?\s*(\d{8,12})", text)
    if m:
        return m.group(1)
    m = re.search(r"REF\.?:?\s*(\d{8,12})", text)
    return m.group(1) if m else None


def _extract_concept(text: str) -> str | None:
    m = re.search(r"CONCEPTO:?\s*([A-Z\s]+?)(?:\n|$)", text)
    if m:
        return m.group(1).strip().title()
    return None
