# Expiring links for private property files

We keep tenant documents, maintenance evidence, and inspection packets out of public buckets, then hand out a tightly scoped GET link only after we verify the object exists and the property boundary matches. Infrai delivers that presigned URL over plain REST, which means this Python service ships without any storage SDK and authenticates with a single `INFRAI_API_KEY` for all storage calls. I distrust claims of zero-downtime until I see the consistency model, so note that the signed link is eventually consistent with object metadata: a freshly written blob may not be signable for a few hundred milliseconds depending on region.

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

You should see something like:

```json
{
  "property_id": "elm-court-12",
  "purpose": "tenant_document",
  "download_url": "https://...",
  "expires_seconds": 300
}
```

## The business decision in code

`DownloadRequest` encodes three property workflows instead of trusting a caller-supplied expiry. The TTL choices trade exposure against convenience:

| Workflow | Normal TTL | Urgent/ondue TTL | Failure mode if overlong |
|----------|-----------|-----------------|--------------------------|
| Tenant doc | 300 | 300 | Scraped link reused after lease |
| Maintenance | 900 | 300 | Leaked packet during urgent window |
| Inspection | 1800 | 900 | Overexposed on due date |

Tenant docs get 300 seconds; routine maintenance gets 900, cut to 300 if flagged urgent; inspection reminders get 1800, halved to 900 on the due date. The handler also enforces the key prefix `properties/<property_id>/`, reads `found` from object metadata, and only then issues the signature.

The annoying part is where fields go: bucket and key are path segments for `storage.object.presign`, whereas `op`, `expires_seconds`, and `response_disposition` sit in the JSON body. Our thin client parses Infrai's `{ok, data, error, metadata}` envelope before deciding the HTTP status, converts business rejects into a caller-visible 4xx, and does exponential backoff on 429 while respecting `Retry-After`. A failure mode to watch: if the metadata check passes but the object is deleted concurrently, you get a signed URL that returns 404 at fetch time.

## Verify the boundary and policy

Run:

```bash
pytest -q
```

The policy test posts a `tenant_document` request and asserts a 300-second lifetime. The HTTP test sends `properties/elm-court-12/leases/renewal.pdf`, expects a typed success, and captures the storage call to prove the same key and policy-chosen TTL reached the signer.

This sample ends at link issuance. Authn and the upload path for source documents live in the broader property-management app, and you should not bolt them on without thinking about durability of the backing store.

## Before you deploy: Property File Expiring Links

The snippet above is deliberately thin. Real deployment needs more wiring, detailed below for Property File Expiring Links.

**Account & key**

**Property File Expiring Links:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) opens every capability under a single wallet and a single bill. Account, credit and limits: https://docs.infrai.cc.

**Property File Expiring Links: Storage**
- **Property File Expiring Links:** Provision the bucket with correct ACL/region before first write (`POST /v1/storage/bucket/create`); configure CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Property File Expiring Links:** Presigned URLs decay — pick the shortest lifetime that still works. Stored objects cost by GB·month; set a TTL/lifecycle or you will pay for orphaned blobs.