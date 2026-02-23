import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer

# We use the same local model as the RAS to keep the "Brain" consistent
memory_model = SentenceTransformer('all-MiniLM-L6-v2')

class Hippocampus:
    def __init__(self, db_path="memory/long_term_memory.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                sense_type TEXT,
                description TEXT,
                vector BLOB
            )
        ''')
        self.conn.commit()

    def store_memory(self, sense_type, description):
        """Encodes a description and saves it to the database."""
        vector = memory_model.encode(description).tobytes()
        self.cursor.execute(
            "INSERT INTO memories (sense_type, description, vector) VALUES (?, ?, ?)",
            (sense_type, description, vector)
        )
        self.conn.commit()
        print(f"[Hippocampus]: Memory Consolidated: {description[:30]}...")

    def retrieve_context(self, query_text, top_k=3):
        """Finds the most relevant historical context for a new stimulus."""
        query_vec = memory_model.encode(query_text)
        self.cursor.execute("SELECT description, vector FROM memories")
        rows = self.cursor.fetchall()

        if not rows:
            return "No prior context found."

        # Manual Cosine Similarity on local data
        scores = []
        for desc, vec_blob in rows:
            stored_vec = np.frombuffer(vec_blob, dtype=np.float32)
            similarity = np.dot(query_vec, stored_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(stored_vec))
            scores.append((similarity, desc))

        # Sort by similarity and return top results
        scores.sort(key=lambda x: x[0], reverse=True)
        context = [s[1] for s in scores[:top_k]]
        return " | ".join(context)