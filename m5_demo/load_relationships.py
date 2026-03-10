from neo4j import GraphDatabase
from dotenv import load_dotenv
import json
import os

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def load_relationships():
    with open("kg_triples_progress.json", "r") as f:
        data = json.load(f)

    triples = data["triples"]

    with driver.session(database=DATABASE) as session:
        for triple in triples:
            subject_label = triple["subject_label"]
            subject_name = triple["subject_name"]
            predicate = triple["predicate"]
            object_label = triple["object_label"]
            object_name = triple["object_name"]
            properties = triple.get("properties", {})

            # Ensure cuisine property is set for Cuisine nodes
            if predicate == "BELONGS_TO_CUISINE" and object_label == "Cuisine":
                properties["name"] = object_name

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