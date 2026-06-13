from app.core.s3_client import get_s3_client, reset_s3_client_cache
from app.services.storage_service import get_storage_service, reset_storage_service_cache


def test_get_s3_client_reuses_cached_instance(monkeypatch):
    reset_s3_client_cache()
    created_clients = []

    class FakeBoto3Module:
        @staticmethod
        def client(*args, **kwargs):
            created_clients.append((args, kwargs))
            return object()

    monkeypatch.setattr("app.core.s3_client.boto3", FakeBoto3Module())

    first_client = get_s3_client()
    second_client = get_s3_client()

    assert first_client is second_client
    assert len(created_clients) == 1


def test_get_storage_service_reuses_cached_instance(monkeypatch):
    reset_storage_service_cache()
    created_services = []

    class FakeStorageService:
        pass

    def fake_storage_service_factory():
        created_services.append(True)
        return FakeStorageService()

    monkeypatch.setattr(
        "app.services.storage_service.StorageService",
        fake_storage_service_factory,
    )

    first_service = get_storage_service()
    second_service = get_storage_service()

    assert first_service is second_service
    assert len(created_services) == 1
