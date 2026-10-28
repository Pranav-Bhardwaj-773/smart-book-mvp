from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_admin
from app.models import Book, Rental, User
from app.schemas import (
    AdminRentalOut,
    BookOut,
    BookCreate,
    InventoryUpdate,
    RentalOut,
    UserOut,
    UserStatusUpdate,
)
from sqlalchemy.exc import IntegrityError
from app.services.rental import _book_status, _rental_out, return_book

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    q: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (User.full_name.ilike(like)) | (User.email.ilike(like))
        )
    return query.order_by(User.id).all()


@router.patch("/users/{user_id}/status", response_model=UserOut)
def set_user_status(
    user_id: int,
    body: UserStatusUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if body.status not in ("active", "inactive", "blocked"):
        raise HTTPException(400, "Invalid status")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if user.role == "admin" and body.status != "active":
        raise HTTPException(400, "Do not block the admin account in the MVP")
    user.status = body.status
    db.commit()
    db.refresh(user)
    return user


@router.get("/books", response_model=list[BookOut])
def list_books_admin(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(Book).order_by(Book.id).all()


@router.post("/books/{book_id}/archive", response_model=BookOut)
def archive_book(
    book_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    book.status = "archived"
    db.commit()
    db.refresh(book)
    return book


@router.post("/books/{book_id}/restore", response_model=BookOut)
def restore_book(
    book_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    book.status = _book_status(book.total_copies, book.available_copies, "available")
    db.commit()
    db.refresh(book)
    return book


@router.post("/books/{book_id}/inventory", response_model=BookOut)
def change_inventory(
    book_id: int,
    body: InventoryUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    rented = book.total_copies - book.available_copies
    new_total = book.total_copies + body.delta
    new_available = book.available_copies + body.delta
    if new_total < rented or new_available < 0 or new_total < 0:
        raise HTTPException(
            400,
            "Inventory change would break copy counts (available cannot go below 0 or above total).",
        )
    book.total_copies = new_total
    book.available_copies = new_available
    if book.status != "archived":
        book.status = _book_status(new_total, new_available, book.status)
    db.commit()
    db.refresh(book)
    return book


@router.get("/rentals")
def list_rentals(
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Rental).options(joinedload(Rental.book), joinedload(Rental.user))
    if status_filter:
        query = query.filter(Rental.status == status_filter)
    rows = query.order_by(Rental.id.desc()).limit(200).all()
    out = []
    for r in rows:
        item = _rental_out(r)
        item["user_id"] = r.user_id
        item["user_email"] = r.user.email
        item["user_name"] = r.user.full_name
        out.append(item)
    return out


@router.post("/rentals/{rental_id}/return")
def admin_return(
    rental_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rental = return_book(db, admin, rental_id)
    rental = (
        db.query(Rental)
        .options(joinedload(Rental.book), joinedload(Rental.user))
        .filter(Rental.id == rental.id)
        .one()
    )
    return _rental_out(rental)


@router.get("/stats")
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return {
        "books": db.query(func.count(Book.id)).scalar(),
        "users": db.query(func.count(User.id)).scalar(),
        "active_rentals": db.query(func.count(Rental.id))
        .filter(Rental.status.in_(("active", "overdue")))
        .scalar(),
        "overdue_rentals": db.query(func.count(Rental.id))
        .filter(Rental.status == "overdue")
        .scalar(),
    }

@router.post("/books", response_model=BookOut, status_code=201)
def add_book(
    body: BookCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = body.model_dump()
    cover = data.pop("cover_url") or f"https://picsum.photos/seed/{body.isbn}/240/360"
    book = Book(
        **data,
        available_copies=body.total_copies,
        status="available",
        cover_url=cover,
    )
    db.add(book)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "ISBN already exists")
    db.refresh(book)
    return book