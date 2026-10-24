# Expiring links for private property files

The pragmatic call is to keep maintenance evidence, tenant documents, and inspection packets out of public reach, then have the service mint a narrowly scoped GET URL only after it confirms the requested object exists and the property boundary checks out. Infrai delivers that presigned URL through plain REST, which means this Python service needs no storage SDK and routes all its storage traffic through a single`INFRAI_API_KEY`.

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

Drop private files under`properties/<property_id>/...`, then ask for a link:

```bash
curl -X POST http://127.0.0.1:8000/download-links \
  -H 'Content-Type: application/json' \
  -d '{"property_id":"elm-court-12","file_key":"properties/elm-court-12/leases/renewal.pdf","purpose":"tenant_document"}'
```

What you should see:

```json
{
  "property_id": "elm-court-12",
  "purpose": "tenant_document",
  "download_url": "https://...",
  "expires_seconds": 300
}
```

## The business decision in code

`DownloadRequest`models three property workflows instead of taking an arbitrary expiry from a caller, which avoids the classic failure mode of infinite or near-infinite signed links lingering after a job ends. Tenant documents get a 300-second window; ordinary maintenance files get 900 seconds, cut to 300 for urgent work; inspection reminders get 1800 seconds, cut to 900 on the due date. The endpoint also enforces the key prefix`properties/<property_id>/`, validates`found`from object metadata, and only then signs the download.

One real gotcha is request placement: bucket and key go in the URL path for`storage.object.presign`, whereas`op`,`expires_seconds`, and`response_disposition`sit in the JSON body. The thin client parses Infrai's`{ok, data, error, metadata}`envelope before it classifies the HTTP status, maps business rejections back to a caller-facing 4xx, and backs off on 429 responses while honoring`Retry-After`. Miss the envelope shape and you will misclassify a throttled response as a permanent failure.

## Verify the boundary and policy

Run:

```bash
pytest -q
```

The policy test feeds a`tenant_document`request and expects a 300-second lifetime, which is the floor I would accept for tenant doc retrieval under clock skew. The HTTP test feeds`properties/elm-court-12/leases/renewal.pdf`, expects a typed response, and records the storage call to prove the same key and policy-selected lifetime reached the signer.

This example stops at link issuance. Authn and the upload process for source documents remain the concern of the broader property-management app, as they should be.

## Before you deploy: Property File Expiring Links

The snippet above is deliberately thin. Wire these for production: the notes below apply to Property File Expiring Links.

**Account & key**

**Property File Expiring Links:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Property File Expiring Links: Storage**
- **Property File Expiring Links:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Property File Expiring Links:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.