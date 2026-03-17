from __future__ import annotations

import random
from enum import StrEnum
from io import BytesIO

import fitz
from PIL import Image, ImageFilter


class NoiseLevel(StrEnum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


_NOISE_PARAMS = {
    NoiseLevel.LIGHT: {"angle": 2, "blur": 0.5, "quality": 80},
    NoiseLevel.MEDIUM: {"angle": 3, "blur": 1.0, "quality": 60},
    NoiseLevel.HEAVY: {"angle": 5, "blur": 1.5, "quality": 40},
}


class ScanSimulator:

    @staticmethod
    def _pdf_to_images(pdf_path: str, dpi: int = 200) -> list[Image.Image]:
        doc = fitz.open(pdf_path)
        images = []
        for page in doc:
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            images.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
        doc.close()
        return images

    @staticmethod
    def _images_to_pdf(images: list[Image.Image], output_path: str) -> None:
        if not images:
            return
        first, *rest = images
        first.save(output_path, format="PDF", save_all=True, append_images=rest)

    def _apply_rotation(self, img: Image.Image, max_angle: float) -> Image.Image:
        angle = random.uniform(-max_angle, max_angle)
        return img.rotate(angle, expand=True, fillcolor=(255, 255, 255))

    def _apply_blur(self, img: Image.Image, radius: float) -> Image.Image:
        return img.filter(ImageFilter.GaussianBlur(radius=radius))

    def _apply_grayscale(self, img: Image.Image) -> Image.Image:
        if random.random() < 0.8:
            return img.convert("L").convert("RGB")
        return img

    def _apply_jpeg_artifacts(self, img: Image.Image, quality: int) -> Image.Image:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        return Image.open(buf).copy()

    def apply_effects(self, img: Image.Image, level: NoiseLevel) -> Image.Image:
        params = _NOISE_PARAMS[level]
        img = self._apply_rotation(img, params["angle"])
        img = self._apply_blur(img, params["blur"])
        img = self._apply_grayscale(img)
        img = self._apply_jpeg_artifacts(img, params["quality"])
        return img

    def apply_noise(self, pdf_path: str, output_path: str, level: NoiseLevel) -> None:
        images = self._pdf_to_images(pdf_path)
        noisy = [self.apply_effects(img, level) for img in images]
        self._images_to_pdf(noisy, output_path)
