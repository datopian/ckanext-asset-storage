import logging
import mimetypes
import os.path
from importlib import import_module
from shutil import copyfileobj
from typing import Any, BinaryIO, Dict, Optional, Tuple

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

NAMED_BACKENDS = {'local': 'ckanext.asset_storage.storage:LocalStorage',
                  }

_log = logging.getLogger(__name__)


def get_storage(backend_type, backend_config):
    # type: (str, Dict[str, Any]) -> StorageBackend
    backend_type = NAMED_BACKENDS.get(backend_type, backend_type)
    try:
        module_name, factory_name = backend_type.split(':')
    except ValueError:
        raise ValueError('Invalid backend name: expecting either a name'
                         'backend, or a callable designated in the format '
                         '`package.module:class`')

    try:
        module = import_module(module_name, __package__)
        factory = getattr(module, factory_name)
    except (ImportError, AttributeError):
        raise ValueError('Invalid backend name: unable to import {}'.format(backend_type))

    try:
        return factory(**backend_config)
    except TypeError as e:
        raise TypeError('Are you storage missing backend configuration options? (was: {})'.format(e))


class DownloadTarget(object):
    """A response for a download request

    Typically, this is instantiated by a `StorageBackend.download()` call using
    one of the two factory methods to represent either a redirection response
    or a direct download response.
    """
    def __init__(self, fileobj=None, filename=None, mimetype=None, redirect_to=None, redirect_code=302):
        # type: (Optional[BinaryIO], Optional[str], Optional[str], Optional[str], Optional[int]) -> DownloadTarget
        if mimetype is None and filename:
            mimetype = mimetypes.guess_type(filename)[0]
        self.fileobj = fileobj
        self.filename = filename
        self.mimetype = mimetype
        self.redirect_to = redirect_to
        self.redirect_code = redirect_code

    @classmethod
    def send_file(cls, fileobj, filename, mimetype=None):
        # type: (BinaryIO, str, Optional[str]) -> DownloadTarget
        """Factory for direct download responses
        """
        return cls(fileobj, filename, mimetype=mimetype)

    @classmethod
    def redirect(cls, redirect_to, redirect_code=302):
        # type: (str, Optional[int]) -> DownloadTarget
        """Factory for redirection response
        """
        return cls(redirect_to=redirect_to, redirect_code=redirect_code)


class StorageBackend(object):
    """Interface for all storage backends
    """
    def get_storage_uri(self, name, prefix=None):
        # type: (str, Optional[str]) -> str
        """Get the URI of the file in storage, based on file name and prefix.
        This can be a previously uploaded file or an about-to-be-uploaded file.

        Returned URI can be an absolute HTTP URL (for storage backends that allow
        direct public HTTP access) or a relative URI (an actual "identifier" for
        the file in storage that is), in which case the calling code will be
        responsible for requesting the storage backend to either download the file
        or provide an absolute external URL for it when it is requested in the future.
        """
        raise NotImplementedError("Inheriting classes must implement this")

    def upload(self, stream, name, prefix=None, max_size=None):
        # type: (BinaryIO, str, Optional[str], Optional[int]) -> int
        """Upload a file and return the number of bytes saved

        If max_size is specified, the storage backend should not accept files
        larger than that size
        """
        raise NotImplementedError("Inheriting classes must implement this")

    def download(self, uri):
        # type: (str) -> DownloadTarget
        """Download a file from storage, given the file's URI

        This will return a DownloadTarget object, which can represent
        either a direct download (and will include the open file object and
        info about the file) or a redirection to a new URL.
        """
        raise NotImplementedError("Inheriting classes must implement this")

    def delete(self, uri):
        # type: (str) -> bool
        """Delete a file from storage

        Returns a bool indicating whether the file was deleted or not.
        This may not be supported by all storage backends.
        """
        return False


class LocalStorage(StorageBackend):
    """A storage backend for storing assets in the local file system
    """
    def __init__(self, storage_path):
        self._path = storage_path

    def get_storage_uri(self, name, prefix=None):
        if prefix:
            return '{}/{}'.format(prefix, name)
        else:
            return name

    def upload(self, stream, name, prefix=None, max_size=None):
        """Save the file in local storage
        """
        file_path = self._get_file_path(name, prefix)
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True)

        with file_path.open('wb') as f:
            copyfileobj(stream, f)
        return self.get_storage_uri(name, prefix)

    def download(self, uri):
        """Download the file from local storage
        """
        name, prefix = self._parse_uri(uri)
        file_path = self._get_file_path(name, prefix)
        fileobj = file_path.open('rb')
        return DownloadTarget.send_file(fileobj, name)

    def delete(self, uri):
        file_path = self._get_file_path(*self._parse_uri(uri))
        try:
            file_path.unlink()
        except OSError as e:
            _log.warning('Failed to remove local file {}: {}'.format(file_path, e))
            return False
        return True

    def _get_file_path(self, name, prefix):
        # type: (str, Optional[str]) -> Path
        path = Path(self._path)
        if prefix:
            path = path / prefix
        return path / name

    @staticmethod
    def _parse_uri(uri):
        # type: (str) -> Tuple[str, Optional[str]]
        parts = os.path.split(uri)
        if len(parts) == 1:
            return parts[0], None
        elif len(parts) == 2:
            return parts[1], parts[0]
        else:
            raise ValueError("Invalid file URI for this storage module")
