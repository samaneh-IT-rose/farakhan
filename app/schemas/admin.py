"""Pydantic response schemas for admin endpoints."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SubmissionFileMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_key: str
    original_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class SubmissionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_code: str
    first_name: str
    last_name: str
    national_code: str
    gender: str
    mobile_number: str
    province_name: str
    county_name: str
    created_at: datetime
    files: list[SubmissionFileMeta]


class SubmissionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_code: str
    first_name: str
    last_name: str
    national_code: str
    gender: str
    birth_date_jalali: str | None
    birth_date_gregorian: date | None
    military_status: str | None
    education_degree: str | None
    education_field: str | None
    license_status: str
    license_description: str | None
    center_ownership: str
    province_id: int
    county_id: int
    province_name: str
    county_name: str
    phone: str | None
    postal_code: str | None
    address: str | None
    mobile_number: str
    individual_rooms: int
    group_rooms: int
    child_rooms: int
    counselors_count: int
    has_waiting_space: bool
    accepts_company_pattern: bool
    has_accessibility: bool
    terms_accepted_at: datetime
    created_at: datetime
    updated_at: datetime | None
    files: list[SubmissionFileMeta]


class PaginatedSubmissions(BaseModel):
    items: list[SubmissionListItem]
    page: int
    page_size: int
    total: int
