import pytest

from src.property_media import (
    CropPlan,
    InspectionReminder,
    MaintenanceRequest,
    TenantDocument,
    build_property_record,
)


def test_record_keeps_all_crop_variants_and_property_context():
    plan = CropPlan("front.jpg", ("1:1", "4:3", "16:9"))
    record = build_property_record(
        plan,
        MaintenanceRequest("A-12", "window latch", "high"),
        TenantDocument("t-9", "id", "docs/t-9-id.png"),
        InspectionReminder("A-12", "2026-09-30", "smoke alarm"),
    )
    assert record["crop"]["aspects"] == ["1:1", "4:3", "16:9"]
    assert record["maintenance"]["priority"] == "high"
    assert record["tenant_document"]["object_key"].startswith("docs/")
    assert record["inspection_reminder"]["due_on"] == "2026-09-30"


def test_render_variants_only_requests_crops():
    from src.property_media import render_variants

    class CropClient:
        def __init__(self):
            self.calls = []

        def crop(self, image, aspect):
            self.calls.append((image, aspect))
            return {"data": {"aspect": aspect}}

    client = CropClient()
    plan = CropPlan("front.jpg", ("1:1", "4:3", "16:9"))
    outputs = render_variants(client, plan)
    assert client.calls == [("front.jpg", aspect) for aspect in plan.aspects]
    assert outputs == [
        {"aspect": aspect, "result": {"aspect": aspect}}
        for aspect in plan.aspects
    ]
