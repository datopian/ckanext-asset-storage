"""Tests for plugin.py
"""
import ckanext.asset_storage.plugin as plugin


def test_plugin():
    p = plugin.AssetStoragePlugin()
    assert p
