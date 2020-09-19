"""ckanext-external-storage Flask blueprints
"""
from flask import Blueprint

blueprint = Blueprint(
    'asset_storage',
    __name__,
)


def uploaded_file(file_uri):
    """Download an asset

    This may either return a redirect response to the canonical asset URL,
    or the asset itself as a stream of bytes (?)
    """
    return file_uri


blueprint.add_url_rule(u'/uploads/<file_uri>', view_func=uploaded_file)
