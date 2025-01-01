from neo4j import GraphDatabase
import logging
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

class MemoryManager:
    def __init__(self, uri=None, user=None, password=None):
        uri = uri or os.getenv("NEO4J_URI")
        user = user or os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
        password = password or os.getenv("NEO4J_PASSWORD")
        
        if not all([uri, user, password]):
            missing = []
            if not uri: missing.append("URI")
            if not user: missing.append("USER/USERNAME")
            if not password: missing.append("PASSWORD")
            raise ValueError(f"Neo4j connection details are missing ({', '.join(missing)}). Check your .env file.")
            
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def add_concept(self, name, description):
        query = (
            "MERGE (c:Concept {name: $name}) "
            "SET c.description = $description "
            "RETURN c.name AS name"
        )
        with self.driver.session() as session:
            result = session.run(query, name=name, description=description)
            self.logger.info(f"Added concept: {result.single()['name']}")

    def relate_concepts(self, name1, name2, relationship_type):
        query = (
            "MATCH (c1:Concept {name: $name1}) "
            "MATCH (c2:Concept {name: $name2}) "
            f"MERGE (c1)-[r:{relationship_type}]->(c2) "
            "RETURN type(r) AS relation"
        )
        with self.driver.session() as session:
            result = session.run(query, name1=name1, name2=name2)
            record = result.single()
            if record:
                self.logger.info(f"Created relation: {name1} -[{record['relation']}]-> {name2}")
            else:
                self.logger.warning(f"Failed to create relation between {name1} and {name2}. Check if concepts exist.")

    def query_concept(self, name):
        query = (
            "MATCH (c:Concept {name: $name}) "
            "RETURN c.name AS name, c.description AS description"
        )
        with self.driver.session() as session:
            result = session.run(query, name=name)
            record = result.single()
            if record:
                return {"name": record["name"], "description": record["description"]}
            return None

    def record_decision(self, context, decision, outcome="Pending"):
        """Permanently append a decision to the graph. No deletions allowed."""
        query = (
            "MERGE (c:Context {name: $context}) "
            "CREATE (d:Decision {name: $decision, outcome: $outcome, timestamp: datetime()}) "
            "MERGE (c)-[:LED_TO_DECISION]->(d) "
            "RETURN d.name AS decision"
        )
        with self.driver.session() as session:
            result = session.run(query, context=context, decision=decision, outcome=outcome)
            self.logger.info(f"Recorded permanent decision: {result.single()['decision']} (Outcome: {outcome})")

if __name__ == "__main__":
    print("Testing MemoryManager...")
    with MemoryManager() as mm:
        mm.add_concept("Shack-Hartmann", "Wavefront sensor using a lenslet array to measure local tilt.")
        mm.add_concept("Zernike Polynomials", "Sequence of polynomials orthogonal on a unit disk, used to describe optical aberrations.")
        mm.relate_concepts("Shack-Hartmann", "Zernike Polynomials", "MEASURES_FOR")
        
        info = mm.query_concept("Shack-Hartmann")
        print(f"Retrieved: {info}")
