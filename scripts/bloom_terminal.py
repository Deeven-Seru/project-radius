import os
import sys
import time
import argparse
from datetime import datetime
from neo4j import GraphDatabase

# ANSI escape codes for styling
CLEAR_SCREEN = "\033[H\033[2J\033[3J"
BOLD = "\033[1m"
RESET = "\033[0m"

# Colors for node labels
COLORS = {
    "PROJECT": "\033[38;5;51m",       # Cyan
    "DECISION": "\033[38;5;220m",      # Gold/Yellow
    "ACTION": "\033[38;5;121m",        # Light Green
    "CONSEQUENCE": "\033[38;5;203m",   # Coral/Red
    "RESULT": "\033[38;5;48m",         # Spring Green
    "CONTEXT": "\033[38;5;141m",       # Lavender
    "CONCEPT": "\033[38;5;213m",       # Pink
    "PHYSICS": "\033[38;5;165m",       # Purple
    "CONSTRAINT": "\033[38;5;39m",      # Blue
    "METRIC": "\033[38;5;81m",         # Steel Blue
    "ALGORITHM": "\033[38;5;153m",      # Ice Blue
    "COMPONENT": "\033[38;5;111m",      # Sky Blue
    "HARDWARE": "\033[38;5;208m",       # Orange
    "PAPER": "\033[38;5;246m",          # Muted Gray
    "DATASTRUCTURE": "\033[38;5;180m",  # Sand/Tan
    "DEFAULT": "\033[38;5;250m"        # Gray
}

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

def get_color(labels):
    if not labels:
        return COLORS["DEFAULT"]
    primary = labels[0].upper()
    return COLORS.get(primary, COLORS["DEFAULT"])

def format_node(name, labels, props):
    color = get_color(labels)
    label_str = labels[0] if labels else "Unknown"
    # Format details nicely
    detail_parts = []
    for k, v in props.items():
        if k != 'name' and k != 'timestamp' and k != 'created_at':
            # Trucate long property values for display
            val_str = str(v)
            if len(val_str) > 60:
                val_str = val_str[:57] + "..."
            detail_parts.append(f"{k}: {val_str}")
    details = f" ({', '.join(detail_parts)})" if detail_parts else ""
    return f"{color}{BOLD}[{label_str}]{RESET} {color}{name}{RESET}{details}"

def fetch_graph_data(driver):
    nodes = {}
    rels = []
    
    with driver.session() as session:
        # Get all nodes
        nodes_res = session.run("MATCH (n) RETURN elementId(n) as id, labels(n) as labels, properties(n) as props")
        for record in nodes_res:
            nodes[record['id']] = {
                'labels': record['labels'],
                'props': dict(record['props']),
                'name': record['props'].get('name', 'Unnamed')
            }
            
        # Get all relationships
        rels_res = session.run("MATCH (n)-[r]->(m) RETURN elementId(n) as src, type(r) as type, elementId(m) as tgt, properties(r) as props")
        for record in rels_res:
            rels.append({
                'src': record['src'],
                'type': record['type'],
                'tgt': record['tgt'],
                'props': dict(record['props'])
            })
            
    return nodes, rels

def draw_bloom_terminal(env, uri):
    driver = None
    try:
        user = env.get("NEO4J_USERNAME")
        pwd = env.get("NEO4J_PASSWORD")
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        
        nodes, rels = fetch_graph_data(driver)
        
        # Build adjacency maps for bidirectional traversal
        adj = {}
        for r in rels:
            src, tgt = r['src'], r['tgt']
            adj.setdefault(src, []).append((r, 'out', tgt))
            adj.setdefault(tgt, []).append((r, 'in', src))
            
        # Find roots (typically Project nodes)
        project_ids = [nid for nid, node in nodes.items() if "Project" in node['labels']]
        
        # Clear screen and print Header
        print(CLEAR_SCREEN, end="")
        print(f"🧠 {BOLD}\033[38;5;201mBLOOM TERMINAL — ACTIVE BRAIN MONITOR\033[0m")
        print(f"📡 Cluster: {BOLD}{uri}{RESET}")
        print(f"🕒 Last Synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Nodes: {BOLD}{len(nodes)}{RESET} | Relationships: {BOLD}{len(rels)}{RESET}")
        print("—" * 80)
        
        # Open URL hint
        bloom_url = f"https://bloom.neo4j.io/index.html?connectURL={uri.replace(':', '%3A').replace('/', '%2F')}"
        print(f"🔗 {BOLD}\033[4mOpen Web Bloom:\033[0m {bloom_url}")
        print("—" * 80)
        
        # Print hierarchical structure starting from Projects
        printed_ids = set()
        
        def print_tree(node_id, prefix="", is_last=True, rel_label=None):
            node = nodes.get(node_id)
            if not node:
                return
            
            printed_ids.add(node_id)
            
            # Print relation connector if present
            rel_str = f" {rel_label}" if rel_label else ""
            connector = "└── " if is_last else "├── "
            
            node_display = format_node(node['name'], node['labels'], node['props'])
            print(f"{prefix}{connector}{rel_str} {node_display}")
            
            # Find neighbors that haven't been printed yet
            neighbors = adj.get(node_id, [])
            unvisited_neighbors = []
            for r, direction, neighbor_id in neighbors:
                if neighbor_id not in printed_ids:
                    unvisited_neighbors.append((r, direction, neighbor_id))
            
            new_prefix = prefix + ("    " if is_last else "│   ")
            for idx, (r, direction, neighbor_id) in enumerate(unvisited_neighbors):
                last_child = (idx == len(unvisited_neighbors) - 1)
                rel_lbl = f"-[{r['type']}]->" if direction == 'out' else f"<-[{r['type']}]-"
                print_tree(neighbor_id, new_prefix, last_child, rel_lbl)
                
        # 1. Print all project-connected subgraphs
        for idx, pid in enumerate(project_ids):
            last_p = (idx == len(project_ids) - 1)
            print_tree(pid, is_last=last_p)
            print()
            
        # 2. Print remaining unvisited nodes and relationships
        unvisited = [nid for nid in nodes if nid not in printed_ids]
        if unvisited:
            print("📦 Unlinked/Sub-graphs:")
            for nid in unvisited:
                # Find nodes that have no incoming relations amongst unvisited to start printing
                has_unvisited_in = False
                for r, direction, neighbor_id in adj.get(nid, []):
                    if direction == 'in' and neighbor_id in unvisited:
                        has_unvisited_in = True
                        break
                if not has_unvisited_in:
                    print_tree(nid, prefix="  ", is_last=True)
                    
        # 3. Print Cross-Relationships between already printed structures (if any)
        cross_rels = []
        for r in rels:
            # If relationship was not traversed during tree print
            # (e.g. relationship between two nodes that were printed in separate branches)
            # we list it at the bottom to ensure completeness
            src_name = nodes.get(r['src'], {}).get('name')
            tgt_name = nodes.get(r['tgt'], {}).get('name')
            # Check if this link was already represented by tree printing
            # We can simplify by listing all relationships not shown hierarchically
            # But let's keep it simple: print all connections for completeness if requested.
            pass
            
    except Exception as e:
        print(f"\033[31mError querying database: {e}\033[0m")
    finally:
        if driver:
            driver.close()

def main():
    parser = argparse.ArgumentParser(description="Real-time Neo4j Bloom Terminal Visualizer")
    parser.add_argument("--refresh", type=int, default=5, help="Refresh interval in seconds (0 to run once)")
    args = parser.parse_args()
    
    env = load_env()
    uri = env.get("NEO4J_URI")
    
    if not uri:
        print("Error: NEO4J_URI not configured in .env file.")
        sys.exit(1)
        
    try:
        if args.refresh <= 0:
            draw_bloom_terminal(env, uri)
        else:
            print("Starting Bloom Terminal monitor... Press Ctrl+C to exit.")
            while True:
                draw_bloom_terminal(env, uri)
                print("—" * 80)
                print(f"Refreshing in {args.refresh}s... (Ctrl+C to quit)")
                time.sleep(args.refresh)
    except KeyboardInterrupt:
        print("\nBloom Terminal stopped.")

if __name__ == "__main__":
    main()
