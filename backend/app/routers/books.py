from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book
from app.schemas import BookListOut, BookOut
from app.services.search import search_books

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=BookListOut)
def list_books(
    q: str | None = Query(default=None, description="Natural-language search"),
    sort: str = Query(default="relevance"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    language: str | None = None,
    genre: str | None = None,
    category: str | None = None,
    author: str | None = None,
    reading_level: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    pages_max: int | None = None,
    available_only: bool = False,
    db: Session = Depends(get_db),
):
    extra = {
        "language": language,
        "genre": genre,
        "category": category,
        "author": author,
        "reading_level": reading_level,
        "year_from": year_from,
        "year_to": year_to,
        "pages_max": pages_max,
        "available_only": available_only,
    }
    items, total, criteria, exact = search_books(
        db, q=q, sort=sort, page=page, page_size=page_size, extra=extra
    )
    message = None
    if q and not items:
        message = "No exact matching books were found. Try changing your search or removing some filters."
    elif q and not exact:
        message = "No exact matching books were found. Showing related books."

    return BookListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        query=criteria.original or q,
        exact_match=exact,
        message=message,
    )


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book