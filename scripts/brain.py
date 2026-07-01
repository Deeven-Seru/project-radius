import os
import sys
import argparse
from datetime import datetime, timezone
from neo4j import GraphDatabase

# Helper to load .env manually to avoid extra dependencies
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

def get_driver(env):
    uri = env.get("NEO4J_URI") or os.environ.get("NEO4J_URI")
    user = env.get("NEO4J_USERNAME") or os.environ.get("NEO4J_USERNAME")
    pwd = env.get("NEO4J_PASSWORD") or os.environ.get("NEO4J_PASSWORD")
    
    if not uri or not user or not pwd or "<YOUR_INTELLIGENCE_HUB_URI>" in uri:
        print("Error: Neo4j Global Intelligence Hub URI is not configured yet.")
        print("Please configure the 'NEO4J_URI' in your .env file with your Aura connection URI.")
        print(f"Loaded details: URI={uri}, USERNAME={user}, PASSWORD={'***' if pwd else None}")
        sys.exit(1)
        
    return GraphDatabase.driver(uri, auth=(user, pwd))

def init_project(session, project_name):
    # Ensure Project node exists
    query = """
    MERGE (p:Project {name: $name})
    ON CREATE SET p.created_at = $now, p.status = "Active"
    RETURN p
    """
    session.run(query, name=project_name, now=datetime.now(timezone.utc).isoformat())

def add_decision(session, project_name, decision_name, outcome):
    init_project(session, project_name)
    query = """
    MATCH (p:Project {name: $project_name})
    CREATE (d:Decision {
        name: $name,
        outcome: $outcome,
        timestamp: $now
    })
    CREATE (p)-[:HAS_DECISION]->(d)
    RETURN d
    """
    res = session.run(query, project_name=project_name, name=decision_name, outcome=outcome, now=datetime.now(timezone.utc).isoformat())
    return list(res)

def add_action(session, project_name, decision_name, action_name, description=None):
    init_project(session, project_name)
    # Link action to decision or to project directly if decision is not specified
    if decision_name:
        query = """
        MATCH (p:Project {name: $project_name})-[:HAS_DECISION]->(d:Decision {name: $decision_name})
        CREATE (a:Action {
            name: $name,
            description: $desc,
            timestamp: $now
        })
        CREATE (d)-[:LED_TO_ACTION]->(a)
        RETURN a
        """
        res = session.run(query, project_name=project_name, decision_name=decision_name, name=action_name, desc=description, now=datetime.now(timezone.utc).isoformat())
    else:
        query = """
        MATCH (p:Project {name: $project_name})
        CREATE (a:Action {
            name: $name,
            description: $desc,
            timestamp: $now
        })
        CREATE (p)-[:EXECUTES_ACTION]->(a)
        RETURN a
        """
        res = session.run(query, project_name=project_name, name=action_name, desc=description, now=datetime.now(timezone.utc).isoformat())
    return list(res)

def add_consequence(session, project_name, action_name, consequence_name, impact=None):
    query = """
    MATCH (p:Project {name: $project_name})
    MATCH (p)-[:HAS_DECISION]->(:Decision)-[:LED_TO_ACTION]->(a:Action {name: $action_name})
    CREATE (c:Consequence {
        name: $name,
        impact: $impact,
        timestamp: $now
    })
    CREATE (a)-[:HAD_CONSEQUENCE]->(c)
    RETURN c
    """
    res = session.run(query, project_name=project_name, action_name=action_name, name=consequence_name, impact=impact, now=datetime.now(timezone.utc).isoformat())
    # Fallback to match action via direct EXECUTES_ACTION
    if not list(res):
        query_fallback = """
        MATCH (p:Project {name: $project_name})-[:EXECUTES_ACTION]->(a:Action {name: $action_name})
        CREATE (c:Consequence {
            name: $name,
            impact: $impact,
            timestamp: $now
        })
        CREATE (a)-[:HAD_CONSEQUENCE]->(c)
        RETURN c
        """
        res = session.run(query_fallback, project_name=project_name, action_name=action_name, name=consequence_name, impact=impact, now=datetime.now(timezone.utc).isoformat())
    return list(res)

def add_result(session, project_name, action_name, result_name, value=None):
    query = """
    MATCH (p:Project {name: $project_name})
    MATCH (p)-[:HAS_DECISION]->(:Decision)-[:LED_TO_ACTION]->(a:Action {name: $action_name})
    CREATE (r:Result {
        name: $name,
        value: $value,
        timestamp: $now
    })
    CREATE (a)-[:ACHIEVED_RESULT]->(r)
    RETURN r
    """
    res = session.run(query, project_name=project_name, action_name=action_name, name=result_name, value=value, now=datetime.now(timezone.utc).isoformat())
    # Fallback to match action via direct EXECUTES_ACTION
    if not list(res):
        query_fallback = """
        MATCH (p:Project {name: $project_name})-[:EXECUTES_ACTION]->(a:Action {name: $action_name})
        CREATE (r:Result {
            name: $name,
            value: $value,
            timestamp: $now
        })
        CREATE (a)-[:ACHIEVED_RESULT]->(r)
        RETURN r
        """
        res = session.run(query_fallback, project_name=project_name, action_name=action_name, name=result_name, value=value, now=datetime.now(timezone.utc).isoformat())
    return list(res)

def query_memory(session, project_name):
    # Fetch everything related to this specific project to enforce non-overlapping isolation
    query = """
    MATCH (p:Project {name: $project_name})
    OPTIONAL MATCH (p)-[r1]->(n1)
    OPTIONAL MATCH (n1)-[r2]->(n2)
    RETURN p, r1, n1, r2, n2
    """
    results = session.run(query, project_name=project_name)
    nodes = {}
    rels = set()
    
    for record in results:
        p = record['p']
        if p:
            nodes[p.element_id] = {"labels": list(p.labels), "props": dict(p)}
            
        n1 = record['n1']
        r1 = record['r1']
        if n1 is not None and r1 is not None:
            nodes[n1.element_id] = {"labels": list(n1.labels), "props": dict(n1)}
            rels.add((r1.start_node.element_id, r1.type, r1.end_node.element_id))
            
        n2 = record['n2']
        r2 = record['r2']
        if n2 is not None and r2 is not None:
            nodes[n2.element_id] = {"labels": list(n2.labels), "props": dict(n2)}
            rels.add((r2.start_node.element_id, r2.type, r2.end_node.element_id))

    print(f"\n--- PROJECT MEMORY: {project_name} ---")
    if not nodes:
        print("No memory nodes found for this project.")
        return
        
    print(f"\nNodes ({len(nodes)}):")
    for el_id, info in nodes.items():
        print(f"  [{info['labels'][0]}] {info['props'].get('name', 'Unnamed')} | Props: {info['props']}")
        
    print(f"\nRelationships ({len(rels)}):")
    for src, rel_type, tgt in sorted(rels):
        src_name = nodes[src]['props'].get('name', 'Unnamed')
        tgt_name = nodes[tgt]['props'].get('name', 'Unnamed')
        print(f"  ({src_name}) -[{rel_type}]-> ({tgt_name})")

def main():
    parser = argparse.ArgumentParser(description="Antigravity Neo4j Aura Brain memory tool")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    
    # Init project
    init_parser = subparsers.add_parser("init-project")
    init_parser.add_argument("--project", required=True, help="Project name")
    
    # Add decision
    dec_parser = subparsers.add_parser("add-decision")
    dec_parser.add_argument("--project", required=True, help="Project name")
    dec_parser.add_argument("--name", required=True, help="Decision description")
    dec_parser.add_argument("--outcome", required=True, help="Outcome of decision")
    
    # Add action
    act_parser = subparsers.add_parser("add-action")
    act_parser.add_argument("--project", required=True, help="Project name")
    act_parser.add_argument("--decision", help="Decision name to link to (optional)")
    act_parser.add_argument("--name", required=True, help="Action name")
    act_parser.add_argument("--desc", help="Action description")
    
    # Add consequence
    cons_parser = subparsers.add_parser("add-consequence")
    cons_parser.add_argument("--project", required=True, help="Project name")
    cons_parser.add_argument("--action", required=True, help="Action name to link to")
    cons_parser.add_argument("--name", required=True, help="Consequence description")
    cons_parser.add_argument("--impact", help="Impact rating or description")
    
    # Add result
    res_parser = subparsers.add_parser("add-result")
    res_parser.add_argument("--project", required=True, help="Project name")
    res_parser.add_argument("--action", required=True, help="Action name to link to")
    res_parser.add_argument("--name", required=True, help="Result description")
    res_parser.add_argument("--value", help="Result value or metrics")
    
    # Query project memory
    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("--project", required=True, help="Project name")
    
    args = parser.parse_args()
    env = load_env()
    driver = get_driver(env)
    
    with driver.session() as session:
        if args.cmd == "init-project":
            init_project(session, args.project)
            print(f"Project '{args.project}' initialized.")
        elif args.cmd == "add-decision":
            add_decision(session, args.project, args.name, args.outcome)
            print(f"Decision added to project '{args.project}'.")
        elif args.cmd == "add-action":
            add_action(session, args.project, args.decision, args.name, args.desc)
            print(f"Action added to project '{args.project}'.")
        elif args.cmd == "add-consequence":
            add_consequence(session, args.project, args.action, args.name, args.impact)
            print(f"Consequence added to action '{args.action}'.")
        elif args.cmd == "add-result":
            add_result(session, args.project, args.action, args.name, args.value)
            print(f"Result added to action '{args.action}'.")
        elif args.cmd == "query":
            query_memory(session, args.project)
            
    driver.close()

if __name__ == "__main__":
    main()
