import mimetypes
from importlib import import_module
from typing import Any, BinaryIO, Dict, Optional

NAMED_BACKENDS = {'local': 'ckanext.asset_storage.storage.local:LocalStorage',
                  }


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
            if mimetype is None:
                mimetype = 'application/octet-stream'

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

    def upload(self, stream, name, prefix=None, mimetype=None):
        # type: (BinaryIO, str, Optional[str], Optional[str]) -> int
        """Upload a file and return the number of bytes saved

        Some storage backends may store metadata such as the file's MIME type,
        but this is not supported by all storage backends.
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
