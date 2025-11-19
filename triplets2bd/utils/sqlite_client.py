# sqlite_client.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Iterable, Tuple, Dict, Any

class SqliteClient:
    """
    Cliente mínimo para SQLite con helpers parecidos a Neo4jClient:
      - write(query, params)
      - write_many(batch)
      - executescript(sql)
    """
    def __init__(self, db_path: str | Path = "./kggen.sqlite") -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.text_factory = str

    def write(self, query: str, params: Dict[str, Any] | Tuple[Any, ...] | None = None):
        cur = self.conn.cursor()
        if params is None:
            cur.execute(query)
        else:
            cur.execute(query, params)
        self.conn.commit()
        return cur

    def write_many(self, batch: Iterable[Tuple[str, Dict[str, Any]]]):
        cur = self.conn.cursor()
        for q, p in batch:
            cur.execute(q, p)
        self.conn.commit()

    def executescript(self, sql: str):
        self.conn.executescript(sql)
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
