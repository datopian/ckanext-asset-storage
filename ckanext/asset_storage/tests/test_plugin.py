"""Tests for plugin.py
"""
import pytest

from ckanext.asset_storage import plugin, uploader


def test_plugin():
    p = plugin.AssetStoragePlugin()
    assert p


@pytest.mark.ckan_config(uploader.CONF_BACKEND_CONFIG, '{"path": "some/path/here"}')
def test_plugin_parses_backend_configuration(ckan_config):
    p = plugin.AssetStoragePlugin()
    p.update_config(ckan_config)
    assert ckan_config[uploader.CONF_BACKEND_CONFIG] == {"path": "some/path/here"}
