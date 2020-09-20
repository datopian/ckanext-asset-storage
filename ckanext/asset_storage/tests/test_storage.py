"""Tests for the storage module
"""
import pytest

from ckanext.asset_storage import storage
from ckanext.asset_storage.storage.local import LocalStorage


def test_get_backend_with_named_backend():
    """Test that loading a named storage backend works
    """
    backend = storage.get_storage('local', {'storage_path': '/tmp'})
    assert isinstance(backend, LocalStorage)


def test_get_backend_with_custom_backend():
    """Test that loading a custom storage backend works
    """
    backend = storage.get_storage('ckanext.asset_storage.storage.local:LocalStorage',
                                  {'storage_path': '/tmp'})
    assert isinstance(backend, LocalStorage)


def test_get_backend_invalid_custom_name():
    """Test that loading backend fails with specific error if name is invalid
    """
    with pytest.raises(ValueError):
        storage.get_storage('ckanext.asset_storage.storage.local.LocalStorage',
                            {'storage_path': '/tmp'})

    with pytest.raises(ValueError):
        storage.get_storage('ckanext.asset_storage.storage:local:LocalStorage',
                            {'storage_path': '/tmp'})


def test_get_backend_nonexisting_module():
    """Test that loading backend fails with specific error if backend module is unknown
    """
    with pytest.raises(ValueError):
        storage.get_storage('ckanext.asset_storage.storage.madeupstorage:Storage', {})


def test_get_backend_nonexisting_callable():
    """Test that loading backend fails with specific error if callable is unknown
    """
    with pytest.raises(ValueError):
        storage.get_storage('ckanext.asset_storage:storage:SomeMadeUpStorage', {})
