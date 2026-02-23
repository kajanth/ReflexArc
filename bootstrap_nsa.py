import os
import sqlite3
import json

def setup_nsa():
    print("🧠 Initializing Neuro-Synthetic Architecture (NSA) Bootstrap...")

    # 1. Create Directory Structure
    dirs = ['sensors', 'memory', 'skills']
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"[+] Created directory: /{d}")
        
        # Ensure skills is a python package
        if d == 'skills':
            with open('skills/__init__.py', 'w') as f: pass

    # 2. Initialize Hippocampus (SQLite DB)
    db_path = "memory/long_term_memory.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sense_type TEXT,
            description TEXT,
            vector BLOB
        )
    ''')
    conn.commit()
    conn.close()
    print("[+] Initialized Hippocampus Database.")

    # 3. Initialize Interoception (Stats JSON)
    stats_path = "memory/stats.json"
    if not os.path.exists(stats_path):
        with open(stats_path, "w") as f:
            json.dump({"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}, f)
        print("[+] Initialized Interoception Stats.")

    # 4. Generate the 'agent.md' DNA
    with open('agent.md', 'w') as f:
        f.write("# NSA System DNA\nRole: Neuro-Synthetic Orchestrator\nGoal: Zero-token autonomy via sensory reflexes.")
    print("[+] Generated agent.md.")

    # 5. Create a placeholder Skill (Homeostasis)
    homeostasis_code = """
import psutil
import time

def run(data=None):
    cpu = psutil.cpu_percent()
    print(f"[Cerebellum]: Homeostasis Check - CPU at {cpu}%")
    return cpu
"""
    with open('skills/homeostasis.py', 'w') as f:
        f.write(homeostasis_code.strip())
    print("[+] Encoded first Muscle Memory: Homeostasis.")

    print("\n✅ Bootstrap Complete!")
    print("Next Steps:")
    print("1. Install requirements: pip install opencv-python numpy sentence-transformers openai psutil")
    print("2. Add your OPENAI_API_KEY to your environment variables.")
    print("3. Run your main.py to begin sensory monitoring.")

if __name__ == "__main__":
    setup_nsa()