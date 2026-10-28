import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models import Book
from app.services.vector_store import semantic_search

logger = logging.getLogger(__name__)

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
    "available", "english", "short", "simple", "easy",
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
    scores: dict[int, float] = field(default_factory=dict)
    rag_context: list[str] = field(default_factory=list)


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


def apply_db_filters(query: Query, c: SearchCriteria, extra: dict) -> Query:
    """Apply standard relational DB filters."""
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

    return query


def search_books(
    db: Session,
    *,
    q: str | None,
    sort: str,
    page: int,
    page_size: int,
    extra: dict,
):
    """
    Semantic RAG search using Qdrant Vector Database.
    Reads matching vectors using cosine similarity, enriches with database models,
    and applies relevant filtering and sorting.
    """
    criteria = parse_query(q or "")

    language = extra.get("language") or criteria.language
    year_from = extra.get("year_from") if extra.get("year_from") is not None else criteria.year_from
    year_to = extra.get("year_to") if extra.get("year_to") is not None else criteria.year_to
    pages_max = extra.get("pages_max") if extra.get("pages_max") is not None else criteria.pages_max
    reading_level = extra.get("reading_level") or criteria.reading_level
    genre = extra.get("genre") or criteria.genre
    category = extra.get("category") or criteria.category
    author = extra.get("author") or criteria.author
    available_only = extra.get("available_only") or criteria.available_only

    books: list[Book] = []
    exact = True

    if q and q.strip():
        # Build semantic search query with any detected semantic expansion
        semantic_query = q.strip()
        if criteria.similar_to:
            semantic_query = f"{semantic_query} magic fantasy adventure similar to {criteria.similar_to}"

        vector_filters = {}
        if language:
            vector_filters["language"] = language
        if available_only:
            vector_filters["available_only"] = True
        if year_from is not None:
            vector_filters["year_from"] = year_from
        if year_to is not None:
            vector_filters["year_to"] = year_to
        if pages_max is not None:
            vector_filters["pages_max"] = pages_max
        if reading_level:
            vector_filters["reading_level"] = reading_level

        # Query Qdrant Vector Database
        try:
            vector_results = semantic_search(
                query_text=semantic_query,
                limit=50,
                filters=vector_filters,
            )
        except Exception as e:
            logger.error(f"Error querying Qdrant vector store: {e}")
            vector_results = []

        if vector_results:
            top_score = vector_results[0][1]
            # Dynamic cutoff to retain relevant semantic matches and exclude irrelevant tail
            cutoff = max(0.50, top_score * 0.83) if top_score >= 0.50 else 0.40
            relevant_results = [r for r in vector_results if r[1] >= cutoff]

            book_scores: dict[int, float] = {}
            ordered_ids: list[int] = []
            for b_id, score, payload in relevant_results:
                book_scores[b_id] = score
                ordered_ids.append(b_id)
                summary_text = payload.get("summary") or payload.get("title") or ""
                criteria.rag_context.append(f"[{payload.get('title')}]: {summary_text}")

            criteria.scores = book_scores

            # Fetch books from database
            retrieved_books = (
                db.query(Book)
                .filter(Book.id.in_(ordered_ids), Book.status != "archived")
                .all()
            )
            book_map = {b.id: b for b in retrieved_books}

            # Preserve semantic relevance rank
            filtered_books: list[Book] = []
            for b_id in ordered_ids:
                if b_id in book_map:
                    b = book_map[b_id]
                    # Post-filter if author, genre, or category was strictly specified
                    if author and author.lower() not in (b.authors or "").lower():
                        continue
                    if genre and genre.lower() not in (b.genre or "").lower():
                        continue
                    if category and category.lower() not in (b.category or "").lower():
                        continue
                    filtered_books.append(b)

            books = filtered_books
            exact = top_score >= 0.52

        # Fallback to database query if vector search returned nothing
        if not books:
            logger.info("Semantic vector search returned 0 results, falling back to database query")
            fallback_query = apply_db_filters(db.query(Book), criteria, extra)
            if criteria.terms:
                like_clauses = [
                    or_(
                        Book.title.ilike(f"%{term}%"),
                        Book.description.ilike(f"%{term}%"),
                        Book.summary.ilike(f"%{term}%"),
                        Book.keywords.ilike(f"%{term}%"),
                        Book.genre.ilike(f"%{term}%"),
                        Book.category.ilike(f"%{term}%"),
                    )
                    for term in criteria.terms
                ]
                fallback_query = fallback_query.filter(or_(*like_clauses))
            books = fallback_query.all()
            exact = False
    else:
        # No query string: standard catalog browsing with applied filters
        query = apply_db_filters(db.query(Book), criteria, extra)
        books = query.all()
        exact = True

    # Sorting
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
    elif sort == "relevance" and criteria.scores:
        # Default relevance sorts by semantic vector score descending
        books.sort(key=lambda b: criteria.scores.get(b.id, 0.0), reverse=True)

    total = len(books)
    start = (page - 1) * page_size
    page_items = books[start : start + page_size]
    return page_items, total, criteria, exact