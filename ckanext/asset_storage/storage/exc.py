"""Storage specific errors
"""
import six

_BaseException = Exception if six.PY3 else StandardError  # noqa: F821


class StorageError(_BaseException):
    """Base exception for all storage errors
    """
    pass


class InvalidInput(StorageError, ValueError):
    """Exception indicating input provided to storage is invalid
    """
    pass


class ObjectNotFound(StorageError, IOError):
    """Exception indicating that a requested file was not found
    """
