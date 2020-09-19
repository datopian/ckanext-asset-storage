"""Tests for the uploader module
"""
import pytest

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
