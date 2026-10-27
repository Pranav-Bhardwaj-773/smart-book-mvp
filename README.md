# Smart Book Catalog MVP

## Run the backend
Python 3.10+ required.
```bash
cd backend
python -m venv .venv
```
Windows PowerShell: `.venv\Scripts\Activate.ps1`  
macOS/Linux: `source .venv/bin/activate`

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## Run the frontend (second terminal)
Node.js 20+ required.
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000

## MVP features
- Natural-language-ish search using query parsing, keywords, metadata, and relevance ranking
- Catalog and availability display
- SQLite persistence
- Rent and return books
- Maximum 2 Active/Overdue rentals per demo user
- 14-day rental duration and duplicate rental checks

## Important limitations
This is a local demo MVP. It uses a demo user ID and has no real login, registration, admin authorization, notifications, vector embeddings, or production-grade concurrency protection. Do not expose it publicly as-is. The search is a keyword/metadata baseline, not true semantic vector search.
