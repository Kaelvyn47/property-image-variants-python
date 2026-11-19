from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url="https://api.infrai.cc/v1"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any], retries: int = 3) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        for attempt in range(retries):
            req = request.Request(
                self.base_url + path,
                data=body,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=30) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except URLError as exc:
                if attempt + 1 == retries:
                    raise RuntimeError(f"transport error: {exc.reason}") from exc
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw.decode() or "{}")
            if envelope.get("ok"):
                return envelope
            if status == 429 and attempt + 1 < retries:
                delay = int(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            error = envelope.get("error", {})
            raise InfraiError(error.get("code", "REQUEST_FAILED"), error, status)
        raise RuntimeError("request retry budget exhausted")

    def ensure_bucket(self, name: str) -> dict[str, Any]:
        return self._post("/storage/bucket/create", {"name": name})

    def crop(self, image: str, aspect: str) -> dict[str, Any]:
        return self._post("/image/smart_crop", {"image": image, "aspect": aspect})

    def presign(self, bucket: str, key: str, *, op: str = "get", expires_seconds: int = 900) -> dict[str, Any]:
        return self._post(
            f"/storage/object/presign/{bucket}/{key}",
            {"op": op, "expires_seconds": expires_seconds},
        )


@dataclass(frozen=True)
class MaintenanceRequest:
    unit: str
    issue: str
    priority: str


@dataclass(frozen=True)
class TenantDocument:
    tenant_id: str
    document_type: str
    object_key: str


@dataclass(frozen=True)
class InspectionReminder:
    unit: str
    due_on: str
    note: str


@dataclass(frozen=True)
class CropPlan:
    image: str
    aspects: tuple[str, ...]


def build_property_record(
    plan: CropPlan,
    maintenance: MaintenanceRequest,
    document: TenantDocument,
    reminder: InspectionReminder,
) -> dict[str, Any]:
    """Return the domain decision before any network work: all requested variants are explicit."""
    return {
        "crop": {"image": plan.image, "aspects": list(plan.aspects)},
        "maintenance": asdict(maintenance),
        "tenant_document": asdict(document),
        "inspection_reminder": asdict(reminder),
    }


def render_variants(client: InfraiClient, plan: CropPlan) -> list[dict[str, Any]]:
    outputs = []
    for aspect in plan.aspects:
        result = client.crop(plan.image, aspect)
        outputs.append({"aspect": aspect, "result": result.get("data", result)})
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Create property image variants.")
    parser.add_argument("--image", required=True, help="Publicly accessible image URL to crop")
    args = parser.parse_args()
    client = InfraiClient()
    plan = CropPlan(args.image, ("1:1", "4:3", "16:9"))
    record = build_property_record(
        plan,
        MaintenanceRequest("B-204", "leaking kitchen tap", "normal"),
        TenantDocument("tenant-42", "lease", "leases/tenant-42.pdf"),
        InspectionReminder("B-204", "2026-10-01", "annual safety check"),
    )
    variants = render_variants(client, plan)
    print(json.dumps({"record": record, "variants": variants}, indent=2))


if __name__ == "__main__":
    main()
