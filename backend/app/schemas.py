from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    confirm_password: str
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("email")
    @classmethod
    def email_has_at(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or v.startswith("@") or v.endswith("@"):
            raise ValueError("Invalid email format")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Password and confirm password must match")
        return self


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_has_at(cls, v: str) -> str:
        return v.strip().lower()

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None
    role: str
    status: str
    created_at: datetime | None
    last_login_at: datetime | None

    model_config = {"from_attributes": True}

class BookOut(BaseModel):
    id: int
    isbn: str
    title: str
    subtitle: str | None
    authors: str
    description: str
    summary: str
    category: str
    genre: str
    language: str
    publisher: str
    publication_year: int
    edition: str | None
    page_count: int
    keywords: str
    search_tags: str
    reading_level: str
    cover_url: str | None
    total_copies: int
    available_copies: int
    status: str

    model_config = {"from_attributes": True}


class BookListOut(BaseModel):
    items: list[BookOut]
    total: int
    page: int
    page_size: int
    query: str | None
    exact_match: bool
    message: str | None = None

class RentRequest(BaseModel):
    book_id: int
class RentalOut(BaseModel):
    id: int
    book_id: int
    book_title: str
    authors: str
    start_at: datetime | None
    duration_days: int
    due_at: datetime
    returned_at: datetime | None
    status: str
    days_remaining: int | None = None
    days_overdue: int | None = None
class DashboardOut(BaseModel):
    full_name: str
    active_count: int
    max_allowed: int
    remaining: int
    capacity_message: str
    current: list[RentalOut]
    history: list[RentalOut]