import random

import fitz
from PIL import Image, ImageFilter


def pdf_to_images(pdf_path: str, dpi: int = 200) -> list[Image.Image]:
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


def apply_scan_effects(img: Image.Image, level: str = "medium") -> Image.Image:
    if level == "light":
        angle = random.uniform(-2, 2)
        blur_radius = 0.5
        quality = 80
    elif level == "heavy":
        angle = random.uniform(-5, 5)
        blur_radius = 1.5
        quality = 40
    else:  # medium
        angle = random.uniform(-3, 3)
        blur_radius = 1.0
        quality = 60

    img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))
    img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    if random.random() < 0.8:
        img = img.convert("L").convert("RGB")

    # JPEG compression artifacts
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    img = Image.open(buf).copy()

    return img


def images_to_pdf(images: list[Image.Image], output_path: str):
    if not images:
        return
    first, *rest = images
    first.save(output_path, format="PDF", save_all=True, append_images=rest)


def apply_noise(pdf_path: str, output_path: str, level: str = "medium"):
    images = pdf_to_images(pdf_path)
    noisy = [apply_scan_effects(img, level) for img in images]
    images_to_pdf(noisy, output_path)
