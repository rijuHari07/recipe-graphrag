from neo4j import GraphDatabase

URI = "neo4j+s://75558f53.databases.neo4j.io"
USER = "75558f53"
PASSWORD = "VGStYe2sUkw6ejnw-LfNcry_HSQM6RQ1cTtVFq7V4rA"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) AS count")
    print("Connected! Node count:", result.single()["count"])