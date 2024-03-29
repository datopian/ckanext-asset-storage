"""ckanext-external-storage Flask blueprints
"""
from ckan.plugins import toolkit
from flask import Blueprint, redirect, send_file

from .storage import exc
from .uploader import decode_uri, get_configured_storage

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
    try:
        storage_result = storage.download(decode_uri(file_uri))
    except exc.ObjectNotFound:
        return toolkit.abort(
            404,
            "The requested asset was not found in storage: {}".format(
                decode_uri(file_uri)
            ),
        )

    if storage_result.fileobj:
        # File-like object, just serve it
        return send_file(storage_result.fileobj, mimetype=storage_result.mimetype)
    elif storage_result.redirect_to:
        # Got a redirect response to an external URL
        return redirect(storage_result.redirect_to, storage_result.redirect_code)

    raise ValueError("Unexpected response from storage backend: {}".
                     format(storage_result))


blueprint.add_url_rule(u'/uploads/<path:file_uri>', view_func=uploaded_file)
