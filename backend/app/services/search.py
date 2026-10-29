import logging
import re
from dataclasses import dataclass, field, replace
from difflib import get_close_matches, SequenceMatcher

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models import Book
from app.services.vector_store import semantic_search

logger = logging.getLogger(__name__)

# Generic words users type in NL queries; requiring them excludes most catalog rows.
_KEYWORD_STOPWORDS = frozenset(
    {
        "book",
        "books",
        "read",
        "reading",
        "find",
        "show",
        "recommend",
        "recommendation",
        "something",
        "anything",
        "looking",
        "want",
        "need",
        "the",
        "and",
        "for",
        "with",
        "about",
    }
)

# High-value catalog topics for typo correction (pykon → python).
_TOPIC_TOKENS = frozenset(
    {
        "python",
        "java",
        "javascript",
        "programming",
        "mystery",
        "fantasy",
        "fiction",
        "history",
        "poetry",
        "classic",
        "romance",
        "science",
        "leadership",
        "business",
    }
)

_FUZZY_CUTOFF = 0.72
_search_vocab_cache: frozenset[str] | None = None


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


def _load_search_vocabulary(db: Session) -> frozenset[str]:
    global _search_vocab_cache
    if _search_vocab_cache is not None:
        return _search_vocab_cache

    terms: set[str] = set(_TOPIC_TOKENS)
    rows = (
        db.query(Book.keywords, Book.category, Book.genre, Book.title, Book.authors)
        .filter(Book.status != "archived")
        .all()
    )
    for keywords, category, genre, title, authors in rows:
        for blob in (keywords, category, genre, title, authors):
            if not blob:
                continue
            for part in re.split(r"[\W,]+", blob.lower()):
                if len(part) >= 3:
                    terms.add(part)
    _search_vocab_cache = frozenset(terms)
    return _search_vocab_cache


def invalidate_search_vocabulary_cache() -> None:
    global _search_vocab_cache
    _search_vocab_cache = None


def _fuzzy_correct_token(token: str, vocabulary: frozenset[str]) -> str:
    if len(token) < 3:
        return token
    pool = list(vocabulary | _TOPIC_TOKENS)
    matches = get_close_matches(token, pool, n=1, cutoff=_FUZZY_CUTOFF)
    return matches[0] if matches else token


def correct_query_spelling(db: Session, query_text: str) -> str:
    """Fix common typos token-by-token (e.g. pykon → python)."""
    vocabulary = _load_search_vocabulary(db)
    words = query_text.split()
    if not words:
        return query_text
    corrected_words: list[str] = []
    changed = False
    for word in words:
        core = re.sub(r"^\W+|\W+$", "", word)
        if len(core) >= 3 and core.lower() not in _KEYWORD_STOPWORDS:
            fix = _fuzzy_correct_token(core.lower(), vocabulary)
            if fix != core.lower():
                changed = True
                prefix = word[: len(word) - len(core) - (0 if word.endswith(core) else 0)]
                # Preserve simple punctuation wrapper
                if word.startswith(core):
                    corrected_words.append(fix + word[len(core) :])
                elif word.endswith(core):
                    corrected_words.append(word[: -len(core)] + fix)
                else:
                    corrected_words.append(fix)
                continue
        corrected_words.append(word)
    return " ".join(corrected_words) if changed else query_text


def _token_near_topic(token: str, topic: str) -> bool:
    return SequenceMatcher(None, token.lower(), topic).ratio() >= _FUZZY_CUTOFF


def parse_query(q: str) -> SearchCriteria:
    original = q.strip()
    text = original.lower()
    criteria = SearchCriteria(original=original)
    tokens = [t for t in re.split(r"\W+", text) if len(t) >= 2]

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
    elif re.search(r"\bpython|programming\b", text) or any(
        _token_near_topic(t, "python") for t in tokens
    ):
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
        if category.lower() == "programming":
            query = query.filter(
                or_(
                    Book.category.ilike("%program%"),
                    Book.genre.ilike("%program%"),
                    Book.keywords.ilike("%python%"),
                    Book.title.ilike("%python%"),
                )
            )
        else:
            query = query.filter(Book.category.ilike(f"%{category}%"))
    if author:
        query = query.filter(Book.authors.ilike(f"%{author}%"))
    if available_only:
        query = query.filter(Book.available_copies > 0)

    return query


def keyword_search(
    db: Session,
    query_text: str,
    criteria: SearchCriteria,
    extra: dict,
) -> list[Book]:
    """Fallback text search when Qdrant is unavailable or returns no hits."""
    text = query_text.strip()
    if not text:
        return []

    # NL phrases like "beginner friendly" hint at audience; catalog uses labels like
    # "general" / "intermediate", so do not hard-filter on inferred reading_level.
    filter_criteria = criteria
    if not extra.get("reading_level") and criteria.reading_level:
        filter_criteria = replace(criteria, reading_level=None)

    terms = [
        t
        for t in re.split(r"\W+", text.lower())
        if len(t) >= 2 and t not in _KEYWORD_STOPWORDS
    ]
    if not terms:
        pattern = f"%{text}%"
        query = apply_db_filters(db.query(Book), filter_criteria, extra).filter(
            or_(
                Book.title.ilike(pattern),
                Book.authors.ilike(pattern),
                Book.summary.ilike(pattern),
                Book.keywords.ilike(pattern),
                Book.genre.ilike(pattern),
                Book.category.ilike(pattern),
            )
        )
        return query.limit(200).all()

    books = _keyword_query(
        db, filter_criteria, extra, terms, match_all_terms=True
    ).limit(200).all()
    if books:
        return books

    books = _keyword_query(
        db, filter_criteria, extra, terms, match_all_terms=False
    ).limit(200).all()
    if books:
        return books

    if criteria.reading_level in ("beginner",):
        return _audience_fallback_query(db, filter_criteria, extra).limit(200).all()

    vocabulary = _load_search_vocabulary(db)
    fuzzy_terms = [_fuzzy_correct_token(t, vocabulary) for t in terms]
    if fuzzy_terms != terms:
        books = _keyword_query(
            db, filter_criteria, extra, fuzzy_terms, match_all_terms=True
        ).limit(200).all()
        if books:
            return books
        books = _keyword_query(
            db, filter_criteria, extra, fuzzy_terms, match_all_terms=False
        ).limit(200).all()
        if books:
            return books

    return []


def _keyword_query(
    db: Session,
    filter_criteria: SearchCriteria,
    extra: dict,
    terms: list[str],
    *,
    match_all_terms: bool,
):
    query = apply_db_filters(db.query(Book), filter_criteria, extra)
    if not terms:
        return query

    term_clauses = []
    for term in terms:
        pattern = f"%{term}%"
        term_clauses.append(
            or_(
                Book.title.ilike(pattern),
                Book.authors.ilike(pattern),
                Book.summary.ilike(pattern),
                Book.keywords.ilike(pattern),
                Book.genre.ilike(pattern),
                Book.category.ilike(pattern),
            )
        )
    if match_all_terms:
        for clause in term_clauses:
            query = query.filter(clause)
    else:
        query = query.filter(or_(*term_clauses))
    return query


def _audience_fallback_query(
    db: Session,
    filter_criteria: SearchCriteria,
    extra: dict,
):
    """When NL mentions beginner/easy reads, map to catalog reading_level values."""
    relaxed = replace(filter_criteria, reading_level=None)
    query = apply_db_filters(db.query(Book), relaxed, extra)
    return query.filter(
        Book.reading_level.in_(
            ["general", "intermediate", "ages 5-10", "ages 12-18", "ages 13+"]
        )
    )


def _resolve_vector_hits(
    db: Session,
    relevant_results: list[tuple[int, float, dict]],
    *,
    author: str | None,
    genre: str | None,
    category: str | None,
) -> list[Book]:
    ordered_ids = [r[0] for r in relevant_results]
    retrieved_books = (
        db.query(Book)
        .filter(Book.id.in_(ordered_ids), Book.status != "archived")
        .all()
    )
    book_map = {b.id: b for b in retrieved_books}
    filtered_books: list[Book] = []
    seen: set[int] = set()

    for b_id, _score, payload in relevant_results:
        b = book_map.get(b_id)
        if b is None and payload.get("isbn"):
            b = (
                db.query(Book)
                .filter(Book.isbn == payload["isbn"], Book.status != "archived")
                .first()
            )
        if b is None or b.id in seen:
            continue
        if author and author.lower() not in (b.authors or "").lower():
            continue
        if genre and genre.lower() not in (b.genre or "").lower():
            continue
        if category and category.lower() == "programming":
            cat_ok = (
                "program" in (b.category or "").lower()
                or "program" in (b.genre or "").lower()
                or "python" in (b.title or "").lower()
                or "python" in (b.keywords or "").lower()
            )
            if not cat_ok:
                continue
        elif category and category.lower() not in (b.category or "").lower():
            continue
        seen.add(b.id)
        filtered_books.append(b)
    return filtered_books


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

    try:
        if q and q.strip():
            raw_query = q.strip()
            corrected_query = correct_query_spelling(db, raw_query)
            typo_corrected = corrected_query != raw_query

            if typo_corrected:
                typo_criteria = parse_query(corrected_query)
                books = keyword_search(db, corrected_query, typo_criteria, extra)
                if books:
                    criteria = typo_criteria
                    exact = True
                else:
                    books = []

            # Keyword search before vector/embedding keeps small hosts (e.g. Render) from OOMing.
            if not books:
                books = keyword_search(db, raw_query, criteria, extra)
                if books:
                    exact = True

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

            if not books:
                vector_results: list[tuple[int, float, dict]] = []
                search_texts = [raw_query]
                if typo_corrected:
                    search_texts = [corrected_query, raw_query]
                for search_text in dict.fromkeys(search_texts):
                    vector_results = semantic_search(
                        query_text=search_text,
                        limit=50,
                        filters=vector_filters,
                    )
                    if vector_results:
                        break

                if vector_results:
                    top_score = vector_results[0][1]
                    cutoff = max(0.50, top_score * 0.83) if top_score >= 0.50 else 0.40
                    relevant_results = [
                        result for result in vector_results if result[1] >= cutoff
                    ]
                    showing_related = not relevant_results
                    if showing_related:
                        relevant_results = vector_results

                    book_scores: dict[int, float] = {}
                    for b_id, score, payload in relevant_results:
                        book_scores[b_id] = score
                        summary_text = payload.get("summary") or payload.get("title") or ""
                        criteria.rag_context.append(f"[{payload.get('title')}]: {summary_text}")

                    criteria.scores = book_scores

                    books = _resolve_vector_hits(
                        db,
                        relevant_results,
                        author=author,
                        genre=genre,
                        category=category,
                    )
                    exact = not showing_related and top_score >= 0.52 and bool(books)

            if not books:
                lookup_q = corrected_query if corrected_query != raw_query else raw_query
                if lookup_q != raw_query:
                    criteria = parse_query(lookup_q)
                books = keyword_search(db, lookup_q, criteria, extra)
                used_typo_fix = corrected_query != raw_query and bool(books)
                exact = bool(books) and (
                    used_typo_fix
                    or not (
                        criteria.reading_level == "beginner"
                        and not extra.get("reading_level")
                    )
                )

        else:
            # No query string: standard catalog browsing with applied filters
            query = apply_db_filters(db.query(Book), criteria, extra)
            books = query.all()
            exact = True
    except Exception:
        logger.exception("Search failed for query %r", q)
        if q and q.strip():
            books = keyword_search(db, q.strip(), criteria, extra)
            exact = bool(books) and not (
                criteria.reading_level == "beginner" and not extra.get("reading_level")
            )
        else:
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