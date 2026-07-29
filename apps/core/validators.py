import os

from django.core.exceptions import ValidationError

# Matches the upload spec on the quote form: .ai / .jpg / .png / .pdf, max 20 MB.
ALLOWED_DESIGN_FILE_EXTENSIONS = {".ai", ".jpg", ".jpeg", ".png", ".pdf"}
MAX_DESIGN_FILE_SIZE_BYTES = 20 * 1024 * 1024


def validate_design_file(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_DESIGN_FILE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_DESIGN_FILE_EXTENSIONS))
        raise ValidationError(f"Unsupported file type '{ext}'. Allowed: {allowed}.")
    if file.size > MAX_DESIGN_FILE_SIZE_BYTES:
        raise ValidationError("File too large. Maximum size is 20 MB.")


def validate_image_file(file, max_size_mb=8):
    ext = os.path.splitext(file.name)[1].lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    if ext not in allowed:
        raise ValidationError(
            f"Unsupported image type '{ext}'. Allowed: {', '.join(sorted(allowed))}."
        )
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Image too large. Maximum size is {max_size_mb} MB.")
