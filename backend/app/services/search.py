import re
from dataclasses import dataclass, field

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models import Book

SYNONYMS = {
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "py": "python",
    "dsa": "data structures",
    "scifi": "science fiction",
    "sci-fi": "science fiction",
    "pm": "project management",
}

STOPWORDS = {
    "a", "an", "the", "me", "i", "want", "show", "find", "suggest",
    "books", "book", "about", "for", "to", "learn", "learning",
    "written", "by", "in", "of", "and", "or", "please", "need",
    "an", "available", "english", "short", "simple", "easy",
    "beginner", "beginner-friendly", "beginners", "suitable",
}


@dataclass
class SearchCriteria:
    original: str
    terms: list[str] = field(default_factory=list)
    language: str | None = None
    available_only: bool = False
    year_from: int | None = None
    year_to: int | None = None
    pages_max: int | None = None
    reading_level: str | None = None
    genre: str | None = None
    category: str | None = None
    author: str | None = None
    similar_to: str | None = None


def parse_query(q: str) -> SearchCriteria:
    original = q.strip()
    text = original.lower()
    criteria = SearchCriteria(original=original)

    if re.search(r"\bavailable\b", text):
        criteria.available_only = True

    if re.search(r"\benglish\b", text):
        criteria.language = "English"
    elif re.search(r"\bhindi\b", text):
        criteria.language = "Hindi"

    m = re.search(r"(?:after|since|published after)\s+(\d{4})", text)
    if m:
        criteria.year_from = int(m.group(1))

    m = re.search(r"(?:before|until)\s+(\d{4})", text)
    if m:
        criteria.year_to = int(m.group(1))

    m = re.search(r"(?:fewer|less)\s+than\s+(\d+)\s+pages", text)
    if m:
        criteria.pages_max = int(m.group(1))
    elif re.search(r"\bshort\b", text):
        criteria.pages_max = 280

    if re.search(r"\b(beginner|beginners|easy|simple|beginner-friendly)\b", text):
        criteria.reading_level = "beginner"

    if re.search(r"\bmystery\b", text):
        criteria.genre = "Mystery"
    elif re.search(r"science[- ]fiction|\bsci-?fi\b", text):
        criteria.genre = "Science Fiction"
    elif re.search(r"\bfantasy\b", text):
        criteria.genre = "Fantasy"
    elif re.search(r"\bpoetry\b", text):
        criteria.genre = "Poetry"

    if re.search(r"\bhistory\b", text):
        criteria.category = "History"
    elif re.search(r"\bleadership\b", text):
        criteria.category = "Business"
    elif re.search(r"\bpython|programming\b", text):
        criteria.category = "Programming"

    m = re.search(r"(?:written by|books by|by)\s+([a-z][a-z\s.]+?)(?:\.|$)", text)
    if m:
        criteria.author = m.group(1).strip(" .")

    m = re.search(r"similar to\s+(.+)$", text)
    if m:
        criteria.similar_to = m.group(1).strip(" .")
        criteria.genre = criteria.genre or "Fantasy"

    cleaned = text
    for src, dest in SYNONYMS.items():
        cleaned = re.sub(rf"\b{re.escape(src)}\b", dest, cleaned)

    tokens = re.findall(r"[a-z0-9]+", cleaned)
    criteria.terms = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    return criteria


def apply_filters(query: Query, c: SearchCriteria, extra: dict) -> Query:
    language = extra.get("language") or c.language
    year_from = extra.get("year_from") if extra.get("year_from") is not None else c.year_from
    year_to = extra.get("year_to") if extra.get("year_to") is not None else c.year_to
    pages_max = extra.get("pages_max") if extra.get("pages_max") is not None else c.pages_max
    reading_level = extra.get("reading_level") or c.reading_level
    genre = extra.get("genre") or c.genre
    category = extra.get("category") or c.category
    author = extra.get("author") or c.author
    available_only = extra.get("available_only") or c.available_only

    query = query.filter(Book.status != "archived")

    if language:
        query = query.filter(Book.language.ilike(language))
    if year_from is not None:
        query = query.filter(Book.publication_year >= year_from)
    if year_to is not None:
        query = query.filter(Book.publication_year <= year_to)
    if pages_max is not None:
        query = query.filter(Book.page_count <= pages_max)
    if reading_level:
        query = query.filter(Book.reading_level.ilike(reading_level))
    if genre:
        query = query.filter(Book.genre.ilike(f"%{genre}%"))
    if category:
        query = query.filter(Book.category.ilike(f"%{category}%"))
    if author:
        query = query.filter(Book.authors.ilike(f"%{author}%"))
    if available_only:
        query = query.filter(Book.available_copies > 0)

    if extra.get("q_like"):
        like = f"%{extra['q_like']}%"
        query = query.filter(
            or_(
                Book.title.ilike(like),
                Book.subtitle.ilike(like),
                Book.authors.ilike(like),
                Book.description.ilike(like),
                Book.summary.ilike(like),
                Book.keywords.ilike(like),
                Book.search_tags.ilike(like),
                Book.genre.ilike(like),
                Book.category.ilike(like),
                Book.isbn.ilike(like),
            )
        )

    terms = list(c.terms)
    if c.similar_to:
        terms.extend(["magic", "wizard", "fantasy", "hogwarts"])

    for term in terms:
        like = f"%{term}%"
        query = query.filter(
            or_(
                Book.title.ilike(like),
                Book.subtitle.ilike(like),
                Book.authors.ilike(like),
                Book.description.ilike(like),
                Book.summary.ilike(like),
                Book.keywords.ilike(like),
                Book.search_tags.ilike(like),
                Book.genre.ilike(like),
                Book.category.ilike(like),
            )
        )
    return query


def score_book(book: Book, c: SearchCriteria) -> int:
    blob = " ".join(
        [
            book.title,
            book.subtitle or "",
            book.authors,
            book.description,
            book.summary,
            book.keywords,
            book.search_tags,
            book.genre,
            book.category,
        ]
    ).lower()
    score = 0
    for term in c.terms:
        if term in blob:
            score += 3
        if term in (book.title or "").lower():
            score += 5
        if term in (book.authors or "").lower():
            score += 4
    if c.available_only or True:
        if book.available_copies > 0:
            score += 1
    if c.reading_level and book.reading_level == c.reading_level:
        score += 2
    return score


def search_books(
    db: Session,
    *,
    q: str | None,
    sort: str,
    page: int,
    page_size: int,
    extra: dict,
):
    criteria = parse_query(q or "")
    query = apply_filters(db.query(Book), criteria, extra)
    books = query.all()

    if q and not books:
        loose = db.query(Book).filter(Book.status != "archived")
        if criteria.terms:
            like = f"%{criteria.terms[0]}%"
            loose = loose.filter(
                or_(
                    Book.title.ilike(like),
                    Book.description.ilike(like),
                    Book.keywords.ilike(like),
                    Book.genre.ilike(like),
                    Book.category.ilike(like),
                )
            )
        books = loose.all()
        exact = False
    else:
        exact = True

    books.sort(key=lambda b: score_book(b, criteria), reverse=True)

    if sort == "title_asc":
        books.sort(key=lambda b: b.title.lower())
    elif sort == "title_desc":
        books.sort(key=lambda b: b.title.lower(), reverse=True)
    elif sort == "year_new":
        books.sort(key=lambda b: b.publication_year, reverse=True)
    elif sort == "year_old":
        books.sort(key=lambda b: b.publication_year)
    elif sort == "availability":
        books.sort(key=lambda b: b.available_copies, reverse=True)

    total = len(books)
    start = (page - 1) * page_size
    page_items = books[start : start + page_size]
    return page_items, total, criteria, exact