"""CKAN Uploader implementation that wraps our storage backends
"""
import cgi
import datetime
from typing import Optional, Union

from ckan.lib.munge import munge_filename_legacy
from ckan.lib.uploader import _get_underlying_file  # noqa
from ckan.plugins import toolkit
from six.moves.urllib_parse import quote
from werkzeug.datastructures import FileStorage

from ckanext.asset_storage.storage import StorageBackend, get_storage

CONF_BACKEND_TYPE = 'ckanext.asset_storage.backend_type'
CONF_BACKEND_CONFIG = 'ckanext.asset_storage.backend_config'
ALLOWED_UPLOAD_TYPES = (cgi.FieldStorage, FileStorage)

# This is used for typing uploaded file form field wrapper
UploadedFileWrapper = Union[cgi.FieldStorage, FileStorage]


def get_configured_storage():
    # type: () -> StorageBackend
    backend_type = toolkit.config.get('ckanext.asset_storage.backend_type', 'local')
    config = toolkit.config.get('ckanext.asset_storage.backend_config', {})
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
            self._uploaded_file = _get_underlying_file(uploaded_file)
            filename = self._get_storage_uri(self._filename, self._object_type)

        elif self._old_filename and not self._old_filename.startswith('http'):
            if not self._clear:
                # Keep the old filename in data_dict
                filename = self._old_filename
            elif self._filename == self._old_filename:
                # Clear the old filename from data_dict
                filename = ''

        if filename is not None:
            data_dict[url_field] = filename

    def _get_storage_uri(self, filename, prefix):
        # type: (str, Optional[str]) -> str
        """Get the URI of a to-be-uploaded file from the storage backend and
        encode it in a way suitable for saving in the DB
        """
        storage_url = self._storage.get_storage_uri(filename, prefix)
        if _is_absolute_http_url(storage_url):
            return storage_url
        return quote(storage_url, safe='')

    def upload(self, max_size=2):
        """Actually upload the file.

        max_size is the maximum file size to accept in megabytes
        (note that not all backends will support this limitation).
        """
        if self._uploaded_file:
            self._storage.upload(self._uploaded_file,
                                 self._filename,
                                 self._object_type,
                                 max_size)
            self._clear = True

        if self._clear \
                and self._old_filename \
                and not _is_absolute_http_url(self._old_filename):
            self._storage.delete(self._old_filename)

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
        if not _is_absolute_http_url(url):
            return url
        url_pattern = toolkit.url_for('asset_storage.uploaded_file', file_uri='__URI__')
        pattern_parts = url_pattern.split('__URI__')
        if len(pattern_parts) != 2:
            raise RuntimeError("We really didn't get the expected URL pattern here")

        if url.startswith(pattern_parts[0]) and url.endswith(pattern_parts[1]):
            return url[len(pattern_parts[0])][:-len(pattern_parts[1])]


def _is_absolute_http_url(url):
    # type (str) -> bool
    """Tell if a string looks like an absolute HTTP URL

    >>> _is_absolute_http_url('https://foo.com/bar')
    True
    >>> _is_absolute_http_url('http://foo.com/bar')
    True
    >>> _is_absolute_http_url('http-file')
    False
    >>> _is_absolute_http_url('/foo/bar')
    False
    >>> _is_absolute_http_url('url')
    False
    >>> _is_absolute_http_url(None)
    False
    """
    try:
        return url[0:6] in {'http:/', 'https:'}
    except (TypeError, IndexError, ValueError):
        return False
