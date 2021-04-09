"""Tests for the uploader module
"""
from cgi import FieldStorage

import pytest
from six import BytesIO
from werkzeug.datastructures import FileStorage

from ckanext.asset_storage import uploader


@pytest.mark.parametrize('value,expected', [
    ('https://foo.com/bar', True),
    ('http://foo.com/bar', True),
    ('http-file', False),
    ('https.csv', False),
    ('/foo/bar', False),
    ('url', False),
    (None, False),
    (['https://', 'http:'], False)
])
def test_is_absolute_http_uri(value, expected):
    assert expected == uploader.is_absolute_http_url(value)


def test_uploader_update_data_dict():
    """Test that the uploader updates the data dict properly
    """
    backend = uploader.get_configured_storage()
    up = uploader.AssetUploader(backend, 'group', )
    data_dict = {'url': 'foo.png',
                 'clear': '',
                 'file': FileStorage(name='file', filename='foo.png', stream=BytesIO(b'hello'))}
    up.update_data_dict(data_dict, 'url', 'file', 'clear')
    assert data_dict['url'].startswith('http://localhost:5000/uploads/group/')
    assert data_dict['url'].endswith('-foo.png')


def test_uploader_update_data_dict_existing_file():
    """Test that the uploader updates the data dict properly when a file already exists
    """
    backend = uploader.get_configured_storage()
    up = uploader.AssetUploader(backend, 'group', 'bar.png')
    data_dict = {'url': 'foo.png',
                 'clear': '',
                 'file': FileStorage(name='file', filename='foo.png', stream=BytesIO(b'hello'))}
    up.update_data_dict(data_dict, 'url', 'file', 'clear')
    assert data_dict['url'].startswith('http://localhost:5000/uploads/group/')
    assert data_dict['url'].endswith('-foo.png')


def test_uploader_update_data_dict_no_upload():
    """Test that the uploader doesn't change the URL if no upload was done
    """
    backend = uploader.get_configured_storage()
    up = uploader.AssetUploader(backend, 'group', 'original.png')
    data_dict = {'url': 'original.png',
                 'clear': '',
                 'file': FileStorage(name='file')}
    up.update_data_dict(data_dict, 'url', 'file', 'clear')
    assert data_dict['url'] == 'original.png'


def test_uploader_update_data_dict_no_upload_no_previous_file():
    """Test that the uploader updates the data dict properly
    """
    backend = uploader.get_configured_storage()
    up = uploader.AssetUploader(backend, 'group')
    data_dict = {'url': 'foo.png',
                 'clear': '',
                 'file': FileStorage(name='file', filename='foo.png', stream=BytesIO(b'hello'))}
    up.update_data_dict(data_dict, 'url', 'file', 'clear')
    assert data_dict['url'].startswith('http://localhost:5000/uploads/group/')
    assert data_dict['url'].endswith('-foo.png')


def test_uploader_update_data_dict_cleared():
    """Test that the uploader updates the data when 'clear' is set
    """
    backend = uploader.get_configured_storage()
    up = uploader.AssetUploader(backend, 'group', 'original.png')
    data_dict = {'url': 'original.png',
                 'clear': '1',
                 'file': FileStorage(name='file')}
    up.update_data_dict(data_dict, 'url', 'file', 'clear')
    assert data_dict['url'] == ''


def test_uploader_update_data_dict_existing_file_cgi():
    """Test that the uploader updates the data dict properly when a file already exists

    This test simulates CKAN 2.8 (Pylons / cgi) based upload
    """
    backend = uploader.get_configured_storage()
    up = uploader.AssetUploader(backend, 'group', 'bar.png')
    data_dict = {'url': 'foo.png',
                 'clear': '',
                 'file': FieldStorage(fp=BytesIO(b'hello'),
                                      headers={"content-disposition": 'form-data; name="file"; filename="foo.png"'})}
    up.update_data_dict(data_dict, 'url', 'file', 'clear')
    assert data_dict['url'].startswith('http://localhost:5000/uploads/group/')
    assert data_dict['url'].endswith('-foo.png')


def test_uploader_property():
    backend = uploader.get_configured_storage()
    up = uploader.AssetUploader(backend, 'group', 'bar.png')
    data_dict = {'url': 'foo.png',
                 'clear': '',
                 'file': FieldStorage(fp=BytesIO(b'hello'),
                                      headers={"content-disposition": 'form-data; name="file"; filename="foo.png"'})}
    up.update_data_dict(data_dict, 'url', 'file', 'clear')
    assert up.filename == 'foo.png'
