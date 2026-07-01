import os
import sys
from neo4j import GraphDatabase
import json

def load_env():
    env_vars = {}
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    env_vars[key.strip()] = val.strip().strip('"').strip("'")
    return env_vars

def main():
    try:
        env = load_env()
        uri = env.get("NEO4J_URI")
        user = env.get("NEO4J_USERNAME")
        pwd = env.get("NEO4J_PASSWORD")
        if not uri or not user or not pwd:
            print("Error: Neo4j credentials not found in .env")
            sys.exit(1)
            
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        with driver.session() as session:
            print("--- ALL NODES ---")
            query = """
            MATCH (n)
            RETURN id(n) as id, labels(n) as labels, properties(n) as props
            """
            results = session.run(query)
            nodes = {}
            for record in results:
                n_id = record['id']
                nodes[n_id] = {
                    'labels': record['labels'],
                    'props': dict(record['props'])
                }
                # Remove timestamp objects for printing
                if 'timestamp' in nodes[n_id]['props']:
                    nodes[n_id]['props']['timestamp'] = str(nodes[n_id]['props']['timestamp'])
            for n_id in sorted(nodes.keys()):
                print(f"Node {n_id}: {nodes[n_id]}")
            
            print("\n--- ALL RELATIONSHIPS ---")
            query_rels = """
            MATCH (n)-[r]->(m)
            RETURN id(n) as source, type(r) as type, id(m) as target, properties(r) as props
            """
            results_rels = session.run(query_rels)
            for record in results_rels:
                print(f"({record['source']}) -[{record['type']}]-> ({record['target']}) | Props: {dict(record['props'])}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
