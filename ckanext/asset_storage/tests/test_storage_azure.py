"""Tests for the Azure storage backend

TODO: add dynamic / vcr based tests
"""
from ckanext.asset_storage.storage import get_storage
from ckanext.asset_storage.storage.azure_blobs import AzureBlobStorage

FAKE_CONN_STRING = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)


def test_store_can_instantiate():
    storage = AzureBlobStorage('my-container', FAKE_CONN_STRING)
    assert storage


def test_storage_fetched_from_factory():
    storage = get_storage('azure_blobs', {"container_name": "my-container", "connection_string": FAKE_CONN_STRING})
    assert isinstance(storage, AzureBlobStorage)
