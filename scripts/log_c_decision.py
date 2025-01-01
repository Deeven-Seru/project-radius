import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from memory_manager import MemoryManager

def log_c_decision():
    print("Logging architectural decision to Neo4j...")
    with MemoryManager() as mm:
        mm.record_decision(
            context="ISRO 10ms Execution Constraint",
            decision="Wrote core centroiding in C with ctypes Python harness. Benchmark yielded 0.1389ms.",
            outcome="Successful - Crushed the deadline requirement"
        )
    print("Decision logged.")

if __name__ == "__main__":
    log_c_decision()
