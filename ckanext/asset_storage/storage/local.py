import logging
import os.path
from shutil import copyfileobj
from typing import Optional, Tuple

from ckanext.asset_storage.storage import DownloadTarget, StorageBackend, exc

from pathlib import Path


_log = logging.getLogger(__name__)


class LocalStorage(StorageBackend):
    """A storage backend for storing assets in the local file system
    """
    def __init__(self, storage_path):
        self._path = storage_path

    def get_storage_uri(self, name, prefix=None):
        if prefix:
            return os.path.join(prefix, name)
        else:
            return name

    def upload(self, stream, name, prefix=None, mimetype=None):
        """Save the file in local storage
        """
        file_path = self._get_file_path(name, prefix)
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True)

        with file_path.open('wb') as f:
            copyfileobj(stream, f)
            return f.tell()

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
