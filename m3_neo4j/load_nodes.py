from neo4j import GraphDatabase
import json

URI = "neo4j+s://75558f53.databases.neo4j.io"
USER = "75558f53"
PASSWORD = "VGStYe2sUkw6ejnw-LfNcry_HSQM6RQ1cTtVFq7V4rA"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def load_nodes():
    with open("kg_nodes.json", "r") as f:
        nodes = json.load(f)

    with driver.session() as session:
        for node in nodes:
            label = node["label"]
            name = node["name"]
            properties = node.get("properties", {})

            # Ensure name property exists
            properties["name"] = name

            query = f"""
            MERGE (n:{label} {{name: $name}})
            SET n += $properties
            """

            session.run(query, name=name, properties=properties)

    print("Nodes loaded successfully!")

if __name__ == "__main__":
    load_nodes()