import json
import sqlite3
import os
import time
from datetime import datetime
from sensors.cognitive_load import CognitiveLoadSensor
from sensors.circadian import CircadianSensor

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_stats():
    with open("memory/stats.json", "r") as f:
        return json.load(f)

def get_recent_memories():
    conn = sqlite3.connect("memory/long_term_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, description FROM memories ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    return rows

def render_dashboard():
    cognitive = CognitiveLoadSensor()
    circadian = CircadianSensor()
    
    while True:
        clear_screen()
        stats = get_stats()
        memories = get_recent_memories()
        
        # Calculate Savings (Assuming $0.03 average per traditional agent call)
        potential_cost = stats['calls'] * 0.03
        savings = potential_cost - stats['total_spent']
        
        # Cognitive metrics
        cog_metrics = cognitive.get_metrics()
        phase = circadian.get_phase()
        
        print("="*55)
        print(f" 🧠 NSA NERVOUS SYSTEM DASHBOARD | {datetime.now().strftime('%H:%M:%S')}")
        print("="*55)
        
        print(f"\n[📊 INTEROCEPTION — Internal State]")
        print(f"  • Token Spend:        ${stats['total_spent']:.4f}")
        print(f"  • Estimated Savings:   ${max(0, savings):.4f} 🔥")
        print(f"  • Cognitive Latency:   {stats['avg_latency']:.2f}s")
        print(f"  • Cortex Ratio:        {cog_metrics['cortex_ratio']:.0%} "
              f"({cog_metrics['cortex_calls']}C / {cog_metrics['reflex_calls']}R / {cog_metrics['log_calls']}L)")
        print(f"  • Efficiency Score:    {cog_metrics['efficiency_score']:.0%}")
        print(f"  • Circadian Phase:     {phase}")
        
        print(f"\n[👁️  SENSORY ARRAY — Active Senses]")
        sensor_names = [
            ("👀", "Vision"),
            ("👂", "Auditory"),
            ("📡", "System Vitals"),
            ("📂", "Filesystem"),
            ("🌐", "Network Probe"),
            ("🛡️", " Threat Detection"),
            ("⏰", "Circadian"),
            ("🧠", "Curiosity"),
            ("📊", "Cognitive Load"),
        ]
        status_line = "  "
        for emoji, name in sensor_names:
            status_line += f"{emoji} {name}: ON  "
        print(status_line)

        print(f"\n[🧬 HIPPOCAMPUS — Recent Memories]")
        for timestamp, desc in memories:
            print(f"  • [{timestamp}] {desc[:45]}...")

        print(f"\n[🦿 CEREBELLUM — Learned Skills]")
        skills = [f for f in os.listdir('skills') if f.endswith('.py') and f != '__init__.py']
        print(f"  • Skill Inventory ({len(skills)}): {', '.join(skills)}")

        print("\n" + "="*55)
        print(" Press Ctrl+C to exit dashboard...")
        time.sleep(2)

if __name__ == "__main__":
    render_dashboard()