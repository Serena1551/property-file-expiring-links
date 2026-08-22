from fastapi.testclient import TestClient

from property_file_service import app, storage_client


class RecordingStorage:
    def __init__(self) -> None:
        self.presign_args: dict[str, object] = {}

    def head_object(self, bucket: str, key: str) -> dict[str, object]:
        return {"found": True}

    def presign_download(self, bucket: str, key: str, **body: object) -> dict[str, str]:
        self.presign_args = {"bucket": bucket, "key": key, **body}
        return {"url": "https://downloads.example/signed-renewal"}


def test_service_issues_scoped_tenant_document_link(monkeypatch) -> None:
    storage = RecordingStorage()
    monkeypatch.setenv("PROPERTY_FILES_BUCKET", "private-documents")
    app.dependency_overrides[storage_client] = lambda: storage
    try:
        response = TestClient(app).post(
            "/download-links",
            json={
                "property_id": "elm-court-12",
                "file_key": "properties/elm-court-12/leases/renewal.pdf",
                "purpose": "tenant_document",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["expires_seconds"] == 300
    assert storage.presign_args["expires_seconds"] == 300
    assert storage.presign_args["key"] == "properties/elm-court-12/leases/renewal.pdf"
