import io
from PIL import Image, ImageOps, ImageFilter


def preprocess(image_bytes: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Resize to 600x820 (standard receipt size for our synthetic data)
    img = img.resize((600, 820), Image.LANCZOS)

    # Mild sharpening helps OCR accuracy
    img = img.filter(ImageFilter.SHARPEN)

    return img


def to_bytes(img: Image.Image, fmt: str = "JPEG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()
