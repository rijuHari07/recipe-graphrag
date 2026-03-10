"""
One-time script to patch r.steps into Neo4j for all Recipe nodes.
Steps were missing from kg_nodes.json because the KG builder didn't extract them.
This reads steps directly from the original CSV and loads them into Neo4j.

Usage:
    python patch_steps.py --csv your_file.csv
"""
import ast
import argparse
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

URI      = os.getenv("NEO4J_URI")
USER     = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")


def parse_steps(raw) -> list[str]:
    """Safely parse steps whether stored as a Python list-literal string or real list."""
    if isinstance(raw, list):
        return [str(s).strip() for s in raw if str(s).strip()]
    if isinstance(raw, str) and raw.strip():
        stripped = raw.strip()
        if stripped.startswith("["):
            try:
                parsed = ast.literal_eval(stripped)
                if isinstance(parsed, list):
                    return [str(s).strip() for s in parsed if str(s).strip()]
            except (ValueError, SyntaxError):
                pass
        # fallback: plain text
        return [stripped]
    return []


def load_csv_steps(csv_path: str) -> dict[str, list[str]]:
    """
    Returns {recipe_name_lowercase: [step1, step2, ...]}
    Deduplicates — one recipe may appear many times (one row per user interaction).
    """
    df = pd.read_csv(csv_path, usecols=["name", "steps"])
    df = df.dropna(subset=["name", "steps"])
    df = df.drop_duplicates(subset=["name"])   # keep first occurrence per recipe

    recipe_steps = {}
    for _, row in df.iterrows():
        name  = str(row["name"]).strip().lower()
        steps = parse_steps(row["steps"])
        if name and steps:
            recipe_steps[name] = steps

    return recipe_steps


def patch_neo4j(recipe_steps: dict[str, list[str]], dry_run: bool = False) -> None:
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    cypher_fetch = "MATCH (r:Recipe) RETURN r.name AS name"
    cypher_patch = """
        MATCH (r:Recipe)
        WHERE toLower(r.name) = $name
        SET r.steps = $steps
    """

    with driver.session(database=DATABASE) as session:
        # Fetch all recipe names currently in Neo4j
        existing = [record["name"] for record in session.run(cypher_fetch)]
        existing_lower = {n.lower(): n for n in existing if n}

        matched   = 0
        unmatched = 0

        for name_lower, steps in recipe_steps.items():
            if name_lower in existing_lower:
                matched += 1
                if not dry_run:
                    session.run(cypher_patch, name=name_lower, steps=steps)
            else:
                unmatched += 1

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Patch complete.")
        print(f"  Recipes in CSV with steps : {len(recipe_steps)}")
        print(f"  Matched to Neo4j nodes    : {matched}")
        print(f"  No Neo4j match (skipped)  : {unmatched}")
        if not dry_run:
            print(f"  r.steps SET on            : {matched} nodes")

    driver.close()


def verify(csv_name: str) -> None:
    """Quick sanity check: print r.steps for one recipe after patching."""
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver.session(database=DATABASE) as session:
        result = session.run(
            "MATCH (r:Recipe) WHERE toLower(r.name) = $name RETURN r.steps AS steps",
            name=csv_name.strip().lower(),
        )
        row = result.single()
        if row:
            print(f"\nVerification for '{csv_name}':")
            steps = row["steps"]
            if steps:
                for i, s in enumerate(steps, 1):
                    print(f"  {i}. {s}")
            else:
                print("  r.steps is still null — check the recipe name matches exactly.")
        else:
            print(f"  Recipe '{csv_name}' not found in Neo4j.")
    driver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Patch r.steps into Neo4j from CSV.")
    parser.add_argument("--csv",     required=True,  help="Path to your master CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without writing")
    parser.add_argument("--verify",  default="crete bean and spinach stew",
                        help="Recipe name to spot-check after patching")
    args = parser.parse_args()

    print(f"Loading steps from: {args.csv}")
    recipe_steps = load_csv_steps(args.csv)
    print(f"Found {len(recipe_steps)} unique recipes with steps in CSV.")

    patch_neo4j(recipe_steps, dry_run=args.dry_run)

    if not args.dry_run:
        verify(args.verify)
