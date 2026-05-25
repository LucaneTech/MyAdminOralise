from whitenoise.storage import CompressedManifestStaticFilesStorage


class RelaxedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """WhiteNoise storage that silently skips missing referenced files."""
    manifest_strict = False
