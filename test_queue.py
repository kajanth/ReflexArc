import json
from utils.proposal_queue import attempt_implementation

class DummyRouter:
    def route(self, tier, messages):
        class DummyResponse:
            def __init__(self, c):
                self.content = c
                self.cost = 0
                self.total_tokens = 0
        
        # Simulate an LLM wrapping the output in markdown
        return DummyResponse("""
Here is the code patch you requested:

FILE: skills/dummy_skill.py
```python
def run(event_bus, data):
    print("Dummy skill updated via proposal queue!")
```
""")

if __name__ == "__main__":
    proposal = {
        "id": "prop_test_1",
        "agent": "CodeFixer",
        "content": "Make a dummy skill do something new."
    }
    
    # Create the dummy file so os.path.exists passes
    with open("skills/dummy_skill.py", "w") as f:
        f.write("def run(): pass\n")
        
    router = DummyRouter()
    print("Result:", attempt_implementation(proposal, router))
