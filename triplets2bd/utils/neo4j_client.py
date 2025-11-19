from __future__ import annotations
from typing import Any, Iterable
from neo4j import GraphDatabase, basic_auth
from utils.config import settings

class Neo4jClient:
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        self._driver = GraphDatabase.driver(
            uri or settings.NEO4J_URI,
            auth=basic_auth(user or settings.NEO4J_USER, password or settings.NEO4J_PASSWORD),
            max_connection_lifetime=3600,
        )

    def close(self):
        self._driver.close()

    def write_many(self, cypher_and_params: Iterable[tuple[str, dict]]):
        def _tx(tx):
            results = []
            for cy, pa in cypher_and_params:
                results.append(tx.run(cy, **pa).consume())
            return results
        with self._driver.session() as s:
            return s.execute_write(_tx)

    def write(self, cypher: str, params: dict):
        with self._driver.session() as s:
            return s.run(cypher, **params).data()
