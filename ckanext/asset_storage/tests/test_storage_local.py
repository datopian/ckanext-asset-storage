"""Tests for the local storage backend
"""
import pytest
from six import BytesIO

from ckanext.asset_storage.storage import exc
from ckanext.asset_storage.storage.local import LocalStorage, copy_fileobj


def test_copy_fileobj():
    test_string = b'This is a source string'
    source = BytesIO(test_string)
    dest = BytesIO()
    written = copy_fileobj(source, dest)
    assert dest.getvalue() == source.getvalue()
    assert written == len(test_string)


def test_copy_fileobj_exceeds_max():
    source = BytesIO(b'This is a source string')
    dest = BytesIO()
    with pytest.raises(exc.InvalidInput):
        copy_fileobj(source, dest, max_bytes=5)


def test_store_get_uri():
    storage = LocalStorage(storage_path='/tmp/whatever')
    uri = storage.get_storage_uri('my-picture.jpeg', 'users')
    assert 'users/my-picture.jpeg' == uri


def test_store_get_uri_no_prefix():
    storage = LocalStorage(storage_path='/tmp/whatever')
    uri = storage.get_storage_uri('my-picture.jpeg')
    assert 'my-picture.jpeg' == uri


def test_store_upload(storage_path):
    """Test uploading to local storage
    """
    content = b'This is the contents of the file'
    storage = LocalStorage(storage_path=storage_path)
    written = storage.upload(BytesIO(content), 'my-file.txt', 'assets')
    assert written == len(content)

    actual = (storage_path / 'assets' / 'my-file.txt').read_bytes()
    assert actual == content


def test_store_upload_with_max_bytes(storage_path):
    """Test uploading to local storage
    """
    content = b'This is the contents of the file'
    storage = LocalStorage(storage_path=storage_path)
    written = storage.upload(BytesIO(content), 'my-file.txt', 'assets', max_bytes=1024)
    assert written == len(content)


def test_store_upload_exceeds_max_bytes(storage_path):
    """Test uploading to local storage
    """
    content = b'This is the contents of the file'
    storage = LocalStorage(storage_path=storage_path)
    with pytest.raises(exc.InvalidInput):
        storage.upload(BytesIO(content), 'my-file.txt', 'assets', max_bytes=5)


def test_store_upload_download(storage_path):
    """Test uploading to local storage and then downloading
    """
    content = b'This is the contents of the file'
    storage = LocalStorage(storage_path=storage_path)
    storage.upload(BytesIO(content), 'my-file.txt', 'assets')

    target = storage.download(storage.get_storage_uri('my-file.txt', 'assets'))
    assert target.redirect_to is None
    assert target.mimetype == 'text/plain'
    assert target.fileobj.read() == content


def test_store_download_non_existing_file(storage_path):
    """Test downloading a non-existing file throws an exception
    """
    storage = LocalStorage(storage_path=storage_path)
    with pytest.raises(exc.ObjectNotFound):
        storage.download(storage.get_storage_uri('other-file.txt', 'assets'))


def test_store_delete_file_is_removed(storage_path):
    """Test that removing an existing file works
    """
    content = b'This is the contents of the file'
    storage = LocalStorage(storage_path=storage_path)
    storage.upload(BytesIO(content), 'my-file.txt', 'assets')

    stored_uri = storage.get_storage_uri('my-file.txt', 'assets')
    target = storage.download(stored_uri)
    assert target.fileobj.read() == content

    removed = storage.delete(stored_uri)
    assert removed

    # File should now be non-existent
    with pytest.raises(exc.ObjectNotFound):
        storage.download(stored_uri)


def test_store_delete_non_existing_file(storage_path):
    """Test that removing a non-existing file returns `False`
    """
    storage = LocalStorage(storage_path=storage_path)
    stored_uri = storage.get_storage_uri('other-file.txt', 'assets')
    removed = storage.delete(stored_uri)
    assert not removed
