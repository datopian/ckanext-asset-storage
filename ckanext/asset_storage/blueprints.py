"""ckanext-external-storage Flask blueprints
"""
from flask import Blueprint, redirect, send_file

from .uploader import decode_uri, get_configured_storage, is_absolute_http_url

blueprint = Blueprint(
    'asset_storage',
    __name__,
)


def uploaded_file(file_uri):
    """Download an asset

    This may either return a redirect response to the canonical asset URL,
    or the asset itself as a stream of bytes (?)
    """
    storage = get_configured_storage()
    storage_result = storage.download(decode_uri(file_uri))
    if hasattr(storage_result, 'read'):
        # File-like object, just serve it
        return send_file(storage_result)
    elif isinstance(storage_result, tuple):
        # Got a redirect with pre-defined status code
        return redirect(storage_result[0], storage_result[1])
    elif is_absolute_http_url(storage_result):
        # Got a redirect with no status code, default to 302
        return redirect(storage_result)

    raise ValueError("Unexpected response from storage backend: {}".
                     format(storage_result))


blueprint.add_url_rule(u'/asset/<file_uri>', view_func=uploaded_file)
