from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OCRLine(BaseModel):
    text: str
    confidence: float
    box: list | None = None
    page: int = 1


class OCRResponse(BaseModel):
    upload_token: str
    filename: str
    raw_text: str
    lines: list[OCRLine]
    suggested: dict


class OrderCreate(BaseModel):
    upload_token: str
    source_filename: str = Field(default="upload", max_length=255)
    order_number: str = Field(min_length=1, max_length=100)
    customer_name: str = Field(min_length=1, max_length=200)
    order_date: date | None = None
    total_amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="TWD", max_length=10)
    notes: str | None = None
    raw_text: str = ""
    extracted_data: dict = Field(default_factory=dict)


class OrderUpdate(BaseModel):
    order_number: str | None = Field(default=None, min_length=1, max_length=100)
    customer_name: str | None = Field(default=None, min_length=1, max_length=200)
    order_date: date | None = None
    total_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    notes: str | None = None
    status: str | None = None
    extracted_data: dict | None = None


class OwnerOut(BaseModel):
    id: str
    email: str
    name: str


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_number: str
    customer_name: str
    order_date: date | None
    total_amount: Decimal | None
    currency: str
    status: str
    notes: str | None
    source_filename: str
    raw_text: str
    extracted_data: dict
    created_at: datetime
    updated_at: datetime
    owner: OwnerOut


class OrderList(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int


class DashboardStats(BaseModel):
    total_orders: int
    this_month: int
    total_amount: Decimal
    pending_review: int
