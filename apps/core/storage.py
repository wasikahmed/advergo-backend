from django.conf import settings
from django.core.files.storage import FileSystemStorage


def get_raw_file_storage():
    """
    Storage for non-image binary files (PDFs, .ai design files, ...).

    `MediaCloudinaryStorage` (the STORAGES["default"]) uploads everything as
    Cloudinary resource_type="image", which Cloudinary's delivery security
    policy blocks for non-image files like PDFs (401 on fetch, even though
    the upload itself succeeds) -- discovered by actually round-tripping an
    invoice PDF through it, not by reading the docs. Anything that isn't
    guaranteed to be a photo needs resource_type="raw" instead.
    """
    if settings.USE_CLOUDINARY:
        from cloudinary_storage.storage import RawMediaCloudinaryStorage

        return RawMediaCloudinaryStorage()
    return FileSystemStorage()
