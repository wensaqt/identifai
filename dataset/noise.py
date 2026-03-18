# Backward-compatible re-exports from factories.noise
from .factories.noise import NoiseLevel, ScanSimulator  # noqa: F401


def pdf_to_images(pdf_path: str, dpi: int = 200):
    return ScanSimulator._pdf_to_images(pdf_path, dpi)


def apply_scan_effects(img, level: str = "medium"):
    return ScanSimulator().apply_effects(img, NoiseLevel(level))


def images_to_pdf(images, output_path: str):
    ScanSimulator._images_to_pdf(images, output_path)


def apply_noise(pdf_path: str, output_path: str, level: str = "medium"):
    ScanSimulator().apply_noise(pdf_path, output_path, NoiseLevel(level))
