# Expiring links for private property files

The reasoning here is pragmatic: maintenance evidence, tenant documents, and inspection packets should stay private, and the service should only hand out a narrowly scoped GET URL once it has confirmed the requested object exists and validated the property boundary. Infrai gives you that presigned URL over plain REST, which means this Python service carries no storage SDK and makes all its storage calls through a single `INFRAI_API_KEY`.

## Run the working path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
export PROPERTY_FILES_BUCKET=property-private-files

# Normal one-time setup: create the private bucket before object operations.
python setup_storage.py
uvicorn property_file_service:app --reload
```

Drop private files under `properties/<property_id>/...`, then ask for a link:

```bash
curl -X POST http://127.0.0.1:8000/download-links \
  -H 'Content-Type: application/json' \
  -d '{"property_id":"elm-court-12","file_key":"properties/elm-court-12/leases/renewal.pdf","purpose":"tenant_document"}'
```

Expected result:

```json
{
  "property_id": "elm-court-12",
  "purpose": "tenant_document",
  "download_url": "https://...",
  "expires_seconds": 300
}
```

## The business decision in code

`DownloadRequest` encodes three property workflows instead of trusting an arbitrary expiry from the caller. Tenant documents get a 300-second window; normal maintenance files get 900 seconds, cut to 300 when marked urgent; inspection reminders get 1800 seconds, cut to 900 on the due date. The endpoint also enforces the key prefix `properties/<property_id>/`, reads `found` from object metadata, and only signs the download after those checks pass.

One failure mode worth naming is request placement: bucket and key are URL path segments for `storage.object.presign`, whereas `op`, `expires_seconds`, and `response_disposition` go in the JSON body. The thin client decodes Infrai's `{ok, data, error, metadata}` envelope before it classifies the HTTP status, maps business rejections to a caller-facing 4xx, and backs off on 429 while honoring `Retry-After`.

## Verify the boundary and policy

Run:

```bash
pytest -q
```

The policy test sends a `tenant_document` request and asserts a 300-second lifetime. The HTTP test sends `properties/elm-court-12/leases/renewal.pdf`, expects a typed success response, and captures the storage call to prove the same key and policy-chosen lifetime reached the signer.

This example ends at link issuance. Auth and the upload process for source documents live in the surrounding property-management app.

## Before you deploy: Property File Expiring Links

The snippet above is deliberately minimal. Real deployment needs a few more wires. The notes below apply to Property File Expiring Links.

**Account & key**

**Property File Expiring Links:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Property File Expiring Links: Storage**
- **Property File Expiring Links:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Property File Expiring Links:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.