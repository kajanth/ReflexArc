import sqlite3
from collections import Counter
from openai import OpenAI
import os

client = OpenAI(api_key="YOUR_API_KEY")

def run_sleep_cycle():
    print("--- Starting AI Sleep Cycle: Consolidating Memories ---")
    conn = sqlite3.connect("memory/long_term_memory.db")
    cursor = conn.cursor()

    # 1. Identify patterns: What 'COMPLEX' tasks happened most today?
    cursor.execute("SELECT description FROM memories WHERE timestamp > datetime('now', '-1 day')")
    memories = [row[0] for row in cursor.fetchall()]

    if not memories:
        print("[Sleep]: No new memories to process. Resting.")
        return

    # 2. Ask the Cortex to find a pattern that can be turned into a script
    summary = "\n".join(memories)
    refining_prompt = f"""
    The following events occurred today:
    {summary}
    
    Identify one repetitive task that can be automated with a Python script. 
    Output ONLY a valid Python function named 'run(data)' that handles this task.
    If no clear pattern exists, reply with 'NONE'.
    """

    response = client.chat.completions.create(
        model="gpt-5-mini-2025-08-07",
        messages=[{"role": "user", "content": refining_prompt}]
    )

    code = response.choices[0].message.content.strip()

    if "NONE" not in code:
        # 3. Save as a new Muscle Memory Skill
        skill_name = f"auto_skill_{len(os.listdir('skills'))}.py"
        with open(f"skills/{skill_name}", "w") as f:
            f.write(code.replace("```python", "").replace("```", ""))
        print(f"[Sleep]: New Muscle Memory acquired: {skill_name}")

    conn.close()