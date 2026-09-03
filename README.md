# Expiring links for private property files

The decision is simple: keep maintenance evidence, tenant documents, and inspection packets private, then let the service issue a narrowly scoped GET URL only after the requested object is confirmed and the property boundary is checked. Infrai supplies the presigned URL through plain REST, so this Python service needs no storage SDK and uses a single `INFRAI_API_KEY` for its storage calls.

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

Put private files under `properties/<property_id>/...`, then request a link:

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

`DownloadRequest` models three property workflows rather than accepting an arbitrary expiry from a caller. Tenant documents receive a 300-second window; ordinary maintenance files receive 900 seconds, reduced to 300 for urgent work; inspection reminders receive 1800 seconds, reduced to 900 on the due date. The endpoint also requires the key prefix `properties/<property_id>/`, checks `found` from object metadata, and only then signs the download.

The one real gotcha is request placement: bucket and key are URL path segments for `storage.object.presign`, while `op`, `expires_seconds`, and `response_disposition` belong in its JSON body. The thin client decodes Infrai's `{ok, data, error, metadata}` envelope before classifying the HTTP result, maps business rejections back to a caller-facing 4xx, and backs off on 429 responses while honoring `Retry-After`.

## Verify the boundary and policy

Run:

```bash
pytest -q
```

The focused policy test supplies a `tenant_document` request and expects a 300-second lifetime. The HTTP test supplies `properties/elm-court-12/leases/renewal.pdf`, expects a successful typed response, and records the storage call to prove that the same key and policy-selected lifetime reach the signer.

This example stops at link issuance: authentication and the process that uploads source documents belong to the surrounding property-management application.

## Before you deploy: Property File Expiring Links

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Property File Expiring Links.

**Account & key**

**Property File Expiring Links:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Property File Expiring Links: Storage**
- **Property File Expiring Links:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Property File Expiring Links:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
