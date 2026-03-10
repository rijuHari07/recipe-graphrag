from dotenv import load_dotenv
import os
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

print("URI =", repr(URI))
print("USER =", repr(USER))
print("DATABASE =", repr(DATABASE))

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

with driver.session(database=DATABASE) as session:
    result = session.run("MATCH (n) RETURN count(n) AS count")
    print("Connected! Node count:", result.single()["count"])