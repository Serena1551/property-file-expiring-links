"""Property-specific policy for private document downloads."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class FilePurpose(StrEnum):
    MAINTENANCE_REQUEST = "maintenance_request"
    TENANT_DOCUMENT = "tenant_document"
    INSPECTION_REMINDER = "inspection_reminder"


class DownloadRequest(BaseModel):
    property_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    file_key: str = Field(min_length=1, max_length=500)
    purpose: FilePurpose
    urgent: bool = False
    inspection_due_days: int | None = Field(default=None, ge=0, le=365)

    @model_validator(mode="after")
    def inspection_context_matches_purpose(self) -> "DownloadRequest":
        if self.purpose is FilePurpose.INSPECTION_REMINDER and self.inspection_due_days is None:
            raise ValueError("inspection_due_days is required for an inspection reminder")
        if self.purpose is not FilePurpose.INSPECTION_REMINDER and self.inspection_due_days is not None:
            raise ValueError("inspection_due_days only belongs to an inspection reminder")
        return self


class DownloadGrant(BaseModel):
    property_id: str
    purpose: FilePurpose
    download_url: str
    expires_seconds: int


def choose_expiry(request: DownloadRequest) -> int:
    """Keep sensitive tenant records shortest; allow routine inspection packets longer."""
    if request.purpose is FilePurpose.TENANT_DOCUMENT:
        return 300
    if request.purpose is FilePurpose.MAINTENANCE_REQUEST:
        return 300 if request.urgent else 900
    return 900 if request.inspection_due_days == 0 else 1800
