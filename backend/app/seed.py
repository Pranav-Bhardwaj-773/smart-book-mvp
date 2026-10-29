import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import bcrypt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AppSettings, Book, Notification, Rental, User

logger = logging.getLogger(__name__)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _status(total: int, available: int, book_status: str | None = None) -> str:
    raw = (book_status or "").strip().lower()
    if raw in ("archived", "lost"):
        return "archived"
    if available <= 0 or raw in ("fully rented", "under maintenance"):
        return "unavailable"
    if available < total:
        return "partially_available"
    return "available"


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def get_books_json_path() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "books.json",
        Path.cwd() / "books.json",
        Path.cwd() / "backend" / "books.json",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return candidates[0]


def load_books_from_json(
    db: Session, force: bool = False, json_path: Path | str | None = None
) -> int:
    """
    Load books from books.json into the DB table.
    Auto-increments id starting from 1 (leaves id unset on Book instances).
    """
    path = Path(json_path) if json_path else get_books_json_path()
    if not path.exists():
        logger.error(f"books.json not found at {path}")
        print(f"Error: books.json not found at {path}")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        books_data = json.load(f)

    if force:
        logger.info("Clearing existing books table for fresh reseed.")
        db.query(Book).delete()
        db.commit()

    book_objects = []
    for item in books_data:
        isbn = str(item.get("isbn") or "").strip()
        title = str(item.get("title") or "").strip()
        subtitle = item.get("subtitle")

        authors_raw = item.get("authors", [])
        if isinstance(authors_raw, list):
            authors = ", ".join(authors_raw)
        else:
            authors = str(authors_raw or "")

        description = str(item.get("description") or "")
        summary = str(item.get("summary") or "")
        category = str(item.get("category") or "General")
        genre = str(item.get("genre") or "General")
        publisher = str(item.get("publisher") or "Unknown")
        publication_year = int(item.get("publicationYear") or 2024)
        language = str(item.get("language") or "English")
        edition = str(item.get("edition") or "1st")
        page_count = int(item.get("numberOfPages") or 100)
        cover_url = item.get("coverImage") or f"https://picsum.photos/seed/{isbn}/240/360"

        kw_raw = item.get("keywords", [])
        keywords = ", ".join(kw_raw) if isinstance(kw_raw, list) else str(kw_raw or "")

        tags_raw = item.get("searchTags", [])
        search_tags = ", ".join(tags_raw) if isinstance(tags_raw, list) else str(tags_raw or "")

        reading_level = str(item.get("readingLevel") or "general").lower()
        total_copies = int(item.get("totalCopies") or 1)
        avail_raw = item.get("availableCopies")
        available_copies = int(avail_raw) if avail_raw is not None else total_copies
        if available_copies > total_copies:
            available_copies = total_copies
        if available_copies < 0:
            available_copies = 0

        book_status = item.get("bookStatus")
        status = _status(total_copies, available_copies, book_status)

        created_at = _parse_dt(item.get("createdDate"))
        updated_at = _parse_dt(item.get("updatedDate"))

        book = Book(
            isbn=isbn,
            title=title,
            subtitle=subtitle,
            authors=authors,
            description=description,
            summary=summary,
            category=category,
            genre=genre,
            language=language,
            publisher=publisher,
            publication_year=publication_year,
            edition=edition,
            page_count=page_count,
            keywords=keywords,
            search_tags=search_tags,
            reading_level=reading_level,
            cover_url=cover_url,
            total_copies=total_copies,
            available_copies=available_copies,
            status=status,
        )
        if created_at:
            book.created_at = created_at
        if updated_at:
            book.updated_at = updated_at

        book_objects.append(book)

    db.add_all(book_objects)
    db.commit()
    logger.info(f"Successfully loaded {len(book_objects)} books into database.")
    return len(book_objects)


def seed_if_empty(db: Session, force_books: bool = False) -> None:
    """Ensure default admin, settings, and seed books from books.json."""
    if db.query(User).first() is None:
        db.add(
            User(
                full_name="Library Admin",
                email="admin@smartbook.local",
                password_hash=hash_password("Admin123!"),
                phone="9990001111",
                role="admin",
                status="active",
            )
        )
        db.commit()

    if db.query(AppSettings).first() is None:
        db.add(AppSettings(default_rental_days=settings.default_rental_days))
        db.commit()

    if force_books or db.query(Book).count() == 0:
        load_books_from_json(db, force=force_books)


if __name__ == "__main__":
    from app.database import SessionLocal

    parser = argparse.ArgumentParser(description="Seed database from books.json")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear existing books and reload all books from books.json with auto-increment ID",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Also re-index Qdrant vector database after seeding",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        seed_if_empty(session, force_books=args.force)
        count = session.query(Book).count()
        print(f"Database seeded successfully. Total books in DB: {count}")

        if args.index:
            from app.services.vector_store import index_books_from_db

            print("Re-indexing books into Qdrant vector DB...")
            indexed = index_books_from_db(session, recreate=True)
            print(f"Indexed {indexed} books into Qdrant vector DB.")
    finally:
        session.close()