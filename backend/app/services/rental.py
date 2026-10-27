from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import AppSettings, Book, Rental, User

ACTIVE = ("active", "overdue")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def mark_overdue(db: Session) -> None:
    db.query(Rental).filter(Rental.status == "active", Rental.due_at < _now()).update(
        {"status": "overdue"}, synchronize_session=False
    )


def _book_status(total: int, available: int, current: str) -> str:
    if current == "archived":
        return "archived"
    if available <= 0:
        return "unavailable"
    if available < total:
        return "partially_available"
    return "available"


def _duration(db: Session) -> int:
    row = db.query(AppSettings).first()
    return row.default_rental_days if row else settings.default_rental_days


def _active_count(db: Session, user_id: int) -> int:
    return (
        db.query(Rental)
        .filter(Rental.user_id == user_id, Rental.status.in_(ACTIVE))
        .count()
    )


def _rental_out(rental: Rental) -> dict:
    now = _now()
    days_remaining = None
    days_overdue = None
    if rental.status == "active":
        days_remaining = max(0, (rental.due_at - now).days)
    elif rental.status == "overdue":
        days_overdue = max(0, (now - rental.due_at).days)
    return {
        "id": rental.id,
        "book_id": rental.book_id,
        "book_title": rental.book.title,
        "authors": rental.book.authors,
        "start_at": rental.start_at,
        "duration_days": rental.duration_days,
        "due_at": rental.due_at,
        "returned_at": rental.returned_at,
        "status": rental.status,
        "days_remaining": days_remaining,
        "days_overdue": days_overdue,
    }


def capacity_message(active_count: int, max_allowed: int) -> str:
    remaining = max(0, max_allowed - active_count)
    if active_count >= max_allowed:
        return f"Active rentals: {active_count} of {max_allowed}. Return a book to rent another one."
    if remaining == 1:
        return f"Active rentals: {active_count} of {max_allowed}. You can rent 1 more book."
    return f"Active rentals: {active_count} of {max_allowed}. You can rent {remaining} more books."


def rent_book(db: Session, user: User, book_id: int) -> Rental:
    mark_overdue(db)

    

    existing = (
        db.query(Rental)
        .filter(
            Rental.user_id == user.id,
            Rental.book_id == book_id,
            Rental.status.in_(ACTIVE),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You already have an active rental for this book.",
        )

    if _active_count(db, user.id) >= settings.max_active_rentals:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You already have two active rentals. Please return one of your books before renting another.",
        )

    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")
    if book.status == "archived":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This book is no longer available for rental.",
        )

    result = db.execute(
        update(Book)
        .where(
            Book.id == book_id,
            Book.status != "archived",
            Book.available_copies > 0,
        )
        .values(available_copies=Book.available_copies - 1)
    )
    if result.rowcount != 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This book was rented by another user and is no longer available."
            if book.available_copies > 0
            else "This book is currently unavailable.",
        )

    db.refresh(book)
    book.status = _book_status(book.total_copies, book.available_copies, book.status)

    days = _duration(db)
    now = _now()
    rental = Rental(
        user_id=user.id,
        book_id=book_id,
        start_at=now,
        duration_days=days,
        due_at=now + timedelta(days=days),
        status="active",
    )
    db.add(rental)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You already have an active rental for this book.",
        )
    db.refresh(rental)
    return rental


def return_book(db: Session, user: User, rental_id: int) -> Rental:
    mark_overdue(db)
    rental = db.get(Rental, rental_id)
    if rental is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "The requested rental record could not be found.",
        )
    if rental.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "The requested rental record could not be found.",
        )
    if rental.status not in ACTIVE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This book has already been returned or cannot be returned.",
        )

    rental.status = "returned"
    rental.returned_at = _now()

    result = db.execute(
        update(Book)
        .where(Book.id == rental.book_id, Book.available_copies < Book.total_copies)
        .values(available_copies=Book.available_copies + 1)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This book has already been returned or cannot be returned.",
        )

    book = db.get(Book, rental.book_id)
    if book and book.status != "archived":
        book.status = _book_status(book.total_copies, book.available_copies, book.status)

    db.commit()
    db.refresh(rental)
    return rental


def dashboard(db: Session, user: User) -> dict:
    mark_overdue(db)
    db.commit()

    rows = (
        db.query(Rental)
        .options(joinedload(Rental.book))
        .filter(Rental.user_id == user.id)
        .order_by(Rental.created_at.desc())
        .all()
    )
    current = [_rental_out(r) for r in rows if r.status in ACTIVE]
    history = [_rental_out(r) for r in rows if r.status not in ACTIVE]
    active_count = len(current)
    max_allowed = settings.max_active_rentals
    remaining = max(0, max_allowed - active_count)
    return {
        "full_name": user.full_name,
        "active_count": active_count,
        "max_allowed": max_allowed,
        "remaining": remaining,
        "capacity_message": capacity_message(active_count, max_allowed),
        "current": current,
        "history": history,
    }