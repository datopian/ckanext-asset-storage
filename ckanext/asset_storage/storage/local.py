import logging
import os.path
from typing import IO, Optional, Tuple

from ckanext.asset_storage.storage import DownloadTarget, StorageBackend, exc

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path


_log = logging.getLogger(__name__)


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

    def upload(self, stream, name, prefix=None, max_bytes=None):
        """Save the file in local storage
        """
        file_path = self._get_file_path(name, prefix)
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True)

        with file_path.open('wb') as f:
            return copy_fileobj(stream, f, max_bytes=max_bytes)

    def download(self, uri):
        """Download the file from local storage
        """
        name, prefix = self._parse_uri(uri)
        file_path = self._get_file_path(name, prefix)
        try:
            fileobj = file_path.open('rb')
        except IOError:
            raise exc.ObjectNotFound('The requested file was not found')
        return DownloadTarget.send_file(fileobj, name)

    def delete(self, uri):
        file_path = self._get_file_path(*self._parse_uri(uri))
        try:
            file_path.unlink()
        except (IOError, OSError) as e:
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


def copy_fileobj(source, target, max_bytes=None, length=16*1024):
    # type: (IO, IO, Optional[int], int) -> int
    """Copy the contents of one file-like object to another

    This is essentially similar to `shutil.copyfileobj`, except that:
     - it allows to stop copying after a specified number of bytes,
       as a safety mechanism
     - it will return the total number of bytes copied
    """
    written = 0
    while True:
        buf = source.read(length)
        if not buf:
            break
        if max_bytes is not None and written + len(buf) > max_bytes:
            raise exc.InvalidInput('File exceeds limit of {} bytes'.format(max_bytes))
        target.write(buf)
        written += len(buf)
    return written
