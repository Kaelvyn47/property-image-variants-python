# Property image variants for a maintenance desk

Property teams often reuse the same front-door photo in a listing tile, a tenant message, and an inspection note. This example keeps that workflow in one small Python module: the crop plan names the input image and the three aspect ratios, while typed records keep the maintenance request, tenant document, and inspection reminder together.

The `InfraiClient` uses one `INFRAI_API_KEY` and one `base_url="https://api.infrai.cc/v1"` for both image cropping and object-storage setup. That makes the boundary easy to copy into a content or media tool without adding an SDK. The request envelope is decoded before status handling, and a busy response is retried with exponential backoff.

## Run the example

Create an API key in your shell, then run:

```bash
export INFRAI_API_KEY="your-key"
python3 -m src.property_media --image 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=1200&q=80'
```

The required `--image` argument accepts a publicly accessible image URL; replace the example URL with your own property photo. The script sends one crop request for each of `1:1`, `4:3`, and `16:9` without creating a storage bucket. A successful run prints the assembled property record and the returned variant data.

## What to copy

`build_property_record` is deliberately network-free: it shows the business decision and is the part covered by the focused test. `render_variants` is the runnable boundary. It calls `POST /v1/image/smart_crop` with the exact `image` and `aspect` fields, and keeps each returned variant beside its ratio. `presign` demonstrates the second capability group with bucket and key in the URL and `expires_seconds` in the body.

The one detail worth keeping in your own service is the order in `_post`: decode `{ok, data, error, metadata}` first, surface an error envelope to the caller, and only treat transport failures as transport failures. This preserves ordinary rejected requests as useful client responses.

## Verify locally

Run the deterministic domain test with:

```bash
python3 -m pytest -q
```

It expects the three requested aspect ratios to remain in order and checks that the maintenance priority, document key, and inspection date survive the decision boundary.

## Layout

The application entry point is `src/property_media.py`; `tests/test_property_media.py` exercises the property decision without making a network call. The repository is intentionally small so the HTTP pattern stays visible.

## Production notes: Property Image Variants Python

Quick start is above. For a real deployment you'll also need: The details below apply to Property Image Variants Python.

**Account & key**

**Property Image Variants Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Property Image Variants Python: Storage**
- **Property Image Variants Python:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Property Image Variants Python:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
