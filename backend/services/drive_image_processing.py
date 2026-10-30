"""Validate image pixels and create a separate, non-diagnostic thumbnail."""
import hashlib
import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_PIXELS = 40_000_000
THUMBNAIL_SIZE = (512, 512)
IMAGE_FORMATS = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp', 'BMP': 'image/bmp', 'TIFF': 'image/tiff'}


class ImageValidationError(ValueError):
    pass


def prepare_image(original, declared_mime):
    if not original:
        raise ImageValidationError('ملف الصورة فارغ')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(original)) as probe:
                mime = IMAGE_FORMATS.get(probe.format)
                if mime is None or mime != declared_mime or probe.width * probe.height > MAX_IMAGE_PIXELS:
                    raise ImageValidationError('نوع الصورة أو أبعادها غير مدعومة')
                probe.verify()
            with Image.open(io.BytesIO(original)) as image:
                image.seek(0)
                image.load()
                thumb = ImageOps.exif_transpose(image)
                thumb.thumbnail(THUMBNAIL_SIZE)
                if thumb.mode not in {'RGB', 'L'}:
                    thumb = thumb.convert('RGB')
                output = io.BytesIO()
                thumb.save(output, format='JPEG', quality=82, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        if isinstance(exc, ImageValidationError):
            raise
        raise ImageValidationError('ملف الصورة غير صالح أو أبعاده كبيرة جدًا') from exc
    thumbnail = output.getvalue()
    return {'original': original, 'mime': mime, 'size': len(original),
            'sha256': hashlib.sha256(original).hexdigest(), 'thumbnail': thumbnail,
            'thumbnail_sha256': hashlib.sha256(thumbnail).hexdigest()}
