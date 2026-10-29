from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | inactive | blocked
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    rentals: Mapped[list["Rental"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("total_copies >= 0", name="ck_book_total_nonneg"),
        CheckConstraint("available_copies >= 0", name="ck_book_available_nonneg"),
        CheckConstraint(
            "available_copies <= total_copies", name="ck_book_available_lte_total"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isbn: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authors: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), index=True)
    genre: Mapped[str] = mapped_column(String(80), index=True)
    language: Mapped[str] = mapped_column(String(40), index=True)
    publisher: Mapped[str] = mapped_column(String(120))
    publication_year: Mapped[int] = mapped_column(Integer, index=True)
    edition: Mapped[str | None] = mapped_column(String(40), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer)
    keywords: Mapped[str] = mapped_column(Text, default="")
    search_tags: Mapped[str] = mapped_column(Text, default="")
    reading_level: Mapped[str] = mapped_column(String(40), default="general")
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_copies: Mapped[int] = mapped_column(Integer, default=1)
    available_copies: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="available", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    rentals: Mapped[list["Rental"]] = relationship(back_populates="book")


class Rental(Base):
    __tablename__ = "rentals"
    __table_args__ = (
        Index(
            "ux_active_rental",
            "user_id",
            "book_id",
            unique=True,
            sqlite_where=text("status IN ('active', 'overdue')"),
            postgresql_where=text("status IN ('active', 'overdue')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    duration_days: Mapped[int] = mapped_column(Integer)
    due_at: Mapped[datetime] = mapped_column(DateTime)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="rentals")
    book: Mapped["Book"] = relationship(back_populates="rentals")


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    default_rental_days: Mapped[int] = mapped_column(Integer, default=14)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text)
    related_rental_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="notifications")