#!/usr/bin/env python3
"""
Indexing script for Smart Book Library.
Reads books from the database table, generates vector embeddings, and stores them in Qdrant Vector DB.

Usage:
    python index_books.py [--recreate] [--query "search term"]
"""

import argparse
import sys
import time

from app.database import SessionLocal
from app.models import Book
from app.services.vector_store import (
    index_books_from_db,
    semantic_search,
)
from app.config import settings


def run_indexing(recreate: bool = False) -> int:
    print("=" * 60)
    print("Starting Book Indexing into Qdrant Vector DB")
    print("=" * 60)
    print(f"Collection Name : {settings.qdrant_collection}")
    print(f"Embedding Model : {settings.embedding_model}")
    print(f"Vector Store    : {settings.qdrant_url or settings.qdrant_path}")
    print(f"Recreate        : {recreate}")
    print("-" * 60)

    db = SessionLocal()
    start_time = time.time()
    try:
        book_count = db.query(Book).count()
        print(f"Found {book_count} total books in database table 'books'.")

        indexed_count = index_books_from_db(db, recreate=recreate)
        elapsed = time.time() - start_time
        print(f"Indexing completed successfully in {elapsed:.2f} seconds.")
        print(f"Indexed {indexed_count} books into Qdrant collection '{settings.qdrant_collection}'.")
        return indexed_count
    except Exception as e:
        print(f"Error during indexing: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


def run_test_query(query: str):
    print("\n" + "=" * 60)
    print(f"Testing Semantic Search for Query: '{query}'")
    print("=" * 60)
    results = semantic_search(query, limit=5)
    if not results:
        print("No matching books found.")
        return

    for idx, (book_id, score, payload) in enumerate(results, start=1):
        print(f"{idx}. [Score: {score:.4f}] ID: {book_id}")
        print(f"   Title   : {payload.get('title')}")
        print(f"   Authors : {payload.get('authors')}")
        print(f"   Category: {payload.get('category')} | Genre: {payload.get('genre')}")
        print(f"   Summary : {payload.get('summary')}")
        print("-" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Index books from database table into Qdrant vector database."
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the Qdrant collection before indexing.",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Optional test search query to run after indexing.",
    )

    args = parser.parse_args()
    count = run_indexing(recreate=args.recreate)

    test_q = args.query if args.query else "machine learning and artificial intelligence for beginners"
    run_test_query(test_q)


if __name__ == "__main__":
    main()
