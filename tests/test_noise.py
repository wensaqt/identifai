import os
import random
import tempfile

from PIL import Image

from dataset.noise import apply_noise, apply_scan_effects, images_to_pdf, pdf_to_images


def _make_dummy_pdf():
    """Create a minimal 1-page PDF with a white image."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    img = Image.new("RGB", (200, 300), "white")
    img.save(path, format="PDF")
    return path


class TestScanEffects:
    def test_output_is_image(self):
        img = Image.new("RGB", (100, 100), "white")
        result = apply_scan_effects(img, "medium")
        assert isinstance(result, Image.Image)

    def test_levels(self):
        img = Image.new("RGB", (100, 100), "blue")
        for level in ("light", "medium", "heavy"):
            random.seed(0)
            result = apply_scan_effects(img, level)
            assert result.size[0] > 0
            assert result.size[1] > 0


class TestPdfRoundtrip:
    def test_pdf_to_images_and_back(self):
        pdf_path = _make_dummy_pdf()
        images = pdf_to_images(pdf_path, dpi=72)
        assert len(images) == 1
        assert isinstance(images[0], Image.Image)

        fd, out_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        images_to_pdf(images, out_path)
        assert os.path.getsize(out_path) > 0

        os.unlink(pdf_path)
        os.unlink(out_path)


class TestApplyNoise:
    def test_noisy_pdf_created(self):
        pdf_path = _make_dummy_pdf()
        fd, out_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)

        apply_noise(pdf_path, out_path, "light")
        assert os.path.getsize(out_path) > 0

        os.unlink(pdf_path)
        os.unlink(out_path)
