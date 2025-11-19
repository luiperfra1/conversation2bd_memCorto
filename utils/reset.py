# reset.py
from __future__ import annotations

def reset_domain_sqlite(sqlite_db_path: str) -> bool:
    """
    Resetea tablas de dominio en SQLite (NO toca la tabla 'log').
    Devuelve True si fue bien, False en caso contrario.
    """
    try:
        from triplets2bd.utils.sqlite_client import SqliteClient
        from triplets2bd.utils.schema_sqlite_bootstrap import reset_sql
        db = SqliteClient(sqlite_db_path)
        reset_sql(db.conn)
        db.close()
        return True
    except Exception:
        return False


from typing import Optional, Tuple
from neo4j import GraphDatabase, basic_auth


def reset_domain_neo4j(uri: str, user: str, password: str, database: Optional[str] = None) -> bool:
    driver = GraphDatabase.driver(uri, auth=basic_auth(user, password))
    try:
        with driver.session(database=database or "neo4j") as s:
            s.run("MATCH (n) DETACH DELETE n").consume()
        return True
    finally:
        driver.close()
