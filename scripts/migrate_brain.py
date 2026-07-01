import os
import sys
from neo4j import GraphDatabase

# Old database credentials
OLD_URI = "neo4j+s://5dc0982d.databases.neo4j.io"
OLD_AUTH = ("5dc0982d", "u3hULmkt4JdHWMbbVX3xmDOsRgzlErPypJanO9CMdkI")

# Load new database credentials from .env
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
    env = load_env()
    new_uri = env.get("NEO4J_URI")
    new_user = env.get("NEO4J_USERNAME")
    new_pwd = env.get("NEO4J_PASSWORD")
    
    if not new_uri or not new_user or not new_pwd:
        print("Error: New Neo4j credentials not found in .env")
        sys.exit(1)
        
    print(f"Connecting to Old Database: {OLD_URI}")
    old_driver = GraphDatabase.driver(OLD_URI, auth=OLD_AUTH)
    
    print(f"Connecting to New Database: {new_uri}")
    new_driver = GraphDatabase.driver(new_uri, auth=(new_user, new_pwd))
    
    # 1. Fetch all nodes and relationships from the old database
    nodes = []
    relationships = []
    
    with old_driver.session() as session:
        # Fetch nodes
        res_nodes = session.run("MATCH (n) RETURN id(n) as id, labels(n) as labels, properties(n) as props")
        for record in res_nodes:
            nodes.append({
                'id': record['id'],
                'labels': record['labels'],
                'props': dict(record['props'])
            })
            
        # Fetch relationships
        res_rels = session.run("MATCH (n)-[r]->(m) RETURN id(n) as source, type(r) as type, id(m) as target, properties(r) as props")
        for record in res_rels:
            relationships.append({
                'source': record['source'],
                'type': record['type'],
                'target': record['target'],
                'props': dict(record['props'])
            })
            
    print(f"Fetched {len(nodes)} nodes and {len(relationships)} relationships from the old database.")
    
    # 2. Write to the new database
    # We will map old node IDs to new node IDs or use unique properties like 'name' to reference them.
    # To be safe and preserve the exact graph structure, we can write the nodes, keep a mapping of old ID -> new elementId/ID, and then create relationships.
    old_id_to_new_name = {}
    
    with new_driver.session() as session:
        # Optional: clear the new database first to ensure a clean migration?
        # Actually, let's query first to see if it's empty or has nodes.
        # We will MERGE based on Name and Labels to avoid duplication if some nodes already exist.
        print("Migrating nodes...")
        for node in nodes:
            labels_str = ":".join(node['labels'])
            # Create properties string for Cypher
            props_keys = list(node['props'].keys())
            
            # Use a MERGE query to avoid duplicate nodes on subsequent runs
            # We assume 'name' is the unique identifier for nodes. If a node has no name, we use its ID or another property.
            name_val = node['props'].get('name', f"Node_{node['id']}")
            
            # Build Cypher to merge
            # We'll merge on the name property and labels
            cypher = f"MERGE (n:{labels_str} {{name: $name}})"
            if node['props']:
                set_parts = []
                for k in node['props'].keys():
                    if k != 'name':
                        set_parts.append(f"n.{k} = ${k}")
                if set_parts:
                    cypher += " ON CREATE SET " + ", ".join(set_parts)
                    cypher += " ON MATCH SET " + ", ".join(set_parts)
            
            params = dict(node['props'])
            params['name'] = name_val
            session.run(cypher, **params)
            old_id_to_new_name[node['id']] = name_val
            
        print("Migrating relationships...")
        for rel in relationships:
            src_name = old_id_to_new_name.get(rel['source'])
            tgt_name = old_id_to_new_name.get(rel['target'])
            
            if not src_name or not tgt_name:
                print(f"Skipping relationship: source or target name not found for {rel}")
                continue
                
            # Create relationship between matching nodes by name
            cypher = f"""
            MATCH (a {{name: $src_name}})
            MATCH (b {{name: $tgt_name}})
            MERGE (a)-[r:{rel['type']}]->(b)
            ON CREATE SET r = $props
            ON MATCH SET r = $props
            """
            session.run(cypher, src_name=src_name, tgt_name=tgt_name, props=rel['props'])
            
    print("Migration complete!")
    old_driver.close()
    new_driver.close()

if __name__ == "__main__":
    main()
