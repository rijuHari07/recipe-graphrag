from __future__ import annotations
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()
class Neo4jExecutor:
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:
        self.uri = uri or os.getenv("NEO4J_URI")
        self.user = user or os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.database = database or os.getenv("NEO4J_DATABASE")
        if not all([self.uri, self.user, self.password]):
            raise ValueError("Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USER/NEO4J_USERNAME, and NEO4J_PASSWORD.")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def execute_query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher, **params)
                return [dict(record) for record in result]
        except Exception as exc:
            return [{"error": str(exc)}]

    def test_connection(self) -> Dict[str, Any]:
        query = "MATCH (n) RETURN count(n) AS node_count"
        rows = self.execute_query(query)
        return rows[0] if rows else {"node_count": 0}

    def close(self) -> None:
        self.driver.close()


if __name__ == "__main__":
    executor = Neo4jExecutor()
    print(executor.test_connection())
    executor.close()
