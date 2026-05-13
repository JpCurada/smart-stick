"""SQLite wrapper — connection management, query execution, and migrations.

A thin abstraction so every repository uses the same connection, error
handling, and locking strategy.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from core.config import Config
from core.exceptions import StorageError
from storage.schema import ALL_TABLES, INDEXES
from utils.logger import get_logger

_log = get_logger(__name__)


class Database:
    """Thread-safe SQLite wrapper. One connection, serialized via lock."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Config.DATABASE_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    def connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(
                self._path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL;")
            self._connection.execute("PRAGMA foreign_keys=ON;")
        return self._connection

    def initialize_schema(self) -> None:
        """Create all tables and indexes if they don't exist."""
        with self._lock:
            conn = self.connect()
            for ddl in ALL_TABLES:
                conn.execute(ddl)
            for index_sql in INDEXES:
                conn.execute(index_sql)
            conn.commit()
            _log.info("schema initialized at %s", self._path)

    def execute(self, query: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            try:
                cursor = self.connect().execute(query, params)
                self._connection.commit()  # type: ignore[union-attr]
                return cursor
            except sqlite3.Error as exc:
                raise StorageError(f"query failed: {exc}") from exc

    def executemany(self, query: str, rows: Iterable[Sequence[Any]]) -> None:
        with self._lock:
            try:
                self.connect().executemany(query, rows)
                self._connection.commit()  # type: ignore[union-attr]
            except sqlite3.Error as exc:
                raise StorageError(f"batch query failed: {exc}") from exc

    def fetch_all(self, query: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            try:
                cursor = self.connect().execute(query, params)
                return cursor.fetchall()
            except sqlite3.Error as exc:
                raise StorageError(f"fetch failed: {exc}") from exc

    def fetch_one(self, query: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        with self._lock:
            try:
                cursor = self.connect().execute(query, params)
                return cursor.fetchone()
            except sqlite3.Error as exc:
                raise StorageError(f"fetch failed: {exc}") from exc

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self.connect()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def vacuum(self) -> None:
        with self._lock:
            self.connect().execute("VACUUM;")

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
