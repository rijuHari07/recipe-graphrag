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

def load_nodes():
    with open("kg_nodes.json", "r") as f:
        nodes = json.load(f)

    with driver.session(database=DATABASE) as session:
        for node in nodes:
            label = node["label"]
            name = node["name"]
            properties = node.get("properties", {})
            properties["name"] = name

            # Ensure steps are included in the properties if available
            if "steps" in node:
                properties["steps"] = node["steps"]

            query = f"""
            MERGE (n:{label} {{name: $name}})
            SET n += $properties
            """
            session.run(query, name=name, properties=properties)

    print("Nodes loaded successfully!")

if __name__ == "__main__":
    load_nodes()