"""Storage specific errors
"""


class StorageError(Exception):
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
