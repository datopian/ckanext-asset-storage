import shutil

import pytest


@pytest.fixture()
def storage_path(tmp_path):
    path = tmp_path / "asset_storage"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(str(tmp_path))
