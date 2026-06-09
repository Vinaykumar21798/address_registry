Address Registry System

This is a very simple and beginner-friendly project to extract US addresses from PDF files, remove duplicates, and manage them nicely. 

Here is the list of all tasks done in this project

1. Database Setup: Created SQLite database with 3 tables (documents, addresses, and address_documents link table). You can check tables in DB Browser for SQLite. When the FastAPI server starts, it checks if the database is created and creates it automatically.
2. Persisting Uploads: Every upload is saved. On success, document is stored as 'processed'. If upload fails (like no address found, scanned PDF, corrupt file), the document is still saved with 'failed' status and a clear reason.
3. SHA-256 Duplicate Check: Rejects duplicate files using SHA-256 hash. If duplicate file is uploaded, server returns HTTP 409 Conflict with details and logs it. No new rows are created.
4. Address Normalization: Normalizes raw addresses (making them UPPERCASE, standardizing abbreviations like STREET to ST, AVENUE to AVE, etc.). It parses them using 'usaddress' library. If parsing fails, it saves raw text and flags the row.
5. Deduplicate Addresses: Before inserting any address, it looks up the normalized text. If it is already there, it won't insert a new address; it will just add a link in address_documents. Stats endpoint GET /stats displays total documents, unique addresses, duplicate files rejected, and duplicate addresses caught.
6. Browse (Pagination, Detail, Soft Delete): GET /addresses supports pagination (limit and offset params). Delete is a soft-delete (sets deleted_at timestamp instead of hard deleting). Addresses are rendered in a clean Bootstrap table in the frontend.
7. Search and Filters: Supports search term and city, state, zip filtering combined with pagination. Matches are case-insensitive and safe from SQL injection.
8. Fuzzy Near-Duplicates matching: Compares addresses with same ZIP/City and flags them if similarity score is >= 90 using RapidFuzz library. It stores them in duplicate_candidates table with status pending.
9. Review & Merge: Reviewers can correct addresses (PATCH /addresses/{id}) or merge duplicates (POST /duplicates/{id}/resolve). A merge points the loser's documents to the winner and marks the loser as merged.
10. CSV Export: Export filtered addresses directly to CSV using StreamingResponse.

Bonus Tasks:
1. Content-Level Duplicate check: Hashes extracted text to block duplicate contents even if file bytes/hashes are different.
2. Bulk Import CLI: Run python import_folder.py to push all PDFs in the folder through the API.
3. FTS5 Search Indexing: Used SQLite FTS5 index for fast full-text queries instead of slow LIKE scans.

---

Setup Instructions :

1. Install Libraries First
First of all, run this command in your terminal to install all required libraries:
```bash
pip install fastapi uvicorn sqlalchemy rapidfuzz usaddress requests pdfplumber
```

2. Start Uvicorn Server
Go to the project folder and start the FastAPI server:
```bash
python -m uvicorn app.main:app --reload
```
Now, open your browser and go to `http://127.0.0.1:8000/`. You will see the clean, light-themed UI directly.

3. Bulk Import All PDFs
If you want to upload all sample PDFs in one go, simply run this import script:
```bash
python import_folder.py
```
It will show the full summary of processed, duplicates, and failed files at the end.

4. Run Search Performance Comparison
To see how fast FTS5 is compared to LIKE search, just run this speed test script:
```bash
python scratch/compare_search.py
```

---

File Structure:
`app/main.py` -> Backend server logic (FastAPI routes)
`app/database/db.py` -> SQLite connection & ORM query functions
`app/database/models.py` -> SQLAlchemy tables definition
`templates/index.html` -> Simple Bootstrap frontend
`static/script.js` -> JavaScript to fetch API and update UI
`static/style.css` -> Spacing and margin styles
