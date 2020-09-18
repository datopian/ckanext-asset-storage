from importlib import import_module
from typing import Any, BinaryIO, Dict

NAMED_BACKENDS = {'local': 'ckanext.asset_storage.storage:LocalStorage',
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

    return factory(**backend_config)


class StorageBackend(object):
    """Interface for all storage backends
    """
    def upload_file(self, name, stream):
        # type: (str, BinaryIO) -> str
        """Upload a file and return the new file's URL
        """
        raise NotImplementedError("Inheriting classes must implement this")

    def resolve_url(self, url):
        # type: (str) -> str
        """Resolve a relative or incomplete URL into something a browser can
        use to download a file
        """
        return url


class LocalStorage(StorageBackend):

    def __init__(self, storage_path):
        self._path = storage_path

    def upload_file(self, name, stream):
        pass

    def resolve_url(self, url):
        return super(LocalStorage, self).resolve_url(url)
