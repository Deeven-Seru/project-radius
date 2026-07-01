# Antigravity Workspace Customizations - Project Radius

## Global Intelligence Hub (Neo4j Aura Brain)
We use a Neo4j Aura instance as our shared memory/brain to index decisions, actions, consequences, results, etc., isolated by project. This replaces the Honcho memory engine.

### Connecting to the Brain
Connection credentials are stored in `.env` in the project root:
- `NEO4J_URI`: Connection URI (e.g., `neo4j+s://<id>.databases.neo4j.io`)
- `NEO4J_USERNAME`: Database username (or instance ID)
- `NEO4J_PASSWORD`: Database password / client secret

### Brain Schema
The brain stores memory project-wise to ensure separation and prevent overlap:
- `(Project)`: Root node for a project (e.g., `Project {name: "PROJECT RADIUS"}`).
- `(Decision)`: Major technical decisions (e.g., `Decision {name: "...", outcome: "...", timestamp: "..."}`).
  - Connected via `(Project)-[:HAS_DECISION]->(Decision)`.
- `(Action)`: Actions taken under the project or a decision.
  - Connected via `(Decision)-[:LED_TO_ACTION]->(Action)` or `(Project)-[:EXECUTES_ACTION]->(Action)`.
- `(Consequence)`: Non-obvious effects of actions.
  - Connected via `(Action)-[:HAD_CONSEQUENCE]->(Consequence)`.
- `(Result)`: Quantifiable performance metrics or outcomes.
  - Connected via `(Action)-[:ACHIEVED_RESULT]->(Result)`.

### Memory Management Tool
Use the utility script [scripts/brain.py](file:///Users/deeven/Developer/Project%20Radius/scripts/brain.py) to read and update this brain:

- **Query memory**:
  ```bash
  python3 scripts/brain.py query --project "PROJECT RADIUS"
  ```
- **Add decision**:
  ```bash
  python3 scripts/brain.py add-decision --project "PROJECT RADIUS" --name "Description of decision" --outcome "Outcome detail"
  ```
- **Add action**:
  ```bash
  python3 scripts/brain.py add-action --project "PROJECT RADIUS" --decision "Name of decision" --name "Action name" --desc "Action description"
  ```
- **Add consequence**:
  ```bash
  python3 scripts/brain.py add-consequence --project "PROJECT RADIUS" --action "Action name" --name "Consequence description" --impact "Impact scale"
  ```
- **Add result**:
  ```bash
  python3 scripts/brain.py add-result --project "PROJECT RADIUS" --action "Action name" --name "Result metric" --value "Value detail"
  ```

### Rules of Engagement
1. **Query First**: At the start of a task, query the project memory to recall prior decisions, context, and lessons learned.
2. **Log Decisively**: At the end of a task or significant implementation phase, record key decisions, actions, consequences, and results.
3. **Strict Isolation**: Always scope queries and writes with `--project "PROJECT RADIUS"` to prevent overlap across different workspaces or directories.
