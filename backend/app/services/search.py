import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Query, Session

from app.models import Book
from app.services.vector_store import semantic_search


@dataclass
class SearchCriteria:
    original: str
    language: str | None = None
    available_only: bool = False
    year_from: int | None = None
    year_to: int | None = None
    pages_max: int | None = None
    reading_level: str | None = None
    genre: str | None = None
    category: str | None = None
    author: str | None = None
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
    exact = not (q and q.strip())

    if q and q.strip():
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
        # Reading level inferred from natural language should guide semantic ranking,
        # not exclude books whose indexed metadata uses a different level label.
        if extra.get("reading_level"):
            vector_filters["reading_level"] = reading_level

        vector_results = semantic_search(
            query_text=q.strip(),
            limit=50,
            filters=vector_filters,
        )

        if vector_results:
            top_score = vector_results[0][1]
            cutoff = max(0.50, top_score * 0.83) if top_score >= 0.50 else 0.40
            relevant_results = [result for result in vector_results if result[1] >= cutoff]
            showing_related = not relevant_results
            if showing_related:
                relevant_results = vector_results

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
            exact = not showing_related and top_score >= 0.52

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