import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from memory_manager import MemoryManager

def log_reconstruction_decision():
    print("Logging architectural decision to Neo4j...")
    with MemoryManager() as mm:
        mm.record_decision(
            context="Real-time Zernike solver constraint",
            decision="Calculated inverse geometry matrix offline. Handled real-time reconstruction via Matrix-Vector Multiplication in C. Yielded 0.143ms total pipeline time.",
            outcome="Successful - Math simplified for extreme performance."
        )
    print("Decision logged.")

if __name__ == "__main__":
    log_reconstruction_decision()
