from whitenoise.storage import CompressedManifestStaticFilesStorage

try:
    from whitenoise.storage import MissingFileError
except ImportError:
    MissingFileError = type(None)


class RelaxedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """WhiteNoise storage that silently skips missing referenced files in CSS."""
    manifest_strict = False

    def post_process(self, *args, **kwargs):
        for name, hashed_name, processed in super().post_process(*args, **kwargs):
            if isinstance(processed, MissingFileError):
                processed = False
            yield name, hashed_name, processed
