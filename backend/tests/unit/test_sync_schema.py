from uuid import uuid4

import pytest
from pydantic import ValidationError

from gophkeeper.api.schemas.sync import PushResultResponse, PushResultStatus


def test_push_result_status_accepts_documented_value():
    result = PushResultResponse(
        id=uuid4(),
        status="applied",
        version=1,
        seq=1,
    )

    assert result.status is PushResultStatus.APPLIED
    assert result.model_dump(mode="json")["status"] == "applied"


def test_push_result_status_rejects_unknown_value():
    with pytest.raises(ValidationError):
        PushResultResponse(
            id=uuid4(),
            status="partial",
            version=1,
            seq=1,
        )


def test_push_result_status_schema_documents_allowed_values():
    schema = PushResultResponse.model_json_schema()

    assert schema["$defs"]["PushResultStatus"]["enum"] == ["applied", "conflict"]
