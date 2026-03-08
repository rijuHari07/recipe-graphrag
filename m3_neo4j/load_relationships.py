from neo4j import GraphDatabase
import json

URI = "neo4j+s://75558f53.databases.neo4j.io"
USER = "75558f53"
PASSWORD = "VGStYe2sUkw6ejnw-LfNcry_HSQM6RQ1cTtVFq7V4rA"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def load_relationships():
    with open("kg_triples_progress.json", "r") as f:
        data = json.load(f)

    triples = data["triples"]

    with driver.session() as session:
        for triple in triples:
            subject_label = triple["subject_label"]
            subject_name = triple["subject_name"]
            predicate = triple["predicate"]
            object_label = triple["object_label"]
            object_name = triple["object_name"]
            properties = triple.get("properties", {})

            query = f"""
            MATCH (a:{subject_label} {{name: $subject_name}})
            MATCH (b:{object_label} {{name: $object_name}})
            MERGE (a)-[r:{predicate}]->(b)
            SET r += $properties
            """

            session.run(
                query,
                subject_name=subject_name,
                object_name=object_name,
                properties=properties
            )

    print("Relationships loaded successfully!")

if __name__ == "__main__":
    load_relationships()