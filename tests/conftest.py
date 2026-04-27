import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.repository import reset_repository_for_tests


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_TEMP_DIR", str(tmp_path))
    get_settings.cache_clear()
    reset_repository_for_tests()
    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


@pytest.fixture
def auth_editor():
    return {
        "X-User-Id": "user-editor-1",
        "X-Tenant-Id": "tenant-a",
        "X-User-Roles": "editor",
    }


@pytest.fixture
def auth_viewer():
    return {
        "X-User-Id": "user-viewer-1",
        "X-Tenant-Id": "tenant-a",
        "X-User-Roles": "viewer",
    }


@pytest.fixture
def auth_admin():
    return {
        "X-User-Id": "user-admin-1",
        "X-Tenant-Id": "tenant-a",
        "X-User-Roles": "admin",
    }
