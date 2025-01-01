"""
commit_research_memory.py
--------------------------
Logs key findings and results to a local research memory file.
Intended as a lightweight session log, not a database.
"""
import json
import os
import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'research_log.jsonl')

def log_result(tag: str, data: dict):
    entry = {"timestamp": datetime.datetime.utcnow().isoformat(), "tag": tag, **data}
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    print(f"Logged [{tag}]: {data}")

if __name__ == '__main__':
    log_result("benchmark", {
        "mse": 0.076,
        "r2_pct": 99.914,
        "latency_ms": 0.044,
        "r0_m": 11.585,
        "tau0_s": 0.01
    })
