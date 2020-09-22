"""CKAN Uploader implementation that wraps our storage backends
"""
import datetime
import logging
import mimetypes
import os
import io
from typing import Optional, Union

from ckan.lib.munge import munge_filename_legacy
from ckan.lib.uploader import _get_underlying_file  # noqa
from ckan.lib.uploader import ALLOWED_UPLOAD_TYPES, MB
from ckan.plugins import toolkit
from six.moves.urllib_parse import quote, unquote

from ckanext.asset_storage.storage import StorageBackend, get_storage

CONF_BACKEND_TYPE = 'ckanext.asset_storage.backend_type'
CONF_BACKEND_CONFIG = 'ckanext.asset_storage.backend_options'

# This is used for typing uploaded file form field wrapper
UploadedFileWrapper = Union[ALLOWED_UPLOAD_TYPES]

_log = logging.getLogger(__name__)


def get_configured_storage():
    # type: () -> StorageBackend
    backend_type = toolkit.config.get(CONF_BACKEND_TYPE, 'local')
    config = toolkit.config.get(CONF_BACKEND_CONFIG, {})
    return get_storage(backend_type=backend_type, backend_config=config)


class AssetUploader(object):

    def __init__(self, storage, object_type, old_filename=None):
        # type: (StorageBackend, str, Optional[str]) -> AssetUploader
        """Create a new Uploader instance

        This is called by CKAN when a new asset is about to be uploaded. It
        may happen on group / org creation or editing, or when an admin sets
        the site logo, for example.

        `object_type` is set based on the asset type (e.g. `group` or `admin`)
        and is typically used as part of the asset name in storage.

        `old_filename` is set when editing an existing group, and will contain
        the current name or URL of the file in storage, before editing.
        """
        self._storage = storage
        self._object_type = object_type
        self._filename = None
        self._clear = None
        self._file_field_name = None
        self._uploaded_file = None
        self._old_filename = None

        if old_filename:
            self._old_filename = self._parse_old_uri(old_filename)

    def update_data_dict(self, data_dict, url_field, file_field, clear_field):
        """Manipulate data from the data_dict. This needs to be called before it
        reaches any validators.

        `url_field` is the name of the field where the upload is going to be.

        `file_field` is name of the key where the FieldStorage is kept (i.e
        the field where the file data actually is).

        `clear_field` is the name of a boolean field which requests the upload
        to be deleted.
        """
        self._filename = data_dict.get(url_field, '')
        self._clear = data_dict.pop(clear_field, None)
        uploaded_file = data_dict.pop(file_field, None)
        filename = None

        if isinstance(uploaded_file, ALLOWED_UPLOAD_TYPES):
            self._filename = self._create_uploaded_filename(uploaded_file)
            self._uploaded_file = uploaded_file
            filename = self._get_storage_uri(self._filename, self._object_type)
            _log.debug("Got a new uploaded asset, file name will be %s", self._filename)

        elif self._old_filename and not self._old_filename.startswith('http'):
            if not self._clear:
                # Keep the old filename in data_dict
                filename = self._old_filename
            elif self._filename == self._old_filename:
                # Clear the old filename from data_dict
                filename = ''

        if filename is not None:
            _log.debug("Updating data_dict before upload: %s set to %s", url_field, filename)
            data_dict[url_field] = filename

    def upload(self, max_size=2):
        """Actually upload the file.

        max_size is the maximum file size to accept in megabytes
        (note that not all backends will support this limitation).
        """
        if self._uploaded_file is not None:
            _log.debug("Initiating file upload for %s, storage is %s", self._filename, self._storage)
            size = get_uploaded_size(self._uploaded_file)
            _log.debug("Detected file size: %s", size)
            if size and max_size and size > max_size * MB:
                raise toolkit.ValidationError({'upload': ['File upload too large']})

            mimetype = get_uploaded_mimetype(self._uploaded_file)
            _log.debug("Detected file MIME type: %s", mimetype)
            stored = self._storage.upload(_get_underlying_file(self._uploaded_file),
                                          self._filename,
                                          self._object_type,
                                          mimetype=mimetype)
            _log.debug("Finished uploading file %s, %d bytes written to storage", self._filename, stored)
            self._clear = True

        if self._clear \
                and self._old_filename \
                and not is_absolute_http_url(self._old_filename):
            _log.debug("Clearing old asset file: %s", self._old_filename)
            self._storage.delete(self._old_filename)

    def _get_storage_uri(self, filename, prefix):
        # type: (str, Optional[str]) -> str
        """Get the URI of a to-be-uploaded file from the storage backend and
        encode it in a way suitable for saving in the DB
        """
        storage_url = self._storage.get_storage_uri(filename, prefix)
        if is_absolute_http_url(storage_url):
            return storage_url
        return toolkit.url_for('asset_storage.uploaded_file',
                               file_uri=quote(storage_url, safe='/'),
                               _external=True)

    @staticmethod
    def _create_uploaded_filename(uploaded_file_field):
        # type: (UploadedFileWrapper) -> str
        """Create a filename for storage for the new uploaded file
        """
        now = str(datetime.datetime.utcnow())
        filename = '{}-{}'.format(now, uploaded_file_field.filename)
        return munge_filename_legacy(filename)

    @staticmethod
    def _parse_old_uri(url):
        # type (str) -> str
        """Parse the storage provided URI out of an absolute download URL saved
        in the CKAN DB

        This will return the original URL if it does not match our
        expected pattern
        """
        if not is_absolute_http_url(url):
            return url
        url_pattern = toolkit.url_for('asset_storage.uploaded_file', file_uri='__URI__', _external=True)
        pattern_parts = url_pattern.split('__URI__')
        if len(pattern_parts) != 2:
            raise RuntimeError("We really didn't get the expected URL pattern here")

        if url.startswith(pattern_parts[0]) and url.endswith(pattern_parts[1]):
            return decode_uri(url[len(pattern_parts[0])][:-len(pattern_parts[1])])


def decode_uri(uri):
    # type: (str) -> str
    """Decode a URI before passing it to storage
    """
    return unquote(uri)


def is_absolute_http_url(url):
    # type (str) -> bool
    """Tell if a string looks like an absolute HTTP URL
    """
    try:
        return url[0:6] in {'http:/', 'https:'}
    except (TypeError, IndexError, ValueError):
        return False


def get_uploaded_mimetype(uploaded):
    # type: (UploadedFileWrapper) -> Optional[str]
    """Try to figure out the mime type of an uploaded file
    """
    mimetype = None
    # Uploaded content-type header set by client
    try:
        mimetype = uploaded.headers['Content-Length']
    except (AttributeError, KeyError):
        pass

    if mimetype:
        return mimetype

    # Guess mimetype based on file extension (may still be None)
    mimetype = mimetypes.guess_type(uploaded.filename)[0]
    return mimetype


def get_uploaded_size(uploaded):
    # type: (UploadedFileWrapper) -> Optional[int]
    """Try to figure out the size in bytes of an uploaded file

    This may not work for all uploaded file types, in which case None will
    be returned
    """
    # Let's try to get the size from the stream first, as it is more reliable and secure
    stream = _get_underlying_file(uploaded)
    try:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(0)
        return size
    except (AttributeError, IOError):  # no seek / non-seekable stream
        pass

    try:
        # FlaskFileStorage / cgi.FieldStorage
        return uploaded.headers['Content-Length']
    except (AttributeError, KeyError):
        pass

    return None
