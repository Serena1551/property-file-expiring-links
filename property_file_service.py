"""HTTP entry point for property-file download grants."""

import os
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException

from infrai_storage import InfraiError, InfraiStorage
from property_downloads import DownloadGrant, DownloadRequest, choose_expiry

app = FastAPI(title="Property file expiring links")


def storage_client() -> InfraiStorage:
    return InfraiStorage.from_environment()


@app.post("/download-links", response_model=DownloadGrant)
def create_download_link(
    request: DownloadRequest,
    storage: Annotated[InfraiStorage, Depends(storage_client)],
) -> DownloadGrant:
    bucket = os.environ.get("PROPERTY_FILES_BUCKET", "property-private-files")
    expected_prefix = f"properties/{request.property_id}/"
    if not request.file_key.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="File is outside the requested property")

    try:
        head = storage.head_object(bucket, request.file_key)
        if not head.get("found"):
            raise HTTPException(status_code=404, detail="Property file was not found")

        expiry = choose_expiry(request)
        filename = request.file_key.rsplit("/", 1)[-1]
        signed = storage.presign_download(
            bucket,
            request.file_key,
            expires_seconds=expiry,
            response_disposition=f'attachment; filename="{filename}"',
        )
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.code) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Storage request could not be completed") from exc

    return DownloadGrant(
        property_id=request.property_id,
        purpose=request.purpose,
        download_url=str(signed["url"]),
        expires_seconds=expiry,
    )
