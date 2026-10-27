import hashlib
import io

import pytest
from PIL import Image

from backend.services.drive_image_processing import ImageValidationError, prepare_image


def test_original_bytes_are_unchanged_and_thumbnail_is_separate():
    output = io.BytesIO()
    Image.new('RGB', (800, 600), 'red').save(output, format='PNG')
    original = output.getvalue()
    result = prepare_image(original, 'image/png')
    assert result['original'] == original
    assert result['sha256'] == hashlib.sha256(original).hexdigest()
    assert result['thumbnail'] != original
    with Image.open(io.BytesIO(result['thumbnail'])) as thumbnail:
        assert thumbnail.format == 'JPEG' and thumbnail.width <= 512 and thumbnail.height <= 512
    with pytest.raises(ImageValidationError):
        prepare_image(original, 'image/jpeg')
    with pytest.raises(ImageValidationError):
        prepare_image(b'not-an-image', 'image/png')


def test_oversized_pixel_dimensions_are_rejected(monkeypatch):
    import backend.services.drive_image_processing as processing
    output = io.BytesIO()
    Image.new('RGB', (20, 20), 'white').save(output, format='PNG')
    monkeypatch.setattr(processing, 'MAX_IMAGE_PIXELS', 100)
    with pytest.raises(ImageValidationError):
        prepare_image(output.getvalue(), 'image/png')
