import logging
import re
import time
from contextlib import contextmanager
from typing import Any, Generator, List, Optional, Tuple

from qdrant_client import QdrantClient, models
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Book

logger = logging.getLogger(__name__)

_fastembed_model: Optional[Any] = None
_gemini_client: Optional[Any] = None


def is_gemini_embedding() -> bool:
    return "gemini" in (settings.embedding_model or "").lower() and bool(settings.gemini_api_key)


def get_vector_dimension() -> int:
    """Return the vector dimensionality corresponding to the configured embedding model."""
    if is_gemini_embedding():
        return 3072
    return 384


def _get_gemini_client() -> Any:
    """Singleton getter for the official google-genai Client."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai as google_genai

        _gemini_client = google_genai.Client(api_key=settings.gemini_api_key)
        logger.info(f"Initialized google-genai SDK client for model: {settings.embedding_model}")
    return _gemini_client


def get_embedding_model() -> Any:
    """Singleton getter for FastEmbed TextEmbedding model (used when Gemini is not configured)."""
    global _fastembed_model
    if _fastembed_model is None:
        from fastembed import TextEmbedding

        logger.info(f"Loading local FastEmbed model: {settings.embedding_model}")
        _fastembed_model = TextEmbedding(model_name=settings.embedding_model)
    return _fastembed_model


def _extract_retry_delay(err_str: str) -> float:
    try:
        m = re.search(r'"retryDelay":\s*"([0-9.]+)', err_str)
        if m:
            return float(m.group(1)) + 1.0
        m = re.search(r'retry in ([0-9.]+)', err_str, re.IGNORECASE)
        if m:
            return float(m.group(1)) + 1.0
    except Exception:
        pass
    return 15.0


def _embed_gemini_batch(texts: List[str]) -> List[List[float]]:
    """Embed texts using the official google-genai SDK with rate-limit retry."""
    from google.genai import errors as genai_errors

    model_name = settings.embedding_model or "gemini-embedding-2"
    client = _get_gemini_client()
    all_embeddings: List[List[float]] = []

    batch_size = 10
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        max_retries = 6
        for attempt in range(max_retries):
            try:
                response = client.models.embed_content(
                    model=model_name,
                    contents=chunk,
                )
                for emb in response.embeddings:
                    all_embeddings.append(list(emb.values))
                break
            except genai_errors.ClientError as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_time = _extract_retry_delay(err_str)
                    logger.warning(
                        f"Gemini rate limit (429). Pausing {wait_time:.1f}s "
                        f"(attempt {attempt + 1}/{max_retries})..."
                    )
                    print(f"Gemini rate limit: pausing {wait_time:.1f}s before retrying...", flush=True)
                    time.sleep(wait_time)
                else:
                    raise
        else:
            raise RuntimeError("Exceeded maximum retries for Gemini embedding batch.")

    return all_embeddings


def _embed_gemini_single(text: str) -> List[float]:
    """Embed a single text using the official google-genai SDK with rate-limit retry."""
    from google.genai import errors as genai_errors

    model_name = settings.embedding_model or "gemini-embedding-2"
    client = _get_gemini_client()

    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = client.models.embed_content(
                model=model_name,
                contents=text,
            )
            return list(response.embeddings[0].values)
        except genai_errors.ClientError as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait_time = _extract_retry_delay(err_str)
                logger.warning(f"Gemini rate limit on single embed. Pausing {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                raise
    raise RuntimeError("Exceeded maximum retries for Gemini single embedding.")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts using Gemini if configured, otherwise local FastEmbed."""
    if not settings.enable_vector_search:
        raise RuntimeError("Vector search is disabled (ENABLE_VECTOR_SEARCH=false)")
    if is_gemini_embedding():
        return _embed_gemini_batch(texts)
    model = get_embedding_model()
    return [v.tolist() for v in model.embed(texts)]


def embed_single_text(text: str) -> List[float]:
    """Embed a single query or text."""
    if is_gemini_embedding():
        return _embed_gemini_single(text)
    model = get_embedding_model()
    return list(model.embed([text]))[0].tolist()


@contextmanager
def get_qdrant_client() -> Generator[QdrantClient, None, None]:
    """Yield a QdrantClient instance and ensure it is properly closed when in local storage mode."""
    if settings.qdrant_url:
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=60.0,
            check_compatibility=False,
        )
        try:
            yield client
        finally:
            client.close()
    else:
        client = QdrantClient(path=settings.qdrant_path)
        try:
            yield client
        finally:
            client.close()


def build_book_content(book: Book | dict) -> str:
    """Build a rich, structured textual representation of a book for semantic embedding."""
    if isinstance(book, dict):
        title = book.get("title", "") or ""
        subtitle = book.get("subtitle", "") or ""
        authors = book.get("authors", "") or ""
        category = book.get("category", "") or ""
        genre = book.get("genre", "") or ""
        language = book.get("language", "") or ""
        reading_level = book.get("reading_level", "") or ""
        pub_year = book.get("publication_year", "")
        desc = book.get("description", "") or ""
        summary = book.get("summary", "") or ""
        keywords = book.get("keywords", "") or ""
        tags = book.get("search_tags", "") or ""
    else:
        title = getattr(book, "title", "") or ""
        subtitle = getattr(book, "subtitle", "") or ""
        authors = getattr(book, "authors", "") or ""
        category = getattr(book, "category", "") or ""
        genre = getattr(book, "genre", "") or ""
        language = getattr(book, "language", "") or ""
        reading_level = getattr(book, "reading_level", "") or ""
        pub_year = getattr(book, "publication_year", "") or ""
        desc = getattr(book, "description", "") or ""
        summary = getattr(book, "summary", "") or ""
        keywords = getattr(book, "keywords", "") or ""
        tags = getattr(book, "search_tags", "") or ""

    parts = [
        f"Title: {title}",
        f"Subtitle: {subtitle}" if subtitle else "",
        f"Author: {authors}" if authors else "",
        f"Category: {category}" if category else "",
        f"Genre: {genre}" if genre else "",
        f"Language: {language}" if language else "",
        f"Publication Year: {pub_year}" if pub_year else "",
        f"Reading Level: {reading_level}" if reading_level else "",
        f"Overview: {summary}" if summary else "",
        f"Description: {desc}" if desc else "",
        f"Keywords: {keywords}" if keywords else "",
        f"Tags: {tags}" if tags else "",
    ]
    return "\n".join(p for p in parts if p)


def ensure_collection(client: QdrantClient, recreate: bool = False) -> None:
    """Ensure the Qdrant collection exists with proper vector configuration and payload indexes."""
    target_dim = get_vector_dimension()
    exists = client.collection_exists(settings.qdrant_collection)
    if exists and not recreate:
        # Check if existing collection vector dimension matches expected dimension
        try:
            coll_info = client.get_collection(settings.qdrant_collection)
            current_dim = getattr(coll_info.config.params.vectors, "size", None)
            if current_dim and current_dim != target_dim:
                logger.info(
                    f"Vector dimension mismatch ({current_dim} != {target_dim}). Recreating collection '{settings.qdrant_collection}'."
                )
                recreate = True
        except Exception as e:
            logger.warning(f"Could not inspect collection config: {e}")

    if exists and recreate:
        logger.info(f"Recreating Qdrant collection: {settings.qdrant_collection} (target dim={target_dim})")
        client.delete_collection(settings.qdrant_collection)
        exists = False

    if not exists:
        logger.info(f"Creating Qdrant collection '{settings.qdrant_collection}' with dimension {target_dim}")
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=models.VectorParams(
                size=target_dim,
                distance=models.Distance.COSINE,
            ),
        )

    # Ensure payload indexes exist for filtered fields
    for field, schema_type in [
        ("status", models.PayloadSchemaType.KEYWORD),
        ("language", models.PayloadSchemaType.KEYWORD),
        ("category", models.PayloadSchemaType.KEYWORD),
        ("genre", models.PayloadSchemaType.KEYWORD),
        ("reading_level", models.PayloadSchemaType.KEYWORD),
        ("available_copies", models.PayloadSchemaType.INTEGER),
        ("publication_year", models.PayloadSchemaType.INTEGER),
        ("page_count", models.PayloadSchemaType.INTEGER),
    ]:
        try:
            client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name=field,
                field_schema=schema_type,
            )
        except Exception:
            pass


def index_books_from_db(db: Session, recreate: bool = False) -> int:
    """Read all non-archived books from SQL database table and index them in Qdrant vector DB."""
    books = db.query(Book).filter(Book.status != "archived").all()
    if not books:
        logger.warning("No books found in table to index.")
        return 0

    texts = [build_book_content(b) for b in books]
    embeddings = embed_texts(texts)

    points = []
    for b, emb in zip(books, embeddings):
        vector = emb if isinstance(emb, list) else emb.tolist()
        payload = {
            "book_id": b.id,
            "isbn": b.isbn,
            "title": b.title,
            "subtitle": b.subtitle,
            "authors": b.authors,
            "category": b.category,
            "genre": b.genre,
            "language": b.language,
            "publisher": b.publisher,
            "publication_year": b.publication_year,
            "page_count": b.page_count,
            "reading_level": b.reading_level,
            "status": b.status,
            "total_copies": b.total_copies,
            "available_copies": b.available_copies,
            "cover_url": b.cover_url,
            "summary": b.summary,
            "description": b.description,
            "keywords": b.keywords,
            "search_tags": b.search_tags,
        }
        points.append(
            models.PointStruct(
                id=b.id,
                vector=vector,
                payload=payload,
            )
        )

    with get_qdrant_client() as client:
        ensure_collection(client, recreate=recreate)
        batch_size = 64
        for i in range(0, len(points), batch_size):
            chunk = points[i : i + batch_size]
            client.upsert(
                collection_name=settings.qdrant_collection,
                points=chunk,
            )

    logger.info(f"Successfully indexed {len(points)} books into Qdrant collection '{settings.qdrant_collection}'.")
    from app.services.search import invalidate_search_vocabulary_cache

    invalidate_search_vocabulary_cache()
    return len(points)


def qdrant_index_in_sync(db: Session) -> bool:
    """True when Qdrant contains the same catalog rows as the SQL database."""
    db_count = db.query(Book).filter(Book.status != "archived").count()
    if db_count == 0:
        return True
    try:
        with get_qdrant_client() as client:
            if not client.collection_exists(settings.qdrant_collection):
                return False
            q_count = client.count(settings.qdrant_collection).count
            if q_count != db_count:
                return False
            sample_id = (
                db.query(Book.id).filter(Book.status != "archived").order_by(Book.id).limit(1).scalar()
            )
            if sample_id is None:
                return True
            points = client.retrieve(
                collection_name=settings.qdrant_collection,
                ids=[int(sample_id)],
                with_payload=False,
            )
            return len(points) > 0
    except Exception as e:
        logger.warning(
            "Could not verify Qdrant index sync (%s); skipping startup re-index.", e
        )
        return True


def upsert_single_book(book: Book) -> None:
    """Index or update a single book in Qdrant."""
    if not settings.enable_vector_search:
        return
    try:
        text = build_book_content(book)
        vec = embed_single_text(text)
        payload = {
            "book_id": book.id,
            "isbn": book.isbn,
            "title": book.title,
            "subtitle": book.subtitle,
            "authors": book.authors,
            "category": book.category,
            "genre": book.genre,
            "language": book.language,
            "publisher": book.publisher,
            "publication_year": book.publication_year,
            "page_count": book.page_count,
            "reading_level": book.reading_level,
            "status": book.status,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
            "cover_url": book.cover_url,
            "summary": book.summary,
            "description": book.description,
            "keywords": book.keywords,
            "search_tags": book.search_tags,
        }
        with get_qdrant_client() as client:
            ensure_collection(client, recreate=False)
            client.upsert(
                collection_name=settings.qdrant_collection,
                points=[
                    models.PointStruct(
                        id=book.id,
                        vector=vec,
                        payload=payload,
                    )
                ],
            )
    except Exception as e:
        logger.error(f"Failed to upsert book {book.id} to Qdrant: {e}")


def semantic_search(
    query_text: str,
    limit: int = 50,
    filters: Optional[dict] = None,
) -> List[Tuple[int, float, dict]]:
    """
    Search Qdrant for books semantically matching query_text.
    Returns list of tuples: (book_id, score, payload)
    """
    if not query_text or not query_text.strip():
        return []

    if not settings.enable_vector_search:
        return []

    try:
        query_vector = embed_single_text(query_text.strip())
    except Exception as e:
        logger.warning("Embedding failed for search query: %s", e)
        return []

    filter_conditions: List[Any] = []
    must_not_conditions: List[Any] = [
        models.FieldCondition(key="status", match=models.MatchValue(value="archived"))
    ]

    if filters:
        if filters.get("language"):
            filter_conditions.append(
                models.FieldCondition(
                    key="language", match=models.MatchValue(value=filters["language"])
                )
            )
        if filters.get("available_only"):
            filter_conditions.append(
                models.FieldCondition(
                    key="available_copies", range=models.Range(gt=0)
                )
            )
        if filters.get("year_from") is not None:
            filter_conditions.append(
                models.FieldCondition(
                    key="publication_year", range=models.Range(gte=filters["year_from"])
                )
            )
        if filters.get("year_to") is not None:
            filter_conditions.append(
                models.FieldCondition(
                    key="publication_year", range=models.Range(lte=filters["year_to"])
                )
            )
        if filters.get("pages_max") is not None:
            filter_conditions.append(
                models.FieldCondition(
                    key="page_count", range=models.Range(lte=filters["pages_max"])
                )
            )
        if filters.get("reading_level"):
            filter_conditions.append(
                models.FieldCondition(
                    key="reading_level", match=models.MatchValue(value=filters["reading_level"].lower())
                )
            )

    qdrant_filter = None
    if filter_conditions or must_not_conditions:
        qdrant_filter = models.Filter(
            must=filter_conditions if filter_conditions else None,
            must_not=must_not_conditions if must_not_conditions else None,
        )

    try:
        with get_qdrant_client() as client:
            if not client.collection_exists(settings.qdrant_collection):
                return []

            res = client.query_points(
                collection_name=settings.qdrant_collection,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=limit,
                with_payload=True,
            )

            results = []
            for point in res.points:
                book_id = point.payload.get("book_id", point.id) if point.payload else point.id
                results.append((int(book_id), float(point.score), point.payload or {}))
            return results
    except Exception as e:
        logger.warning("Qdrant semantic search failed: %s", e)
        return []
