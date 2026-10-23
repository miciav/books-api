"""
Books API - a minimal CRUD service backed by PostgreSQL.

Endpoints
  GET    /health          -> service + database status
  GET    /books           -> list all books
  GET    /books/<id>      -> get one book
  POST   /books           -> create a book   (JSON: title, author, year)
  PUT    /books/<id>      -> update a book   (JSON: any of title, author, year)
  DELETE /books/<id>      -> delete a book

All settings are read from environment variables (see README.md).
"""
import os
import time

import psycopg
from psycopg.rows import dict_row
from flask import Flask, jsonify, request

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "books"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}
APP_PORT = int(os.getenv("APP_PORT", "8000"))
FIELDS = ("title", "author", "year")

app = Flask(__name__)


def get_conn():
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row, connect_timeout=5)


def init_db(retries=30, delay=2):
    """Create the table, waiting for the database to be ready."""
    for attempt in range(1, retries + 1):
        try:
            with get_conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS books (
                        id     SERIAL PRIMARY KEY,
                        title  TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year   INTEGER
                    )
                    """
                )
            print(f"Connected to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}", flush=True)
            return
        except psycopg.OperationalError as e:
            print(f"[{attempt}/{retries}] database not ready: {e}".strip(), flush=True)
            time.sleep(delay)
    raise SystemExit("Could not connect to the database, giving up.")


@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return jsonify(status="ok", database="up")
    except psycopg.OperationalError:
        return jsonify(status="error", database="down"), 503


@app.get("/books")
def list_books():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return jsonify(rows)


@app.get("/books/<int:book_id>")
def get_book(book_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = %s", (book_id,)).fetchone()
    if row is None:
        return jsonify(error="not found"), 404
    return jsonify(row)


@app.post("/books")
def create_book():
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("author"):
        return jsonify(error="'title' and 'author' are required"), 400
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO books (title, author, year) VALUES (%s, %s, %s) RETURNING *",
            (data["title"], data["author"], data.get("year")),
        ).fetchone()
    return jsonify(row), 201


@app.put("/books/<int:book_id>")
def update_book(book_id):
    data = request.get_json(silent=True) or {}
    updates = {k: data[k] for k in FIELDS if k in data}
    if not updates:
        return jsonify(error=f"provide at least one of {list(FIELDS)}"), 400
    # Column names come from the FIELDS whitelist, values are passed as parameters.
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    with get_conn() as conn:
        row = conn.execute(
            f"UPDATE books SET {set_clause} WHERE id = %s RETURNING *",
            (*updates.values(), book_id),
        ).fetchone()
    if row is None:
        return jsonify(error="not found"), 404
    return jsonify(row)


@app.delete("/books/<int:book_id>")
def delete_book(book_id):
    with get_conn() as conn:
        row = conn.execute("DELETE FROM books WHERE id = %s RETURNING id", (book_id,)).fetchone()
    if row is None:
        return jsonify(error="not found"), 404
    return "", 204


init_db()

if __name__ == "__main__":
    # 0.0.0.0 is required to be reachable from outside the container.
    app.run(host="0.0.0.0", port=APP_PORT)
